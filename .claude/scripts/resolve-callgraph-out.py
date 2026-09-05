#!/usr/bin/env python3
"""callgraphs の生成先を返す。**スキルはこの判断を自前でやらない。**

規範は .claude/directions/callgraphs.md §3.1: フロー分離後、生成先は常に SSOT
(docs/03-impl/callgraphs/)である。廃止されたフェーズモデルの staged 出力(タスク配下)は
変更指示の全廃(ワークフロー再設計 2026-08-19)とともに retired — /build 中の過渡は
構築記録の state が可視化し、再生成は /verify-impl と /relations が行う(principles.md §1)。

このスクリプトが残る理由: 呼び出し側(スキル・CI・許可リスト)の形を安定させるため。
生成先の決め方がまた変わっても、変わるのはここ1箇所である。

使い方:
    python3 .claude/scripts/resolve-callgraph-out.py [--ssot] [--explain]

標準出力にはリポジトリ相対のディレクトリを**1行だけ**出す(コマンド置換で使うため)。
`--ssot` は明示のための別名(結果は同じ)。理由は `--explain` で標準エラーに出す。

    CG_SSOT=$(python3 .claude/scripts/resolve-callgraph-out.py --ssot)
    python3 .claude/scripts/build-callgraphs.py --out "$CG_SSOT"

終了コード: 0=決まった 2=使い方エラー
"""

from __future__ import annotations

import sys

SSOT_DIR = "docs/03-impl/callgraphs"


def main(argv: list[str]) -> int:
    if any(a in ("-h", "--help") for a in argv[1:]):
        print(__doc__)   # 明示要求は 0。使い方エラーの 2 と区別する(tools-readme §2)
        return 0
    flags = set(argv[1:])
    if flags - {"--ssot", "--explain"}:
        print(__doc__)
        return 2
    if "--explain" in flags:
        print("生成先は常に SSOT である(callgraphs.md §3.1)。", file=sys.stderr)
    print(SSOT_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
