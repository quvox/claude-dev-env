# レビュー: オーケストレーター 端末モード不具合の修正

対象: `orchestrator/term.go`(新規), `orchestrator/dashboard.go`, `orchestrator/mode.go`, `orchestrator/main.go`
日付: 2026-06-28
契機: `claude-dev orchestrate` で壁打ち（ai_rule_manager のセキュリティ脆弱性・非効率処理のレビュー作業を依頼）→ `/exit` 後に worker が全く進まず、ダッシュボードのキー入力 `d`/`q`/`p` も反応しない、という報告。

## 不具合の根本原因

対話 `claude`（全画面 TUI）は共有 TTY を非カノニカル（raw, `ICANON=False`）モードに切り替え、**終了時もカノニカルへ戻さない**。これを pty 上の実機 `claude` で確認した（実行中・`/exit` 後ともに `ICANON=False ECHO=False`）。コントローラは同じ TTY を使うため、復帰後の行バッファ読み取りが破綻する:

- raw モードでは Enter が `\n`(0x0A) ではなく `\r`(0x0D) を送る。
- `dashboard.go` の旧 `readKeys` と `main.go` の `terminalConfirm` はいずれも `ReadString('\n')` で `\n` を待つため**永久ブロック**。

これが両症状の単一原因:
1. ダッシュボードのキー `d`/`p`/`q` が無反応。
2. 壁打ちが `control.json` を書かなかった場合に呼ばれる `terminalConfirm` が入力を受け付けられず、`executing` へ遷移できないため worker が一切起動しない。

## 修正の方針

端末モードをコントローラが自前で所有する。新規 `term.go` に `stty` 呼び出しのみで実装（外部 Go モジュールを増やさず stdlib のみ方針を維持）:
- `RunInteractive` の対話 `claude` 終了直後に `ttyRestoreSane()` でカノニカルへ復元。
- `readKeys` は `rawKeyMode()`（`-icanon -echo min 0 time 1`）で TTY を自前設定し 1 バイト読み（Enter 不要・即時反応）。`VMIN=0/VTIME=1` により無入力時 `os.Stdin.Read` が約 0.1 秒ごとに `(0, io.EOF)` を返し、`ctx` キャンセルを取りこぼさず goroutine も残さない。終了時に復元。
- `main.go` に `defer ttyRestoreSane()`（シグナル経路も含めた最終復元）。

## 観点別の所見

### 1. 要件・ユースケースに合致しているか
- 合致。06/60 のユースケース「壁打ち→`/exit`→実行ダッシュボードで監督」「`p`/`q` 操作」「`control.json` 不在時の確認」が成立するようになった。
- 設計の「`d` はバイナリ内 no-op」は維持。`isig` を無効化していないため Ctrl-C → シグナルハンドラ → state flush の経路も維持。

### 2. 無駄な処理が含まれていないか
- なし。旧実装にあった `bufio.Reader` を撤去し 1 バイト読みに簡素化。`stty` 呼び出しは状態遷移時のみ（毎ティックではない）。レンダリングは従来どおり 1 秒間隔。

### 3. 処理時間を改善できる余地
- キー反応はブロッキング行読み（Enter 必須）から即時 1 バイト反応へ改善。`VTIME=1`(0.1 秒)で `ctx` キャンセル検知も高速。レンダリング負荷の増加なし。

### 4. セキュリティ脆弱性
- `stty` は固定引数のみで起動し、ユーザ入力を引数に渡さない（コマンドインジェクションなし）。`SLACK_BOT_TOKEN` の worker/対話 claude への非伝播など既存の技術的封じ込めは不変。新たな権限・ネットワーク・ファイル書き込みを追加していない。

## 残課題（本修正の対象外・別途対応を推奨）
- **worktree 再作成の堅牢性**: 再現テスト中、`.orchestrator/worktrees/<id>` ディレクトリのみ削除されブランチ `orch/<id>` が残った状態で `git worktree add -b` が `fatal: a branch named 'orch/<id>' already exists`（exit 255）で失敗し、`stuck_limit` まで再試行→介入ループに陥る事象を観測。`Worker.PrepareWorktree` はディレクトリ存在時のみ再利用するが、「ディレクトリ無し・ブランチ有り」のケースを扱っていない。既存ブランチ検出時の再利用（`worktree add <path> <branch>`）またはクリーンアップを別 issue として推奨。今回の報告（キー/確認入力）とは独立。

## 検証（端末モード）
- 実機 `claude` を pty 起動し `/exit` 後の `ICANON=False` を確認（根本原因の裏取り）。
- fake `claude`（同条件で raw を残す）による再現テスト:
  - 修正前: ダッシュボードで `q` を押しても 10 秒以内に終了せず（キー無反応を再現）。
  - 修正後: `q` 押下 0.2 秒で終了。確認入力(`execute`)も受理され `executing→dispatch→task_done→completed→done` まで到達。依存関係(t2→t1)順も尊重。
- `go test ./...` 全て pass、`go vet ./...` 指摘なし。

---

# 追補（同日）: 状態ライフサイクル・worker 権限・worktree 堅牢化＋実機検証

端末モード修正後の再テストで報告された追加事象（「前回結果が残って壁打ちを飛ばし実行モードになり操作不能」「以後オーケストレーター起動が即終了」）と、実機（fake でない `claude`）での動作確認の要望に対応した。

## 追加で判明した不具合と修正
1. **完了済み run の即終了**：`state.json` に Phase=`done` が残ると run loop が即 return。→ `isResumable`（executing/intervening のみ再開）を導入し、done/不在/未知は壁打ちから新規開始。
2. **壁打ち飛ばし**：古い Phase=`executing` へ無言で再開。→ 新規/再開を標準出力に明示し、`--fresh` で中断 run も強制新規化（`Store.ResetRun` + `CleanOrchWorktrees`）。
3. **worker が無言で何もしない（実機で発覚）**：worker の `claude -p` に `--permission-mode` 未指定でヘッドレス時に全 Write/Bash が拒否（`permission_denials` を実機で確認）。→ `ExecClaude.PermissionMode`＋`config.worker_permission_mode`（既定 `bypassPermissions`）を明示送出。レビュアも同 runner を共有。
4. **worktree 再作成失敗**：ディレクトリのみ消えブランチ `orch/<id>` 残存時に `add -b` が失敗し再試行ループ。→ `BranchExists`→`WorktreeAddExisting` で既存ブランチへ再接続（前回 review の「残課題」を解消）。

## 観点別の所見（追加分）
- **要件・ユースケース合致**：「壁打ち→自律実行」「中断からの再開」「やり直し（--fresh）」が成立。即終了・操作不能の双方を解消。
- **無駄な処理**：再開判定は起動時 1 回。`CleanOrchWorktrees` は --fresh/新規開始時のみ。冗長処理なし。
- **処理時間**：worker が権限拒否で空回りしていた問題を解消し、実装が実際に進む。再試行ループ（worktree 失敗）も解消。
- **セキュリティ**：`bypassPermissions` は worker のみ（隔離コンテナ・FW・proxy・instruction 制約・`SLACK_BOT_TOKEN` 非伝播で blast radius を限定。06 §10 の既定方針に合致）。`worker_permission_mode: ""` で無効化も可能。`stty`・git 呼び出しはいずれも固定/内部生成の引数のみでユーザ入力を渡さない（インジェクションなし）。

## 実機検証（fake でない `claude`）
- 実機 worker（`--permission-mode bypassPermissions`）が `FROM_WORKER.md` を作成・git コミットし、`permission_denials:[]`・`{"done":true,...}` を返すことを確認。
- Phase=executing を種に**実機オーケストレーター**を起動 → `dispatch→worker_result→task_done→completed→run_done`。実機 worker＋実機レビュア（承認）＋実 `git merge` により作業ブランチ(main)へ `FROM_WORKER.md` が統合されることを 30 秒で確認（権限拒否 0）。
- 状態ライフサイクル：done 残置→新規 run、`--fresh`→executing 上書きで新規、再開時メッセージ表示、を確認。
- 留意：ヘッドレス（非 TTY）で介入トリガーが発火すると対話 `claude` が即終了して再開ループになる。本オーケストレーターは TTY（tmux ウィンドウ）前提で、その場合は介入時に人間入力を待つため問題にならない。テスト時の `stuck_limit:1` は発火しやすいだけで不具合ではない。

## 反映に必要な操作
- バイナリはイメージへ焼き込み（`Dockerfile.claude` の `orch-builder`、`COPY orchestrator/*.go` 済みで新規 `term.go` も含む）。`make build-claude`（VNC 版は `build-claude-vnc`）で再ビルド後、新コンテナで有効。

---

# 追補2（2026-06-29）: 実機（配布イメージ）での全面動作確認と「claude が見つからない」不具合

イメージ再ビルド後に `../ai_rule_manager` の実機コンテナで再確認したところ、新たな致命的不具合を発見・修正し、最終的に配布イメージのバイナリで全経路の動作を確認した。

## 追加で判明した不具合（最重要）
- **`claude` が PATH に無く全 `exec("claude")` が失敗**：`claude-dev orchestrate` は tmux ウィンドウの非対話シェル（`zsh -c`）で起動する。`claude` の導入先 `~/.local/bin` は対話シェル `.zshrc` でしか PATH に入らないため、起動環境に `claude` が無い。壁打ち・介入・worker・レビュアのすべてが「executable file not found」で起動できず、これが「壁打ちが飛ぶ／worker が何もしない」の実体だった（実機 tmux ウィンドウで `claude NOT FOUND` を直接確認。旧 `.orchestrator/audit.jsonl` にも該当エラーが残存）。
- 修正：`claudebin.go` を追加し、`claudePath()`（`LookPath`→`$HOME/.local/bin/claude` フォールバック）で絶対パス解決＋`claudeChildEnv()` で PATH 補完。`mode.go`/`worker.go` の起動を切替。

## 実機検証（fake でない claude・配布イメージ）
- 配布イメージを `make build-claude-vnc` で再ビルドし、コンテナを作り直して**イメージ同梱の `/usr/local/bin/claude-orchestrator`** を使用。
- tmux 相当の制限 PATH（`~/.local/bin` 無し＝`claude NOT on PATH`）で、`t-kubo` 実行・実機 claude にて：
  - **状態ライフサイクル**：leftover Phase=`done` のまま起動しても「🆕 新規セッションを開始します」と表示し**即終了しない**（報告された不具合の解消を実機確認）。
  - **worker パイプライン**：`SHIP.md` を作成・コミットし作業ブランチ(main)へマージ（`dispatch→review_result→task_done→completed→run_done`）。権限拒否 0。
  - **壁打ち**：対話 `claude` の TUI（フォルダ信頼プロンプト）まで起動（以前は executable not found で即 confirm に落ちていた）。
- 留意：壁打ち/worker いずれも初回フォルダで claude の「信頼」プロンプトが出る場合がある。壁打ちは人間が同席するため対応可能。worker（`claude -p`＋bypass）は本検証で信頼確認なく完走した。

## 結論（中間）
端末モード・状態ライフサイクル・worker 権限・worktree 堅牢化・claude 実行ファイル解決の 5 系統の修正により、`claude-dev orchestrate` の壁打ち→自律実行→完了の全経路が、配布イメージの実機 claude で動作することを確認した。

---

# 追補3（2026-06-29）: 可観測性・中断の再開可能化・完了検証＋設計/実装の総点検

実機運用で「ずっと待機中に見える／`[d]` で何も出ない／`[q]` で worker が消え復元不能」となり実質使えなかった。UX/設計の不備を是正し、設計↔実装の不整合と未実装機能を総点検した。

## 是正した不具合（UX/設計）
1. **ダッシュボードが running を反映しない**：タスク dispatch 時に `syncDashboard` を呼ばず、完了まで「待機中」表示のままだった → running 時に同期し、状態ラベル・経過時間・試行回数を表示。
2. **`[d]` が no-op**：詳細表示が未実装で worker の様子が一切見えなかった → 実行中 worker のログ末尾をライブ表示するトグルとして実装。併せて worker 出力を `--output-format stream-json --verbose` で**ログへライブ tee**（従来の `json` は完了まで無出力で「空ログ」だった）。
3. **`[q]` が破壊的で復元不能**：中断が `done` 遷移＝終了扱いで、(さらに done→fresh のため) 再開できず全 worker の作業を失っていた → `[q]` を**状態保存つき中断（`errSuspended`、Phase=executing 維持）**に変更。次回起動で中断点から再開（worktree のコミット保全）。離席だけなら tmux detach を案内。

## 総点検（独立した 2 系統の監査を実施）
- 設計↔実装の不整合監査と、仕様→コードの実装ギャップ監査を別々に実施。
- **判明した唯一の「documented-but-unimplemented」罠＝Config B（`--workers-window`）**：ドキュメントは実機能のように記載しつつ、バイナリも CLI も何もしていなかった → **廃止**（`[d]` ライブ表示が同用途を満たすため）。フラグを `main.go`/`claude-dev` から削除し、設計/CLI ドキュメントからも除去。
- **`completion`（完了基準）が収集されるだけで未使用**だったギャップ → **助言的な自然言語完了検証**を実装（`checkCompletion`、ブロックしない・read-only 意図）。
- 残る未実装（`reviewer_vendor: codex`／Slack 双方向／Docker Agent／不足分の自動タスク化）は**いずれも設計上の将来フェーズ**であり、`60_orchestrator.md` に**「実装状況（v1）」節**を新設して実装済み／未実装を明示（隠れた未実装を無くす）。
- 設計 `06`（§4.5 主要な統合点、§5.2/5.3 キー意味・Config B 廃止）と実装仕様 `60`（ダッシュボードキー・worker stream-json・完了検証・blocked 終端性・reviewer_vendor 注記・実装状況節）を実装に一致させ、監査が挙げた不整合（[d] 意味、continue_wallbounce、config/ORCHESTRATOR.md/intervene.md の設計未言及、answer.md 所有者、go.sum 等）を解消。go.sum は依存ゼロのため不要＝現状の Dockerfile が正しいことを確認。

## 観点別所見（追加分）
- **要件・ユースケース合致**：「worker の様子が見える」「中断して後で再開」という実運用要件を満たすようになった。
- **無駄な処理**：`syncDashboard` の追加呼び出しは dispatch 時のみ。完了検証は完了時 1 回（助言）。
- **処理時間**：体感のブロッカー（見えない・中断＝全損）を解消。
- **セキュリティ**：完了検証は「変更するな・検証のみ」を指示する read-only 意図の `claude -p`。worker 同様 `SLACK_BOT_TOKEN` は不伝播。新規の外部通信・権限なし。

## 検証
- `go build`/`go vet`/`go test ./...` 全 pass。stream-json 解析・完了検証解析の単体テストを追加（実 `claude` の stream-json 実出力サンプルでも解析成功を確認）。
- 配布イメージ（`claude-dev-claude-vnc`）を再ビルド済み。

## 結論
端末モード・状態ライフサイクル・worker 権限・worktree 堅牢化・claude 実行ファイル解決に加え、可観測性（running 表示・`[d]` ライブ出力）・中断の再開可能化・完了検証を実装。設計↔実装の不整合を解消し、未実装機能は「実装状況（v1）」として明示。`claude-dev orchestrate` が実運用で観測可能・中断再開可能な状態になった。
