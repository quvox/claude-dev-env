---
id: 2026-11-22-gemini-modes
since: 2026-11-22
kind: judgment
detect: test -f colabtmux.conf || exit 1; grep -qE '^判断完了: [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$' .claude/missions/gemini-modes.md 2>/dev/null && exit 1; exit 0
paths: .claude/missions
summary: gemini を使うモード(g1/g2)と、a1 で codex が使えないときの縮退先 a1g を足し、codex のモデル名を新しい名前へ替える
---

# 2026-11-22 gemini を使えるようにする(g1/g2/a1g)と、codex のモデル名の更新

## 何が変わったか

**1つめ。gemini が使えるようになった。** gemini は Antigravity CLI(コマンド名 `agy`)で動く。
新しいモードが2つ足された。正は `.claude/directions/orchestration.md` §1.2.1 と §1.5 である。

- **g1** — 中央と作業役が gemini、`@review`・`@survey`・`@qa` が claude(a1 の gemini 版)。
- **g2** — gemini だけ(a2・o2 の gemini 版)。画面を触る `@qa` は起こせない(gemini が画面を触れるかが未確認のため)。
- 中央が gemini で、人間の明示が無いときの既定は **g1** である(claude なら a1、codex なら o1 のまま)。

**2つめ。a1 で codex が使えないときの縮退先が変わった。** これまでは直接 a2(claude だけ)へ縮退した。
これからは、**まず相手側だけを gemini に替えた `a1g`** へ縮退する。中心は claude のままである。
gemini も使えないときは、**これまでどおり a2 へ縮退する**(その値は凍結のまま変えていない)。
`a1g` の `@qa` だけは claude のままである(画面を触る口が gemini にあるか未確認のため)。

**3つめ。codex のモデル名を新しい名前へ替えた。** 重い層は `gpt-6.1-sol` → `gpt-6.2-sol`、
軽い・中の層は `gpt-6-luna` → `gpt-6.1-terra`。層と effort は変えていない。
`colabtmux.conf`(配布物)の codex の起動例も `gpt-6.2-sol` へ替わっている。

**4つめ。gemini のモデルが無いときの代わり。** 指定した gemini のモデルがアカウントに無いときは、
`launch-agent.py` が `gemini-3.8-flash` / `high` に替えて起こす(gemini だけ。claude と codex は替えない)。
**gemini の 4 系(`gemini-4-neon` など)は、4 系を使えるプランのアカウントでだけ動く。**
使えないアカウントでは、表の値のつもりで起こしても、実際には `gemini-3.8-flash` で動く。

## 手順

1. 人間へ確かめる。**gemini を使わないなら、設定も台帳も変えない。** 次の3つだけを知らせる。
   - a1 のプロジェクトは、codex が使えないとき、まず gemini を試すようになった。
     gemini を入れていなければ、これまでどおり a2 へ縮退する。
   - codex のモデル名が替わった。**そのアカウントで新しい名前(`gpt-6.2-sol` / `gpt-6.1-terra`)が
     使えるかは、実際に起こして確かめるまで分からない。**
   - 使えないときは、`colabtmux.conf` の codex の起動例か、起動行のモデルを、使える名前へ人間が直す。
2. **gemini を使う場合だけ**、次を確かめる。
   - `agy` が入っていて、サインイン済みか(`agy models` が一覧を出す)。
   - **端末の砂箱が使える環境か。** 使えない環境では `agy --mode auto` が
     「`--mode auto is not available`」と警告し、承認を求めるモードへ戻って無人にならない。
     そのときは gemini を不調として扱う(`orchestration.md` §1.3)。
   - 4 系を使えるプランか(`agy models` に `gemini-4-neon` が出るか)。出なければ 3.8 で動く。
3. 判断と日時を `.claude/missions/gemini-modes.md` へ残す(`判断完了: <YYYY-MM-DD HH:MM>`)。
   **このファイルは移行判断の済否だけを示すもので、配車設定の正本ではない。**
   要るが判断待ちのまま `判断完了:` を書いて済扱いにしない。
4. 進行中のミッションの台帳は触らない。a1g・g1・g2 は、台帳の「選択モード」「実効モード」の欄が
   これらの値を取れるようになっただけである(`orchestration.md` §7)。
   `python3 .claude/scripts/stamps.py record --mode <モード> --executor <エンジン> ...` も、
   gemini と新しいモードを受け付けるようになっている。

## 移らなかったときに何が起きるか

gemini を使わないプロジェクトは、ほとんど何も変わらない。**ただし a1 のプロジェクトで codex が
使えなくなったとき、gemini を入れていなければ、これまでどおり a2 へ縮退する** — 動きは変わらない。
**codex の新しいモデル名がそのアカウントに無いと、codex の役が起動できない。** 人間が気づかないと、
`@review` などが返らないまま待つことになる。起動時の標準エラーか、ウィンドウの画面で確かめられる。
gemini を使いたいのに砂箱を確かめないと、承認待ちで止まる実行役ができる。
