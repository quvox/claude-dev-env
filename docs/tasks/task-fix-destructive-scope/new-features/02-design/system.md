---
target: docs/02-design/system.md
change: replace
sections:
  - "## モジュール分割定義"
  - "### 結合テスト対象"
  - "### E2Eシナリオ一覧"
  - "#### SCR-01 cli-commands"
deletes: []
reason: MOD-cli-common が排他ロック(MODULE-cli-common-lock)を担うため分割定義の責務欄と機能数を、MOD-cli-reset がそれに依存するため依存欄を更新する(D0-env-08 項6 / DSN-env-02)。E2E-01 が破壊的操作の対象限定まで覆うのでシナリオ欄を更新する。logout / reset に `--yes` を公開フラグとして追加し(FR-env-03 受入基準 15・16)、`stop <name>` が受理する文字集合を制約に加える(FR-env-01 受入基準18)。UI 設計は画面・フィールド・状態の正なので、コマンド面の追加はここへ降ろす
reflected: 2026-08-04
---

## モジュール分割定義

<!-- 29モジュール。CLI はサブコマンド単位で1モジュール(決定シート 論点3)。
     機能(relations)は83本で、その境界は docs/03-impl/features.md が持つ。 -->

| モジュールID | 責務 | 対応要件 | 依存 | 詳細設計 | relations の接頭辞 |
|---|---|---|---|---|---|
| MOD-cli-common | ホスト CLI の共有基盤。コンテナ名の導出、稼働・存在・イメージの判定、インフラ(ネットワーク・共有ボリューム)の用意、SSH 鍵の選択と保存、noVNC URL の組み立て、実行ユーザの解決、**共有資源を触る6コマンドの排他ロックの取得・解放・残骸の引き継ぎ**(`D0-env-08` 項6 / `DSN-env-02`) | FR-env-01, FR-env-02, FR-env-03, FR-env-04, FR-env-09, FR-env-10, FR-env-11, NFR-ops-02, NFR-ops-03, NFR-scale-01, SR-01, SR-10, SR-11, SR-12, SR-20 | — | なし | `MODULE-cli-common-*` |
| MOD-cli-setup | イメージをビルドし、ネットワークと共有ボリュームを作る初回セットアップ | FR-env-01, FR-env-09, SR-01 | MOD-cli-common | なし | `MODULE-cli-setup` |
| MOD-cli-start | 開発コンテナの起動(既定はブラウザ確認あり)。再接続・VM モード・認証受け渡し・鍵転送・ポート割当を含む | FR-env-01〜08, FR-env-11, FR-env-12, NFR-avail-02, NFR-scale-01, NFR-sec-01, NFR-ops-02, SR-04, SR-14, SR-20 | MOD-cli-common | なし | `MODULE-cli-start` |
| MOD-cli-stop | セッションの停止と compose 生成物の片付け。遊休なら docker-proxy と SSH ブリッジも停止する | FR-env-01, FR-env-07, NFR-ops-02, SR-20 | MOD-cli-common | なし | `MODULE-cli-stop` |
| MOD-cli-attach | 実行中コンテナの tmux セッションへ接続する | FR-env-01, NFR-ops-02, SR-20 | MOD-cli-common | なし | `MODULE-cli-attach` |
| MOD-cli-code | 新しい tmux ウィンドウで Claude Code を起動する | FR-env-01, FR-env-08, FR-env-12, NFR-ops-02, SR-20 | MOD-cli-common | なし | `MODULE-cli-code` |
| MOD-cli-list | 実行中セッションの一覧と noVNC URL を表示する | FR-env-01, FR-env-11, NFR-ops-02, SR-20 | MOD-cli-common | なし | `MODULE-cli-list` |
| MOD-cli-login | Claude の OAuth ログインをコンテナ内で実行し共有ボリュームへ保存する | FR-env-03, NFR-ops-02, SR-03, SR-15, SR-20 | MOD-cli-common | なし | `MODULE-cli-login` |
| MOD-cli-login-codex | Codex のデバイス認証を実行し共有ボリュームの `codex/` へ保存する | FR-env-03, FR-env-12, NFR-scale-02, NFR-ops-02, SR-03, SR-15, SR-20 | MOD-cli-common | なし | `MODULE-cli-login-codex` |
| MOD-cli-logout | Claude と Codex の認証情報を共有ボリュームごと削除する | FR-env-03, NFR-scale-02, NFR-ops-02, SR-20 | MOD-cli-common | なし | `MODULE-cli-logout` |
| MOD-cli-forward | 指定ポートのホスト側フォワードを動的に追加する | FR-env-06, NFR-scale-01, NFR-ops-02, SR-20 | MOD-cli-common | なし | `MODULE-cli-forward` |
| MOD-cli-unforward | 指定ポートのフォワードを解除する | FR-env-06, NFR-ops-02, SR-20 | MOD-cli-common | なし | `MODULE-cli-unforward` |
| MOD-cli-ports | フォワード一覧と noVNC URL を表示する | FR-env-06, FR-env-11, NFR-ops-02, SR-20 | MOD-cli-common | なし | `MODULE-cli-ports` |
| MOD-cli-ssh-keys | 使う SSH 鍵の対話選択・保存・初期化(`select` / `reset` のディスパッチを含む) | FR-env-04, NFR-ops-02, SR-20 | MOD-cli-common | なし | `MODULE-cli-ssh-keys*` |
| MOD-cli-firewall | コンテナ内のファイアウォールルールを表示する | FR-env-05, NFR-ops-02, SR-20 | MOD-cli-common | なし | `MODULE-cli-firewall` |
| MOD-cli-orchestrate | コンテナ内で orchestrator を起動する(ゴール指定・`--fresh` 対応、未起動時の自動起動) | FR-orch-01, FR-orch-02, NFR-avail-01, NFR-ops-02, SR-20 | MOD-cli-common | なし | `MODULE-cli-orchestrate` |
| MOD-cli-pull | GHCR からビルド済みイメージを取得して以降の判定名へ付け替える | FR-env-09, NFR-ops-02, SR-20 | — | なし | `MODULE-cli-pull` |
| MOD-cli-upgrade | 全イメージをキャッシュ無しで再ビルドして更新する | FR-env-01, FR-env-09, NFR-ops-02, SR-20 | — | なし | `MODULE-cli-upgrade` |
| MOD-cli-reset | 管理ラベルを持つコンテナ・ボリューム・イメージを削除して初期状態へ戻す。**共有資源(docker-proxy / `claude-dev-net`)は遊休のときだけ削除し、他が稼働中なら残して「完全な初期化になっていない」ことを表示する**(`D0-env-08` 項2 / `FR-env-01` 受入基準9) | FR-env-01, FR-env-03, NFR-ops-02, SR-20 | MOD-cli-common | なし | `MODULE-cli-reset` |
| MOD-makefile | ビルド・セットアップ・CLI の導入/除去・ログイン・更新・自己検証題材の配置といった入口 | FR-env-01, FR-env-03, FR-env-07, FR-env-09, FR-env-10, FR-env-11, FR-env-12, FR-orch-01, FR-orch-09, NFR-ops-03, SR-10, SR-20, SR-30 | — | なし | `MODULE-makefile-*` |
| MOD-entrypoint | コンテナ起動時の初期化(UID/GID 追従・認証コピー・既定設定の生成/補完・ファイアウォール起動・MCP/VNC/Chrome・tmux・同期ループ・ポート同期の起動) | FR-env-02, FR-env-03, FR-env-05〜08, FR-env-11, FR-env-12, NFR-avail-02, NFR-avail-03, NFR-ops-02, NFR-scale-02, SR-02, SR-20 | MOD-firewall, MOD-portsync, MOD-vm-mode | なし | `MODULE-entrypoint-claude` |
| MOD-firewall | コンテナ内のブラックリスト型ファイアウォールの構成 | FR-env-05, NFR-sec-01, NFR-sec-02, NFR-avail-03, SR-02, SR-20 | — | なし | `MODULE-firewall-init` |
| MOD-docker-proxy | Docker API を検査・書き換えして透過中継する常駐プロキシ | FR-env-07, NFR-sec-01, SR-02, SR-04, SR-21, SR-31 | — | なし | `MODULE-docker-proxy-serve` |
| MOD-portsync | DooD 環境で公開ポートを検出し転送する | FR-env-06, FR-env-07, SR-20 | — | なし | `MODULE-portsync-dood` |
| MOD-vm-mode | ゲスト VM の起動・provision・ポート同期・資源逼迫の監視と操作ヘルパー | FR-env-06, FR-env-08, NFR-ops-01, NFR-avail-03, SR-14, SR-20 | — | なし | `MODULE-vm-mode-*` |
| MOD-orchestrator | 2モードの制御ループ、worker の並列実行と分離、タスク単位の介入、相互レビュー、TUI、通知、状態保全 | FR-orch-01〜FR-orch-08, NFR-perf-03, NFR-avail-01, NFR-avail-03, NFR-sec-03, NFR-ops-04, SR-21, SR-22, SR-31 | — | なし | `MODULE-orchestrator-*` |
| MOD-hooks | エージェントのフックからプロンプトを保存し、通知を送る | FR-orch-07, NFR-ops-01, NFR-sec-03, NFR-avail-03 | — | なし | `MODULE-hooks-*` |
| MOD-container-tools | コンテナ内で利用者が使う補助資産(レート制限の解除待ちなど) | FR-env-01, NFR-ops-01, SR-20 | — | なし | `MODULE-container-tools-*` |
| MOD-sample-project | 自己検証題材の配置と、題材そのもの | FR-orch-09, SR-23 | — | なし | `MODULE-sample-project-*` |

**分割定義に含めないもの**: コンテナイメージの定義(`Dockerfile.*`)と GHCR 配布ワークフローは
モジュールではなく、**イメージの作り方は `03-impl/environments/images.md`、GHCR への公開構成は
`03-impl/infra/local/ghcr.md`** が持つ(理由は `DSN-mod-05`)。

**どのモジュールにも属さない要件(8件)とその担い手**。上の表の「対応要件」に現れないのはこの8件
だけであり、いずれも「振る舞いを実装するモジュール」が原理的に存在しない種類の要件である
(割り当て漏れではない)。下の「要件カバレッジ確認」にも同じ担い手を書く。

| 要件 | 担い手 | なぜモジュールでないか |
|---|---|---|
| NFR-perf-01, NFR-perf-02 | `03-impl/environments/images.md`, `03-impl/infra/local/ghcr.md` | イメージのレイヤー構成とビルド設定が決める性能であり、実行される入口を持たない(`DSN-mod-05`) |
| SR-13(マルチアーキ), SR-24(マルチステージ), SR-33(CI 日次実行) | 同上 | 同上。ビルド・配布の構成そのもの |
| SR-05(信頼できる社内開発用途に限る) | `00-requests/request.md`「やらないこと」2 | 利用の前提条件であり、実装物を持たない |
| SR-32(Bash に自動テストを設けない) | 本書「テスト戦略」`DSN-test-01` | 「作らない」ことの宣言であり、実装物を持たない |
| SR-34(Codex を confinement を緩めずに実行) | `02-design/environments.md`「Codex実行設定」 | 外部エージェントの実行設定であり、製品コードのモジュールではない |

### 結合テスト対象

| 契約 ID | 契約の当事者 | テストを持つ責任モジュール |
|---|---|---|
| CTR-cli-container(**起動側**) | MOD-cli-start → MOD-entrypoint | MOD-entrypoint(呼び出し元はシェルで自動テストを持てないため観測側が担当。手段は実機確認) |
| CTR-cli-container(**破壊的操作の対象の識別**) | MOD-cli-start(管理ラベルの発行側)→ MOD-cli-stop / MOD-cli-logout / MOD-cli-reset(読み手) | **MOD-cli-stop / MOD-cli-logout / MOD-cli-reset**(読み手が観測側。`D0-env-08`。**発行側がラベルを付けるのをやめると読み手の削除対象が空になる**ため、契約の遵守は読み手の側でしか観測できない)。全モジュールがシェル実装で自動テストを持てないため、手段は**実機確認 = E2E-01 手順8**(`FR-env-01` 受入基準 9・14〜21 / `FR-env-03` 受入基準 14〜23) |
| CTR-entrypoint-firewall | MOD-entrypoint → MOD-firewall | MOD-entrypoint(手段は実機確認) |
| CTR-docker-api | Claude コンテナ → MOD-docker-proxy | MOD-docker-proxy(観測側。`go test` で機械検証) |
| CTR-cli-orchestrator | MOD-cli-orchestrate → MOD-orchestrator | MOD-orchestrator(観測側。実 tmux と実エージェントを要するため手段は実機確認=E2E-04 / E2E-05) |
| CTR-orchestrator-prompt | MOD-orchestrator → worker / 対話 Claude | MOD-orchestrator(生成と検知は `go test`。実プロセスとの結合は実機確認=E2E-04) |

**`CTR-cli-container` を2行に分けた理由**: この契約は当事者の異なる2つの取り決めを持つ。
起動時に渡す環境変数・オプション(`MOD-cli-start` → `MOD-entrypoint`)と、
**破壊的操作が削除対象を決めるための管理ラベル・遊休判定・ロックキー**
(`MOD-cli-start` が付け、`MOD-cli-stop` / `-logout` / `-reset` が読む)である。
後者は `MOD-entrypoint` を一切通らないため、1行目の責任モジュールでは観測できない。

### E2Eシナリオ一覧

| E2E ID | 対応 UC | シナリオ | 対象/対象外(理由) |
|---|---|---|---|
| E2E-01 | UC-01 | `claude-dev start`(ブラウザ確認あり / `--no-vnc`)→ `/workspace` マウント・認証・ファイアウォール・tmux → `claude` 起動 → 再実行での再接続。**続けて破壊的操作が「自分が作った資源」にだけ効くことを確認する**: 管理ラベルの付与 / 遊休判定がイメージに依存しないこと / 排他ロックと残骸の引き継ぎ / ラベルを持たない既存コンテナを巻き込まないこと / compose 資源が別プロジェクトを巻き込まないこと / `stop` が受理しない名前 / `logout` がプロジェクト配下の認証コピーを消すこと / 確認と非対話時の中止 / 削除失敗の列挙(`FR-env-01` 受入基準 9・14〜21 / `FR-env-03` 受入基準 14〜23) | 対象(Must) |
| E2E-02 | UC-02 | `claude-dev forward` → 8100 番台の割当と SSH トンネル → クライアントのブラウザで表示 → `claude-dev ports` で確認 | 対象(Must) |
| E2E-03 | UC-03 | コンテナ内で危険な `docker run` → 拒否 / `/workspace` bind の許可 / 通常操作の透過 | 対象(Must) |
| E2E-04 | UC-04 | `orchestrate` → ブレインストーミング → plan 確定 → worker 並列 → 要判断1件のみ待機・他は継続 → 回答で復帰 → 完了(`make orch-sample` で題材を配置して実走) | 対象(Must) |
| E2E-05 | UC-05 | 実行中に端末を全終了 → `orchestrate` 再実行 → 合流/再開・完了済みの非再実行・plan と履歴の保持 | 対象(Should) |
| E2E-06 | UC-06 | `claude-dev login-codex` → デバイス認証 → 別プロジェクトで `start` → 再ログイン不要で `codex` が起動し、**シェルコマンドが成功して `/workspace` を読み書きできる**。landlock の疎通確認が通り、読み取り専用の明示指定で読み取りが成功する。トークン更新が次のコンテナへ引き継がれる | 対象(Must) |

**全 UC がカバーされている**(UC-01〜UC-06 → E2E-01〜E2E-06)。上流の UC を持たない E2E シナリオは
作らない。

#### SCR-01 cli-commands

| 項目 | 型・制約 | 必須 | 備考 |
|---|---|---|---|
| サブコマンド | 18 種の列挙 | 必須 | 未知の語とヘルプ要求は使い方を表示する |
| 対象セッション名 | 文字列(省略時はカレントディレクトリから導出)。**`stop <name>` に限り `[A-Za-z0-9._-]` のみ受理する** | 任意 | `stop` / `ports` / `forward` など。**受理文字集合の制約は `stop` だけに掛かる**: `stop` は名前をそのまま排他ロックのキー=パス要素として使うため(`FR-env-01` 受入基準18)。受理できない文字を含む場合は**何も削除せず**理由を表示して終了コード 1 で終わる。`ports` / `forward` などは本変更で制約を変えない(ロックを取らないため) |
| フラグ | `--no-vnc` / `--kvm` / `--vm` / `--vm-fresh` / `--fresh` / **`--yes`** | 任意 | 非対応の組み合わせは実行前に拒否する。**`--yes` は破壊的操作(`logout` / `reset`)の確認プロンプトを飛ばす**(`D0-env-08` 項3)。端末を持たない環境で破壊的操作を実行する唯一の手段であり、指定が無ければ中止する |

状態: **初期**=使い方の表示 / **実行中**=進捗行(イメージ名・バージョン・待機の経過)/
**エラー**=日本語の原因と次の操作の案内 / **空**=対象セッションが無い旨 /
**完了**=接続 URL とアタッチ。

**破壊的操作の状態**(`logout` / `reset`): **確認**=削除対象の名前を1行ずつ列挙して同意を求める /
**中止**=同意が得られない、または端末が無く `--yes` も無い旨と `--yes` の指定方法 /
**一部失敗**=消えなかった資源を1件ずつ列挙(成功時の文言は出さない)/
**残した資源**=管理ラベルを持たないため削除しなかったコンテナの名前と、停止中のものは
列挙していない旨。

**排他待ちで中止の状態**(`start` / `stop` / `logout` / `reset` / `login` / `login-codex` の
**6コマンド共通**): 保持している操作の名前とプロセス ID と再実行の方法を表示し、終了コード 1 で
終わる(`FR-env-01` 受入基準16)。**破壊的操作だけの状態ではない**: 共有ボリュームまたは
docker-proxy を触る6コマンドすべてがこの状態を持つ。
