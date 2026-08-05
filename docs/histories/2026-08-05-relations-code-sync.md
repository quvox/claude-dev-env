---
id: 2026-08-05-relations-code-sync
date: 2026-08-05
task: task-relations-code-sync
origin_layer: 03
issue: docs/issues/038-modify-closure-relations-still-diverge-from-code.md
summary: relations の記述をコードへ全面追随させた(実質50件)。コードは1行も変えていない
---

<!-- タスクごとに1ファイル。追記のみ(確定したエントリの文章は書き換えない)。
     タスク・進捗・TODO は書かない(それは memo.md の仕事だった)。 -->

# 2026-08-05 relations の記述をコードへ全面追随させる

## 変更理由

**CLAUDE.md 原則2(コード ⇄ 03-impl の完全一致)の侵害を解消するため。**
`docs/issues/038` / `032` / `019` / `005` / `017` / `056` が挙げていた「relations の本文が
コードと食い違う箇所」が、2026-08-05 の再突き合わせで**実質 50 件**残っていた。

起点層は **03**(記述の誤り)。ただし2つだけ **02 起点**の項目が混ざっており、
CLAUDE.md §3「フェーズをまたいで往復しない」に従って同じ下降で直した:

- `038` 追加#6 — `02-design/contracts/orchestrator-prompt.md` が「必須」の意味
  (検証失敗か既定値補完か)を書いていなかった(`D0-orch-15` の 2026-08-04 改めを 02 へ書き下す)。
- `056` #7・#8 — 02 に残る変更相対の言い回し。

**このタスクはコードを変えない。** 記述をコードへ合わせるのが目的で、実装の誤りが見つかった場合は
issue 起票のみとした(フェーズ1 の決定シート論点4 = 案A)。

## 変更内容の要約

- **relations 21本・contracts 2本・tests 1本・features・index・01 の受入基準1行**を、
  すべて**コードで裏取りして**実装の事実へ揃えた(変更指示30ファイル)。
- **変更相対の言い回しを SSOT から一掃した。** 実測は当初の見積もり(8箇所)より多く
  **44 行 / 16 ファイル**で、うち **25 件を修正**、**19 件は正当**として残した
  (コードが実際に出力する文面の引用・日付で固定された決定の改訂記録・却下した案の記録)。
- **未修正のコード欠陥2件を新しい issue へ切り出した**(`038` を削除すると追跡先を失うため)。
- `019` の「実在しないテスト識別子」を実名へ、または「未検証(テスト未実装)」へ落とした。
- **コード差分はゼロ**。`build-callgraphs.py` が「書き換え: なし(既に最新)」を返したことが
  機械的な裏付けである。

## 更新したドキュメント

| ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|
| docs/00-requests/decisions/orch.md | 1.2.0 → 1.2.1 | `D0-orch-15` の「形式の検証が一箇所も無い」の追跡先を、実在しない `034` と削除する `038` から `058` / `059` へ改め、「形式の検証と採点基準の双方」と正確に言い直した(**層00。人間の合意を得て編集**) |
| docs/01-requirements/functional.md | 1.5.0 → 1.5.1 | `FR-env-01` 受入基準15 の「本変更より前に起動した既存コンテナ」を「管理ラベルが付く前に起動されたコンテナなど」へ(観測できる性質で言い直す) |
| docs/02-design/system.md | 2.2.0 → 2.2.1 | `#### SCR-01` の `stop` の受理文字集合の注記から「本変更で制約を変えない」を除き、`### DSN-mod-05` の「本タスクの範囲外」を「このキットの範囲外」へ |
| docs/02-design/contracts/cli-container.md | 1.4.1 → 1.4.2 | 一意化名の説明3箇所を、導入前を基準にした表現から**観測できる性質**(「古い名前を持つ compose 資源が既存環境に残っている場合」)へ |
| docs/02-design/contracts/orchestrator-prompt.md | 1.2.0 → **1.3.0** | 「必須」の意味を**新たに規定**した: 欠けていても検証失敗にはせず Go のゼロ値で埋める。根拠は `D0-orch-15`(スキーマ強制はツールでは行わない) |
| docs/03-impl/contracts/cli-container.md | 1.5.0 → 1.5.1 | 既知の制限の「本変更より前に起動した資源」を「管理ラベルも一意化された compose 名も持たない資源が既存環境に残っている」へ |
| docs/03-impl/contracts/orchestrator-prompt.md | 1.1.0(据え置き) | 本文は変えず、上流が MINOR で上がったため**合格証を再発行**(against 1.2.0 → 1.3.0) |
| docs/03-impl/tests/orchestrator.md | 1.1.1 → **1.4.1** | 実在しない `TestReadyTasks_Basic` を排除(`FR-orch-05` 受入基準2 は「未検証」へ、`MODULE-orchestrator-plan` は実在する3件へ)。`CTR-cli-orchestrator` の行を追加。**人間の裁定 #1 = B により `FR-orch-06` 受入基準2 を「実装済み」→「未検証(テスト未実装)」へ**(1.3.0 → 1.4.0)。状態セルの太字を語彙どおりに戻して索引の数え落としを解消(1.4.0 → 1.4.1) |
| docs/03-impl/index.md | 1.11.0 → **1.13.1** | `019` / `032` / `038` を「コードとの乖離として未解決のもの」から外した。「実装の欠陥として起票済み」を 15 → **18 件**(`005` が「既知の制限」から参照されるようになった分 +1、切り出した `057` / `058` で +2)。「01(要件)との差異」に2行を追加 |
| docs/03-impl/features.md | 層として index.md が認証 | 「到達しない関数についての判断」から「本タスクでは直さない」を除いた |
| docs/03-impl/relations/MODULE-*.md(21本) | 層として index.md が認証 | 下の「機能間連携仕様書の変化」を見る |

## 実装したもの

| 対象 | 内容 | コミット |
|---|---|---|
| **なし(コード差分ゼロ)** | 本タスクは記述をコードへ合わせるもので、実装は1行も変えていない。`orchestrator/` `docker-proxy/` `scripts/` `claude-dev` `claude-dev-mac` に変更なし | — |
| 検証 | lint(`go vet ./...` 両モジュール)・テスト(`go test ./...` / `go test -mod=vendor ./...`)がグリーン。`callgraph-check.py` の重大度「高」0 件、`check-relations.py` / `check-contracts.py` / `check-changeset.py`(I1〜I10)すべて合格 | `100075f` |

## 機能間連携仕様書の変化

| 種別 | ID | 内容 |
|---|---|---|
| 変更(`callers` / `callees`) | MODULE-orchestrator-controller | `callees` に `MODULE-orchestrator-slack` を追加。**インターフェース越し**(`Notifier` = `worker.go:77`)なので静的コールグラフに辺が出ず、本文に呼び出し位置7箇所(`controller.go:323`/`:454`/`:741`/`:1038`/`:1050`/`:1053`/`:1090`)を根拠として書いた |
| 変更(`callers`) | MODULE-orchestrator-slack | `callers` に `MODULE-orchestrator-controller` を追加(対称) |
| 変更(`callers`) | MODULE-orchestrator-claude-exec | `callers` に `-worker` と `-review` を追加。同じくインターフェース越し(`ClaudeRunner` = `worker.go:48`〜`:51`、実体 `worker.go:350`) |
| 変更(本文) | MODULE-orchestrator-review | 戻り値を `(GateOutcome, error)` と確定。`error` が非 `nil` になるのは context キャンセルのみ。`{"findings":null}` は nil スライスとして復号でき**ゲートを通過する**。再整形は「内容を変えない」ことをコードでは保証しない。レビュアログは `workers/<taskID>.review.log` |
| 変更(本文) | MODULE-orchestrator-term | `selectMenu` の引数は `items []menuItem`、`rawKeyMode` は `(func(), bool)`、`ttyRestoreSane` は戻り値なし、`sttyRun` は `bool`。バナーは stderr・メニュー本体は stdout |
| 変更(本文) | MODULE-orchestrator-worker | `Dispatch(ctx, p, t, feedback)` の引数表。`ExecGit.run` の出力を捨てる箇所。`HasCommits` は製品コードから呼ばれない |
| 変更(本文) | MODULE-orchestrator-state-intervention | `OpenIntervention` と `Intervention` は**別型**。サイドカーの製品用途は `handoff_note.md` だけ。壊れた `open.json` で判断待ちキューが失われる事実を異常系へ |
| 変更(本文) | MODULE-orchestrator-streamlog / -dashboard / -main / -plan / -state / -config / -session / -worktree / -mode / -trigger | 未知の `type` の破棄、`actions` チャネルの満杯時の破棄、`--workspace` の既定、不存在の依存 ID も `blocked` にする、`ArchiveRun` の退避、既定10項目と `worker_grace_seconds` の 0、`remain-on-exit on`、git の stderr、`ResolveArgsOne` が呼ばれない、`TriggerContext` の項目 — いずれもコードの事実へ |
| 変更(本文) | MODULE-cli-start | entrypoint の副作用の参照を明示。「### 並行性」の表の**2行が同じ入力で相反していた**のを、ロックキーをコードで裏取り(`claude-dev:245`〜`:251` / `:396`〜`:401`)して限定を足した |
| 変更(本文) | MODULE-docker-proxy-serve | 既知の制限に「解釈できないリクエストボディは検査せず中継する」を追加(`docs/issues/005` の対処案1) |
| 変更(本文) | MODULE-cli-reset / -stop / -logout | 変更相対の言い回しを除去。**`MODULE-cli-reset` の2箇所は現行実装について事実と異なっていた**(終了コード) |
| 追加なし / 削除なし | — | 機能の増減は無い(FT2 = 機能表に無いエントリポイント 0 件) |

**コールグラフとの突き合わせで棄却したもの**: CG4 の確度「候補」**7辺**
(`claude-exec` / `mode` / `session` / `term` → `controller` / `session`)は全件棄却した。
すべて `exec.Cmd.Run()` の呼び出しが `Controller.Run` / `SessionManager.Run` と**同名衝突**した
候補辺であり、実在する経路ではない(`term.go:54` / `session.go:119` ほか)。

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 新規 issue | docs/issues/056 | SSOT に残る変更相対の言い回し。**閉じない**: SSOT 側は全件解消したが、**コードが出力する文言そのものが変更相対**(`claude-dev:1091`/`:1669`/`:2110`)という残件がある |
| 新規 issue | docs/issues/057 | 壊れた `intervention/open.json` で判断待ちキューが黙って失われる(`FR-orch-05` 受入基準7 違反)。`038` から切り出した |
| 新規 issue | docs/issues/058 | 未知の `severity` が「重大でない」扱いで品質ゲートを通過する。`038` から切り出した |
| 新規 issue | docs/issues/059 | `FR-orch-06` 受入基準2 を覆うテストが実在しないのに「実装済み」だった。**人間が案B(テストを書く)で裁定**し、コードを触る別タスクで閉じる |
| 気づき | docs/feedbacks/020 | 静的コールグラフはインターフェース越しの呼び出しを見られない。CG3「低(実装前)」= interface dispatch / CG4「候補」= 同名衝突。見分ける順序を残した |
| キット案件 | .claude/improvements/KIT-nested-section-reflection-and-callee-body-check.md | 変更指示の `sections:` に親子の見出しを併記すると反映が**二重挿入**する(今回2件)。`callees` ⇄ 本文の `### 節` に 1:1 検査が無い(今回4件が独立レンズ頼み) |
| キット案件 | .claude/improvements/KIT-audit-scope-budget-and-change-relative-vocabulary.md | 1本の監査に載せる対象の上限(30ファイル / relations は1本1監査)。変更相対語の走査語彙。テンプレートの「閉じる予定」列と §1 の緊張 |
| 解消した issue | docs/issues/019(削除) | `tests/orchestrator.md` が実在しないテスト識別子を挙げていた8件。7件は 2026-08-04 に、残る `TestReadyTasks_Basic` を本タスクで解消 |
| 解消した issue | docs/issues/032(削除) | 影響範囲外だった orchestrator 7本がコードと20箇所で食い違っていた |
| 解消した issue | docs/issues/038(削除) | 影響範囲内の relations 21本が反映後もコードと食い違っていた。**未修正のコード欠陥2件は `057` / `058` へ切り出して追跡を継続** |
| 開いたまま | docs/issues/001 / 004 / 005 / 017 / 054 / 056 | `001` は到達不能シンボルの追記のみ、`005` は実装と `AC-03` の例外明記が残る、`017` は relations 分が**空振り**(3行とも既に解消済みだった)、`054` は参照表記の規約がキット案件、`056` は上記のとおり |

**独立レンズ**: フェーズ2 で Codex 3本(`readiness` / `docs` / 再監査)、フェーズ4 の1回目の認証で
Codex 6本中5本が成功した(`relations` 一括監査のみ 900 秒でタイムアウト)。
**2回目の認証(§6 の回答適用後)ではアカウント利用上限により1本も立たず**、
不変則7 に従い**サブエージェントによる代替は行っていない**。
relations 83本のうち独立にコードと全文照合できたのは **1本**(`MODULE-orchestrator-review`)だけで、
そこから 11 件の乖離が出た。**2026-08-10 以降の `/doc-check full` が本来のマイルストーン保証の場**である。
