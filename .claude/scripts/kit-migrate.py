#!/usr/bin/env python3
"""キットの版を上げた後に、このプロジェクトで要る移行を台帳から数え上げる。

**上書き展開(`tar -xzf`)で直るものは、この台帳に載らない。** 載るのは、配布物を展開しても
直らないものだけである — 記録ファイルの引っ越し、配布物に含まれない設定ファイルへの追記、
プロジェクトが自分で持っている宣言の作り直し。**その3つは展開では触られないので、
黙って取り残される。**

台帳は `.claude/migrations/*.md` で、1件 = 1ファイル。frontmatter は次の6つで、
**6つとも必須である**(欠けは台帳の不備として終了コード 2):

    id:      ファイル名の拡張子を除いた部分と同じ(取り違えと重複の検出に使う)
    since:   この移行が本流に入った日(YYYY-MM-DD)
    kind:    mechanical(手順が機械的に決まる)/ judgment(人間の判断が要る)
    detect:  シェル1行。**0 = まだ要る / 1 = 済んでいる / それ以外 = 判定できなかった**
    paths:   その移行が触るパス(空白区切り)。**未コミットの差分が在れば当てさせない**
    summary: 1行要約(報告にそのまま載る長さで書く)

**`detect` の 1 と「それ以外」を分けるのは、シェルがそう作られているからである** — `test` と
`grep` は「偽」を 1 で返し、**命令が無い(127)・構文が壊れている(2)・打ち切り**はどれも別の値に
なる。**判定できなかったものを「済んだ」と言うと、移行が黙って消える**(2026-08-25 の独立検査
D-1)。だから **1 だけを「済んだ」と読み、他は全部「判定できなかった」として要る側に並べる。**

**`paths` は関所である。** そのパスに未コミットの差分が在るあいだ、**その移行は当てられない** —
差分が在るのは**誰かがいまそこを書いている**ということであり、移行で上書きすれば書きかけが
戻らない。移行はいつでも当て直せる。

本文には「何が変わったか」「手順」「移らなかったときに何が起きるか」を書く。
**本文を読んで手順を当てるのは `/kit-migrate`(人間か AI)であって、この道具ではない** —
機械に当てられない形の手順が混ざるからである。この道具がするのは、
**どれが要るかを判定して並べること**だけである。

`detect` に書けるのは**キットが配る文字列だけ**である(プロジェクトが書き足すものではない)。
実行はプロジェクトのルートで、1件 30 秒で打ち切る。

    python3 .claude/scripts/kit-migrate.py            # list。要る/不要を並べる
    python3 .claude/scripts/kit-migrate.py check      # 要るものが在れば 1、無ければ 0
    python3 .claude/scripts/kit-migrate.py --selftest

**終了コードは `tools-readme.md` §2 の約束どおりである**: 0=問題なし / 1=検出あり(要る移行が
在る)/ 2=設定・解析のエラー(台帳の不備)。**`list` は表示専用なので 1 を返さない** —
判定に使う側は `check` を打つ。
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

LEDGER = ".claude/migrations"
FIELDS = ("id", "since", "kind", "detect", "paths", "summary")
KINDS = ("mechanical", "judgment")
TIMEOUT = 30
SKIP = {"README.md"}  # 台帳の読み方への案内。移行の項目ではない

NEEDED, DONE, UNKNOWN, BUSY = "要る", "不要", "判定不能", "書きかけ"


def frontmatter(text: str) -> dict[str, str]:
    """`---` で囲まれた `key: value` を読む。**値の中の `:` は残す。**

    yaml を使わないのは、キットが外部の依存を1つも持たない範囲で済むからである
    (`detect` にはコロンを含むシェルが来るので、最初の `:` だけで割る)。
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    out: dict[str, str] = {}
    for ln in lines[1:]:
        if ln.strip() == "---":
            break
        if ":" not in ln:
            continue
        k, v = ln.split(":", 1)
        out[k.strip()] = v.strip()
    return out


def load(root: Path) -> tuple[list[dict[str, str]], list[str]]:
    """台帳を読む。**不備は落とさずに理由つきで返す** — 黙って飛ばすと移行が消える。"""
    d = root / LEDGER
    items: list[dict[str, str]] = []
    bad: list[str] = []
    if not d.is_dir():
        return items, bad
    seen: dict[str, str] = {}
    for p in sorted(d.glob("*.md")):
        if p.name in SKIP:
            continue
        fm = frontmatter(p.read_text(encoding="utf-8", errors="replace"))
        miss = [f for f in FIELDS if not fm.get(f)]
        if miss:
            bad.append(f"{p.name}: frontmatter に {', '.join(miss)} が無い")
            continue
        if fm["id"] != p.stem:
            bad.append(f"{p.name}: id({fm['id']})がファイル名({p.stem})と違う")
            continue
        if fm["kind"] not in KINDS:
            bad.append(f"{p.name}: kind が {' / '.join(KINDS)} のどれでもない({fm['kind']})")
            continue
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fm["since"]):
            bad.append(f"{p.name}: since が YYYY-MM-DD でない({fm['since']})")
            continue
        if fm["id"] in seen:
            bad.append(f"{p.name}: id が {seen[fm['id']]} と重複している")
            continue
        seen[fm["id"]] = p.name
        fm["_path"] = str(Path(LEDGER) / p.name)
        items.append(fm)
    return items, bad


def probe(item: dict[str, str], root: Path) -> str:
    """`detect` を走らせる。**0 = 要る / 1 = 済んでいる / それ以外 = 判定できなかった。**

    判定できなかったものは `判定不能` として**要る側に並べる** — 「済んだ」と言う方が高くつく
    (移行が要るのに誰も気づかないまま作業が続く)。理由は `_note` に載せて必ず出す。
    """
    try:
        r = subprocess.run(item["detect"], shell=True, cwd=root, capture_output=True,
                           text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        item["_note"] = f"detect が {TIMEOUT} 秒で打ち切られた"
        return UNKNOWN
    except OSError as e:                                    # シェルが起こせない
        item["_note"] = f"detect を実行できなかった: {e}"
        return UNKNOWN
    if r.returncode == 0:
        return NEEDED
    if r.returncode == 1:
        return DONE
    first = (r.stderr or r.stdout).strip().splitlines()
    item["_note"] = (f"detect が {r.returncode} を返した"
                     + (f": {first[0][:120]}" if first else "(出力なし)"))
    return UNKNOWN


def busy(item: dict[str, str], root: Path) -> list[str]:
    """`paths` に未コミットの差分が在るかを見る。**在れば当てさせない。**

    git の外(まだ `git init` していないプロジェクト)では見られないので、その旨を残して
    通す — **在るかどうか判らないことを「在る」と言うと、移行が永久に当たらなくなる。**
    """
    paths = item["paths"].split()
    if not paths:
        return []
    r = subprocess.run(["git", "status", "--porcelain", "--"] + paths,
                       cwd=root, capture_output=True, text=True)
    if r.returncode != 0:
        item["_note"] = ((item.get("_note", "") + " / ") if item.get("_note") else "") \
            + "git で差分を見られなかった(このまま当てる前に自分で確かめよ)"
        return []
    return [ln[3:] for ln in r.stdout.splitlines() if ln.strip()]


def report(root: Path) -> tuple[list[dict[str, str]], list[str]]:
    items, bad = load(root)
    for it in items:
        it["_state"] = probe(it, root)
        if it["_state"] in (NEEDED, UNKNOWN):
            dirty = busy(it, root)
            if dirty:
                it["_dirty"] = " ".join(dirty[:6])
                it["_state"] = BUSY
    return items, bad


def main() -> int:
    ap = argparse.ArgumentParser(
        description="キットの版を上げた後に要る移行を台帳から数え上げる",
        epilog="終了コード: 0=問題なし / 1=要る移行が在る(check のみ)/ 2=台帳の不備",
    )
    ap.add_argument("cmd", nargs="?", default="list", choices=["list", "check"])
    ap.add_argument("--root", default=".", help="プロジェクトのルート(既定: いまの場所)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    root = Path(a.root).resolve()
    items, bad = report(root)

    if bad:
        print("## 移行の台帳に不備がある(判定できない)")
        for b in bad:
            print(f"  NG  {b}")
        print(f"  → 正は .claude/skills/kit-migrate/SKILL.md。{LEDGER}/ を直す")
        return 2

    need = [it for it in items if it["_state"] != DONE]
    if a.cmd == "check":
        print(f"移行: 要る {len(need)} 件 / 全 {len(items)} 件")
        for it in need:
            print(f"  {it['_state']}  {it['id']}({it['kind']}, since {it['since']})"
                  f"— {it['summary']}")
            if it.get("_note"):
                print(f"        ★ {it['_note']}")
            if it.get("_dirty"):
                print(f"        ★ 未コミットの差分: {it['_dirty']} — **当てない**")
        return 1 if need else 0

    if not items:
        print(f"移行の台帳が空である({LEDGER}/ に項目が無い)")
        return 0
    print(f"## 移行の台帳({len(items)} 件。要る {len(need)} 件)")
    for it in items:
        print(f"  [{it['_state']}] {it['id']}  {it['kind']}  since {it['since']}")
        print(f"         {it['summary']}")
        if it.get("_note"):
            print(f"         ★ {it['_note']}(要る側に寄せた)")
        if it.get("_dirty"):
            print(f"         ★ 未コミットの差分: {it['_dirty']}")
            print("           **当てない。** 誰かがそこを書いている(SKILL.md §3)")
        if it["_state"] != DONE:
            print(f"         手順: {it['_path']}")
    return 0


# ---------------------------------------------------------------- 自己検査


def selftest() -> int:
    results: list[tuple[str, bool, str]] = []

    def ck(name: str, cond: bool, note: str = "") -> None:
        results.append((name, cond, note))

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        d = root / LEDGER
        d.mkdir(parents=True)

        def item(name: str, **kw: str) -> None:
            fm = {"id": name, "since": "2026-08-25", "kind": "mechanical",
                  "detect": "true", "paths": "docs/x.md", "summary": "要約"}
            fm.update(kw)
            body = "".join(f"{k}: {v}\n" for k, v in fm.items() if not k.startswith("_"))
            (d / f"{name}.md").write_text(f"---\n{body}---\n\n本文\n", encoding="utf-8")

        def run_cmd(*args: str) -> tuple[int, str]:
            r = subprocess.run([sys.executable, str(Path(__file__).resolve()), *args,
                                "--root", str(root)], capture_output=True, text=True)
            return r.returncode, r.stdout + r.stderr

        # (a) detect の終了コード 0 = まだ移行が要る。非ゼロ = 済んでいる
        item("a-needed", detect="true")
        item("b-done", detect="false")
        rc, out = run_cmd("list")
        ck("(a) list は 0 を返す", rc == 0, out)
        ck("(a) 要るものを要ると言う", "[要る] a-needed" in out, out)
        ck("(a) 済んだものを不要と言う", "[不要] b-done" in out, out)
        ck("(a) 要るものだけ手順のパスを出す",
           out.count("手順: ") == 1 and "a-needed.md" in out, out)
        rc, out = run_cmd("check")
        ck("(a) check は要るものが在れば 1", rc == 1, out)
        ck("(a) check は件数を出す", "要る 1 件 / 全 2 件" in out, out)

        # (a') detect が 1 以外の非ゼロを返したら「判定不能」で、**要る側に並ぶ**
        item("a2-broken", detect="no-such-command-xyz")
        rc, out = run_cmd("check")
        ck("(a') 判定できなければ 1(要る側)", rc == 1, out)
        ck("(a') 判定不能と言う", "判定不能  a2-broken" in out, out)
        ck("(a') 返ってきた終了コードを出す", "127" in out, out)
        item("a3-syntax", detect="if [")
        rc, out = run_cmd("check")
        ck("(a'') 構文エラーも判定不能", "判定不能  a3-syntax" in out, out)
        (d / "a2-broken.md").unlink()
        (d / "a3-syntax.md").unlink()

        # (b) 要るものが無ければ check は 0(**無い状態が正常である**)
        (d / "a-needed.md").unlink()
        rc, out = run_cmd("check")
        ck("(b) 要るものが無ければ 0", rc == 0, out)

        # (c) detect はプロジェクトのルートで走る(相対パスがそのまま書ける)
        (root / "marker").write_text("x", encoding="utf-8")
        item("c-cwd", detect="test -f marker")
        rc, out = run_cmd("check")
        ck("(c) detect の cwd はルートである", rc == 1 and "c-cwd" in out, out)
        (d / "c-cwd.md").unlink()

        # (d) 台帳の不備は 3。**黙って飛ばさない**
        (d / "d-broken.md").write_text("---\nid: d-broken\n---\n", encoding="utf-8")
        rc, out = run_cmd("list")
        ck("(d) 欠けた欄があれば 2", rc == 2, out)
        ck("(d) 何が無いかを名指しする", "since" in out and "detect" in out, out)
        (d / "d-broken.md").unlink()

        item("e-mismatch", id="別の名前")
        rc, out = run_cmd("list")
        ck("(e) id とファイル名の食い違いは 2", rc == 2, out)
        (d / "e-mismatch.md").unlink()

        item("f-kind", kind="mechanica")
        rc, out = run_cmd("list")
        ck("(f) kind の綴り違いは 2", rc == 2, out)
        (d / "f-kind.md").unlink()

        item("g-since", since="2026/08/25")
        rc, out = run_cmd("list")
        ck("(g) since の書式違いは 2", rc == 2, out)
        (d / "g-since.md").unlink()

        # (k) paths に未コミットの差分が在れば「書きかけ」で、当てさせない
        subprocess.run(["git", "init", "-q"], cwd=root, capture_output=True)
        subprocess.run(["git", "-c", "user.email=t@e", "-c", "user.name=t",
                        "commit", "-qm", "base", "--allow-empty"], cwd=root,
                       capture_output=True)
        (root / "docs").mkdir(exist_ok=True)
        (root / "docs" / "x.md").write_text("書きかけ\n", encoding="utf-8")
        item("k-busy", detect="true", paths="docs/x.md")
        rc, out = run_cmd("list")
        ck("(k) 未コミットの差分が在れば書きかけ", "[書きかけ] k-busy" in out, out)
        ck("(k) 当てるなと言う", "当てない" in out, out)
        rc, out = run_cmd("check")
        ck("(k) check は書きかけも要る側に数える", rc == 1 and "書きかけ" in out, out)
        (d / "k-busy.md").unlink()
        (root / "docs" / "x.md").unlink()

        # (h) 値の中のコロンを落とさない(detect はシェルなので普通に混ざる)
        fm = frontmatter("---\nid: x\ndetect: test -f a && echo y: z\n---\n")
        ck("(h) 最初のコロンだけで割る", fm.get("detect") == "test -f a && echo y: z", str(fm))

        # (i) README.md は項目ではない(案内を移行と数えない)
        (d / "README.md").write_text("案内である\n", encoding="utf-8")
        rc, out = run_cmd("list")
        ck("(i) README.md を項目に数えない", rc == 0 and "README" not in out, out)

        # (j) 台帳が空・無いのは異常ではない
        for p in d.glob("*.md"):
            p.unlink()
        rc, out = run_cmd("list")
        ck("(j) 空の台帳は 0", rc == 0 and "空である" in out, out)
        d.rmdir()
        rc, out = run_cmd("check")
        ck("(j) 台帳が無くても 0", rc == 0, out)

    for n, ok, _ in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {n}")
    ng = [(n, note) for n, ok, note in results if not ok]
    if ng:
        print(f"\n{len(ng)} 件 FAIL", file=sys.stderr)
        for n, note in ng:
            print(f"--- {n}\n{note}", file=sys.stderr)
        return 1
    print(f"\n全 {len(results)} 項目 PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
