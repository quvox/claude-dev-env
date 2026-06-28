# 変更履歴: 60_orchestrator.md

> 対応文書: `docs/impl/60_orchestrator.md`

## 2026-06-28
- 新規作成。設計文書 `docs/06_orchestration.md` に基づき、AI オーケストレーター（Go 製コントローラ）の実装仕様を起こした（コード着手前の仕様。実装の正本となる）。
- 既存 `docker-proxy/` の Go 規約に倣って構成を定義：module `github.com/quvox/claude-dev-env/orchestrator`（go 1.22）、`golang:1.24-alpine` でのマルチステージビルド。独立コンテナではなく claude イメージへ `claude-orchestrator` として焼き込み、プロジェクトコンテナ内で実行する方針を明記。
- 主要構成を確定：
  - 状態ストア `/workspace/.orchestrator/`（state/plan/control/summary/assumptions/interventions/audit/worktrees）のファイル構成とスキーマ。
  - 状態機械（wallbounce/executing/intervening/done）と run loop。
  - モード切替の実装（対話 `claude` を子プロセスで exec し TTY 共有・終了までブロック／実行はダッシュボード描画）。
  - 壁打ち↔実行↔介入の handoff を `control.json` のファイル受け渡しで実現。
  - worker ディスパッチ（`claude -p`＋git worktree＋構造化出力 `WorkerResult`）、品質ゲート（別 worker レビューの改訂ループ）、トリガー判定、Slack 通知（コントローラ一本化）、設定、並行性・再開・エラー処理、ビルド配置、CLI 連携契約、テスト方針。
- 06 §12 未決事項に対する本仕様での決定を表で明示（stuck_limit=3、状態ストア構成確定、計画実行ベース＋分岐点のみ適応、別アプローチは StuckLimit 到達前に試行、Slack は一方向、モデルは config 既定 sonnet）。レビューで変更しうる旨を併記。
- 実装着手時に更新する既存文書（10_cli.md / 40_devcontainer.md / 20_makefile.md / 04_cli-reference.md）を明記。本書作成時点ではコード未着手のため未更新。
- レビュー反映：`max_workers` の既定を 2 → **5** に変更。設定のマージ優先順位（組み込み既定 → `~/.config/claude-dev.yaml` の `orchestrator:` → プロジェクト `/workspace/.orchestrator/config.yaml`）と YAML 例を追記。
- 「頭脳の所在（Claude か Go か）」節を追加。推論・判断はすべて Claude（壁打ち脳＝対話 claude、worker 脳＝claude -p、分岐点の適応判断）が担い、Go は決定論的な段取り（配管）に徹することを明記。
- 設計↔実装／実装内部の整合性確認（独立エージェントによる複数ラウンド検証、Round1=4本→Round4=1本、収束まで）に伴う修正:
  - 「試行回数とエスカレーション（Attempts / stuck_limit / max_review_rounds）」節を新設。1 試行(Attempt)・revise・trigger3 発火条件・別アプローチの定義を確定し、§品質ゲート・§worker・§介入トリガー・スキーマ各所をこれに統一（全エージェントが指摘した二重定義/曖昧を解消）。
  - worktree の取り込み主体を明確化：worker が worktree でコミット、controller が merge/rebase（`merge_strategy`）で統合（git は orchestrator ユーザ、worker bypass と独立）。
  - トリガー1（後戻り不可操作）の現実的検出を明記：worker には当該操作を行わせず `NeedsHuman` でエスカレーション、worker へ `SLACK_BOT_TOKEN` を渡さない、push/deploy は controller のみ。
  - `NeedsHuman.Options` は worker が提示する候補データで、controller が intervening 対話モードで select→submit 提示する旨を明記（06 §7 との見かけ矛盾を解消）。
  - 列挙値・遷移の明文化：`NeedsHuman.Reason`（critical_decision/ambiguity/policy_branch/prerequisite_broken、trigger1/2/4/5）、レビュー severity（critical/major/minor、重大=critical|major）、Task.Status の遷移、トリガー表各行への reason 値付与。
  - JSONL レコードのスキーマ（Assumption/Intervention/AuditEntry）を追加。
  - 状態機械の図を修正（intervening を独立状態として描き、解決後 executing へ復帰、abort は done）。run loop 段落4に resume/abort 分岐を追記。
  - control.json のライフサイクル（原子的書き込み・controller が消費後削除・再開時は plan.json を正本に残存を無視）を明記。再開時の running/review/revise タスクの扱いを具体化。
  - `completion` の評価（実装仕様ドキュメント由来の自然言語基準を最終検証）、continue_wallbounce の遷移、dashboard `[d]` ペインの扱い（実行モードのみ・対話 TUI 前に閉じる）を追記。
  - コード一覧に `instructions/`（wallbounce.md / intervene.md）を追加、Dockerfile に `go.sum` の COPY を追加、独立モジュール（go.work 不使用）を明記。
  - 用語ゆれの統一（config 値はすべて snake_case：max_workers/stuck_limit/max_review_rounds 等）、内部参照の見出し名を実在見出しに一致。
  - `max_workers` 既定を 5 に確定。

## 2026-06-28（実装）
- `orchestrator/` を Go（stdlib のみ・外部依存なし）で実装。go build/vet/test/`-race`/gofmt すべて緑。docker-proxy と同方式のマルチステージで `claude-orchestrator` を claude イメージへ焼き込み。
- 外部依存回避のため go.sum 前提を撤回し、config を自前フラット YAML パーサ（stdlib）で読む方針に確定（仕様の go.mod/Dockerfile 記述を更新）。
- 仕様↔実装の整合性確認（実コードと突き合わせる独立エージェント検証）で検出した差異を解消：
  - 【実装修正】実行モードを**真の並行実行**化（max_workers の goroutine プール、planMu/mergeMu、スナップショット実行、trigger 発火→ctx キャンセル→待機→intervening、複数発火は abort 優先・task ID 昇順）。
  - 【実装修正】トリガー1 が `blocked` を設定して介入後に再実行されないバグを修正。`Task.IrrevApproved` を追加し、承認後は pre-dispatch を再発火させない。仕様の Task スキーマに `IrrevApproved` を追記。
  - 【実装修正】revise の Dispatch エラーで trigger3 を取りこぼさないよう lastSevere を保持。
  - 【実装修正】`WorkerResult.Assumptions` を追加し controller が `assumptions.jsonl` へ追記。仕様の WorkerResult スキーマに `assumptions` を追記。
  - 【仕様修正＝v1 スコープ確定】完了判定は「全タスク done を完了」に確定。`completion` の `claude -p` 自然言語検証＋未充足時の再計画は将来拡張点として明記（v1 未実装）。
  - 【仕様修正】ダッシュボード `[d]` は tmux/CLI レイヤの affordance（バイナリ内 no-op）と明記。worker・対話 claude いずれにも `SLACK_BOT_TOKEN` を渡さない旨に統一。`controller_test.go` をテスト一覧へ追記。並行性節を実装（排他制御・merge 直列化・ctx キャンセル）に一致させた。
- 動作確認：スタブ `claude` と実 git を用いたエンドツーエンドのスモーク（executing → 2 タスクを依存順で実行 → review → worktree merge → assumptions 記録 → Phase=done）が exit 0 で成功。

## 2026-06-28（判断基準の明文化）
- オーケストレーターの判断基準を CLAUDE.md ではなく instruction テンプレート等に明文化：
  - `orchestrator/instructions/wallbounce.md`：介入トリガー 5 条件・「軽微判断は最も妥当な仮定を置いて進め記録」・状況サマリ定型を追記。
  - `orchestrator/instructions/intervene.md`：トリガー種別ごとの解き方を追記。
  - `worker.go` の `workerResultGuide`：仮定 vs エスカレーションの判断ルールと `assumptions` フィールドを追記（WorkerResult.Assumptions と整合）。
- 仕様 §instruction 注入に「判断基準の所在（CLAUDE.md に置かない理由を含む）」節を追加。共通＝instructions/*.md・worker guide、定量＝config、プロジェクト固有＝ルートの `ORCHESTRATOR.md`（任意）と整理。
- プロジェクト固有 policy ローダを実装：`state.go` の `LoadProjectPolicy(workspace)` が `<workspace>/ORCHESTRATOR.md`（任意・コミット対象。`.orchestrator/` 運用状態とは別）を読み、存在すれば見出し付きで返す（無ければ no-op）。mode.go（壁打ち/介入の `--append-system-prompt`）・worker.go（`BuildPrompt`）・review.go（`buildReviewPrompt`）の各プロンプト先頭に prepend。`policy_test.go` で present/absent/empty と各プロンプトへの反映を検証。build/vet/test/`-race`/gofmt 緑。
- 開発方法論（上流→下流の開発フロー、各段階の整合性確認、ユースケースに基づく動作確認、レビュー〔4 観点〕結果を `docs/reviews/` に残す）を、オーケストレーターの判断基準として `orchestrator/instructions/wallbounce.md` に追記（CLAUDE.md の「開発フロー／動作確認／レビュー」と整合）。仕様 §instruction 注入の「判断基準の所在」にも反映。
