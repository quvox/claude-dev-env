#!/usr/bin/env python3
"""shell 抽出器の入口の種別(`cgx/shell_regex.py`)の fixture。

**置く理由は `make check` がこれを実行することである。** 規範は
`.claude/directions/callgraphs.md` の CG6 の行と `scripts/callgraph-design.md` の shell の行が
持ち、**「何を主張しない値か」は合成コードでしか固定できない。**

いま固定しているのは 2026-08-25 の変更である: **分岐を持たないスクリプトは `protocol: main`**
(種別を主張しない)。**`case "$1"` の分岐は `cli` のまま**(引数を捌いている証拠が在る)。
vpnsys-op の実測では、`docker/*/entrypoint.sh` が `kind: event` の機能の実体なのに
`cli`(対話的な道具)と主張していた。
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cgx import shell_regex as sh                                 # noqa: E402

DISPATCH = """#!/bin/sh
case "${1:-help}" in
  up)
    do_up
    ;;
  down)
    do_down
    ;;
esac
"""

PLAIN = """#!/bin/sh
set -e
exec /usr/local/bin/serve --config /etc/app.conf
"""


def endpoints(files: dict[str, str]) -> list[tuple[str, str]]:
    cfg = json.loads((Path(__file__).resolve().parent / "callgraph-config.json").read_text())
    with tempfile.TemporaryDirectory() as td:
        # macOS は /var/folders/... がシンボリックリンクで、.resolve() すると
        # /private/var/folders/... に変わる。extract() 内の collect_files は
        # base_dir.resolve() した結果を root に対して relative_to するので、
        # root 自身を先に resolve しておかないと ValueError で全ファイルが落ちる。
        root = Path(td).resolve()
        for rel, body in files.items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(body, encoding="utf-8")
        out = sh.extract(root, cfg, None)
    return sorted((e["protocol"], e["id"]) for e in out.get("endpoints", []))


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    def ck(name: str, cond: bool, note: str = "") -> None:
        checks.append((name, cond, note))

    got = endpoints({"ops.sh": DISPATCH})
    ck("(a) case の分岐は cli(引数を捌いている証拠が在る)",
       got and all(p == "cli" for p, _ in got) and len(got) == 2, str(got))

    got = endpoints({"docker/hub/entrypoint.sh": PLAIN})
    ck("(b) 分岐の無いスクリプトは main(種別を主張しない)",
       got == [("main", "dispatch entrypoint.sh @ docker/hub/entrypoint.sh::main")], str(got))

    got = endpoints({"ops.sh": DISPATCH, "docker/hub/entrypoint.sh": PLAIN})
    ck("(c) 混在しても、それぞれの値になる",
       sorted({p for p, _ in got}) == ["cli", "main"], str(got))

    for name, ok, _ in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    ng = [(n, note) for n, ok, note in checks if not ok]
    if ng:
        print(f"\n{len(ng)} 件 FAIL", file=sys.stderr)
        for n, note in ng:
            print(f"--- {n}\n{note}", file=sys.stderr)
        return 1
    print(f"OK shell 抽出器の入口の種別 {len(checks)} 項目")
    return 0


if __name__ == "__main__":
    sys.exit(main())
