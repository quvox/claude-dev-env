---
id: terminology
version: 1.2.0
updated: 2026-08-05
source:
  - docs/00-requests/request.md
summary: 本システムで使う語の定義・英語表記(識別子)・使ってはいけない言い方
keywords: [用語集, 識別子, 表記ゆれ]
verified:
  at: 2026-08-05
  version: 1.2.0
  against:
    - doc: docs/00-requests/request.md
      version: 1.3.0
---

# 用語集

| 用語 | 定義 | 含む例 | 含まない例 | 英語表記(識別子) | 使ってはいけない言い方 |
|---|---|---|---|---|---|
| 安全 | **ホストのあらゆる情報を破壊しないこと、および鍵情報が直接漏洩しないこと**。ただし claude や codex のログイントークンのような**一過性のもの**は除く。観測可能な形は `NFR-sec-01`(隔離と最小権限の4項目)と `D0-env-08`(破壊的操作の対象は自分が作った資源に限る)が定める | ホストの `~/.ssh/` の秘密鍵ファイルがコンテナから読めないこと / `claude-dev stop` が管理ラベルを持たないコンテナを削除しないこと | 共有ボリュームに置いた Claude / Codex のログイントークンがコンテナから読めること(**一過性の資格情報**なので本定義の「鍵情報」に含まない) | safety | 「安全に」「安全な」(**何が守られるかを伴わない表現**)。定義を指さずにこの語を単独で使わない |
| 公開ポート | ホスト側のポート番号がコンテナのポートへ結び付けられ、**ホストのネットワークから到達できる状態**にあるポート | `claude-dev forward 5173` が立てる中継のホスト側ポート / VM モードのポート同期が開くポート | ブラウザ確認ありの構成で `claude-dev start` が開く **noVNC の 6080 番台**(`D0-env-02` が明示した例外であり、利用者の Web アプリ用ポートではない) | published port | 「ポートが開いている」(どちら側のポートか、到達できるのは誰かを伴わない表現) |
| ブロック対象ドメイン | ファイアウォールが外向き通信を拒否するドメインの集合。**設定で与えられる**(既定は `scripts/init-firewall-claude.sh` の `BLACKLIST_DOMAINS` 配列に同梱する16件)。**集合の中身は仕様で固定しない**(利用者が編集する前提のテンプレートである) | `pastebin.com`(ペーストサイト系9件)/ `webhook.site`(Webhook テスト系3件)/ `ngrok.io`(トンネリング系4件) | コメントアウトされた本番環境の雛形2件(適用されない)/ クラウドメタデータの IP(`169.254.169.254` ほか)と SMTP ポート(**別の規則**で拒否するのでこの集合に含まない) | `BLACKLIST_DOMAINS` | 「危険なサイト」「怪しいドメイン」(集合が特定できない表現) |
| 破壊的操作 | **利用者の作業内容またはログイン状態を失わせうる削除**を行うサブコマンド。現時点では `claude-dev stop` / `claude-dev logout` / `claude-dev reset` の3つを指す(`D0-env-08`) | `claude-dev logout`(共有ボリュームの認証を消す)/ `claude-dev reset`(共有資源を消す) | `claude-dev list` / `claude-dev ports`(読み取りだけ)/ `claude-dev unforward`(中継コンテナだけを消し、作業内容もログイン状態も失わせない) | destructive command | 「危険な操作」(Docker API 側の拒否対象 = `FR-env-07` と混同する) |
| 管理ラベル | 本システムが Docker 資源を作るときに付ける **Docker ラベル**。「本システムが作った」ことと「どのプロジェクトのものか」を表す。名前と値の形式は契約 `CTR-cli-container` が定める(`D0-env-08` / `D0-env-10`) | プロジェクトごとの Claude コンテナに付く、所有と対象プロジェクトを表すラベル | docker-proxy / `fwd-*` 中継コンテナ / 共有ボリューム / ネットワーク / イメージ(**固定名または固定接頭辞で所有権が読み取れる**ので、ラベルではなく名前で識別する) | management label | 「タグ」(Docker のイメージタグと紛れる) |
| 資源逼迫 | **ゲスト VM の QEMU プロセスの CPU 使用率が、割り当て上限(`-smp` の値)に対して 60% 以上である状態が、15 秒周期で 12 回連続(合計約3分)観測された状態**。この状態で監視デーモンがヘルスファイルに `STATE=WARN` を書き、tmux とダッシュボードが警告を表示する。**この3つの数値は既定値であり、上書きする手段は `03-impl` が定める**(一次情報は `MODULE-vm-mode-healthd`) | 4 vCPU を割り当てた VM で QEMU の CPU 使用率が 240%(= 上限比 60%)以上を約3分続けた状態 | 同じ負荷が 1 分で収まった状態(12 回連続に達しない)/ ゲストの RAM 使用率だけが高く CPU 使用率が閾値未満の状態(**監視は CPU 使用率しか見ない**) | resource pressure | 「重い」「逼迫している」(閾値を伴わない表現)。「RAM 逼迫」(本定義は CPU 使用率だけを見るので別概念になる) |
| claude-dev | ホスト側 CLI。コンテナのライフサイクル・認証・ポート・SSH 鍵を操作する。Linux は `claude-dev`、macOS は `claude-dev-mac`(`make install` が OS を判定して symlink を統一する) | | | `claude-dev` / `claude-dev-mac` | 「CLIツール」単独表記 |
| Claude コンテナ | プロジェクトごとに起動する開発用コンテナ。ブラウザ確認あり(`claude-dev-claude-vnc`)/なし(`claude-dev-claude`) | | | `claude-dev-<project>` | — (「プロジェクトコンテナ」は同義。文脈で使い分ける) |
| Codex CLI | OpenAI 製のコーディングエージェント CLI(npm パッケージ `@openai/codex`、コマンド名 `codex`)。Claude コンテナに同梱し、`codex login --device-auth` で認証する。認証ファイルは `~/.codex/auth.json` | | | `codex` | 本文で `codex` と書く(コマンド名を指すときのみ可) |
| Codex サンドボックス | Codex CLI がシェルコマンドを実行する際に張る自前の隔離機構。強度は `config.toml` の `sandbox_mode`(`read-only` / `workspace-write` / `danger-full-access`)で決まる。Linux には bubblewrap(既定。Claude コンテナ内では起動できない)と landlock(`features.use_legacy_landlock` で選ぶ。読み取り専用のみ実用)の 2 バックエンドがある | | | `sandbox_mode` | bubblewrap / bwrap / landlock は実装名。方針を語るときは「Codex サンドボックス」と書く |
| docker-proxy | Docker Socket Proxy。生ソケットを直接使わせず、危険な Docker API を拒否する Go 製リバースプロキシ。全 Claude コンテナで共有する | | | `claude-dev-docker-proxy` | 「プロキシ」単独 |
| forward プロキシ | `claude-dev forward` が立てる `fwd-<name>-<port>` の socat コンテナ。Web アプリのポート中継用 | | | `fwd-<name>-<port>` | docker-proxy と混同する書き方 |
| DooD | Docker-outside-of-Docker。コンテナがホストの Docker デーモンを(docker-proxy 経由で)使う既定方式 | | | `dood` | DinD(本構成では非採用)と混同する書き方 |
| VM モード | オプトイン(`--vm`)。ゲスト VM(QEMU+virtiofs)内でネイティブ Docker を動かす層構成 | | | `vm-mode` | — |
| オーケストレーター | プロジェクトに1体立てる AIオーケストレーター。ブレインストーミング/実行の2モードを持つ「1実体」 | | | `orchestrator` | リードエージェント(旧称) |
| コントローラ | オーケストレーターの外部制御ループ本体(Go 実装。`orchestrate` で起動し tmux に常駐する) | | | `controller` | — |
| worker | 実装/レビューを行うコーディングエージェント(`claude -p`)。git worktree で分離する | | | `worker` | ワーカー、コーディングエージェント(同義だが表記は worker に統一) |
| ブレインストーミングモード | 人間×対話 Claude でゴール/仕様を固める検討モード(自動化しない) | | | `brainstorming` | ブレスト(本文では正式名を使う) |
| 実行モード | plan の各タスクを worker へ並行ディスパッチして自律実装するモード | | | `execute` | — |
| 介入 | 実行中に要判断が出たタスク1件を保留し、その worker ウィンドウで対話 Claude に諮ること | | | `intervention` | ストップ・ザ・ワールド(旧廃止方式) |
| 介入トリガー | 人間の判断を仰ぐ5条件(重大判断/曖昧さ/行き詰まり/方針分岐/前提崩れ) | | | `trigger` | — |
| 運用状態 | `.orchestrator/` に置く `plan.json` / `control.json` / `state.json` と追記型ログ。機械が読み書きし、人間は直接編集しない | | | `.orchestrator/` | — |
| ORCHESTRATOR.md | リポジトリルートに置く任意のプロジェクト固有方針(コミット対象。運用状態とは別) | | | `ORCHESTRATOR.md` | — |

## 判断に迷いやすい区別

| A | B | 何が違うか |
|---|---|---|
| docker-proxy | forward プロキシ(socat) | 前者は Docker API を検査・制限する共有プロキシ。後者は Web アプリのポートを中継する使い捨てコンテナ |
| DooD(既定) | VM モード | DooD はホストの Docker デーモンを proxy 経由で使う軽量既定。VM モードは VM 内ネイティブ Docker(bind/compose/privileged 可)でオプトイン |
| ブレインストーミングモード | 実行モード | 前者は人間主導・同期・自動化しない検討。後者は自律・並列の実装。境界は仕様ドキュメント |
| 仕様(`docs/`) | 運用状態(`.orchestrator/`) | 固まった仕様は `docs/` に、進捗・仮定・plan 等の運用状態は `.orchestrator/` に置く |
| Codex サンドボックス | Claude コンテナの隔離 | 前者は codex がコンテナ内で自前に張る隔離(既定は無効化。読み取り専用を要求する呼び出しのためだけに landlock を残す)。後者はコンテナ/ホスト間の隔離境界(唯一の境界であり緩めない) |
| Codex CLI の同梱 | 異種ベンダー worker の常用 | 前者は開発者がコンテナ内で codex を使える状態にすること(決定済み)。後者はオーケストレーターが worker/レビューアーとして codex を常用すること(未決) |
