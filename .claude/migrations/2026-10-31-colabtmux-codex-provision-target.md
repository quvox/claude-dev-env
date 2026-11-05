---
id: 2026-10-31-colabtmux-codex-provision-target
since: 2026-10-31
kind: mechanical
detect: grep -q 'colabtmux:begin' CLAUDE.md && exit 0; test -L AGENTS.md || exit 1; test -f .colabtmux/colabtmux.conf || exit 1; python3 -c 'import sys,tomllib; d=tomllib.load(open(".colabtmux/colabtmux.conf","rb")); sys.exit(3 if d.get("agent_kind",{}).get("codex",{}).get("provision_target")==".colabtmux/usage-codex.md" else 0)' 2>/dev/null; r=$?; test $r -eq 3 && exit 1; test $r -eq 0 && exit 0; exit 2
paths: .colabtmux/colabtmux.conf CLAUDE.md
summary: codex の教え込みの書き込み先を .colabtmux/usage-codex.md に指定する。指定しないと codex を起こすたびに CLAUDE.md の末尾へ道具の管理ブロックが入る
---

## 何が変わったか

colabtmux は codex を起こすたびに、使い方の案内(管理ブロック `<!-- colabtmux:begin v=1 -->` 〜
`<!-- colabtmux:end -->`)を**既定では `AGENTS.md` へ**書き込む。このキットでは **`AGENTS.md` は
`CLAUDE.md` へのシンボリックリンク**なので、書込みは**全役が読む `CLAUDE.md` の末尾**に入る
(2026-10-31 に実測。codex の `@review` を1体起こしただけで約100行が入り、そのままコミットされた)。

雛形の `colabtmux.conf` は 2026-10-31 から `[agent_kind.codex]` に
`provision_target = ".colabtmux/usage-codex.md"` を持つ(理由はその節のコメント)。
**ただし colabtmux は設定を状態の置き場所(`.colabtmux/colabtmux.conf`)から読み、直下の雛形は
読まない**(colabtmux 側の `docs/02-design/contracts/conf.md`「置き場所は状態の置き場所の中」)。
**上書き展開だけでは、実際に効く設定にこの1行が入らない。** `.colabtmux/colabtmux.conf` は
最初の `colabtmux start` が既定値で作るので、**まだ無いプロジェクトではこの移行はまだ当てられない**
(`detect` は「済んだ」を返す)— 最初の `start` の後、codex を起こす前に、もう一度
`kit-migrate.py check` を打つ(`/setup` §2.2 も同じことを言う)。
**この移行で防げない場合が1つ残る** — 最初の `start` を codex で打つ(`colabtmux start --kind codex`)と、
既定値の設定のまま codex の教え込みが `CLAUDE.md` へ入る。そのときはこの移行の手順3で消す
(`detect` は混入を見て「要る」を返す)。根は「colabtmux が直下の雛形を読まない」ことであり、
この移行の範囲の外である。

`detect` は TOML として読み、`[agent_kind.codex]` の値だけを見る(行の grep では、別の種の節に
同じ値が在るだけで「済んだ」と誤る)。`python3` に `tomllib` が無い・設定が TOML として読めない
ときは「判定できなかった」を返す。

## 手順

1. 書く先は `.colabtmux/colabtmux.conf` である(`c=.colabtmux/colabtmux.conf`)。

2. `$c` の `[agent_kind.codex]` に1行足す。**表をもう1つ書かない** — 同じ名前の表が2つ在ると
   TOML として読めず、colabtmux が終了コード2で止まる(2026-10-31 に実測)。表が無ければ作る:

   ```toml
   [agent_kind.codex]
   provision_target = ".colabtmux/usage-codex.md"
   ```

   足した後に `python3 -c "import tomllib;print(tomllib.load(open('$c','rb'))['agent_kind']['codex'])"`
   で読めることを確かめる。
3. `CLAUDE.md` に `colabtmux:begin` が在れば、その区間(`begin` の行から `end` の行まで)と、
   **`begin` の直前に道具が足した空行1行**を消す(道具はブロックの前に改行を1つ挟んで書く)。
   **消した後の `CLAUDE.md` は配布物と1バイトも違わない**はずである —
   `python3 .claude/scripts/kit-manifest.py check` が `CLAUDE.md` を差異に挙げなければよい。

**`colabtmux provision` を確かめのために打たない** — 定義された全種へ配るので、起こしていない
gemini 向けの `GEMINI.md` がルートに生える。次に codex を起こしたとき、`CLAUDE.md` が変わらず
`.colabtmux/usage-codex.md` ができていれば効いている。

## 移らなかったときに何が起きるか

codex を起こすたびに、`CLAUDE.md` の末尾へ道具の管理ブロックが入る。`CLAUDE.md` は全役が
起動時に読むので、**キットの規範と食い違う道具の案内**(「`--json` なしで全文が読める」—
`orchestration.md` が「道具の案内ではなく、この節を信じること」と名指しで退けているもの)が全エージェントの文脈に載り、気づかなければ
そのままコミットされる。`kit-manifest.py check` も `CLAUDE.md` を「改造した」と出し続ける。
