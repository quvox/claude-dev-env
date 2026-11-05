#!/usr/bin/env python3
"""UX 文書(docs/ux/)の grep 級の実在検査。規範は .claude/directions/ux.md「機械検査」。

使い方:
    python3 .claude/scripts/check-ux.py [--root <repo>]
    python3 .claude/scripts/check-ux.py --selftest   # 壊した事例で各検査が落ちることを示す

見るのは6つ(対象は screens/ と commands/ と flows.md だけ。reviews/ は歴史の記録なので
対象外 — 古い条項・消えた面への言及は誤りではない):

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
  UX4  達成条件の欄 — screens/ と commands/ の「達成条件」の節の表が在るなら、その各行が
       4つの欄(達成 ID / 何が達成されるか / 実現する条項 / 確かめる手段)を持ち、
       どれも空でないこと。山かっこだけの雛形のまま(`<...>`)の欄は空と同じに扱う。
       達成 ID は `SCR-nn-A#` / `CMD-nn-A#` の形で、その面の ID はそのファイル自身の
       面の ID と一致すること(別の面の番号を書いた行は、どこからも引けない)。
       **表が無いこと自体は違反ではない**(遡って書かせない裁定 — ux.md「達成条件」)。
       表を持たない画面は、違反ではなく注記として件数と ID を印字する(終了コードは変えない)。
  UX5  見え方の基準 — screens/ の `- 見え方の基準:` の行が在るなら、そこが指す画像ファイルが
       実在すること。`未取得` は正当な値。山かっこだけの雛形のままは未記入として違反。
       **行そのものが無いことは違反ではない**(UX4 と同じ — 注記で見えるようにする)。
       commands/ は対象外(コマンドの面は見え方の基準を持たない — ux.md)。
  UX6  コマンドファイル — UX2 のコマンド版。(a) コマンド一覧の台帳の行(未実装の印なし)に
       対応する commands/CMD-nn-*.md が実在する、(b) commands/ の各ファイルの CMD-nn が
       台帳に載っている、(c) flows.md の本文に出る CMD-nn が台帳に載っている。
       **見出しを求めるのは、その種の面を持つプロジェクトだけである** — 画面一覧は
       screens/ が在るか本文に SCR-nn が出るとき、コマンド一覧は commands/ が在るか
       本文に CMD-nn が出るときにだけ、見出しの不在を違反にする。

違反は非0終了(ブロッキング)。走る時機は /build のタスク内整合確認(クロージャに docs/ux/
が入るとき)と、/verify-tests が qa 試験区分を走らせる前(周回末)。
docs/ux/ が無いプロジェクトでは何も見ずに 0 を返す — **操作面を持たない成果物では正当な状態で
あり、持っているのにまだ書いていないプロジェクトでは「これから埋める」状態である**
(どちらかはこの検査には判らない。判るのは 02 の「操作面の宣言」である — directions/ux.md)。
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
CMD_RE = re.compile(r'(?<![A-Za-z0-9_-])CMD-\d+(?![0-9-])')          # 台帳のセル用(厳密)
CMD_BODY_RE = re.compile(r'(?<![A-Za-z0-9_-])CMD-\d+(?![0-9])')      # 本文用(ファイル名形も拾う)
CMD_FILE_RE = re.compile(r'^(CMD-\d+)-.+\.md$')   # commands/ のファイル名(CMD-nn-<コマンド>.md)
LEDGER_HEADING_RE = re.compile(r'^#{1,6}\s*画面一覧\s*$')   # 完全一致 — 「画面一覧と…」のような別見出しに当てない
CMD_LEDGER_HEADING_RE = re.compile(r'^#{1,6}\s*コマンド一覧\s*$')   # 同上(コマンドの台帳)
# 参照の書式の正は ux.md「状態と経緯を分ける」— 「reviews/NN.md の指摘 <n>」
REVIEW_REF_RE = re.compile(r'reviews/(\d+)\.md\s*の指摘\s*(\d+)')
ACH_HEADING_RE = re.compile(r'^#{1,6}\s*達成条件\s*$')    # 完全一致 — 下の NEAR が「惜しい見出し」を拾う
# 「達成条件」で始まるが完全一致でない見出し。**素通りさせず違反にする** — 補足を付けた見出し
# (「## 達成条件(この画面)」)は節として読まれず、表ごと検査されないうえ「まだ書かれていない」と
# 誤って注記される(空欄と不在を区別する、というこの層の流儀の逆が出る)
ACH_HEADING_NEAR_RE = re.compile(r'^#{1,6}\s*達成条件.*$')
ACH_ID_RE = re.compile(r'^((?:SCR|CMD)-\d+)-A\d+$')       # 達成 ID(ux.md「達成条件」)
BASELINE_LINE_RE = re.compile(r'^\s*[-*]\s*見え方の基準\s*[:：]\s*(.*)$')   # ux.md「見え方の基準」
# 行から画像のパスを拾う — 山かっこ・空白・バッククォート・読点を含まない、画像の拡張子で終わるもの
IMG_PATH_RE = re.compile(r'(?<![\w/.-])([\w./-]+\.(?:png|jpg|jpeg|webp|gif))(?![\w.])', re.I)
SEP_CELL_RE = re.compile(r'^:?-{3,}:?$')                   # 表の区切り行のセル


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


def ledger_rows(flows_text: str, heading_re: re.Pattern = LEDGER_HEADING_RE,
                id_re: re.Pattern = SCR_RE) -> tuple[dict[str, bool], bool]:
    """flows.md の台帳の節の表から {面の ID: 未実装か} を集める(既定は「画面一覧」)。

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
    table_rows, heading_found = section_table_rows(flows_text, heading_re)
    for _, cells in table_rows:
        if cells and id_re.fullmatch(cells[0].strip("`")):
            rows.setdefault(cells[0].strip("`"),
                            any(c.strip("`") == "未実装" for c in cells))
    return rows, heading_found


def section_table_rows(text: str, heading_re: re.Pattern) -> tuple[list[tuple[int, list[str]]], bool]:
    """見出しが `heading_re` に一致する節の中の表の行を (行番号, セルの並び) で返す。

    **この解析の規則は、この関数ひとつが持つ**(台帳も達成条件も同じ規則で読む)。
    フェンス(``` と ~~~。開いた印と同じ印でだけ閉じる)の中と、4スペース以上字下げした
    `#` の行は、見出しとして読まない — **見出しに見える行で節が閉じ、その後ろの実在する
    行が丸ごと落ちるのを止めるためである**(それが起きると「書いてあるのに無い」という、
    原因の逆を指す違反になる)。**表の行には字下げの判定を掛けない**(箇条書きの下に置いた
    表はコードブロックではない)。2つ目の返り値は、その見出しが1度でも在ったか。
    """
    out: list[tuple[int, list[str]]] = []
    in_section = False
    heading_found = False
    fence = ""                           # 開いているフェンスの印(``` か ~~~)。閉じるのは同じ印だけ
    in_comment = False                   # <!-- --> の中(雛形は書き方をすべてここで渡す)
    for i, line in enumerate(text.splitlines(), 1):
        # **HTML コメントの中は読まない** ★ — 配っている雛形は「書き方」も「例」も
        # <!-- --> で渡す流儀なので、例に表の行を1つ書いた瞬間に実データとして読まれ、
        # 正しく書かれたファイルが落ちる(実測)。開始と終了が同じ行に在る形も外す。
        probe = re.sub(r'<!--.*?-->', '', line)
        if in_comment:
            if "-->" not in probe:
                continue
            probe = probe.split("-->", 1)[1]
            in_comment = False
        if "<!--" in probe:
            probe = probe.split("<!--", 1)[0]
            in_comment = True
        line = probe
        stripped = line.lstrip()
        if not stripped:
            continue
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
            in_section = bool(heading_re.match(line.strip()))
            heading_found = heading_found or in_section
            continue
        if not in_section or not stripped.startswith("|"):
            continue
        out.append((i, split_cells(line)))
    return out, heading_found


def split_cells(line: str) -> list[str]:
    """表の1行をセルに割る。**`\\|`(エスケープしたパイプ)は区切りではない。**

    markdown では、セルの中にパイプ文字を書くときは `\\|` と書く(`a \\| b`)。素朴に
    `split("|")` すると欄が1つ多く数えられ、**正しく書かれた行が「欄が5個である」で落ちる**
    (実測 — `commands/` の達成条件はパイプの表記を含みやすい)。
    """
    SENT = "\x00"                       # 本文に現れない印へ退避してから割る
    cells = line.strip().strip("|").replace("\\|", SENT).split("|")
    return [c.replace(SENT, "|").strip() for c in cells]


def main_check(repo: Path, quiet: bool = False) -> int:
    """検査の本体。違反が1件でも在れば 1、無ければ 0(`quiet` は自己検査のための静音)。"""
    ux = repo / "docs/ux"
    if not ux.is_dir():
        if not quiet:
            print("check-ux: docs/ux/ が無い — 対象なし"
              "(操作面を持たない成果物では正当。持っているなら、次にその面を触る /build が作る)")
        return 0

    flows = ux / "flows.md"
    screens_dir = ux / "screens"
    commands_dir = ux / "commands"
    # 操作面の2種(ux.md「ファイル構成」)。UX2 は画面、UX6 はコマンドで、見る向きは同じ3つである
    surfaces = [
        ("UX2", "画面一覧", screens_dir, "screens", SCR_FILE_RE, SCR_BODY_RE,
         LEDGER_HEADING_RE, SCR_RE, "SCR-nn-<画面>.md"),
        ("UX6", "コマンド一覧", commands_dir, "commands", CMD_FILE_RE, CMD_BODY_RE,
         CMD_LEDGER_HEADING_RE, CMD_RE, "CMD-nn-<コマンド>.md"),
    ]
    surface_files = sorted(
        [q for d in (screens_dir, commands_dir) if d.is_dir() for q in d.glob("*.md")])
    targets = ([flows] if flows.is_file() else []) + surface_files

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

    # UX2 / UX6 — 台帳(flows.md の表)⇄ 面のファイル ⇄ 本文の3つの向き
    # **見出しを求めるのは、その種の面を持つプロジェクトだけである** — 画面しか持たない製品の
    # flows.md に「コマンド一覧」は要らず、その逆も同じ(ux.md「機械検査」の UX2 (a) / UX6)。
    flows_text = flows.read_text(errors="replace") if flows.is_file() else ""
    for code, label, sdir, sub, file_re, body_re, head_re, id_re, name_form in surfaces:
        files = sorted(sdir.glob("*.md")) if sdir.is_dir() else []
        ledger, heading_found = ledger_rows(flows_text, head_re, id_re)
        body_ids = {m for line in flows_text.splitlines() for m in body_re.findall(line)}
        if not (files or body_ids or ledger):
            continue                     # その種の面を持たないプロジェクト
        if flows.is_file() and not heading_found:
            violations.append(f"{code} {flows.relative_to(repo)} に「{label}」の見出しが無い"
                              f"(台帳はその節の表である — ux.md「ファイル構成」)")
        elif heading_found and not ledger:
            # **見出しは在るのに ID の行が1つも無い** — 1列目が面の ID でない表(サブコマンド名を
            # 1列目にした等)を書くと、台帳が空のまま全部の向きが素通りする。
            kind = "SCR" if code == "UX2" else "CMD"
            violations.append(f"{code} {flows.relative_to(repo)} の「{label}」に面の ID の行が無い"
                              f"(1列目が {kind}-nn のセルだけを台帳として読む — "
                              f"台帳が唯一の定義場所である。ux.md「ファイル構成」)")
        # (a) 台帳の行(未実装の印なし)→ 面のファイルが実在
        for sid, unimplemented in sorted(ledger.items()):
            if unimplemented:
                continue
            if sdir.is_dir() and list(sdir.glob(f"{sid}-*.md")):
                continue
            violations.append(f"{code} {flows.relative_to(repo)} の台帳の {sid} に対応する "
                              f"docs/ux/{sub}/{sid}-*.md が無い"
                              f"(未実装なら、いずれかの欄にちょうど「未実装」とだけ書く)")
        # (c) 本文に出る面の ID → 台帳に載っている(ファイル名形の言及も拾う)
        for i, line in enumerate(flows_text.splitlines(), 1):
            for sid in body_re.findall(line):
                if sid not in ledger:
                    violations.append(f"{code} {flows.relative_to(repo)}:{i} 本文の {sid} が "
                                      f"{label}(台帳の表)に無い — 台帳が唯一の定義場所である")
                    break   # 同じ行の重複報告を避ける
        # (b) 面のファイル → 台帳に載っている
        for q in files:
            m = file_re.match(q.name)
            if not m:
                violations.append(f"{code} {q.relative_to(repo)} のファイル名が {name_form} の形でない")
            elif m.group(1) not in ledger:
                violations.append(f"{code} {q.relative_to(repo)} の {m.group(1)} が "
                                  f"docs/ux/flows.md の{label}(台帳の表)に無い")

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

    # UX7 — 「画面を使える手段(BR-13)」の水準が「未決」のまま残っていないか ★
    # (2026-09-15。inspection-28 A-22)
    # 基本要件 BR-13(キーボードだけで完了できる / 支援する道具に名前と状態が読める /
    # 色や大きさだけに頼らない)の**水準そのものは 01 の条項が持ち**、
    # docs/ux/policy.md はその条項 ID を指すだけである(directions/baseline.md §3.13)。
    # 雛形は「まだ決めていないなら『未決』と書く」と言っており、**それは正しい書き方**だが、
    # **未決のまま何周も進めることは意図されていない**(baseline.md: 決まるまで
    # 画面を作る・変えるタスクは BR-13 の該当を判定できない)。
    # 構築記録の検査は「条項を指したか」の形しか見ないので、指した先が「未決」でも通る。
    # **ここで止めないと、水準を1つも決めないまま画面の確認が形式上 green になる。**
    # **画面が1つも無いプロジェクトには掛けない** — BR-13 は画面を持つ製品の要件である。
    # **掛かるのは「画面を持つ製品」である。画面はファイルの有無だけでは決まらない** ★ —
    # コマンドしか持たない製品でも、**端末の対話画面**を持つならこの要件は効く
    # (`.claude/directions/ux.md`「policy.md は画面のためのもの」/ 雛形 ux-command.md の
    # 「対話画面を持つか」)。**その宣言を読まないと、コマンドだけの製品が素通りする。**
    has_screen = screens_dir.is_dir() and any(
        SCR_FILE_RE.match(q.name) for q in screens_dir.iterdir())
    if not has_screen and commands_dir.is_dir():
        dialog_re = re.compile(r'対話画面を持つか\s*[:：]\s*(.*?)\s*$')
        for q in sorted(commands_dir.iterdir()):
            if not CMD_FILE_RE.match(q.name):
                continue
            for line in q.read_text(errors="replace").splitlines():
                dm = dialog_re.match(line.strip().lstrip("-* "))
                if dm and dm.group(1).startswith("持つ"):
                    has_screen = True
                    break
            if has_screen:
                break
    if has_screen:
        policy = ux / "policy.md"
        if not policy.is_file():
            violations.append("UX7 docs/ux/policy.md が無い — 画面が在るのに基調が無い")
        else:
            level_re = re.compile(r'^\s*[-*]\s*水準を定める条項\s*[:：]\s*(.*?)\s*$')
            found = False
            for i, line in enumerate(policy.read_text(errors="replace").splitlines(), 1):
                lm = level_re.match(line)
                if not lm:
                    continue
                found = True
                value = lm.group(1).strip().strip("`")
                # 引用符・括弧で囲っただけの「未決」も未決である ★ —
                # 囲めば通るなら、この検査は綴りの遊びで抜けられる。
                # **全角と半角の両方を、外れなくなるまで繰り返し剥がす** —
                # 1回しか剥がさないと二重の囲み(「"未決"」)で抜け、
                # 一方の幅しか持たないと、もう一方の幅で抜ける。
                PAIRS = ('""', "''", "\uff02\uff02", "\uff07\uff07",
                         "\u300c\u300d", "\u300e\u300f",       # 「」『』
                         "()", "\uff08\uff09",                   # () ()
                         "[]", "\uff3b\uff3d",                   # [] []
                         "\u3008\u3009", "\u300a\u300b",       # 〈〉《》
                         "\u3010\u3011", "\u3014\u3015",       # 【】〔〕
                         "\uff62\uff63",                         # ｢｣
                         "\u201c\u201d", "\u2018\u2019")        # “” ‘’
                while True:
                    for pair in PAIRS:
                        if len(value) >= 2 and value[0] == pair[0] and value[-1] == pair[1]:
                            value = value[1:-1].strip()
                            break
                    else:
                        break
                if not value:
                    violations.append(
                        f"UX7 {policy.relative_to(repo)}:{i} 画面を使える手段(BR-13)の"
                        f"水準を定める条項が空欄である"
                        f"(まだ決めていないなら「未決」と書く — 空欄は「無い」と"
                        f"「書き忘れ」を区別しない)")
                elif value.startswith("<") and value.endswith(">"):
                    violations.append(
                        f"UX7 {policy.relative_to(repo)}:{i} 画面を使える手段(BR-13)の"
                        f"水準を定める条項が雛形のまま未記入である")
                elif value.startswith("未決"):
                    violations.append(
                        f"UX7 {policy.relative_to(repo)}:{i} 画面を使える手段(BR-13)の"
                        f"水準が「未決」のままである — 水準を 01 の受け入れ基準として決め、"
                        f"その条項 ID をここに書く(決まるまで画面のタスクは BR-13 の"
                        f"該当を判定できない。directions/baseline.md §3.13。"
                        f"この検査は 2026-09-15 に足した — 既に動いているプロジェクトの"
                        f"直し方は .claude/migrations/2026-09-15d-br13-level.md)")
            if not found:
                violations.append(
                    f"UX7 {policy.relative_to(repo)} に「水準を定める条項:」の行が無い — "
                    f"画面を使える手段(BR-13)の節は雛形が持っている")

    # UX4/UX5 — 達成条件の表と見え方の基準
    # (どちらも「在るなら中身を見る」。無いこと自体は違反にしない — ux.md「達成条件」の代金)
    # **UX4 は操作面の2種の両方に掛かり、UX5 は画面だけである** — コマンドの面は
    # 見え方の基準を持たない(出力の固定は保存済みの期待値が担う。ux.md「見え方の基準」)。
    notes: list[str] = []
    for q in surface_files:
        is_screen = q.parent.name == "screens"
        m = (SCR_FILE_RE if is_screen else CMD_FILE_RE).match(q.name)
        own = m.group(1) if m else None
        body = q.read_text(errors="replace")
        missing: list[str] = []

        if is_screen:
            # UX5 — 見え方の基準の行(在るなら、指す画像が実在すること)
            baseline_found = False
            for i, line in enumerate(body.splitlines(), 1):
                bm = BASELINE_LINE_RE.match(line)
                if not bm:
                    continue
                baseline_found = True
                value = bm.group(1).strip().strip("`")
                if value.startswith("<") and value.endswith(">"):
                    violations.append(
                        f"UX5 {q.relative_to(repo)}:{i} 見え方の基準が雛形のまま未記入である"
                        f"(画像のパスを書くか、撮っていないなら「未取得」と書く)")
                    continue
                paths = IMG_PATH_RE.findall(value)
                if not paths:
                    if value != "未取得":
                        violations.append(
                            f"UX5 {q.relative_to(repo)}:{i} 見え方の基準に画像のパスが無い"
                            f"(撮っていないなら「未取得」とだけ書く — 空欄と別の主張である)")
                    continue
                for rel in paths:
                    if not (repo / rel).is_file():
                        violations.append(
                            f"UX5 {q.relative_to(repo)}:{i} 見え方の基準 {rel} が実在しない")
            if not baseline_found:
                missing.append("見え方の基準")
        else:
            # コマンドの面は見え方の基準を持たない(ux.md「見え方の基準」)。
            # **書いても何も鳴らないと、同じことを2つの仕組みで持つ状態を検査が止められない。**
            for i, line in enumerate(body.splitlines(), 1):
                if BASELINE_LINE_RE.match(line):
                    violations.append(
                        f"UX5 {q.relative_to(repo)}:{i} コマンドの面は「見え方の基準」を持たない"
                        f"(出力の固定は保存済みの期待値(golden)が担う — ux.md「見え方の基準」)")

        # UX4 — 達成条件の表(画面もコマンドも同じ)
        rows, found = section_table_rows(body, ACH_HEADING_RE)
        if not found:
            # 「惜しい見出し」を黙って見逃さない(ux.md「機械検査」の UX4)
            near = [(i, l.strip()) for i, l in enumerate(body.splitlines(), 1)
                    if ACH_HEADING_NEAR_RE.match(l.strip())]
            for i, line in near:
                violations.append(
                    f"UX4 {q.relative_to(repo)}:{i} 見出し {line!r} は「達成条件」ちょうどでない"
                    f"(補足を付けると節として読まれず、表が検査されないまま通る)")
            if not near:
                missing.append("達成条件")
        if missing:
            notes.append(f"{own or q.name}({'・'.join(missing)})")
        if not found:
            continue
        data_rows = 0
        for i, cells in rows:
            head = cells[0].strip("`") if cells else ""
            if head in ("達成 ID", "達成ID"):
                continue                                  # 表の見出しの行
            if cells and all(SEP_CELL_RE.match(c) for c in cells if c):
                continue                                  # 区切りの行
            data_rows += 1
            if len(cells) != 4:
                violations.append(
                    f"UX4 {q.relative_to(repo)}:{i} 達成条件の行の欄が {len(cells)} 個である"
                    f"(4個 — 達成 ID / 何が達成されるか / 実現する条項 / 確かめる手段)")
                continue
            blank = [n for n, c in zip(("達成 ID", "何が達成されるか", "実現する条項", "確かめる手段"), cells)
                     if not c.strip("`") or (c.startswith("<") and c.endswith(">"))]
            if blank:
                violations.append(
                    f"UX4 {q.relative_to(repo)}:{i} 達成条件の欄が未記入である: {' / '.join(blank)}"
                    f"(該当が無いなら「上流に規定が無い」のように書く — 空欄と別の主張である)")
            aid = cells[0].strip("`")
            am = ACH_ID_RE.match(aid)
            if not am:
                violations.append(
                    f"UX4 {q.relative_to(repo)}:{i} 達成 ID {aid!r} が "
                    f"{'SCR' if is_screen else 'CMD'}-nn-A# の形でない")
            elif own and am.group(1) != own:
                violations.append(
                    f"UX4 {q.relative_to(repo)}:{i} 達成 ID {aid} の面の ID が"
                    f"このファイルの {own} と違う(どこからも引けない行になる)")
        if data_rows == 0:
            violations.append(
                f"UX4 {q.relative_to(repo)} に達成条件の節が在るのに行が1つも無い"
                f"(節ごと無いのは許すが、空の節は「決めていない」を隠す)")

    if not quiet:
        for v in violations:
            print(v)
        if notes:
            print(f"check-ux: 注記 — まだ書かれていない操作面 {len(notes)} 件: "
                  f"{', '.join(notes)}(違反ではない。触ったときに埋める — ux.md「達成条件」)")
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

    # UX7 の既定 — 画面が在る事例では、水準を決めた policy.md を置く(決めてある状態が
    # 正常形である)。UX7 そのものの事例は policy= を差し替えて作る。
    POLICY = "- 水準を定める条項: FR-auth-01-1\n- 適用しない範囲と理由: なし\n"

    def run(flows: str, screens: tuple[str, ...] = ("SCR-01-ログイン.md",),
            reviews: dict[str, str] | None = None, functional: str | None = CLAUSES,
            screen_body: str = "# 画面\n", images: tuple[str, ...] = (),
            commands: tuple[str, ...] = (), command_body: str = "# コマンド\n",
            policy: str | None = POLICY) -> int:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "docs/ux/screens").mkdir(parents=True)
            (root / "docs/ux/reviews").mkdir(parents=True)
            (root / "docs/01-requirements").mkdir(parents=True)
            if functional is not None:
                (root / "docs/01-requirements/functional.md").write_text(functional, encoding="utf-8")
            (root / "docs/ux/flows.md").write_text(flows, encoding="utf-8")
            if policy is not None:
                (root / "docs/ux/policy.md").write_text(policy, encoding="utf-8")
            for name in screens:
                (root / "docs/ux/screens" / name).write_text(screen_body, encoding="utf-8")
            if commands:
                (root / "docs/ux/commands").mkdir(parents=True, exist_ok=True)
                for name in commands:
                    (root / "docs/ux/commands" / name).write_text(command_body, encoding="utf-8")
            for rel in images:
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_bytes(b"\x89PNG\r\n")
            for name, body in (reviews or {}).items():
                (root / "docs/ux/reviews" / name).write_text(body, encoding="utf-8")
            return main_check(root, quiet=True)

    OK_FLOWS = LEDGER + "\n## 操作の流れ\n\nSCR-01 を通る(FR-auth-01-1)。\n"
    cases: list[tuple[str, int]] = [
        # UX7 — 画面を使える手段(BR-13)の水準(2026-09-15。inspection-28 A-22)
        ("UX7 水準が未決", run(OK_FLOWS, policy="- 水準を定める条項: 未決\n")),
        ("UX7 雛形のまま",
         run(OK_FLOWS, policy="- 水準を定める条項: <FR-<domain>-nn-#>\n")),
        ("UX7 行が無い", run(OK_FLOWS, policy="# デザインの基調\n")),
        ("UX7 policy.md が無い", run(OK_FLOWS, policy=None)),
        ("UX7 空欄", run(OK_FLOWS, policy="- 水準を定める条項:\n")),
        ("UX7 鉤括弧で囲った未決",
         run(OK_FLOWS, policy="- 水準を定める条項: 「未決」\n")),
        ("UX7 引用符で囲った未決",
         run(OK_FLOWS, policy='- 水準を定める条項: "未決"\n')),
        ("UX7 コマンドだけでも対話画面を持つなら掛かる",
         run("## コマンド一覧\n\n| コマンドID | コマンド | 目的 |\n|---|---|---|\n"
             "| CMD-01 | go | <> |\n", screens=(), policy="- 水準を定める条項: 未決\n",
             commands=("CMD-01-go.md",),
             command_body="# コマンド\n\n- 対話画面を持つか: 持つ\n")),
        ("UX7 決めてあれば通る", run(OK_FLOWS)),
        ("UX7 画面が無ければ掛からない",
         run("## コマンド一覧\n\n| コマンドID | コマンド | 目的 |\n|---|---|---|\n"
             "| CMD-01 | go | <> |\n", screens=(), policy=None,
             commands=("CMD-01-go.md",))),
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
    # UX4 — 達成条件の表。**雛形は実物を読む**(配っている ux-screen.md が節を持たなく
    # なったのに検査だけ残る、をここで捕まえる)
    stpl = kit / "templates" / "ux-screen.md"
    if not stpl.is_file():
        print(f"エラー: 雛形が無い: {stpl}")
        return 2
    if not any(ACH_HEADING_RE.match(l.strip())
               for l in stpl.read_text(encoding="utf-8").splitlines()):
        print(f"NG 雛形 {stpl.name} に「達成条件」の見出しが無い(検査が読む表が雛形に無い)")
        return 1

    ACH_HEAD = ("## 達成条件\n\n| 達成 ID | 何が達成されるか | 実現する条項 | 確かめる手段 |\n"
                "|---|---|---|---|\n")
    OK_ROW = "| SCR-01-A1 | 資格情報を入れると次の画面へ進む | FR-auth-01-1 | `login.spec.ts` |\n"
    cases += [
        ("UX4 表が無いのは違反ではない", run(LEDGER, screen_body="# 画面\n")),
        ("UX4 埋まっていれば通る", run(LEDGER, screen_body=ACH_HEAD + OK_ROW)),
        ("UX4 欄が空", run(LEDGER, screen_body=ACH_HEAD +
                          "| SCR-01-A1 | 次の画面へ進む | FR-auth-01-1 |  |\n")),
        ("UX4 欄が4つでない", run(LEDGER, screen_body=ACH_HEAD +
                                "| SCR-01-A1 | 次の画面へ進む | FR-auth-01-1 |\n")),
        ("UX4 雛形のまま", run(LEDGER, screen_body=ACH_HEAD +
                            "| SCR-01-A1 | <1文> | FR-auth-01-1 | `login.spec.ts` |\n")),
        ("UX4 別の画面の達成 ID", run(LEDGER, screen_body=ACH_HEAD +
                                  "| SCR-09-A1 | 次の画面へ進む | FR-auth-01-1 | `x.ts` |\n")),
        ("UX4 達成 ID の形が違う", run(LEDGER, screen_body=ACH_HEAD +
                                  "| A1 | 次の画面へ進む | FR-auth-01-1 | `x.ts` |\n")),
        ("UX4 節が在るのに行が無い", run(LEDGER, screen_body="## 達成条件\n\nまだ書いていない。\n")),
        # 節の外の表は達成条件ではない(見出しの完全一致と節の閉じ方を同時に見る)
        ("UX4 別の節の表を達成条件と読まない",
         run(LEDGER, screen_body=ACH_HEAD + OK_ROW +
             "\n## 項目\n\n| 項目 | 型 |\n|---|---|\n| メール | 文字列 |\n")),
    ]

    # UX5 — 見え方の基準。**雛形は実物を読む**(配っている ux-screen.md からこの行が
    # 消えたのに検査だけ残る、をここで捕まえる)
    if not any(BASELINE_LINE_RE.match(l) for l in stpl.read_text(encoding="utf-8").splitlines()):
        print(f"NG 雛形 {stpl.name} に「見え方の基準」の行が無い(検査が読む行が雛形に無い)")
        return 1

    BL = "tests/visual/baselines/SCR-01/初期.png"
    cases += [
        ("UX5 行が無いのは違反ではない", run(LEDGER, screen_body="# 画面\n")),
        ("UX5 未取得は違反ではない", run(LEDGER, screen_body="- 見え方の基準: 未取得\n")),
        ("UX5 実在する画像なら通る",
         run(LEDGER, screen_body=f"- 見え方の基準: {BL}\n", images=(BL,))),
        ("UX5 実在しない画像", run(LEDGER, screen_body=f"- 見え方の基準: {BL}\n")),
        ("UX5 雛形のまま",
         run(LEDGER, screen_body="- 見え方の基準: <…を列挙。まだ撮っていなければ 未取得>\n")),
        ("UX5 パスでも未取得でもない",
         run(LEDGER, screen_body="- 見え方の基準: あとで撮る\n")),
        ("UX5 2枚のうち片方が実在しない",
         run(LEDGER,
             screen_body=f"- 見え方の基準: {BL}, tests/visual/baselines/SCR-01/エラー.png\n",
             images=(BL,))),
    ]
    # UX6 — コマンドの面。**雛形は実物を読む**(配っている ux-flows.md からコマンド一覧が
    # 消えたのに検査だけ残る、をここで捕まえる)
    ftpl = tpl.read_text(encoding="utf-8")
    if not any(CMD_LEDGER_HEADING_RE.match(l.strip()) for l in ftpl.splitlines()):
        print(f"NG 雛形 {tpl.name} に「コマンド一覧」の見出しが無い(検査が台帳を読めない形)")
        return 1

    CMD_LEDGER = ("## コマンド一覧\n\n| コマンドID | サブコマンド | 目的 |\n|---|---|---|\n"
                  "| CMD-01 | `tool deploy` | 配る |\n")
    CMD_ACH = ("## 達成条件\n\n| 達成 ID | 何が達成されるか | 実現する条項 | 確かめる手段 |\n"
               "|---|---|---|---|\n"
               "| CMD-01-A1 | 設定が誤っていると理由が読める文で出る | 上流に規定が無い | `deploy.test.ts` |\n")
    cases += [
        # 画面しか無い製品に「コマンド一覧」の見出しは要らない(逆も同じ)
        ("UX6 コマンドを持たない製品は見出しを求められない", run(LEDGER)),
        ("UX6 画面を持たない製品は画面一覧を求められない",
         run(CMD_LEDGER, screens=(), commands=("CMD-01-deploy.md",))),
        ("UX6 コマンドファイルが無い", run(LEDGER + "\n" + CMD_LEDGER)),
        ("UX6 台帳に無いコマンドファイル",
         run(LEDGER + "\n" + CMD_LEDGER, commands=("CMD-01-deploy.md", "CMD-09-余計.md"))),
        ("UX6 本文の ID が台帳に無い",
         run(LEDGER + "\n" + CMD_LEDGER + "\n## 操作の流れ\n\nCMD-09 を打つ。\n",
             commands=("CMD-01-deploy.md",))),
        ("UX6 見出しが無い",
         run(LEDGER + "\n### 配るコマンド\n\n| コマンドID | 目的 |\n|---|---|\n| CMD-01 | 配る |\n",
             commands=("CMD-01-deploy.md",))),
        ("UX6 未実装の印ならファイルは要らない",
         run(LEDGER + "\n## コマンド一覧\n\n| コマンドID | 目的 |\n|---|---|\n| CMD-01 | 未実装 |\n")),
        # UX4 はコマンドの面にも掛かる
        ("UX4 コマンドの達成条件も見る",
         run(LEDGER + "\n" + CMD_LEDGER, commands=("CMD-01-deploy.md",),
             command_body=CMD_ACH)),
        ("UX4 コマンドに画面の達成 ID を書いた",
         run(LEDGER + "\n" + CMD_LEDGER, commands=("CMD-01-deploy.md",),
             command_body=CMD_ACH.replace("CMD-01-A1", "SCR-01-A1"))),
    ]
    # 2026-09-15 の独立レビューが挙げた解析の穴。**どれも「正しく書いた行が落ちる」か
    # 「壊れた行が通る」かのどちらかだった** — 事例で固定する
    cases += [
        ("解析 セルの中のエスケープしたパイプは区切りではない",
         run(LEDGER, screen_body=ACH_HEAD +
             "| SCR-01-A1 | 出力を `a \\| b` へ渡せる | FR-auth-01-1 | `x.ts` |\n")),
        ("解析 HTML コメントの中の表の行を読まない",
         run(LEDGER, screen_body="## 達成条件\n\n<!-- 例(消すこと):\n"
             "| SCR-99-A1 | <1文> |  | |\n-->\n\n" + ACH_HEAD.split("## 達成条件\n\n")[1] + OK_ROW)),
        ("解析 1行の中で閉じるコメントも外す",
         run(LEDGER, screen_body=ACH_HEAD + OK_ROW + "<!-- | SCR-99-A1 | x | | | -->\n")),
        ("UX4 惜しい見出し(補足つき)は違反",
         run(LEDGER, screen_body="## 達成条件(この画面)\n\n"
             + ACH_HEAD.split("## 達成条件\n\n")[1] + "| SCR-99-A1 |  |  |  |\n")),
        ("UX5 コマンドの面に見え方の基準を書いたら違反",
         run(LEDGER + "\n" + CMD_LEDGER, commands=("CMD-01-deploy.md",),
             command_body="- 見え方の基準: 未取得\n" + CMD_ACH)),
        ("UX2 台帳の見出しは在るが ID の行が無い",
         run("## 画面一覧\n\n| 画面名 | 目的 |\n|---|---|\n| ログイン | 入る |\n")),
        ("UX6 台帳の見出しは在るが ID の行が無い",
         run(LEDGER + "\n## コマンド一覧\n\n| サブコマンド | 目的 |\n|---|---|\n"
             "| `tool deploy` | 配る |\n", commands=("CMD-01-deploy.md",))),
    ]
    expected = {"正常形": 0, "解析 フェンス・字下げの中の見出しで節が閉じない": 0,
                "解析 箇条書きの下の台帳も読む": 0,
                "印 ちょうど未実装なら画面ファイルは要らない": 0,
                "UX4 表が無いのは違反ではない": 0, "UX4 埋まっていれば通る": 0,
                "UX4 別の節の表を達成条件と読まない": 0,
                "UX5 行が無いのは違反ではない": 0, "UX5 未取得は違反ではない": 0,
                "UX5 実在する画像なら通る": 0,
                "UX6 コマンドを持たない製品は見出しを求められない": 0,
                "UX6 画面を持たない製品は画面一覧を求められない": 0,
                "UX6 未実装の印ならファイルは要らない": 0,
                "UX4 コマンドの達成条件も見る": 0,
                "解析 セルの中のエスケープしたパイプは区切りではない": 0,
                "解析 HTML コメントの中の表の行を読まない": 0,
                "解析 1行の中で閉じるコメントも外す": 0,
                "UX7 決めてあれば通る": 0, "UX7 画面が無ければ掛からない": 0}
    bad = [name for name, rc in cases if rc != expected.get(name, 1)]
    if bad:
        print("NG 期待と違った事例: " + " / ".join(bad))
        return 1
    print(f"OK check-ux の自己検査({len(cases)} 事例: UX1〜UX7 と解析の境界)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
