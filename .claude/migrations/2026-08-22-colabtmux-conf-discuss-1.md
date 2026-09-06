---
id: 2026-08-22-colabtmux-conf-discuss-1
since: 2026-08-22
kind: mechanical
detect: c=.colabtmux/colabtmux.conf; test -f "$c" || c=colabtmux.conf; test -f "$c" && ! grep -q discuss-1 "$c"
paths: .colabtmux/colabtmux.conf colabtmux.conf
summary: colabtmux.conf の監視の除外に discuss-1 を足す。足さないと議論用のウィンドウで停止の誤報が鳴る
---

## 何が変わったか

議論用のウィンドウ(`discuss-1`)は人間の入力を待って静止するので、**掲示板の監視が
「止まった」と判定して Slack を鳴らす。** 雛形の `colabtmux.conf` は 2026-08-22 から
監視の除外に `discuss-1` を持っている(`orchestration.md` §1.6)。

**`colabtmux.conf` は導入時に1度だけ雛形から複写するファイルであり、配布物の上書き展開では
更新されない。** だから既存のプロジェクトには自分で足す必要がある。

## 手順

`colabtmux.conf` の `[monitor]` の `exclude_windows` に `"discuss-1"` を足す。
**除外は完全一致である**(前方一致は無いので、名前は `discuss-1` に固定する)。

```toml
exclude_windows = ["orchestrator", "discuss-1"]
```

雛形との差が他にも在るかは `diff "$c" .claude/templates/colabtmux.conf` で見る。
**雛形をそのまま上書きしてはならない** — `[project] name` はこのプロジェクトの値である。

**設定の置き場は2つありうる** ★ — `colabtmux` は自分の状態の置き場(`.colabtmux/`)の中に
設定を作る版があり、そのときリポジトリ直下には1つも無い。**先に `.colabtmux/colabtmux.conf`
を見て、無ければ直下の `colabtmux.conf` を見る**(この移行の `detect` もその順で見る):

```bash
c=.colabtmux/colabtmux.conf; test -f "$c" || c=colabtmux.conf
```

**片方だけを見る門は、設定が在るのに「無い」と読み、この移行を「不要」と表示する**
(実測 2026-09-01: `.colabtmux/` にだけ設定を持つプロジェクトで、除外が入っていないのに
`detect` が閉じていた)。

## 移らなかったときに何が起きるか

議論用のウィンドウを起こすたびに、約5分後に停止の誤報が Slack へ出る。
**誤報が続くと、本物の停止の知らせが信じられなくなる。**
