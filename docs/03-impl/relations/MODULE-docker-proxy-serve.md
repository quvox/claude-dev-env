---
id: MODULE-docker-proxy-serve
module: MOD-docker-proxy
kind: tool
sync: sync
impl: docker-proxy/main.go::main
callers: なし
callees: なし
contracts: CTR-docker-api
design: DSN-mod-01, DSN-arch-01, DSN-mod-04
requirements: FR-env-07, NFR-sec-01
tests: docker-proxy/main_test.go::TestValidateContainerCreate_BlocksPrivileged, docker-proxy/main_test.go::TestValidateContainerCreate_BlocksPidHost, docker-proxy/main_test.go::TestValidateContainerCreate_BlocksNetworkHost, docker-proxy/main_test.go::TestValidateContainerCreate_BlocksUsernsHost, docker-proxy/main_test.go::TestValidateContainerCreate_BlocksDangerousCaps, docker-proxy/main_test.go::TestValidateContainerCreate_BlocksDevices, docker-proxy/main_test.go::TestValidateExecCreate_BlocksPrivileged, docker-proxy/main_test.go::TestContainerCreateRe, docker-proxy/main_test.go::TestHijackEndpointRe, docker-proxy/binds_test.go::TestContainWorkspacePath, docker-proxy/binds_test.go::TestContainWorkspacePath_LexicalOnly, docker-proxy/binds_test.go::TestRewriteBinds_RewritesUnderWorkspace, docker-proxy/binds_test.go::TestRewriteBinds_RejectsOutsideWorkspace, docker-proxy/binds_test.go::TestRewriteBinds_MountsBindOutsideRejected, docker-proxy/binds_test.go::TestValidateContainerCreate_RewritesWorkspaceBind
updated: 2026-08-02
summary: Docker API を検査・書き換えして透過中継する常駐プロキシ
---

# MODULE-docker-proxy-serve Docker API 検査プロキシ

## 目的

生の `/var/run/docker.sock` をコンテナへ渡さずに Docker を使えるようにする(FR-env-07・
NFR-sec-01)。ホスト掌握につながる操作(privileged・host namespace・危険 capability・デバイス
割り当て・`/workspace` 外の bind)を `403` で拒否し、`/workspace` 配下の bind だけを呼び出し元
プロジェクトの実ホストパスへ書き換えて通す。契約 `CTR-docker-api` の実装本体である。

## 処理の流れ

1. 起動時に `os.Stat("/var/run/docker.sock")` でソケットの存在を確認する。無ければ `Fatal` で終了する。
2. `http.ListenAndServe(listenAddr, handler)` で単一ハンドラの透過プロキシとして待ち受ける
   (ルート登録は無く、すべてのパスを1つのハンドラで受ける)。
3. リクエストごとに次の順で処理する:
   1. パス先頭の `/v{version}` を剥がした `cleanPath` を作る
      (`/v1.45/containers/create` → `/containers/create`)。
   2. `cleanPath` が `blockedPathPrefixes`(`/swarm` / `/plugins` / `/configs` / `/secrets`)に
      前方一致すれば、メソッドを問わず `403 Forbidden`(本文 `blocked: <path> is not allowed`)。
   3. `POST` かつ `containerCreateRe` に一致 → `validateContainerCreate`。エラーなら `403`。
   4. `POST` かつ `containerExecCreateRe` に一致 → `validateExecCreate`。エラーなら `403`。
   5. `POST` かつ `hijackEndpointRe` に一致 → `handleHijack` へ委譲する。
   6. どれにも当たらなければ `httputil.ReverseProxy` で透過中継する(`ALLOW` ログ)。
4. **`validateContainerCreate`**: ボディを読んで復元(`readAndRestoreBody`)し、
   `HostConfig` を検査する。`Privileged==true` / `PidMode=="host"` / `NetworkMode=="host"` /
   `UsernsMode=="host"` / `CapAdd` に危険 cap(`SYS_ADMIN` / `SYS_PTRACE` / `SYS_RAWIO` /
   `SYS_MODULE` / `DAC_READ_SEARCH`。大文字化して照合)/ `Devices` が1件以上 のいずれかで拒否する。
   パース不能や `HostConfig` が `nil` なら許可する(Docker 側の検証に委ねる)。
5. **bind の書き換え**: `allowWorkspaceBinds` が真で、`resolveProjectDir(clientIP)` が解決できた
   場合だけ `rewriteBinds(body, projectDir)` を呼ぶ。`containWorkspacePath` が
   「`/workspace` または `/workspace/…` であること」と「`filepath.Join` + `Clean` の結果が
   `projectDir` の配下に収まること」を字句的に検査し、実ホストパスへ書き換える。
   書き換えたら `r.Body` / `r.ContentLength` / `Content-Length` を更新して中継する。
   `projectDir` が空(機能無効または呼び出し元不明)のときは `/` 始まりの bind をすべて拒否し、
   名前付きボリュームは許可する。
6. **`resolveProjectDir`**: proxy 自身が `GET http://docker/containers/json` を実行し、
   `NetworkSettings.Networks[*].IPAddress` が呼び出し元 IP と一致するコンテナの `Mounts` から
   `Destination=="/workspace"` の `Source`(実ホストパス)を得る。結果は `ip → dir` を TTL 60 秒で
   `sync.Mutex` 保護のキャッシュに保持する。解決できなければ空文字(= 拒否側にフォールバック)。
7. **`handleHijack`**: `Upgrade: tcp` を伴う exec start / attach / resize を生 TCP で中継する
   (`httputil.ReverseProxy` は Upgrade を扱えないため専用実装)。Docker ソケットへ `net.Dial` し、
   `http.Hijacker` でクライアント接続を奪い、双方向 `io.Copy` を goroutine で回す。
   Client→Docker 側は HTTP サーバの `bufio.Reader` に残ったバッファを先に流す。各方向は完了時に
   `CloseWrite` で半クローズし、panic は recover でログにする。

## 呼び出され方

- 契機: `MODULE-cli-start` の `ensure_docker_proxy_container`(および `MODULE-makefile-*` の
  ビルド系)が用意したコンテナとして常駐し、各 Claude コンテナが
  `DOCKER_HOST=tcp://claude-dev-docker-proxy:2375` で HTTP を送ってきたとき。
- 前提条件: ホストの `/var/run/docker.sock` が RO マウントされていること。
  `claude-dev-net` に接続していること。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `CLAUDE_DEV_ALLOW_WORKSPACE_BINDS` | 環境変数 | 任意 | `1`(既定)で `/workspace` 配下 bind の書き換えを許可。`0` で全面拒否 |

- 認可: `claude-dev-net` に参加しているコンテナ(ネットワーク到達性が認可の境界)。

## 連携先と連携内容

連携先なし。Docker デーモンへの中継は Unix ソケットへの HTTP 呼び出しであり、機能間の辺には現れない。
呼び出し元(各 Claude コンテナ)も別プロセスなのでコールグラフ上の辺を持たない。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | HTTP レスポンス。許可 = Docker からの応答を透過、拒否 = `403 Forbidden`(本文 `blocked: <理由>`)、中継失敗 = `502 Bad Gateway` |
| 永続化 | なし。**触る資源は Docker Unix ソケット `/var/run/docker.sock`** と、インメモリの `ip → PROJECT_DIR` キャッシュ(TTL 60 秒・`sync.Mutex` 保護・永続化なし) |
| 発火するイベント | なし |
| ログ | 標準出力へ `ALLOW` / `BLOCK` と理由、中継失敗 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| Docker ソケットが存在しない | 起動時に `Fatal` で終了する | proxy コンテナが立たず、コンテナ内から Docker が使えない |
| 中継に失敗した | `ErrorHandler` が `502 Bad Gateway` を返しログへ出す | docker クライアントがエラーを受け取る |
| ボディが JSON として解釈できない | **許可する**(Docker 側の検証に委ねる) | 検査をすり抜けるが、Docker が最終的に弾く |
| 呼び出し元コンテナを特定できない | `resolveProjectDir` が空を返し、`/` 始まりの bind をすべて拒否する | 名前付きボリュームだけが使える |
| `/workspace` 外の bind | `403`(cap や device の検査より**前**に判定する) | 拒否理由が bind として返る |
| `..` によるパス脱出 | `containWorkspacePath` が `filepath.Clean` 後に `projectDir` 配下かを検査して拒否する | `403` |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | symlink の実体解決を行わず、字句的な封じ込めだけにする(proxy はホストのファイルシステムを持たず `EvalSymlinks` が常に失敗するため) | D0-sec-05 |
| 2 | パース不能なボディは中継を許可する(独自の解釈で誤って弾かないため) | D0-sec-05 |
| 3 | `resolveProjectDir` を変数として保持し、テストでスタブを注入できるようにする(この結果、静的解析では `cachedResolveProjectDir` / `lookupProjectDir` への辺が見えない) | D0-orch-02 |
| 4 | 標準ライブラリだけで実装する(依存を増やさない) | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| **字句的封じ込めのみで symlink 脱出を防げない** | プロジェクト内の symlink がホスト外を指していると、その先が bind されうる(残存リスク) | なし(意図した割り切り) |
| `cachedResolveProjectDir` / `lookupProjectDir` は関数値経由で呼ばれる | 静的解析では未到達に見える(Tier 2 の限界) | なし |
| create 検査の後に hijack 判定へ落ちうる構造 | create パスと hijack パスは正規表現が排他なので実害は無い | なし |
