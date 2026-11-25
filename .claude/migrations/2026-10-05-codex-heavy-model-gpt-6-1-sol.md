---
id: 2026-10-05-codex-heavy-model-gpt-6-1-sol
since: 2026-10-05
kind: mechanical
detect: c=.colabtmux/colabtmux.conf; test -f "$c" && grep -qE '"--model", *"(gpt-6-sol|gpt-5[.]6-sol|gpt-6[.]1-sol)"' "$c"
paths: .colabtmux/colabtmux.conf
summary: codex の重い側のモデル名が gpt-6.2-sol になった。.colabtmux/colabtmux.conf の codex の起動行に残る古い名前(gpt-6-sol・gpt-5.6-sol・gpt-6.1-sol)を直す
---

## 何が変わったか

**codex の重い層のモデル名を `gpt-6.2-sol` に改めた**(2026-11-22。人間の指示)。**この移行は
2026-10-05 に `gpt-6.1-sol` への書き換えとして作ったが、その後さらに上がったので、
2026-11-22 に行き先を `gpt-6.2-sol` へ直した**(移行の識別名は、記録との対応が切れないよう変えていない)。
古い名前は3つ: `gpt-5.6-sol`、`gpt-6-sol`、`gpt-6.1-sol`。いずれも移行なしで配られていた。
軽い層の `gpt-6-luna` は変わらない。モデルの対応表の正は
`.claude/directions/orchestration.md` §1.5 である。

規範とリポジトリ直下の `colabtmux.conf` は配布物であり、新しい版を展開すれば上書きされて直る
(`.claude/skills/setup/SKILL.md` の ①)。**直らないのは `colabtmux` が自分の状態の置き場に作る
`.colabtmux/colabtmux.conf` である** — 配布物に含まれないので、上書き展開では更新されない。
だからそれを持つプロジェクトでは、codex で中央エージェントを立てる起動行
(`[agent_kind.codex]` の `command`)に古い名前が残る。

## 手順

見るのは `.colabtmux/colabtmux.conf` だけである(無ければこの移行は要らない)。
**探すのは起動行の値だけ**である — 注記に残る過去の名前は経緯であって、直す対象ではない:

```bash
grep -nE '"--model", *"(gpt-6-sol|gpt-5[.]6-sol|gpt-6[.]1-sol)"' .colabtmux/colabtmux.conf
```

出た行の `--model` の値を `gpt-6.2-sol` に置き換える。**古い名前として数えるのはこの3つだけである**
— 「`gpt-6.2-sol` でない sol は古い」と読むと、名前が次に上がったときにこの移行が新しい名前を
6.2 へ戻し、人間が意図して書いた名前も黙って上書きする。**`gpt-6-luna` は触らない。**
**雛形で丸ごと上書きしてはならない** — このファイルにはこのプロジェクトの値が在りうる。

走っている codex のウィンドウは起こされた時点のモデルのまま動いている。揃えたいなら、
返っていない結果と書きかけを回収してから起こし直す(`orchestration.md` §1.2.1)。

## 移らなかったときに何が起きるか

`colabtmux start --kind codex` で立てた中央エージェントだけが古い名前で起き、規範の表
(`gpt-6.2-sol`)と食い違う。その名前がもう使えない環境では、中央エージェントが起動しない。
