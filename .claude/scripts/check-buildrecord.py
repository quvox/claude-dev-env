#!/usr/bin/env python3
"""構築記録(`docs/build-records/<slug>.md`)の機械検査。**F1 の構築記録ゲート。**

構築記録は「検証を後回しにする者が払う頭金」である(規範: .claude/directions/build-record.md)。
verify 系フローはこの記録を**突き合わせ可能な主張**として読むので、形が崩れた記録は
検証の網に穴を開ける。検査は fail-closed — 「検査したが違反が無い」と「何も検査していない」を
同じ出力にしない。

検査(IDの正はこのファイルの CHECKS だけ。--list で出る):
  BRC1  frontmatter: slug がファイル名と一致 / state が building・awaiting-verify・verified の
        いずれか / started・updated が ISO 日時 / origin が明記され derived か human-report
        (欠落を derived に既定しない — human-report だけに許される問いの経路が黙って消える)/
        **building 以外の state は commit に実在する git commit を持つ**(promote と
        F4 の犯人探しが commit に紐づくため。git が引けない環境では形式だけ見る)
  BRC2  critical フラグが true / false で明記されている。**false なのにクロージャのパスが
        critical-config.json のパターンに掛かるものは違反**(fail-closed — 未記入や誤記入で
        認証・決済・不可逆への接触が検証の優先順位と独立レビューの対象から漏れる穴を塞ぐ)。
        true をパターン不一致で咎めることはない(安全側の申告は上書きしない)
  BRC3  `## 影響範囲(closure)` に1行1パスで1件以上ある(空のクロージャは「何を検証すれば
        よいか」を verify 系に渡せない)
  BRC4  `## 主張` が突き合わせ可能である: 雛形の差し込み記号が残っていない・コマンドと
        最終行の逐語引用(バッククォート)が1つ以上ある・外部挙動の宣言行がある
        (裸の ✓ は散文であって主張ではない — build-record.md §2)
  BRC5  基本要件の点検: `.claude/directions/baseline.md` §2 の全 BR-nn に 該当 / 非該当 の
        判定行がある。該当は落とし先まで(**どこが落とし先かは項目ごとに違う** —
        `baseline.md` §2 の「既定の落とし先」の欄が正である。ここが見るのは、
        書かれた落とし先が実体 — ID・契約・パス — を指しているかだけである)。
        **空欄・「-」・雛形のままは未判定であって非該当ではない**

使い方:
    python3 .claude/scripts/check-buildrecord.py <slug | path>
    python3 .claude/scripts/check-buildrecord.py --all
    python3 .claude/scripts/check-buildrecord.py --list
    python3 .claude/scripts/check-buildrecord.py --selftest

終了コード: 0=合格 1=違反あり 2=使い方・前提エラー
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

RECORDS = Path("docs/build-records")
BASELINE = Path(".claude/directions/baseline.md")
CONFIG = Path(".claude/scripts/critical-config.json")
LOCAL = Path(".claude/scripts/critical-config.local.json")

CHECKS = {
    "BRC1": "frontmatter が壊れている(slug 不一致 / state 不正 / 日時が ISO でない / "
            "origin 欠落・不正 / building 以外なのに commit が実在しない)",
    "BRC2": "critical フラグが無い、または false なのにクロージャが critical パターンに掛かる",
    "BRC3": "影響範囲(closure)が空(1行1パスで、触った文書とコードを全部書く)",
    "BRC4": "主張が突き合わせ可能でない(雛形のまま / コマンドと最終行の逐語引用が無い / "
            "外部挙動の宣言が無い)",
    "BRC5": "基本要件(BR-nn)の判定が欠けている・未判定のまま・該当なのに落とし先が無い",
}

STATES = {"building", "awaiting-verify", "verified"}
ORIGINS = {"derived", "human-report"}
PLACEHOLDER = re.compile(r"<[^<>\n]{0,60}>")
BR_ROW = re.compile(r"^\|\s*\**\s*(BR-\d{2})\s*\**\s*\|")
BR_UNDECIDED = {"", "-", "—", "未定", "未判定", "TBD", "なし", "?"}
BR_LANDING = re.compile(r"docs/|[\w./-]+\.\w+|\b(?:FR|NFR|AC|E2E|MODULE|MOD|PLAN|CTR|D0|D1)-")
CLOSURE_PATH = re.compile(r"^[-*]\s+`?([\w][\w./-]*)`?")


def find_root(start: Path) -> Path:
    cur = start.resolve()
    for cand in (cur, *cur.parents):
        if (cand / "CLAUDE.md").is_file() and (cand / ".claude").is_dir():
            return cand
    return cur


def critical_patterns(root: Path) -> list[str]:
    out: list[str] = []
    for rel in (CONFIG, LOCAL):        # 和集合でマージ(check-lane 前身と同じ考え方)
        path = root / rel
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        v = data.get("critical_path_patterns")
        if isinstance(v, list):
            out += [s for s in v if isinstance(s, str) and s]
    return sorted(set(out))


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    return {m.group(1): m.group(2).strip('`"\'')
            for m in re.finditer(r"(?m)^(\w[\w-]*):\s*(.*?)\s*$", parts[1])}


def section(text: str, name: str) -> str | None:
    m = re.search(rf"^##[^\n]*{re.escape(name)}[^\n]*$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    return m.group(1) if m else None


def closure_paths(text: str) -> list[str]:
    body = section(text, "影響範囲") or ""
    out = []
    for line in body.splitlines():
        m = CLOSURE_PATH.match(line.strip())
        if m and not PLACEHOLDER.search(line):
            out.append(m.group(1))
    return out


def commit_ok(root: Path, value: str) -> tuple[bool, str]:
    """形式(7〜40桁の16進)と、引ける環境では git 上の実在を見る。"""
    if not re.fullmatch(r"[0-9a-f]{7,40}", value or ""):
        return False, f"「{value or '空'}」は commit の形をしていない"
    import subprocess
    try:
        r = subprocess.run(["git", "cat-file", "-e", f"{value}^{{commit}}"],
                           cwd=root, capture_output=True)
    except OSError:
        return True, ""                       # git が無い環境では形式検査まで
    if r.returncode != 0:
        # git はあるがリポジトリ外・浅い clone 等でも失敗しうる — repo かどうかで見分ける
        probe = subprocess.run(["git", "rev-parse", "--git-dir"], cwd=root, capture_output=True)
        if probe.returncode != 0:
            return True, ""
        return False, f"「{value}」は git に実在しない"
    return True, ""


def iso_ok(value: str) -> bool:
    try:
        datetime.fromisoformat(value)
        return True
    except ValueError:
        return False


def baseline_ids(root: Path) -> list[str] | None:
    path = root / BASELINE
    if not path.is_file():
        return None
    ids: list[str] = []
    for line in path.read_text(errors="replace").splitlines():
        m = BR_ROW.match(line.strip())
        if m and m.group(1) not in ids:
            ids.append(m.group(1))
    return ids or None


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def check_record(root: Path, path: Path) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    text = re.sub(r"<!--.*?-->", "", path.read_text(encoding="utf-8", errors="replace"),
                  flags=re.S)
    fm = frontmatter(text)

    # BRC1
    if fm.get("slug", "") != path.stem:
        out.append(("BRC1", f"slug 「{fm.get('slug', '')}」がファイル名 {path.stem} と違う"))
    if fm.get("state", "") not in STATES:
        out.append(("BRC1", f"state 「{fm.get('state', '')}」は "
                            "building / awaiting-verify / verified のどれでもない"))
    for k in ("started", "updated"):
        if not iso_ok(fm.get(k, "")):
            out.append(("BRC1", f"{k} が ISO 日時でない: 「{fm.get(k, '')}」"))
    if fm.get("origin", "") not in ORIGINS:
        out.append(("BRC1", f"origin 「{fm.get('origin', '')}」が無いか、derived / human-report の"
                            "どちらでもない(欠落を derived に既定しない)"))
    if fm.get("state") in ("awaiting-verify", "verified"):
        ok, why = commit_ok(root, fm.get("commit", ""))
        if not ok:
            out.append(("BRC1", f"state: {fm.get('state')} なのに commit が不正: {why}"
                                "(promote と F4 の犯人探しは commit に紐づく)"))

    # BRC3(BRC2 がクロージャを読むので先に)
    paths = closure_paths(text)
    if not paths:
        out.append(("BRC3", "`## 影響範囲(closure)` に実パスが1件も無い"))

    # BRC2
    critical = fm.get("critical", "")
    if critical not in ("true", "false"):
        out.append(("BRC2", f"critical が true / false で書かれていない: 「{critical}」"))
    elif critical == "false":
        pats = critical_patterns(root)
        hits = [p for p in paths for pat in pats if pat.lower() in p.lower()]
        if hits:
            out.append(("BRC2", f"critical: false だがクロージャが critical パターンに掛かる: "
                                f"{', '.join(sorted(set(hits))[:3])} — true に直すか、"
                                "非該当の根拠を主張に書いた上で local 設定でパターンを絞る"))

    # BRC4
    claims = section(text, "主張")
    if claims is None or not PLACEHOLDER.sub("", claims).strip().strip("-* \n"):
        out.append(("BRC4", "`## 主張` が無いか空(触ったテスト green / 外部挙動 / "
                            "critical 接触を、後で突き合わせ可能な形で宣言する)"))
    else:
        if PLACEHOLDER.search(claims):
            out.append(("BRC4", "主張に雛形の差し込み記号(<…>)が残っている"))
        if "`" not in claims:
            out.append(("BRC4", "主張にコマンドと最終行の逐語引用(バッククォート)が1つも無い"
                                "(裸の ✓ は散文 — build-record.md §2)"))
        # **値まで読む** ★(2026-09-04)— 語の存在だけを見ていた間、この行は誰にも
        # 読まれていなかった。成果物の版の桁はここから決まる(`flows.md` §9)。
        # **判定は `stamps.py` の1箇所が持つ**(原則10。同じ規則を二度実装しない) —
        # 入口(ここ)と出口(リリース)で規則がずれると、出口を通った記録がリリースを止める。
        try:
            import stamps
            kind = stamps.behaviour_change(text)            # **入力も同じにする**(節だけを読む)
        except Exception as exc:
            # **黙って旧い検査へ戻らない** ★ — 戻れば「語が在るか」だけになり、
            # 3値でない値が出口を抜けてリリースで止まる(独立検査 2026-09-04)。
            out.append(("BRC4", f"外部挙動の変化の判定器(stamps.py)を読めない: {exc}"))
            kind = None
        if kind == "不明":
            out.append(("BRC4", "外部挙動の変化が3つの値のどれでもない"
                                "(なし / あり(後方互換。…)/ あり(互換を壊す。…))"))

    # BRC5
    ids = baseline_ids(root)
    if ids is None:
        out.append(("BRC5", "baseline.md §2 が読めない(基本要件の一覧が無い)"))
    else:
        body = section(text, "基本要件の点検")
        rows: dict[str, list[str]] = {}
        for line in (body or "").splitlines():
            g = BR_ROW.match(line.strip())
            if g and g.group(1) not in rows:
                rows[g.group(1)] = _cells(line)
        for br in ids:
            cells = rows.get(br)
            if cells is None:
                out.append(("BRC5", f"{br} の判定行が無い"))
                continue
            verdict = (cells[1] if len(cells) > 1 else "").strip("`* 　")
            why = cells[2] if len(cells) > 2 else ""
            land = cells[3] if len(cells) > 3 else ""
            if PLACEHOLDER.search(verdict) or not (verdict.startswith("該当")
                                                   or verdict.startswith("非該当")):
                out.append(("BRC5", f"{br} の判定が 該当 / 非該当 のどちらでもない: "
                                    f"「{verdict}」(空欄・雛形のままは未判定)"))
                continue
            if why in BR_UNDECIDED or PLACEHOLDER.search(why):
                out.append(("BRC5", f"{br} の理由が空(理由の無い非該当は未判定と"
                                    "区別できない)"))
            if verdict.startswith("該当") and (land in BR_UNDECIDED
                                               or PLACEHOLDER.search(land)
                                               or not BR_LANDING.search(land)):
                out.append(("BRC5", f"{br} は該当なのに落とし先が実体を指していない: "
                                    f"「{land}」(ID・契約・パスのいずれかを指すこと。"
                                    f"どこへ降ろすかは baseline.md §2 の欄)"))
    return out


def run(root: Path, targets: list[Path]) -> int:
    total = 0
    for path in targets:
        found = check_record(root, path)
        total += len(found)
        if found:
            print(f"NG  {path.relative_to(root)}: {len(found)} 件")
            for cid, msg in found:
                print(f"  {cid}  {msg}")
        else:
            print(f"OK  {path.relative_to(root)}")
    return 1 if total else 0


def main(argv: list[str]) -> int:
    args = argv[1:]
    if "--selftest" in args:
        return selftest()
    if "--list" in args:
        for cid, desc in CHECKS.items():
            print(f"{cid}: {desc}")
        return 0
    if not args or any(a in ("-h", "--help") for a in args):
        print(__doc__)
        return 0 if args else 2
    root = find_root(Path.cwd())
    if args[0] == "--all":
        base = root / RECORDS
        targets = sorted(p for p in base.glob("*.md")
                         if p.name != "index.md") if base.is_dir() else []
        if not targets:
            print("構築記録なし(docs/build-records/ が空)")
            return 0
        return run(root, targets)
    cand = Path(args[0])
    if not cand.is_file():
        cand = root / RECORDS / f"{args[0]}.md"
    if not cand.is_file():
        print(f"エラー: 構築記録が見つからない: {args[0]}", file=sys.stderr)
        return 2
    return run(root, [cand.resolve()])


def selftest() -> int:
    import contextlib, io, os, tempfile
    previous = Path.cwd()
    quiet = contextlib.redirect_stdout(io.StringIO())
    with tempfile.TemporaryDirectory() as td, quiet:
        root = Path(td)
        (root / ".claude/scripts").mkdir(parents=True)
        (root / ".claude/directions").mkdir(parents=True)
        (root / "CLAUDE.md").write_text("x", encoding="utf-8")
        (root / BASELINE).write_text(
            "## 2. 一覧\n| ID | 名前 |\n|---|---|\n| BR-01 | a |\n| BR-02 | b |\n",
            encoding="utf-8")
        (root / CONFIG).write_text(json.dumps({"critical_path_patterns": ["auth"]}),
                                   encoding="utf-8")
        rec = root / RECORDS; rec.mkdir(parents=True)
        os.chdir(root)
        good = ("---\nslug: add-x\nstate: building\ncritical: false\norigin: derived\n"
                "started: 2026-08-19T09:00:00+09:00\nupdated: 2026-08-19T09:00:00+09:00\n---\n"
                "## 影響範囲(closure)\n- docs/01-requirements/functional.md\n- src/x.py\n"
                "## 主張\n- 触ったモジュールのテスト: green(`pytest tests/x` → `3 passed`)\n"
                "- 外部挙動の変化: なし\n"
                "## 基本要件の点検\n| ID | 判定 | 理由 | 落とし先 |\n|---|---|---|---|\n"
                "| BR-01 | 非該当 | 認証に触れない | - |\n"
                "| BR-02 | 該当 | 入力を受ける | FR-x-01-1 |\n")
        # 宣言が2行在るものは拒む(先頭だけを採らない)
        (rec / "add-x.md").write_text(
            good.replace("- 外部挙動の変化: なし",
                         "- 外部挙動の変化: なし\n- 外部挙動の変化: あり(互換を壊す。x)"),
            encoding="utf-8")
        assert main(["x", "add-x"]) == 1, "宣言が2行在るのに先頭だけを採った"
        (rec / "add-x.md").write_text(good, encoding="utf-8")
        assert main(["x", "add-x"]) == 0, "正しい記録が落ちた"
        # 外部挙動の変化は3値である(2026-09-04)。**値まで読む** — 版の桁がここから決まる
        for ok in ("なし", "あり(後方互換。画面を1つ足した)", "あり(互換を壊す。引数を必須にした)"):
            (rec / "add-x.md").write_text(
                good.replace("- 外部挙動の変化: なし", f"- 外部挙動の変化: {ok}"), encoding="utf-8")
            assert main(["x", "add-x"]) == 0, f"正しい値が落ちた: {ok}"
        for ng in ("あり", "あり(画面を1つ足した)", "たぶん無い",
                   "あり(後方互換XYZ)", "あり(互換を壊す。)", "あり(後方互換。説明なし"):
            (rec / "add-x.md").write_text(
                good.replace("- 外部挙動の変化: なし", f"- 外部挙動の変化: {ng}"), encoding="utf-8")
            assert main(["x", "add-x"]) == 1, f"3値のどれでもない値を通した: {ng}"
        (rec / "add-x.md").write_text(good, encoding="utf-8")
        # critical: false + auth パスは落ちる(fail-closed)
        (rec / "add-x.md").write_text(good.replace("src/x.py", "src/auth/login.py"),
                                      encoding="utf-8")
        assert main(["x", "add-x"]) == 1, "critical パターンを見逃した"
        # critical: true は咎めない
        (rec / "add-x.md").write_text(
            good.replace("critical: false", "critical: true")
                .replace("src/x.py", "src/auth/login.py"), encoding="utf-8")
        assert main(["x", "add-x"]) == 0, "true 申告が咎められた"
        # BR の欠落・未判定は落ちる
        (rec / "add-x.md").write_text(good.replace("| BR-02 | 該当 | 入力を受ける | FR-x-01-1 |\n",
                                                   ""), encoding="utf-8")
        assert main(["x", "add-x"]) == 1, "BR 欠落を見逃した"
        (rec / "add-x.md").write_text(good.replace("非該当 | 認証に触れない", "<該当/非該当> | <>"),
                                      encoding="utf-8")
        assert main(["x", "add-x"]) == 1, "雛形のままを見逃した"
        # origin 欠落は落ちる(既定しない)
        (rec / "add-x.md").write_text(good.replace("origin: derived\n", ""), encoding="utf-8")
        assert main(["x", "add-x"]) == 1, "origin 欠落を見逃した"
        # awaiting-verify なのに commit が無いのは落ちる
        (rec / "add-x.md").write_text(good.replace("state: building", "state: awaiting-verify"),
                                      encoding="utf-8")
        assert main(["x", "add-x"]) == 1, "commit 無しの awaiting-verify を見逃した"
        # 主張に逐語引用が無いのは落ちる
        (rec / "add-x.md").write_text(
            good.replace("- 触ったモジュールのテスト: green(`pytest tests/x` → `3 passed`)",
                         "- 触ったモジュールのテスト green"), encoding="utf-8")
        assert main(["x", "add-x"]) == 1, "逐語引用の無い主張を見逃した"
        # state 不正・クロージャ空も落ちる
        (rec / "add-x.md").write_text(good.replace("state: building", "state: done"),
                                      encoding="utf-8")
        assert main(["x", "add-x"]) == 1, "state 不正を見逃した"
        (rec / "add-x.md").write_text(good.replace("- docs/01-requirements/functional.md\n", "")
                                      .replace("- src/x.py\n", ""), encoding="utf-8")
        assert main(["x", "add-x"]) == 1, "空クロージャを見逃した"
        os.chdir(previous)
    print("OK check-buildrecord: 合格/critical fail-closed/true尊重/BR欠落/雛形/origin/commit/主張/state/クロージャ/外部挙動の3値")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
