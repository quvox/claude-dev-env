#!/usr/bin/env python3
"""ミッションの予算の計器。**数えて出すだけで、何も拒まない**(中央エージェントが配車の前に読む)。

拒む役はデプロイゲート(`stamps.py check`)だけが持つ(規範: `.claude/directions/flows.md` §4・
`glossary.md` §8)。**ここに「止める」機構は無い** — 超過が出ているあいだ新しい仕事を始める
作業指示を配らないのは**規範の禁止**であって、この計器の権能ではない
(`.claude/directions/orchestration.md` §3.0 の6・`/mission` §7)。

**なぜ在るか**: 2026-08-26 に、頼まれた仕事が終わった後も18時間21分、同じ1つの要件が形を変えて
3周し、検査が12回回った。ミッションには時間の上限も本数の上限も無く、止まるかどうかは中央
エージェントの判断に残っていた。**判断に残してはならない** — だから数える側を機械にする。

数えて出すもの(**3つで全部である**):

  ① **経過時間** — 台帳 frontmatter の `開始:` から現在まで。上限は `予算:`(既定は
     ミッション開始時に人間が指定でき、指定が無ければ `6時間`)。**欄そのものが無い台帳
     (この欄の導入より古いもの)は `不明` と読み、発火しない** — 途中から数え始めると、
     起点の解釈だけで誤って止まる。
  ② **出した作業指示の本数** — `.claude/missions/<mid>/orders/*.md` の数。上限は、台帳の
     `## 計画(フェーズ)` の `出す予定の作業指示` 欄の合計の **2倍**。**見込みが書かれて
     いなければ発火しない**(基準が無いものを超過とは言わない)。
  ③ **同じ要件への修繕の本数** — 作業指示の `破れた要件:` 欄(`orchestration.md` §4)の値ごとに
     数え、**3本目で発火**する。ID の無い問題(コードだけの不具合)は数えられない —
     それは承知の上の穴である(課題票の番号で数えると、同じ要件が形を変えるたびに番号が
     変わって発火しない。実測 2026-08-26: 票の番号は 025・026・030 と毎回変わっていた)。

**人間の再開**: 台帳の `## 人間への問い` の節に、人間が次の1行を書く。

    - 再開許可: <YYYY-MM-DD HH:MM> — <人間の一言(省いてよい)>

**この行が n 本在るとき**、①の起点は**最後の再開許可の時刻**へ移り、②と③の上限は
**(n+1) 倍**になる。**同じ台帳に判定と許可が集まるので、中央エージェントの記憶が初期化されても
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
DEFAULT_BUDGET_HOURS = 6.0
REPAIR_LIMIT = 3                  # ③ の上限(同じ要件への修繕は3本目で発火)

_TIME = r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})"
RESUME_RE = re.compile(r"(?m)^\s*[-*]\s*再開許可:\s*" + _TIME)
BROKEN_RE = re.compile(r"(?m)^\s*[-*]\s*破れた要件:\s*(.+?)\s*$")
PLAN_COL = "出す予定の作業指示"


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


def section(text: str, heading: str) -> str:
    """`## <heading>` から次の `## ` までを返す(無ければ空文字)。"""
    lines = text.splitlines()
    out: list[str] = []
    inside = False
    for line in lines:
        if line.startswith("## "):
            if inside:
                break
            inside = line[3:].strip().startswith(heading)
            continue
        if inside:
            out.append(line)
    return "\n".join(out)


def planned_orders(text: str) -> int | None:
    """`## 計画(フェーズ)` の表の `出す予定の作業指示` 欄の合計。欄が無ければ None。"""
    body = section(text, "計画")
    header: list[str] | None = None
    total: int | None = None
    for line in body.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = cells
            continue
        if all(set(c) <= set("-: ") for c in cells):   # 区切り行
            continue
        if PLAN_COL not in header:
            return None
        idx = header.index(PLAN_COL)
        if idx >= len(cells):
            continue
        m = re.search(r"\d+", cells[idx])
        if m:
            total = (total or 0) + int(m.group(0))
    return total


def orders(mission_dir: Path) -> list[Path]:
    d = mission_dir / "orders"
    if not d.is_dir():
        return []
    return sorted(p for p in d.glob("*.md") if p.is_file())


def repairs_by_requirement(order_files: list[Path]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for p in order_files:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in BROKEN_RE.finditer(text):
            rid = m.group(1).strip().strip("`")
            # **埋め忘れの雛形を要件として数えない。** 逐語の一致では守れない(雛形の文面は
            # 変わる)ので、**山括弧で囲まれた値**をまとめて弾く(`orchestration.md` §4 の
            # 様式は `<…>` で穴を示す)。「なし」は ID を持たない問題の正しい書き方である。
            if not rid or rid in ("なし", "-") or (rid.startswith("<") and rid.endswith(">")):
                continue
            counts[rid] = counts.get(rid, 0) + 1
    return counts


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
    mdir = ledger.parent
    lines = [f"  台帳: {ledger.relative_to(root)}(状態: {fm.get('状態', '不明')})"]
    fired = 0

    resumes = [parse_time(f"{d} {t}") for d, t in RESUME_RE.findall(text)]
    resumes = sorted(x for x in resumes if x is not None)
    if resumes:
        lines.append(f"  再開許可: {len(resumes)}件(最後は {resumes[-1]:%Y-%m-%d %H:%M})")
    factor = len(resumes) + 1

    # ① 経過時間
    started = parse_time(fm.get("開始", ""))
    budget = parse_budget(fm.get("予算", ""))
    origin = resumes[-1] if resumes else started
    if origin is None or budget is None:
        why = "開始 が読めない" if origin is None else "予算 が無い(この欄の導入より古い台帳)"
        lines.append(f"  ① 経過時間: 不明 — {why}。発火しない")
    else:
        elapsed = int((now - origin).total_seconds() // 60)
        elapsed = max(elapsed, 0)
        limit = int(budget * 60)
        mark = ""
        if elapsed > limit:
            fired += 1
            mark = "  → 発火"
        base = "最後の再開許可" if resumes else "開始"
        lines.append(f"  ① 経過時間: {fmt_span(elapsed)}({base}から) / 予算 "
                     f"{fmt_span(limit)}{mark}")

    # ② 出した作業指示の本数
    issued = len(orders(mdir))
    planned = planned_orders(text)
    if planned is None or planned <= 0:
        lines.append(f"  ② 出した作業指示: {issued}本 / 上限なし — "
                     f"台帳の 計画(フェーズ)に「{PLAN_COL}」の見込みが無い。発火しない")
    else:
        limit = planned * 2 * factor
        mark = ""
        if issued > limit:
            fired += 1
            mark = "  → 発火"
        lines.append(f"  ② 出した作業指示: {issued}本 / 上限 {limit}本"
                     f"(見込み {planned}本の2倍{'' if factor == 1 else f' × {factor}'})"
                     f"{mark}")

    # ③ 同じ要件への修繕の本数
    counts = repairs_by_requirement(orders(mdir))
    limit = REPAIR_LIMIT * factor
    over = sorted((k for k, v in counts.items() if v >= limit), key=str)
    if not counts:
        lines.append(f"  ③ 同じ要件への修繕: 0本 / {limit}本目で発火"
                     "(作業指示に「破れた要件:」が1件も無い)")
    else:
        top = ", ".join(f"{k}={v}本" for k, v in sorted(counts.items()))
        mark = ""
        if over:
            fired += 1
            mark = f"  → 発火({', '.join(over)})"
        lines.append(f"  ③ 同じ要件への修繕: {top} / {limit}本目で発火{mark}")

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

            # ① 予算超過で発火。終了コードは 0 のまま
            write(root, "2026-08-27-x",
                  f"mission: 2026-08-27-x\n状態: 進行中\n開始: {old}\n予算: 6時間")
            code, out = run("check")
            ck("(c) 予算超過で発火する", "① 経過時間" in out and "→ 発火" in out, out)
            ck("(c) 発火しても終了コードは 0", code == 0, str(code))
            ck("(c) 発火の件数を出す", "発火 1件" in out, out)

            # 予算の欄が無い古い台帳は発火しない
            write(root, "2026-08-27-x", f"mission: 2026-08-27-x\n状態: 進行中\n開始: {old}")
            code, out = run("check")
            ck("(d) 予算の欄が無い台帳は発火しない",
               "① 経過時間: 不明" in out and "発火なし" in out, out)

            # 進行中でない台帳は数えない
            write(root, "2026-08-27-x",
                  f"mission: 2026-08-27-x\n状態: 完了\n開始: {old}\n予算: 6時間")
            code, out = run("check")
            ck("(e) 完了の台帳は数えない", "進行中の台帳なし" in out, out)
            # 名指しすれば読む
            code, out = run("check", "2026-08-27-x")
            ck("(e) 名指しなら状態によらず読む", "① 経過時間" in out, out)
            ck("(e) 無い mid は 2", run("check", "no-such")[0] == 2)

            # 再開許可で数え直す
            write(root, "2026-08-27-x",
                  f"mission: 2026-08-27-x\n状態: 進行中\n開始: {old}\n予算: 6時間",
                  f"## 人間への問い\n- 再開許可: {fresh} — 続けてよい\n")
            code, out = run("check")
            ck("(f) 再開許可で ① が数え直される",
               "再開許可: 1件" in out and "→ 発火" not in out, out)

            # ② 見込みが無ければ発火しない / 在れば2倍で発火する
            d = root / MISSIONS / "2026-08-27-x" / "orders"
            for n in range(9):
                (d / f"{n}.md").write_text("- 実行すること: /build x\n", encoding="utf-8")
            write(root, "2026-08-27-x",
                  f"mission: 2026-08-27-x\n状態: 進行中\n開始: {fresh}\n予算: 6時間")
            code, out = run("check")
            ck("(g) 見込みが無ければ ② は発火しない",
               "② 出した作業指示: 9本 / 上限なし" in out and "発火なし" in out, out)
            write(root, "2026-08-27-x",
                  f"mission: 2026-08-27-x\n状態: 進行中\n開始: {fresh}\n予算: 6時間",
                  "## 計画(フェーズ)\n"
                  "| # | フェーズ | 完了条件 | 状態 | 出す予定の作業指示 | 人間に示した日 |\n"
                  "|---|---|---|---|---|---|\n"
                  "| 1 | 下ごしらえ | x | 完了 | 2 | 2026-08-27 |\n"
                  "| 2 | 本体 | x | 進行中 | 2 | 2026-08-27 |\n")
            code, out = run("check")
            ck("(h) 見込みの2倍を超えると ② が発火する",
               "上限 8本" in out and "→ 発火" in out, out)

            # ③ 同じ要件への修繕は3本目で発火する
            for n in range(9):
                (d / f"{n}.md").unlink()
            for n in range(2):
                (d / f"r{n}.md").write_text(
                    "- 実行すること: /build --repair x\n- 破れた要件: FR-auth-03-1\n",
                    encoding="utf-8")
            write(root, "2026-08-27-x",
                  f"mission: 2026-08-27-x\n状態: 進行中\n開始: {fresh}\n予算: 6時間")
            code, out = run("check")
            ck("(i) 2本目では ③ は発火しない",
               "FR-auth-03-1=2本" in out and "→ 発火" not in out, out)
            ck("(i) 印字は「3本目で発火」の形である", "3本目で発火" in out, out)
            (d / "r2.md").write_text(
                "- 実行すること: /build --repair x\n- 破れた要件: FR-auth-03-1\n",
                encoding="utf-8")
            code, out = run("check")
            ck("(j) 3本目で ③ が発火する",
               "③ 同じ要件への修繕" in out and "→ 発火(FR-auth-03-1)" in out, out)
            # 雛形のままの値は数えない
            (d / "r3.md").write_text("- 破れた要件: なし\n", encoding="utf-8")
            code, out = run("check")
            ck("(k) 「なし」は要件として数えない", "なし=" not in out, out)
            # 埋め忘れの雛形(山括弧の値)も数えない — 雛形の文面が変わっても効く形にしてある
            (d / "r4.md").write_text(
                "- 破れた要件: <要件の ID(`FR-<domain>-nn-#` など)。修繕の作業指示だけに書く>\n",
                encoding="utf-8")
            code, out = run("check")
            ck("(l2) 埋め忘れの雛形は要件として数えない", "要件の ID" not in out, out)
    finally:
        os.chdir(previous)

    print("OK check-mission.py --selftest")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
