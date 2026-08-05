# task-spec-measurability memo-1(2026-08-05 フェーズ1 のローテーションで追い出したもの)

<!-- memo.md から節ごと逐語で移した。要約ではない(.claude/directions/task-memo.md §2)。
     移した理由: 2本の申し送りは 2026-08-05 の再実測(memo.md「調査メモ」)と closure の確定で
     消化済みだから。**未消化だった1件**(terminology.md に「破壊的操作」「管理ラベル」の2行を
     追加する)は memo.md の「やること」へ引き上げてある。 -->

## 前タスクからの申し送り(task-fix-destructive-scope フェーズ4 で転記。2026-08-04)

- **`task-fix-destructive-scope` は完了した。** SSOT が動いたので、**本タスクの変更指示を
  新しい SSOT に対して読み直すこと**。動いたファイルのうち本タスクと重なるもの:
  `01-requirements/functional.md`(1.4.0 → 1.5.0。`FR-env-01` に受入基準14〜21、
  `FR-env-03` に14〜23 を追加)/ `02-design/system.md`(2.0.0 → 2.1.0。`#### SCR-01 cli-commands`・
  `## モジュール分割定義`・`### 結合テスト対象`・`### E2Eシナリオ一覧`)/
  `02-design/relations.md`(1.0.0 → 1.1.0。`## 一覧` に `PLAN-cli-common-lock` を追加して 64 行)/
  `03-impl/tests/e2e.md`(1.1.0 → 1.2.0)/ `03-impl/index.md`(1.8.0 → 1.9.0)。
- **`00-requests/terminology.md` に「破壊的操作」「管理ラベル」の2行を追加すること**
  (1本目では `D0-env-08` の本文に定義を閉じた)。あわせて **`terminology.md` の合格証の発行は
  本タスクの担当**である(`docs/issues/044` で人間が裁定済み。1本目は発行していない)。
- **`docs/issues/049`(`AC-02` が例外なしで「`start` でポート非公開」を要求するが、既定の
  ブラウザ確認ありは noVNC ポートを公開する)を本タスクで直すのが効率的**
  (本タスクが `AC-02` を触るため)。

## 前タスクからの申し送り(task-relations-code-sync フェーズ4 で転記。2026-08-05)

- **`task-relations-code-sync` は完了した。** SSOT が動いたので、**本タスクの前提を新しい SSOT に対して
  読み直すこと**。動いたファイルのうち本タスクと重なるもの:
  `01-requirements/functional.md`(1.5.0 → **1.5.1** PATCH。`FR-env-01` 受入基準15 の言い換えのみ。
  **PATCH なので下流の合格証は失効しない**)/ `02-design/system.md`(2.2.0 → **2.2.1** PATCH。
  `#### SCR-01 cli-commands` と `### DSN-mod-05`)/ `03-impl/index.md`(1.11.0 → **1.13.0**)/
  `03-impl/tests/orchestrator.md`(1.1.1 → **1.3.0**)/ `02-design/contracts/orchestrator-prompt.md`
  (1.2.0 → **1.3.0** MINOR)/ `02-design/contracts/cli-container.md`(1.4.1 → 1.4.2)/
  `03-impl/contracts/cli-container.md`(1.5.0 → 1.5.1)/ `03-impl/features.md` と
  `03-impl/relations/MODULE-*`(層として `03-impl/index.md` が認証)。
- **`docs/issues/017` の残件表を着手時に読み直すこと。** 2本目の決定シート論点5 が想定した
  「`MODULE-orchestrator-claude-exec` / `-session` の relations 2行」は**空振りだった**
  (3行とも現行 SSOT に存在しない)。したがって**本タスクの決定シート論点5 は前提が古い**:
  「2本目で同じファイルを開くので、そこで直すのが最も安い」という推奨理由は成立しない。
  経緯は `docs/issues/017` に記録済み。
- **`docs/issues/056`(変更相対の言い回し)は 2本目でほぼ解消した。** 反映後の SSOT に残る 8 箇所は
  すべて**コードが実際に出力する文面の逐語引用**(`claude-dev:1091`・`:1669`・`:2110`)であり、
  ドキュメントだけを直すと CLAUDE.md 原則2 を破る。**残るのはコード側の文言の是正**で、
  これは本タスクの範囲外(コードを変えるタスクが要る)。走査語彙の不足は
  `.claude/improvements/KIT-audit-scope-budget-and-change-relative-vocabulary.md` に移した。
- **`docs/issues/054` に「削除後に宙に浮く参照」が追記されている。** 2本目が `019`/`032`/`038` を
  削除したため、`docs/00-requests/decisions/orch.md:199`(**層00**)ほかの参照先が実在しなくなる。
  **層00 を開けるのは本タスクの起点層と一致する**ので、ここで一緒に直すのが安い。
- **新しい issue が3本増えた**: `057`(壊れた `open.json` で判断待ちキューが失われる)/
  `058`(未知の `severity` がレビューゲートを通過する)/ `059`(`FR-orch-06` 受入基準2 を覆うテストが
  実在しないのに「実装済み」)。いずれも**コード修正が要る**ので本タスク(仕様の測定可能化)の範囲外。
  ただし `059` は `/doc-check ssot` の決定シート #1 が未回答のまま既定 A を適用しており、
  **`tests/orchestrator.md:67` の状態を「未検証(テスト未実装)」へ落とすかは人間の判断が残っている**。
- **relations 層 83 本のうち、独立レンズがコードと全文照合できたのは 1 本だけ**である
  (22 本一括の監査は 900 秒でタイムアウトした)。その1本から 11 件の乖離が出たので、
  **`MOD-orchestrator` の残り 18 本を1本1監査で回す独立タスク**が要るかもしれない
  (`/doc-check ssot` の決定シート #2。既定は A =「2026-08-10 以降の `/doc-check full` に委ねる」)。

<!-- 2026-08-05 フェーズ1の完了時に追加。1本目・2本目が閉じたので実行順は役目を終えた。 -->

## 実行順(★重要)

**3本連続タスクの3本目。着手は `task-relations-code-sync`(2本目)を閉じた後。**
重なりは 1本目と `01-requirements/functional.md` / `03-impl/index.md`、2本目と `03-impl/index.md`。

**本タスクが最後である理由**: 1本目・2本目がコードと 03 を動かすので、**測定方法を先に固定すると
書き直しになる**(とくに `NFR-sec-02` の測定方法は1本目の `logout` / `reset` の挙動に依存する)。

