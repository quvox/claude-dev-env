---
id: 2026-09-12-runner-bin-excludes
since: 2026-09-12
kind: judgment
detect: python3 -c "import json,sys,pathlib;p=pathlib.Path('.claude/scripts/flow-config.local.json');d=json.loads(p.read_text()) if p.is_file() else {};r=[x for x in d.get('code_roots',[]) if 'tests' in x];e=d.get('code_excludes',[]);sys.exit(1 if (not r or any(x.rstrip('/')=='tests/tools/bin' for x in e)) else 0)"
paths: .claude/scripts/flow-config.local.json
summary: テストを走らせる道具の実行ファイルの置き場を、変更監視の除外に入れる
---

## 何が変わったか

テスト基盤を入れたプロジェクトは、テストコードの置き場 `tests/` を**変更監視の対象**
(`code_roots`)に入れている。ところが同じ `tests/` の下には、**テストを走らせる道具の実行
ファイル**(`tests/tools/bin/`)も置かれ、git で管理されている(clone しただけで走らせられる
ようにするため)。

**そのため、道具を新しい版に差し替えただけで、実装整合(F3)と全試験区分(F4)の鮮度スタンプが
まとめて失効する。** 中身が1行も変わっていないのに、全部やり直しになる。

この設定は `flow-config.local.json`(プロジェクトが持つファイル)に在り、**配布物から除外されて
いるので、上書き展開では直らない。**

## 手順

1. `.claude/scripts/flow-config.local.json` の `code_excludes` に `tests/tools/bin/` を足す。
   ファイルが無ければ、必要な鍵だけを持つものを作る(`flow-config.json` の `_comment` が
   書式の正である)。

   ```json
   {
     "code_excludes": ["tests/tools/bin/"]
   }
   ```

   既に `code_excludes` が在るなら、その配列へ1つ足す(**既存の項目を消さない**)。

2. **足したら、そのぶん鮮度スタンプは失効する**(宣言を変えると失効する — `flows.md` §2)。
   次の検証の周で取り直す。

## 気をつけること

**「読まないから安全」ではない** ★ — あの実行ファイルは試験の証拠を作っている当人であり、
版が変われば絞り込み・skip の判定・カバレッジの読み取りが変わって、**同じテストが別の結果を
出しうる。** 除外したままだと、道具を差し替えても全試験区分が green のまま出荷できる。

**道具の版を上げたときは、試験区分の鮮度スタンプを手で失効させること。**
**失効させる操作は無いので、red を書いて上書きする**:
`python3 .claude/scripts/stamps.py record verify-tests red --scope <試験区分>`
(`unit` / `integration` / `e2e` / `qa` の、走らせている試験区分ぶん)。この移行が消すのは
「**版を上げていないのに失効する**」ほうであって、「版を上げたときに確かめ直す」ほうではない。

## 移らなかったときに何が起きるか

道具を更新するたびに、実装整合と全試験区分の確認済みの印が失効し、**中身が変わっていない
コードに対して検証を回し直すことになる。** 動作は壊れないが、毎回その費用を払う。
