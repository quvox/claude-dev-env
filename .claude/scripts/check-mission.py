#!/usr/bin/env python3
"""ミッションの予算の計器。**数えて出すだけで、何も拒まない**(中央エージェントが配車の前に読む)。

拒む役はデプロイゲート(`stamps.py check`)だけが持つ(規範: `.claude/directions/flows.md` §4・
`glossary.md` §8)。**ここに「止める」機構は無い** — 超過が出ているあいだ新しい仕事を始める
作業指示を配らないのは**規範の禁止**であって、この計器の権能ではない
(`.claude/directions/orchestration.md` §3.0 の6・`/mission` §7)。

**なぜ在るか**: 2026-08-26 に、頼まれた仕事が終わった後も18時間21分、同じ1つの要件が形を変えて
3周し、検査が12回回った。ミッションには時間の上限も本数の上限も無く、止まるかどうかは中央
エージェントの判断に残っていた。**判断に残してはならない** — だから数える側を機械にする。

数えて出すものは、**経過時間の1つだけである**:

  **経過時間** — 台帳 frontmatter の `開始:` から現在まで。上限は `予算:`(既定は
  ミッション開始時に人間が指定でき、指定が無ければ `12時間`)。**欄そのものが無い台帳
  (この欄の導入より古いもの)は `不明` と読み、発火しない** — 途中から数え始めると、
  起点の解釈だけで誤って止まる。

**作業指示の本数は数えない** ★(2026-09-20): 以前はここで本数を2つ数えていた — 出した作業指示
の本数(計画の見込みの2倍で発火)と、同じ要件への修繕の本数(3本目で発火)。**どちらも廃した。
作業指示は何本出してもよい。** ミッションに許す上限は**経過時間だけ**である。

**人間の再開**: 台帳の `## 人間への問い` の節に、人間が次の1行を書く。

    - 再開許可: <YYYY-MM-DD HH:MM> — <人間の一言(省いてよい)>

**この行が在るとき**、経過時間の起点は**最後の再開許可の時刻**へ移る。
**同じ台帳に判定と許可が集まるので、中央エージェントの記憶が初期化されても
許可は消えない**(会話で答えると、`/clear` の後に同じところでもう一度止まる)。

使い方:
    python3 .claude/scripts/check-mission.py check            # 進行中の台帳を読む
    python3 .claude/scripts/check-mission.py check <mid>      # 台帳を名指しする
    python3 .claude/scripts/check-mission.py --selftest

終了コード: **0=読めた(発火の有無では変わらない)** 2=使い方・解析エラー。
**発火は出力で伝える。終了コードで伝えない** — 終了コードで伝えると、それを見た側が
拒む門として扱いはじめる。
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

MISSIONS = Path(".claude/missions")
DEFAULT_BUDGET_HOURS = 12.0

_TIME = r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})"
RESUME_RE = re.compile(r"(?m)^\s*[-*]\s*再開許可:\s*" + _TIME)


def find_root(start: Path) -> Path:
    cur = start.resolve()
    for cand in (cur, *cur.parents):
        if (cand / "CLAUDE.md").is_file() and (cand / ".claude").is_dir():
            return cand
    return cur


def frontmatter(text: str) -> dict[str, str]:
    """`---` で挟まれた先頭ブロックを `鍵: 値` で読む。コメント行(`#`)は落とす。"""
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    out: dict[str, str] = {}
    for line in parts[1].splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            out.setdefault(k.strip(), v.strip())
    return out


def parse_time(value: str) -> datetime | None:
    m = re.search(_TIME, value or "")
    if not m:
        return None
    try:
        return datetime.strptime(f"{m.group(1)} {m.group(2)}", "%Y-%m-%d %H:%M")
    except ValueError:
        return None


def parse_budget(value: str) -> float | None:
    """`予算:` を時間で読む。`6時間` / `6` / `6.5時間` を受ける。読めなければ None。

    **`None` は「不明」であって「0」ではない** — 読めない値で発火させると、書き間違いが
    そのまま停止になる(fail-open で正しい: 拒むのはデプロイゲートだけである)。
    """
    if value is None:
        return None
    v = value.strip()
    if not v or v in ("不明", "なし", "-"):
        return None
    m = re.match(r"^(\d+(?:\.\d+)?)\s*(時間)?$", v)
    if not m:
        return None
    return float(m.group(1))


def ledgers(root: Path) -> list[Path]:
    base = root / MISSIONS
    if not base.is_dir():
        return []
    return sorted(p for p in base.glob("*/ledger.md") if p.is_file())


def fmt_span(minutes: int) -> str:
    return f"{minutes // 60}時間{minutes % 60}分"


def report(root: Path, ledger: Path, now: datetime) -> tuple[list[str], int]:
    """1つの台帳について、印字する行と発火の件数を返す。"""
    text = ledger.read_text(encoding="utf-8", errors="replace")
    fm = frontmatter(text)
    lines = [f"  台帳: {ledger.relative_to(root)}(状態: {fm.get('状態', '不明')})"]
    fired = 0

    resumes = [parse_time(f"{d} {t}") for d, t in RESUME_RE.findall(text)]
    resumes = sorted(x for x in resumes if x is not None)
    if resumes:
        lines.append(f"  再開許可: {len(resumes)}件(最後は {resumes[-1]:%Y-%m-%d %H:%M})")

    # 経過時間(数えるのはこれだけである)
    started = parse_time(fm.get("開始", ""))
    budget = parse_budget(fm.get("予算", ""))
    origin = resumes[-1] if resumes else started
    if origin is None or budget is None:
        why = "開始 が読めない" if origin is None else "予算 が無い(この欄の導入より古い台帳)"
        lines.append(f"  経過時間: 不明 — {why}。発火しない")
    else:
        elapsed = int((now - origin).total_seconds() // 60)
        elapsed = max(elapsed, 0)
        limit = int(budget * 60)
        mark = ""
        if elapsed > limit:
            fired += 1
            mark = "  → 発火"
        base = "最後の再開許可" if resumes else "開始"
        lines.append(f"  経過時間: {fmt_span(elapsed)}({base}から) / 予算 "
                     f"{fmt_span(limit)}{mark}")

    return lines, fired


def main(argv: list[str]) -> int:
    args = argv[1:]
    if "--selftest" in args:
        return selftest()
    if any(a in ("-h", "--help") for a in args):
        print(__doc__)
        return 0
    if not args or args[0] != "check" or len(args) > 2:
        print(__doc__)
        return 2
    want = args[1] if len(args) == 2 else None

    root = find_root(Path.cwd())
    now = datetime.now()
    found = ledgers(root)
    if want:
        found = [p for p in found if p.parent.name == want]
        if not found:
            print(f"NG 台帳が見つからない: {MISSIONS}/{want}/ledger.md")
            return 2
    else:
        running = [p for p in found
                   if frontmatter(p.read_text(encoding="utf-8", errors="replace"))
                   .get("状態", "") == "進行中"]
        found = running

    print("## ミッションの予算(計器。何も拒まない)")
    if not found:
        print("  進行中の台帳なし(数えるものが無い)")
        return 0

    total = 0
    for ledger in found:
        lines, fired = report(root, ledger, now)
        for line in lines:
            print(line)
        total += fired

    if total:
        print(f"  発火 {total}件 — 超過が出ているあいだ、**新しい仕事を始める作業指示を"
              "配らない**(規範: orchestration.md §3.0 の6)。"
              "再配車・codex の出し直し・走っている検証の周を閉じる覆い直しは出してよい。"
              "人間の1行(台帳の「人間への問い」の `- 再開許可:`)で数え直す")
    else:
        print("  発火なし")
    return 0


def selftest() -> int:
    import contextlib
    import io
    import os
    import tempfile
    from datetime import timedelta

    previous = Path.cwd()

    def run(*extra: str) -> tuple[int, str]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(["x", *extra])
        return code, buf.getvalue()

    def write(root: Path, mid: str, fm: str, body: str = "") -> Path:
        d = root / MISSIONS / mid
        (d / "orders").mkdir(parents=True, exist_ok=True)
        p = d / "ledger.md"
        p.write_text(f"---\n{fm}\n---\n{body}", encoding="utf-8")
        return p

    try:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".claude/scripts").mkdir(parents=True)
            (root / "CLAUDE.md").write_text("x", encoding="utf-8")
            os.chdir(root)
            now = datetime.now()
            old = (now - timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")
            fresh = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")

            def ck(label: str, cond: bool, got: str = "") -> None:
                if not cond:
                    raise AssertionError(f"{label}: {got}")

            code, out = run("check")
            ck("(a) 台帳が無くても 0 を返す", code == 0 and "進行中の台帳なし" in out, out)

            # 使い方エラーは 2
            ck("(b) 引数なしは 2", run()[0] == 2)
            ck("(b) 知らない引数は 2", run("bogus")[0] == 2)

            # 予算超過で発火。終了コードは 0 のまま
            write(root, "2026-08-27-x",
                  f"mission: 2026-08-27-x\n状態: 進行中\n開始: {old}\n予算: 6時間")
            code, out = run("check")
            ck("(c) 予算超過で発火する", "経過時間" in out and "→ 発火" in out, out)
            ck("(c) 発火しても終了コードは 0", code == 0, str(code))
            ck("(c) 発火の件数を出す", "発火 1件" in out, out)

            # 予算の欄が無い古い台帳は発火しない
            write(root, "2026-08-27-x", f"mission: 2026-08-27-x\n状態: 進行中\n開始: {old}")
            code, out = run("check")
            ck("(d) 予算の欄が無い台帳は発火しない",
               "経過時間: 不明" in out and "発火なし" in out, out)

            # 進行中でない台帳は数えない
            write(root, "2026-08-27-x",
                  f"mission: 2026-08-27-x\n状態: 完了\n開始: {old}\n予算: 6時間")
            code, out = run("check")
            ck("(e) 完了の台帳は数えない", "進行中の台帳なし" in out, out)
            # 名指しすれば読む
            code, out = run("check", "2026-08-27-x")
            ck("(e) 名指しなら状態によらず読む", "経過時間" in out, out)
            ck("(e) 無い mid は 2", run("check", "no-such")[0] == 2)

            # 再開許可で数え直す
            write(root, "2026-08-27-x",
                  f"mission: 2026-08-27-x\n状態: 進行中\n開始: {old}\n予算: 6時間",
                  f"## 人間への問い\n- 再開許可: {fresh} — 続けてよい\n")
            code, out = run("check")
            ck("(f) 再開許可で経過時間が数え直される",
               "再開許可: 1件" in out and "→ 発火" not in out, out)

            # **本数では発火しない** ★(2026-09-20 に作業指示の本数の上限を廃した)
            d = root / MISSIONS / "2026-08-27-x" / "orders"
            for i in range(30):
                (d / f"{i}.md").write_text(
                    "- 実行すること: /build --repair x\n- 破れた要件: FR-auth-03-1\n",
                    encoding="utf-8")
            write(root, "2026-08-27-x",
                  f"mission: 2026-08-27-x\n状態: 進行中\n開始: {fresh}\n予算: 6時間",
                  "## 計画(フェーズ)\n"
                  "| # | フェーズ | 完了条件 | 状態 | 出す予定の作業指示 | 人間に示した日 |\n"
                  "|---|---|---|---|---|---|\n"
                  "| 1 | 下ごしらえ | x | 完了 | 2 | 2026-08-27 |\n")
            code, out = run("check")
            ck("(g) 作業指示を何本出しても発火しない(見込みの2倍を超えていても)",
               "発火なし" in out, out)
            ck("(g) 同じ要件への修繕を何本出しても発火しない", "FR-auth-03-1" not in out, out)
            ck("(g) 本数はもう印字しない", "本 /" not in out and "上限なし" not in out, out)
    finally:
        os.chdir(previous)

    print("OK check-mission.py --selftest")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
