---
id: decisions
layer: request
title: claude-dev-env 決定台帳
version: 1.2.0
updated: 2026-07-19
verified:
  at: 2026-07-19
  version: 1.2.0
  against: []
summary: >
  既存実装に埋め込まれた設計判断を「決定/委任/要確認」に仕分けた台帳。逆生成のため証跡は
  既存コード・旧docsを指す（人間は00層の承認ゲートで本台帳を追認する）。決定19・委任2・要確認3。
keywords: [決定台帳, 隔離方針, docker-proxy, オーケストレーター, VMモード, 委任]
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
| D-11 | イメージ配布 | GitHub Actions で GHCR へマルチアーキ・日次・タイムスタンプタグで push | チーム全員が同一構成を pull で使える | 旧10_ghcr-images, `.github/workflows/ghcr-images.yml` |
| D-12 | オーケストレーションの実装方式 | 自作の**外部制御ループ**（コントローラがループを所有）。Docker Agent／Stop-hook 力技は当面不採用 | 暴走しない・コンテキストを汚さない・再開可能。L1推論ループは `claude -p`／対話Claudeから借りる | 旧06_orchestration §3 |
| D-13 | オーケストレーターの2モード | 「1実体・2モード」。ブレインストーミング（人間×対話Claude、自動化しない）と実行（自律・並列）。境界は実装仕様ドキュメント | 人間の価値が宿る検討は自動化せず、実装〜整合性確認を自動化する | 旧06_orchestration §2 |
| D-14 | コントローラの常駐方式 | tmux 常駐（`orch-<project>-main` セッション内の `dashboard` ウィンドウで常駐）。各 worker/ブレインストーミングは同セッションの独立ウィンドウ | クライアント破壊でも tmux サーバがセッションを保持→再attachで復旧。完全デーモン化より単純 | 旧06_orchestration §4.1/§5.9 |
| D-15 | 介入はタスク単位 | 要判断はタスク1件のみ `waiting_human` にし、他 worker は止めない。独立最上位状態 `intervening` は廃止 | 旧ストップ・ザ・ワールド方式は1件の判断が全workerを巻き込み大量やり直しを生む | 旧06_orchestration §2.2/§6.2 |
| D-16 | 状態の保全 | 起動時の自動処理で plan/状態/履歴を削除しない。片付けは全タスク done か `--fresh` 時のみ、その場合も `history/<run_id>/` へ退避。実削除は利用者の明示 `rm` だけ | 中断・再開でのやり直しを構造的に排除する（人間の巡回負荷削減が本ツールの価値） | 旧06_orchestration §4.3 |
| D-17 | ダッシュボード UI | bubbletea/lipgloss のイベント駆動 TUI（カーソル選択→Enter で移動）。全消去・全再描画方式と数字キー即移動は廃止。この UI に限り外部依存を許容（vendoring） | ちらつき・強制移動を排し、選択と確定を分離する。Go の「標準ライブラリのみ」方針を本UIだけ変更 | 旧06_orchestration §5.3 |
| D-18 | 品質ゲート（レビュー） | 実装 worker と別 worker（できれば別ベンダー）による独立レビュー。採点は当該タスクの `completion` のみ（プランゴールで採点しない）。レビュー結果は構造化出力（スキーマ強制）で返す。同一フォーマットエラー2回で打切り介入へ | 旧 MODIFICATION の誤採点・パース失敗・試行浪費を構造的に是正 | 旧MODIFICATION, 06_orchestration §8, `orchestrator/review*` |
| D-24 | 複数プロジェクト同時実行時の compose リソース分離とライフサイクル | ①**分離**: DooD 既定モードで各プロジェクトのコンテナ内 `docker compose` が作るネットワーク名・コンテナ名をプロジェクト間で衝突させない。`COMPOSE_PROJECT_NAME` を起動ディレクトリ名で一意化する。`claude-dev-net`（claude↔proxy）は共有のまま分離しない。②**ライフサイクル**: compose で作られたコンテナ群は親 claude コンテナに束ね、`claude-dev stop` 時にラベル `com.docker.compose.project=<正規化NAME>` を持つコンテナと当該プロジェクトの compose デフォルトネットワークを削除する（`docker compose down` 相当。名前付きボリュームは非破壊のため保持）。共有の `claude-dev-net`・docker-proxy は削除しない。VM モードは compose がゲスト内 Docker で完結するため本片付けの対象外 | 全プロジェクトが `/workspace` にマウントされ compose 既定名が `workspace` に衝突するため。分離は compose 層で十分（利用者確認済み）。claude-dev-net の分離は単一共有 proxy 前提と両立しないため見送り。stop 後に compose コンテナが孤児として残り続けるのを防ぐ一方、ボリューム削除は破壊的なため行わず、共有リソースは他プロジェクトが使用中のため残す | 本変更, `claude-dev`/`claude-dev-mac`（`-e COMPOSE_PROJECT_NAME`／`stop`） |

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
| D-22 | 異種ベンダー worker（Codex 等）の常用可否 | 現状 worker は主に Claude。別ベンダー常用に踏み込むかは未決 | 品質ゲート定着後に人間が判断 |
| D-23 | MCP ツールの本格導入 | stdio 方式から段階導入する方針。Docker MCP（DinD/ソケット共有）はセキュリティ要件を満たせる場合のみ | 必要が生じた段階で人間が判断 |
