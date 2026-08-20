---
slug: delete-issue-110-per-human-adjudication
state: verified
critical: false
origin: human-report
issue: docs/issues/110-bug-bundled-arm64-binary-is-a-darwin-build.md
started: 2026-08-20T14:02:52+09:00
updated: 2026-08-20T06:26:50+00:00
commit: 5885f32bdab263c9238a205ce214eedec9888618
summary: 人間の裁定により issue 110 を削除し(closes_when は未充足)、110 を参照している 03 層の集計文と生成索引を整合させる
---

# delete-issue-110-per-human-adjudication — issue 110 を人間の裁定で削除し、参照側を整合させる

## 目的・やらないこと

- 目的: `docs/issues/110`(同梱物 `externals/arm64/colabtmux` が darwin ビルドである)を
  人間の裁定に従って削除し、それを参照している文書が削除後に嘘にならないようにする。
  **`closes_when` の (a)(b)(c) はどれも満たされていない。閉じる根拠は人間の裁定だけである。**
- やらないこと:
  - **`externals/` に一切触れない**(人間が「externals についてはあなたは今は何もしなくてよい」と
    述べた)。差し替え・削除・ビルド・`externals/README.md` の編集をいずれも行わない。
  - **`docs/03-impl/environments/images.md` の記述も変えない** — `closes_when` (c) は
    「人間が『arm64 には同梱しない』と裁定し、`externals/README.md` と同ファイルがその状態を
    述べている」ことを求めるが、人間は同梱しないとは述べておらず「今は何もしなくてよい」と
    述べたので、(c) を満たしたことにはならない。**(c) を満たしたと書かない。**
  - `.devcontainer/` と `docs/01-requirements/functional.md` に触れない(issue 110 の案 C は採らない)。
  - `.claude/` に触れない(`/kit-improve` のパッチが本流へ渡る前の状態である)。
  - 作業ツリーの3差分(`.gitignore` の `.colabtmux/` / `externals/amd64/colabtmux` /
    未追跡 `colabtmux.conf`)に触れない・起票しない・revert しない(要望005 で「放置」と裁定済み)。
  - `docs/histories/` と過去の構築記録の 110 参照は直さない(当時の事実の記録である)。
  - 製品コードを変更しない(このタスクにコード変更は無い)。

## 影響範囲(closure)

- docs/issues/110-bug-bundled-arm64-binary-is-a-darwin-build.md
- docs/issues/index.md
- docs/03-impl/index.md
- docs/reverification.md
- docs/build-records/index.md
- docs/histories/index.md

## 主張

- 触ったモジュールのテスト: コード変更が無いため対象モジュールは無い。参考として
  `cd docker-proxy && go test ./...` → `ok  	github.com/quvox/claude-dev-env/docker-proxy	(cached)`
- lint / build: green(`cd docker-proxy && go vet ./...` → 出力なし・終了コード 0)
- 外部挙動の変化: なし(文書と課題記録だけを変更する。製品コードを1行も変えていない)
- 認証・決済・不可逆への接触: なし(critical: false)
- E2E・全件テスト・ブラウザQA: 実施していない(/verify-tests に委ねる — 収束契約)

## 基本要件の点検

| ID | 判定 | 理由 | 落とし先 |
|---|---|---|---|
| BR-01 | 非該当 | closure はアカウント・権限・認証情報を作る/変える/消す機能を含まない(文書と課題記録のみ) | - |
| BR-02 | 非該当 | closure に利用者・外部から値を受け取る画面・API・CLI・ファイル取込は無い | - |
| BR-03 | 非該当 | 利用者が値を決める識別子を新たに導入しない。issue 番号は既存の採番規則のままである | - |
| BR-04 | 非該当 | プロセス外との値のやり取りが closure に無い(生成物の再生成はツールが行う) | - |
| BR-05 | 非該当 | 削除は利用者の操作で起きるものではなく、人間が明示的に裁定した1回きりの文書削除である。削除物は git 履歴に残り `git show` で復元できる | - |
| BR-06 | 非該当 | 推測されると困る値を作らない | - |

## 決定シート(回答済み)

- 人間の裁定(逐語。要望台帳 006 / 2026-08-20):
  > externalsについてはあなたは今は何もしなくてよい。issueも閉じて

  本タスクが担うのは「issue も閉じて」であり、「externals については何もしなくてよい」は
  **やらないことの根拠**として効く。
- 新たな問いなし(開示のみ)。**残務1行を残すかどうかは AI が決める判断であり、
  人間に問う基準(`delegation.md` §1)を通らない**(観測される振る舞い・外部インターフェース・
  費用・法務・セキュリティ境界・運用の姿勢のどれも動かず、後続タスクの普通の変更で戻せる)。

## 調査メモ

- 母集団の凍結: `python3 .claude/scripts/check-ssot.py docs` → 違反 7 件
  (CS11 参照実在 3 件 = `docs/issues/092` 1件・`docs/issues/002` 2件 / CS20 issue の起点層 4 件)。
  **いずれも 110 とは無関係の既存違反**である。
- ゲート: `check-backlog.py --for-issue 110` 合格(未クローズ issue 7 / 上限 30、残務 44 行 / 上限 50)。
  `check-debt.py --for-issue 110` 合格(例外: `type: bug` は止めない。引数なしでは
  未検証の構築記録 6 / 上限 5 で不合格になるので、この通過は issue 110 を対象にしたことによる)。
- **事実は消えない**(2026-08-20 実測): `file externals/arm64/colabtmux` →
  `Mach-O 64-bit arm64 executable, flags:<|DYLDLINK|PIE>`、8,343,362 バイト。
  HEAD の内容も同じ(`git log -1 -- externals/arm64/colabtmux` → `a411581`)。
- **SSOT は嘘をついていない**: `externals/README.md:17` と
  `docs/03-impl/environments/images.md:53`-`:59` が述べるのは
  「`externals/arm64/` 直下は arm64 の配布イメージにだけ入る」という**設置の規約**だけであり、
  置かれた実体が Linux/arm64 のビルドであるとはどちらも述べていない。
  したがって issue を削除しても 原則1 に反する記述は生じない。
- `docs/03-impl/index.md:28` に「2026-08-20 に起票した `110`(…)はこの数に入らない」の文が現存する。
  110 を削除するとこの `docs/` 参照は CS11(参照実在)の違反になる
  (`.claude/scripts/check-ssot.py:181`。CS11 の母集団は `00-requests` `01-requirements`
  `02-design` `03-impl` の4層のみ)。同ファイルは削除済み issue を裸の番号で書く書式を既に採っている
  (同 28 行の `106` / `002` / `046` / `102`)。
- 110 を参照する他の箇所は `docs/reverification.md:109`(生成物)/ `docs/issues/index.md:15`(生成物)/
  `docs/build-records/fix-make-status-hides-docker-query-failure.md:114`・`:119`・`:132` /
  `docs/histories/2026-08-20-fix-make-status-hides-docker-query-failure.md:40`・`:51`・`:59`・`:89` /
  `docs/histories/2026-08-20-doc-check-ssot-coverage-gap-and-false-completeness-claim.md:124`。
  生成物2本はツールで再生成し、構築記録と履歴は当時の事実なので直さない
  (CS11 の母集団に入らないので機械検査にも掛からない)。
- `docs/pendings.md` に 110 を参照する行は0件である(grep 済み)。
- `python3 .claude/scripts/stamps.py check` は 110 を「bug / severity 高 の issue」として
  デプロイ関門の NG に数えている。削除でこの NG から 1 件減る。

## 進捗メモ(再開点)

- 2026-08-20 14:02 closure 確定・構築記録作成。問いなし(人間の裁定は取得済み)。
- 2026-08-20 14:06 **残務行の裁定: 足さない。**同梱物が darwin ビルドである事実は残るが、
  原則8 のゲートはそれを **issue** へ振り分ける(`AC-07` の不合格条件に当たる severity 「高」)。
  残務は `closes_when` も severity も追跡義務も持たず**検証が読み返さない**列であり
  (`.claude/directions/issues-pendings.md` §2.1 冒頭)、そこへ移すのは記録ではなくゲートの緩めである。
  また行の `path` が `externals/arm64/colabtmux` になるが、人間が externals に触るなと裁定した以上
  この path は closure に入り得ず、排出義務(§2.1 (3))が誰にも発生しない — 50 行の上限に達したとき
  「恒久的に受容する」決定を人間ではなく上限が下すことになる。事実は本記録と履歴に実測値つきで残す。
- 2026-08-20 14:08 `docs/03-impl/index.md:28` の 110 の文を、削除の事実・`closes_when` 3項目が
  未充足であること・集計 4件 は変わらないこと・**同梱物が darwin ビルドである事実は残ること**に
  書き替え、`version` を 1.35.0 → 1.35.1(PATCH)にした。集計値が動かないので PATCH である。
  `verified` は書いていない(原則6 — 同ファイルの合格証は `verified.version: 1.34.0` で、
  着手前から現在の MAJOR.MINOR と一致しておらず既に無効である。本タスクが無効にしたのではない)。
- 2026-08-20 14:10 `docs/issues/110-...md` を削除し、`build-index.py` と `doc-health.py` で
  生成索引4本(`docs/issues/index.md` 7→6件 / `docs/reverification.md` /
  `docs/build-records/index.md` / `docs/histories/index.md`)を再生成した。手書きしていない(原則10)。
- 2026-08-20 14:12 履歴 `docs/histories/2026-08-20-delete-issue-110-per-human-adjudication.md` を書いた。
  書いた直後に `docs/histories/index.md` の「更新文書」列が、**本タスクが更新していない**
  `01-requirements/functional.md` と `03-impl/environments/images.md` を挙げていることに気づいた。
  `doc-health.py:314` は履歴の**全文**から `DOC_RE`(`doc-health.py:50`)でこの列を作るため、
  更新していない SSOT パスを散文に裸で書くと生成索引が嘘になる。生成物は手で直せないので(原則10)、
  履歴側の2箇所を `docs/` 接頭辞なしの表記(`03-impl/environments/images.md` 等。
  `docs/03-impl/index.md:28` が既に採っている書式)に替えて再生成し、列を
  `docs/03-impl/index.md` の1件だけにした。
- 2026-08-20 14:14 タスク内整合確認: closure の6パスを再読し、`check-ssot.py` の違反が着手前と
  同じ 7 件(CS11 3 件 / CS20 4 件。いずれも 110 と無関係の既存違反)であること、
  差分が「同型の欠陥 `bundled-binary-built-for-a-foreign-platform: 1 件` の行が消えた」の1点だけで
  あることを確認した。新たな宙づり参照は生じていない。コード変更が無いため実装との突き合わせ対象は無い。
- 2026-08-20 14:16 残務の排出(closure に載る3行。**いずれも持ち越す**。理由は履歴の
  「検討した代替案」の最終行): 2026-08-11「コード引用の行番号のずれ」/
  2026-08-19「削除済み issue を指す参照が6件」/ 2026-08-20「廃止された `compose-changeset.py` 等を
  指す記録」。**削除した行は無い。**
- 2026-08-20 14:18 常時床: `go vet ./...` 出力なし・終了コード 0、`go test ./...` → `ok`(cached)。

## override(人間の明示)

- なし(override 不使用)

## 申し送り

- **`docs/03-impl/index.md` の合格証が着手前から無効である**: `verified.version: 1.34.0` に対し
  `version` は 1.35.0(本タスクで 1.35.1)。2026-08-20 の `fix-make-status-hides-docker-query-failure`
  が 1.34.1 → 1.35.0 に上げた後、同日の F2 が合格証を 1.34.0 のまま残している。次の
  `/verify-docs` が発行し直す対象である(`verified` は verify 系だけが書く — 原則6)。
- **F4 が `AC-07` を arm64 の実機で照合したとき、同じ欠陥が再発見される。**そのときは
  「新規の発見」ではなく **2026-08-20 の人間の裁定(「externals については今は何もしなくてよい」)
  を人間に再確認する**のが筋である。事実の実測値は本記録の調査メモと履歴に残してある。
