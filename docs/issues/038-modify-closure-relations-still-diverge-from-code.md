---
id: 038-modify-closure-relations-still-diverge-from-code
type: modify
severity: 中
found: 2026-08-04
found_in: /doc-check ssot task-impl-depth(独立監査 Codex `relations` 3本 = check B4/B5/B6。`gpt-5.6-terra` / reasoning `max`。Claude が「高」全件をコードで裏取り)
related: MODULE-orchestrator-controller, MODULE-orchestrator-handoff, MODULE-orchestrator-state-intervention, MODULE-orchestrator-review, MODULE-orchestrator-term, MODULE-orchestrator-session, MODULE-orchestrator-worktree, MODULE-orchestrator-worker, MODULE-orchestrator-mode, MODULE-orchestrator-slack, MODULE-cli-start, MODULE-cli-pull, MODULE-cli-reset, MODULE-cli-stop, MODULE-cli-logout
summary: 【2026-08-04 重大度を高→中に是正。「高」5件(表 #1〜#5)は再裁定=案B により task-impl-depth で解消済みで、残件は中20件・低7件】task-impl-depth が「再実装可能な深度」まで掘り下げた影響範囲内の relations 21本が、SSOT へ反映した後もなおコードと食い違う。残るのは変更指示の sections に入っていなかった節の叙述
---

# 038 影響範囲内の relations が反映後もコードと食い違う

## 事象

`task-impl-depth` は `03-impl/relations/` のうち **21本**を「ドキュメントだけから再実装・再試験できる
深度」へ掘り下げ、`/doc-check task-impl-depth`(task モード)で PASS を得て `/task-close` が SSOT へ
反映した。反映後の SSOT に対して独立監査(Codex `relations` モード、`gpt-5.6-terra` / reasoning `max`)を
**cli 7本 / orchestrator 7本 / orchestrator 7本**の3スコープで掛けたところ、**同じ21本の中に
約34件の食い違い**が残っていた。

`issue 032` は**影響範囲外**の7本についての同種の指摘だが、本 issue は**影響範囲内**である点が違う。
すなわち「掘り下げの対象にした本文そのもの」がコードと一致していない。

### 公開シグネチャ・観測可能な振る舞いの相違(重大度「高」。Claude がコードで全件裏取り)

| # | 箇所 | ドキュメントの記述 | コードの事実 |
|---|---|---|---|
| 1 | `MODULE-orchestrator-controller.md` 呼び出され方・戻り値 | `Controller.Run` の引数表に `plan *Plan`(必須)。中断時の戻り値は `errSuspended` | `orchestrator/controller.go:52` — `func (c *Controller) Run(ctx context.Context) error`(引数は `ctx` だけ)。`:92`〜`:96` — `errSuspended` を**吸収して `nil` を返す**。呼び出し元は中断と正常終了を戻り値で区別できない |
| 2 | `MODULE-orchestrator-controller.md` 処理の流れ・異常系 | 「起動時に `DiscardStale` する」「状態保存の失敗は握りつぶして続行する」 | `orchestrator/controller.go:76` は `st.Phase == PhaseExecuting` の分岐内、`:215` は tmux ブレインストーミング開始時のみ(無条件の起動時ではない)。`SaveState` は `:70` と `:1080` で **`return err` している**(握りつぶすのは `:595` だけ)。**「すべて握りつぶす」は過大な一般化** |
| 3 | `MODULE-orchestrator-state-intervention.md` 異常系 | 「`open.json` が存在しない → 空のキューを返す」 | `orchestrator/state.go:396`〜`:402` — `readJSON` の**すべてのエラー**(JSON 破損・読取失敗を含む)で空キューを返し、エラーを返さない。壊れた `open.json` は判断待ちキュー全体を黙って失い、その後の `Add` が内容を上書きしうる。`MODULE-orchestrator-state-intervention.md` の「目的」は `FR-orch-05`「run をまたいで判断待ちが失われないこと」を掲げているので、**要件との不一致**でもある(`issue 032` #11 が同じ事実を中として記録しているが、`FR-orch-05` との不一致は誰も指摘していなかった) |
| 4 | `MODULE-orchestrator-handoff.md` 呼び出され方・異常系 | `WaitConsume(until)` として `until` だけを引数表に載せる。「エラーは呼び出し元へ伝播する」 | `orchestrator/handoff.go:49` — `WaitConsume(ctx context.Context, poll time.Duration, until func() bool)`。**`poll` は定型引数ではないので `issue 009` の (a)(`ctx` 省略の規約)ではなく (b)(引数の顔ぶれが違う)に当たる**。`task-impl-depth` は「(a) なので触らない」と分類していたが誤り。また `orchestrator/controller.go:246` は `ctrl, _ :=` で**エラーを捨てている** |
| 5 | `MODULE-orchestrator-review.md` 処理の流れ | 受け取る `findings[]` は `severity = critical / major / minor`、`file`、`message`、`aspect` を持つ | `orchestrator/review.go:298`〜`:312` — パーサは `findings` キーの**存在だけ**を確認し、各 finding の必須項目も `severity` の値域も検証しない。`:24`〜`:31` の `HasSevere` は `critical` / `major` の**完全一致**だけを重大とするため、**未知の `severity`(綴り違い・大文字違いを含む)を持つ重大な指摘はゲートを通過する** |

### 記述が実装と違うもの(重大度「中」)

| # | 箇所 | 内容 |
|---|---|---|
| 6 | `MODULE-cli-pull.md` 異常系・既知の制限 | 「`docker tag` の戻り値を見ない。成功フラグは立ち、完了と表示される」と書くが、`claude-dev:668` の `docker tag` は **`set -e` 下の無保護コマンド**で、失敗すれば `_pull_ok=1` と完了表示の**前に**非0終了する(`claude-dev:8` の `set -e`)。→ **`issue 037` ② の前提が成立しない**(下記「他 issue への影響」) |
| 7 | `MODULE-cli-reset.md` 異常系 | 「非 TTY では空入力=キャンセル扱いで終了コード 0」と書くが、`claude-dev:1377` の `read -p ... -n 1 -r` は無保護で、標準入力が EOF なら `set -e` によりキャンセル分岐(`:1379`〜`:1382`)へ**到達せず非0終了**する |
| 8 | `MODULE-cli-start.md` 処理の流れ・副作用 | Linux 版と macOS 版を区別せず1本の本文で書いている。`claude-dev:1015` は未起動時に `CLAUDE_DEV_NO_ATTACH=1` を付けて `start` を再帰呼出しするが、`claude-dev-mac:1025` は `exit 1` で終わり、macOS 版 `start` はこの環境変数を判定せず常に `tmux attach` する。また `require_setup` の実行順が macOS 版では本文の番号順と違う |
| 9 | `MODULE-cli-start.md` entrypoint 節・副作用 | `scripts/entrypoint-claude.sh` の副作用として `/workspace/.codex/config.toml` の作成・補完(`:262`〜`:410`)、`/workspace/CLAUDE.md` の自動更新(`:517`〜`:609`)、VNC 時の `.mcp.json` / `.claude.json` 更新(`:611`〜`:674`)が列挙されていない |
| 10 | `MODULE-orchestrator-controller.md` 並行性 | 「Store への書き込みはすべて `planMu` を取る」「Slack は `planMu` を解放してから送る」「TUI の取りこぼしはチャネルのバッファに残る」の3点がいずれも実装と違う(`runTaskPipeline` は `planMu` 解放後に `Worker.Dispatch` → `AppendAudit` / `updateSummaryLocked` は `planMu` 保持中に `Notify` / `orchestrator/dashtui.go` の `send` は満杯時に `default` で操作を捨てる) |
| 11 | `MODULE-orchestrator-controller.md` frontmatter | `callees` に通知経路(`MODULE-orchestrator-slack`)が無いが、`Controller` は複数箇所で `Notifier.Notify` を呼ぶ。逆に `MODULE-orchestrator-slack.md` の `callers` は `MODULE-orchestrator-main` だけ |
| 12 | `MODULE-orchestrator-claude-exec.md` frontmatter | `callers` に `MODULE-orchestrator-worker` / `-review` が無い。`orchestrator/main.go:143`〜`:155` は同じ `ExecClaude` を Worker と Reviewer に注入し、`worker.go:231` / `review.go:81,126` が `Claude.RunPrompt` を呼ぶ |
| 13 | `MODULE-orchestrator-worker.md` 呼び出され方 | 引数表が `task` と `ctx` の2項目だけ。実シグネチャは `Dispatch(ctx, p *Plan, t *Task, feedback string)` で、`Plan` 全体と差し戻し `feedback` が呼び出し契約に含まれる(`issue 009` (b) と同種) |
| 14 | `MODULE-orchestrator-review.md` 戻り値・副作用 | 「戻り値 = レビュー結果(`findings[]`)とゲート通過可否」と書くが、主シンボル `RunGate` は `(GateOutcome, error)` を返し、`GateOutcome` は `Passed` / `LastSevere` / `FormatError` / `FormatErrorCount` で `findings` を持たない(`orchestrator/review.go:160`〜`:179`) |
| 15 | `MODULE-orchestrator-review.md` 処理の流れ | 「パース不能なら `Task.ReviewFormatErrors++`」と書くが、`RunGate` はローカル変数 `formatErrs` を増やして `GateOutcome` に載せるだけで、live な `Task` への代入は `orchestrator/controller.go:685` が上限到達後に行う |
| 16 | `MODULE-orchestrator-term.md` 呼び出され方・戻り値 | `selectMenu` の引数を「`options` = 文字列の並び」とし、`rawKeyMode` / `ttyRestoreSane` / `sttyRun` が `error` を返すと書くが、実装は `selectMenu(title string, items []menuItem, def int) string` / `rawKeyMode() (func(), bool)` / `ttyRestoreSane()`(戻り値なし)/ `sttyRun(...) bool` |
| 17 | `MODULE-orchestrator-term.md` 異常系 | 「入力が来ないまま `until` に達したら現在のカーソル位置を返す」と書くが、`selectMenu` に `until` 引数もタイマーも無く、`orchestrator/term.go:137`〜`:142` は `n==0` のとき `continue` して読み直す |
| 18 | `MODULE-orchestrator-session.md` 処理の流れ | 「dashboard は `remain-on-exit off`」「すべての tmux 呼び出しは `tmuxRun` に集約」「`Run` の `cmd` は `shellSingleQuote` でクォートする」の3点が実装と違う(`Ensure` は対象を問わず `on` / `DetectSession` / `Has` / `PaneDead` は直接 `exec.CommandContext` / `respawn-pane` は command をそのまま渡す) |
| 19 | `MODULE-orchestrator-worktree.md` 処理の流れ | `HasCommits` が統合前の状態確認に使われると書くが、製品コードに呼び出しが無い(定義とインターフェース宣言だけ) |
| 20 | `MODULE-orchestrator-worktree.md` 異常系 | 「git の stderr はエラーに含めて返す」と書くが、公開 `GitRunner` メソッドは `ExecGit.run` の結合出力を `_` に捨て、呼び出し元へ渡さない |
| 21 | `MODULE-orchestrator-state-intervention.md` 処理の流れ 5 | 「`WriteAtomicSidecar` / `ReadAtomicSidecar` が巨大なプロンプトを `.sys` / `.prompt` として扱う」と書くが、実際は `Mode.WriteLaunchScript` が両ファイルへ直接 `writeAtomic` し、sidecar API の製品利用は `handoff_note.md` である(`issue 032` #12 と同一) |
| 22 | `MODULE-orchestrator-mode.md` 処理の流れ | 「独立ウィンドウ方式では `ResolveArgsOne` を使う」と書くが、製品コードの呼び出しが無く、`Controller` は `IntervenePrompt` と `WriteLaunchScript` を使う |
| 23 | `MODULE-orchestrator-streamlog.md` 処理の流れ・異常系 | 「未知の種別はそのまま出す」と書くが、有効な JSON で `Type` が未知のイベントは `orchestrator/streamlog.go:112`〜`:113` の `default: return ""` で**破棄**される。素通しは非 JSON 行のときだけ(`issue 032` #13 と同一) |

### 記述が不足・不正確なもの(重大度「低」)

| # | 箇所 | 内容 |
|---|---|---|
| 24 | `MODULE-cli-stop.md` 実装上の判断 | 「すべての削除で失敗を握る」と書くが、本体の `docker rm -f "$NAME"`(`claude-dev:1126`)に `|| true` が無い。**同じファイルの戻り値欄は「本体削除だけ非0」と正しく書いており本文内で自己矛盾している** |
| 25 | `MODULE-cli-logout.md` 処理の流れ | Claude コンテナと docker-proxy を `container_exists` で確認してから削除すると書くが、この共通関数を使うのは proxy だけ。Claude コンテナは `claude-dev:638`〜`:642` が `docker ps -a` から直接列挙し、停止中のものも削除対象になる |
| 26 | `MODULE-cli-start.md` / `MODULE-cli-stop.md` の行番号根拠 | `MODULE-cli-start.md` が entrypoint 起動箇所として挙げる `claude-dev:419` / `claude-dev-mac:486` は docker-proxy の `docker run` で、主コンテナ起動は `:901` / `:938`。`MODULE-cli-stop.md` の本体削除根拠 `claude-dev:1125` は実際にはフォワード削除で、本体削除は `:1126` |
| 27 | `MODULE-orchestrator-review.md` 戻り値・副作用 | レビュアログを `workers/<taskID>.log` とするが、`orchestrator/review.go:79` は `WorkerLogPath(t.ID + ".review")` を渡すので実際は `workers/<taskID>.review.log` |
| 28 | `MODULE-orchestrator-term.md` 戻り値・副作用 | 「メニューとモードバナーは標準出力」と書くが、`printModeBanner`(`orchestrator/term.go:75`)は標準エラーへ書く |
| 29 | `MODULE-orchestrator-term.md` frontmatter | `tests` に挙げる `TestBuildQuestion_NumbersOptions` は `term.go` のシンボルを呼ばず、`orchestrator/controller.go:1147` の `buildQuestion` を検証している |
| 30 | `MODULE-orchestrator-slack.md` 既知の制限 | 「`NopNotifier` は製品コードから使われず、テストでのみ使う」と書くが、指定範囲のテストにも参照が無い(意図の記述になっている。`issue 001` と同根) |
| 31 | `MODULE-orchestrator-trigger.md` 呼び出され方 | `TriggerContext` の引数表に `Phase TriggerPhase` / `Result *WorkerResult` / `StuckThisAttempt bool` が無い。`Evaluate` は `Phase` で起動前・実行後の判定を分けるので、値域が無いと呼び出し元が判定を誤りうる |
| 32 | `MODULE-cli-*`(macOS) | macOS 版は `logout` / `stop` / `reset` の削除経路で `xargs -r ... \|\| true` を使う。BSD `xargs` が GNU の `-r` を受理しない環境では、本文が「削除済み・完了」とする資源が実際には削除されず、エラーも表示されない(**推測**。実機未確認) |

## 影響

- **`docs/03-impl/index.md` は relations 層の代表として版と合格証を持つ**(CLAUDE.md 不変則6)ため、
  上の「高」5件が未解決である間は**この層を再認証できない**。`close-task.py` のゲート (b) に効くので
  `task-impl-depth` を閉じられない。
- `issue 004`(「ドキュメントだけから再実装・再試験できる深度」)の目標に対して、**掘り下げの対象に
  した本文そのものが再実装可能でない**。とくに #1(`Run` の引数と中断の戻り値)と #5(`severity` の
  値域が検証されない)は、ドキュメントどおりに再実装すると**別の振る舞いになる**。
- **過程についての含意**: `task-impl-depth` は同じ対象に対して task モードの `/doc-check` を
  **のべ 10 反復以上**回して PASS を出したが、そのうち大半の独立監査は
  `environments.md` の「モデル・reasoning = 未定」により **codex 既定(`gpt-5.6-sol` / reasoning `none`
  = 最弱)**で走っていた(`issue 031`)。規範の既定(`gpt-5.6-terra` / `max`)で掛けた本監査は
  1回で「高」5件を出した。**レンズの強さが検出力を支配している。**

## 原因の見当

**推測**: 掘り下げの作業単位が「節」(`## 呼び出され方` / `## 異常系` / `## 既知の制限` …)であり、
`sections:` に挙げなかった節は SSOT のまま残った。実際に上の多くは
**置換対象に入っていない節**(`## 処理の流れ` / `## 連携先と連携内容` / `## 戻り値・副作用` /
frontmatter の `callers` / `callees`)に集中している。`check-relations.py` と `callgraph-check.py` は
frontmatter と呼び出し関係しか見ないため、散文の乖離を構造的に検出できない
(`.claude/directions/relations.md` §6 の限界)。

## 正はどちらか

**大半は実装が正でドキュメントの記述誤りだと思われるが、CLAUDE.md 原則2 により `/doc-check` は
判定しない。** とくに次は人間の判断が要る。

- **#5(`severity` の値域が検証されない)**: `FR-orch-06` は品質ゲートを要件として持つ。
  未知の `severity` を持つ重大な指摘がゲートを通過するのが意図なら実装が正、
  そうでなければ**実装のバグ**である(`issue 034` の「スキーマ強制はしない」という裁定と
  組み合わせると、**形式の検証がどこにも無い**ことになる)。
- **#3(壊れた `open.json` で判断待ちキューが消える)**: `FR-orch-05`「run をまたいで判断待ちが
  失われないこと」との不一致。実装が正なら要件を精密化する必要がある。
- **#6(`docker tag` は `set -e` で落ちる)**: 事実が判明したので `issue 037` ② の再裁定が必要。

## 対処案

| 案 | 内容 |
|---|---|
| A | 別タスクとして切り、21本の**未置換の節も含めて**コードと突き合わせて揃える(`issue 032` の18件と同時に扱うと対象が重なって効率がよい) |
| B | 「高」5件だけを `task-impl-depth` の影響範囲へ取り込んで閉じ、中低27件は別タスクへ回す(`issue 032` のときと同じやり方) |
| C | `03-impl/relations/` の**残り61本すべて**を同じ強さのレンズに掛けてから、まとめて1タスクにする |

**注**: `issue 032` のときに B を採ったが、その結果が本 issue である
(影響範囲を最小に切ったため、同じ層の同じ性質の乖離が次の実行で再び出た)。
**C は網羅性を取るが、82本 × 未置換節の突き合わせは1タスクの粒度を超える可能性がある** ため、
02 のモジュール分割定義の見直し(CLAUDE.md §3「一度に終われないならモジュールが大きすぎる」)を
併せて検討する価値がある。

## 他 issue への影響

- `issue 037` ②(`docker tag` の失敗を検査しない = バグ)の**前提が成立しない**。#6 のとおり
  `set -e` により非0終了するので、`FR-env-09` 受入基準11「付け替えに失敗したら成功として
  報告してはならない」は**満たされている**(専用のメッセージが出ないだけ)。
  `docs/03-impl/index.md` の「要件との差異(01 ⇄ 03)」行と、2026-08-04 の裁定(037=C の ②)は
  **再検討が必要**。
- `issue 009` (b) の対象に **`WaitConsume`(#4)と `Dispatch`(#13)が漏れていた**。
  `task-impl-depth` の残作業表は `WaitConsume(until)` を「(a) なので触らない」と分類していたが、
  `poll` は定型引数ではないので (b) である。
- `issue 032` #11 / #12 / #13 と本 issue の #3 / #21 / #23 は同一の事実。
  `issue 032` は影響範囲外の7本、本 issue は影響範囲内の21本という切り口の違いで重複している。

## 裁定の記録(2026-08-04)

**人間の裁定: 案A(別タスクで 21 本を未置換節も含めて全面に揃える。`issue 032` の 18 件と同時)。**

- **本 issue は開いたまま**残す。次のタスクで `issue 032`(範囲外7本・18件)と本 issue
  (範囲内21本・約34件)を1つの影響範囲として扱う。
- 高5件も含めて**次タスクで直す**。したがって `03-impl/index.md`「コードとの乖離として
  未解決のもの」に本 issue を挙げた状態が正しい姿である(**人間が判定済みの既知の乖離**)。
- **教訓**: `issue 032` のとき「高2件だけ取り込む」と範囲を最小化した結果が本 issue である
  (同じ層の同じ性質の乖離が再発した)。**部分的に直すと残りが次の検証で再浮上する**
  → `docs/feedbacks/` に記録する。


## 追加(2026-08-04 `/doc-check ssot task-impl-depth` の新しい実行)

裁定(案A: 別タスクで 21 本を未置換節も含めて全面に揃える。`issue 032` の 18 件と同時)は
変わらない。**その別タスクの影響範囲に含めるべき項目を3件追加する。**
いずれも独立監査(Codex `readiness` / `relations`。`gpt-5.6-terra` / reasoning `max`)が
単独で検出し、Claude が本文で裏取りした。

| # | 対象 | 内容 | 起点 |
|---|---|---|---|
| 6 | `docs/02-design/contracts/orchestrator-prompt.md` ⇄ `docs/03-impl/contracts/orchestrator-prompt.md` | **02 は worker / reviewer 結果の複数フィールドを「必須」と定めるが、03 は「必須フィールドの欠落をエラーにせず Go のゼロ値にする」と書いている。** 02 側に「必須だが検証はしない」ことが書かれていないため、「必須」が検証失敗を意味するのか既定値補完を意味するのかが契約から読めない。`done` だけは復号前の行選別条件で担保される(調査メモ #35) | **02**(記述の不足)。03 はコードと一致している |
| 7 | `docs/03-impl/relations/MODULE-orchestrator-review.md` の `## 既知の制限` | **`issue 034`(レビュー結果にスキーマ強制が無い)の行が「正がどちらかは要確認」のまま残っている。** 034 は 2026-08-04 に人間が案A(実装が正)で裁定済みで、`FR-orch-06` 受入基準3 と `D0-orch-15` の双方が更新されている。**裁定済みの論点が未裁定として書かれている** | **03**(裁定の反映漏れ) |
| 8 | `docs/03-impl/index.md` の「コードとの乖離として未解決のもの」 | 本 issue の件数を **「約34件」**と書き、対象の 21 本の `MODULE-ID` を列挙していない。**完了条件を文書から測れない**(check C7 の測定可能性) | **03**(記述の精度) |

### 併せて修正が必要な、本 issue と同じ性質の項目(別 issue に記録済み)

- `docs/issues/005` 追加分: `MODULE-docker-proxy-serve` の `## 既知の制限` に
  「解釈できないボディは検査せず中継する」を追加する。
- `docs/issues/028` 追加分: `docs/03-impl/contracts/cli-container.md` の `## 設計との差異` の
  「差異なし」を訂正する。

**この3件 + 上の2件を合わせると、次のタスクの影響範囲は
「`relations/` 21本 + `issue 032` の7本 + `03-impl/contracts/` 2本 + `02-design/contracts/` 1本」**
になる。`issue 032` のときに「高2件だけ取り込む」と範囲を最小化した結果が本 issue であるという
教訓(上記)から、**今回は同じ性質の乖離を1つの影響範囲にまとめて扱うこと。**

## 裁定の記録(2026-08-04・確定)

**★先の記録(案A)は撤回する。** 案A では `03-impl/index.md` を再認証できず、
`close-task.py` のゲート (b) で `task-impl-depth` を閉じられないことが判明したため、
その前提を示して人間に再確認し、**案B(高5件を `task-impl-depth` で直し、中低27件は別タスク)**
を選択した。

**`task-impl-depth` で解消した「高」5件**(すべてコードで裏取り):

| # | 直したファイル | 内容 |
|---|---|---|
| 1 | `MODULE-orchestrator-controller.md` | `Run` の引数は `ctx` だけ(引数表から `plan` を外し、plan の位置づけを注記) |
| 2 | 同 | 中断(`errSuspended`)は **`Run` が吸収して `nil` を返す**。状態保存の失敗は**経路によって違う**(初回作成とフェーズ遷移は `return err`、executing 中は握りつぶす)。`DiscardStale` は起動時ではなく2箇所限定 |
| 3 | `MODULE-orchestrator-state-intervention.md` | 壊れた `open.json` で**キュー全体が黙って失われる**ことと、**`FR-orch-05` 受入基準7 との食い違い**を異常系に明記 |
| 4 | `MODULE-orchestrator-handoff.md` | `WaitConsume` の引数表に `ctx` と `poll`(0 以下は 500ms)を追加 |
| 5 | `MODULE-orchestrator-review.md` | 検証は「`findings` キーの存在」だけで、**`severity` の値域を検証しないため未知値が重大でない扱いでゲートを通過する**ことを明記 |

**残件は中低27件**(#6〜#18。ただし #6 は `issue 037` の再裁定で解消済み)。次のタスクで
`issue 032` の18件と1つの影響範囲として扱う。**本 issue は開いたまま残す。**


## 追加(2026-08-04 `/doc-check ssot task-impl-depth` の新しい実行)— 重大度を 高 → 中 に是正

上の「裁定の記録(2026-08-04・確定)」は**案B**(高5件は `task-impl-depth` で直し、中低27件は
別タスク)である。本実行で、**その5件が本当に SSOT へ反映されコードと一致しているかを
本文とコードの両方で照合し、全件の解消を確認した**。

| # | 反映先(本文) | 突き合わせたコード | 結果 |
|---|---|---|---|
| 1 | `MODULE-orchestrator-controller.md:29`, `:174` | `orchestrator/controller.go:52`(`Run(ctx context.Context) error` = 引数は `ctx` だけ) | 一致 |
| 2 | 同 `:30`, `:146`, `:229` | `controller.go:70`・`:1080` は `return err`、`:88`〜`:98` は `errSuspended` を吸収して `nil` を返す | 一致 |
| 3 | `MODULE-orchestrator-state-intervention.md:85` | `orchestrator/state.go:396`〜`:402`(`readJSON` の**すべての**エラーで空キューを返す) | 一致。`FR-orch-05` 受入基準7 との食い違いも明記されている |
| 4 | `MODULE-orchestrator-handoff.md:52`〜`:54` | `orchestrator/handoff.go:49`〜`:52`(`WaitConsume(ctx, poll, until)`。`poll <= 0` なら 500ms) | 一致 |
| 5 | `MODULE-orchestrator-review.md:34`〜`:38` | `orchestrator/review.go:296`〜`:312`(`findings` キーの存在だけ確認)/ `:24`〜`:31`(`HasSevere` は `critical` / `major` の完全一致) | 一致 |

したがって**本 issue の未解決分は表 #7〜#32 の 27 件(中20 / 低7)だけ**である。
`severity` を **高 → 中** に是正した(2026-08-03 に `issue 032` に対して行ったのと同じ是正)。

**これにより `docs/03-impl/index.md`(relations 層の代表)を再認証できる状態になった。**
残る乖離は「人間が裁定済みの既知の乖離」として同ファイルに列挙してある。

### 併せて本実行が解消した、本 issue の「追加」3件

- **#7 解消**: `MODULE-orchestrator-review.md` の `## 既知の制限` に残っていた
  `issue 034` の「正がどちらかは要確認」を削除した。`FR-orch-06` 受入基準3 と `D0-orch-15` は
  どちらも「ツールによるスキーマ強制は行わない」へ改まっているので、**現在は 01・02 との不一致が
  存在しない**(裁定済みの論点が未裁定として残っていた記述誤り)。
- **#8 解消**: `docs/03-impl/index.md` の「約34件」を「残 27 件(本 issue の表 #7〜#32)」へ
  改め、重大度の内訳と解消済みの範囲を書いた(完了条件を文書から測れるようにした)。
- **#6(02/03 契約の「必須」⇄「ゼロ値」)は未解消のまま残す**。02 側に「必須だが検証はしない」を
  書き足すのは設計意図の記述であり、質問キュー #8「02 契約の期待する振る舞いは今回触らない」の
  範囲。次タスクの影響範囲に残る。

### `issue 028` の追加分も解消した

`docs/03-impl/contracts/cli-container.md` の `## 設計との差異` の「差異なし」を、
`issue 028` が指定していた文面(別パスの同名ディレクトリを同一セッション扱いにするため
`NFR-scale-01` の「衝突 0 件」を満たさない)へ差し替えた。
