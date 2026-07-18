---
id: docker-proxy
layer: impl
title: docker-proxy 実装説明書
version: 1.0.0
updated: 2026-07-18
verified:
  at: 2026-07-18
  version: 1.0.0
  against:
    - doc: docs/02-design/system.md
      version: 1.0
summary: >
  Docker API を中継しつつ危険操作を拒否する Go 製リバースプロキシ。POST /containers/create と
  exec のボディを検査し、privileged・host namespace・危険 cap・デバイス・/workspace 外 bind を
  拒否、/workspace 配下 bind は実ホストパスへ書き換える。TCP:2375 で待受け Unix ソケットへ中継する。
keywords: [docker-proxy, Docker Socket Proxy, Go, リバースプロキシ, API検査, bind書換, hijack, セキュリティ]
depends_on: []
source:
  - docs/02-design/system.md
---

# 実装説明書:docker-proxy

## 概要

各 Claude コンテナが `DOCKER_HOST=tcp://claude-dev-docker-proxy:2375` 経由で Docker を使うための、
Go 製リバースプロキシ本体。生 `/var/run/docker.sock` をコンテナへ渡さず、本プロキシが HTTP リクエストを
受けて Unix ソケットへ中継する。中継の途中で `POST /containers/create` と exec 系のボディを検査し、
ホスト掌握につながる危険操作（privileged・host namespace・危険 capability・デバイス割当・`/workspace`
外の bind マウント）を `403` で拒否する。`/workspace` 配下の bind だけは呼び出し元プロジェクトの実ホスト
パスへ書き換えて許可する。上流: [全体設計](../02-design/system.md)（分割定義 docker-proxy 行 / コンテナ→
docker-proxy 契約 / 要件 core/7）。

## ファイル構成

| パス | 役割 |
|---|---|
| docker-proxy/main.go | プロキシ本体。中継・リクエスト検査・/workspace bind 書換・hijack 対応 |
| docker-proxy/main_test.go | 検査ロジック（container create / exec create）と正規表現の単体テスト |
| docker-proxy/binds_test.go | /workspace 配下 bind の封じ込め・書換・機能無効時挙動の単体/結合テスト |
| docker-proxy/go.mod | module 定義（`github.com/quvox/claude-dev-env/docker-proxy`, Go 1.22, 標準ライブラリのみ） |

## モジュール別実装詳細

### リクエストハンドラ（main.go `main` 内の `http.HandlerFunc`）

- **責務:** 全 Docker API リクエストの受口。パス正規化 → 全面拒否エンドポイント判定 → create/exec 検査 →
  hijack 判定 → 透過中継、の順に処理する（設計コンポーネント: docker-proxy 検査プロキシ）。
- **処理の要点:**
  1. パス先頭の `/v{version}` を剥がした `cleanPath` を作る（`/v1.45/containers/create` → `/containers/create`）。
  2. `cleanPath` が `blockedPathPrefixes`（`/swarm`, `/plugins`, `/configs`, `/secrets`）に前方一致すれば
     メソッドを問わず `403 Forbidden`。
  3. `POST` かつ `containerCreateRe` 一致 → `validateContainerCreate`。エラーなら `403`。
  4. `POST` かつ `containerExecCreateRe` 一致 → `validateExecCreate`。エラーなら `403`。
  5. `POST` かつ `hijackEndpointRe` 一致 → `handleHijack` に委譲して return。
  6. いずれにも該当しなければ `httputil.ReverseProxy` で透過中継（`ALLOW` ログ）。
- **正規表現:**
  - `containerCreateRe = ^(/v[\d.]+)?/containers/create`
  - `containerExecCreateRe = ^(/v[\d.]+)?/containers/[^/]+/exec`
  - `hijackEndpointRe = ^(/v[\d.]+)?/(exec/[^/]+/start|containers/[^/]+/attach|exec/[^/]+/resize|containers/[^/]+/resize)`
- **実装上の判断:** create 検査後にヒットする 3・4 は `return` せず後段の hijack 判定へ落ちうる構造だが、create
  パスと hijack パスは正規表現が排他のため実害はない。パース不能ボディは中継を許可する方針（Docker 側検証に委ねる）。

### リバースプロキシと Unix ソケット中継

- `httputil.ReverseProxy` の `Director` で `req.URL.Scheme="http"`・`req.URL.Host="docker"` を設定。
- `Transport.DialContext` は宛先を無視して常に `net.Dial("unix", "/var/run/docker.sock")` する。
- `ErrorHandler` は中継失敗を `502 Bad Gateway` で返しログ出力する。
- 起動時に `os.Stat(socketPath)` でソケット存在を確認し、無ければ `Fatal` で終了する。

### `validateContainerCreate`（main.go）

- **責務:** container create ボディを検査し、危険オプションを拒否・/workspace bind を書換（要件 core/7-2, 7-3）。
- **公開インターフェース（内部関数）:**

```
validateContainerCreate(r *http.Request, logger *log.Logger) -> error   // nil=許可, err=拒否
```

- **処理の要点:**
  - `readAndRestoreBody` でボディを読み、読み取り後に `io.NopCloser(bytes.NewReader(body))` で復元して中継可能に保つ。
  - `body` を最小構造体 `containerCreateBody{HostConfig *hostConfig}` へ unmarshal。パース失敗・`HostConfig` が
    `nil` なら許可（return nil）。
  - `HostConfig` が次のいずれかなら拒否: `Privileged==true` / `PidMode=="host"` / `NetworkMode=="host"` /
    `UsernsMode=="host"` / `CapAdd` に危険 cap（大文字化して `dangerousCapabilities` 照合）/ `Devices` が 1 件以上。
  - bind 処理: `allowWorkspaceBinds` が真かつ `resolveProjectDir(clientIP(r.RemoteAddr))` が解決できた場合のみ
    `projectDir` を得て、`rewriteBinds(body, projectDir)` を呼ぶ。書換があれば `r.Body`・`r.ContentLength`・
    `Content-Length` ヘッダを更新して中継。`rewriteBinds` がエラーを返せば拒否。
- **実装上の判断:** cap 照合は `strings.ToUpper` で大小無視。bind 検査は cap/device 検査より前に行うため、
  /workspace 外 bind は cap 内容に関わらず先に拒否される。

### bind 書換ロジック（`rewriteBinds` / `containWorkspacePath` / `resolveProjectDir`）

DooD 経路で「呼び出し元プロジェクトの `/workspace` 配下」だけ bind を許すための処理（要件 core/7-3）。

- **`resolveProjectDir(remoteIP) -> (string, bool)`**: 変数として保持されテスト時にスタブ注入可能
  （デフォルトは `cachedResolveProjectDir`）。`lookupProjectDir` が proxy 自身から `GET
  http://docker/containers/json` を実行し、各コンテナの `NetworkSettings.Networks[*].IPAddress` が
  `remoteIP` と一致するコンテナを探し、その `Mounts` で `Destination=="/workspace"` の `Source`（実ホスト
  パス）を返す。結果は `ip → dir` を TTL 60s（`projectCacheTTL`）で `sync.Mutex` 保護のキャッシュに保持。
  解決不能なら `""`（＝拒否側フォールバック）。
- **`containWorkspacePath(projectDir, containerSrc) -> (host string, ok bool)`**: 字句的封じ込め。
  `containerSrc` が `/workspace` または `/workspace/…` でなければ拒否。相対部を `filepath.Join(projectDir, rel)`
  し `filepath.Clean`。結果が `projectDir` と一致 or `projectDir + "/"` 前方一致でなければ（`..` 脱出）拒否。
  **symlink の実体解決は行わない**（proxy はホスト FS を持たず `EvalSymlinks` が常に失敗するため。字句的封じ込め
  のみで、プロジェクト内 symlink がホスト外を指す脱出は防げない＝残存リスク）。
- **`rewriteBinds(body, projectDir) -> (body []byte, changed bool, err error)`**: トップレベルと `HostConfig`
  を `map[string]json.RawMessage` で保持して他フィールドを壊さない。`Binds`（`[]string`, `src:dst[:opts]` の
  src のみ）と `Mounts`（`Type=="bind"` の各要素の `Source` のみ）を `containWorkspacePath` で検査・書換。
  `/` 始まりでない `Binds`（名前付きボリューム）や `Type!="bind"` の Mounts は素通し。封じ込め違反は error。
  `projectDir==""`（機能無効 or 呼び出し元不明）のとき、`/` 始まりの bind は全て拒否、名前付きボリュームは許可
  （従来動作）。変更があった場合のみ再エンコードして `changed=true`。

### `validateExecCreate`（main.go）

- ボディを最小構造体 `execCreateBody{Privileged bool}` へ unmarshal し、`Privileged==true` を拒否。
  パース不能なら許可。

### `handleHijack`（main.go）

- **責務:** HTTP Upgrade（`Upgrade: tcp`）を伴うストリーミング系（exec start / attach / resize）を生 TCP で中継。
  `httputil.ReverseProxy` が Upgrade を扱えないため専用実装。
- **処理の要点:** Docker ソケットへ `net.Dial("unix", ...)`。`http.Hijacker` でクライアント接続を奪取。元 HTTP
  リクエストを `r.Write(dockerConn)` で Docker へ送出後、双方向 `io.Copy`（Docker→Client, Client→Docker）を
  goroutine で実行。Client→Docker 側は HTTP サーバの `bufio.Reader` に残ったバッファを先に流してから生
  コネクションをコピー。各方向は完了時に `CloseWrite` で半クローズ、panic は recover でログ化。

## データアクセス

| データ | 操作 | 実施モジュール | 備考 |
|---|---|---|---|
| Docker Unix ソケット `/var/run/docker.sock` | 全 API 中継（ReverseProxy / hijack）+ `GET /containers/json`（呼び出し元 PROJECT_DIR 解決） | docker-proxy | `net.Dial("unix", ...)`。ソケット以外にホスト FS へアクセスしない |
| ip → PROJECT_DIR キャッシュ（インメモリ） | TTL 60s で読み書き | docker-proxy | `sync.Mutex` 保護。永続化なし |

## API実装詳細

本モジュールは Docker API を透過中継するプロキシであり、独自エンドポイントは持たない。中継時の検査・書換・
拒否の対応は以下（パスは `/v{version}` プレフィックス許容。判定は剥がした `cleanPath` で行う）。

### `/swarm`, `/plugins`, `/configs`, `/secrets`（前方一致・全メソッド）

- 動作: 常に `403 Forbidden`（本文 `blocked: <path> is not allowed`）。

### POST `/containers/create`

- 検査対象ボディ: `HostConfig`。
- 拒否（`403`, 本文 `blocked: <理由>`）: `Privileged:true` / `PidMode="host"` / `NetworkMode="host"` /
  `UsernsMode="host"` / `CapAdd` に `SYS_ADMIN`/`SYS_PTRACE`/`SYS_RAWIO`/`SYS_MODULE`/`DAC_READ_SEARCH` /
  `Devices` 1 件以上 / `Binds`・`Mounts(Type=bind)` の src が `/workspace` 外 or 封じ込め違反。
- 書換（許可）: `/workspace` 配下 bind の src を実ホスト PROJECT_DIR へ書換し中継（`Content-Length` 更新）。
- 透過（許可）: `HostConfig` なし・空ボディ・名前付きボリューム bind・`Type=volume/tmpfs` の Mounts・安全 cap。
- パース不能ボディ: 中継を許可（Docker 側検証に委ねる）。

### POST `/containers/{id}/exec`

- 拒否（`403`）: ボディ `Privileged:true`。それ以外は許可。

### POST `/exec/{id}/start`, `/containers/{id}/attach`, `/exec/{id}/resize`, `/containers/{id}/resize`

- 生 TCP hijack で中継（ストリーミング）。

### その他すべて

- `httputil.ReverseProxy` で透過中継。中継失敗時のみ `502 Bad Gateway`。

## 設定・環境変数

| 名前 | 用途 | デフォルト | 必須 |
|---|---|---|---|
| CLAUDE_DEV_ALLOW_WORKSPACE_BINDS | `/workspace` 配下 bind の許可・書換を有効化。`0`/`false`/`no`/`off`（小文字化して照合）で無効化し、全ホスト bind を拒否する従来動作に戻す | 有効（未設定＝有効） | 任意 |

補足（コード内定数）: `listenAddr=":2375"`（TCP 待受け。要件 core/7-1）、`socketPath="/var/run/docker.sock"`、
`workspaceMount="/workspace"`、`projectCacheTTL=60s`。ホスト非公開・`claude-dev-net` 内限定（要件 core/7-4）は
本プロキシ外（cli/devcontainer のネットワーク・ポート設定）で担保する。

## エラーハンドリング実装

| 異常系 | 実装箇所 | 実際の振る舞い | 対応する要件 |
|---|---|---|---|
| 全面拒否エンドポイント | ハンドラの `blockedPathPrefixes` ループ | `403` + `blocked: … is not allowed` | core/7-2（安全側） |
| 危険 create（privileged/host mode/危険 cap/device/外部 bind） | `validateContainerCreate` / `rewriteBinds` | `403` + `blocked: <理由>` | core/7-2 |
| privileged exec | `validateExecCreate` | `403` + `blocked: privileged exec is not allowed` | core/7-2 |
| 呼び出し元 PROJECT_DIR 解決不能 | `resolveProjectDir`→`projectDir=""` | 絶対 bind を全拒否（安全側フォールバック） | core/7-2,7-3 |
| ボディ parse 不能 | `validateContainerCreate`/`validateExecCreate`/`rewriteBinds` | 中継許可（Docker 側検証に委ねる）+ WARN ログ | 設計「判定不能は安全側」の例外＝正規 JSON 前提 |
| 中継失敗 | ReverseProxy `ErrorHandler` | `502 Bad Gateway` + ログ | — |
| hijack 中の panic | `handleHijack` の recover | ログ化して継続 | — |

## テスト

| テスト(ファイル::ケース名) | レベル | 検証内容 | 対応する受け入れ基準/契約 |
|---|---|---|---|
| main_test.go::TestValidateContainerCreate_AllowsCleanRequest | 単体 | クリーンな create を許可 | core/7-2 |
| main_test.go::TestValidateContainerCreate_AllowsNamedVolume | 単体 | 名前付きボリューム bind を許可 | core/7-2,7-3 |
| main_test.go::TestValidateContainerCreate_AllowsNoHostConfig | 単体 | HostConfig なしを許可 | core/7-2 |
| main_test.go::TestValidateContainerCreate_AllowsEmptyBody | 単体 | 空ボディ（nil body）を許可 | core/7-2 |
| main_test.go::TestValidateContainerCreate_AllowsSafeCaps | 単体 | 安全 cap（NET_ADMIN）を許可 | core/7-2 |
| main_test.go::TestValidateContainerCreate_BlocksHostBind | 単体 | ホストバインドを拒否 | core/7-2 |
| main_test.go::TestValidateContainerCreate_BlocksBindMount | 単体 | Mounts type=bind（/etc）を拒否 | core/7-2 |
| main_test.go::TestValidateContainerCreate_BlocksPrivileged | 単体 | privileged を拒否 | core/7-2 |
| main_test.go::TestValidateContainerCreate_BlocksPidHost | 単体 | PidMode=host を拒否 | core/7-2 |
| main_test.go::TestValidateContainerCreate_BlocksNetworkHost | 単体 | NetworkMode=host を拒否 | core/7-2 |
| main_test.go::TestValidateContainerCreate_BlocksUsernsHost | 単体 | UsernsMode=host を拒否 | core/7-2 |
| main_test.go::TestValidateContainerCreate_BlocksDangerousCaps | 単体 | 危険 cap（SYS_ADMIN）を拒否 | core/7-2 |
| main_test.go::TestValidateContainerCreate_BlocksDevices | 単体 | デバイスマッピングを拒否 | core/7-2 |
| main_test.go::TestValidateExecCreate_BlocksPrivileged | 単体 | privileged exec を拒否 | core/7-2 |
| main_test.go::TestValidateExecCreate_AllowsNormal | 単体 | 通常 exec を許可 | core/7-2 |
| main_test.go::TestContainerCreateRe | 単体 | create 正規表現がバージョン付き/なしを判定 | core/7-2 |
| main_test.go::TestHijackEndpointRe | 単体 | hijack 正規表現が start/attach/resize を判定 | core/7-1 |
| binds_test.go::TestContainWorkspacePath | 単体 | /workspace 配下→実パス、外部・prefix trick・.. 脱出・空 projectDir を拒否 | core/7-3 |
| binds_test.go::TestContainWorkspacePath_LexicalOnly | 単体 | symlink 非解決（字句受理）・.. 脱出は字句的に拒否 | core/7-3（残存リスク） |
| binds_test.go::TestRewriteBinds_RewritesUnderWorkspace | 単体 | /workspace/app→PROJECT_DIR/app 書換・opts/他フィールド保持・名前付きボリューム不変 | core/7-3 |
| binds_test.go::TestRewriteBinds_RejectsOutsideWorkspace | 単体 | /etc bind を拒否 | core/7-2 |
| binds_test.go::TestRewriteBinds_MountsBind | 単体 | Mounts type=bind の Source 書換・兄弟フィールド保持 | core/7-3 |
| binds_test.go::TestRewriteBinds_MountsBindOutsideRejected | 単体 | docker.sock の bind マウントを拒否 | core/7-2 |
| binds_test.go::TestRewriteBinds_EmptyProjectRejectsAbsolute | 単体 | 機能無効時に絶対 bind 拒否・名前付きボリューム素通し | core/7-3 |
| binds_test.go::TestValidateContainerCreate_RewritesWorkspaceBind | 結合 | `resolveProjectDir` をスタブ注入し、create ボディの /workspace/app が PROJECT_DIR/app へ書換され中継ボディに反映されることを検証 | 契約: コンテナ→docker-proxy |

実行方法: `cd docker-proxy && go test ./...`（[tech steering](../_steering/tech.md) の単体テストコマンド）。

補足: 「コンテナ→docker-proxy」契約の検証観点のうち「危険 bind/privileged/host mode 拒否・/workspace bind
書換・通常操作透過」は上記単体/結合テストで担保する。実 Docker デーモンを介したエンドツーエンドは E2E-3
（[e2e.md](e2e.md) 側）が担う。

## 既知の制限・技術的負債

- **検査はブラックリスト方式**: 「既知の危険オプション」を拒否するもので、Docker API 全面の安全性は保証しない。
  新たな危険項目は `blockedPathPrefixes`・検査項目の追加で対応する。
- **パース不能ボディは透過**: 検査は正規 JSON ボディを前提とする。破損ボディは Docker 側検証に委ねる。
- **bind 封じ込めは字句的（symlink 非解決）**: proxy はホスト FS を持たないため `EvalSymlinks` できず、
  プロジェクト内 symlink がホスト外を指す脱出は検出できない（残存リスク）。
- `resolveProjectDir` の TTL 60s の間、コンテナの /workspace マウント変更は反映が遅れうる。

## 運用メモ

- TCP:2375 で待受け、`/var/run/docker.sock` を bind マウントして起動する（イメージ定義・ネットワーク配線は
  devcontainer/cli 側）。ホストへポート公開しないこと（要件 core/7-4）。
- 動作ログは stdout に `[docker-proxy]` プレフィックスで出力（ALLOW / BLOCKED / HIJACK / REWRITE）。拒否理由の
  切り分けはこのログを参照する。
- `/workspace` bind を一時的に全面拒否したい場合は `CLAUDE_DEV_ALLOW_WORKSPACE_BINDS=0` で起動する。
