#!/usr/bin/env python3
"""キットの据え付け層(`kit-migrate.py`)の自己検査を走らせる fixture。

**置く理由は `make check` がこれを実行することである。** 自己検査は書いただけでは腐る —
スクリプトを直して自己検査が追随していなければ、ここで止まる
(`test-state-scripts.py` と同じ役目で、あちらは状態層を持つ)。

`kit-manifest.py` と `kit-patch.py` は `--selftest` を持たない。持ったらここへ足す。
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEDGER = HERE.parent / "migrations"


def verdicts(root: Path) -> dict[str, str]:
    """実際の台帳を root に対して走らせ、id → 要る/不要 を返す。"""
    r = subprocess.run([sys.executable, str(HERE / "kit-migrate.py"), "list",
                        "--root", str(root)], capture_output=True, text=True)
    assert r.returncode == 0, f"list が {r.returncode} を返した\n{r.stdout}{r.stderr}"
    out: dict[str, str] = {}
    for ln in r.stdout.splitlines():
        ln = ln.strip()
        if ln.startswith("[要る] ") or ln.startswith("[不要] "):
            out[ln[5:].split()[0]] = ln[1:3]
    return out


def real_ledger() -> int:
    """**配っている台帳そのもの**の判定を、3つの形の偽プロジェクトで固定する。

    自己検査(`kit-migrate.py --selftest`)が見るのは道具の振る舞いであって、
    台帳に書いてある `detect` の中身ではない。**そこを誰も見ていないと、
    条件を1文字直したときに黙って判定が反転する**(2026-08-25 の独立検査 K-3)。
    """
    cases = {
        "旧い形": {"docs/pendings.md": "## 残務(文書整合ほか)\n\n- 2026-08-01 a:b c\n"},
        "新しい形": {"docs/residual.md": "## 残務(文書整合ほか)\n\nなし\n",
                     "docs/pendings.md": "## P-001 なにか\n"},
        "docs が無い": {},
    }
    want = {"旧い形": "要る", "新しい形": "不要", "docs が無い": "不要"}
    for name, files in cases.items():
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shutil.copytree(LEDGER, root / ".claude" / "migrations")
            for rel, body in files.items():
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text(body, encoding="utf-8")
            got = verdicts(root).get("2026-08-25-residual-split")
            if got != want[name]:
                print(f"NG 台帳 residual-split: {name} は {want[name]} のはずが {got}",
                      file=sys.stderr)
                return 1
    # colabtmux.conf を持たないプロジェクトでは、あの移行は要らない(上の3つがそれである)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        shutil.copytree(LEDGER, root / ".claude" / "migrations")
        (root / "colabtmux.conf").write_text('exclude_windows = ["orchestrator"]\n',
                                             encoding="utf-8")
        if verdicts(root).get("2026-08-22-colabtmux-conf-discuss-1") != "要る":
            print("NG 台帳 discuss-1: 除外に無いのに「不要」と出た", file=sys.stderr)
            return 1
    print("OK 配っている台帳の判定(3つの形)")
    return 0


def main() -> int:
    for name in ("kit-migrate.py",):
        r = subprocess.run([sys.executable, str(HERE / name), "--selftest"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(f"NG {name} --selftest\n{r.stdout}\n{r.stderr}", file=sys.stderr)
            return 1
    print("OK キットの据え付け層の自己検査")
    return real_ledger()


if __name__ == "__main__":
    sys.exit(main())
