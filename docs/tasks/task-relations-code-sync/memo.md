---
id: task-relations-code-sync
phase: 決定
origin_layer: 03
issue: docs/issues/038-modify-closure-relations-still-diverge-from-code.md
date: 2026-08-04
updated: 2026-08-04
source:
  - docs/02-design/contracts/orchestrator-prompt.md
  - docs/03-impl/contracts/cli-container.md
  - docs/03-impl/contracts/orchestrator-prompt.md
  - docs/03-impl/tests/orchestrator.md
  - docs/03-impl/index.md
summary: relations の記述をコードへ全面追随させる(issue 038 の残27件 + 032 の17件 + 019 の残1件)
---

<!-- タスクの背骨。フェーズ1で作られフェーズ4で削除されるまで、このファイルだけで
     どのフェーズからでも再開できること(/clear を挟んでも)。
     ・仕様ドキュメントではない(version / verified を持たない)
     ・未決点はここに置く。仕様ドキュメントには絶対に書かない
     ・削除は /task-close の機械ゲート経由(close-task.py)。rm 禁止 -->

# task-relations-code-sync relations の記述をコードへ全面追随させる

> 解決済みの経緯: (まだ無し)

## 実行順(★重要)

**3本連続タスクの2本目。着手は `task-fix-destructive-scope`(1本目)を閉じた後。**
1本目が `MODULE-cli-start` / `-stop` / `-reset` / `-logout` と
`03-impl/contracts/cli-container.md` / `03-impl/index.md` を動かすため、
**先に本タスクを回すと同じファイルを二度直すことになる**(重なりの実測は1本目の memo)。

**着手時にやること**: 1本目の反映で SSOT が動いているので、**`issue 038` / `032` の残件表を
コードと突き合わせ直してから** closure を確定する(CLAUDE.md「先に閉じた方が SSOT を動かす」)。
1本目が cli 系4本を実態へ書き直すため、**038 の cli 系の残件は消えている可能性が高い**。

## 目的

**CLAUDE.md 原則2(コード ⇄ 03-impl の完全一致)の侵害を解消する。** relations の本文が
コードと食い違う箇所が確定分で **45 件**ある。

| issue | 残件 | 対象 |
|---|---|---|
| `038` | **中20件 / 低7件**(表 #7〜#32) | `task-impl-depth` が掘り下げた21本のうち、変更指示の `sections` に入っていなかった節(`## 処理の流れ` / `## 連携先と連携内容` / `## 戻り値・副作用` と frontmatter の `callers` / `callees`) |
| `032` | **中10件 / 低7件**(+ 裁定済みの中#6) | 影響範囲外だった orchestrator 7本(`-streamlog` / `-state-intervention` / `-dashboard` / `-main` / `-plan` / `-state` / `-config`) |
| `019` | **残1件** | `tests/orchestrator.md:57`・`:110` の `TestReadyTasks_Basic`(実在しないテスト識別子) |
| `038` #6 | 1件 | `02-design/contracts/orchestrator-prompt.md` が「必須」の意味(検証失敗か既定値補完か)を書いていない ← **02 起点** |

起点層は **03**(記述の誤り)。ただし `038` #6 だけは **02 起点**なので同じ下降で直す。

## やること・やらないこと

| 種別 | 内容 |
|---|---|
| やること | `038` の残27件と `032` の17件を**コードで裏取りして記述を直す**(実装は変えない)/ `019` の残1件を実名へ / `038` #6 で 02 の契約に「必須だが検証しない」を明記 / `03-impl/contracts/cli-container.md` の「設計との差異」を実態へ / `03-impl/index.md` の集計を更新 |
| やらないこと | **コードの変更**(記述をコードへ合わせるタスク。実装の誤りが見つかったら issue 起票のみ)/ **`issue 009` (a) の17件**(`ctx` 省略の規約が未決 = `/kit-improve` 案件。論点2)/ 測定不能語と NFR の測定可能性(3本目)/ 1本目が触る cli 系4本の**新規の記述変更** |

## 影響範囲(closure)

<!-- ★着手時に 038 / 032 の残件表をコードと突き合わせ直して確定する。
     下表は 2026-08-04 時点の見込みである。frontmatter の source: も着手時に更新する。 -->

| 層 | SSOT のパス | 変更指示のパス | 変更の種類 |
|---|---|---|---|
| 02 | docs/02-design/contracts/orchestrator-prompt.md | new-features/02-design/contracts/orchestrator-prompt.md | replace(`038` #6。「必須」の意味を明記) |
| 03 | docs/03-impl/relations/MODULE-orchestrator-*.md(**14本前後**) | new-features/… | replace(`038` の残件 + `032` の17件。`-controller` / `-review` / `-term` / `-session` / `-worker` / `-mode` / `-slack` / `-claude-exec` / `-handoff` / `-worktree` / `-trigger` / `-streamlog` / `-state-intervention` / `-dashboard` / `-main` / `-plan` / `-state` / `-config` のうち残件があるもの) |
| 03 | docs/03-impl/relations/MODULE-cli-*.md | - | **★着手時に判定**(1本目が実態へ直すので残件が消えている見込み。残っていれば closure へ追加) |
| 03 | docs/03-impl/relations/MODULE-docker-proxy-serve.md | - | **★着手時に判定**(`038` の表に登場するが `docs/issues/005` と重なる) |
| 03 | docs/03-impl/contracts/cli-container.md | new-features/03-impl/contracts/cli-container.md | replace(「設計との差異」を実態へ。`038` の追加分) |
| 03 | docs/03-impl/contracts/orchestrator-prompt.md | new-features/03-impl/contracts/orchestrator-prompt.md | replace(02 側の明記に対応する 03 の実値) |
| 03 | docs/03-impl/tests/orchestrator.md | new-features/03-impl/tests/orchestrator.md | replace(`019` の残1件を実名へ) |
| 03 | docs/03-impl/index.md | new-features/03-impl/index.md | replace(「コードとの乖離として未解決のもの」から 038 / 032 / 019 を外す) |
| 01 | docs/01-requirements/ 全ファイル | - | 変更なし(理由: 要件は変わらない。記述をコードへ合わせるだけ) |
| 00 | docs/00-requests/ 全ファイル | - | 変更なし(理由: 決定・委任・受入基準は変わらない) |

## 決定シート(提示中 — 未回答)

| # | 論点 | 選択肢 | 推奨案(理由・下流の代償・崩れる条件) | 未回答時の既定 | 根拠 |
|---|---|---|---|---|---|
| 1 | **`038` #6(`CTR-orchestrator-prompt` の「必須」の意味)** | **A**: 02 に「**必須だが検証はしない**(欠落は Go のゼロ値になる)」と明記(= 03 とコードが正)/ **B**: 欠落を検証エラーにする(**コード変更**)/ **C**: 「必須」を「期待するフィールド」に言い換える | **A**。`D0-orch-15` は 2026-08-04 に「**スキーマ強制はツールで行わない**」へ改まっており、検証しないことが**決定済みの方針**である。B はその決定に反する。**下流の代償**: 「必須」が「検証されない期待」を意味するので読み手に注意が要る(明記で解消)。**崩れる条件**: 将来スキーマ強制を導入するなら 00 の `D0-orch-15` から改める | **A** | 上流: `D0-orch-15`(★2026-08-04 改め)/ `FR-orch-06` #3 同層: `CTR-cli-container` は環境変数について「受け側は値の不正で起動を止めない」と同型の明記を持つ 下流: `03-impl/contracts/orchestrator-prompt.md` / `MODULE-orchestrator-review` |
| 2 | **`issue 009` (a) の17件(`ctx` 省略の規約)を含めるか** | **A**: 含めない(`/kit-improve` で規約を決めてから別途)/ **B**: 規約なしで17件を機械的に補う / **C**: 規約の策定も本タスクでやる | **A**。規約は**キットの話**で書き込み先が違う(`/kit-improve` は `docs/` を触らない)。**下流の代償**: 17件が残り、`03-impl/index.md` に未解決として書き続ける。**崩れる条件**: 規約が「省略してはならない」に決まると17件は本タスクと同種の作業になる → **その場合は本タスクの着手前に `/kit-improve` を回す**のが得 | **A** | 上流: CLAUDE.md §6 / `docs/issues/009` の対処案 A 同層: `task-impl-depth` も (a) を範囲外にした 下流: `03-impl/index.md` の「コードとの乖離」欄 |
| 3 | **`032` の「低」7件も直すか** | **A**: 中・低すべて直す / **B**: 中10件だけ | **A**。同じファイルを開くので**二度触らない方が安い**。低7件は表記ゆれ・語の精度で判断に迷いが無い。**下流の代償**: 変更行数と照合対象が増える。**崩れる条件**: 低7件のどれかが「実装が誤り」だった場合は issue 起票に回す(記述を実装へ合わせてはならない) | **A** | 上流: CLAUDE.md 原則2 同層: `task-impl-depth` が高5件だけ先に直して中低27件を残し、**その結果が本タスク**である(分けた代償が既に出ている) 下流: `03-impl/index.md` |
| 4 | **実装が誤っていた場合の扱い** | **A**: issue を起票して**記述はコードのまま**にし、コードは変えない / **B**: 軽微ならその場で直す | **A**。本タスクでコードを変えると「何が正だったか」の記録が混ざる。**下流の代償**: 実装の欠陥が残る(issue で追跡)。**崩れる条件**: 明らかな要件違反で修正が数行なら判断を仰ぐ(→ 決定シート) | **A** | 上流: CLAUDE.md 原則2「どちらが正かを勝手に決めない」/ 原則8 同層: `task-impl-depth` は同方針で19件を起票した 下流: `docs/issues/` |

### 委任にしてよいか確認したい項目

| # | 論点 | 委任範囲 | 制約(ガードレール) |
|---|---|---|---|
| a | 各食い違いを「記述の誤り」と判定してよい範囲 | `038` / `032` の各行について、コードを読んで**コードが正**と確認できたものは記述を直す | **コードから一意に読み取れる事実だけを書く**(`D0-scope-07` と同じ制約)。要件・契約・観測可能な振る舞いに関わる食い違いは委任範囲外(→ issue または決定シート)。**推測を仕様として書かない** |

## 未決点

| # | 未決点 | 帰着 | 検出元 |
|---|---|---|---|
| (フェーズ2 の実装ドライランで埋める) | | | |

## 調査メモ

- `docs/issues/038` の表 #7〜#32 と `docs/issues/032` の表が**行単位の作業リスト**になっている
  (各行に「ドキュメントの記述」と「コードの事実」が `path:line` 付きで併記されている)。
- 2026-08-04 に実測した例(**未修正のまま残っている**): `MODULE-orchestrator-term.md:48`,`:61` は
  `selectMenu` の引数を「`options` = 文字列の並び」、`rawKeyMode` / `ttyRestoreSane` / `sttyRun` を
  「エラーを返す」と書くが、実コードは `orchestrator/term.go:96`(`items []menuItem`)/
  `:34`(`(func(), bool)`)/ `:44`(戻り値なし)/ `:48`(`bool`)である。
- **高5件(`038` の #1〜#5)は `task-impl-depth` で解消済み**(2026-08-04 にコードで再確認)。
- `check-relations.py` は**合格**している(対称性・参照実在・必須項目)。食い違いは**本文の叙述**に
  集中しており、機械検査では捕まらない種類である。

## 質問キュー(未提示)

| # | 質問 | 前提 | いつ聞くか |
|---|---|---|---|
| (なし) | | | |

## タスクリスト

- [ ] 0. **着手時**: `038` / `032` の残件表をコードと突き合わせ直し、1本目の反映で消えた行を除いて closure を確定する
- [ ] 1. `/task-doc task-relations-code-sync`(02→03 の1回の下降) _Depends:_ 0, 決定シートの回答
- [ ] 2. `/doc-check task-relations-code-sync` が PASS _Depends:_ 1
- [ ] 3. `/implement task-relations-code-sync`(**コードは変えない**。記述のみ) _Depends:_ 2
- [ ] 4. `/task-close task-relations-code-sync` _Depends:_ 3

## Definition of Done

- [ ] (フェーズ2/3 が具体化する。最低限: `038` / `032` / `019` を削除できる状態 / `callgraph-check` 高0 / `check-relations` 合格 / **コード差分が空**)

## 進捗メモ

- 2026-08-04 フェーズ1。`issue 038` を起点に `032` / `019` を同時対象として宣言。
  3本連続タスクの2本目(1本目 `task-fix-destructive-scope` の完了後に着手)。
  決定シート4論点 + 委任1件を提示。

## 申し送り事項

- **着手前に判断が要ること**: 決定シート論点2 で「規約を先に決める」を選ぶ場合は、
  **本タスクの前に `/kit-improve`** を回して `.claude/directions/relations.md` に
  `ctx` 省略の規約を書く(そうすれば `issue 009` (a) の17件も本タスクで閉じられる)。
- 3本目 `task-spec-measurability` は本タスクの後。重なりは `03-impl/index.md` のみ。
- **2026-08-10 19:52 以降に `/doc-check full`** を新しいセッションで1回(前タスクからの申し送り)。

## 前タスクからの申し送り(task-fix-destructive-scope フェーズ4 で転記。2026-08-04)

- **`task-fix-destructive-scope` は完了した。** SSOT が動いたので、**本タスクの変更指示を
  新しい SSOT に対して読み直すこと**(`/doc-check` が失効を検出する)。
  とくに次のファイルが動いた: `03-impl/contracts/cli-container.md`(1.3.0 → 1.4.0。
  実装上の事実を全面的に取り直し、7行追加)/ `03-impl/index.md`(1.8.0 → 1.9.0。
  本数 82 → 83、起票済み 16 → 15 件)/ `MODULE-cli-start` / `-stop` / `-reset` / `-logout`
  (戻り値・副作用 / 異常系 / 既知の制限 / 並行性 を全面的に書き替えた)/
  `03-impl/features.md`(`MODULE-cli-common-lock` を追加して 83 機能)。
- **`docs/issues/038` / `032` の relations 乖離**は本タスク(2本目)の担当のまま。
  ただし **`MODULE-cli-start` / `-stop` / `-logout` / `-reset` / `-login` / `-login-codex` の
  6本は 1本目が実装から書き直したので、乖離の件数を数え直すこと**(1本目が閉じた分がある)。
