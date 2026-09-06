#!/usr/bin/env python3
"""キット内参照の実在検査。**規範を再構築すると、スクリプトとスキルの参照が黙って死ぬ**。

実測: CLAUDE.md の全面再構築(停止条件つき規範化)の後、キット内に
「CLAUDE.md §9」(存在しない節。エラーメッセージの案内先)が4箇所、
「.claude/directions/layer-fit.md」(統合で消えたファイル)が3箇所、
「task-memo.md §3.3」「issues-pendings.md §1.1」(改番で消えた小節)などが残った。
どれも**利用者が最も規範を必要とする瞬間(検査に落ちた時)に行き止まりを見せる**参照であり、
人間が読むまで気づけない一方、機械なら一撃で全件出る型の欠陥 — CS11(参照実在)の思想を
キット自身に向けたのがこの検査である。

見るもの(キットのテキスト全部: CLAUDE.md / agents / directions / skills / roles / templates /
scripts / tools-readme):
  (a) `.claude/`(または裸の)agents/ directions/ templates/ skills/ scripts/ roles/ へのパス参照が実在するか
  (b) 「CLAUDE.md §n」「原則n」が現在の CLAUDE.md の節数・原則数の中か
  (c) 「<file>.md §n(.m)」が、そのファイルの番号付き見出しに実在するか
      (§ の直前 60 文字以内の最後の .md 名に紐づける。ファイル名が無い § は見ない —
       自スキル内参照「§0A」等は対象外。番号付き見出しを持たないファイルも見ない)
  (d) キットのテキスト(.md と .py の両方)が名指す検査ID(CS-nn / SH-nn / BRC-n / LA-n)が、
      それを実装するスクリプトの CHECKS / names に実在するか(実測: 再設計後に
      CS13・CS16・CS17・CS23 の亡霊参照が6ファイルに残った — inspection-14。
      **`.py` も見る**: 掃除の後に `.md` の外で生き延びた `CS17` が1件残っていた — inspection-21 C-6)
  (e) `baseline.md` の `| BR-nn |` 行が **§2 の中だけ**に在るか(基本要件を読む
      スクリプトは節では切らず**ファイル全体**から集めるので、§2 の外に置いた行は
      「書いた覚えのない項目」として一覧に入る。規範の側の宣言は `baseline.md` §2 の冒頭)

使い方:
    python3 .claude/scripts/check-kit-refs.py             # キット直下(CLAUDE.md がある所)で
    python3 .claude/scripts/check-kit-refs.py --root sysdev
    python3 .claude/scripts/check-kit-refs.py --selftest

終了コード: 0=違反なし 1=違反あり 2=使い方・解析エラー
"""

import pathlib
import re
import sys

# パス参照: プレースホルダ(< >)や glob(*)を含むものは参照ではない
PATH_RE = re.compile(r'(?:\.claude/)?(?:agents|directions|templates|skills|scripts|roles)/[\w./-]+\.(?:md|py|json)')
SEC_RE = re.compile(r'§\s*(\d+(?:\.\d+)*)')
FILE_TOKEN_RE = re.compile(r'([\w./-]*[\w-]\.md)')
HEADING_RE = re.compile(r'^#{1,4}\s*(?:§\s*)?(\d+[A-Za-z]?(?:\.\d+)*)[.\s]', re.M)
PRINCIPLE_RE = re.compile(r'原則\s*(\d+)')


def kit_texts(root):
    """検査対象のテキストファイル一覧(パス, 本文)。

    - スクリプトの selftest 部(`def selftest` 以降)は見ない — フィクスチャのパスは
      実在しないのが正しい。
    - このスクリプト自身も見ない — docstring が実測の死んだ参照を逐語で記録している。
    - `scripts/` は `.py` だけでなく `.md`(設計記録)も見る。配布物であり、規範が正として
      参照している一方で走査の外に在ったため、退役したスキル5つと削除されたスクリプト1本を
      「いま直す対象」として名指す表が腐ったまま残っていた(inspection-21 C-11)。
    """
    files = [root / "CLAUDE.md", root / ".claude" / "tools-readme.md"]
    for pat in ("agents/*.md", "directions/*.md", "templates/*.md", "skills/*/SKILL.md", "roles/*.md"):
        files += sorted((root / ".claude").glob(pat))
    files += sorted(p for p in (root / ".claude" / "scripts").rglob("*.py")
                    if "__pycache__" not in p.parts and p.name != "check-kit-refs.py")
    files += sorted((root / ".claude" / "scripts").rglob("*.md"))
    out = []
    for p in files:
        if not p.is_file():
            continue
        text = p.read_text(errors="replace")
        if p.suffix == ".py":
            text = re.split(r'^def selftest\b', text, maxsplit=1, flags=re.M)[0]
        out.append((p, text))
    return out


def headings_of(path, cache):
    """番号付き見出しの番号トークン集合。無ければ None(そのファイルは § を検査しない)。"""
    if path not in cache:
        toks = set(HEADING_RE.findall(path.read_text(errors="replace"))) if path.is_file() else set()
        cache[path] = toks or None
    return cache[path]


def resolve_md(token, root):
    """§ 参照が指す .md をキット内で解決する。解決できなければ None(検査しない)。"""
    token = token.lstrip("(`「『")
    if "<" in token or "*" in token:
        return None
    cands = []
    if "/" in token:
        # **`lstrip("./")` にしてはならない。** 集合として剥がすので `.claude/…` の先頭の `.` が
        # 落ち、次行の `.claude/` 判定が永久に偽になる — その形の参照(実測 106/117 件)が
        # 黙って未検査になっていた(2026-08-18)。剥がすのは先頭の `./` 1回だけである。
        rel = token[2:] if token.startswith("./") else token
        rel = rel[len(".claude/"):] if rel.startswith(".claude/") else rel
        # **キットの中だけを解決する。**`docs/…` を解決すると、キットの規範が製品仕様ドキュメントの
        # 節番号を検査することになり、/kit-improve §0 の「docs/ はキットの変更の一部ではない」に
        # 反する。実害も出た: `docs/03-impl/index.md` の `## 02 との差分` が見出し番号 `02` として
        # 拾われ、その文書に §3 が無いという誤検知になった(2026-08-10。§3 は同じ行が名指しする
        # `/task-close` の節であって index.md の節ではない)。docs/ 側の参照実在は CS11 が見る。
        cands = [root / ".claude" / rel]
    elif token == "CLAUDE.md":
        cands = [root / "CLAUDE.md"]
    else:
        # 裸のファイル名は directions のものとみなす(templates と重名でも、§ 付き参照の
        # 実態は規範側 — templates は番号付き見出しを持たないので誤検査にならない)
        cands = [root / ".claude" / "directions" / token]
    return next((c for c in cands if c.is_file()), None)


NAMED_SEC_RE = re.compile(r'「([^」]{4,})」')
READING_ROW_RE = re.compile(r'(?m)^\|\s*`?/[\w-]+`?\s*\|')


def named_headings_of(path, cache):
    """見出しの**文字列そのもの**の集合。番号付き見出ししか見ない §検査の穴を塞ぐ。"""
    key = ("named", path)
    if key not in cache:
        toks = set()
        if path.is_file():
            for line in path.read_text(errors="replace").splitlines():
                m = re.match(r'^#{1,4}\s+(.+?)\s*$', line)
                if m:
                    toks.add(m.group(1))
                    # 「## 3. Format」→「Format」でも指せるようにする(番号は §n 側で指す)
                    toks.add(re.sub(r'^[\d.]+[A-Za-z]?\.?\s*', '', m.group(1)))
        cache[key] = toks
    return cache[key]


def check_reading_manifest(root, hcache):
    """reading.md が名指す節が実在するか。**この検査が無いと読了マニフェストは黙って腐る。**

    表の各行から `<file>.md §n` と `<file>.md 「見出し名」` を拾い、そのファイルに在るかを見る。
    §n 側は check() の (c) が拾うので、ここは**名前で指した見出し**を担当する。
    """
    path = root / ".claude" / "directions" / "reading.md"
    if not path.is_file():
        return []
    out = []
    for row in path.read_text(errors="replace").splitlines():
        if not READING_ROW_RE.match(row):
            continue
        # 1つの行に複数ファイルが並ぶので、`<name>.md` ごとに直後の断片を見る
        for m in re.finditer(r'`([\w./-]+\.md)`([^`]*)', row):
            target = resolve_md(m.group(1), root)
            if target is None:
                continue
            for named in NAMED_SEC_RE.findall(m.group(2)):
                if named not in named_headings_of(target, hcache):
                    out.append((pathlib.Path(".claude/directions/reading.md"),
                                f"{m.group(1)} に見出し「{named}」が無い"))
    return out


CHECK_ID_RE = re.compile(r'\b(CS|SH|BRC|LA)(\d+)\b')
CHECK_OWNERS = {"CS": "scripts/check-ssot.py", "SH": "scripts/check-sheet.py",
                "BRC": "scripts/check-buildrecord.py", "LA": "scripts/check-language.py"}


def implemented_check_ids(root):
    """スクリプトが実装する検査IDの集合("CS8" 等)。定義行 `"CS8":` を拾う。"""
    ids = set()
    for rel in CHECK_OWNERS.values():
        path = root / ".claude" / rel
        if not path.is_file():
            continue
        for m in re.finditer(r'"((?:CS|SH|BRC|LA)\d+)"\s*:', path.read_text(errors="replace")):
            ids.add(m.group(1))
    return ids


def check_ids_in_norms(root, files):
    """(d) キットのテキストが名指す検査IDが実装に在るか。**`.py` も見る。**

    定義行(`"CS8":`)は実装の側なので必ず impl に入り、素通りする。拾いたいのは
    コメント・docstring に残った亡霊参照である(実測: 掃除の後に `check-ssot.py` の
    `CS17` が1件だけ生き延びた — inspection-21 C-6)。
    """
    impl = implemented_check_ids(root)
    if not impl:
        return []
    out = []
    for path, text in files:
        rel = path.relative_to(root)
        for m in CHECK_ID_RE.finditer(text):
            cid = m.group(1) + m.group(2)
            if cid not in impl:
                out.append((rel, f"実在しない検査ID: {cid}"
                                 f"(実装の正: {CHECK_OWNERS[m.group(1)]})"))
    return out


BASELINE_REL = pathlib.PurePosixPath(".claude/directions/baseline.md")
BR_TABLE_ROW = re.compile(r"^\|\s*\**\s*BR-\d{2}\s*\**\s*\|")


def check_baseline_rows(root):
    """(e) `| BR-nn |` 行が §2 の中だけに在るか。

    `check-buildrecord.py` と `check-baseline-verdicts.py` はどちらも baseline.md を
    **行単位で全体走査**して ID を集める(節では切らない)。だから §3 の説明や §4 の
    廃止の記録として同じ形の行を書くと、その ID が黙って一覧に入り、**全タスクの構築記録が
    その判定行を要求される**。規範はこれを禁じている(`baseline.md` §2 の冒頭・§4.4)。
    """
    path = pathlib.Path(root) / BASELINE_REL
    if not path.is_file():
        return []                       # baseline.md を持たないキットは対象外
    out, sec = [], None
    for i, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        m = re.match(r"^##\s*(\d+)\.", line)
        if m:
            sec = m.group(1)
        if BR_TABLE_ROW.match(line.strip()) and sec != "2":
            out.append((BASELINE_REL, f"§2 の外に `| BR-nn |` の行が在る(:{i})"
                                      f" — 機械はファイル全体から ID を集める"))
    return out


def check(root):
    root = pathlib.Path(root)
    claude = root / "CLAUDE.md"
    if not claude.is_file():
        print(f"エラー: {claude} が無い(--root にキットの根を渡す)", file=sys.stderr)
        return 2
    ctext = claude.read_text(errors="replace")
    csecs = {m.group(1) for m in re.finditer(r'^## (\d+)\.', ctext, re.M)}
    # 原則の数は §2 の番号付き項目から数える(書き写すと正が2つになる)
    body2 = ctext.split("## 2.", 1)[-1].split("\n## ", 1)[0]
    nprin = max((int(m.group(1)) for m in re.finditer(r'^(\d+)\. \*\*', body2, re.M)), default=0)

    out, hcache = [], {}
    for path, text in kit_texts(root):
        rel = path.relative_to(root)
        flat = re.sub(r'\s+', ' ', text)
        # (a) パス参照の実在。*.local.json は利用者ローカルの上書きで、無いのが既定。
        # 「xxx」はキットの例示プレースホルダ(cgx/base.py の `xxx.py` 等)
        for m in PATH_RE.finditer(flat):
            tok = m.group(0)
            if "<" in tok or "*" in tok or "xxx" in tok or tok.endswith(".local.json"):
                continue
            p = tok[len(".claude/"):] if tok.startswith(".claude/") else tok
            if not (root / ".claude" / p).exists():
                out.append((rel, f"実在しないパス: {tok}"))
        # (b) 原則番号の範囲
        for m in PRINCIPLE_RE.finditer(flat):
            if int(m.group(1)) > nprin:
                out.append((rel, f"存在しない原則: 原則{m.group(1)}(原則は {nprin} まで)"))
        # (c) <file>.md §n の見出し実在(CLAUDE.md §n もここで見る)
        for m in SEC_RE.finditer(flat):
            window = flat[max(0, m.start() - 60):m.start()]
            files = FILE_TOKEN_RE.findall(window)
            if not files:
                continue
            target = resolve_md(files[-1], root)
            if target is None:
                continue
            if target == claude:
                if m.group(1) not in csecs:
                    out.append((rel, f"存在しない節: CLAUDE.md §{m.group(1)}(節は 1〜{max(map(int, csecs))})"))
                continue
            toks = headings_of(target, hcache)
            if toks is None:
                continue
            sec = m.group(1)
            if sec not in toks and not any(t.startswith(sec) and t[len(sec):len(sec) + 1].isalpha()
                                           for t in toks):
                out.append((rel, f"{files[-1].lstrip('(`「『')} に §{sec} が無い"))

    out += check_reading_manifest(root, hcache)
    out += check_ids_in_norms(root, kit_texts(root))
    out += check_baseline_rows(root)

    if out:
        print(f"NG  キット内の参照と宣言 {len(out)} 件が規範と合っていない"
              f"(改番の追随漏れ、または §2 の外の `| BR-nn |` 行):")
        for rel, msg in out:
            print(f"  {rel}: {msg}")
        return 1
    print("OK  キット内参照(パス・CLAUDE.md 節・原則番号・§見出し・reading.md の名前付き見出し・"
          "検査ID)すべて実在。`| BR-nn |` の行も §2 の中だけ")
    return 0


def selftest():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        (root / ".claude" / "directions").mkdir(parents=True)
        (root / ".claude" / "scripts").mkdir()
        (root / "CLAUDE.md").write_text(
            "## 1. A\n## 2. P\n1. **a.**\n2. **b.**\n## 3. B\n", encoding="utf-8")
        (root / ".claude" / "directions" / "x.md").write_text("## 1. a\n### 1.2 b\n", encoding="utf-8")
        ok = (root / ".claude" / "scripts" / "ok.py")
        ok.write_text("# CLAUDE.md §3 と 原則2 と .claude/directions/x.md §1.2\n", encoding="utf-8")
        assert check(root) == 0, "正しい参照が違反になった"
        ok.write_text("# CLAUDE.md §9 / 原則12 / .claude/directions/gone.md / x.md §3.3\n",
                      encoding="utf-8")
        assert check(root) == 1, "死んだ参照を見逃した"
        # **`.claude/` を前置した形**。この形が解決できないと、キットの § 参照の大半が
        # 黙って未検査になる(上の resolve_md のコメント)。両向きで見る。
        ok.write_text("# .claude/directions/x.md §1.2\n", encoding="utf-8")
        assert check(root) == 0, ".claude/ 付きの正しい § 参照が違反になった"
        ok.write_text("# .claude/directions/x.md §9\n", encoding="utf-8")
        assert check(root) == 1, ".claude/ 付きの死んだ § 参照を見逃した"
        # 読了マニフェストの名前付き見出し(番号付き見出ししか見ない §検査の穴)
        ok.write_text("# ok\n", encoding="utf-8")
        reading = root / ".claude" / "directions" / "reading.md"
        reading.write_text("| `/task-doc` | — | `x.md` 「b」 |\n", encoding="utf-8")
        assert check(root) == 0, "実在する名前付き見出しが違反になった"
        reading.write_text("| `/task-doc` | — | `x.md` 「消えた見出し」 |\n", encoding="utf-8")
        assert check(root) == 1, "reading.md の死んだ名前付き見出しを見逃した"
        reading.unlink()
        # (e) `| BR-nn |` は §2 の中だけ。**baseline.md が無いキットは対象外**である
        base = root / ".claude" / "directions" / "baseline.md"
        base.write_text("## 2. 一覧\n| ID |\n|---|\n| **BR-01** | a |\n"
                        "## 3. 各項目\n### 3.1 BR-01\n- 本文\n", encoding="utf-8")
        assert check(root) == 0, "§2 の中の BR 行が違反になった"
        base.write_text("## 2. 一覧\n| ID |\n|---|\n| **BR-01** | a |\n"
                        "## 4. 足しかた\n| BR-02 | 廃止 |\n", encoding="utf-8")
        assert check(root) == 1, "§2 の外の BR 行を見逃した"
        base.unlink()
    print("selftest: OK")
    return 0


def main(argv):
    root = "."
    if any(a in ("-h", "--help") for a in argv):
        print(__doc__)   # 明示要求は 0。使い方エラーの 2 と区別する(tools-readme §2)
        return 0
    if "--selftest" in argv:
        return selftest()
    if "--root" in argv:
        i = argv.index("--root")
        if i + 1 >= len(argv):
            print("エラー: --root に値が無い", file=sys.stderr)
            return 2
        root = argv[i + 1]
    return check(root)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
