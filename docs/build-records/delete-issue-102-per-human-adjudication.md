---
slug: delete-issue-102-per-human-adjudication
state: verified
critical: false
origin: human-report
issue: docs/issues/102-bug-colabtmux-refuses-to-launch-codex-on-a-nonzero-bwrap-probe.md
started: 2026-08-20T12:44:30+09:00
updated: 2026-08-20T05:43:36+00:00
commit: 75bd636962c2d77573ab13f6c702129cdb6ec1f7
summary: 人間の裁定により issue 102 を削除し、102 を参照している索引・03 層の集計・残務行を整合させる
---

# delete-issue-102-per-human-adjudication — issue 102 を人間の裁定で削除し、参照側を整合させる

## 目的・やらないこと

- 目的: `docs/issues/102`(colabtmux が bwrap の非ゼロを理由に codex を起こさない)を
  人間の裁定に従って削除し、それを参照している文書が削除後に嘘にならないようにする。
- やらないこと:
  - キット(`.claude/`)には一切触れない。102 の残る作業は `.claude/directions/orchestration.md`
    §1.1.1 の判定行の修正であり、それは別オーダー(`/kit-improve`)が担当している。
  - `externals/` `.gitignore` `colabtmux.conf` に触れない(別オーダーが書き込み中)。
  - `docs/issues/109` に触れない(別オーダー)。
  - `docs/histories/` と `docs/feedbacks/` の 102 参照は直さない(当時の事実であり、
    `docs/pendings.md:168` が「履歴は当時の事実なので直さない」と定めている)。
  - 製品コードを変更しない(このタスクにコード変更は無い)。

## 影響範囲(closure)

- docs/issues/102-bug-colabtmux-refuses-to-launch-codex-on-a-nonzero-bwrap-probe.md
- docs/issues/index.md
- docs/03-impl/index.md
- docs/pendings.md
- docs/reverification.md

## 主張

- 触ったモジュールのテスト: コード変更が無いため対象モジュールは無い。参考として
  `cd docker-proxy && go test ./...` → `ok  	github.com/quvox/claude-dev-env/docker-proxy	(cached)`
- lint / build: green(`cd docker-proxy && go vet ./...` → 出力なし・終了コード 0)
- 外部挙動の変化: なし(文書と課題記録だけを変更する。製品コードは1行も変えていない)
- 認証・決済・不可逆への接触: なし(critical: false)
- E2E・全件テスト・ブラウザQA: 実施していない(/verify-tests に委ねる — 収束契約)

## 基本要件の点検

| ID | 判定 | 理由 | 落とし先 |
|---|---|---|---|
| BR-01 | 非該当 | closure はアカウント・権限・認証情報を作る/変える/消す機能を含まない(文書と課題記録のみ) | - |
| BR-02 | 非該当 | closure に利用者・外部から値を受け取る画面・API・CLI・ファイル取込は無い | - |
| BR-03 | 非該当 | 利用者が値を決める識別子を新たに導入しない。issue 番号は既存の採番規則のままである | - |
| BR-04 | 非該当 | プロセス外との値のやり取りが closure に無い(生成物の再生成はツールが行う) | - |
| BR-05 | 非該当 | 削除は利用者の操作で起きるものではなく、人間が明示的に裁定した1回きりの文書削除である。削除物は git 履歴に残り復元できる | - |
| BR-06 | 非該当 | 推測されると困る値を作らない | - |

## 決定シート(回答済み)

- 人間の裁定(逐語。要望台帳 003 / 2026-08-20):
  > issue 102 は消していい。バイナリ差し替えは意図したものなので起票して。kitの不備は修正してパッチを作って

  このうち本タスクが担うのは「issue 102 は消していい」だけである(残る2件は別オーダー)。
- 新たな問いなし(開示のみ)。

## 調査メモ

- 母集団の凍結: `python3 .claude/scripts/check-ssot.py docs` → 125 ファイル。
  違反 7 件(CS11 参照実在 3 件 / CS20 issue の起点層 4 件)。**いずれも 102 とは無関係の既存違反**である。
- ゲート: `check-backlog.py --for-issue 102` 合格(未クローズ issue 8 / 上限 30、残務 41 行 / 上限 50)。
  `check-debt.py --for-issue 102` 合格(例外: type: bug は止めない)。引数なしの `check-debt.py` は不合格なので、
  この通過は issue 102 を対象にしたことによる。
- `docs/issues/102-...md:9` の `closes_when` 3項目のうち、実測で満たしたのは
  「`codex sandbox --enable use_legacy_landlock -- /bin/true` が終了コード 0」だけである。
  残る「colabtmux から codex を起動でき報告が出ないこと」は直す先がキットの
  `.claude/directions/orchestration.md` §1.1.1 であり、「`codex exec` が起こすコマンドが成功すること」は
  共有ボリュームに codex の認証が無く無人では確認できない。**製品側に残る作業は無い。**
- `docs/03-impl/index.md:28` に「`docs/issues/102`(…)はこの数に含めない」の文が現存する。
  102 を削除するとこの `docs/` 参照は CS11(参照実在)の違反になる
  (`.claude/scripts/check-ssot.py:181`。CS11 の母集団は `00-requests` `01-requirements` `02-design` `03-impl` の
  4層のみ — `check-ssot.py:366` の `SSOT_LAYERS`)。同ファイルは削除済み issue を裸の番号で書く書式を既に採っている
  (同 28 行の `106` / `002` / `046`)。
- `docs/03-impl/index.md` は 2026-08-20 の `/verify-impl all`(`auto-fix: 515849a`)が 1.34.0 へ上げ、
  同版の合格証を書いている(`docs/03-impl/index.md:3`, `:10`-`:15`)。この記録の編集はその後に載る。
- `docs/pendings.md:155` の残務行が指す仕事は**キットの規範の修正**であり、issue 102 の削除では消えない。
  行内の `docs/issues/102` 参照だけが宙づりになる。
- `docs/reverification.md:115` に 102 の鮮度確認行がある。同ファイルは `doc-health.py` の生成物である
  (`docs/reverification.md:3`)ので手書きせず再生成する(原則10)。
- `docs/histories/` 6 ファイル・`docs/feedbacks/032`・`docs/build-records/document-codex-sandbox-preconditions.md` にも
  102 の参照があるが、いずれも当時の事実の記録なので直さない。
- `python3 .claude/scripts/stamps.py check` は 102 を「bug / severity 高 の issue」としてデプロイ関門の
  NG に数えている。削除でこの NG から 1 件減る(残るのは 109)。

## 進捗メモ(再開点)

- 2026-08-20 12:44 closure 確定・構築記録作成。問いなし(人間の裁定は取得済み)。
- 2026-08-20 12:50 `docs/pendings.md:155` を裁定: **行は残す**(指す仕事は
  `.claude/directions/orchestration.md` §1.1.1 の判定行の修正で、キット側に未了。102 の削除では消えない)。
  宙づりになる `docs/issues/102` 参照だけを、削除した事実と履歴への案内に書き替えた。
- 2026-08-20 12:52 `docs/03-impl/index.md:28` の 102 の文を、削除済みである旨と
  「集計 4件 は変わらない」に書き替え、`version` を 1.34.0 → 1.34.1(PATCH)にした。
  集計値が動かないので PATCH であり、同日の `/verify-impl all` が書いた合格証(`verified.version: 1.34.0`)は
  MAJOR.MINOR が一致したまま有効である(原則6)。`verified` は書いていない。
- 2026-08-20 12:54 `docs/issues/102-...md` を削除し、`build-index.py` と `doc-health.py` で
  生成索引4本(`docs/issues/index.md` 8→7件 / `docs/reverification.md` / `docs/build-records/index.md` /
  `docs/histories/index.md`)を再生成した。手書きはしていない(原則10)。
- 2026-08-20 12:56 履歴 `docs/histories/2026-08-20-delete-issue-102-per-human-adjudication.md` を書いた。
- 2026-08-20 12:57 タスク内整合確認: closure の4文書と2生成物を再読し、
  `check-ssot.py` の CS11(参照実在)が着手前と同じ3件(いずれも 102 と無関係の既存違反)に戻ったことを確認した。
  文書と実体の食い違いは無し(コード変更が無いため実装との突き合わせ対象も無い)。
- 2026-08-20 12:58 残務の裁定(closure に `docs/pendings.md` が入るため):
  102 由来の 2026-08-20 の行 = **持ち越す**(キット側の仕事。別タスクが担当)。
  2026-08-11 の「コード引用の行番号のずれ」の行(対象に `docs/03-impl/index.md` の4箇所を含む) =
  **持ち越す**(取り直しには `claude-dev` / `claude-dev-mac` へ1件ずつ当て直す作業が要り、本タスクの closure の外。
  本タスクはコード引用を1箇所も触っていない)。どちらも削除していない。

## override(人間の明示)

- なし(override 不使用)

## 申し送り

- **キット側に残る仕事**: `.claude/directions/orchestration.md` §1.1.1 の可否判定を
  `bwrap ...` から `codex sandbox -- /bin/true` に替えること。`/kit-improve` の別タスクが担当している。
  `docs/pendings.md` の 2026-08-20 の残務行がこれを持つ。
- **持ち越した残務**: 2026-08-11 の「コード引用の行番号のずれ」。`docs/03-impl/index.md` の
  `claude-dev:2607` / `claude-dev-mac:2649` の各2箇所は `fix-session-list-undercount` の +15 が乗っている。
  次にこの索引のコード引用を触るタスクが同じ降下で取り直すこと。
- `python3 .claude/scripts/stamps.py check` のブロッキング issue は 102 が外れて `109` の1件になった。
