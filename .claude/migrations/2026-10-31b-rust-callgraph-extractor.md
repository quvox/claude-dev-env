---
id: 2026-10-31b-rust-callgraph-extractor
since: 2026-10-31
kind: mechanical
detect: python3 -c 'import json,sys; d=json.load(open(".claude/scripts/callgraph-config.local.json")); sys.exit(3 if (d.get("languages",{}).get("rust",{}).get("enabled") is False) else 0)' 2>/dev/null; test $? -eq 3 && exit 1; find . \( -path ./.git -o -path ./.claude -o -name target -o -name vendor -o -name node_modules \) -prune -o -name '*.rs' -print 2>/dev/null | head -1 | grep -q . || exit 1; test -x .claude/.venv/bin/python || exit 0; .claude/.venv/bin/python -c 'import tree_sitter_rust' 2>/dev/null && exit 1; exit 0
paths: docs/03-impl/callgraphs
summary: コールグラフの生成が Rust を解析するようになった。Rust のファイルを持つプロジェクトは setup-tools.py を打ち直して解析用のライブラリを入れる。入れないと build-callgraphs.py が止まる
---

## 何が変わったか

**コールグラフの生成(`build-callgraphs.py`)が Rust のソース(`.rs`)を解析するようになった。**
それまで Rust には解析の部品が無く、Rust の関数はコールグラフに1つも現れなかった。機能表の
入口が Rust の関数を指していると、2026-10-31 の取り込み(`KIT-callgraph-ft1-unsupported-lang`)
以降は「未検査」として数だけが出ていた。

いまは、関数・`impl` のメソッド・トレイトの既定のメソッドを記号にし、`use` 宣言と
`Cargo.toml` のパッケージ名から呼び出し先を解き、`axum` / `actix-web` / `rocket` の経路
(接頭辞の `nest` / `scope` / `mount` を含む)と、バイナリの `fn main` を入口として出す。
部品は `.claude/scripts/cgx/rust_treesitter.py`、解析に使うライブラリは `tree-sitter-rust` である。

**このライブラリはキット専用の作業環境(`.claude/.venv`)に入る。** 作業環境は
`setup-tools.py` が `requirements.txt` から作るもので、**上書き展開では中身が増えない。**
Rust のファイルを持つプロジェクトで入れないまま `build-callgraphs.py` を打つと、
「rust の抽出器を起動できない」と直し方を1行出して終了コード2で止まる(Go / TypeScript と同じ扱い。
欠けた地図のまま検査を完走させない)。**Rust のファイルを1つも持たないプロジェクトでは止まらない**
(ライブラリを読み込む前に、対象が0件なら空の結果を返す)ので、この移行は要らない。

## 手順

1. 作業環境に依存を入れ直す:

   ```bash
   python3 .claude/scripts/setup-tools.py
   ```

   配布物の `requirements.lock` に `tree-sitter-rust` の版が入っているので、その版が入る。

2. コールグラフを作り直す:

   ```bash
   python3 .claude/scripts/build-callgraphs.py
   ```

   `docs/03-impl/callgraphs/rust.md` ができる。

3. 機能表(`docs/03-impl/features.md`)を持っているなら、検査を1度打つ:

   ```bash
   python3 .claude/scripts/callgraph-check.py
   ```

   **それまで「未検査」だった Rust の入口と、機能間連携仕様書の `impl` が、ここから照合される。**
   表記がコールグラフの記号と1文字でも違うと、入口は FT1(機能表の入口が実在しない。**以降の検査が
   止まる**)、`impl` は CG1(重大度「高」)になる。記号の表記は次のとおりで、正は `rust.md` の関数表である:

   | 書いてあった形 | 直す先 | 理由 |
   |---|---|---|
   | `src/auth.rs::JwksVerifier::verify` | `src/auth.rs::JwksVerifier.verify` | 記号の修飾は言語によらず `.` で繋ぐ(`callgraphs.md` §5.1)。`::` は「ファイル」と「修飾名」の区切りに1度だけ使う |
   | `src/code_mail.rs::SesCodeMailer`(構造体・列挙型・トレイトそのもの) | そのメソッドを1つずつ(`src/code_mail.rs::SesCodeMailer.send_code` …) | 型そのものは記号にならない。記号になるのは関数・`impl` のメソッド・トレイトの既定のメソッドだけである。入口なら、外から呼ばれるメソッドを選ぶ |
   | `src/x.rs::inner::f`(ファイルの中の `mod inner { … }`) | `src/x.rs::inner.f` | 同上 |

   **2026-10-31 の実測**: Rust を使う手元のプロジェクトの写しで打ったところ、機能表の入口7件が FT1、
   `impl` の約20件が CG1 になった。どれも上の表のどちらかの形だった。直すのは事実の差異の書き換え
   (`/verify-impl`)で足りる。

**Rust を解析させたくないときは**、`.claude/scripts/callgraph-config.local.json` に
`"languages": {"rust": {"enabled": false}}` と書く。そのときこの移行は「済んだ」になり、
Rust の入口は従来どおり「未検査」として数だけが出る。

## 移らなかったときに何が起きるか

`build-callgraphs.py` が止まり、コールグラフが作り直されない。実装整合の確認(`/verify-impl`)は
コールグラフの再生成から始まるので、そこで止まる。
