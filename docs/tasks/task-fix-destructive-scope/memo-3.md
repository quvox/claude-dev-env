# memo-3 — フェーズ2 の前半(フェーズ1宣言・下降・初回の独立監査・`/doc-check` 1回目)

<!-- memo.md から追い出した解決済みの経緯。ローテーションは要約ではないので逐語で移してある。
     2026-08-04 の `/doc-check`(3回目)が memo.md 441 行(閾値300)を検出して実施した。 -->

## 進捗メモ

- 2026-08-04 フェーズ1。`issue 020` を起点に `024` / `025` / `029` / `045` を同時対象として宣言。
  3本連続タスクの1本目。決定シート6論点 + 委任2件を提示。
- 2026-08-04 フェーズ2。決定シートの回答(全6論点 A / 委任 a・b 承認)を得て 00→03 の1回の下降を実施。
  変更指示 **18ファイル**(00×1 / 01×1 / 02×3 / 03×13)。影響範囲に
  `02-design/relations.md`・`03-impl/features.md`・`03-impl/relations/MODULE-cli-common-lock.md`(新設)・
  `03-impl/tests/cli-common.md`・`03-impl/tests/e2e.md` を追加し、
  `03-impl/contracts/cli-container.md`・`03-impl/index.md`・`03-impl/tests/cli-reset.md`・
  `01-requirements/non-functional.md`・`00-requests/terminology.md` は変更なしと判定した(理由は closure 表)。
  実装ドライラン: 自分のパス1 で未決点8件(人間判断3 / ドキュメント記載4 / 委任決定1)。
  パス2 でコードの事実13件を確認(調査メモ)。`docs/issues/046` を起票。
- 2026-08-04 **独立監査(Codex `gpt-5.6-terra` / reasoning max、`readiness`)が11件を指摘**
  (高8 / 中3)。**誤検知は0件。** 内訳: 1件は自分も立てた U-1 と同一(独立に同じ穴を検出)/
  9件をドキュメント記載で解消(U-9〜U-17)/ 1件はキットが意図した一時状態として裁定(U-18)。
  影響範囲に `02-design/system.md` が増えた(`SCR-01` の公開フラグに `--yes` が無かった)。
  **1回目の実行はキットの `audit-schema.json` の不備で HTTP 400 失敗**したため、スクラッチパッド上の
  修正版スキーマで1回だけ再実行した(§3 の許す1回の再試行。原因は明らかに環境要因)。
  `git status --porcelain` の比較で Codex による書き込みが無いことを確認済み。
  **未決点 U-1〜U-3 が人間判断のため、`/implement` はまだ開始できない**(原則7)。
- 2026-08-04 **`/doc-check task-fix-destructive-scope`(新規サブエージェント)判定: 不合格(残存 5 件)。
  レンズ: Codex(`gpt-5.6-terra` / reasoning max、3本 + 修正後の再監査1本)。**
  独立レンズは合計 27 件を指摘(高11 / 中13 / 低3)。**誤検知は 1 件のみ**(U-18 と同じ、
  実装前に書かない節に旧挙動が残るという指摘。キットの規範どおりなので棄却)。
  範囲外・既起票として棄却したのは 5 件(`docs/issues/005` / `042` / `017`+3本目 / `044` / `D0-env-07`)。
  **自動修正 14 件・委任決定(D0-env-09)2 件を適用した**(下記)。
  **残存する重大度「高」5 件(U-20〜U-24)はすべて人間判断が必要**なので、原則7 により
  `/implement` は開始できない。決定シートを提示済み。
  - 自動修正: 契約の `DSN-env-02`(対象を6コマンドへ / 関連を項6 へ)と非TTY 行の対象限定 /
    `02-design/system.md` に**モジュール分割定義**と**E2Eシナリオ一覧**を影響範囲へ追加
    (`MOD-cli-common` の責務に排他、`MOD-cli-reset` の依存を `MOD-cli-common` へ、機能数 82→83、
    E2E-01 のシナリオ欄)/ `SCR-01` の受理文字集合を `stop` 限定に、排他待ち状態を6コマンド共通へ /
    `02-design/relations.md` 末尾コメントを 64 行・全83機能へ / `MODULE-cli-stop` の項番号3箇所 /
    `MODULE-cli-logout` の失敗集計に手順9 を追加・判断8 の手順番号 / `MODULE-cli-start` の
    is-running 注記(名前衝突では削除しない)/ `03-impl/tests/cli-logout.md` に `FR-env-01` 受入基準9 /
    `03-impl/tests/e2e.md` に手順8-5 の proxy 保持確認と2つのトレーサビリティ表 /
    `MODULE-cli-common-lock` の判断表を 1〜12 へ振り直し・`deletes: []` の明示。
  - 委任決定(`D0-env-09`): 残骸ロックの回収を **`mv` による原子的な引き取り**へ(U-25)、
    **`trap` を `mkdir` より前に**仕掛け `owner` 欠落は1秒待って読み直す(U-26)。
  - 機械検査: `callgraph-check.py --to-be` 重大度「高」**0**(中3 は範囲外の既存指摘)/
    `check-relations.py` 合格 / `check-contracts.py` 合格 / `build-callgraphs.py --check` 最新 /
    `cluster-features.py --check` 最新 / `build-index.py --check` 差分なし。
    `check-changeset.py` の I2(23件)と I10(1件)は**既知の偽陽性**(SSOT 側の callee と機能表を
    見ないため。全件を実読して確認済み)。
