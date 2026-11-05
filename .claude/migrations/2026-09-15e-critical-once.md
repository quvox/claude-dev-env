---
id: 2026-09-15e-critical-once
since: 2026-09-15
kind: judgment
detect: test -f tests/gates.yml && python3 -c "import re,sys,os;blk=lambda text,name:(lambda m:(m.group(3) if m else ''))(re.search(r'\n([ \t]*)'+name+r':[ \t]*(#[^\n]*)?\n(.*?)(?=\n\1\S|\Z)',chr(10)+text+chr(10),re.S));t=open('tests/gates.yml',encoding='utf-8').read();gblk=lambda n:blk(t,n);st=open('tests/suites.yml',encoding='utf-8').read() if os.path.isfile('tests/suites.yml') else '';sblk=lambda n:blk(st,n) if n else '';excl=lambda n:(lambda m:(m.group(1) if m else ''))(re.search(r'\n[ \t]+exclude_tags:[ \t]*\[([^\]]*)\]',chr(10)+sblk(n)+chr(10)));suiteof=lambda gb,k:(lambda sub:(lambda m:(m.group(1) if m else None))(re.search(r'\n[ \t]+suite:[ \t]*([A-Za-z0-9_-]+)',chr(10)+sub+chr(10))) if sub else None)(blk(gb,k)) or (lambda m:(m.group(1) if m else ''))(re.search(r'\n[ \t]+'+k+r':[^\n]*suite:[ \t]*([A-Za-z0-9_-]+)',chr(10)+gb+chr(10)));f1u=suiteof(gblk('f1-fast'),'unit');f4u=suiteof(gblk('f4-unit'),'unit');f1i=suiteof(gblk('f1-fast'),'integration');f4i=suiteof(gblk('f4-integration'),'integration');f4e=suiteof(gblk('f4-e2e'),'e2e');uok=bool(f1u) and bool(f4u) and f1u!=f4u and '@critical' not in excl(f1u) and '@critical' in excl(f4u);iok=bool(f1i) and bool(f4i) and f1i!=f4i and '@critical' not in excl(f1i) and '@critical' in excl(f4i);eok=bool(f4e) and '@critical' in excl(f4e);sys.exit(1 if (uok and iok and eok) else 0)"
paths: tests/suites.yml tests/gates.yml
summary: 重要テストが、通常の実行と重要専用の実行で二度走っている。通常側のスイートから重要テストを外して一度だけにする
---

## 何が変わったか

**出荷の前には、テストを2通りの形で走らせている。**

1. **通常の実行** — 結果が揺れる試験や、期限つきで外しているものを除いて走らせる
2. **重要テストだけの実行** — **何も除かずに**走らせる(除外に紛れた重要テストを拾うため)

**この2つが、同じ重要テストを二度走らせている。** 通常の実行の側が、重要テストを外して
いないためである。**重要テストが増えるほど、無駄な時間が増える。**
利用者の操作を端から端まで試す種類のテストでは、**準備と後片付けも二度払う。**

**2026-09-15 から、通常の実行の側は「重要でないテスト」に絞る**
(裁定。検査の記録は `histories/inspection-28.md` の B-6)。

**確かめるものは1つも減らない** — 通常の実行が「重要でないもの」、もう一方が「重要なもの」を
受け持つので、**合わせた対象は絞る前と1件も変わらない。**

## 手順

**判断が要る移行である。** スイートの中身はプロジェクトごとに違う。

1. **`tests/gates.yml` を開き、`f1-*`(構築ループ)と `f4-*`(出荷判定)が
   `unit` / `integration` の各キットでどのスイート名を呼んでいるかを見る。**

2. **f1 と f4 が同じスイート名を共有しているものだけを複製する** ★ — 既定では
   `f1-fast` / `f1-unit` / `f1-integration` と `f4-unit` / `f4-integration` が
   同じ `unit` / `integration` を指している。**その名前へ直接 `@critical` を足さない**
   (足すと、構築ループが読む側からも重要テストが消える)。代わりに、
   出荷判定専用の複製スイート(例: `unit-noncritical` / `integration-noncritical`。
   `include` は元と同じ)を新設し、**複製の側にだけ** `exclude_tags` へ
   `@critical` を足す。`f4-unit` / `f4-integration` の `suite:` をその複製へ
   向け替え、**`f1-*` が呼ぶ `unit` / `integration` 本体は無変更のまま残す。**

   ```yaml
   unit-noncritical:
     include: [<unit と同じ include>]
     exclude_tags: ["@flaky", "@critical"]
   ```

   ```yaml
   # tests/gates.yml
   f4-unit:
     unit: { suite: unit-noncritical, forbid_skip: false }
   ```

3. **`f4-e2e` が呼ぶスイート(既定は `e2e-full`)は複製しなくてよい** — `f1-*` の
   どのキットも E2E を呼ばないので、共有による事故が起きない。既定どおり、
   そのスイート自身の `exclude_tags` に直接 `@critical` を足してよい。

4. **重要テストだけを走らせる側(`critical-*`)は触らない** — あちらは
   `exclude_tags` を空にしてあり、それがこの仕組みの要である。

5. **構築の途中で使うスイート(`f1-*` が呼ぶもの)は狭めない** ★ —
   あれは速く回すための実行であって、出荷してよいかの判定ではない。
   狭めると、書いている最中に重要テストが1度も走らなくなる。
   **手順2で複製を新設するのは、この条項を満たしたまま出荷判定側だけを絞るためである。**

## 気をつけること

**すべてのテストに `@critical` を付けているプロジェクトでは、出荷判定側の実行が
「対象0件」になる。それは正常である** — 重要テストだけの実行が全部を受け持っている。
出荷の判定は、その「対象0件」を合格として扱う。

**逆に、`@critical` を1件も付けていないプロジェクトでは、何も変わらない。**

**f1 と f4 が最初から別のスイート名を使っているプロジェクトでは、手順2の複製は不要である**
(共有していないので、直接 `exclude_tags` に `@critical` を足してよい)。

## 移らなかったときに何が起きるか

**壊れはしない。** 同じテストが二度走るだけで、結果は変わらない。
**払い続けるのは時間である** — 重要テストの本数に比例して増える。
