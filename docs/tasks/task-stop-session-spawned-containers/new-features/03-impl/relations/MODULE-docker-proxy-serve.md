---
target: docs/03-impl/relations/MODULE-docker-proxy-serve.md
change: replace
sections:
  - "## 目的"
  - "## 処理の流れ"
  - "## 戻り値・副作用"
  - "## 異常系"
  - "## 実装上の判断"
  - "## 既知の制限"
reason: '`FR-env-07` 受入基準11・12 と `DSN-env-04` を docker-proxy 側の作業指示へ降ろす。(1) 目的に「作られた資源に所有者の印を付ける」を足す(**印を読んで削除するのはこの機能ではない**ことも書く)。(2) 処理の流れの 3-3(コンテナ作成の検査)に、拒否判定をすべて通過したあとで所有者ラベルを注入する手順を足し、**新しく `POST /networks/create` に一致する経路(3-4)を足す**(ネットワーク作成要求はこれまで検査対象ですらなく、透過中継されていた)。既存の hijack 判定と透過中継は番号だけ繰り下がる。注入の実体は bind の書き換え(`rewriteBinds`)と同じく、ボディを読んで書き換え `r.Body` / `ContentLength` / `Content-Length` を更新する経路である。(3) 戻り値・副作用のログ欄に付与・非付与の行を足す。(4) 異常系に3行(呼び出し元を特定できない / ボディを解釈できない / 利用者が同じキーを指定していた)を足す。(5) 実装上の判断に3件(注入を拒否判定の後に置く / 付与失敗で拒否しない / 呼び出し元の解決は既存のキャッシュに相乗りする)を足す。(6) 既知の制限に2行(印を付けられない要求の残存 / TTL 60 秒のキャッシュの窓)を足す。**拒否の判定基準は1つも変えない**。(7) **`/doc-check`(2026-08-07)の独立レビューの指摘により3点を直した**: 手順5 と手順6 がそれぞれ「`r.Body` / `ContentLength` / `Content-Length` を更新して中継する」と書いており、文面どおり実装すると判断8 の「ボディの再構成は1回」と矛盾する2回再構成になるため、書き戻しを手順6 の末尾1箇所に集約した(判断8 に既存15本の回帰も明記)/ 手順6 が `allowWorkspaceBinds` に触れておらず、同じ `resolveProjectDir` を使う手順5 の `if` へ畳み込むと bind 全面拒否の環境で所有者ラベルが黙って付かなくなるため、スイッチに依存しないことを明記した / 呼び出し元の判定に**値が空文字の場合**を加えた。あわせて変更相対語「本設計」を「`DSN-env-04` の導入」へ改めた(`docs/issues/056` の同型)'
id: MODULE-docker-proxy-serve
module: MOD-docker-proxy
kind: tool
sync: sync
impl: docker-proxy/main.go::main
callers: なし
callees: なし
contracts: CTR-docker-api
design: DSN-mod-01, DSN-arch-01, DSN-mod-04, DSN-env-04
requirements: FR-env-07, NFR-sec-01
tests: docker-proxy/labels_test.go::TestValidateContainerCreate_InjectsOwnerLabels, docker-proxy/labels_test.go::TestValidateContainerCreate_InjectsOwnerLabelsWithoutHostConfig, docker-proxy/labels_test.go::TestValidateContainerCreate_InjectionLeavesOtherFieldsIntact, docker-proxy/labels_test.go::TestValidateContainerCreate_OverwritesUserSuppliedOwnerLabel, docker-proxy/labels_test.go::TestValidateContainerCreate_NoOwnerLabelWhenCallerUnknown, docker-proxy/labels_test.go::TestValidateContainerCreate_NoOwnerLabelWhenProjectDirEmpty, docker-proxy/labels_test.go::TestValidateContainerCreate_UnparseableBodyRelayedUnchanged, docker-proxy/labels_test.go::TestValidateContainerCreate_RejectedRequestIsNotLabelled, docker-proxy/labels_test.go::TestValidateContainerCreate_BindRewriteAndLabelShareOneReconstruction, docker-proxy/labels_test.go::TestValidateContainerCreate_LabelsIndependentOfBindSwitch, docker-proxy/labels_test.go::TestLabelNetworkCreate_InjectsOwnerLabels, docker-proxy/labels_test.go::TestLabelNetworkCreate_NoOwnerLeavesBodyUntouched, docker-proxy/labels_test.go::TestNetworkCreateRe, docker-proxy/labels_test.go::TestInjectOwnerLabels_EmptyOwnerIsNoop, docker-proxy/main_test.go::TestValidateContainerCreate_BlocksPrivileged, docker-proxy/main_test.go::TestValidateContainerCreate_BlocksPidHost, docker-proxy/main_test.go::TestValidateContainerCreate_BlocksNetworkHost, docker-proxy/main_test.go::TestValidateContainerCreate_BlocksUsernsHost, docker-proxy/main_test.go::TestValidateContainerCreate_BlocksDangerousCaps, docker-proxy/main_test.go::TestValidateContainerCreate_BlocksDevices, docker-proxy/main_test.go::TestValidateExecCreate_BlocksPrivileged, docker-proxy/main_test.go::TestContainerCreateRe, docker-proxy/main_test.go::TestHijackEndpointRe, docker-proxy/binds_test.go::TestContainWorkspacePath, docker-proxy/binds_test.go::TestContainWorkspacePath_LexicalOnly, docker-proxy/binds_test.go::TestRewriteBinds_RewritesUnderWorkspace, docker-proxy/binds_test.go::TestRewriteBinds_RejectsOutsideWorkspace, docker-proxy/binds_test.go::TestRewriteBinds_MountsBindOutsideRejected, docker-proxy/binds_test.go::TestValidateContainerCreate_RewritesWorkspaceBind
updated: 2026-08-07
summary: Docker API を検査・書き換えして中継し、作られた資源に所有者ラベルを付ける常駐プロキシ
---

## 目的

生の `/var/run/docker.sock` をコンテナへ渡さずに Docker を使えるようにする(FR-env-07・
NFR-sec-01)。ホスト掌握につながる操作(privileged・host namespace・危険 capability・デバイス
割り当て・`/workspace` 外の bind)を `403` で拒否し、`/workspace` 配下の bind だけを呼び出し元
プロジェクトの実ホストパスへ書き換えて通す。

**あわせて、コンテナ作成要求とネットワーク作成要求に所有者ラベルを付けて中継する**
(`FR-env-07` 受入基準11。`DSN-env-04`)。これは「あとで誰が片付けてよいか」を資源自身に
持たせるための印であり、**印を読んで削除するのはこの機能ではない**
(`MODULE-cli-stop` / `MODULE-cli-reset` が読む)。

契約 `CTR-docker-api` の実装本体である。

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
      **所有者ラベルの注入はこの関数の中で行う**(手順6)。ハンドラから別に呼ばないのは、
      注入が「拒否判定をすべて通過したあと」でなければならず(判断5)、
      ボディの再構成を1回にまとめる(判断8)には bind の書き換えと同じ関数の中に
      置くのが最も短いからである。
   4. **`POST` かつ `networkCreateRe` に一致 → `labelNetworkCreate` が所有者ラベルを注入する**
      (手順6 と同じ注入を、拒否判定なしで行う専用の関数)。
      **拒否判定は持たない**(ネットワーク作成に、ホストを危険に晒す要素は無い)。
   5. `POST` かつ `containerExecCreateRe` に一致 → `validateExecCreate`。エラーなら `403`。
   6. `POST` かつ `hijackEndpointRe` に一致 → `handleHijack` へ委譲する。
   7. どれにも当たらなければ `httputil.ReverseProxy` で透過中継する(`ALLOW` ログ)。
4. **`validateContainerCreate`**: ボディを読んで復元(`readAndRestoreBody`)し、
   `HostConfig` を検査する。`Privileged==true` / `PidMode=="host"` / `NetworkMode=="host"` /
   `UsernsMode=="host"` / `CapAdd` に危険 cap(`SYS_ADMIN` / `SYS_PTRACE` / `SYS_RAWIO` /
   `SYS_MODULE` / `DAC_READ_SEARCH`。大文字化して照合)/ `Devices` が1件以上 のいずれかで拒否する。
   パース不能や `HostConfig` が `nil` なら許可する(Docker 側の検証に委ねる)。
5. **bind の書き換え**: `allowWorkspaceBinds` が真で、`resolveProjectDir(clientIP)` が解決できた
   場合だけ `rewriteBinds(body, projectDir)` を呼ぶ。`containWorkspacePath` が
   「`/workspace` または `/workspace/…` であること」と「`filepath.Join` + `Clean` の結果が
   `projectDir` の配下に収まること」を字句的に検査し、実ホストパスへ書き換える。
   `projectDir` が空(機能無効または呼び出し元不明)のときは `/` 始まりの bind をすべて拒否し、
   名前付きボリュームは許可する。
   **書き戻しはここでは行わない**(手順6 の注入と同じ要求で起きうるため、`r.Body` /
   `r.ContentLength` / `Content-Length` の更新は手順6 の末尾で1回だけ行う。判断8)。
6. **所有者ラベルの注入**(`FR-env-07` 受入基準11・12。`DSN-env-04`):
   - **前提**: **手順4 の拒否判定をすべて通過していること。** 拒否される要求に印を付けても
     意味が無く、注入を先に置くと注入の失敗が拒否判定に影響しうる。
   - **`allowWorkspaceBinds`(`CLAUDE_DEV_ALLOW_WORKSPACE_BINDS`)の値によらず行う。**
     手順5 と同じ `resolveProjectDir` を使うので同じ `if` へ畳み込みたくなるが、畳み込むと
     bind を全面拒否へ倒した環境で所有者ラベルが付かなくなり、`stop` の片付けが全件空振りする
     (契約 `CTR-docker-api`「検査する要素と判定」が明示する)。
   - 接続元 IP から呼び出し元コンテナを引き当て、**そのコンテナの `claude-dev.project-dir`
     ラベルの値**を所有者として得る。**`/workspace` のマウント元(手順5 が bind の書き換えに
     使う値)ではない**: `stop` は `claude-dev.owner-project-dir` と `claude-dev.project-dir` の
     **文字列一致**で削除対象を選ぶので、2つを同じ1つのラベルから取ることで一致を
     構成上の帰結にする(`DSN-env-04`)。
     **`GET /containers/json` の応答は `Labels` を含む**ので、手順7 の問い合わせを1回増やさずに
     同時に取れる(キャッシュも共有する)。
   - **ラベルを持たない、値が空文字である、またはコンテナを引き当てられない場合は
     「所有者を得られなかった」として扱う**(空値を写すと、`stop` では引けないが `reset` では
     消える資源ができ、両側が同じ1つのラベルに依存するという根拠がその1点で破れる。
     契約 `CTR-cli-container` の `DSN-env-04`「呼び出し元を特定できた」の定義)。
   - 解決できた場合、ボディの**トップレベルの `Labels` オブジェクト**に
     `claude-dev.role=spawned` と `claude-dev.owner-project-dir=<絶対パス>` を書き込む
     (`Labels` が無ければ作る)。**利用者が同じキーを指定していた場合は上書きする**。
     **それ以外のフィールドは触らない。**
   - **手順5 の bind 書き換えと本手順の注入をすべて済ませてから、最後に1回だけ**
     `r.Body` / `r.ContentLength` / `Content-Length` を更新して中継する
     (**ボディの再構成は要求あたり1回だけ**。判断8)。どちらも起きなかった要求は
     ボディに触れずにそのまま中継する。
   - **解決できない、ボディを解釈できない、書き換えに失敗した場合は、元のボディのまま中継する**
     (作成を拒否しない。`FR-env-07` 受入基準12)。
   - **`HostConfig` を持たない要求にも注入する。** `docker run alpine true` が出すボディは
     `HostConfig` を持たないことがあり、そこで早期に戻ると**最も普通の作り方で作られた
     コンテナに印が付かない**。拒否判定は `HostConfig` があるときだけ行い、注入はその外に置く。
   - **ボリューム作成要求には注入しない**(名前付きボリュームは片付けの対象外である)。
7. **呼び出し元の解決**: proxy 自身が `GET http://docker/containers/json` を実行し、
   `NetworkSettings.Networks[*].IPAddress` が呼び出し元 IP と一致するコンテナから**2つの値**を得る。
   結果は `ip → (2値)` を TTL 60 秒で `sync.Mutex` 保護のキャッシュに保持する。
   - **bind の書き換え用**: `Mounts` の `Destination=="/workspace"` の `Source`(実ホストパス)。
     得られなければ空文字(= `/` 始まりの bind をすべて拒否する)。
   - **所有者ラベル用**: `Labels` の `claude-dev.project-dir` の値。
     得られなければ空文字(= 所有者ラベルを付けない)。
   **2つは別々に空になりうる**(ラベルを持たない Claude コンテナでは前者だけが得られる)。
   **問い合わせは1回で足りる**(同じ応答から両方を読む)。
8. **`handleHijack`**: `Upgrade: tcp` を伴う exec start / attach / resize を生 TCP で中継する
   (`httputil.ReverseProxy` は Upgrade を扱えないため専用実装)。Docker ソケットへ `net.Dial` し、
   `http.Hijacker` でクライアント接続を奪い、双方向 `io.Copy` を goroutine で回す。
   Client→Docker 側は HTTP サーバの `bufio.Reader` に残ったバッファを先に流す。各方向は完了時に
   `CloseWrite` で半クローズし、panic は recover でログにする。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | HTTP レスポンス。許可 = Docker からの応答を透過、拒否 = `403 Forbidden`(本文 `blocked: <理由>`)、中継失敗 = `502 Bad Gateway`。**所有者ラベルの注入は応答を変えない**(要求ボディだけを書き換える) |
| 永続化 | なし。**触る資源は Docker Unix ソケット `/var/run/docker.sock`** と、インメモリの `ip → PROJECT_DIR` キャッシュ(TTL 60 秒・`sync.Mutex` 保護・永続化なし)。**副作用として、作成されるコンテナとネットワークにラベル `claude-dev.role` / `claude-dev.owner-project-dir` が付く**(資源そのものは Docker が作る) |
| 発火するイベント | なし |
| ログ | 標準出力へ `ALLOW` / `BLOCK` と理由、中継失敗。**所有者ラベルを付与したときは付与した資源の種別と所有者(絶対パス)、付与しなかったときはその理由**(呼び出し元を特定できない / ボディを解釈できない)を出す |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| Docker ソケットが存在しない | 起動時に `Fatal` で終了する | proxy コンテナが立たず、コンテナ内から Docker が使えない |
| 中継に失敗した | `ErrorHandler` が `502 Bad Gateway` を返しログへ出す | docker クライアントがエラーを受け取る |
| ボディが JSON として解釈できない | **許可する**(Docker 側の検証に委ねる)。**所有者ラベルも注入できない** | 検査をすり抜けるが、Docker が最終的に弾く。**作られた資源は `stop` / `reset` の片付け対象から外れる**(`FR-env-07` 受入基準12) |
| 呼び出し元コンテナを特定できない(接続元 IP に一致するコンテナが無い) | 2値とも空になる。`/` 始まりの bind をすべて拒否し、**所有者ラベルも付与せずに中継する**(作成は拒否しない) | 名前付きボリュームだけが使える。**作られた資源は片付け対象から外れる** |
| **呼び出し元は特定できたが `claude-dev.project-dir` ラベルを持たない**(管理ラベルが付く前に起動された Claude コンテナ) | **bind の書き換えは通常どおり行う**(マウント元は得られる)。**所有者ラベルだけを付与せずに中継する** | そのセッションから作られた資源は片付け対象から外れる。**`stop` 側も同じラベルが読めず片付けをスキップする**ので、片方だけが成功する状態は生じない |
| **所有者ラベルの書き込みに失敗した**(ボディの再構成に失敗した等) | **元のボディのまま中継する**(作成を拒否しない)。理由をログへ出す | 作られた資源は片付け対象から外れる |
| **利用者が `claude-dev.role` / `claude-dev.owner-project-dir` と同じキーのラベルを指定していた** | **proxy の値で上書きする** | 利用者の指定は失われる。所有者の判定が利用者の入力で狂わない |
| `/workspace` 外の bind | `403`(cap や device の検査より**前**に判定する) | 拒否理由が bind として返る |
| `..` によるパス脱出 | `containWorkspacePath` が `filepath.Clean` 後に `projectDir` 配下かを検査して拒否する | `403` |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | symlink の実体解決を行わず、字句的な封じ込めだけにする(proxy はホストのファイルシステムを持たず `EvalSymlinks` が常に失敗するため) | D0-sec-05 |
| 2 | パース不能なボディは中継を許可する(独自の解釈で誤って弾かないため) | D0-sec-05 |
| 3 | `resolveProjectDir` を変数として保持し、テストでスタブを注入できるようにする(この結果、静的解析では `cachedResolveProjectDir` / `lookupProjectDir` への辺が見えない) | D0-orch-02 |
| 4 | 標準ライブラリだけで実装する(依存を増やさない) | D0-scope-02 |
| 5 | **所有者ラベルの注入を、拒否判定をすべて通過したあとに置く。** 拒否される要求に印を付けても意味が無く、注入を先に置くと注入の失敗が拒否判定を飛ばしうる。**ネットワーク作成要求は拒否判定を持たない**ので、注入だけを行う | D0-env-10 / `DSN-env-04` |
| 6 | **注入に失敗しても作成要求を拒否しない**(元のボディのまま中継する)。`DSN-dp-01`「判定できない入力は通す」と同じ倒し方であり、片付けの都合でコンテナが作れなくなるほうが害が大きい。**代償は「片付けられない資源が生じうる」ことで、それは「既知の制限」に書く** | D0-env-10 / `D0-sec-05` |
| 7 | **呼び出し元の解決を既存の `resolveProjectDir` の経路に相乗りさせ、同じ応答から `Labels` の `claude-dev.project-dir` も取り出す**(戻り値を2値に増やし、キャッシュも2値で持つ)。**Docker への問い合わせは要求あたり1回のまま**である。**所有者ラベルの値にマウント元を使わないのは**、`stop` が照合する `claude-dev.project-dir` と別の出所になり、両者が一致する保証が仕様として存在しないためである(`DSN-env-04`)。**テストのためのスタブ注入(判断3)はこの2値の関数に対して行う** | D0-scope-02 / `DSN-env-04` |
| 8 | **ボディの再構成を1回にまとめる**(bind の書き換えと所有者ラベルの注入が同じ要求で起きうるため)。2回に分けると `Content-Length` の更新が二重になり、片方の書き換えが失われる経路ができる。**したがって手順5 は書き戻さず、手順6 の末尾で1回だけ `r.Body` / `ContentLength` / `Content-Length` を更新する**。回帰の確かめ方は `03-impl/tests/docker-proxy.md`「テスト設計の判断」が持つ | D0-scope-02 |
| 9 | **ネットワーク作成のパスを、コンテナ作成と同じく版接頭辞を許す正規表現で判定する**(`/v1.45/networks/create` と `/networks/create` の双方が来る) | D0-scope-02 |
| 10 | **注入の本体を `injectOwnerLabels(body, owner) ([]byte, bool)` として切り出し、コンテナ作成とネットワーク作成の双方から呼ぶ。** 書き戻しも `writeBackBody(r, body)` の1つに集約する。両経路で「トップレベルの `Labels` に2つ書く」ことは同一なので、分けると片方だけ直る経路ができる | D0-scope-02 |
| 11 | **`resolveProjectDir` の戻り値を `(workspaceSource, ownerProjectDir string)` の2値にし、`ok` を落とす**。どちらも「得られなければ空文字」で表せるうえ、**2つは別々に空になりうる**(管理ラベルを持たない Claude コンテナでは前者だけ得られる)ので、1つの `ok` では表せない | D0-scope-02 / `DSN-env-04` |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| **字句的封じ込めのみで symlink 脱出を防げない** | プロジェクト内の symlink がホスト外を指していると、その先が bind されうる(残存リスク) | なし(意図した割り切り) |
| `cachedResolveProjectDir` / `lookupProjectDir` は関数値経由で呼ばれる | 静的解析では未到達に見える(Tier 2 の限界) | なし |
| create 検査の後に hijack 判定へ落ちうる構造 | create パスと hijack パスは正規表現が排他なので実害は無い | なし |
| **解釈できないリクエストボディは検査せず中継する** | 拒否すべき操作がそのボディに含まれていても通る(最終的な検証は Docker daemon 側だけになる)。`AC-03`「危険な操作は拒否される」に対する残存リスクである。**あわせて所有者ラベルも付けられないので、その資源は `stop` / `reset` の片付け対象から外れる** | `docs/issues/005-modify-docker-proxy-relays-unparseable-bodies.md` |
| **呼び出し元を特定できない要求で作られた資源には所有者ラベルが付かない** | その資源は `stop` / `reset` で片付けられず、ホストに残る。**利用者への表示も行わない**(印が無い以上、存在を知る手段が無い) | なし(閾値の外: **00 が「そう決めた」と明示しているもの**。`D0-env-08` 項8 / `FR-env-07` 受入基準12) |
| **管理ラベルを持たない Claude コンテナからの要求にも所有者ラベルが付かない** | 管理ラベルが付く前に起動されたコンテナの中から作られた資源は片付け対象から外れる。**bind の書き換えは効くので、利用者から見て Docker は普通に使える**(気づく手掛かりが無い) | なし(閾値の外: `stop` 側にも同じ限界があり、利用者への表示はそちらが行う。`MODULE-cli-stop` の「既知の制限」) |
| **呼び出し元の解決結果を TTL 60 秒でキャッシュする** | コンテナが消えて同じ IP が別のコンテナへ再割り当てされた直後の最大 60 秒間、**古い所有者を書き込みうる**。その資源は前の所有者の `stop` で消える(`reset` では所有者を問わないので影響しない) | なし(閾値の外: 同じ IP の再割り当ては Docker のネットワークプールが枯渇に近づいたときに起きる。被害は「別セッションの `stop` で消える」ことで、`reset` は所有者を問わないため回収はできる) |
| **ラベルを付けるのは作成時だけである** | 既に存在するコンテナに後から印を付ける経路は無い(Docker API にラベルの追加が無い)。**`DSN-env-04` の導入より前に作られた資源は永久に対象外である** | なし(閾値の外: `D0-env-08` 項8 が明示) |
