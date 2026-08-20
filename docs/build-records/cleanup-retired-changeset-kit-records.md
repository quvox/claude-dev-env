---
slug: cleanup-retired-changeset-kit-records
state: verified
critical: false
origin: human-report
issue: なし
started: 2026-08-20T09:19:37+09:00
updated: 2026-08-20T05:43:36+00:00
commit: 1b924ba194d50490b7f2784828745990cea09f47
summary: 規約刷新で廃止された変更指示系スクリプト・規範に紐づくキットパッチ・残務・issue を後始末する
---

# cleanup-retired-changeset-kit-records — 廃止済みスクリプトに紐づく記録の後始末

## 目的・やらないこと

- 目的: 2026-08-20 の規約刷新で `.claude/scripts/check-changeset.py` / `close-task.py` /
  `compose-changeset.py` / `changeset-invariants.json` と `.claude/directions/change-set.md` が
  廃止されたことに伴い、それらだけを対象にしていた成果物(キットパッチ)・残務・issue を消す。
  人間の要望001「規約を新しくしたので、まずキットの修正は破棄する」の実行である。
- やらないこと: キット本体(`CLAUDE.md` / `.claude/`)の編集(CLAUDE.md §3 の凍結。
  `/kit-improve` の領分)。SSOT(00〜03)の本文編集。製品コードの変更。
  `docs/03-impl/index.md` の日付つき検証記録の書き換え(worker-2 の closure と交わるため、
  および日付で固定された記録を再構成すると事実でなくなるため — 残務1行として残す)。

## 影響範囲(closure)

- kit-patches/2026-08-10-compose-changeset-and-close-task.patch(削除)
- docs/pendings.md(残務セクション)
- docs/issues/076-bug-check-changeset-treats-staged-callgraphs-as-change-instructions.md(削除)
- docs/issues/079-modify-cs6-cs7-are-permanently-unchecked-with-no-recorded-decision.md(削除)
- docs/issues/081-bug-check-changeset-aborts-on-a-non-utf8-file-in-the-task-directory.md(削除)
- docs/issues/index.md(build-index.py が再生成)

## 主張

- 触ったモジュールのテスト: 該当なし(製品コードを1バイトも触っていない)。
  回帰確認として `cd docker-proxy && go test ./...` を実行 → green
  (最終行の逐語: `ok  	github.com/quvox/claude-dev-env/docker-proxy	(cached)`、終了コード 0)
- lint / build: `cd docker-proxy && go vet ./...` → green(出力なし・終了コード 0)。
  状態層の自己検査 `python3 .claude/scripts/test-state-scripts.py` → 最終行の逐語:
  `OK 状態層+一括検査: stamps / check-debt / check-buildrecord / check-sheet / check-ssot`
- 外部挙動の変化: なし(製品の振る舞いに触れる変更を含まない)
- 認証・決済・不可逆への接触: なし(critical: false)
- E2E・全件テスト・ブラウザQA: 実施していない(/verify-tests に委ねる — 収束契約)

## 基本要件の点検

| ID | 判定 | 理由 | 落とし先 |
|---|---|---|---|
| BR-01 | 非該当 | closure にアカウント・権限・認証情報を扱う機能が1つも無い(記録ファイルの削除のみ) | - |
| BR-02 | 非該当 | 利用者・外部から値を受け取る経路が closure に無い | - |
| BR-03 | 非該当 | 利用者が値を決める識別子を新たに作らない | - |
| BR-04 | 非該当 | プロセス境界を越える値のやり取りが closure に無い | - |
| BR-05 | 非該当 | 利用者の操作で起きることは何も変わらない。消えるのは開発記録であり、git 履歴に残る | - |
| BR-06 | 非該当 | 秘密・トークンの類を生成しない | - |

## 決定シート(回答済み)

- 問いなし(開示のみ)。問う基準(`delegation.md` §1)を通る項目が0件だったため、
  シートは作らず・出さずに続行した。判断はすべて標準委任の内側である。

## 調査メモ

- `check-ssot.py docs` の凍結した母集団: 125 ファイル / NG 違反 13 件
  (CS11 参照実在 5 件・CS20 issue の起点層 8 件)。2026-08-20 09:15 実行。
- `.claude/scripts/` に `check-changeset.py` / `close-task.py` / `compose-changeset.py` /
  `changeset-invariants.json` は実在しない(`ls .claude/scripts/` で確認)。
- `.claude/directions/change-set.md` は実在しない(`ls` で確認)。
- `kit-patches/` は空。パッチファイルは作業ツリーで削除済み・未コミット
  (`git status --porcelain` → ` D kit-patches/2026-08-10-compose-changeset-and-close-task.patch`)。
- `python3 .claude/scripts/check-kit-refs.py` → OK(キット内参照はすべて実在)。
  `*.local.json` は「無いのが既定」と明記されている(`check-kit-refs.py:197-201`)。
- 廃止済みスクリプト/規範を名指す残務: `docs/pendings.md` の 167 / 170 / 171 / 172 / 173 /
  174 / 176 / 179 行(8 行)。
- 廃止済みスクリプト/規範だけを対象にした issue: 076 / 079 / 081 の3件。
  `docs/issues/index.md` 以外に 00〜03 からの参照は無い(CS11 の違反一覧に現れない)。
- SSOT 側の言及: `docs/02-design/system.md:465-467`(HTML コメント)と
  `docs/03-impl/index.md:41,48,50`(日付つき検証記録)。どちらも closure 外と裁定(下記 進捗メモ)。

## 進捗メモ(再開点)

- 2026-08-20 09:19 構築記録を作成。入口ゲート2本とも合格(issue 13/30・残務 42/50・
  未検証記録 0/5・未回答シート 0)。
- 2026-08-20 09:25 closure を確定。`@triage` の当たり(パッチ・残務3行・issue 076/081)に対し、
  同根の残務5行(167/171/174/176/179)と issue 079 を足し、`docs/03-impl/index.md` と
  `docs/02-design/system.md` は closure 外と裁定した(理由は履歴の「検討した代替案」)。
- 2026-08-20 09:27 [DS-08] 1コミットにまとめる — 理由: 削除どうしが互いに依存せず、
  分けても独立に検証できる単位が増えない。見直す条件: 製品コードを含む変更が加わったとき。
- 2026-08-20 09:30 `docs/pendings.md` を編集(残務 42 → 35 行)。issue 076/079/081 を削除。
  `build-index.py` と `doc-health.py` で生成物4本を再生成。
- 2026-08-20 09:33 常時床を実行。`go vet` / `go test`(docker-proxy)/ `test-state-scripts.py`
  すべて green。`check-ssot.py docs` の NG は 13 件 → 10 件(CS20 が 8 → 5)。
- 2026-08-20 09:35 履歴 `docs/histories/2026-08-20-cleanup-retired-changeset-kit-records.md` を作成。

## override(人間の明示)

- なし(override 不使用)

## 申し送り

- なし
