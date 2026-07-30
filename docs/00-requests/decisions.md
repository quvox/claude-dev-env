---
id: decisions
layer: request
title: claude-dev-env 決定台帳
version: 1.5.0
updated: 2026-07-30
verified:
  at: 2026-07-29
  version: 1.4.0
  against: []
summary: >
  既存実装に埋め込まれた設計判断を「決定/委任/要確認」に仕分けた台帳。逆生成のため証跡は
  既存コード・旧docsを指す（人間は00層の承認ゲートで本台帳を追認する）。決定22・委任2・要確認3。
keywords: [決定台帳, 隔離方針, docker-proxy, オーケストレーター, VMモード, 委任, ClaudeCodeバージョン, CodexCLI]
source: null
---

# 決定台帳:claude-dev-env

> 本台帳はブラウンフィールド逆生成により、既存実装・旧docs に埋め込まれた判断を明文化したもの。
> 証跡列は上流セッションの生ログではなく「その判断が具現化している既存資産」を指す。
> **人間は本パッケージの承認（人間ゲート①）をもってこれらを追認する。**

## 決定事項

<!-- 人間が決めたこと。下流はこのとおりに作る -->

| ID | 判断項目 | 決定内容 | 理由・背景 | 証跡 |
|---|---|---|---|---|
| D-1 | エージェント隔離モデル | 単一コンテナ同居型。root/worker は同一コンテナ・同一FSを共有し、個別隔離しない。隔離境界はコンテナ／ホスト間のみ | 信頼できる社内開発用途に限定する割り切り。個別隔離は実装・運用コストが高い | 旧00_idea-2 §3/§7, 実装（1プロジェクト=1コンテナ） |
| D-2 | Docker アクセス方式 | 生ソケットをマウントせず、Go製 `docker-proxy` 経由で制限付き Docker API を使う。ホストバインドマウント（`/workspace` 配下を除く）・privileged・host ネットワーク/PID 等を拒否 | 生ソケット共有はホスト掌握リスク。既定で危険操作を遮断する | 旧02_architecture/03_security, `docker-proxy/` |
| D-3 | 認証共有方式 | 認証ファイル（`.credentials.json`/`.claude.json`）のみコンテナ間共有。symlink を使わず「コピー＋30秒ごとのバックグラウンド同期」 | Claude Code のアトミック書き込み（tmp→rename）で symlink が壊れるため。セッション/設定はコンテナ固有に保つ | 旧02_architecture §認証, entrypoint |
| D-4 | SSH 鍵の扱い | 秘密鍵ファイルはマウントしない。プロジェクト直下 `.claude-dev.yaml` の `ssh_keys` だけで指定し、プロジェクト専用 ssh-agent のソケット（mac は socat TCP ブリッジ）のみ転送 | 鍵ファイルの露出を避けつつ、ディレクトリごとに異なる鍵を使えるようにする | 旧01_getting-started, `claude-dev` |
| D-5 | ネットワーク下り制御 | コンテナ内で iptables ファイアウォールを設定する | レビュー前コードの外部通信を制御する | 旧03_security, `scripts/init-firewall-claude.sh` |
| D-6 | ブラウザ確認方式 | VNC ありイメージにコンテナ内 Chrome を統合し、chrome-devtools MCP（localhost 直結）で操作。noVNC はポート6080〜を動的割当 | 旧「共有Chromeコンテナ＋socat二段リレー」は競合・複雑。プロジェクト独立に | 旧02_architecture §ブラウザ操作, entrypoint |
| D-7 | ポート公開方針 | `start` 時はポートマッピングしない。`claude-dev forward` で socat プロキシコンテナを立て 8100〜を動的割当。クライアントは SSH ControlMaster `-O forward` | 不要なホスト公開を避け、必要時だけ最小公開する | 旧01/02, `claude-dev` |
| D-8 | KVM デバイスの受け渡し | 既定では `/dev/kvm` 等を渡さない。`--kvm` 指定時のみ device 渡し（無ければ警告しソフトエミュ） | 通常は Chrome 操作で足りる。過剰な特権付与を避ける | 旧02_architecture, entrypoint |
| D-9 | VM モード | 重い Docker 案件向けにオプトイン（`--vm`）。QEMU+virtiofs のゲストVMで**ネイティブDocker**を動かし、claude コンテナは privileged 化しない。`/workspace` は virtiofs で同一パス共有、Docker は `DOCKER_HOST` | bind/compose/privileged が要る案件と、軽量既定（DooD+proxy）を両立する | 旧08_vm-mode, `scripts/vm*` |
| D-10 | macOS 対応 | ホスト CLI を `claude-dev-mac` に差し替え（`make install` が OS 判定で symlink）。SSH agent は TCP ブリッジ、ポート直結、VM/KVM 非対応、arm64 ネイティブ | OS 依存をホスト CLI に閉じ、コンテナ資産は OS 非依存に保つ | 旧09_macos-support, `claude-dev-mac` |
| D-11 | イメージ配布 | GitHub Actions で GHCR へマルチアーキ・日次・タイムスタンプタグで push | チーム全員が同一構成を pull で使える | 旧10_ghcr-images, `.github/workflows/ghcr-images.yml`（同梱 Claude Code のバージョン方針は D-26） |
| D-12 | オーケストレーションの実装方式 | 自作の**外部制御ループ**（コントローラがループを所有）。Docker Agent／Stop-hook 力技は当面不採用 | 暴走しない・コンテキストを汚さない・再開可能。L1推論ループは `claude -p`／対話Claudeから借りる | 旧06_orchestration §3 |
| D-13 | オーケストレーターの2モード | 「1実体・2モード」。ブレインストーミング（人間×対話Claude、自動化しない）と実行（自律・並列）。境界は実装仕様ドキュメント | 人間の価値が宿る検討は自動化せず、実装〜整合性確認を自動化する | 旧06_orchestration §2 |
| D-14 | コントローラの常駐方式 | tmux 常駐（`orch-<project>-main` セッション内の `dashboard` ウィンドウで常駐）。各 worker/ブレインストーミングは同セッションの独立ウィンドウ | クライアント破壊でも tmux サーバがセッションを保持→再attachで復旧。完全デーモン化より単純 | 旧06_orchestration §4.1/§5.9 |
| D-15 | 介入はタスク単位 | 要判断はタスク1件のみ `waiting_human` にし、他 worker は止めない。独立最上位状態 `intervening` は廃止 | 旧ストップ・ザ・ワールド方式は1件の判断が全workerを巻き込み大量やり直しを生む | 旧06_orchestration §2.2/§6.2 |
| D-16 | 状態の保全 | 起動時の自動処理で plan/状態/履歴を削除しない。片付けは全タスク done か `--fresh` 時のみ、その場合も `history/<run_id>/` へ退避。実削除は利用者の明示 `rm` だけ | 中断・再開でのやり直しを構造的に排除する（人間の巡回負荷削減が本ツールの価値） | 旧06_orchestration §4.3 |
| D-17 | ダッシュボード UI | bubbletea/lipgloss のイベント駆動 TUI（カーソル選択→Enter で移動）。全消去・全再描画方式と数字キー即移動は廃止。この UI に限り外部依存を許容（vendoring） | ちらつき・強制移動を排し、選択と確定を分離する。Go の「標準ライブラリのみ」方針を本UIだけ変更 | 旧06_orchestration §5.3 |
| D-18 | 品質ゲート（レビュー） | 実装 worker と別 worker（できれば別ベンダー）による独立レビュー。採点は当該タスクの `completion` のみ（プランゴールで採点しない）。レビュー結果は構造化出力（スキーマ強制）で返す。同一フォーマットエラー2回で打切り介入へ | 旧 MODIFICATION の誤採点・パース失敗・試行浪費を構造的に是正 | 旧MODIFICATION, 06_orchestration §8, `orchestrator/review*` |
| D-24 | 複数プロジェクト同時実行時の compose リソース分離とライフサイクル | ①**分離**: DooD 既定モードで各プロジェクトのコンテナ内 `docker compose` が作るネットワーク名・コンテナ名をプロジェクト間で衝突させない。`COMPOSE_PROJECT_NAME` を起動ディレクトリ名で一意化する。`claude-dev-net`（claude↔proxy）は共有のまま分離しない。②**ライフサイクル**: compose で作られたコンテナ群は親 claude コンテナに束ね、`claude-dev stop` 時にラベル `com.docker.compose.project=<正規化NAME>` を持つコンテナと当該プロジェクトの compose デフォルトネットワークを削除する（`docker compose down` 相当。名前付きボリュームは非破壊のため保持）。共有の `claude-dev-net`・docker-proxy は削除しない。VM モードは compose がゲスト内 Docker で完結するため本片付けの対象外 | 全プロジェクトが `/workspace` にマウントされ compose 既定名が `workspace` に衝突するため。分離は compose 層で十分（利用者確認済み）。claude-dev-net の分離は単一共有 proxy 前提と両立しないため見送り。stop 後に compose コンテナが孤児として残り続けるのを防ぐ一方、ボリューム削除は破壊的なため行わず、共有リソースは他プロジェクトが使用中のため残す | 本変更, `claude-dev`/`claude-dev-mac`（`-e COMPOSE_PROJECT_NAME`／`stop`） |
| D-25 | コンテナ内動作の判定マーカー（`container` 環境変数） | 全 claude コンテナに環境変数 `container=docker` を持たせ、コンテナ内で動作するプロセスが「自分がコンテナ内か」を判定できるようにする。名前・値は systemd/podman の標準慣習（`container=<runtime>`）に合わせ `container=docker` とする。イメージ焼き込み（`Dockerfile.claude` の base ステージの `ENV`）で付与し、VNC 版も `FROM base` 継承で同値を持つ。起動経路（`docker run`／login 等の一時コンテナ含む）に依存させないためイメージ側で常時保証する | 内部プロセス（entrypoint・各スクリプト・オーケストレーター等）が環境依存の分岐を安全にできるようにする恒久マーカーが要る。名前・値を既存の業界標準慣習に合わせることで、systemd 等の外部ツールとの互換も同時に得られる。起動時 `-e` 付与は経路依存で漏れうるためイメージ側に置く | 本変更, `.devcontainer/Dockerfile.claude` |
| D-26 | 同梱する Claude Code のバージョン方針と、そのキャッシュキーの置き場所 | ①**チャネル**: 配布イメージに焼く Claude Code は `https://downloads.claude.ai/claude-code-releases/latest` を CI の prepare ジョブで具体バージョン（例 `2.1.220`）へ解決し、build-arg として**ピン留めして**インストールする。`install.sh` の引数なし既定（`stable` チャネル）は使わない。②**逃げ道**: 不良版を引いた場合は `workflow_dispatch` の入力で特定バージョンを手動指定して焼き直せるようにする（`install.sh` は `stable｜latest｜具体バージョン` を受け付ける）。③**キャッシュキー**: バージョン文字列そのものをキャッシュキーとし、時刻由来の cache-bust（`CLAUDE_CACHE_BUST`）は廃止する。新版が出た日だけ当該レイヤーが失効し、出ない日は完全にキャッシュヒットする。④**日次更新の意味**: 「日次で更新」の保証はタグが変わることではなく、**同梱 Claude Code が `latest` に追随すること**を含む（要件9の受け入れ基準に反映） | 2026-07-18 の変更（バージョンを build-arg から `labels` へ移しレイヤーキャッシュを実効化）以降、レイヤーチェーンから日々変わる値が消え、claude 導入層が永久にキャッシュヒットするようになった。結果、ラベルだけが日次更新され**同梱版は 2026-07-19 時点の 2.1.214 で凍結**していた。`stable` は段階的公開のため現行 `latest` より古い版を指すことがあり（2026-07-29 観測: stable=2.1.212 / latest=2.1.220）、`stable` 追随ではむしろ現状より古い版を焼くことになる。`latest` ピン留めならホスト側 claude（`latest` 追随）と版が揃い、認証共有時にホスト/イメージ間のバージョン差が問題になりにくい（D-3 の `--update=none` 方針と整合）。時刻由来ではなく内容由来のキーにすることで、キャッシュの実効性（pull を増分に保つ）と鮮度を両立できる | 本変更, `.github/workflows/ghcr-images.yml`, `.devcontainer/Dockerfile.claude` |
| D-27 | Codex CLI の同梱・バージョン方針・認証共有方式 | ①**同梱**: 配布 2 イメージ（`claude-cli`/`claude-vnc`）に OpenAI Codex CLI（npm パッケージ `@openai/codex`）を導入する。導入 `RUN` は Claude Code と同じ**配布ステージの終端レイヤー**に置く。②**バージョン**: CI の prepare ジョブで npm registry の最新版を具体バージョン（例 `0.146.0`）へ解決し、build-arg でピン留めしてインストールする。`@latest` の直書きはしない。`workflow_dispatch` の入力で特定バージョンを手動指定して焼き直せるようにする。③**認証**: `codex login --device-auth`（ヘッドレス前提のデバイス認証）を採り、`$CODEX_HOME/auth.json`（既定 `~/.codex/auth.json`）**のみ**を既存 `claude-dev-auth` ボリュームの `codex/` サブディレクトリ経由でコンテナ間・ホスト間共有する。共有方式は D-3 と同じ「起動時コピー＋30 秒ごとのバックグラウンド書き戻し」。`config.toml`・セッション/履歴はコンテナ固有に保つ。④**ログイン導線**: ホスト CLI に独立サブコマンド `claude-dev login-codex` を追加する（既存 `login` は claude 専用のまま。`logout` は共有ボリュームを空にする現状挙動を維持し、codex 認証も同時に消える）。⑤**スコープ**: 本決定は「開発者がコンテナ内で codex を使える状態」までであり、オーケストレーターの worker/レビューアーとして codex を常用するかは D-22 のまま未決 | codex も claude 同様に更新が速く、`@latest` を直書きすると文字列が変化せずレイヤーキャッシュが永久ヒットして**中身だけ凍結**する（D-26 で実際に発生した事象）。内容由来キーを終端レイヤーに置く方針をそのまま横展開すれば、鮮度と `docker pull` の増分性を両立できる。npm パッケージは platform 別バイナリを optionalDependencies で取得し linux-arm64 も提供されるため、マルチアーキ配布（D-11）と両立する。`auth.json` は保存方式の既定が keyring ではなくファイル・パーミッション 0600・その場書き換えで、トークンリフレッシュにより内容が変わるため書き戻し同期が必要。認証の器を既存ボリュームへ相乗りさせるのは、インフラ作成・`logout`・`reset` の分岐を増やさないため。ログインは対象ごとに独立コマンドとし、既存 `login` の挙動を変えずに片方だけログインし直せるようにする | 本変更, `.devcontainer/Dockerfile.claude`, `scripts/entrypoint-claude.sh`, `claude-dev`/`claude-dev-mac`, `.github/workflows/ghcr-images.yml` |

## AIへの委任

<!-- 下流AIの裁量に任せること。範囲と制約を必ず書く -->

| ID | 判断項目 | 委任範囲 | 制約・ガードレール | 証跡 |
|---|---|---|---|---|
| D-19 | 03-impl 記述の粒度と実コードとの対応づけ | 各モジュールの 03-impl でどこまで詳細を書くか、コードのどの範囲を1ファイルに束ねるか | 02-design の分割定義（12モジュール）を逸脱しない。同じコードを複数の03-implに重複させない。データ構造・IF・ロジックの意図を書き、行単位コードは書かない | 本移行タスク |
| D-20 | 逆生成時の軽微な曖昧さの穴埋め | 旧docsとコードで表現が食い違う軽微点は、**コードを正**として記述する | 要件・契約・振る舞いに関わる食い違いは委任範囲外＝停止して人間に確認（要確認へ）。穴埋めした点は feedback/log.md に記録 | 本移行タスク |

## 要確認(未決)

<!-- 意図的に残す未決事項。下流はここで停止して聞く -->

| ID | 判断項目 | 論点 | 誰が・いつまでに決めるか |
|---|---|---|---|
| D-21 | オーケストレーターのモデル/effort ポリシーの将来調整 | 工程別のモデル選択（設計系=opus/high、実装系=sonnet/high）は 2026-07 時点の方針。基準見直し時は要合意 | 運用実測を見て人間が随時 |
| D-22 | 異種ベンダー worker（Codex 等）の常用可否 | 現状 worker は主に Claude。別ベンダー常用に踏み込むかは未決。**Codex CLI の同梱と認証共有は D-27 で決定済み**であり、ここで未決なのはオーケストレーターが worker/レビューアーとして codex を常用するかどうかのみ | 品質ゲート定着後に人間が判断 |
| D-23 | MCP ツールの本格導入 | stdio 方式から段階導入する方針。Docker MCP（DinD/ソケット共有）はセキュリティ要件を満たせる場合のみ | 必要が生じた段階で人間が判断 |
