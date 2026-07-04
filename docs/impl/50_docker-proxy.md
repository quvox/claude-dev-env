---
summary: Docker APIを安全に中継するGo製リバースプロキシの検査ロジック・接続ハイジャック処理・テスト仕様を記述する。
keywords: [ Docker Socket Proxy, Go, リバースプロキシ, API検査, セキュリティ, hijack, コンテナ ]
---

# 実装仕様: docker-proxy/（Docker Socket Proxy）

> **この文書の役割**: Claude コンテナから Docker API を安全に利用させるための Go 製リバースプロキシの実装仕様。セキュリティ上の位置づけは `docs/03_security.md`、ビルドは [40_devcontainer.md](40_devcontainer.md) を参照。

## 要件（なぜ必要か）

生の `/var/run/docker.sock` をコンテナへ渡すと、ホストファイルシステムのバインドマウントや privileged コンテナ起動を通じてホストを掌握できてしまう。そこで Docker API を中継しつつ、**危険な操作だけをリクエスト検査で拒否**するプロキシを共有コンテナとして挟む。Claude コンテナは `DOCKER_HOST=tcp://claude-dev-docker-proxy:2375` 経由でのみ Docker を操作する。

## カバーするコード

```
docker-proxy/
├── main.go        プロキシ本体（中継 + リクエスト検査 + hijack 対応 + /workspace bind 書換）
├── main_test.go   検査ロジック・正規表現の単体テスト
├── binds_test.go  /workspace 配下 bind の許可・書換・封じ込めの単体/結合テスト
└── go.mod         module 定義
```

## 定数・ルール定義

- `listenAddr = ":2375"`、`socketPath = "/var/run/docker.sock"`。
- `dangerousCapabilities`: `SYS_ADMIN`, `SYS_PTRACE`, `SYS_RAWIO`, `SYS_MODULE`, `DAC_READ_SEARCH`（追加を拒否）。
- `blockedPathPrefixes`: `/swarm`, `/plugins`, `/configs`, `/secrets`（メソッド問わず全面拒否）。
- `workspaceMount = "/workspace"`（claude コンテナ内のプロジェクトマウント点）。環境変数 `CLAUDE_DEV_ALLOW_WORKSPACE_BINDS`（既定有効。`0`/`false`/`no` で無効）で `/workspace` 配下 bind 許可を切替。`resolveProjectDir` のキャッシュ TTL は既定 60s。
- 正規表現:
  - `containerCreateRe`: `POST /containers/create`（`/v{ver}` プレフィックス許容）。
  - `containerExecCreateRe`: `POST /containers/{id}/exec`。
  - `hijackEndpointRe`: `exec/{id}/start` / `containers/{id}/attach` / `exec/{id}/resize` / `containers/{id}/resize`（HTTP コネクション乗っ取りが必要なストリーミング系）。

## リクエスト処理フロー（`main` のハンドラ）

1. パスから `/v{ver}` プレフィックスを剥がした `cleanPath` を作る。
2. `blockedPathPrefixes` に前方一致したら `403 Forbidden`。
3. `POST` かつ `containerCreateRe` 一致 → `validateContainerCreate`。違反は `403`。
4. `POST` かつ `containerExecCreateRe` 一致 → `validateExecCreate`。違反は `403`。
5. `POST` かつ `hijackEndpointRe` 一致 → `handleHijack`（後述）。
6. 上記以外 → `httputil.ReverseProxy` で Unix ソケットへ中継（`ALLOW` ログ）。

ReverseProxy は `Director` で `scheme=http`/`host=docker` を設定し、`Transport.DialContext` で Unix ソケットへダイヤルする。

## 検査ロジック

### `validateContainerCreate`
リクエストボディを `readAndRestoreBody`（読み取り後に `io.NopCloser` で復元し中継可能にする）で取得し、`HostConfig` を最小構造体へ unmarshal。パース不能時は中継を許可（Docker 側の検証に委ねる）。`HostConfig` が次のいずれかに該当すれば拒否:
- `Privileged: true`
- `PidMode/NetworkMode/UsernsMode == "host"`
- `CapAdd` に `dangerousCapabilities` を含む（大文字化して照合）
- `Devices` が 1 件以上（デバイスマッピング全面拒否）

bind（`Binds` のホストパス〔`/` 始まり〕・`Mounts` の `Type=="bind"`）は **`rewriteBinds`/`containWorkspacePath`/`resolveProjectDir`（下記）** で処理する。名前付きボリューム（`/` 始まりでない `Binds`）・`Type=="volume"/"tmpfs"` は従来どおり許可。

### `/workspace` 配下 bind の許可・書き換え（`rewriteBinds` / `containWorkspacePath` / `resolveProjectDir`）
DooD 経路で「呼び出し元プロジェクトの `/workspace` 配下」だけ bind を許すための処理（設計 [../03_security.md](../03_security.md) §5「/workspace 配下 bind の許可」）。既定有効・環境変数 `CLAUDE_DEV_ALLOW_WORKSPACE_BINDS`（`0`/`false`/`no`/`off` で無効）で切替。

1. **有効性判定**: 機能無効なら従来動作（`/` 始まりの `Binds`・`Type==bind` の `Mounts` を拒否）。
2. **呼び出し元 `PROJECT_DIR` 解決** `resolveProjectDir(remoteIP)`:
   - `r.RemoteAddr` の IP を取り出し、proxy 自身が Unix ソケットへ `GET /containers/json` して各コンテナの `NetworkSettings.Networks[*].IPAddress` と一致するものを探す。
   - そのコンテナの `Mounts` で `Destination == "/workspace"` の `Source`（ホスト側パス）を `PROJECT_DIR` とする。
   - 結果は `ip → PROJECT_DIR` を短命 TTL（既定 60s）でキャッシュ（`sync.Mutex` 保護）。解決不能なら **拒否側にフォールバック**（安全側）。
3. **書き換え＋封じ込め** `containWorkspacePath(projectDir, containerSrc)`:
   - `containerSrc` が `/workspace` または `/workspace/…` でなければ（＝他のホストパス）**拒否**。
   - 相対部を `filepath.Join(projectDir, rel)` し `filepath.Clean`。結果が `projectDir` と一致 or `projectDir + "/"` 前方一致でなければ（`..` 脱出）**拒否**。
   - **封じ込めは字句的**（`Clean`＋前方一致）に限定し、**symlink の実体解決は行わない**。proxy コンテナはホスト FS を持たず（docker socket のみ）ホストパスの `EvalSymlinks`/`Lstat` は常に失敗するため。プロジェクト内 symlink がホスト外を指す脱出は防げない（残存リスク＝[../03_security.md](../03_security.md) §残存リスク）。
   - OK なら書き換え後ホストパスを返す。
4. **ボディ再構築**: 他フィールドを壊さないよう、トップレベルと `HostConfig` を `map[string]json.RawMessage` で保持し、`Binds`（`[]string`。`src:dst[:opts]` の src のみ書換）と `Mounts`（各要素 `map[string]json.RawMessage` の `Source` のみ書換）だけ再エンコードして差し替える。変更があれば `r.Body` と `Content-Length`/`r.ContentLength` を更新して中継。

### `validateExecCreate`
ボディの `Privileged: true` を拒否。

### `handleHijack`
`httputil.ReverseProxy` が HTTP Upgrade（`Upgrade: tcp`）のストリーミングを扱えないため、生 TCP で中継する。Docker ソケットへ `net.Dial("unix", ...)` し、`http.Hijacker` でクライアント接続を奪取。元 HTTP リクエストを Docker へ書き出した後、双方向に `io.Copy`（Docker→Client、Client→Docker）。Client→Docker 側は HTTP サーバの `bufio.Reader` に残ったバッファを先に流してから生コネクションをコピーする。各方向は完了時に `CloseWrite` で半クローズし、panic は recover でログ化。

## テスト（main_test.go / binds_test.go）

`validateContainerCreate` / `validateExecCreate` と 2 つの正規表現に対する単体テスト。主な観点:
- 許可: クリーンな create、名前付きボリューム、`HostConfig` なし、空ボディ、安全な cap（`NET_ADMIN`）、通常 exec。
- 拒否: ホストバインド、bind マウント、privileged、`PidMode`/`NetworkMode`/`UsernsMode=host`、危険 cap（`SYS_ADMIN`）、デバイスマッピング、privileged exec。
- 正規表現: `containerCreateRe` / `hijackEndpointRe` がバージョン付き/なしパスを正しく判定する。
- `/workspace` 配下 bind（`containWorkspacePath` / ボディ書換）: `/workspace/…`→`PROJECT_DIR/…` へ書換（`Binds` の opts 保持・`Mounts` の他フィールド保持）、`/workspace` 外のホストパス拒否、`..` 脱出拒否（字句的封じ込め。symlink は非解決＝残存リスク）、機能無効時は全ホスト bind 拒否。`resolveProjectDir` はテスト用に依存注入できる形にする（実 Docker API に触れず単体テスト可能にする）。

実行: `cd docker-proxy && go test ./...`。

## 注意点

- 検査はブラックリスト的に「既知の危険オプション」を拒否するもので、Docker API 全面の安全性を保証するものではない。`blockedPathPrefixes` と検査項目の更新で対応する。
- パース不能なボディは通す設計のため、検査は正規の JSON ボディを前提とする。
