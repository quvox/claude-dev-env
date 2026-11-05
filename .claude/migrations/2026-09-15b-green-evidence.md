---
id: 2026-09-15b-green-evidence
since: 2026-09-15
kind: judgment
detect: python3 -c "import json,os,sys;p='.claude/state/stamps.json';sys.exit(1 if not os.path.isfile(p) else (0 if any(e.get('verdict')=='green' and not e.get('evidence') for e in json.load(open(p,encoding='utf-8')).get('latest',{}).values()) else 1))"
paths: .claude/state/stamps.json artifacts/ .gitignore
summary: 合格(green)の記録に証跡の添付が要るようになった。証跡を持たない既存の合格記録は、次にその検証を回したときに置き換わる
---

## 何が変わったか

**検証が「合格した」と記録するとき、実際に走らせた結果のファイルを添えることが必須になった**
(2026-09-15 の裁定。検査の記録は `histories/inspection-28.md` の A-7)。

これまで合格の記録は**完全な自己申告**だった。走らせた当人が「通った」と書くだけで、
**実際に何を走らせ、何が返ったのかは、どこにも残らなかった。**
デプロイしてよいかの判定はこの記録を読んで決まるので、**取り違えや思い込みを
打ち消すものが1つも無かった。**

いまは `record` に `--evidence <パス>` が要る:

```bash
python3 .claude/scripts/stamps.py record verify-docs green --evidence artifacts/verify-docs.log
```

- **合格(`green`)にだけ要る。** 不合格(`red`)には要らない。
- **複数渡してよい**(`--evidence a --evidence b`)。
- 機械が見るのは「**そのファイルが実在して、中身が空でないこと**」だけである。
  **中身が本物かどうかは見ない** — そこまでは別の仕組みの仕事である。
  それでも、後から人間や別のエージェントが**現物を開いて確かめられる**ようになる。

## このプロジェクトで何をするか

**急いで何かをする必要は無い。** 証跡を持たない既存の合格記録はそのまま読めるし、
デプロイしてよいかの判定も今までどおり動く。**次にその検証を回したときに、証跡つきの
記録へ置き換わる。**

用意しておくことが2つある:

1. **実行結果の置き場を決める。** 既定は `artifacts/` である。
   **そこはコードの置き場(`code_roots`)の外に置き、`.gitignore` に入れる** —
   入れないと、結果を書き出すたびに検証の記録が古くなる(`.claude/directions/flows.md` §2)。
   既に `artifacts/` を使っているなら、何もしなくてよい。
2. **検証を回す手順が、結果をファイルへ書き出しているか見る。** 画面に出して捨てていると、
   渡すパスが無い。`... 2>&1 | tee artifacts/<検証の名前>.log` のように、
   **画面にも出しつつファイルにも残す**形にする。

## 確かめ方

```bash
python3 .claude/scripts/stamps.py show      # 記録の一覧。evidence の欄が在るか見る
```
