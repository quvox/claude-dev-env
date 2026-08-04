---
id: 2026-08-04-doc-check-ssot-unrecorded-00-edit
date: 2026-08-04
task: task-impl-depth
origin_layer: 00
issue: docs/issues/017, docs/issues/019, docs/issues/044
summary: 前回の全面再認証の後に記録の無い編集が4ファイルへ入り2件の合格証が失効していた。03-impl/index.md は事実照合のうえ 1.7.0 で再認証し、00 層の terminology.md は内容が正しいまま「承認の記録が無い」ため合格証を発行せず issue 044 として人間の裁定に上げた
---

<!-- タスクごとに1ファイル。追記のみ(確定したエントリの文章は書き換えない)。
     タスク・進捗・TODO は書かない(それは memo.md の仕事だった)。 -->

# 2026-08-04 記録の無い 00 層の編集と、失効していた2件の再認証

## 変更理由

`/doc-check ssot task-impl-depth` を本日3本目の実行として走らせた。直前の実行は
「版を持つ仕様ドキュメント 64 件すべてに有効な合格証が揃った」で終わっていたが、
**その後に histories にも `memo.md` の進捗メモにも記録の無い編集が 4 ファイルへ入っており、
うち 2 件の合格証が MAJOR.MINOR 不一致で失効していた**。

| ドキュメント | version 遷移 | 合格証 | 記録 |
|---|---|---|---|
| docs/00-requests/terminology.md | 1.0.0 → **1.1.0** | 1.0.0 のまま = **失効** | 無し |
| docs/01-requirements/non-functional.md | 1.2.0 → 1.2.1 | 1.2.0(PATCH なので有効) | 無し |
| docs/01-requirements/functional.md | 1.3.1 → 1.3.2 | 1.3.1(PATCH なので有効) | 無し |
| docs/03-impl/index.md | 1.5.0 → **1.6.0** | 1.5.0 のまま = **失効** | 無し |

4 件はすべて同じ起点を持つ。`terminology.md` に用語 **「資源逼迫」** の閾値付きの定義
(CPU 使用率が割り当て上限比 60% 以上の状態が 15 秒周期で 12 回連続)が追加され、
`non-functional.md`(`NFR-ops-01` の要件列)と `functional.md`(先頭コメント)がその定義を
指す文に書き換わっていた。

## 変更内容の要約

- **独立監査は1本も成立しなかった。** `codex exec` を1本試したところ
  `ERROR: You've hit your usage limit`(復旧予定 2026-08-10 19:52)で、環境要因が明らかなので
  再試行していない。CLAUDE.md 不変則7 により**代替のサブエージェントは無断で立てていない**
  (`/codex-audit` §5 の `ssot` 増分の fail ポリシー = 警告して続行)。
  **したがって本実行の合格証も Claude 単独の検証に基づく。**
- **`docs/00-requests/terminology.md` には合格証を発行せず、失効した verified ブロックを削除した。**
  判断の根拠は内容ではなく**手続き**である。
  - **内容は正しい**: 閾値 15 / 60 / 12 は `scripts/vm-healthd.sh:28`〜`:30` の既定値
    (`VM_HEALTH_INTERVAL` / `VM_HEALTH_CPU_PCT` / `VM_HEALTH_SUSTAIN`、コメントに `12×15s≒3分`)と
    一致し、認証済みの `docs/03-impl/relations/MODULE-vm-mode-healthd.md`(処理の流れ 2〜4・引数表)
    の記述とも一致する。
  - **しかし承認の記録が無い**: `.claude/directions/00-requests.md` は「この層は人間のもの。
    00 への意味のある変更はすべて人間の合意が要る」と定める。用語集は全層が従う規範であり、
    そこに閾値を書くことは意味のある変更である。
  - **かつ未回答の論点を先取りしている**: `task-impl-depth` の決定シート論点6(未回答)は
    `docs/issues/017` / `041` / `043` の閉じ方を人間に問うており、「資源逼迫」に定義を与えることは
    その答えの一部である。`D0-scope-06`(要件に関わる食い違いは委任外)/ `D0-scope-07`
    (範囲は `03-impl/relations/` と `contracts/` だけ)のどちらの委任にも入らない。
  - → **`docs/issues/044` を起票**し、対処案 A(承認)/ B(差し戻し)/ C(用語は 00・数値は 02)を
    決定シートへ上げた。**差し戻しはしていない**(内容が正しいものを `/doc-check` の判断で消すのは
    それ自体が意味の決定になる)。
  - この1件は `task-impl-depth` の影響範囲(closure)に入っていないため、
    `close-task.py` のゲート (b) はブロックしない。
- **`docs/03-impl/index.md` は本文の主張を1項目ずつ機械照合したうえで 1.7.0 で再認証した。**
  照合で古かったのは **1 箇所だけ**で、`issue 019` の残件数が「8件」のままだった。
  実際は 7 件が実名へ置換済みで、残るのは `TestReadyTasks_Basic`(`tests/orchestrator.md:57`・`:110`
  の2箇所)だけである。`docs/03-impl/` 全体を語境界付きで走査して旧名の残存 0 を確認した。
  `docs/issues/019` の frontmatter `summary` も同じ理由で古かったので訂正した。
- **`docs/issues/017` に 03 側の 2 箇所を追加した。** どちらも 02 側の同型の行は既に記録済みで、
  **下降の片側だけが記録されていた**もの: `MODULE-makefile-update-claude.md:14` の「高速更新」
  (02 は `relations.md:91` を記録済み)と `MODULE-vm-mode-healthd.md:21`,`:89` の「RAM 逼迫」
  (`terminology.md` が定義したのは `資源逼迫` で、`RAM 逼迫` は定義の無い別概念)。
  「資源逼迫」7箇所は **`issue 044` の裁定が出るまで本 issue から外さない**と明記した。
- **機械検査は全合格**: `build-callgraphs --check` 最新 / `cluster-features --check` 最新 /
  `callgraph-check` **高0**・中3・低17・参考20 / `check-contracts` 合格 /
  `check-relations` 合格(82/82)/ `build-index --check` 差分なし(`docs/issues/index.md` のみ再生成)。
  受入基準カバレッジ **180 = 180**(欠落0・余剰0・重複0)、NFR 15/15。
  02⇄03 は PLAN 63・MODULE 82 で PLAN のみ 0 件・MODULE のみ 19 件(orchestrator 内部18 + mathkit で、
  `02-design/relations.md` の意図的除外と完全一致)。**コード差分は空**。

## 更新したドキュメント

| ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|
| docs/00-requests/terminology.md | 1.1.0(変更なし) | **合格証を発行せず、失効していた 1.0.0 の verified ブロックを削除**。理由を先頭コメントに書いた(`docs/issues/044`) |
| docs/03-impl/index.md | 1.6.0 → **1.7.0** | 「コードとの乖離として未解決のもの」の `issue 019` を「8件」→「残 1 件(`TestReadyTasks_Basic`。2箇所)」へ訂正。**合格証を再発行** |
| docs/issues/019 | — | frontmatter `summary` を実態(7件解消 / 残1件)へ訂正 |
| docs/issues/017 | — | 03 側の 2 箇所を追加。「資源逼迫」7箇所は `issue 044` の裁定待ちと明記 |
| docs/issues/044 | — | 新規起票(severity 高。手続きと合格証の失効に対するもので、内容の誤りではない) |
| docs/issues/index.md | — | `build-index.py` で再生成(35 件) |

## 実装したもの

なし。**コードは1行も変更していない**(`git diff --stat -- . ':!docs'` が空)。

## 機能間連携仕様書の変化

なし。`callees` / `contracts` / `tests` の構造も本文も変えていないため、
`check-relations.py`(82/82 合格)と `callgraph-check.py`(高0)の結果は前回と同値である。

## この実行が残した限界(必ず申し送る)

- **独立レンズが1本も走っていない**(2回連続)。修正と再検証を同じセッションで行うのは自己レビューで、
  それを補償するのが独立レンズである。**2026-08-10 以降に `/doc-check full` を新しいセッションで
  1回**走らせること。
- **`/kit-improve` 案件(新規)**: **`terminology.md` はどのドキュメントの `source:` にも現れない**
  (`.claude/directions/01-requirements.md` の frontmatter 例も terminology を挙げていない)。
  しかし「全層がこの用語集に従う」と定められた規範なので、**用語の定義が変わっても下流の合格証は
  失効しない**。今回まさにそれが起きた(用語集が受入基準の測定可能性を変えたのに、
  `functional.md` / `non-functional.md` の合格証は有効なまま)。
  用語集を全ドキュメントの暗黙の `source` として扱う検査が要る。
- **`/kit-improve` 案件(新規)**: **`/doc-check` が「前回の実行の後に入った記録の無い編集」を
  検出できるのは、合格証が MAJOR.MINOR で失効したときだけ**である。今回 `functional.md` 1.3.2 と
  `non-functional.md` 1.2.1 は PATCH bump だったため機械検査をすべて通過し、
  合格証の失効を追いかけた結果として**間接的に**見つかった。
  version の遷移と histories の記載を突き合わせる検査(「記録の無い bump」の検出)が要る。
- **`docs/issues/036`(severity 高・データ破壊: `start` の後片付けが同名の稼働中コンテナを消す)は
  開いたまま**である(前回からの継続。人間の裁定済みで合格証はブロックしていない)。
