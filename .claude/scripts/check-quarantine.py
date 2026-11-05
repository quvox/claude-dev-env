#!/usr/bin/env python3
"""一時除外(quarantine)の宣言と、テストに付いた印の食い違いを見る。

    python3 .claude/scripts/check-quarantine.py            # 検査する
    python3 .claude/scripts/check-quarantine.py --selftest  # 壊した事例で落ちることを示す

**なぜ要るか** ★(2026-09-15。inspection-28 A-5)。

不安定なテストを実行対象から外す経路は、**期限を持つ台帳(`tests/quarantine.yml`)への
登録1本**である。ところがスイートの宣言は `exclude_tags: ["@flaky"]` でその印の付いた
テストを丸ごと外すので、**印を付けるだけで、期限を1日も持たないまま実行されなくなる。**
期限切れを見る仕組みは台帳の `due` しか読まないので、**印だけで外れたテストには、
期限の検査が永久に掛からない。**

だからここで見るのは1つである: **印が付いているのに台帳に無いテストが在るか。**

**見るのは形だけである。** そのテストが本当に不安定かどうかは見ない。
**印を消すべきか、台帳へ登録すべきかも決めない** — どちらにするかは人と、その run が決める。

**fail-closed ではない** ★ — テストの置き場が宣言されていない・読めないときは
「見ていない」と言って 0 を返す。**ここで止めると、テスト基盤を入れる前のプロジェクトが
一歩も進めなくなる。** 止める役はデプロイゲートが別に負っている。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CONFIG = ".claude/scripts/flow-config.json"
LOCAL = ".claude/scripts/flow-config.local.json"
QUARANTINE = "tests/quarantine.yml"
# 印は言語をまたいで同じ綴りである(`@flaky`)。コメント・デコレータ・タグ属性のどれでも拾う。
FLAKY = re.compile(r"@flaky\b")
TEST_EXT = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rb", ".java", ".rs", ".kt", ".swift"}


def cfg(root: Path) -> dict:
    out: dict = {}
    for name in (CONFIG, LOCAL):
        f = root / name
        if f.is_file():
            try:
                out.update(json.loads(f.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                pass
    return out


def test_roots(root: Path) -> list[str]:
    """テストコードの置き場。

    見るのは2つである:

    - **試験区分ごとの置き場の宣言(`scope_roots`)の値すべて** —
      **名前で当てない** ★(2026-09-15 の2巡目)。「パスに `test` が入っているもの」で
      絞っていたが、`e2e/` `spec/` `integration/` のような置き場を宣言した
      プロジェクトでは**1ファイルも走査せずに通ってしまう。**
    - **`tests/` が実在するなら、他の宣言の有無によらず足す** ★(同じく2巡目)—
      `scope_roots` の宣言はテスト基盤を入れてから書くものなので、
      **入れる前のプロジェクトでは空である。**そこで既定を落とすと、
      いちばん普通の置き方をしているプロジェクトを1つも見ないことになる。

    **製品コードの置き場(`code_roots`)は見ない** ★ — あそこを走査すると、
    製品のコメントや文字列に出てくる `@flaky`(タグの説明など)を印と読んで、
    **一時除外を1つも使っていないプロジェクトを止める。**
    """
    c = cfg(root)
    roots: list[str] = []
    for v in (c.get("scope_roots") or {}).values():
        if isinstance(v, list):
            roots += [x for x in v if isinstance(x, str)]
    if (root / "tests").is_dir():
        roots.append("tests")
    return sorted(set(roots))


def quarantined(root: Path) -> set[str]:
    """台帳に登録されているテストの名前。読めなければ空を返す(呼ぶ側が「見ていない」と言う)。"""
    f = root / QUARANTINE
    if not f.is_file():
        return set()
    names: set[str] = set()
    for raw in f.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r'\s*-?\s*test\s*:\s*(.*?)\s*$', raw)
        if not m:
            continue
        v = m.group(1)
        for q in ('"', "'"):
            if len(v) >= 2 and v.startswith(q) and v.endswith(q):
                v = v[1:-1]
        if v:
            names.add(v.strip())
    return names


def tagged(root: Path, roots: list[str]) -> list[tuple[str, int, str]]:
    """`@flaky` の印が付いた箇所。(パス, 行, その行) を返す。"""
    out: list[tuple[str, int, str]] = []
    for r in roots:
        base = root / r
        if not base.exists():
            continue
        files = [base] if base.is_file() else [p for p in base.rglob("*") if p.is_file()]
        for p in files:
            if p.suffix not in TEST_EXT:
                continue
            try:
                lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for i, line in enumerate(lines, 1):
                if FLAKY.search(line):
                    out.append((p.relative_to(root).as_posix(), i, line.strip()))
    return out


def check(root: Path) -> int:
    roots = test_roots(root)
    if not roots:
        print("## 一時除外の検査: テストコードの置き場が分からないので見ていない"
              "(flow-config の scope_roots か tests/ が要る)")
        return 0
    missing = [r for r in roots if not (root / r).exists()]
    marks = tagged(root, roots)
    seen = len(roots) - len(missing)
    if missing:
        print(f"## 一時除外の検査: 宣言された {len(roots)} か所のうち "
              f"{len(missing)} か所が実在しないので見ていない: {', '.join(missing[:5])}")
    if not marks:
        print(f"## 一時除外の検査: 見た {seen} か所 / `@flaky` の印 0 件")
        print("  OK  印だけで実行対象から外れているテストは無い")
        return 0
    listed = quarantined(root)
    # **名前の突き合わせは緩く採る** — 印の行からテストの名前を機械で取り出すことは
    # 言語ごとに違って当てにならない。そこで「その印が在るファイルが、台帳のどれかの
    # 項目のパスに現れるか」で見る。**取りこぼす側へ倒してある**(誤って鳴らすより、
    # 見つけたものだけを出す)。見つけたものは、その run が1件ずつ確かめる。
    files_in_ledger = {n.split("::")[0] for n in listed}
    orphan = [(p, i, s) for p, i, s in marks if p not in files_in_ledger]
    print(f"## 一時除外の検査: 見た {seen} か所 / `@flaky` の印 {len(marks)} 件 / "
          f"台帳の登録 {len(listed)} 件")
    if not orphan:
        print("  OK  印の付いたファイルはすべて台帳に載っている")
        return 0
    print(f"  NG  台帳に無いファイルに `@flaky` が付いている: {len(orphan)} 件")
    for p, i, s in orphan[:20]:
        print(f"      - {p}:{i}  {s[:80]}")
    if len(orphan) > 20:
        print(f"      (ほか {len(orphan) - 20} 件)")
    print("  → 実行に戻すか、期限を付けて tests/quarantine.yml へ登録するかのどちらかにする。")
    print("     印だけで外れたテストには、期限の検査が永久に掛からない"
          "(規範: .claude/skills/verify-tests/SKILL.md の試験区分を回す段)。")
    return 1


def selftest() -> int:
    import tempfile
    bad = []

    def case(name: str, files: dict, expect: int) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for rel, body in files.items():
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(body, encoding="utf-8")
            got = check(root)
            if got != expect:
                bad.append(f"{name}(期待 {expect} / 実際 {got})")

    case("印が無ければ通る", {"tests/a_test.py": "def test_x():\n    pass\n"}, 0)
    case("印が在って台帳に無ければ落ちる",
         {"tests/a_test.py": "# @flaky\ndef test_x():\n    pass\n"}, 1)
    case("印が在って台帳に在れば通る",
         {"tests/a_test.py": "# @flaky\ndef test_x():\n    pass\n",
          "tests/quarantine.yml": 'quarantined:\n  - test: "tests/a_test.py::test_x"\n    due: 2099-01-01\n'},
         0)
    case("引用符の無い登録も読む",
         {"tests/a_test.py": "# @flaky\ndef test_x():\n    pass\n",
          "tests/quarantine.yml": "quarantined:\n  - test: tests/a_test.py::test_x\n    due: 2099-01-01\n"},
         0)
    case("テストの置き場が無ければ見ない", {"src/a.py": "# @flaky\n"}, 0)
    # 名前で当てない(2026-09-15 の2巡目)— `test` を含まない置き場も走査する
    case("test を含まない置き場も見る",
         {".claude/scripts/flow-config.json": '{"scope_roots": {"e2e": ["e2e/"]}}',
          "e2e/a.spec.ts": "// @flaky\nit('x', () => {})\n"}, 1)
    # 2巡目: 宣言が在っても tests/ を落とさない / 製品コードは見ない
    case("宣言が在っても tests/ を見る",
         {".claude/scripts/flow-config.json": '{"code_roots": ["src/"]}',
          "tests/a_test.py": "# @flaky\ndef test_x():\n    pass\n"}, 1)
    case("製品コードの @flaky では止まらない",
         {".claude/scripts/flow-config.json": '{"code_roots": ["src/"]}',
          "src/a.py": "# タグの説明: @flaky を付けると不安定と分類される\n"}, 0)
    case("宣言した置き場が無くても落ちない",
         {".claude/scripts/flow-config.json": '{"scope_roots": {"e2e": ["nowhere/"]}}'}, 0)
    case("テスト以外の拡張子は見ない",
         {"tests/notes.md": "@flaky と書いてあるだけ\n"}, 0)
    if bad:
        print("NG 期待と違った事例: " + " / ".join(bad))
        return 1
    print("OK check-quarantine の自己検査(10 事例: 印と台帳の突き合わせ)")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--selftest", action="store_true",
                    help="壊した事例で落ちることを示す")
    args = ap.parse_args(argv[1:])
    return selftest() if args.selftest else check(Path(args.root))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
