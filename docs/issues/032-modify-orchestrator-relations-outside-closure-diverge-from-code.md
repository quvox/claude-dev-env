---
id: 032-modify-orchestrator-relations-outside-closure-diverge-from-code
type: modify
severity: 中
found: 2026-08-03
found_in: /doc-check ssot(独立監査 Codex `relations` モード = check B4/B5。Claude が全20件をコードで裏取り)
related: MODULE-orchestrator-streamlog, MODULE-orchestrator-state-intervention, MODULE-orchestrator-dashboard, MODULE-orchestrator-main, MODULE-orchestrator-plan, MODULE-orchestrator-state, MODULE-orchestrator-config
summary: 【2026-08-04 重大度を高→中に是正。高2件(#1 / #2)は task-impl-depth の反映で解消済み】task-impl-depth の影響範囲に入っていない orchestrator の機能間連携仕様書7本が、コードと20箇所で食い違う。残件は中10件 / 低7件 + 中#6(裁定済み・別タスク)
---

## 事象

`task-impl-depth` は `03-impl/relations/` のうち19本を対象とし、残り63本は
「issue 004 が挙げた7観点のいずれにも該当せず、現状の記述で深度が足りている」として変更なしと決めた。
そのうち **orchestrator の7本**(`config` / `dashboard` / `main` / `plan` / `state` /
`state-intervention` / `streamlog`)を独立監査(Codex `relations`)に掛けたところ、
**20箇所でコードと食い違っていた**。**全件を Claude がコードで裏取りして事実であることを確認した**
(裏取りできなかったものは1件も無い)。

`check-relations.py`(82/82 合格)・`callgraph-check.py`(重大度「高」0件)・
`check-contracts.py`(合格)は**いずれもこれらを検出しない**。フロントマターの `impl` パス・
シンボル・`tests` は全件実在し、機械検査が見るのはそこまでで、**本文の散文が実装と一致するかは
見ていない**ためである。

### 観測可能な振る舞いが違うもの(重大度「高」)

| # | 箇所 | ドキュメントの記述 | コードの事実 |
|---|---|---|---|
| 1 | **【解消済み(task-impl-depth の反映。2026-08-04 `/doc-check ssot` がコードで確認)】** `MODULE-orchestrator-state-intervention.md` 異常系「`control.json` が壊れている」 | 「handoff は**未消費として扱い、次のポーリングで再試行する**」 | `orchestrator/handoff.go:19`〜`:26` — `LoadControl` がエラーなら `_ = h.Store.DeleteControl()` で**ファイルを削除**し `(nil, nil)` を返す。再試行はしない |
| 2 | **【解消済み(同上)】** `MODULE-orchestrator-streamlog.md` 戻り値・副作用 | 戻り値 = 「`io.Writer` の契約どおり書き込みバイト数とエラー」/ 永続化 = 「`workers/<taskID>.log` へ**追記**される」 | `orchestrator/streamlog.go:32`〜`:48` — `io.WriteString` のエラーを**すべて捨て**、常に `(len(p), nil)` を返す。`orchestrator/worker.go:396` は `os.Create(logPath)` を使うので**開始時にファイルを truncate する**(追記ではない) |

**2026-08-04 `/doc-check ssot task-impl-depth` の確認**: 上記2件はいずれも SSOT 側が実装の事実へ
訂正済みであることをコードで裏取りした(`MODULE-orchestrator-state-intervention.md` 異常系 =
「削除して『無い』と同じ扱い」/ `MODULE-orchestrator-streamlog.md` 戻り値 = 「常に `(len(p), nil)`」・
永続化 = 「`os.Create` で切り詰めて作り直される(追記ではない)」)。
したがって**本 issue に未解決の重大度「高」は無くなり、frontmatter の severity を「中」へ是正した。**
残件は下の中10件 / 低7件 + 中#6(裁定済み・記述修正のみ)である。

**#1 は同じ誤りが `MODULE-orchestrator-handoff.md` にもあり、そちらは `task-impl-depth` が
「実装が正」として訂正済み**である(進捗メモ 2026-08-03)。**同じ文が2本目にも書かれていることに
5回の反復を通じて誰も気づかなかった。**

### 記述が実装と違うもの(重大度「中」)

| # | 箇所 | ドキュメントの記述 | コードの事実 |
|---|---|---|---|
| 3 | `MODULE-orchestrator-streamlog.md` フロントマター | `callees: なし` | `orchestrator/streamlog.go:159,233` が `oneline` を呼ぶ。`oneline` は `orchestrator/dashboard.go:176` で定義され、`MODULE-orchestrator-dashboard` に属する = **モジュールを跨ぐ呼び出しが宣言されていない** |
| 4 | `MODULE-orchestrator-dashboard.md` 呼び出され方 | 引数は `state` のみ、戻り値「なし」 | `orchestrator/dashtui.go:55` — `newDashProgram(ctx, st, store, sessions, actions) *tea.Program`。`Init` は `tea.Cmd`、`Update` は `(tea.Model, tea.Cmd)`、`View` は `string` を返す |
| 5 | `MODULE-orchestrator-dashboard.md` 処理の流れ | executing のときに起動し、`View()` は**毎描画で** VM health を読む | `orchestrator/dashtui.go:69,145`〜`:152` — brainstorming でも同じ TUI が動き、その分岐は **health を読む前に画面を返す** |
| 6 | `MODULE-orchestrator-dashboard.md` 処理の流れ | controller が直近サマリと仮定件数も `DashboardState` に書き込む | `LastSummary` / `LastSummaryTS` / `AssumptionsN` / `InterventionsN` への**代入が製品コードに1件も無い**(`orchestrator/dashtui.go:233` は `s.LastSummary` を表示している) |
| 7 | `MODULE-orchestrator-main.md` 呼び出され方 | `--workspace` は**必須**で git ルートであること | `orchestrator/main.go:25` — 既定値は `defaultWorkspace()` なので必須ではなく、git ルートかの検証も無い |
| 8 | `MODULE-orchestrator-main.md` 処理の流れ | 設定読込 → Store 作成 → 残骸掃除 | `orchestrator/main.go:58,84` — `NewStore` が先で、掃除は `--fresh` のときだけ。`:135` の「goal があり plan が無いとき最小 `Plan` を保存する」副作用が本文に無い |
| 9 | `MODULE-orchestrator-plan.md` | 不存在の依存 ID は ready にならず永久に着手されない | `orchestrator/plan_test.go:42,56` — `Deps: []string{"missing"}` のタスクは **`blocked` へ遷移する**(failed 依存として扱われる) |
| 10 | `MODULE-orchestrator-state.md` 異常系 | archive の退避先が既存なら `os.Rename` が失敗する | `orchestrator/state.go:353`〜`:365` — `os.MkdirAll` を先に行い、既存ディレクトリを失敗扱いする分岐は無い |
| 11 | `MODULE-orchestrator-state-intervention.md` | `open.json` の項目は `{InterventionID, TaskID}` | `orchestrator/state.go:193`〜`:200` — `Intervention` の JSON フィールドは `id` / `task_id` / `trigger_reason` / `question` / `answer` / `ts`。また `LoadOpenInterventions` は**すべての読取・JSON エラーで空キューを返しエラーを返さない** |
| 12 | `MODULE-orchestrator-state-intervention.md` | `WriteAtomicSidecar` / `ReadAtomicSidecar` が `sessions/<key>.sys`・`.prompt` を扱う | 両メソッドは root 直下の任意名を扱う汎用。実際の `.sys` / `.prompt` / `.sh` は `Mode.WriteLaunchScript` が直接書き、`.sh` は `os.WriteFile` |
| 13 | `MODULE-orchestrator-streamlog.md` | 未知の種別はそのまま出す | `orchestrator/streamlog.go:88`〜`:95` — 有効 JSON の未知の外側イベントは `return ""` で**破棄**。本文に無い `system/init` と `result.is_error` の分岐がある |

### 記述が不足・不正確なもの(重大度「低」)

| # | 箇所 | 内容 |
|---|---|---|
| 14 | `MODULE-orchestrator-config.md` 処理の流れ 1 | 組込既定の列挙に `worker_model=sonnet` と `SlackChannel=DefaultSlackChannel` が無い(`orchestrator/config.go:52`〜`:63` は10項目、本文は8項目) |
| 15 | `MODULE-orchestrator-config.md` 処理の流れ 5 | 「非数値や **0 以下** など」と書くが、`worker_grace_seconds` だけは `n >= 0` で **0 を有効値として採る**(`orchestrator/config.go:112`〜`:114`)。「など」で一般化しているため誤読を招く |
| 16 | `MODULE-orchestrator-dashboard.md` | `actions` に本文に無い `intervene` 種別がある。`ctrl+c` も `q` と同じく quit(`orchestrator/dashtui.go:28,123,124`)。`send` はチャネル満杯時に `default` 節で操作を黙って捨てる |
| 17 | `MODULE-orchestrator-dashboard.md` 連携先 | 「タスク ID を渡して成否を受け取る」と書くが、`orchestrator/dashtui.go:113,115` は生成済み tmux target を `SwitchTo` へ渡し、**戻り値の error を `_ =` で捨てている** |
| 18 | `MODULE-orchestrator-main.md` | 起動時の判定結果を標準エラーへ出すと書くが、`orchestrator/main.go` に `os.Stderr` への書き込みは **0 件**で、7 箇所すべて `fmt.Println` / `fmt.Printf`(標準出力) |
| 19 | `MODULE-orchestrator-plan.md` | `NormalizeForResume` は running/review/revise のみを pending に戻すと書くが、`orchestrator/controller.go:1402`〜`:1414` は**空文字の Status も pending に正規化する** |
| 20 | `MODULE-orchestrator-state.md` | `NewStore` が workspace の絶対パス制約を保証すると読めるが、`orchestrator/state.go:232`〜`:234` は `filepath.Join` するだけで絶対化も相対パス拒否もしない(`issue 011` と同種) |

## 影響

`docs/03-impl/index.md` は relations 層の**代表として版と合格証を持つ**(CLAUDE.md 不変則6)。
上記のうち #1・#2 は**観測可能な振る舞いの相違**であり、
「ドキュメントだけから再実装・再試験できる」という `issue 004` の目標に対して、
再実装すると**別の振る舞いになる**。とくに #2 の「追記」は、再起動時にログが消えるか残るかという
運用上の違いになる。

したがって未解決の重大度「高」が2件あり、`/doc-check` の PASS 条件を満たさない。
2026-08-03 の `/doc-check ssot` は **`docs/03-impl/index.md` の `verified` ブロックを削除**した。
これは `close-task.py` のゲート (b)(影響範囲の全 SSOT の合格証が有効であること)に効くため、
**`task-impl-depth` はこの2件が裁定されるまで閉じられない**。

## 原因の見当

7本は `/relations --apply --bootstrap` がコールグラフから起こしたもので、
その後**本文の散文だけを人間・AI が読み合わせる機会が無かった**という**推測**。
機械検査(`check-relations.py` / `callgraph-check.py` / `check-contracts.py`)は
フロントマターと呼び出し関係しか見ないため、散文の乖離は構造的に検出できない
(`.claude/directions/relations.md` §6 の限界)。`issue 009` が同じ層の
**関数シグネチャ**について同じ性質の乖離を記録している。

## 正はどちらか

**20件すべて実装が正である可能性が高いが、CLAUDE.md 原則2 により `/doc-check` は判定しない。**
とくに次の2つは人間の判断が要る。

- **#2 のログ追記**: `os.Create` による truncate が意図なのか、追記が本来の設計意図で実装が誤りなのか。
  `MODULE-orchestrator-dashboard` の tail 表示がこの書式を読むので、**設計が正なら実装のバグ**である。
- **#6 の `LastSummary` 系**: 表示用フィールドが製品コードから一度も書かれていない。
  ドキュメントの記述が正なら**実装の欠落**であり、ダッシュボードに常に空欄が出ている。

残る18件は「実装が正・ドキュメントの記述誤り」で説明できるが、**要確認**。

## 対処案

| 案 | 内容 |
|---|---|
| A | `task-impl-depth` の影響範囲を7本へ拡張し、この下降の中で20件を実装の事実へ揃える(`/doc-check` の「フェーズをまたいで往復しない」に沿う)。ただし当該タスクは既にフェーズ2を1回下降し終えており、7本 × 20件は小さくない |
| B | 20件を別タスクとして切る(`/task-new 032`)。`task-impl-depth` は #1・#2 の**2件だけ**を取り込んで閉じ、`docs/03-impl/index.md` を再認証できる状態にする |
| C | `issue 004` の残件として束ね、`03-impl/relations/` の**残り63本すべて**を独立監査に掛けてから、まとめて1タスクにする(今回の7本で20件出たので、63本では相当数が見込まれる) |

**B が最小で、A は往復を避ける原則に沿い、C は網羅性を取る。** #2 と #6 の「正はどちらか」は
どの案でも先に人間が答える必要がある(実装のバグかもしれないため)。

## 裁定の記録(2026-08-03)

**人間の裁定**(`task-impl-depth` の質問キュー #10〜#11):

| 対象 | 裁定 | 扱い |
|---|---|---|
| 高#1 `MODULE-orchestrator-state-intervention`(壊れた `control.json`) | **実装が正** | `task-impl-depth` の変更指示に取り込み、**本タスクで解消**(`/task-close` で削除する) |
| 高#2 `MODULE-orchestrator-streamlog`(戻り値と「追記」) | **実装が正** | 同上 |
| 中#6 `LastSummary` / `AssumptionsN` / `InterventionsN` が未代入 | **記述を直すだけ**(実装の欠落としては追わない) | 03 を実装に合わせる。**本 issue に残す**(修正は別タスク) |
| 残り(中10件 / 低7件) | 未裁定 | **本 issue に残す。別タスクで扱う** |

したがって**本 issue は閉じない**。`task-impl-depth` の `/task-close` 後は「高2件を除く18件」が
残件になる(高2件の行に「解消済み(task-impl-depth)」と印を付けること)。

