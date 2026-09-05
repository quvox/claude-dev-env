#!/usr/bin/env python3
"""バックログ(未クローズの課題票と残務)の計器。**数えて出すだけで、何も拒まない**。

`/build` の入口で読む。掃除が「誰かがそうしようと決めたとき」にしか起きなかったのが
課題票が数百件になった原因だが、**着手を拒む役はこのスクリプトが持たない** —
拒む役は及第ライン(デプロイゲート `stamps.py check`)だけが持つ
(規範: CLAUDE.md 原則8 と `.claude/directions/issues-pendings.md` §1・§2.1)。
ゆえにここには上限という概念が無く、設定ファイルも要らない。

数えて出すもの:
  未クローズの課題票 = docs/issues/*.md のうち index.md 以外(課題票は解決時にファイルごと消える)
  残務            = docs/residual.md の「## 残務」節の行(日付先頭)

**残務の 50 は上限ではない**: 2026-08-25 の裁定で行数の上限は廃止され、50 は
`doc-health.py --rotate` がファイルをローテーションする引き金になった(1行も落ちない。
正は issues-pendings.md §2.1)。**数えるのは現行の `docs/residual.md` だけである** —
押し出された `docs/residual-NNN.md` はどのフローも読まない。

**台帳の欠落は「0件」と読まない**(fail-closed)。docs/ が在るのに issues/ か
residual.md が無いのは /setup 済みプロジェクトの破損であって、数えられたという結果ではない。

使い方:
    python3 .claude/scripts/check-backlog.py
    python3 .claude/scripts/check-backlog.py --selftest

終了コード: 0=読めた(数の大小では変わらない) 2=使い方・台帳の破損
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def find_root(start: Path) -> Path:
    cur = start.resolve()
    for candidate in (cur, *cur.parents):
        if (candidate / "CLAUDE.md").is_file() and (candidate / ".claude").is_dir():
            return candidate
    return cur


def open_issues(root: Path) -> list[str]:
    base = root / "docs" / "issues"
    if not base.is_dir():
        return []
    return sorted(p.name for p in base.glob("*.md")
                  if p.name != "index.md" and not p.name.startswith("._"))


def leftovers(root: Path) -> list[str]:
    path = root / "docs" / "residual.md"
    if not path.is_file():
        return []
    text = re.sub(r"<!--[\s\S]*?-->", "", path.read_text(encoding="utf-8"))
    out, inside = [], False
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^##\s+残務", stripped):
            inside = True
            continue
        if stripped.startswith("## "):
            inside = False
        if inside and re.match(r"^-\s+\d{4}-\d{2}-\d{2}\b", stripped):
            out.append(stripped)
    return out


def main(argv: list[str]) -> int:
    args = argv[1:]
    if "--selftest" in args:
        return selftest()
    if any(a in ("-h", "--help") for a in args):
        print(__doc__); return 0
    if args:
        print(__doc__); return 2

    root = find_root(Path.cwd())
    # **台帳の欠落を「0件」と読まない。** 数えられなかったのであって、少なかったのではない。
    if (root / "docs").is_dir():
        missing = [rel for rel in ("docs/issues", "docs/pendings.md", "docs/residual.md")
                   if not (root / rel).exists()]
        if missing:
            print("エラー: バックログの台帳が無い: " + ", ".join(missing)
                  + "(/setup が作るもの。欠落を『0件』と読むわけにはいかない。"
                    "旧い版から上げたなら、手順は "
                    ".claude/directions/issues-pendings.md §2.1 の「旧い版から上げたとき」)",
                  file=sys.stderr)
            return 2
        # **移行の取り残しも「0件」と読まない。** `cp` だけして行の移し替えを忘れると、
        # 旧 pendings.md に残った行はどの道具からも見えないまま「残務 0 行」で通る
        # (2026-08-25 の独立検査で実測)。手順は issues-pendings.md §2.1。
        old = root / "docs" / "pendings.md"
        if old.is_file():
            body = re.sub(r"<!--[\s\S]*?-->", "", old.read_text(encoding="utf-8"))
            if any(re.match(r"^##\s+残務", line.strip()) for line in body.splitlines()):
                print("エラー: docs/pendings.md に `## 残務` の節がまだ在る — 残務の移行が"
                      "途中である(その行は誰からも見えない)。手順は "
                      ".claude/directions/issues-pendings.md §2.1", file=sys.stderr)
                return 2
    issues, left = open_issues(root), leftovers(root)
    print(f"未クローズの課題票: {len(issues)} 件")
    print(f"残務: {len(left)} 行")
    print("→ この計器は着手を拒まない。**自動配車はこの数を読んで報告するだけで、"
          "次に何を回すかを決めない**(契機は人間の指示、範囲はデプロイゲート stamps.py check。"
          "正は directions/flows.md §4)。**人間はこの数を判断材料にしてよい**")
    return 0


def selftest() -> int:
    import contextlib, io, os, tempfile
    previous = Path.cwd()

    def run(*extra: str) -> tuple[int, str]:
        buf, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
            code = main(["x", *extra])
        return code, buf.getvalue() + err.getvalue()

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / ".claude/scripts").mkdir(parents=True)
        (root / "CLAUDE.md").write_text("x", encoding="utf-8")
        issues = root / "docs/issues"; issues.mkdir(parents=True)
        (root / "docs/residual.md").write_text("## 残務(文書整合ほか)\n\nなし\n", encoding="utf-8")
        (root / "docs/pendings.md").write_text("# 棚上げ事項\n\nなし\n", encoding="utf-8")
        os.chdir(root)
        assert run()[0] == 0, "空のバックログで 0 を返さなかった"
        # **どれだけ溜まっても拒まない**(旧 max_open_issues の撤廃がこれ)
        for n in range(31):
            (issues / f"{n:03d}-modify-x.md").write_text("type: modify\nseverity: 中\n",
                                                         encoding="utf-8")
        (issues / "index.md").write_text("# 一覧\n", encoding="utf-8")   # index は数えない
        code, out = run()
        assert code == 0, "課題票 31件で拒んだ"
        assert "未クローズの課題票: 31 件" in out, f"件数を出していない: {out}"
        assert "上限" not in out, f"出力に上限が残っている: {out}"
        # 残務も数えて出すだけ
        (root / "docs/residual.md").write_text(
            "## 残務(文書整合ほか)\n\n"
            "- 2026-01-01 docs/a.md:§1 a\n- 2026-01-02 docs/a.md:§2 b\n- 2026-01-03 docs/a.md:§3 c\n",
            encoding="utf-8")
        code, out = run()
        assert code == 0, "残務3行で拒んだ"
        assert "残務: 3 行" in out, f"残務を数えていない: {out}"
        # 撤廃した旗は使い方エラーになる(黙って無視して通さない)
        for gone in ("--sweep-task", "--override", "--for-issue"):
            assert run(gone)[0] == 2, f"撤廃した {gone} が受け付けられた"
        # 台帳そのものが欠けているのを「0件」と読まない(fail-closed。数の話ではない)
        import shutil
        shutil.move(str(root / "docs/residual.md"), str(root / "_p.md"))
        assert run()[0] == 2, "residual.md 欠落が空バックログとして通った"
        shutil.move(str(root / "_p.md"), str(root / "docs/residual.md"))
        # 棚上げの台帳も同じく fail-closed である(残務へ寄せたときに落ちていた)
        shutil.move(str(root / "docs/pendings.md"), str(root / "_q.md"))
        assert run()[0] == 2, "pendings.md 欠落が空バックログとして通った"
        shutil.move(str(root / "_q.md"), str(root / "docs/pendings.md"))
        # 移行の取り残し(旧 pendings.md に残務の節が在る)を「0件」と読まない
        keep = (root / "docs/pendings.md").read_text(encoding="utf-8")
        (root / "docs/pendings.md").write_text(
            keep + "\n## 残務(文書整合ほか)\n\n- 2026-01-01 docs/README.md:§1 移し忘れ\n",
            encoding="utf-8")
        code, out = run()
        assert code == 2, f"移行の取り残しが通った: {out}"
        (root / "docs/pendings.md").write_text(keep, encoding="utf-8")
        shutil.move(str(issues), str(root / "_i"))
        assert run()[0] == 2, "issues/ 欠落が空バックログとして通った"
        shutil.move(str(root / "_i"), str(issues))
        os.chdir(previous)                              # 一時ディレクトリを掴んだまま抜けない
    print("OK check-backlog: 何も拒まない/課題票と残務の件数表示/撤廃した旗/台帳欠落は fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
