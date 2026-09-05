#!/usr/bin/env python3
"""検証負債の計器。**数えて出すだけで、何も拒まない**(`/build` の入口で読む)。

フロー分離は「検証をあとで払う」設計である(及第ライン — CLAUDE.md §4)。負債がどれだけ
溜まっているかは見えていなければならないが、**着手を止める判断はこのスクリプトが持たない** —
拒む役は及第ライン(デプロイゲート `stamps.py check`)だけが持つ(規範:
.claude/directions/flows.md §4)。ゆえにここには超過という概念が無く、設定に値も無い。

数えて出すもの:
  (1) 未検証の構築記録: docs/build-records/*.md の state: awaiting-verify。
      **building のまま max_building_hours を超えて滞留したものも未検証に数える**
      (放置された過渡状態は verify の穴になる — --demote で awaiting-verify へ降格できる。
       この時間は拒むための値ではなく、過渡状態と滞留を分ける定義である)。
      **未コミットの変更が残る間、--demote は見送る**: 降格した記録は再開プローブ
      (`/build <slug>` — orchestration.md §3.2.1)の対象から外れるので、降格してよいのは
      コミット済みの仕事だけである(inspection-16 H-6)。
      **state が読めない・語彙の外の記録も未検証に数える**(記録を壊すと負債から
      消える、を許さない。inspection-14)
  (2) verify 系(F2/F3、および F4 の **f4_scopes の各試験区分**)の最終 green の古さ。
      いちばん古いものを日数で出す(鮮度スタンプ皆無・試験区分の欠けはその名を出す)。
      **読むのは `last_green` である**(`stamps.py` の `green_entry` が正 — 原則10)。
      素の red は最終 green の基準点を消さないので(inspection-17 判断4)、
      **red を1回記録しただけで「一度も検証されていない」と出してはならない**
      (inspection-21 C-9)。
      **これは「記録した日からの日数」であって、いま green かどうかではない** — 失効の正は
      `stamps.py check` である(1時間前に記録して直後に失効した鮮度スタンプも「0日」と出る)。
      どのフローを先に回すかを決めるなら、この数字ではなく `stamps.py check` を読むこと。
  (3) **全数(`all`)の最終実行からの日数**(`stamps.py record --full` が残す印)。
      増分では回らない検査が在る(用語の例が埋まっているかの点検・決定の見直す条件の発火 — flows.md §2.1)ので、
      「一度も全数を回さないまま green」に気づける唯一の数字である。**これも何も拒まない。**
  (4) 未回答シート: docs/sheets/ に残っているファイル
      (回答は転記とともにシートを削除するのが規範 — **残っている = 未回答**)
  (5) **試験区分の置き場の宣言漏れ**: `scope_roots` / `ui_roots` を宣言していないために
      広いほうへ倒れている試験区分の件数(判定の正は `stamps.py` の `widened` — 原則10)。
      **宣言する行為はどの手順の義務でもない**: 狭く誤ると穴になるので正は
      「迷ったら書かない」であり、義務にすればその反対を全作業に配ることになる
      (inspection-23 C-8)。**だからここは数えるだけである** — 内訳と直し方は
      `stamps.py check` の注記が出す。**これも何も拒まない。**

使い方:
    python3 .claude/scripts/check-debt.py
    python3 .claude/scripts/check-debt.py --demote     # 滞留した building を降格して数え直す
    python3 .claude/scripts/check-debt.py --selftest

終了コード: 0=読めた(数の大小では変わらない) 2=使い方・解析エラー
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import stamps                     # noqa: E402  鮮度スタンプの読み方の正はあちら側(原則10)

CONFIG = Path(".claude/scripts/flow-config.json")
LOCAL = Path(".claude/scripts/flow-config.local.json")
STATE = Path(".claude/state/stamps.json")
RECORDS = Path("docs/build-records")
SHEETS = Path("docs/sheets")
DEFAULTS = {"max_building_hours": 24}
VERIFY_FLOWS = ("verify-docs", "verify-impl", "verify-tests")


def find_root(start: Path) -> Path:
    cur = start.resolve()
    for cand in (cur, *cur.parents):
        if (cand / "CLAUDE.md").is_file() and (cand / ".claude").is_dir():
            return cand
    return cur


def settings(root: Path) -> dict[str, int]:
    """building の滞留を分ける時間だけを読む(拒むための値はもう無い)。"""
    out = dict(DEFAULTS)
    for rel in (CONFIG, LOCAL):
        path = root / rel
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except OSError:
            continue                    # 読めない(権限等)は無いのと同じ
        except ValueError:
            # 黙って既定へ縮退しない — max_building_hours が意図と違う値で走るのは誤値方向
            # (inspection-17 低位)。走行は止めないが、壊れていることは必ず言う。
            print(f"警告: {rel} が JSON として読めない — 既定値で走る(設定を直すこと)",
                  file=sys.stderr)
            continue
        for k in DEFAULTS:
            if isinstance(data.get(k), int) and data[k] >= 0:
                out[k] = data[k]
    return out


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    out = {}
    for m in re.finditer(r"(?m)^(\w[\w-]*):\s*(.*?)\s*$", parts[1]):
        out[m.group(1)] = m.group(2).strip('`"\'')
    return out


def parse_ts(value: str) -> datetime | None:
    try:
        ts = datetime.fromisoformat(value)
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def records(root: Path) -> list[tuple[Path, dict[str, str]]]:
    base = root / RECORDS
    if not base.is_dir():
        return []
    return [(p, frontmatter(p.read_text(encoding="utf-8", errors="replace")))
            for p in sorted(base.glob("*.md"))
            if p.name != "index.md" and not p.name.startswith("._")]


def debt_records(root: Path, conf: dict, now: datetime) -> tuple[list[str], list[Path]]:
    """(未検証扱いの記録の名前一覧, 降格すべき building 滞留の一覧)。"""
    names, stale = [], []
    for path, fm in records(root):
        state = fm.get("state", "")
        if state == "awaiting-verify":
            names.append(f"{path.name} (awaiting-verify)")
        elif state == "building":
            ts = parse_ts(fm.get("updated", "") or fm.get("started", ""))
            if ts is None or (now - ts).total_seconds() > conf["max_building_hours"] * 3600:
                names.append(f"{path.name} (building 滞留 > {conf['max_building_hours']}h)")
                stale.append(path)
        elif state != "verified":
            # 壊れた記録・語彙の外は「未検証」に数える — 壊すと負債から消える経路を塞ぐ
            names.append(f"{path.name} (state が読めない/語彙の外: 「{state or '無し'}」)")
    return names, stale


def f4_scopes(root: Path) -> list[str]:
    for rel in (LOCAL, CONFIG):        # local が優先(stamps.py と同じ規則)
        path = root / rel
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        v = data.get("f4_scopes")
        if not (isinstance(v, list) and v and all(isinstance(s, str) for s in v)):
            continue
        got = set(v)
        # 受理する縮小は qa 外しだけ(stamps.py と同じ fail-closed — inspection-16 H-5)
        default = ["unit", "integration", "e2e", "qa"]
        if got == set(default) or got == set(default) - {"qa"}:
            return [x for x in default if x in got]
        return default
    return ["unit", "integration", "e2e", "qa"]


def last_green_age_days(root: Path, now: datetime) -> tuple[float | None, str]:
    """verify 系(F4 は試験区分別)のうち最も古い最終 green の経過日数。欠けがあれば (None, 理由)。

    **`latest` ではなく `last_green` を読む**(`stamps.py green_entry` が正 — 原則10)。
    素の red は基準点を消さないので、red を1回記録したフローを
    「green 鮮度スタンプが無い」に落としてはならない(inspection-21 C-9)。"""
    data = stamps.load_stamps(root)
    need = ["verify-docs", "verify-impl"] + [f"verify-tests:{s}" for s in f4_scopes(root)]
    worst: float | None = None
    missing = []
    for k in need:
        e = stamps.green_entry(data, k)
        ts = parse_ts(str(e.get("at", ""))) if isinstance(e, dict) else None
        if ts is None:
            missing.append(k)
            continue
        age = (now - ts).total_seconds() / 86400
        worst = age if worst is None else max(worst, age)
    if missing:
        return None, "green 鮮度スタンプが無い: " + ", ".join(missing)
    return worst, ""


def last_full(root: Path, now: datetime) -> str:
    """全数(`all`)の最終実行を1行にする。**拒まない計器の1項目**(flows.md §2.1)。

    対象は F2/F3 のみ — F4 は毎回が suite 丸ごと=全数であり印を持たない(inspection-16 D1)。"""
    path = root / STATE
    marks = {}
    if path.is_file():
        try:
            marks = json.loads(path.read_text(encoding="utf-8")).get("full", {})
        except (OSError, ValueError):
            marks = {}
    if not isinstance(marks, dict):
        marks = {}
    need = ["verify-docs", "verify-impl"]      # F4 は全数の印を持たない(D1)
    out = []
    for k in need:
        e = marks.get(k)
        ts = parse_ts(str(e.get("at", ""))) if isinstance(e, dict) else None
        if ts is None:
            out.append(f"{k}=一度も無い")
            continue
        out.append(f"{k}={(now - ts).total_seconds() / 86400:.0f}日前")
    return " / ".join(out)


def open_sheets(root: Path) -> list[str]:
    """docs/sheets/ に残っているシート。**残っていること自体が未回答である**(古さは問わない)。"""
    base = root / SHEETS
    if not base.is_dir():
        return []
    out = []
    for p in sorted(base.glob("*.md")):
        fm = frontmatter(p.read_text(encoding="utf-8", errors="replace"))
        made = fm.get("created", "") or fm.get("date", "")
        out.append(f"{p.name}({made} 作成)" if made else p.name)
    return out


def scope_declaration_gaps(root: Path) -> list:
    """置き場の宣言が無いせいで広いほうへ倒れている (フロー, 試験区分) の一覧。

    **判定の正は `stamps.widened` である**(原則10 — 規則をここへ書き写さない)。
    **宣言する行為はどの手順の義務でもない**: 狭く誤ると穴になるので正は
    「迷ったら書かない」であり、義務にすればその反対を全作業に配ることになる
    (inspection-23 C-8)。ここは数えるだけで、何も拒まない。"""
    out = []
    for scope in f4_scopes(root):
        why = stamps.widened(root, "verify-tests", scope)
        if why is not None:
            out.append((f"verify-tests:{scope}", why))
    return out


def main(argv: list[str]) -> int:
    args = argv[1:]
    if "--selftest" in args:
        return selftest()
    if any(a in ("-h", "--help") for a in args):
        print(__doc__); return 0
    demote = "--demote" in args
    if [a for a in args if a != "--demote"]:
        print(__doc__); return 2

    root = find_root(Path.cwd())
    conf = settings(root)
    now = datetime.now(timezone.utc)
    names, stale = debt_records(root, conf, now)

    if demote and stale:
        import subprocess
        pending = []
        try:
            st = subprocess.run(["git", "status", "--porcelain"], cwd=root,
                                capture_output=True, text=True, check=True)
            pending = [ln for ln in st.stdout.splitlines() if ln.strip()]
        except OSError:
            pending = []              # git の無い環境では従来どおり(降格は git 前提の運用)
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr or ""
            if "not a git repository" in stderr:
                pending = []          # リポジトリ外 = git の無い環境と同じ扱い(従来どおり)
            else:
                # git リポジトリの中で status が失敗した(壊れた index・ロック等)。
                # 「未コミットなし」と読むと作業中ツリーでも降格が走る(inspection-17 M-14)。
                # 判定不能は見送りへ倒す(fail-closed)。
                print("降格を見送り: git status が失敗し、未コミットの有無を判定できない"
                      f"(exit {exc.returncode})。git を直してから --demote を出し直すこと")
                stale = []
        if pending:
            print(f"降格を見送り: 作業ツリーに未コミットの変更が {len(pending)} 件 — "
                  "滞留 building の途中成果かもしれず、降格すると再開経路"
                  "(/build <slug> — orchestration.md §3.2.1)が消える。"
                  "コミットするか片付けてから --demote を出し直すこと")
            stale = []
        sha = ""
        try:
            sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                                 text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            pass
        for path in stale:
            text = path.read_text(encoding="utf-8")
            text = re.sub(r"(?m)^state:\s*building\s*$", "state: awaiting-verify", text, count=1)
            text = re.sub(r"(?m)^updated:\s*.*$",
                          f"updated: {now.isoformat(timespec='seconds')}", text, count=1)
            if sha:
                # 変更点はこの HEAD 以前のどこか — 検証範囲の上界として現在の HEAD を刻む
                text = re.sub(r"(?m)^commit:\s*(-|<[^>]*>)?\s*$",
                              f"commit: {sha}", text, count=1)
            path.write_text(text, encoding="utf-8")
            print(f"降格: {path.name} building → awaiting-verify(次の検証の周の対象に戻す)")
        names, stale = debt_records(root, conf, now)

    print(f"未検証の構築記録: {len(names)} 件")
    for n in names:
        print(f"  - {n}")
    age, why = last_green_age_days(root, now)
    if age is None:
        print(f"verify 系の最終 green: {why}")
    else:
        print(f"verify 系の最終 green: 最も古いフローで {age:.1f} 日前"
              "(記録日からの日数。いま green かの正は stamps.py check)")
    print("全数(all)の最終実行: " + last_full(root, now))
    gaps = scope_declaration_gaps(root)
    # **注記は件数の行に付ける** — 内訳の最後の1件の理由の中に貼り付くと、その1件だけの
    # 但し書きに見える(inspection-23 C-8 の独立確認)。
    print(f"試験区分の置き場の宣言漏れ: {len(gaps)} 件"
          + "(宣言が無いぶん広く倒れている = 無関係な変更でも失効する。"
            "判定は変えていない。内訳の直し方は stamps.py check の注記。"
            "宣言は義務ではない — 狭く誤ると穴になるので、迷ったら宣言しない)"
          + ("".join(f"\n  - {k} — {why}" for k, why in gaps) if gaps else ""))
    sheets = open_sheets(root)
    print(f"未回答シート: {len(sheets)} 件"
          + (" — " + ", ".join(sheets) if sheets else ""))
    print("→ この計器は着手を拒まない。**自動配車はこの数を読んで報告するだけで、"
          "次に何を回すかを決めない**(契機は人間の指示、範囲はデプロイゲート stamps.py check。"
          "正は directions/flows.md §4)。**人間はこの数を判断材料にしてよい**")
    return 0


def selftest() -> int:
    import contextlib, io, os, tempfile
    previous = Path.cwd()

    def run(*extra: str) -> tuple[int, str]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(["x", *extra])
        return code, buf.getvalue()

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / ".claude/scripts").mkdir(parents=True)
        (root / "CLAUDE.md").write_text("x", encoding="utf-8")
        rec = root / "docs/build-records"; rec.mkdir(parents=True)
        os.chdir(root)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        assert run()[0] == 0, "空で 0 を返さなかった"
        (root / ".claude/state").mkdir(parents=True)
        stamp = {"latest": {k: {"flow": f, "scope": s, "commit": "c", "at": now,
                                "verdict": "green"}
                            for k, f, s in [("verify-docs", "verify-docs", None),
                                            ("verify-impl", "verify-impl", None),
                                            ("verify-tests:unit", "verify-tests", "unit"),
                                            ("verify-tests:integration", "verify-tests", "integration"),
                                            ("verify-tests:e2e", "verify-tests", "e2e"),
                                            ("verify-tests:qa", "verify-tests", "qa")]}}
        (root / STATE).write_text(json.dumps(stamp), encoding="utf-8")
        # **どれだけ溜まっても拒まない**(旧 max_awaiting_verify の撤廃がこれ)
        for n in range(6):
            (rec / f"r{n}.md").write_text(
                f"---\nslug: r{n}\nstate: awaiting-verify\nupdated: {now}\n---\n",
                encoding="utf-8")
        code, out = run()
        assert code == 0, "未検証6件で拒んだ"
        assert "未検証の構築記録: 6 件" in out, f"件数を出していない: {out}"
        assert "上限" not in out, f"出力に上限が残っている: {out}"
        # 古い鮮度スタンプも拒まない。日数として出るだけ
        old = {"latest": {k: dict(v, at="2020-01-01T00:00:00+00:00")
                          for k, v in stamp["latest"].items()}}
        (root / STATE).write_text(json.dumps(old), encoding="utf-8")
        code, out = run()
        assert code == 0, "古い鮮度スタンプで拒んだ"
        assert "日前" in out, f"鮮度スタンプの古さを出していない: {out}"
        assert "全数(all)の最終実行: " in out and "一度も無い" in out, \
            f"全数の鮮度を出していない: {out}"
        # 素の red は最終 green の基準点を消さない(inspection-21 C-9)。
        # latest が red でも last_green が在れば「日数」で出る。
        red = {"latest": {k: dict(v, verdict="red") for k, v in stamp["latest"].items()},
               "last_green": dict(stamp["latest"])}
        (root / STATE).write_text(json.dumps(red), encoding="utf-8")
        code, out = run()
        assert "green 鮮度スタンプが無い" not in out, \
            f"red を1回記録しただけで「一度も検証されていない」と出した: {out}"
        (root / STATE).write_text(json.dumps(stamp), encoding="utf-8")
        # 壊れた state は未検証に数える
        (rec / "z.md").write_text("---\nslug: z\nstate: done\n---\n", encoding="utf-8")
        code, out = run()
        assert "z.md (state が読めない/語彙の外" in out, f"壊れた state が漏れた: {out}"
        (rec / "z.md").unlink()
        for n in range(6):
            (rec / f"r{n}.md").unlink()
        # building 滞留は未検証に数え、--demote で降格される
        (rec / "b.md").write_text(
            "---\nslug: b\nstate: building\nupdated: 2020-01-01T00:00:00+00:00\n---\n",
            encoding="utf-8")
        code, out = run()
        assert "building 滞留" in out, f"滞留を数えていない: {out}"
        run("--demote")
        demoted = (rec / "b.md").read_text(encoding="utf-8")
        assert "awaiting-verify" in demoted, "--demote が降格しなかった"
        assert "updated: 2020-01-01" not in demoted, "--demote が updated を進めなかった"
        (rec / "b.md").unlink()
        # 未コミットの変更が在る間は --demote が見送る(降格は再開経路を消す — inspection-16 H-6)
        import subprocess
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        (rec / "b2.md").write_text(
            "---\nslug: b2\nstate: building\nupdated: 2020-01-01T00:00:00+00:00\n---\n",
            encoding="utf-8")
        code, out = run("--demote")
        assert "state: building" in (rec / "b2.md").read_text(encoding="utf-8"), \
            "汚れた作業ツリーで降格した"
        assert "降格を見送り" in out, f"見送りの理由を出していない: {out}"
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "-m", "c"], cwd=root, check=True)
        run("--demote")
        assert "awaiting-verify" in (rec / "b2.md").read_text(encoding="utf-8"), \
            "クリーンな作業ツリーで降格しない"
        (rec / "b2.md").unlink()
        # 残っているシートは古さを問わず未回答に数える(拒みはしない)
        sheets = root / "docs/sheets"; sheets.mkdir(parents=True)
        (sheets / "s.md").write_text(f"---\ncreated: {now}\n---\n", encoding="utf-8")
        code, out = run()
        assert code == 0, "未回答シートで拒んだ"
        assert "未回答シート: 1 件" in out, f"新しいシートを数えていない: {out}"
        # 試験区分の置き場の宣言漏れは数えるだけ(義務にしない — inspection-23 C-8)
        assert "試験区分の置き場の宣言漏れ: 0 件" in out, \
            f"置き場が未宣言のとき 0 件と出していない: {out}"
        (root / ".claude/scripts/flow-config.local.json").write_text(
            json.dumps({"code_roots": ["src/"]}), encoding="utf-8")
        code, out = run()
        assert code == 0, "宣言漏れが在るのに拒んだ"
        assert "試験区分の置き場の宣言漏れ: 4 件" in out, \
            f"広く倒れている試験区分を数えていない: {out}"
        assert "義務ではない" in out, f"宣言が義務でないことを言っていない: {out}"
        (root / ".claude/scripts/flow-config.local.json").unlink()
        # 撤廃した旗は使い方エラーになる(黙って無視して通さない)
        for gone in ("--repair", "--override", "--for-issue"):
            assert run(gone)[0] == 2, f"撤廃した {gone} が受け付けられた"
        os.chdir(previous)
    print("OK check-debt: 何も拒まない/件数・鮮度スタンプの古さ・全数の鮮度・未回答シートの表示/"
          "置き場の宣言漏れは数えるだけ/"
          "滞留降格/壊れたstate/撤廃した旗/red は最終 green の表示を消さない")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
