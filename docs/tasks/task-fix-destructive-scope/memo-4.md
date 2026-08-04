# task-fix-destructive-scope の解決済みの経緯 (4)

<!-- /implement C-4 のローテーションで memo.md から移した。要約ではなく原文のまま。 -->

## 進捗メモ（フェーズ2 前半・2026-08-04）

- 2026-08-04 `/doc-check task-fix-destructive-scope` を新しい文脈のサブエージェントで実行。
  **1回目は不合格**(残存「高」5件)。自動修正19箇所 + 委任決定2件(`D0-env-09`。残骸ロックの
  引き継ぎを `mv` の原子性へ / `trap` を `mkdir` より前へ)。独立監査 Codex 4本で計27件(高11/中13/低3)、
  誤検知1件のみ。`02-design/system.md` の「モジュール分割定義」と「E2Eシナリオ一覧」が影響範囲に増えた。
  **キットの不具合をもう1件発見**: `check-changeset.py` は引数にタスク slug を渡すと
  「対象0ファイル」で「不変条件の違反なし」と表示して終了する(fail-open)。
- 2026-08-04 `/doc-check` の決定シート5件に人間が**全件 A** で回答し、変更指示へ反映した
  (U-20〜U-24)。**`D0-env-05` を影響範囲に加えた**(00 の既存決定の上書き)。
  `reset` に共有資源の遊休判定、`start` の共有ロックを `docker run` 完了まで、
  `stop` が本体削除前に `project-dir` ラベルを読む、`INT`/`TERM` 時の列挙と終了コード 130。
  **人間判断の未決点はゼロ。** memo.md を 366 行 → 333 行へローテーション(`memo-2.md` を新設)。

- 2026-08-04 **`/doc-check` の再実行がセッション上限で中断した**(復帰 18:50 JST)。
  ツールの問題なので issue / pending には起票しない(CLAUDE.md 不変則6)。
  **モデルを使わない機械検査だけは実行して全部通した**:
  `callgraph-check.py --to-be task-fix-destructive-scope` **重大度「高」0**(中3 は
  `MODULE-entrypoint-claude` の CG3 = プロセス境界をまたぐ起動で、影響範囲外の既存指摘)/
  `check-relations.py` 合格(82/82)/ `check-contracts.py` 合格 /
  `build-callgraphs.py --check` 最新 / `cluster-features.py --check` 最新 /
  `build-index.py --check` 差分なし / `check-changeset.py` I1 合格 /
  `sections` の 49 個が SSOT と文字列一致・本文欠落0。
  **自分で1点直した**: `start` の共有資源ロックの解放位置を「`docker run` の完了」から
  **「手順15 の再試行ループを抜けたところ」**へ(ポート競合の再試行の途中で離すと、
  次の試行で作られるコンテナが保護の外に出る)。契約の区間定義も同じ語へ揃えた。
  **★ここまでは自己検証であり `/doc-check` の代わりにはならない**(私が変更指示の書き手である)。
  **フェーズ2 を抜けるには 18:50 JST 以降に新しい文脈で
  `/doc-check task-fix-destructive-scope` を実行して PASS を得る必要がある。**
  それまで `/implement` を開始してはならない。
