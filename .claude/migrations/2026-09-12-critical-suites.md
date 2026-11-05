---
id: 2026-09-12-critical-suites
since: 2026-09-12
kind: judgment
detect: test -f tests/suites.yml && python3 -c "import re,sys;t=chr(10)+open('tests/suites.yml',encoding='utf-8').read()+chr(10);blk=lambda n:re.search(r'\n([ \t]*)critical-'+n+r':[ \t]*\n(.*?)(?=\n\1\S|\Z)',t,re.S);val=lambda b,k:(lambda m:(m.group(1).strip() if m else ''))(re.search(r'\n[ \t]+'+k+r':[ \t]*(.*?)[ \t]*\n',chr(10)+b+chr(10)));ok=lambda n:(lambda m:bool(m) and bool(val(m.group(2),'include').strip('[] ')) and '@critical' in val(m.group(2),'require_tags'))(blk(n));sys.exit(1 if all(ok(n) for n in ('unit','integration','e2e')) else 0)"
paths: tests/suites.yml
summary: suites.yml に試験区分別のクリティカルパス回帰(critical-unit / -integration / -e2e)を3つ足す
---

## 何が変わったか

`f4-critical`(重要テストを除外なしで通すテスト実行ゲート)が呼ぶスイートが3つ要る。
`tests/` は初回に1度だけ展開され、以後は上書きされないので、**上書き展開では直らない。**

**この移行を先に当てる** ★ — スイートが無いまま `2026-09-12-critical-gates` を当てると、
テスト実行ゲートが存在しないスイートを指すことになり、ランナーが止まる。

## 手順

1. `tests/suites.yml` に3つ足す。
   `min_count` は `@critical` を1件でも付けてから有効にする(導入直後は0件が正しい)。

   ```yaml
     critical-unit:
       include: ["src/**/*.test.*"]
       require_tags: ["@critical"]
       exclude_tags: []
       # min_count: 1

     critical-integration:
       include: ["tests/integration/**/*.test.*"]
       require_tags: ["@critical"]
       exclude_tags: []
       # min_count: 1

     critical-e2e:
       include: ["tests/e2e/**/*.spec.*"]
       require_tags: ["@critical"]
       exclude_tags: []
       # min_count: 1
   ```

   **`include` はこのプロジェクトの配置に合わせる** — 既にある `unit` / `integration` /
   `e2e-full` の `include` をそのまま写すのが確実である。
   **`exclude_tags: []` を消さない** — ここが空であることが、`@flaky` と一時除外を
   取り戻す仕掛けそのものである。

## 移らなかったときに何が起きるか

- `f4-critical` を足しても、呼ぶスイートが無いのでランナーが止まる。
- スイートを1つか2つだけ足して中断すると、**足りない試験区分が黙って抜ける** —
  この移行の要否判定は3つそろっていることを見るので、残りが案内される。

**テスト基盤(`tests/`)を入れていないプロジェクトには、この移行は掛からない**
(`detect` が `tests/suites.yml` の実在を先に見る)。
