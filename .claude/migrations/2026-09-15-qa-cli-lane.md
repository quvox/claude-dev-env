---
id: 2026-09-15-qa-cli-lane
since: 2026-09-15
kind: judgment
detect: python3 -c "import json,sys,os;p=[q for q in ('.claude/scripts/flow-config.local.json','.claude/scripts/flow-config.json') if os.path.isfile(q)];s=[json.load(open(q,encoding='utf-8')).get('f4_scopes') for q in p];sys.exit(0 if any(isinstance(x,list) and 'qa' not in x for x in s) else 1)"
paths: .claude/scripts/flow-config.local.json .claude/scripts/flow-config.json docs/02-design/system.md docs/02-design/environments.md
summary: 画面が無いことを理由に qa 試験区分を外しているなら、サブコマンドの有無で判断をやり直し、02 の操作面の宣言と CLI 検証の実行条件を作る
---

## 何が変わったか

**探索的QA(`qa` 試験区分)の実体が2つになった**(2026-09-15 の人間の裁定)。
これまでは「ブラウザで画面を触るレーン」しか無く、**画面を持たないプロジェクトは
`f4_scopes` から `qa` を外してよい**ことになっていた。

いまは兄弟のレーンが在る — **サブコマンドを実際に叩いて、台本(テスト)に書いていない
ところで壊れていないかを探すレーン**(`.claude/skills/cli-qa/SKILL.md`)である。
したがって**「画面が無い」は `qa` を外す理由にならない**。

**`qa` を外してよいのは、人が直接操作する面(画面もサブコマンドも)が1つも無い成果物だけ**
である — 他のプログラムから呼ばれるだけの部品(ライブラリ)などが、それに当たる。

**この移行は宣言ファイルの1行だけを触る。** 配布物を上書きしても直らないのは、
`flow-config.local.json` がプロジェクト自身の持ち物だからである。

## 手順

**判断が要る移行である。** 機械は「`qa` が外れている」ことしか見られず、
**それが正しいかどうかは、この成果物が何であるかによる。**

1. この製品に、**人が直接打つサブコマンド**が在るかを確かめる。
   在るなら手順2へ。**1つも無い**(他のプログラムから呼ばれるだけの部品である)なら、
   **何もしない** — いまの宣言のままで正しい。そのことを記録に1行残す。
2. `.claude/scripts/flow-config.local.json`(無ければ `flow-config.json`)の
   `f4_scopes` に `"qa"` を戻す。

   ```json
   { "f4_scopes": ["unit", "integration", "e2e", "qa"] }
   ```

3. 戻したら、**`qa` の鮮度スタンプは red から始まる。** 次の `/verify-tests` が
   探索的CLI QA を起こして green にする(手順の正は `.claude/skills/cli-qa/SKILL.md`)。
4. **02 の「操作面の宣言」を今の形にする** ★ — `docs/02-design/system.md` の見出しが
   旧い「## UI設計」の1行のままなら、2行の形に直す(雛形は `.claude/templates/02-system.md`):

   ```
   - 画面: なし(この製品は端末から打つ道具である)
   - コマンドの面: あり — 中身は docs/ux/(コマンド一覧は docs/ux/flows.md)
   ```

   **ここが、qa 試験区分の適用外を宣言する唯一の場所である**(`.claude/directions/02-design.md`)。
   探索的CLI QA は**この宣言**を見て適用外かどうかを決める — **台帳(`docs/ux/flows.md` の
   「コマンド一覧」)の有無では決めない。**
5. **`docs/02-design/environments.md` に「CLI 検証の実行条件」の節を作る** ★ —
   成果物のビルド、実行ファイルの場所、**隔離した作業環境の用意と後始末**、
   壊してはならないもの。**探索的CLI QA はこの節を名前で読む**ので、無ければそのレーンは
   「環境の不備」で止まる(`.claude/skills/cli-qa/SKILL.md` §1 の 2)。
   雛形の表は `.claude/templates/02-environments.md` に在る。
6. **操作面の台帳をこの移行で書き起こさない** ★ —
   `docs/ux/flows.md` の「コマンド一覧」と `docs/ux/commands/` は、
   **次にそのサブコマンドを触る `/build` が作る**(遡って全部を埋めない、という同じ日の裁定。
   規則の正は `.claude/directions/ux.md`「達成条件」の代金の段)。
   台帳がまだ無いあいだ、探索的CLI QA は `docs/01-requirements/` の `UC-nn` と実物だけを
   頼りに走り、「記述が無い」ことを報告に1行書く(`cli-qa/SKILL.md` §1)。

## 移らなかったときに何が起きるか

- **サブコマンドを持つ製品が、探索的QAを1度も通さずに出荷できる。**
  台本(テスト)は「書いてあるものが通ること」しか見ないので、
  **引数の取り違え・中断したあとの残骸・読めないエラー文言は、誰にも見られないまま出る。**
- デプロイゲートは `f4_scopes` に載っている試験区分しか要求しないので、
  **何も鳴らない。**「見ないと決めた」と「決め忘れた」が区別できない状態が続く。
- 手順4・5 を飛ばして `qa` だけ戻すと、**探索的CLI QA は起きた先で止まる** —
  適用外かどうかを決める宣言(手順4)も、どこで叩けばよいかの宣言(手順5)も無いからである。
  **止まること自体は正しい振る舞いだが、その run は red のまま人間へ返る。**
