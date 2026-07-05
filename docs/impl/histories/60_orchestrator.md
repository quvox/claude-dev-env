# 変更履歴: 60_orchestrator.md

> 対応文書: `docs/impl/60_orchestrator.md`

## 2026-07-05（「続ける」＝対話に直接戻す／ブレインストーミングホームの階段状崩れ修正）
- 背景：人間から「『1.続ける』を選んで Enter しても brainstorming ウィンドウに移動しない（ホームに戻され再選択が要る）／そもそも窓が無いように見える」との指摘。クリーン再現では「続ける」で brainstorming 窓は復活していた（`done` で消えていたのは別要因）が、(a) ホーム画面の下部ヒント行が右へ階段状にずれる描画バグ、(b)「続ける＝対話に戻る」という期待と実挙動（ホームで再選択）が不一致、の2点が真の問題だった。
- 着地の分岐（`controller.go`）：`runBrainstormingSession(ctx, enterConversation)` に着地フラグを追加。初回起動は `false`＝`SwitchTo(DashboardWindow)`（ホーム＝カーソル選択式）、`continue`／実行不可差し戻しは `true`＝`SwitchTo(BrainstormingWindow)`（対話へ直接戻す）。`runBrainstorming` を**内部ループ**化し、continue/実行不可のたびに `enterConversation=true` で再入場、`execute`（実行可）/`abort`/`done` でのみ遷移する（従来は `return nil` で外側ループへ戻していた）。
- 階段状崩れ修正（`dashtui.go` View ブレインストーミング分岐）：ヒント行を `lipgloss.Render("…\n")` と改行込みで描いていたのを、**改行を `Render` の外**（`WriteByte('\n')`）に出して各行のテキストだけをスタイルする形へ。styled セグメントに `\n` が入ると bubbletea の行差分が崩れ後続行が右へずれるため。
- 検証：`go build`/`go test ./...` pass。実機（hisol-work）でクリーン起動→ホーム描画が全行 col0（崩れ無し）、`/exit` 相当→確認メニュー正常（❯1.続ける/2.終了）、`1`（続ける）→**brainstorming 窓が active**（対話へ直接復帰・claude 稼働）を確認。配布イメージ再ビルド。
- 設計同期：`06_orchestration.md`（§4.5「1.続ける」＝対話に戻る＝`select-window`、§5.1/§8 の起動フローを「カーソル選択→Enter・以後の続けるは対話へ直接戻る」に更新、旧 `Ctrl-b w` 記述を除去）、`60_orchestrator.md`（ブレインストーミング着地の分岐・内部ループ・`printBrainstormingHome` 廃止＝bubbletea View 化を反映）。

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

## 2026-06-29（実機検証で判明した構造的不具合の是正：実装仕様改訂）
- 実機運用で判明した不具合（介入で全 worker 停止／中断後のやり直し／レビュー誤採点・パース失敗）を是正する設計を実装仕様へ反映（実装は「実装状況」の「設計確定・実装待ち」）。
- スキーマ：State.Phase から `intervening` を削除（wallbounce/executing/done）。Task に `Completion`（必須・タスク固有完了基準）・`SessionID`（`--resume` 用）・`OpenInterventionID`・`ReviewFormatErrors` を追加。新ステータス `waiting_human`。介入キュー `intervention/open.json`（`OpenInterventions`/`OpenIntervention`）を導入し、単一 `open_intervention` サイドカー＋最上位 `intervening` 状態を廃止。control.json の intervention_id を任意化（複数解決時は answer.md 有無で再照合）。
- 制御フロー：状態機械図と run loop を改訂。トリガー発火は当該タスクのみ作用（全 worker を束ねる `runCtx` の `runCancel()` 廃止）、peer 継続、`[i]` オンデマンド介入対応、`waiting_human` が残る間は run を終了しない。
- worker ディスパッチ：`session_id` 捕捉と `--resume`（同一 Attempt 再開）／新 Attempt はセッション破棄、中間コミット方針を追記。
- 品質ゲート：タスク固有 `completion` のみで採点（フォールバック禁止）・構造化出力・フォーマット違反と内容不合格の分離（`review_format_error_limit`・`review_gate_defect`）・レビュー専用リトライ。
- 並行性・再開・エラー処理：トリガー発火＝タスク単位保留（peer 不停止）、再開で done を再実行しない正規化・`waiting_human` 保持・`--resume` 再開、Ctrl-C をクリーン中断化。
- 設定：`review_format_error_limit`（既定 2）・`worker_grace_seconds`（既定 10）を追加。
- CLI：自己検証用バイナリフラグ `--start-executing`（ready な seed plan で壁打ちを飛ばす検証専用 affordance）を明記。`--workspace`/`--instructions` を整理。
- 自己検証：[70_sample-project.md] / [docs/07_self-verification.md] への参照と、テスト方針へのシナリオ（peer 継続・done 再実行なし・waiting_human 保持・SessionID 再開・フォーマット違反で再実作業しない）を追加。

## 2026-07-01（実装：タスク単位介入・作業保全・品質ゲート是正・自己検証サンプル）
- 06/60 の設計改訂を Go 実装に反映。`go build`/`vet`/`test`（`-race` 含む）緑・gofmt 済み。
- 介入のタスク単位化：`recordFire`/全 worker `runCancel()`/最上位 `intervening` 状態/`open_intervention` サイドカーを廃止。`waiting_human` 状態＋`intervention/open.json` キュー（`state.go`）、`openInterventionLocked`/`resolveInterventions`（`controller.go`）、ダッシュボード `[i]`＋要判断件数（`dashboard.go`）。peer は継続。
- 作業保全：`Task.SessionID`/`ResumeSession` と `RunOpts`（`--session-id`/`--resume`）、`NormalizeForResume` が running/review/revise→pending＋resume フラグ・done/waiting_human は保持。Ctrl-C を `main.go` で `context.Canceled` はクリーン終了に、`runExecuting` の `ctx.Done()` を `errSuspended` 化。worker grace は `exec.Cmd.Cancel`(SIGINT)+`WaitDelay`（`worker_grace_seconds`）。中間コミット指示を `workerResultGuide` に追記。
- 品質ゲート：`Task.Completion` で採点（`review.go` buildReviewPrompt、プランゴールへのフォールバック廃止）、`RunGate` が `GateOutcome`（Passed/FormatError/LastSevere）を返し、フォーマット違反は worker 再ディスパッチせずレビューのみ再試行→`review_format_error_limit` 到達で `review_gate_defect` 介入。`runWallbounce` に `lintPlan`（completion 必須）。config に `review_format_error_limit`/`worker_grace_seconds`。
- 検証 affordance：`--start-executing`（`main.go`。ready な seed plan で壁打ちを飛ばす。ResetRun でシード plan を消さないよう分岐）。
- テスト：`controller_test.go` を per-task 介入モデルに更新（peer 継続・trigger1 waiting_human・resolve 承認）、`RunGate` の新シグネチャ、mock `RunPrompt(..., RunOpts)`。`policy_test.go` は `ResolveArgs` に更新。
- 自己検証サンプル：`examples/orch-sample/`（mathkit＋seed plan、t-announce/t-release を irreversible）、`scripts/orch-sample.sh`（冪等 scaffold）、Makefile `orch-sample`/`orch-sample-clean`、`build-orchestrator` を `-o orchestrator` 化。
- 未了：実 `claude -p` を用いた S1〜S5 の実機 E2E 検証（docs/07）。

## 2026-07-01（実機 E2E で発見した 2 件の不具合を修正）
- 自己検証サンプルに対する実機 E2E（docs/reviews/2026-07-01_orchestrator-e2e.md）で 2 件の不具合を発見・修正。単体テストは緑のまま。
- 相対 `--workspace` での worktree パス二重ネスト（git worktree add exit 128 → stuck）を修正：`main.go` で `filepath.Abs` 正規化。制御フロー節に手順 0 として追記。
- `ParseReviewResult` が stream-json を解釈できずレビュー全滅（→ review_gate_defect）だったのを修正：`ParseWorkerResult` と同型化（`resultFromStream`→envelope→bare、`findReviewResultJSON`）。§worker ディスパッチ 4 に追記。
- E2E で S1（peer 継続）・S2/S3（中断再開で done を再実行しない・SIGTERM クリーン中断）・S4（タスク固有 completion 採点）・S5（open.json 同時 4 件）・フォーマット違反時の worker 非再実行を実挙動で確認。結果は docs/reviews/2026-07-01_orchestrator-e2e.md。

## 2026-07-01（仕様↔実装 徹底整合性確認と是正）
- 5 領域の独立監査（状態/制御フロー/worker・review・trigger・config/mode・dashboard・main・slack/サンプル）を実施。
- 【実装バグ修正・高】`NormalizeForResume` が running/review/revise→pending 時に `ResumeSession` を立てておらず、ハードクラッシュ後の再開で SessionID があっても `--resume` されず白紙やり直しになる不具合を修正（SessionID 非空なら ResumeSession=true）。graceful 中断（[q]/Ctrl-C）は resetToPending が永続化するため元々問題なし。
- 【実装整理・低】`ResetRun` から廃止済みサイドカー `open_intervention` の削除対象を除去。`main.go` の doc コメント2箇所から廃止済み `intervening` を除去。
- 【仕様是正】§並行性の「トリガー発火＝タスク単位の保留」を実態に整合：トリガーは pre-dispatch か worker 完了後に評価されるため走行中 worker の個別 kill は不要（per-task 中断 context は持たない）。`worker_grace_seconds` は中断経路のみに適用、と明記。06 §6.2 も同旨に修正。
- 【仕様是正】トリガー表の条件4「計画上のマーク」・条件5「依存結果との矛盾検出」を v1 未実装（フェーズ2以降）と明記（実装は NeedsHuman 駆動のみ）。
- 【仕様補完】Task スキーマに `ResumeSession` を追記。
- 70：カバーするコードのツリーに実在ファイル（stats/strings/geometry.py スタブ・pytest.ini・.gitignore）を追加、「テストだけ」を「テストとスタブ」に修正。
- 再ビルド・`go test`（-race 含む）緑・gofmt 済み。

## 2026-07-03（VM モード対応）
- VM モード（CLAUDE_DEV_VM=1）時、`VMModePreamble()`（state.go）を壁打ち/介入 instruction と worker/reviewer プロンプト先頭に前置（発見導線2。ORCHESTRATOR.md 前置と同機構）。DOCKER_HOST はゲスト値を環境から継承（Go 側追加操作なし）。docs/impl/80_vm-mode.md 参照。

## 2026-07-04（実行モードダッシュボードに VM 資源逼迫バナー）
- `dashboard.go` の `render()` に、VM モード時のみ `vm-healthd` の health ファイル（`$HOME/.claude-dev-vm/health`、80 §7.2）を読む `readVMHealthBanner()` を追加。`STATE=WARN` かつ `TS` が新しい（既定120秒以内）ときだけ画面上部へ赤の警告バナーを出す。ファイル無し/非VM/鮮度切れ/パース失敗は "" で無表示（読取専用・ベストエフォート）。
- controller ループは非改変（dashboard.go 限定）。`dashboard_test.go`（新規）で WARN鮮度/OK無表示/stale無視/非VMモードの4ケースを検証・緑。

## 2026-07-04（オーケストレーター UX 改修の実装仕様＋実装）
- 06 の UX 改修（§4.3/§4.5/§5.4–5.7/§8.1）を 60 に反映し実装：
  - term.go: selectMenu（矢印↑↓/j k＋Enter・番号即確定・各項目説明・非TTU既定=続ける）と printModeBanner（壁打ち/介入/実行の入場バナー）。純関数 resolveMenu を分離し term_test.go で検証。
  - main.go: terminalConfirm をテキスト入力から selectMenu（1.続ける/2.実行/3.終了・日本語）へ置換（bufio 依存除去）。
  - controller.go: runWallbounce を「execute+ready+lint clean→executing／execute だが実行不可→reportNotExecutable+壁打ち直帰（メニュー無し）／continue_wallbounce→再実行／abort→done／control 無・不明→メニュー」に再構成。reportNotExecutable（端末stderr＋audit＋Slack＋handoff_note.md、plan.json 編集を促さない文言）。buildQuestion の選択肢を 1. 連番化。executing/intervene 入場で printModeBanner。ダッシュボードに要判断一覧（タスク名）。
  - mode.go: WallbounceArgs が handoff_note.md を消費して instruction 先頭へ前置。
  - 状態ストアに handoff_note.md（機械所有・人間非編集）。
- 指示テンプレ：wallbounce.md（plan.json タスクスキーマに completion 追加＝必須化・自己検証で全completion揃うまで ready/execute しない・/exit 案内・handoff_note 反映・plan.json を人間編集させない・選択肢番号・日本語）、intervene.md（キュー進捗の口頭明示・answer.md 記録後 /exit・番号・日本語）。
- 設計↔実装仕様・実装仕様内の整合性を独立多エージェントで徹底確認し、メニュー起動条件の二重定義・worker 言語前提の食い違い・§13 誤参照・テスト一覧漏れ等を是正。
- 検証: go build/vet 緑、gofmt 済み、go test（-race 含む）全緑（term_test.go の selectMenu/resolveMenu/buildQuestion 連番、controller_test の reportNotExecutable/handoff_note を追加）。対話メニューの実機 TTY E2E は次段階（自己検証サンプルで attach 確認）。

## 2026-07-05（独立セッション方式の実装仕様＋構成要素の実装）
- 「独立セッション方式（新アーキ）」節を追加（デーモン化・session.go・保持シェル・worker セッション・セレクタ・介入のセッション内対話・単一コマンド復旧・mouse off）。全体構成のモジュール表・カバー・実装状況を更新。06↔60・実装↔60 を独立エージェントで徹底確認し、保持シェル方式/pre-dispatch セッション/ResolveArgs 二重契約/命名(<CNAME>)/旧新ラベリング等を是正。
- 実装（構成要素・go build/vet/test -race 緑・gofmt 済み）：session.go（SessionManager・命名・Ensure保持シェル+mouse off・Run/Kill/Has/SwitchTo・ExpectedSessions/EnsureAll）、daemon.go（pidfile群）、handoff.go WaitConsume（control.json 監視）、controller.go の worker セッション結線（open/closeWorkerSession・nil ガード）と介入 per-worker（reconcileOne/resolveOne）、mode.go ResolveArgsOne、dashboard.go セレクタ（selectableWorkerID/SwitchTo）、main.go で Sessions 注入。単体テスト追加。
- 未実装（最終結線＝要・実機 E2E）：コントローラのデーモン化、RunInteractive→セッション launch+WaitConsume 置換、claude-dev orchestrate 改修、selector からの介入対話起動、pre-dispatch セッション生成。現行の対話・実行の既定動作は旧単一ウィンドウ方式のまま、その上に worker セッションのビュー＋セレクタが加わった状態。

## 2026-07-05（独立ウィンドウ方式：1 セッション＋ウィンドウ）
- 「独立セッション方式」→「独立ウィンドウ方式」へ改訂。session.go を window API（`MainSession`＋`DashboardWindow`/`WallbounceWindow`/`WorkerWindow`、`new-window`/`kill-window`/`select-window`/`list-windows`、`SetupMainSession`〔自窓を dashboard へ改名＋mouse off〕、`remain-on-exit on`〔dashboard は off〕、`splitTarget`）へ書き換え。`Has` は `list-windows` で窓名を厳密照合（`display-message -t session:window` が窓不在でも現窓へフォールバックし誤って成功を返す落とし穴を回避＝実機で判明・修正）。
- controller/dashboard/mode/main を window ターゲットへ結線。`ReqAbort` でも `closeWallbounceSession` を呼ぶよう対称化。`[d]`（ダッシュボード内 tail）と番号キー（個別ウィンドウ切替）は併存（置換ではない）と明記。
- 未使用の `daemon.go`（setsid デーモン用 pidfile。tmux 常駐方式では has-session が主機構）を削除。旧称・旧命名のコードコメントを刷新。
- 独立2エージェントで design↔impl↔code を徹底確認し、front matter/責務表/§実装状況の「セッション」語誤用・`ResolveArgsOne`→`IntervenePrompt`・テスト帰属・`-n dashboard` 正本整合を是正。`go build`/`vet`/`gofmt`/`go test -race` 全緑。

## 2026-07-05（生存判定：has-session → pgrep〔コントローラプロセス〕）
- 復旧/二重起動防止の生存判定を has-session から「claude-orchestrator プロセスの生存」へ変更（06 §5.9）。claude-dev orchestrate（10_cli 正本）を、コンテナ内 pgrep で cmdline が claude-orchestrator で始まるプロセス（tmux 起動ラッパを除外）を判定→生存なら attach／不在なら空き殻セッションを kill-session してから new-session -n dashboard で起こし直し(resume)、へ改修。self-kill は不採用（clean done は dashboard 窓 remain-on-exit off でセッション自然消滅、空き殻は中断/クラッシュ時のみ＝pgrep 判定で吸収）。Go コード変更なし。§80/§87/実装状況/10_cli を更新。独立2エージェントで design↔impl 整合確認。実機 E2E：空き殻状態で has-session=TRUE のところ pgrep=ABSENT を確認、復旧で resume まで確認。

## 2026-07-05（ダッシュボード＝bubbletea カーソル選択 TUI）
- dashboard.go を共有状態＋純ヘルパに縮小し、dashtui.go（新規・bubbletea dashModel）でカーソル選択式 TUI を実装。controller の実行ループは isTTY 時に newDashProgram（WithAltScreen＋WithContext）を起動し、旧 render/renderString/readKeys/Dashboard/KeyEvent/startDash/stopDash/数字キー即移動/選択番号‹k› を撤去。ユーザ操作は actions チャネル（resolve/intervene/quit）＋モデル内（カーソル/[p]/[d]）。bubbletea/lipgloss を go.mod に追加し vendoring（vendor/）で取り込み、Dockerfile.claude を -mod=vendor に更新。テスト：TestDashView_RendersTasksAndCursor 他（dashtui_test.go）。旧 render テストは撤去。go build/vet/test -race 全緑。実機で TUI 描画＋カーソル移動を確認。

## 2026-07-05（追補：コントローラが実行中セッション名を検出＝Enter 無反応の根治）
- 背景：実機で「ホームで Enter を押しても brainstorming に移動しない／何もできない」。調査の結果、コントローラが `main` という名前のセッション内で走っていたのに、`SessionManager` は自セッション名を `orch-<CNAME>-main` と決め打ちしていたため、ウィンドウ生成・`select-window` がすべて**人間が attach している `main` とは別のセッション**（`orch-…-main`）に向かい、Enter が空振りしていた（`claude-dev start` が既定で作る `main` セッションと衝突）。
- 修正（`session.go`/`controller.go`）：`SessionManager.sessionOverride` を追加し、`DetectSession(ctx)` が `$TMUX` 有り時に `tmux display-message -p '#{session_name}'` で実行中セッション名を取得して束縛。`MainSession()` はそれを優先返却。コントローラは `Run` 冒頭（`SetupMainSession` の前）で `DetectSession` を呼ぶ。`--print-main-session` は tmux 外実行なので従来どおり正準名 `orch-<CNAME>-main` を返し、ラッパのセッション作成と互換。
- 検証：実機で「`main` という名前のセッション内でコントローラ起動」を再現→ brainstorming ウィンドウが**同じ `main` セッション**に作られ、ホームで Enter→brainstorming が active になることを確認。正準 `orch-hisol-work-main` 経路も従来どおり動作。`go build`/`go test ./...` pass。配布イメージ再ビルド。
- 設計同期：`60_orchestrator.md`（命名と管理／実装構成の `session.go` 節に `DetectSession`・`sessionOverride` を追記）。

## 2026-07-05（追補：worker ログを Claude Code 風の可読表示に整形）
- 背景：worker ウィンドウ／`[d]` 詳細が worker の生 stream-json をそのまま `tail -F` していたため「JSON が流れるだけで理解できない」。
- 修正（新規 `streamlog.go`／`worker.go`）：`ExecClaude.RunPrompt` の `io.MultiWriter` を「生 stream-json → バッファ（結果解析用）」＋「`workers/<taskID>.log` → `streamPrettyWriter`（整形）」に変更。`streamPrettyWriter` は改行区切りでイベントを受け、`formatStreamLine` が Claude Code 風へ整形：`assistant` text は本文、`tool_use` は `⏺ <ツール名>(<主要引数の要約>)`（Bash→command／Read・Write・Edit→file_path／Grep・Glob→pattern／他→主要フィールドか短縮 JSON）、`tool_result` は `  ⎿ <先頭短縮＋(N 行)>`、`result` は区切り＋完了。パース不能行はそのまま出力（欠落なし）。結果解析（`ParseWorkerResult`）は生バッファを使うので整形は解析に非影響（ログは表示専用）。
- 検証：`streamlog_test.go`（各イベント種別の整形・部分行バッファリング）pass。実機の生 worker ログ（`t2.log`, 191 行）を通し、`⏺ Bash(...)`／`⏺ Read(path)`／`  ⎿ … (N 行)`／地の文が読める形になることを目視確認。`go test ./...` は環境依存でハングする既存の対話テスト `TestIntervene_ResolveApprovesIrreversible`（実 claude を `RunInteractive` で起動＝本変更と無関係・clean tree でも同様）以外は pass。配布イメージ再ビルド。
- 設計同期：`60_orchestrator.md`（worker ディスパッチ step3・`[d]` 節・実装構成に `streamlog.go` を追記）。

## 2026-07-05（追補：review_gate_defect＝レビュア出力の形式不遵守を根治）
- 背景：実機 w-t3 が「ゲート側の不具合」（`review_gate_defect`）で要判断になった。レビュア（sonnet-5）の最終 `result` を確認すると、規定の構造化 JSON ではなく**英語の散文の結論**（"Review complete — no critical or major findings. …"）だった。レビュー自体は合格判定なのに、JSON を 1 行も出さなかったため `ParseReviewResult` が解析不能→`review_format_error_limit`（既定 2）連続で `review_gate_defect` に昇格＝**合格が人間介入へ誤昇格**していた。ゲート機構（レビュア出力のパース契約）の頑健性不足。
- 修正（`review.go`）：
  - `reviewGuide` を強化＝「自動ゲートが JSON としてパースする／散文で答えると false gate defect になる。最終メッセージは JSON オブジェクト 1 個のみ・散文の結論やコードフェンス禁止・合格は `{"findings":[]}`」を明示。
  - `findReviewResultJSON` を頑健化＝(a) 最終行の厳密一致を優先、(b) 失敗時は ```json フェンスや散文中に埋もれた `{...}` を、文字列リテラル内 `}` を無視するブレース対応スキャン（新規 `findJSONObjects`）で拾い、`findings` キーを持つ最後のオブジェクトを採用。共通判定は `tryReviewResult`（`findings` キー必須＝無関係な JSON を弾く）。
- 検証：`review_parse_test.go`（厳密／散文後の JSON／フェンス／同一行前置／文字列内 `}`／純散文は失敗／findings 無しオブジェクトは棄却）pass。純散文（今回の t3 の生ログ相当）は依然パース不能＝安全側で人間へ（誤って合格扱いにしない）。指示強化で次回以降は JSON を確実に出させ誤昇格を抑止。`go test`（既存の対話ハングテスト除く）pass。配布イメージ再ビルド。
- 設計同期：`60_orchestrator.md` §品質ゲート項目4（レビュア指示強化・パーサ頑健化）。

## 2026-07-05（追補：介入解決後に run が恒久停止する競合を根治）
- 背景：実機 w-t3 で要判断に回答し `/exit` した直後、pane は死ぬが閉じず・dashboard も変わらず・以降進まなくなった。調査：`intervention_resolved` は記録され `open.json` は空・`answer.md` も正しく書かれていたのに、plan.json の t3 は `waiting_human` のまま、コントローラは生存（idle）。
- 原因：`resolveInterventionInSession` が `resolveOne`（ディスクから別コピーを `LoadPlan`→`reconcileOne`→`SavePlan`）を呼んでいたため、`runExecuting` が保持する**共有メモリの `plan`（t3=waiting_human）と乖離**。ループは (1) t3 が pending に戻ったと気づかず再ディスパッチせず、(2) 次の `SavePlan` でディスクの pending を waiting_human に上書きし戻す → 回答直後に恒久停止。
- 修正（`controller.go`）：`resolveInterventionInSession(ctx, plan, taskID)` に共有 `plan` を渡し、`planMu` 下で `reconcileOne(plan,…)`＋`SavePlan(plan)` を実行（`resolveInterventions` レガシー経路と同じ正しいパターンに統一）。呼び出し側は解決直後に `syncDashboard`＋`refreshInterventionCount` で即時反映。`resolveOne` は単体テストで使用中のため保持。
- 検証：`go build`／`go test`（既存の対話ハングテスト除く）pass。設計 `60_orchestrator.md`（介入＝worker ウィンドウ内で対話の項に「共有 plan へ突合」の必須事項を明記）。配布イメージ再ビルド。
