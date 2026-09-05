#!/usr/bin/env python3
"""UX 文書(docs/ux/)の grep 級の実在検査。規範は .claude/directions/ux.md「機械検査」。

使い方:
    python3 .claude/scripts/check-ux.py [--root <repo>]
    python3 .claude/scripts/check-ux.py --selftest   # 壊した事例で各検査が落ちることを示す

見るのは3つ(対象は screens/ と flows.md だけ。reviews/ は歴史の記録なので対象外 —
古い条項・消えた画面への言及は誤りではない):

  UX1  条項参照 — 引いている条項 ID(FR-<domain>-nn-#)が 01-requirements/functional*.md の
       受け入れ基準の表に実在し、かつ 種別 が delete(退役)でないこと。
       条項 ID は不動でも行は delete 印付きで残るので(01-requirements.md)、
       「実在するか」だけでは退役を検出できない。
       functional*.md が1本も無いのに条項を参照しているのも違反である(実在を確かめられない
       参照を green にすると、移行途中の壊れた骨組みが仕上げ検査を通る)。参照が無ければ
       functional*.md の不在は違反ではない。
  UX2  画面ファイル — 3つの向き:
       (a) flows.md の「画面一覧」の見出しの下の表(台帳。他の節の表は台帳ではない —
           見出しが無ければ違反。コードブロックの中の `#` は見出しとして読まない)の行のうち、
           いずれかの欄がちょうど「未実装」の行を除いて、
           対応する screens/SCR-nn-*.md が実在する(印の行は対象外 — 画面ファイルは
           その画面を最初に実装する /build が作る。ux.md「場面1」。語を含むだけの文は
           印にならない)。
       (b) screens/ の各ファイルの SCR-nn が台帳に載っている。
       (c) flows.md の本文(操作の流れ・遷移図)に出る SCR-nn が台帳に載っている —
           台帳が唯一の定義場所である。ファイル名形(SCR-nn-<画面>.md)の言及も ID として拾う。
  UX3  指摘番号 — 「reviews/NN.md の指摘 <n>」の参照先(ファイルと指摘の行)が実在すること。
       指摘の行は reviews/NN.md の表の1列目(`| <n> |`)である。

違反は非0終了(ブロッキング)。走る時機は /build のタスク内整合確認(クロージャに docs/ux/
が入るとき)と、/verify-tests が qa 試験区分を走らせる前(周回末)。
docs/ux/ が無いプロジェクトでは何も見ずに 0 を返す(UI 無しは正当な状態)。
"""
import argparse
import re
import sys
from pathlib import Path

# ID の切り出しは \b を使わない — Unicode では日本語も word character なので、
# 「SCR-02へ進む」「FR-auth-01-1を実現する」のような日本語直結の ID に \b が成立しない。
# 前は英数・下線・ハイフン以外(行頭を含む)、後ろは数字・ハイフン以外(日本語直結を許す)。
CLAUSE_RE = re.compile(r'(?<![A-Za-z0-9_-])FR-[A-Za-z0-9-]*[A-Za-z][A-Za-z0-9-]*-\d+-\d+(?![0-9-])')
SCR_RE = re.compile(r'(?<![A-Za-z0-9_-])SCR-\d+(?![0-9-])')          # 台帳のセル用(厳密)
# 本文用 — 直後のハイフンを許す(「screens/SCR-99-幽霊.md」のようなファイル名形の言及も
# ID として拾う。厳密な形だけだと、消えた画面へのファイル名参照が誰にも拾われない)
SCR_BODY_RE = re.compile(r'(?<![A-Za-z0-9_-])SCR-\d+(?![0-9])')
SCR_FILE_RE = re.compile(r'^(SCR-\d+)-.+\.md$')   # screens/ のファイル名(SCR-nn-<画面>.md)
LEDGER_HEADING_RE = re.compile(r'^#{1,6}\s*画面一覧\s*$')   # 完全一致 — 「画面一覧と…」のような別見出しに当てない
# 参照の書式の正は ux.md「状態と経緯を分ける」— 「reviews/NN.md の指摘 <n>」
REVIEW_REF_RE = re.compile(r'reviews/(\d+)\.md\s*の指摘\s*(\d+)')


def load_clauses(repo: Path) -> tuple[dict[str, bool], bool]:
    """functional*.md の受け入れ基準の表から {条項ID: 退役か} を集める。

    表の行は `| FR-x-nn-# | 種別 | 基準 |`(01-functional.md の雛形)。1列目が条項 ID、
    2列目が 種別 で、退役は 種別 = delete である。2つ目の返り値は functional*.md が
    1本でも在ったか。
    """
    clauses: dict[str, bool] = {}
    found = False
    for p in sorted((repo / "docs/01-requirements").glob("functional*.md")):
        found = True
        for line in p.read_text(errors="replace").splitlines():
            if not line.lstrip().startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and CLAUSE_RE.fullmatch(cells[0].strip("`")):
                cid = cells[0].strip("`")
                clauses[cid] = (cells[1].strip("`") == "delete")
    return clauses, found


def ledger_rows(flows_text: str) -> tuple[dict[str, bool], bool]:
    """flows.md の「画面一覧」の節の表から台帳 {SCR-nn: 未実装か} を集める。

    台帳はその節の、1列目のセルが SCR-nn の表の行だけである — 他の節の表(遷移を表で
    書いたプロジェクトなど)は台帳ではないので読まない(読むと、印の付いた行が後の表の
    同じ SCR の行に上書きされうる)。「未実装」の印は、いずれかの欄がちょうど「未実装」で
    あること(ux.md「場面1」— 目的の欄が典型。語を含むだけの文は印にならない)。
    2つ目の返り値は「画面一覧」の見出しが在ったか。

    フェンス(``` と ~~~。開いた印と同じ印でだけ閉じる)の中と、4スペース以上字下げした
    `#` の行は、見出しとして読まない — **見出しに見える行で節が閉じ、その後ろの実在する
    台帳の行が丸ごと落ちるのを止めるためである**(それが起きると「台帳に書いてあるのに
    台帳に無い」という、原因の逆を指す違反になる)。**表の行には字下げの判定を掛けない**
    (箇条書きの下の台帳はコードブロックではない)。
    なお UX2(c) の本文走査はフェンスの中も見る — 遷移図(mermaid)の `SCR-nn` を拾うためで
    あり、**フェンスに入れれば台帳の外の ID を書けるようにはならない。**
    """
    rows: dict[str, bool] = {}
    in_section = False
    heading_found = False
    fence = ""                           # 開いているフェンスの印(``` か ~~~)。閉じるのは同じ印だけ
    for line in flows_text.splitlines():
        stripped = line.lstrip()
        mark = next((m for m in ("```", "~~~") if stripped.startswith(m)), "")
        if mark:
            fence = "" if fence == mark else (fence or mark)
            continue
        if fence:
            continue                     # フェンスの中の # は見出しではない(節を閉じない)
        if stripped.startswith("#"):
            # **字下げを見るのは見出しの認識だけである。** 4スペース以上ならコードブロックの
            # 中の `#` なので節を閉じない。**表の行にこの判定を掛けてはならない** —
            # 箇条書きの下に置いた台帳は4スペース字下げでもコードブロックではなく、
            # 落とすと「台帳に書いてあるのに台帳に無い」という原因の逆を指す違反が出る。
            if len(line) - len(stripped) >= 4:
                continue
            in_section = bool(LEDGER_HEADING_RE.match(line.strip()))
            heading_found = heading_found or in_section
            continue
        if not in_section or not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and SCR_RE.fullmatch(cells[0].strip("`")):
            rows.setdefault(cells[0].strip("`"),
                            any(c.strip("`") == "未実装" for c in cells))
    return rows, heading_found


def main_check(repo: Path, quiet: bool = False) -> int:
    """検査の本体。違反が1件でも在れば 1、無ければ 0(`quiet` は自己検査のための静音)。"""
    ux = repo / "docs/ux"
    if not ux.is_dir():
        if not quiet:
            print("check-ux: docs/ux/ が無い — 対象なし(UI 無しは正当な状態)")
        return 0

    flows = ux / "flows.md"
    screens_dir = ux / "screens"
    targets = [p for p in ([flows] if flows.is_file() else [])
               + sorted(screens_dir.glob("*.md") if screens_dir.is_dir() else [])]

    violations: list[str] = []

    # UX1 — 条項参照の実在と未退役
    clauses, functional_found = load_clauses(repo)
    for p in targets:
        for i, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
            for cid in CLAUSE_RE.findall(line):
                if not functional_found:
                    violations.append(
                        f"UX1 {p.relative_to(repo)}:{i} 条項 {cid} を参照しているが "
                        f"01-requirements/functional*.md が無い(実在を確かめられない)")
                elif cid not in clauses:
                    violations.append(
                        f"UX1 {p.relative_to(repo)}:{i} 条項 {cid} が functional*.md に実在しない")
                elif clauses[cid]:
                    violations.append(
                        f"UX1 {p.relative_to(repo)}:{i} 条項 {cid} は退役済み(種別 delete)")

    # UX2 — 台帳(flows.md の表)⇄ screens/ ⇄ 本文の3つの向き
    ledger: dict[str, bool] = {}
    if flows.is_file():
        text = flows.read_text(errors="replace")
        ledger, heading_found = ledger_rows(text)
        if not heading_found:
            violations.append(f"UX2 {flows.relative_to(repo)} に「画面一覧」の見出しが無い"
                              f"(台帳はその節の表である — ux.md「ファイル構成」)")
        # (a) 台帳の行(未実装の印なし)→ 画面ファイルが実在
        for sid, unimplemented in sorted(ledger.items()):
            if unimplemented:
                continue
            if screens_dir.is_dir() and list(screens_dir.glob(f"{sid}-*.md")):
                continue
            violations.append(f"UX2 {flows.relative_to(repo)} の台帳の {sid} に対応する "
                              f"docs/ux/screens/{sid}-*.md が無い(未実装なら、いずれかの欄にちょうど「未実装」とだけ書く)")
        # (c) 本文に出る SCR-nn → 台帳に載っている(ファイル名形の言及も拾う)
        for i, line in enumerate(text.splitlines(), 1):
            for sid in SCR_BODY_RE.findall(line):
                if sid not in ledger:
                    violations.append(f"UX2 {flows.relative_to(repo)}:{i} 本文の {sid} が "
                                      f"画面一覧(台帳の表)に無い — 台帳が唯一の定義場所である")
                    break   # 同じ行の重複報告を避ける
    # (b) screens/ の各ファイル → 台帳に載っている
    if screens_dir.is_dir():
        for p in sorted(screens_dir.glob("*.md")):
            m = SCR_FILE_RE.match(p.name)
            if not m:
                violations.append(f"UX2 {p.relative_to(repo)} のファイル名が SCR-nn-<画面>.md の形でない")
            elif m.group(1) not in ledger:
                violations.append(f"UX2 {p.relative_to(repo)} の {m.group(1)} が "
                                  f"docs/ux/flows.md の画面一覧(台帳の表)に無い")

    # UX3 — 「reviews/NN.md の指摘 <n>」の参照先の実在
    for p in targets:
        for i, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
            for nn, num in REVIEW_REF_RE.findall(line):
                rev = ux / "reviews" / f"{nn}.md"
                if not rev.is_file():
                    violations.append(f"UX3 {p.relative_to(repo)}:{i} 参照先 docs/ux/reviews/{nn}.md が無い")
                    continue
                row = re.compile(rf'^\s*\|\s*{int(num)}\s*\|')
                if not any(row.match(l) for l in rev.read_text(errors="replace").splitlines()):
                    violations.append(f"UX3 {p.relative_to(repo)}:{i} "
                                      f"docs/ux/reviews/{nn}.md に指摘 {num} の行が無い")

    if not quiet:
        for v in violations:
            print(v)
        print(f"check-ux: 違反 {len(violations)} 件"
              f"(対象 {len(targets)} ファイル。reviews/ は対象外 — ux.md)")
    return 1 if violations else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="UX 文書の実在検査(規範: .claude/directions/ux.md)")
    ap.add_argument("--root", default=".", help="リポジトリの根(既定: カレント)")
    ap.add_argument("--selftest", action="store_true",
                    help="壊した事例で各検査が落ちることを示す(/kit-improve §6-3)")
    args = ap.parse_args()
    return selftest() if args.selftest else main_check(Path(args.root))



def selftest() -> int:
    """壊した事例で各検査が実際に落ちることを示す(`/kit-improve` §6-3)。

    **雛形は実物を読む** — 配っている `ux-flows.md` の台帳の形を変えたのに、この検査が
    追随していない、をここで捕まえる。解析(`ledger_rows`)がこの検査でいちばん壊れやすい
    ところなので、事例はその境界に寄せてある。
    """
    import tempfile

    kit = Path(__file__).resolve().parent.parent          # .claude/
    tpl = kit / "templates" / "ux-flows.md"
    if not tpl.is_file():
        print(f"エラー: 雛形が無い: {tpl}")
        return 2
    if not any(LEDGER_HEADING_RE.match(l.strip())
               for l in tpl.read_text(encoding="utf-8").splitlines()):
        print(f"NG 雛形 {tpl.name} に「画面一覧」の見出しが無い(検査が台帳を読めない形になっている)")
        return 1

    LEDGER = ("## 画面一覧\n\n"
              "| 画面ID | 画面名 | 目的 | 関連 UC |\n|---|---|---|---|\n"
              "| SCR-01 | ログイン | <> | UC-01 |\n")
    CLAUSES = ("| 条項 ID | 種別 | 基準 |\n|---|---|---|\n"
               "| FR-auth-01-1 | 正常系 | WHEN x |\n| FR-auth-01-2 | delete | IF y |\n")

    def run(flows: str, screens: tuple[str, ...] = ("SCR-01-ログイン.md",),
            reviews: dict[str, str] | None = None, functional: str | None = CLAUSES) -> int:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "docs/ux/screens").mkdir(parents=True)
            (root / "docs/ux/reviews").mkdir(parents=True)
            (root / "docs/01-requirements").mkdir(parents=True)
            if functional is not None:
                (root / "docs/01-requirements/functional.md").write_text(functional, encoding="utf-8")
            (root / "docs/ux/flows.md").write_text(flows, encoding="utf-8")
            for name in screens:
                (root / "docs/ux/screens" / name).write_text("# 画面\n", encoding="utf-8")
            for name, body in (reviews or {}).items():
                (root / "docs/ux/reviews" / name).write_text(body, encoding="utf-8")
            return main_check(root, quiet=True)

    cases: list[tuple[str, int]] = [
        # (a) 素の正常形は通る
        ("正常形", run(LEDGER + "\n## 操作の流れ\n\nSCR-01 を通る(FR-auth-01-1)。\n")),
        # UX1 — 実在しない条項 / 退役した条項 / 台帳が無いのに参照している
        ("UX1 実在しない条項", run(LEDGER + "\n## 操作の流れ\n\nFR-auth-99-9 を実現する。\n")),
        ("UX1 退役した条項", run(LEDGER + "\n## 操作の流れ\n\nFR-auth-01-2 を実現する。\n")),
        ("UX1 条項の台帳が無い",
         run(LEDGER + "\n## 操作の流れ\n\nFR-auth-01-1 を実現する。\n", functional=None)),
        # UX2 — 画面ファイルが無い / 台帳に無い画面ファイル / 本文の ID が台帳に無い / 見出しが無い
        ("UX2 画面ファイルが無い", run(LEDGER, screens=())),
        ("UX2 台帳に無い画面ファイル",
         run(LEDGER, screens=("SCR-01-ログイン.md", "SCR-09-余計.md"))),
        ("UX2 本文の ID が台帳に無い",
         run(LEDGER + "\n## 操作の流れ\n\nSCR-09 へ迷い込む。\n")),
        ("UX2 見出しが無い", run(LEDGER.replace("## 画面一覧\n", "画面一覧\n"))),
        # UX3 — 参照先のファイルが無い / 指摘の行が無い
        ("UX3 参照先のファイルが無い",
         run(LEDGER + "\n配置は reviews/03.md の指摘 7 を参照。\n")),
        ("UX3 指摘の行が無い",
         run(LEDGER + "\n配置は reviews/00.md の指摘 7 を参照。\n",
             reviews={"00.md": "| # | 指摘 |\n|---|---|\n| 1 | 初期判断 |\n"})),
    ]
    # 解析の境界 — ここが壊れると、実在する台帳の行が黙って落ちる
    FENCED = ("## 画面一覧\n\n~~~\n# 見出しに見える行\n~~~\n\n"
              "    # 字下げした見出しらしき行\n\n"
              "| 画面ID | 画面名 |\n|---|---|\n| SCR-01 | ログイン |\n")
    INDENTED_LEDGER = ("## 画面一覧\n\n- 補足: 画面は次のとおり。\n\n"
                       "    | 画面ID | 画面名 |\n    |---|---|\n    | SCR-01 | ログイン |\n")
    OTHER_TABLE = (LEDGER + "\n## 画面遷移\n\n| 遷移元 | 遷移先 |\n|---|---|\n"
                   "| SCR-02 | SCR-01 |\n")
    cases += [
        ("解析 フェンス・字下げの中の見出しで節が閉じない", run(FENCED)),
        ("解析 箇条書きの下の台帳も読む", run(INDENTED_LEDGER)),
        # 別の節の表は台帳ではない → SCR-02 は台帳に無い本文の ID として鳴る
        ("解析 別の節の表を台帳と読まない", run(OTHER_TABLE)),
        # 印はちょうど「未実装」の欄だけ。語を含む文は印にならない
        ("印 ちょうど未実装なら画面ファイルは要らない",
         run("## 画面一覧\n\n| 画面ID | 目的 |\n|---|---|\n| SCR-01 | 未実装 |\n", screens=())),
        ("印 語を含むだけの文は印にならない",
         run("## 画面一覧\n\n| 画面ID | 目的 |\n|---|---|\n"
             "| SCR-01 | 未実装の一覧を出す画面 |\n", screens=())),
    ]
    expected = {"正常形": 0, "解析 フェンス・字下げの中の見出しで節が閉じない": 0,
                "解析 箇条書きの下の台帳も読む": 0,
                "印 ちょうど未実装なら画面ファイルは要らない": 0}
    bad = [name for name, rc in cases if rc != expected.get(name, 1)]
    if bad:
        print("NG 期待と違った事例: " + " / ".join(bad))
        return 1
    print(f"OK check-ux の自己検査({len(cases)} 事例: UX1/UX2/UX3 と解析の境界)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
