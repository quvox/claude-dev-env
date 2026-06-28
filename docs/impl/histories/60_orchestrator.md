# 変更履歴: 60_orchestrator.md

> 対応文書: `docs/impl/60_orchestrator.md`

## 2026-06-29（可観測性・中断の再開可能化・完了検証・Config B 廃止／設計↔実装の総点検）
- 背景：実機運用で「ずっと待機中に見える／`[d]` で何も出ない／`[q]` で worker が消えて復元不能」となり使い物にならなかった。原因はダッシュボード設計と中断セマンティクスの不備。併せて設計↔実装の不整合と未実装機能を総点検した。
- ダッシュボード（`dashboard.go`）：タスクが running になった時点で `syncDashboard` を呼ぶよう変更し、状態ラベル（待機中/実行中/…）・経過時間・試行回数を表示。`syncDashboard` は running の開始時刻を引き継いで経過時間が伸びるようにした。`[d]` を no-op から「実行中 worker のログ末尾をライブ表示するトグル」に実装（`renderDetail`/`tailFile`）。`NewDashboard` は `Store` を受け取る。
- 中断の再開可能化（`controller.go`）：`[q]`（KeyQuit）を `PhaseDone` 遷移から **`errSuspended` 返却**へ変更。状態を `executing` のまま保存して終了し、次回起動で中断点から再開する（破壊的でない）。`Run` は `errSuspended` をクリーン終了として扱う。
- worker 出力のストリーミング（`worker.go`）：`--output-format json`→**`stream-json --verbose`** に変更し、`io.MultiWriter` でログへライブ tee。これで `[d]` が進捗をリアルタイム表示できる。`ParseWorkerResult` を stream-json（result イベントの `result` 抽出）・単一 envelope・bare の 3 形態対応に刷新（`worker_stream_test.go` で実出力サンプルを含め検証）。
- 完了検証（`controller.go`）：`verifyCompletion` に **助言的な自然言語完了検証** `checkCompletion`/`buildCompletionPrompt`/`parseCompletionVerdict` を実装。`plan.completion` を `claude -p` で検証し未充足の可能性を Slack 通知に添える。ブロックしない（エラー/解析不能は満たした扱い）。`completion` フィールドが収集されるだけで未使用だったギャップを解消。
- Config B 廃止：`--workers-window` フラグを `main.go`・`claude-dev` から削除。worker 可観測性は `[d]` ライブ表示に一本化（ドキュメントにあるのに動かない罠を除去）。
- ドキュメント総点検：設計 `06_orchestration.md`（§4.5 主要な統合点を追加：指示テンプレート・`ORCHESTRATOR.md`・handoff の続ける/実行/終了・config キー・完了検証／§5.2・5.3 のキー意味と Config B 廃止）と実装仕様 `60_orchestrator.md`（ダッシュボードキー・worker `stream-json`・完了検証・`blocked` の終端性・`reviewer_vendor` は v1 未使用・**実装状況（v1）節を新設**）を実装に一致させ、設計↔実装の不整合（[d] no-op vs 実機、continue_wallbounce 未記載、config/ORCHESTRATOR.md/intervene.md の設計未言及 等）を解消。`reviewer_vendor: codex`・Slack 双方向・Docker Agent・不足分の自動タスク化は明示的に「未実装（将来フェーズ）」と記載。
- 検証：`go build`/`go vet`/`go test ./...` 全 pass。stream-json 解析・完了検証解析の単体テスト追加。配布イメージ再ビルド済み。

## 2026-06-29（claude 実行ファイルの解決：非対話 PATH 問題）
- 不具合：`claude-dev orchestrate` は tmux ウィンドウの非対話シェル（`zsh -c`）でオーケストレーターを起動するが、`claude` のネイティブ導入先 `~/.local/bin` は対話シェルの `.zshrc` でしか PATH に追加されないため、その PATH には `claude` が無い。素朴な `exec.Command("claude", …)` が「executable file not found」で失敗し、壁打ち・介入・worker・レビュアのすべてが起動できなかった（実機の tmux ウィンドウで `claude NOT FOUND` を確認。旧 run の `audit.jsonl` にも `wallbounce_exit`＋"executable file not found" が残っていた）。
- 修正：新規 `claudebin.go` を追加。`claudePath()`（`exec.LookPath`→無ければ `$HOME/.local/bin/claude` フォールバック）で絶対パス解決し、`claudeChildEnv()`（`SLACK_BOT_TOKEN` 除去＋claude bin ディレクトリを PATH 補完）を子プロセス環境に使う。`mode.go`（対話）と `worker.go`（worker/レビュア）の両方を `exec.Command("claude", …)`→`exec.Command(claudePath(), …)` に変更。
- 検証（実機 claude・コンテナ）：tmux 相当の制限 PATH（`~/.local/bin` 無し）で `claude NOT on PATH` の状態でも、worker が `PROBE.md`/`SHIP.md` を作成・コミットし作業ブランチへマージ（`dispatch→[review_result→]task_done→completed→run_done`）。対話壁打ち `claude` も TUI（フォルダ信頼プロンプト）まで起動することを確認。`make build-claude-vnc` で再ビルドした**配布イメージの `/usr/local/bin/claude-orchestrator`** でも同結果を確認。
- 関連文書：`docs/impl/60_orchestrator.md`（モード切替節の注記・ファイルツリー）。レビュー追記を `docs/reviews/2026-06-28_orchestrator-tty-fix.md`。

## 2026-06-28（状態ライフサイクル・worker 権限・worktree 堅牢化）
- 不具合1（即終了）：完了済み run が `state.json` に Phase=`done` を残すため、次回 `orchestrate` 起動が run loop の `done` 分岐で即 return し「すぐ終了」していた。
- 不具合2（壁打ち飛ばし）：古い Phase=`executing` 状態が残ると無言で実行モードへ再開し、壁打ちを飛ばして操作不能に見えていた。
- 不具合3（worker が無言で何もしない）：worker の `claude -p` に `--permission-mode` を渡しておらず、ヘッドレスでは全 Write/Bash が権限拒否されていた（実機 `claude -p` で `permission_denials` を確認）。コンテナの `settings.json`（`bypassPermissions`）に暗黙依存しており、設定が無い環境では実装が一切進まない。
- 不具合4（worktree 再作成失敗）：worktree ディレクトリのみ消えてブランチ `orch/<id>` が残ると `git worktree add -b` が「branch already exists」で失敗し、再試行→介入ループに陥っていた。
- 修正：
  - `main.go`：`isResumable`（Phase=executing/intervening のみ再開）を追加。done/不在/未知は壁打ちから新規開始。`--fresh` フラグで中断 run も強制新規化。再開/新規を標準出力に明示。
  - `state.go`：`Store.ResetRun()`（state/plan/control・open_intervention を削除。append-only ログは保持）。
  - `worker.go`：`Worker.PrepareWorktree` を「ディレクトリ既存→再利用／ブランチのみ残存→`WorktreeAddExisting` で再接続／無→`add -b`」に分岐。`CleanOrchWorktrees`（--fresh 時に worktree と `orch/*` ブランチを撤去）。`ExecClaude.PermissionMode` を追加し `--permission-mode` を明示送出。`GitRunner` に `BranchExists`/`WorktreeAddExisting` を追加。
  - `config.go`：`worker_permission_mode`（既定 `bypassPermissions`）を追加。
  - `claude-dev`：`orchestrate` に `--fresh` を受け渡し（→ 10_cli.md / 04_cli-reference.md）。
- 検証（実機 claude）：(a) `--permission-mode bypassPermissions` 付きで実機 worker が FROM_WORKER.md を作成・コミット（`permission_denials:[]`）。(b) Phase=executing を種に実機オーケストレーターを起動し、`dispatch→worker_result→task_done→completed→run_done` で実機 worker＋実機レビュア＋実 git マージが作業ブランチへ統合されることを 30 秒で確認。(c) done 残置→新規 run、`--fresh`→executing 上書き新規、再開メッセージを確認。`go test ./...` 全 pass。
- 関連文書：`docs/impl/60_orchestrator.md`（再開節・worker §3/§1・config 表/例・ファイルツリー）、`docs/impl/10_cli.md`、`docs/04_cli-reference.md`。レビュー追記を `docs/reviews/2026-06-28_orchestrator-tty-fix.md`。

## 2026-06-28（端末モード不具合の修正）
- 不具合：壁打ち/介入の対話 `claude`（全画面 TUI）が共有 TTY を非カノニカル（raw）モードのまま残して終了するため、コントローラ復帰後の行バッファ読み取りが永久ブロックしていた。結果として (a) ダッシュボードのキー入力 `d`/`p`/`q` が反応しない、(b) `control.json` 不在時の `terminalConfirm` 確認入力が受け付けられず実行フェーズへ遷移できず worker が全く進まない、という症状が出ていた（raw モードでは Enter が `\n` ではなく `\r` を送り、`ReadString('\n')` が `\n` を待ち続けるため）。
- 修正：端末モードをコントローラが自前で所有する方針を追加。
  - 新規 `term.go`：`rawKeyMode()`（`stty -icanon -echo min 0 time 1`）と `ttyRestoreSane()`（`stty sane`）を `stty` 呼び出しのみで実装（外部 Go モジュールを増やさず stdlib のみ方針を維持）。
  - `mode.go` `RunInteractive`：対話 `claude` 終了直後に `ttyRestoreSane()` を呼び、カノニカル状態へ復元（`terminalConfirm` と次のダッシュボードが正しく動く）。
  - `dashboard.go` `readKeys`：行バッファ読み（`bufio` + `ReadString('\n')`）を廃し、`rawKeyMode()` で TTY を自前設定して 1 バイトずつ読む（Enter 不要・即時反応）。`VMIN=0/VTIME=1` で無入力時は約 0.1 秒ごとに `(0, io.EOF)` が返るため `ctx` キャンセルを取りこぼさず、stdin にブロックし続ける goroutine も残さない。終了時に復元。
  - `main.go`：経路によらず端末を健全状態へ戻す `defer ttyRestoreSane()` を追加。
- 検証：pty 上で実機の対話 `claude` が終了後も `ICANON=False` を残すことを確認。再現テスト（fake `claude` で同条件を再現）で、修正前は `q` を押しても終了しない／確認入力が通らないことを再現し、修正後はキー即時反応（`q` で 0.2 秒以内に終了）・確認入力受理→`executing`→`dispatch`→`task_done`→`completed`→`done` まで通ることを確認。既存単体テストは全て pass。
- 関連文書：`docs/impl/60_orchestrator.md`（モード切替・ダッシュボード節、ファイルツリー）を更新。レビューを `docs/reviews/2026-06-28_orchestrator-tty-fix.md` に記録。

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
