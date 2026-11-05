---
id: 2026-09-14-codex-role-injection
since: 2026-09-14
kind: judgment
detect: c=.colabtmux/colabtmux.conf; test -f "$c" || c=colabtmux.conf; test -f "$c" || exit 1; test -n "$(ls -A .agents/skills 2>/dev/null)" || exit 0; test -L AGENTS.md || exit 0; exit 1
paths: AGENTS.md .agents .codex
summary: codex にも起動時に役を渡せるようになった(起動の組み立ては launch-agent.py に1本化。.agents/skills/ のリンクで .claude/skills/ の正本を codex にも読ませる)
---

# 2026-09-14 codex にも起動時に役を渡す — 起動の組み立てを1本化し、スキルのリンクを張る

対象: **`colabtmux` で艦隊を動かしているプロジェクト**(`colabtmux.conf` と `AGENTS.md` が在る)。
艦隊を使っていないなら、当てるものは何も無い。

## 何が変わったか

**codex にも「起動時に役を注入する口」が在ることが分かった**(codex-cli 0.154.0 で実測)。
これまでの規範は「codex にはその口が無い」という前提で書かれており、**codex の役は作業指示が
ファイルをパスで名指し、本人が読む**形だった。読むかどうかが相手任せなので、claude 側には無い
「読み損なう経路」がそこだけに在った。

あわせて、**codex にもスキルが在る**ことが分かった。`.agents/skills/<名前>` に
`.claude/skills/<名前>` へのシンボリックリンクを張れば、**`.claude/skills/` の正本がそのまま
codex のスキルとして読み込まれる**(写しは1つも要らない)。

この2つで、**claude と codex のどちらでも中央エージェントにも作業エージェントにもなれる。**

## 上書き展開では直らないもの(= ここで当てるもの)

**この版で、配布物に入るものが増えた** ★ — `AGENTS.md`(`CLAUDE.md` へのリンク)・
`colabtmux.conf`・**`.agents/skills/` のリンク**の3つである。**どれもプロジェクト固有の値を
持たないので、展開すれば正しい姿になる。** だから、ここで手を当てるのは**残り2つだけ**である。

> **2026-09-15 訂正** — この節は当初「配布物に入るものが増えた3つ」に
> `.codex/config.toml` を数え、`.agents/skills/` のリンクは入らないと書いていた。
> **どちらも逆である。** リンクは配布物に入り(固めるときもリンクのまま入り、展開しても
> リンクに戻る)、`.codex/config.toml` は**入らない** — あそこはプロジェクト専用の
> `CODEX_HOME` の置き場でもあり、上書きすると codex がこのディレクトリを信頼した記録と
> ブラウザQAの接続先の許可リストが消えるからである。**無いときだけ `/setup` が作る。**

| | なぜ展開で直らないか |
|---|---|
| **`.codex/config.toml`** | 配布物に入っていない(**上書きしてはならないファイル**なので、`/setup` が無いときだけ作る) |
| **`AGENTS.md` に書き足していたもの** | 旧版では1回だけ複製されるファイルだったので、**展開で上書きされて消える**。消えたものの始末だけが手作業である |

**加えて、codex を使うなら1手要る** — **そのディレクトリを codex に信頼させること。**
信頼していないプロジェクトでは `.codex/config.toml` が丸ごと無視され、codex は書き込みの
たびに人間へ問い、**ウィンドウがそこで止まる。**

## 手順

### 1. codex にこのディレクトリを信頼させる(codex を使うなら)

```bash
codex          # 対話で1度だけ起動し、信頼するかの問いに答える。そのまま終了してよい
```

`~/.codex/config.toml` の `[projects."<絶対パス>"]` に残る。**以後 `.codex/config.toml` が効く。**

### 2. `.agents/skills/` のリンクを確かめる(`.codex/config.toml` も)

```bash
mkdir -p .agents/skills
for d in .claude/skills/*/; do
  name=$(basename "$d")
  [ -e ".agents/skills/$name" ] || ln -s "../../.claude/skills/$name" ".agents/skills/$name"
done
ls -l .agents/skills/ | head
```

**リンクは配布物に入っているので、展開だけで揃っているはずである**(2026-09-15 の訂正)。
上の行は**欠けていたときの張り直し**であり、既に在るものは飛ばすので何度打ってもよい。
リンクが無くても行き止まりではない — codex は作業指示が名指した `SKILL.md` を
ファイルとして読む経路を持っている。

**`.codex/config.toml` は、無いときだけ作る。既に在るものは1バイトも触らない。**

```bash
mkdir -p .codex
cp -n .claude/templates/codex-config.toml .codex/config.toml
```

**`.gitignore` に `.agents/` を足さないこと。** リンクは git で共有する
(clone した人が張り直さずに済む)。

### 3. `AGENTS.md` に書き足していたものの始末

**`AGENTS.md` は `CLAUDE.md` へのシンボリックリンクになった。** 旧版で書き足していた内容は、
展開の時点で消えている。

```bash
git diff HEAD~1 -- AGENTS.md      # 展開の前後で何が消えたかを見る(展開をコミットしているなら)
test -L AGENTS.md && echo "リンクになっている(正しい)"
```

**消えて困る書き足しが在ったら、行き先を選ぶ。** `AGENTS.md` はもう `CLAUDE.md` そのものなので、
**そこへ戻すのは「全役が毎回読むものに足す」ことである**(`CLAUDE.md` はそれだけを持つ決まりである)。

| 書き足していたもの | 行き先 |
|---|---|
| **全役が守るもの** | `CLAUDE.md`(= `AGENTS.md`)へ。**次の展開でまた消えるので、キットへ戻す**(`/kit-improve`) |
| **書く役・判定する役だけのもの** | `.claude/directions/core.md` へ(同じく `/kit-improve` でキットへ戻す) |
| **この1つのプロジェクトの事情** | `docs/` へ。**キットのファイルに書かない** |

**次の型は戻さない** — 新しい仕組みと食い違う。

| 戻さないもの | なぜ |
|---|---|
| 「あなたは…**作業エージェント**である」 | **中央エージェントも同じファイルを読む。** 役は起動時に別で渡る |
| 「**作業指示は1件だけ来る**」 | 同上。中央エージェントには当てはまらない |
| 「あなたの役は作業指示に書かれている。最初に読むこと」 | **廃止。** 役は起動時に入る |
| 「codex にはスラッシュコマンドとしてのスキルが無い」 | **事実でなくなった**(`.agents/skills/` のリンクで正本が読み込まれる) |

**「完了の返信は1回だけ」「9分以内だけ待つ」は `CLAUDE.md` §2 が持っている** — 二重に書かないこと。

### 4. 確かめる

```bash
python3 .claude/scripts/test-launch-agent.py              # 起動コマンドの組み立ての自己検査
python3 .claude/scripts/launch-agent.py codex work --print | head -c 200
test -L AGENTS.md && ! grep -q 'colabtmux:begin' CLAUDE.md && echo "リンクも中身も正しい"
```

`--print` は**起こさずに組み立てた起動行を表示するだけ**である。
`developer_instructions=` の後ろに役の本文が入っていれば正しい(パスだけなら間違い)。

**`colabtmux start` は管理ブロックを `AGENTS.md` の末尾に足す** — リンクなので、
書き込まれるのは `CLAUDE.md` である。入っていたらその区間を消し、配布物1を展開し直す。

## 当てなくてよい場合

- **艦隊を使っていない**(`colabtmux.conf` が無い)
- **codex を混ぜていない** — 手順1と2は飛ばしてよい。手順3だけは、`AGENTS.md` に書き足しが
  在ったなら当てる。
