---
name: setup
description: プロジェクト開始時のセットアップ。docs/ の骨格・git・解析の道具・艦隊の下ごしらえまで、判断の要らない準備を全部やる(質問なし)
model: sonnet
argument-hint: (引数なし)
---

# プロジェクトのセットアップ — 判断の要らない準備を全部

出力はすべて日本語で書く。

**このスキルが用意するのは、判断を要しないものの全部である** — 空のディレクトリ、雛形の逐語複製、
機械が導けるもの(`.gitkeep`、`build-index.py` が生成する索引、`colabtmux.conf` の
`[project] name` = このディレクトリの名前)、**道具の導入**(§2.1)、
そして**艦隊の下ごしらえ**(§2.2)。
**判断を要する文字を1つも書かない**: 仕様ドキュメント(00〜03)の本文、コード、
`callgraph-config.local.json` — **どれもここには属さず、このスキルは何も問わない。**

**「骨格だけ」を、機械的な準備を人間に残す理由にしない** ★ —
**判断を要しない準備をここで飛ばせば、それはそのまま人間の手作業になる。**
2026-08-31 に「`/setup` を打ったのに Python の道具が入らず、`AGENTS.md` も複写されず、
手作業が多すぎる」と報告された。**問わないことと、やらないことは違う。**

理由: 実行環境、lint / テストの正確なコマンド、解析する言語の構成は、
**この時点ではまだ存在しないことがある。** 存在しないものについて問えば「未定」しか返らず、
**推測すると SSOT に嘘が入る**(CLAUDE.md 原則1)。それらは**決まったときに、決まった場所で**
書かれる(§3)。

**このスキルが負う規範の節** — `.claude/directions/reading.md` のこのスキルの行。
それは**床**である: 多く読むことは決して違反ではない。
**読んでいない節から決めることが違反である**(原則9)。

## 1. いまの状態を確認する

- `docs/` が既に在る → **既存ファイルを1バイトも変えない**が、§2 は走らせる:
  `mkdir -p` と `.gitkeep` は既存のディレクトリに対して無害であり、**§2 以降の複写は、
  既に在るファイルを1つも上書きしない**(§2 は `cp -n`。§2.2 は在否と中身を見て、
  **既に在る本文には触らない** — 雛形を足すのは、colabtmux の管理ブロックしか無い
  `AGENTS.md` に対してだけである)。
  ブラウンフィールドのリポジトリには無関係な `docs/`(Sphinx、README)が在るのが普通で、
  **それを理由に §2 を飛ばすと骨格が作られず**、後のスキル
  (`/relations` §3A、`/retrofit` §5)が書く場所を失う。既に在ったものを並べ、**§2.1 以降**へ進む。
- git リポジトリの中に居るかを確認する: `git rev-parse --show-toplevel`
  - 成功 → **`git init` をしない**(親の中にリポジトリを入れ子にしない)。最上位のパスを報告する。
  - 失敗 → `git init` を走らせる。**コミットしない**(最初のコミットに何を入れるかは人間が決める)。
  - **ブランチはここでは切らない。** このスキルが作るのは空のディレクトリと雛形の逐語複写
    だけであり、**捨てたくなるものを何も作らない**からである(`git init` の直後は保護ブランチに
    居るが、コミットが1本も無い状態でもある)。
    **枝を切るのは、最初に `docs/` へ書き込むスキルの入口である** — 何も無いところから
    始めるなら `/build`、既にコードが在るプロジェクトへの導入なら
    **`/relations --apply`** である(`flows.md` §7.1)。
    **後者を落とさないこと** ★ — 以前ここは「最初に書込みを始めるのは `/build` だから、
    そこが切ればよい」と書いていたが、**導入の経路では `/build` は走らない。**
    その1文のせいで、導入は最初から最後まで保護ブランチの上で走っていた。

## 2. 骨格を作る

```bash
mkdir -p docs/00-requests/decisions docs/00-requests/examples \
         docs/01-requirements/decisions \
         docs/02-design/contracts \
         docs/03-impl/callgraphs docs/03-impl/relations docs/03-impl/contracts \
         docs/03-impl/tests docs/03-impl/environments \
         docs/03-impl/infra/local docs/03-impl/infra/dev docs/03-impl/infra/prod \
         docs/build-records docs/sheets docs/histories docs/issues docs/feedbacks
cp -n .claude/templates/pendings.md docs/pendings.md
cp -n .claude/templates/residual.md docs/residual.md
cp -n .claude/templates/03-features.md docs/03-impl/features.md
cp -n .claude/templates/docs-readme.md docs/README.md
find docs -type d -empty -exec touch {}/.gitkeep \;
python3 .claude/scripts/build-index.py
```

- `.claude/state/stamps.json`(鮮度スタンプ)と `.claude/state/releases.json`(リリースの台帳。`flows.md` §9)と `.claude/state/ids.json`(採番の控え。`issues-pendings.md` §2.2)は **git で共有する**。`.gitignore` に入れない:
  記録の中身はどれも中身から決まる値なので、**どこでも同じ答えが出る**ように作られている
  (`flows.md` §2)。追跡すると `record` のたびにツリーが汚れるが、それは
  **1周につき1回の専用コミット**と**明示のパスでの stage とコミット** で消える(同 §2)。

- `docs/03-impl/features.md` は**境界の定義**の雛形である。中身は `/relations` が起案し、
  人間が合意する(`.claude/directions/features.md`)。**ここで書いてはならない。**
- `docs/03-impl/feature-graph.md` は `cluster-features.py` が生成するので、**作ってはならない。**
- 空のディレクトリは `.gitkeep` で git に残す(`infra/dev` などはしばらく空のままである)。

## 2.1 解析の道具を用意する ★

```bash
python3 .claude/scripts/setup-tools.py     # 依存の導入先はキット専用 venv(.claude/.venv)だけ
```

**必ず走らせる。** Go / TypeScript / infra のコールグラフは、必須依存(tree-sitter・PyYAML)が
無いと**起動時に終了コード2で止まる** — 正規表現への縮退経路は無い(`.claude/tools-readme.md` §0)。
**プロジェクト側の環境にもホストにも何も入らない**ので、ここで走らせて壊れるものが無い。

- **終了コード 1(用意できなかったものがある)でも、このスキルは止まらない。** 骨格はもう
  出来ており、やり直しは**この1行を打ち直すだけ**である(venv は何度作り直してもよい —
  `.claude/.gitignore`)。落ちた理由と、その打ち直しの1行を §3 の報告に必ず書く。
  ネットワークの無い環境ではここが落ちるが、それは異常ではない。
- **`--host-tools` は打たない。** あれは opt-in の任意ツールで、無くても精度が1段落ちるだけである。
- **`.claude/scripts/requirements.lock` が書き換わることがある** — この環境で pip が実際に
  解決した版の記録であって、判断ではない。差分が出たら §3 でそう伝える(git が追跡している
  ファイルなので、黙って変わると次に `kit-manifest.py check` が「改造されている」と言う)。
- **解析しない言語の宣言(`callgraph-config.local.json` の `enabled: false`)はここで書かない** —
  それは判断である。§3 でそう伝える。

## 2.2 艦隊の下ごしらえ — 雛形2つ ★

**`colabtmux start` は、この2つのファイルが先に在ることを前提にする**(`orchestration.md` §1)。
どちらも**雛形の逐語複製**であり、判断を1つも含まないので、ここで済ませる。
**`start` のほうが先に走っていることもある**(中央エージェントがこのスキルを作業指示として
配車する経路)。だから**作る側と直す側の両方**を書いてある。

```bash
# ① colabtmux.conf — 無ければ雛形から。名前はこのディレクトリの名前にする
[ -f colabtmux.conf ] || python3 - <<'PY'
import json, os, pathlib
src = pathlib.Path(".claude/templates/colabtmux.conf").read_text(encoding="utf-8")
out = src.replace('name = "PROJECT"', "name = " + json.dumps(os.path.basename(os.getcwd())), 1)
pathlib.Path("colabtmux.conf.new").write_text(out, encoding="utf-8")
os.replace("colabtmux.conf.new", "colabtmux.conf")   # 書けたときにだけ置き換わる
PY

# ② AGENTS.md — 無ければ雛形から。colabtmux の管理ブロックしか無いなら、雛形をその上へ足す
if [ ! -f AGENTS.md ]; then
  cp .claude/templates/AGENTS.md AGENTS.md
elif [ -z "$(sed '/^<!-- colabtmux:begin/,/^<!-- colabtmux:end/d' AGENTS.md | tr -d '[:space:]')" ]; then
  { cat .claude/templates/AGENTS.md; echo; cat AGENTS.md; } > AGENTS.md.new && mv AGENTS.md.new AGENTS.md
fi
```

- **`[project] name` をディレクトリ名にするのは判断ではない** — colabtmux 自身が `--project` を
  省いたときに使う値と同じである。**`PROJECT` のまま残すと、1つの Slack チャンネルに集まる
  全プロジェクトが `[PROJECT]` と名乗る**(雛形の頭のコメント)。
- **ここを `sed` で書かないこと** ★ — 置換文字列の中で `&` と `\` は特別な意味を持ち、区切りに
  選んだ記号(`|` など)がディレクトリ名に現れれば `sed` 自体が失敗する。**しかもリダイレクトが
  先にファイルを作るので、失敗すると 0 バイトの `colabtmux.conf` が残り、次に走らせても
  `[ -f ]` が真になって永久に直らない**(2026-08-31 に `a|b` という名前で実測)。
  上の Python は最後まで書けたときにだけ `os.replace` で置き換える。
- **`AGENTS.md` に colabtmux の管理ブロック(`<!-- colabtmux:begin ... -->`)しか無いのは、
  `colabtmux start` が先に走った跡である**(そのとき colabtmux はこのファイルをブロックだけの
  内容で新規作成する)。雛形の中身を**ブロックの上へ**足す — 雛形自身がこの手順を書いている。
  **ブロックの中は編集しない。** あれは colabtmux のもので、次の起動で書き戻る。
- **本文が1行でも在る `AGENTS.md` には触らない** ★ — そのプロジェクトが自分で書いたものかも
  しれず、前置きも上書きも破壊である。**判定は「管理ブロックを取り除いた残りが空白だけか」で
  行う。** 「雛形の見出しが在るか」で判定してはならない(2026-08-31 に実測: 雛形と違う独自の
  `AGENTS.md` に雛形が前置きされた)。雛形より古いことが気になるなら、それは `/kit-migrate` の
  仕事であり、ここでは §3 でそう伝えるだけにする。
- **既に在る `colabtmux.conf` は上書きしない。** そのファイルはプロジェクトのものであり、
  中身の取捨は判断だからである。代わりに、この運用に要る3つの値が在るかだけを見て、
  欠けていたら §3 で名指す(**直すのは人間である**):

```bash
if [ -f colabtmux.conf ]; then
  for k in 'max_attempts' '[notify]' 'timeout_ms'; do
    grep -qF "$k" colabtmux.conf ||
      echo "colabtmux.conf に $k が無い(雛形: .claude/templates/colabtmux.conf)"
  done
fi
```

  この3つが要る理由は `orchestration.md` §1 が持つ(既定の `max_attempts` のままだと、
  **7分を超えて生成し続けた相手への配信が諦められる**)。

## 3. 作ったものと、次の一手を報告する

作ったディレクトリ・ファイル・git の状態を並べる。そのうえで次を述べる
(**ここで所有を定義し直さない**: 導入経路の正は CLAUDE.md §5 であり、
各スキルが自分の生成物を所有する):

> `docs/01-requirements/system.md`(技術制約)と `docs/02-design/environments.md`
> (lint/テスト/build の**厳密なコマンド**)は**まだありません**。
> **コマンドが実在してから書く**もので、下の経路の中で作られます。
>
> ツール依存の導入(`python3 .claude/scripts/setup-tools.py`。キット専用 venv に閉じます)は
> **こちらで済ませました**(§2.1)。出力をそのまま報告に貼ります — **用意できなかったものが
> あれば、その理由と「`python3 .claude/scripts/setup-tools.py` をもう一度打てば直る」ことを
> 必ず添えます。** Go / TypeScript / infra は必須依存が無いとコールグラフの解析が
> **起動時に止まります**(終了コード2。縮退経路はありません)。
> 精度が1段落ちるだけ(Tier3)で済むのは、外部依存を持たない shell / make です。
> その言語を解析しない選択は `callgraph-config.local.json` の `enabled: false` で明示してください
> — **これは判断なので、こちらでは書きません。**

艦隊(中央エージェント運用)で回すなら、続けて次を渡す:

> `colabtmux.conf` と `AGENTS.md` は用意しました(§2.2)。次に打つのはこの1行です:
>
> ```
> colabtmux start -- claude --permission-mode auto --model opus --effort high \
>   --append-system-prompt-file .claude/roles/orchestrator.md
> ```
>
> **`tmux attach` は要りません**(`start` がこの端末をそのまま繋ぎます)。
> **あなたがこの `/setup` を自分で打ったのではなく、すでに動いている場から自動で走った場合は、
> 上の1行はもう済んでいます。**
> **codex(別の AI)も混ぜるなら、もう1手あります** — そのディレクトリで一度 `codex` を
> 対話で起動して、信頼を与えてください。与えていないと、起動した直後に確認の問いで止まり、
> こちらからの指示が届きません。

そのうえで、当てはまるものを1つ渡す:

**A. コードも仕様ドキュメントも無い(グリーンフィールド)**

> `/build <やりたいことの説明>` を実行してください。構築記録と決定シートを作り、
> 論点を一括で伺ってから、00〜02 を書き、実装まで1ウィンドウで進めます。
> 最初のタスクでは 00〜03 のほぼ全部が新規作成になります。
> 要求を書く前の壁打ちが必要なら、このまま手伝います。

**B. コードは在るが仕様ドキュメントが無い(ブラウンフィールド導入)**

> `/relations all --apply --bootstrap` → `/retrofit` → `/verify-impl all` → `/verify-docs all` の順です。
> **この順序には理由があります**: 機能単位の境界も呼び出し関係も契約も 03-impl が無ければ引けず、
> 無い状態で 02 や 01 を書けば実装を見ていない当てずっぽうになります。
> 検証を F3 → F2 の順にするのも同じ理由です。逆順だと F3-all の書込みが F2-all の
> 鮮度スタンプを失効させ、覆い直しを1回必ず払います。

**C. コードも(古い / 規範に合わない)仕様ドキュメントも在る**

> B と同じ経路です。**ただし最初の1手だけ、既存仕様ドキュメントの状態で分かれます** —
> `docs/03-impl/relations/` が空で、かつ既存の 02 にモジュール分割定義が無いなら、B と同じ
> `/relations all --apply --bootstrap` です。02 に分割定義が既に在るなら「文書の無い既存コード」
> ではないので `--bootstrap` は成立せず(`/relations` §0 の3つ目)、`/relations all --apply` を
> 明示的にご指示ください(同 §0 の2つ目)。既存の分割定義を捨てる必要はありません。
> 既存仕様ドキュメントは `/retrofit` が仕分けて材料に使い、
> 過不足を直して規範準拠に書き直します(事実はコードが正。矛盾は全件列挙されます)。

最後に、この仕組みの要点を4つ述べる:

> ・SSOT(docs/00〜03)は常に「今のシステム」だけを書きます。変更は `/build` がその
>   タスクの範囲(クロージャ)の中で直接書き、出口で実装と突き合わせます。検証は独立した
>   verify 系フロー(文書整合・実装整合・試験)が周期的に行い、全部 green のときだけ
>   デプロイできます(及第ライン)。
> ・03-impl の中心は機能間連携仕様書で、コードから生成し、コードと 1:1 に保ちます。
> ・**実現方法はこちらで決めます** — テストの作り方、エラー処理の実装、ログ、内部命名、
>   要求に書かれていない設定値は、最初から委任済みです(`DS-01`〜`DS-08`。一覧と制約は
>   `.claude/directions/delegation.md`)。**代わりに、決めたことと理由と見直す条件を必ず
>   該当する仕様ドキュメントに書きます** — 実装を見て推測するしかない状態は作りません。
>   狭めたい範囲があれば `docs/00-requests/decisions/` に「決定」として書いてください。
> ・お伺いするのは、**外から見えて、かつ後から戻しにくい**判断だけです。タスクの入口に
>   決定シート1枚(問いが無ければゼロ)、無人の検証は質問シート1枚。
>   **「一括回答」に1行**書けば承認できます。
