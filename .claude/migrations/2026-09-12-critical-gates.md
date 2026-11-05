---
id: 2026-09-12-critical-gates
since: 2026-09-12
kind: judgment
detect: test -f tests/gates.yml && python3 -c "import re,sys;t=chr(10)+open('tests/gates.yml',encoding='utf-8').read()+chr(10);blk=lambda n:(lambda m:(m.group(2) if m else ''))(re.search(r'\n([ \t]*)'+n+r':[ \t]*\n(.*?)(?=\n\1\S|\Z)',t,re.S));step=lambda b,k,s:bool(re.search(r'\n[ \t]+'+k+r':[^\n]*suite:[ \t]*'+s,chr(10)+b));scan=lambda b:bool(re.search(r'\n[ \t]+secret_scan:[ \t]*true[ \t]*(?:\#[^\n]*)?\n',chr(10)+b+chr(10)));c=blk('f4-critical');ok4=all(step(c,k,'critical-'+k) for k in ('unit','integration','e2e'));ok1=(scan(blk('f1-fast')) and step(blk('f1-fast'),'unit','unit') and step(blk('f1-fast'),'integration','integration') and scan(blk('f1-unit')) and step(blk('f1-unit'),'unit','unit') and scan(blk('f1-integration')) and step(blk('f1-integration'),'integration','integration'));sys.exit(1 if ok4 and ok1 else 0)"
paths: tests/gates.yml
summary: gates.yml に f4-critical / f1-unit / f1-integration を足し、構築の3組に secret_scan を足す
---

## 何が変わったか

配られたスキルが、**このプロジェクトの `tests/gates.yml` にまだ無いテスト実行ゲートを呼ぶ**
ようになった。`tests/` は初回に1度だけ展開され、以後は上書きされない場所なので、
**上書き展開では直らない。** 足さないまま新しい手順を打つと、ランナーが
「gate が定義されていません」で `exit 2` になって止まる。

加わったのは3つである。

1. **`f4-critical`** — `@critical` を付けたテストを、`@flaky` と一時除外(`quarantine.yml`)の
   除外を一切かけずに通すテスト実行ゲート。`f4-unit` / `f4-integration` / `f4-e2e` が呼ぶ
   スイートはどちらも除外するので、**重要なテストを一時除外に入れたままでも試験区分が緑になる**
   — その穴を塞ぐ。`/verify-tests` はこれを試験区分ごとの合格条件に入れている。
2. **`f1-unit` / `f1-integration`** — 構築で使う組。`f1-fast` は unit と integration の
   2ステップを持ち、`--grep` / `--files` は両方に掛かるので、**片方の試験区分しか持たない
   モジュールを絞ると、持っていない側が0件になる**(`--grep` なら run 全体が不合格、
   `--files` だけなら黙って skipped)。存在する試験区分だけを呼べるようにする。
3. **構築の3組が `secret_scan` を呼ぶ** — 資格情報の混入を見る静的チェックのステップ。
   **コマンドを書くのは別の移行である**(`2026-09-12-secret-scan`)。

**この移行は `tests/gates.yml` だけを触る。** スイートの定義・混入検査のコマンド・
設計文書のコマンド表は、**それぞれ別の移行に分けてある** ★ — 1本にまとめていたころは、
`f4-critical` という字面が `gates.yml` に1度書かれただけで**全部済んだ**と判定し、
途中で中断した導入の残りが誰にも案内されなかった(inspection-27 C-10)。
**先にスイートを足すこと**(`2026-09-12-critical-suites`)— `f4-critical` は
`critical-unit` / `critical-integration` / `critical-e2e` を呼ぶので、
スイートが無いままこれだけ足すとランナーが落ちる。

## 手順

**このプロジェクトの宣言ファイルを編むので、内容を読んでから当てる。**

1. `tests/gates.yml` にテスト実行ゲートを3本足す。
   **`f4-critical` に `strict` を付けない** — `@critical` が1件も無い状態を
   「対象テスト0件」で不合格にしないためで、0件は skipped として見えるほうが事実を伝える。

   ```yaml
     f1-unit:
       secret_scan: true
       unit: { suite: unit, forbid_skip: true }

     f1-integration:
       secret_scan: true
       integration: { suite: integration, forbid_skip: true }

     f4-critical:
       quarantine_overdue: fail
       unit:        { suite: critical-unit, forbid_skip: true }
       integration: { suite: critical-integration, forbid_skip: true }
       e2e:         { suite: critical-e2e, forbid_skip: true }
   ```

2. 既存の `f1-fast` にも `secret_scan: true` を1行足す。
   **構築の3組すべてに要る** — この移行の要否判定は、`f1-fast` / `f1-unit` / `f1-integration`
   の**それぞれ**が `secret_scan: true` を持つかを、組ごとに見る(行の数では数えない —
   数えると、別の組に足した1行で足りないことが隠れる)。

## 移らなかったときに何が起きるか

- `/verify-tests` が `f4-critical` を打てず、`exit 2` で止まる。**試験区分の鮮度スタンプが
  記録できない。**
- `/build` で片方の試験区分しか持たないモジュールを絞ると、`f1-fast` のまま
  `--grep` で不合格になるか、`--files` で黙って skipped になる。
- 資格情報の混入検査が、どのテスト実行ゲートからも呼ばれない。

**テスト基盤(`tests/`)を入れていないプロジェクトには、この移行は掛からない**
(`detect` が `tests/gates.yml` の実在を先に見る)。
