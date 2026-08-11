---
id: 100-bug-logout-cannot-tell-a-file-named-like-the-marker-from-the-marker
type: bug
origin_layer: 03
severity: 中
found: 2026-08-11
found_in: /task-close task-fix-logout-zero-target-path §6(独立レビュー Codex の指摘2 を裁定して起票)
related: docs/03-impl/relations/MODULE-cli-logout.md, docs/03-impl/contracts/cli-container.md, claude-dev, claude-dev-mac
closes_when: 共有ボリュームの中身が印と同名でも印と区別されるようになり(行の内容ではなく位置や件数で判定する)、手順6・手順10 の両方でそれを確認できたとき
summary: 共有ボリュームの「空」判定が grep -vxF で印の文字列を除くため、/auth に印と同名のファイルがあると非空でも空と判定される
---

# 100 印と同名のファイルが印と区別されない

## 事象

`logout` は共有ボリュームの中身を2箇所で列挙し、どちらも列挙の直前に印
`__CLAUDE_DEV_AUTH_LISTED__` を出してから **`grep -vxF` で印の文字列を除いた残り**を見る。

- 手順6(0件判定。`claude-dev:1050`〜`:1051`)
- 手順10(消去後の判定。`claude-dev:1154`〜`:1155`)

判定が**行の内容**で行われているため、`/auth/__CLAUDE_DEV_AUTH_LISTED__` というファイル
またはディレクトリが実在すると、`ls -A /auth` が出すその行も印として除かれ、
**中身があるのに「印以外の行が1つも無い」= 空**と判定される。再現:

```bash
$ out=$(printf "%s\n" "__CLAUDE_DEV_AUTH_LISTED__" "__CLAUDE_DEV_AUTH_LISTED__")
$ printf '%s\n' "$out" | grep -vxF "__CLAUDE_DEV_AUTH_LISTED__" || true
（空 = 空と判定される）
```

同名の**ディレクトリ**であればその配下に認証が残っていても検出されない。

## 何が仕様に反するか

`MODULE-cli-logout` 手順6 の条件 (iii) は「**印以外の行が1つも無い**」であり、実装は
「**印と一致しない行が1つも無い**」を検査している。両者は印と同名の行があるときに食い違う。
手順10 も同じ形なので、認証が残っていても「消去に成功」と報告しうる
(`FR-env-03` 受入基準18 が禁じる状態)。**ドキュメントの記述は正しく、実装が追いついていない。**

## 発生条件と severity

共有ボリューム `claude-dev-auth` をマウントするのは本システムのコンテナだけなので、
25文字の印と完全に一致する名前のファイルが偶然できることはない。故意に置くか、
将来この印を別の用途で書き出すようになった場合に当たる。したがって「中」とする
(共有ボリューム側の同型の欠陥として「中」と裁定された当時の `053` と同じ水準。経緯は `docs/histories/2026-08-11-fix-logout-zero-target-path.md`)。

## 直し方の方向（実装の判断は別タスク）

行の内容で除くのをやめ、**印の行より後ろを中身として扱う**(`sed -n '/^__CLAUDE_DEV_AUTH_LISTED__$/,$p'`
の2行目以降、または `awk` で印を1回だけ消費する)ようにすれば、同名の行が中身として残る。
**手順6 と手順10 の両方を直す必要がある**(判定を関数に切り出さないという `MODULE-cli-logout`
判断15 の `[DS-05]` は、3箇所目が要るときに見直すと定めている — 直すときにその条件が発生する)。

## 範囲外とした理由

`task-fix-logout-zero-target-path` は手順6 に印の方式を**導入**したタスクであり、
その方式は手順10 の既存実装から写した(判断15)。この衝突は写し元にも在る同型の欠陥で、
closure に手順10 は入っていない。原則8 に従い直さずに起票する。
