"""コールグラフ抽出器。

言語ごとに1モジュール。すべて `extract(root, cfg, scope) -> dict` を実装し、
callgraph-schema.json の `languages.<name>` に適合する結果を返す。

抽出手段(tree-sitter / ast / 正規表現)は差し替え可能で、
中間表現が契約である(.claude/scripts/callgraph-design.md §2)。
"""

from __future__ import annotations

# 実装済みの抽出器。build-callgraphs.py はこの表だけを見る。
# 追加するときはここに1行足す(design §1.3 拡張性)。
EXTRACTORS: dict[str, str] = {
    "python": "cgx.python_ast",
    "go": "cgx.go_treesitter",
    "infra": "cgx.infra",
    "typescript": "cgx.ts_treesitter",
    "rust": "cgx.rust_treesitter",
    "shell": "cgx.shell_regex",
    "make": "cgx.make_regex",
}

# シンボルを出さない抽出器(資源・経路・未解決だけを出す)。この言語が名乗る拡張子
# (`.tf` / `.yaml` …)は、機能表の入口や `x-impl` として callgraph に現れようがない
# (`base.unextracted_symbol`。KIT-callgraph-ft1-unsupported-lang)。
NO_SYMBOLS: frozenset[str] = frozenset({"infra"})

# 未実装だが設定で有効にされうる言語。有効なのに未実装なら明示的に報告する。
PLANNED: dict[str, str] = {}
