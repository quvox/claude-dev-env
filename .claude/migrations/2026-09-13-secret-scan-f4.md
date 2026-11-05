---
id: 2026-09-13-secret-scan-f4
since: 2026-09-13
kind: judgment
detect: test -f tests/gates.yml && python3 -c "import re,sys;t=open('tests/gates.yml',encoding='utf-8').read()+chr(10);m=re.search(r'\n([ \t]*)f4-unit:[ \t]*\n(.*?)(?=\n\1\S|\Z)',chr(10)+t,re.S);sys.exit(1 if m and re.search(r'\n[ \t]+secret_scan:[ \t]*true[ \t]*(?:\#[^\n]*)?\n',chr(10)+m.group(2)+chr(10)) else 0)"
paths: tests docs/02-design/environments.md
summary: 資格情報の混入検査が、出荷前に必ず1回走るようになった(f4-unit が strict の下で呼ぶ)
---

## 何が変わったか

`secret_scan`(資格情報 — 鍵・トークン — の混入を見る静的チェック)は、これまで構築の組
(`f1-fast` / `f1-unit` / `f1-integration`)だけが呼んでいた。**あの3本は `strict` を持たない**ので、
`tests/adapters.yml` の `checks.secret_scan` が空のままでも `skipped` で通り続け、
**「全試験合格」から検査の欠落を判別できなかった。**

`f4-unit` に `secret_scan: true` を1行足す。`f4-unit` は `strict: true` を持ち、
`strict` は**アダプタのコマンド未定義による skipped を failed にする**ので、
**コマンドが空のままでは `unit` の試験区分が green にならない。**
製品の完了定義は `unit` の green を要求しているから(`.claude/directions/principles.md` §12)、
これで**出荷までに必ず1回、設定と成功が要求される。**

**足すのは `f4-unit` だけである。** `f4-integration` / `f4-e2e` / `f4-critical` には足さない —
同じ静的チェックを試験区分の数だけ繰り返しても、増えるのは実行時間だけである。

## 手順

1. `tests/gates.yml` の `f4-unit` に1行足す。

   ```yaml
     f4-unit:
       strict: true
       quarantine_overdue: fail
       secret_scan: true
       unit: { suite: unit, forbid_skip: true }
   ```

2. `tests/adapters.yml` の **`checks:`** に `secret_scan` のコマンドが在るかを見る。
   **空なら埋める** — 埋めるまで `unit` は red になる。道具の選定はこのプロジェクトの判断である
   (例: `gitleaks protect --staged --no-banner`)。**この2 の手当ては
   `2026-09-12-secret-scan` の移行が持っている** — そちらが済んでいればここは確かめるだけでよい。

3. `docs/02-design/environments.md` の「lint・テストコマンド」の表の
   **資格情報の混入検査**の行に、2 で決めた文字列を逐語で書く(表が正であり、
   `checks.secret_scan` と同じ文字列にする)。**この3 の手当ては
   `2026-09-12-test-command-table` の移行が持っている。**

**この移行の要否判定が見るのは 1 だけである** ★ — `gates.f4-unit.secret_scan` が `true` か。
コメント・`false`・空の値は「まだ」と読む。2 と 3 は、それぞれの移行が自分で判定する。

## 移らなかったときに何が起きるか

- 資格情報の混入検査は構築の組でしか呼ばれず、**コマンドが空なら一度も走らないまま出荷できる。**
- 混入は一度コミットすると取り返しがつかない。

**テスト基盤(`tests/`)を入れていないプロジェクトには、この移行は掛からない**
(`detect` が `tests/gates.yml` の実在を先に見る)。
**テスト基盤を使わず、言語のテスト命令を直に走らせる構成では、この経路では守れない** ★ —
そちらの手当ては `.claude/skills/verify-tests/SKILL.md` の `unit` の合格条件が持つ。

   