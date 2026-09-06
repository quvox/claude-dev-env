#!/usr/bin/env python3
"""事実の生成器(`build-facts.py`)の自己検査を走らせる fixture。

**置く理由は `make check` がこれを実行することである。** 自己検査は書いただけでは腐る —
生成器を直して自己検査が追随していなければ、ここで止まる(`test-state-scripts.py` と
同じ役目で、あちらは状態層を持つ)。
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    r = subprocess.run([sys.executable, str(HERE / "build-facts.py"), "--selftest"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"NG build-facts.py --selftest\n{r.stdout}\n{r.stderr}", file=sys.stderr)
        return 1
    print("OK 事実の生成器: 機械の欄(埋める/差分ゼロ/冪等)と参照の実在、要旨の長さは数えるだけ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
