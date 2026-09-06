#!/usr/bin/env python3
"""記述言語の検査。**言語規約が文章にしか無ければ fail-open である。**

規範: `.claude/directions/conventions.md` §3 / 用語: `.claude/directions/glossary.md`

実測(2026-08-21): 言語規約は `conventions.md` に文章としてしか存在せず、`check-kit-refs.py` も
`make check` も言語を1バイトも見ていなかった。結果、**英語と定めたファイル群の 6,667 行中
2,970 行(44%)が日本語**であり、**規約は書かれた瞬間から守られていなかった**。
同じ穴から `gate` の1語が5概念に当たり、`gate` 101 / `関門` 26 / `ゲート` 16 と3通りに書かれた。 (LA3-ok)
inspection-14 の「結線が文章にしか無ければ fail-open」を、キット自身の規約に向けたのがこの検査である。

**この検査は列挙を持たない。** 正は2つの規範であって、このスクリプトではない(原則10):

- **どのファイルが何語か** → `conventions.md` §3 の表(1列目のパス、2列目の言語)を読む
- **使ってはならない表記** → `glossary.md` の6欄の表の5列目を読む

見るもの:

  LA1  英語と定めたファイルに、日本語の地の文が在る
  LA2  日本語と定めたファイルに、英語の地の文が在る(英単語が4語以上続く文)
  LA3  規範用語集が「使ってはならない」と書いた表記が、規範に残っている
  LA4  規範用語集の表そのものが壊れている(6欄でない / 日本語と English の両方が空 / 定義が空)
  LA5  規範用語集 §9 が「裸の『X』を書かない」と定めた語が、修飾語を伴わずに単独で書かれている

**LA5 が読むのは「裸の『X』を書かない」の形の行だけである。** ★ §9 の書き方の欄は語ごとに違い、
「文脈が1つに定まるときだけ」「②の意味では使わない」のような**条件つき**の書き分けが大半を占める。
条件つきの禁止は、書き手がどの意味で使ったかを知らないと判定できない — **用語集自身がそう結論している**。
だから LA5 は、**§9 が「裸の『X』を書かない」の形で書いた語だけ**を見る。
**残る語は機械の外に在り、読み手が守る**(原則11。穴の在り処は用語集 §9 に明記してある)。
**許される修飾語は §9 の表から読む** — この列挙もスクリプトへ書き写さない(正が2つになる)。

**規範用語集そのものは LA1〜LA3 の対象外である。** 日本語と English が1行に並ぶのがその表の形であり、
「使ってはならない表記」を書き並べるのがその仕事だからである(`conventions.md` §3.1 が
規範用語集の両側を「訳してはならないもの」として名指している)。規範用語集を見るのは LA4 だけである。

**地の文の判定から外すもの(引用島)は `conventions.md` §3.1 が正である。**
ここで実装するのはその一覧であって、**一覧そのものをここへ書き写さない**(正が2つになる)。

**引用島が効くのは LA1・LA2 だけである。LA3 は生の行を見る。** 禁止表記が最も害を為すのは、
バッククォートに入った「スクリプトが実際に印字する文面」や雛形の中であり、そこは人間がそのまま
読む場所だからである。島を剥がすと、まさにその場所だけが検査から抜ける — 2026-08-21 の実測で、
`roles/work.md` の `回答: この窓にそのまま書いてください` を含む15か所が「窓 0件」を通り抜けていた。 (LA3-ok)

**LA3 の免除は行単位である。** 禁止表記を逐語で持つほかない行(自己検査の fixture、過去の
実測の引用)には、その行に `LA3-ok` の印を置く。**印の無い行は、どのファイルでも見る** —
免除をファイル単位にすると、そのファイルへ後から入った本番の行まで一緒に見逃す。

**Python と JSON のファイルは LA3 だけを見る。** ★ コメントと docstring の日本語化は既に済んでいる一方
(2026-08-21 の実測で英語のコメント0行)、地の文の判定はスクリプトに対してだけ誤検知が多い:
ライブラリ名の並び(`chi` `gin` `echo` `gorilla-mux`)、docstring の中のコード例、
関数シグネチャの引用、JSON の鍵の名前が、どれも「英語の地の文」に見える。**捕まえるものより落とすもののほうが
多い検査は、`make check` を鳴らし続けて信用を失わせる。** 規範(`conventions.md` §3)は変わらず
「スクリプトのコメントは日本語」であり、そこは読み手が守る(原則11)。
禁止表記(LA3)はスクリプトの出力文面にも効くので、そちらは見る。

**段階導入。** 移行中は全ファイルが違反になるので、`.claude/scripts/language-config.json` の
`migrated` に載ったファイルだけを見る。`"migrated": "all"` で全件に切り替える。
**移行済みが0件のときは終了コード 2** — 「検査して問題なし」と「検査していない」を同じ表示にしない。

使い方:
    python3 .claude/scripts/check-language.py              # キット直下(CLAUDE.md がある所)で
    python3 .claude/scripts/check-language.py --root sysdev-multi
    python3 .claude/scripts/check-language.py --list       # 実装している検査IDの一覧
    python3 .claude/scripts/check-language.py --todo       # まだ移行していないファイルを並べる
    python3 .claude/scripts/check-language.py --selftest   # 壊した事例で検知できることを示す

終了コード: 0=違反なし 1=違反あり 2=使い方・解析エラー、または検査対象が0件
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

CONVENTIONS = ".claude/directions/conventions.md"
GLOSSARY = ".claude/directions/glossary.md"
CONFIG = ".claude/scripts/language-config.json"

CHECKS: dict[str, str] = {
    "LA1": "英語と定めたファイルに日本語の地の文が在る(conventions.md §3)",
    "LA2": "日本語と定めたファイルに英語の地の文が在る(conventions.md §3)",
    "LA3": "規範用語集が「使ってはならない」と書いた表記が残っている(glossary.md)",
    "LA4": "規範用語集の表が壊れている(6欄でない / 日本語欄が空 / 日英の両側が空)",
    "LA5": "単独で書いてはならない語が、修飾語を伴わずに書かれている(glossary.md §9)",
}

# 禁止表記(LA3)の免除は**行単位**である。禁止表記を逐語で持つほかない行 — 自己検査の
# fixture、過去の実測の引用 — の**その行に**この印を置く。**印の無い行は全部見る。**
# 免除をファイル単位にすると、そのファイルへ後から入った本番の行まで一緒に見逃す
# (2026-08-22 の実測: 免除されていたスクリプトの印字行に禁止表記が1語残っていた)。
BANNED_OK = "LA3-ok"   # **LA3 と LA5 の両方をこの1つの印で免除する**(印を2種類にしても守る規則は同じ)

# **照合の前に強調記号だけを落とす。** ★ 語の途中に `**` が入るのはこのキットの常用の書き方であり
# (`directions/` と `skills/` だけで 159 箇所)、そのままだと **LA3 は見落とし、LA5 は正しい複合語を
# 違反にする**(2026-08-23 の独立検査 V-1。実測: `受け入れ**条項**` は LA3 を素通りし、 (LA3-ok)
# `デプロイ**ゲート**` は LA5 を誤って鳴らした)。**落とすのは記号だけで、引用島は剥がさない。**
EMPHASIS = re.compile(r"\*\*|__")

# LA5。規範用語集 §9 の3欄の表で、書き方の欄が**この形**で始まる行だけを読む。
# 続けて出てくる「…」のうち**その語で終わるもの**が、許される修飾語つきの形である
# (「仕様ドキュメント」は「仕様書」で終わらないので複合語ではない = 別の語である)。 (LA3-ok)
BARE_BAN = re.compile(r"裸の「([^」]+)」を書かない")

JA = "英語"          # 表の2列目がこの語なら「英語で書くファイル」
EN = "日本語"        # 表の2列目がこの語なら「日本語で書くファイル」
CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿]")

# 英語の地の文 = **大文字だけの語を除いた**英単語が4語以上続くこと。
# 大文字だけの語を数えないのは、`EARS` `WHEN` `SHALL` `OK` のような予約語・頭字語が
# 日本語の文の中に正当に並ぶためである(実測: EARS の説明行が5語として誤検知した)。
WORD = re.compile(r"[A-Za-z][A-Za-z'-]*")
EN_RUN = 4

# ---- 引用島(正は conventions.md §3.1)
FENCE = re.compile(r"^\s*```")
FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.S)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
ISLANDS = [
    re.compile(r"`[^`]*`"),                       # インラインコード
    re.compile(r"「[^」]*」"),                     # 引用
    re.compile(r"『[^』]*』"),                     # 引用
    # 長オプションと、その直後の ASCII の値(コマンド行は地の文ではない)。
    # 値を ASCII に限るのは、`--demote も渡さない` のような後続の日本語まで飲み込まないため。
    re.compile(r"(?<![\w-])--[\w-]+(?:[= ][A-Za-z0-9_./<>{}:-]+)?"),
    re.compile(r"https?://\S+"),                  # URL
    re.compile(r"\]\([^)]*\)"),                   # markdown のリンク先
    re.compile(r"<[^<>\n]{0,80}>"),               # 雛形の差し込み記号
    re.compile(r"原則\s*\d+"),                     # 言語をまたぐ ID
    re.compile(r"§\s*[\dA-Za-z.]+"),               # 節番号
    re.compile(r"\b(?:AC|FR|NFR|CTR|DSN|DS|BRC|BR|CS|SH|LA|UC|TS|SCR|SR|RQ|PLAN|MODULE|MOD|KIT|"
               r"USER|EXTERNAL|E2E|P|D0|D1|D2)"
               r"-[0-9A-Za-z][0-9A-Za-z._-]*"),   # 識別子(長い接頭辞を先に置く)
    re.compile(r"\bF[1-4]\b"),                    # フロー番号
    re.compile(r"\b(?:building|awaiting-verify|verified|green|red|PASS|FAIL|OK|NG)\b"),
    re.compile(r"[\w.-]*[\w-]/[\w./*-]+"),        # パス(スラッシュを含むもの)
    re.compile(r"[\w-]+\.(?:md|py|json|txt|conf|lock|yml|yaml|sh|ts|go)\b"),  # ファイル名
]
TABLE_SEP = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
SENTENCE_SPLIT = re.compile(r"[。!?]|(?<=[.!?])\s")


def find_root(start: Path) -> Path:
    cur = start.resolve()
    for cand in [cur, *cur.parents]:
        if (cand / "CLAUDE.md").is_file() and (cand / ".claude").is_dir():
            return cand
    return cur


# ---------------------------------------------------------------- 規範を読む


def table_rows(text: str, cells: int) -> list[list[str]]:
    """`|` の表から、ちょうど `cells` 欄の行だけを返す(見出し行と区切り行は落とす)。"""
    out = []
    for line in text.replace("\r", "").splitlines():
        line = line.strip()
        if not line.startswith("|") or TABLE_SEP.match(line):
            continue
        row = [c.strip() for c in line.strip("|").split("|")]
        if len(row) == cells and row[0]:
            out.append(row)
    return out


def language_map(conv_text: str) -> list[tuple[str, str]]:
    """(glob, 言語) の一覧。正は conventions.md §3 の表である。

    1列目の**最初のバッククォート語**を glob として使う。
    「`.claude/scripts/**.py` のコメント・docstring・出力」のように語が続く行でも同じ。
    """
    out = []
    for row in table_rows(conv_text, 3):
        m = re.search(r"`([^`]+)`", row[0])
        if not m:
            continue
        lang = re.sub(r"\*", "", row[1]).strip()
        if lang in (JA, EN):
            out.append((m.group(1), lang))
    return out


def banned_spellings(gls_text: str) -> list[str]:
    """規範用語集の5列目(使ってはならない表記)。約束は glossary.md §1。"""
    terms: set[str] = set()
    for row in table_rows(gls_text, 6):
        if row[0] == "日本語":
            continue
        for raw in re.split(r"\s*/\s*", row[4]):
            term = raw.strip().strip("`*").strip()
            if not term or term == "—" or re.search(r"[(（]", term):
                continue
            terms.add(term)
    return sorted(terms, key=len, reverse=True)


def bare_bans(gls_text: str) -> list[tuple[str, re.Pattern[str]]]:
    """LA5。規範用語集 §9 の「裸の『X』を書かない」の行から (語, 正規表現) を作る。

    正規表現は「許される修飾語のどれも直前に無い X」である。**条件つきの書き分けの行は
    この形で始まらないので、最初から読まない**(docstring の LA5 の項)。
    """
    out: list[tuple[str, re.Pattern[str]]] = []
    for row in table_rows(gls_text, 3):
        m = BARE_BAN.search(row[2])
        if not m:
            continue
        word = m.group(1)
        allowed = {q[: -len(word)] for q in re.findall(r"「([^」]+)」", row[2])
                   if q.endswith(word) and q != word}
        look = "".join(f"(?<!{re.escape(a)})" for a in sorted(allowed, key=len, reverse=True))
        out.append((word, re.compile(look + re.escape(word))))
    return out


def glossary_defects(gls_text: str) -> list[str]:
    """LA4。表の行そのものの壊れ。**規範用語集が壊れると LA3 は黙って空振りする。**"""
    bad = []
    for line in gls_text.replace("\r", "").splitlines():
        s = line.strip()
        if not s.startswith("|") or TABLE_SEP.match(s):
            continue
        row = [c.strip() for c in s.strip("|").split("|")]
        if len(row) == 2 or len(row) == 3:      # 欄の意味の表・§9 の表・§10 の表
            continue
        if len(row) != 6:
            bad.append(f"6欄でない行({len(row)}欄): {s[:60]}")
            continue
        if row[0] == "日本語":
            continue
        if not row[0] and not row[1]:
            bad.append(f"日本語も English も空: {s[:60]}")
        if not row[2]:
            bad.append(f"定義が空: {s[:60]}")
    return bad


# ---------------------------------------------------------------- 地の文を取り出す


def prose_lines(text: str, python: bool = False) -> list[tuple[int, str]]:
    """(行番号, 引用島を落とした地の文)。空になった行は返さない。

    `python=True` のときはコメントと docstring だけを見る(コードは地の文ではない)。
    """
    text = FRONTMATTER.sub("", text)
    text = HTML_COMMENT.sub("", text)
    out: list[tuple[int, str]] = []
    in_fence = False
    in_doc: str | None = None
    for n, line in enumerate(text.replace("\r", "").splitlines(), 1):
        if not python and FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if python:
            body = _python_prose(line, in_doc)
            in_doc = body[1]
            line = body[0]
            if not line:
                continue
        if TABLE_SEP.match(line):
            continue
        s = line
        for pat in ISLANDS:
            s = pat.sub(" ", s)
        s = re.sub(r"[|#*>\-–—:=/\\+_~\[\]()。、,.]", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        if s:
            out.append((n, s))
    return out


def _python_prose(line: str, in_doc: str | None) -> tuple[str, str | None]:
    """Python の行から、コメント/docstring の本文だけを取り出す。"""
    stripped = line.strip()
    if in_doc:
        if in_doc in stripped:
            return stripped.split(in_doc, 1)[0], None
        return stripped, in_doc
    m = re.match(r'^[a-zA-Z]{0,2}("""|\'\'\')(.*)$', stripped)
    if m:
        rest = m.group(2)
        if m.group(1) in rest:
            return rest.split(m.group(1), 1)[0], None
        return rest, m.group(1)
    if stripped.startswith("#"):
        return stripped.lstrip("#").strip(), None
    return "", None


def sentences(s: str) -> list[str]:
    return [x.strip() for x in SENTENCE_SPLIT.split(s) if x and x.strip()]


def english_run(s: str) -> int:
    """大文字だけの語を除いた英単語の、最長の連続数。"""
    best = run = 0
    for tok in s.split():
        words = WORD.findall(tok)
        if len(words) == 1 and words[0] == tok and not tok.isupper() and len(tok) > 1:
            run += 1
            best = max(best, run)
        else:
            run = 0
    return best


# ---------------------------------------------------------------- 検査


def expand(root: Path, pattern: str) -> list[Path]:
    """glob を展開する。`**` は再帰の意味に読む(pathlib の `**` は成分1つ分しか当たらない)。"""
    if "**" in pattern:
        head, tail = pattern.split("**", 1)
        base = root / head.rstrip("/")
        return sorted(p for p in base.rglob("*" + tail)
                      if p.is_file() and "__pycache__" not in p.parts)
    return sorted(p for p in root.glob(pattern) if p.is_file())


def targets(root: Path, conv_text: str, migrated) -> list[tuple[Path, str]]:
    """(ファイル, 言語)。`migrated` が "all" でなければ、その一覧に在るものだけ。"""
    out = []
    for pattern, lang in language_map(conv_text):
        for path in expand(root, pattern):
            rel = path.relative_to(root).as_posix()
            if migrated != "all" and rel not in migrated:
                continue
            out.append((path, lang))
    return out


def check_file(path: Path, lang: str, banned: list[str], root: Path,
               bare: list[tuple[str, re.Pattern[str]]] | None = None) -> list[tuple[str, str]]:
    rel = path.relative_to(root).as_posix()
    text = path.read_text(errors="replace")
    lines = prose_lines(text, python=path.suffix == ".py")
    out: list[tuple[str, str]] = []
    # Python と JSON は LA1/LA2 の対象外(理由は docstring)。禁止表記だけを見る。
    for n, body in ([] if path.suffix in (".py", ".json") else lines):
        for sent in sentences(body):
            if lang == JA and CJK.search(sent):
                out.append(("LA1", f"{rel}:{n}: 日本語の地の文: {sent[:70]}"))
                break
            if lang == EN and english_run(sent) >= EN_RUN:
                out.append(("LA2", f"{rel}:{n}: 英語の地の文: {sent[:70]}"))
                break
    # LA3 は言語に関係なく当てる(禁止表記はどちらのファイルでも禁止である)。
    # **引用島を剥がさない生の行を見る。** 禁止表記が最も害を為すのは、バッククォートに
    # 入った「スクリプトが実際に印字する文面」や雛形の中である — そこは人間がそのまま読む。
    # 島を剥がすと、まさにその場所だけが検査から抜ける(2026-08-21 の実測: roles/work.md の
    # `回答: この窓にそのまま書いてください` が「窓 0件」を通り抜けていた)。 (LA3-ok)
    # **免除は行単位である** — `LA3-ok` の印を置いた行だけを飛ばし、残りはどのファイルでも見る。
    for n, body in enumerate(text.splitlines(), 1):
        if BANNED_OK in body:
            continue
        probe = EMPHASIS.sub("", body)      # 照合は写しに当て、報告は元の行を出す
        for term in banned:
            if term in probe:
                out.append(("LA3", f"{rel}:{n}: 禁止表記「{term}」: {body.strip()[:60]}"))
                break
        for word, pat in (bare or []):
            if pat.search(probe):
                out.append(("LA5", f"{rel}:{n}: 修飾語の無い「{word}」: {body.strip()[:60]}"))
                break
    return out


def check(root: Path) -> int:
    conv = root / CONVENTIONS
    gls = root / GLOSSARY
    cfg = root / CONFIG
    for need in (conv, gls):
        if not need.is_file():
            print(f"エラー: {need} が無い(言語規約と規範用語集がこの検査の正である)", file=sys.stderr)
            return 2
    conv_text = conv.read_text(errors="replace")
    gls_text = gls.read_text(errors="replace")

    defects = glossary_defects(gls_text)
    banned = banned_spellings(gls_text)
    bare = bare_bans(gls_text)

    migrated = "all"
    if cfg.is_file():
        try:
            data = json.loads(cfg.read_text())
        except json.JSONDecodeError as e:
            print(f"エラー: {CONFIG} が読めない: {e}", file=sys.stderr)
            return 2
        migrated = data.get("migrated", "all")
        if migrated != "all":
            migrated = set(migrated)

    files = targets(root, conv_text, migrated)
    print(f"## 記述言語の検査: 対象 {len(files)} ファイル / 禁止表記 {len(banned)} 語"
          f" / 単独で書かない語 {len(bare)} 語")

    failures: list[tuple[str, str]] = [("LA4", f"{GLOSSARY}: {d}") for d in defects]
    for path, lang in files:
        # 規範用語集は日英が1行に並ぶのが正しい形であり、禁止表記の宣言元でもある(docstring)
        if path.resolve() == gls.resolve():
            continue
        failures += check_file(path, lang, banned, root, bare)

    if not files:
        print("  --  移行済みのファイルが0件(language-config.json の migrated が空)。"
              "**未検査は合格ではない**", file=sys.stderr)
        for cid, detail in failures:
            print(f"  NG  {cid}  {detail}")
        return 2

    if failures:
        for cid, detail in sorted(failures):
            print(f"  NG  {cid}  {detail}")
        print(f"\n→ 違反 {len(failures)} 件。正は .claude/directions/conventions.md §3 と "
              ".claude/directions/glossary.md である。"
              "**節番号を動かさずに直すこと**(全ファイルの §n 参照が一斉に死ぬ)")
        return 1

    todo = ""
    if migrated != "all":
        todo = f"(まだ移行していないものは --todo で出る)"
    print(f"  OK  記述言語と用語の表記に違反なし {todo}")
    return 0


def todo(root: Path) -> int:
    """まだ移行していないファイルを並べる。移行の進み具合を数で出す。"""
    conv_text = (root / CONVENTIONS).read_text(errors="replace")
    cfg = root / CONFIG
    migrated = set()
    if cfg.is_file():
        data = json.loads(cfg.read_text())
        if data.get("migrated") == "all":
            print("migrated: all — 残りは無い")
            return 0
        migrated = set(data.get("migrated", []))
    done = rest = 0
    for pattern, lang in language_map(conv_text):
        for path in expand(root, pattern):
            rel = path.relative_to(root).as_posix()
            if rel in migrated:
                done += 1
            else:
                rest += 1
                print(f"  {lang}  {rel}")
    print(f"\n移行済み {done} / 残り {rest}")
    return 0


# ---------------------------------------------------------------- 自己検査


CONV_FIXTURE = """# x

## 3. 記述言語

| ファイル | 言語 | 理由 |
|---|---|---|
| `CLAUDE.md` | **英語** | a |
| `.claude/directions/*.md` | **日本語** | b |
| `.claude/scripts/**.py` | **日本語** | c |
| `.claude/scripts/*.json` | **日本語** | d |
"""

GLS_FIXTURE = """# 規範用語集

| 欄 | 中身 |
|---|---|
| 日本語 | a |

| 日本語 | English | 定義 | どこを見るか | 使ってはならない表記 | 人 |
|---|---|---|---|---|---|
| デプロイゲート | deploy gate | 判定(LA3-ok) | `stamps.py check` | 関門 / デプロイ関門 | ★ |
| ウィンドウ | window | 作業単位(LA3-ok) | — | 窓 | — |

| 語 | 当たっているもの | 書き方 |
|---|---|---|
| ゲート | 2つだけ | **裸の「ゲート」を書かない** — 「デプロイゲート」「構築記録ゲート」のどちらかで書く (LA3-ok) |
| 台帳 | 決定台帳 / 要望台帳 | 裸の「台帳」は、文脈が1つに定まるときだけ |
| 仕様書 | 2つある | 「仕様ドキュメント」「機能間連携仕様書」のどちらかで書く — 裸の「仕様書」を書かない (LA3-ok) |
"""


def selftest() -> int:
    results: list[tuple[str, bool, str]] = []

    def ck(name: str, cond: bool, note: str = "") -> None:
        results.append((name, cond, note))

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / ".claude" / "directions").mkdir(parents=True)
        (root / ".claude" / "scripts").mkdir(parents=True)
        (root / CONVENTIONS).write_text(CONV_FIXTURE, encoding="utf-8")
        (root / GLOSSARY).write_text(GLS_FIXTURE, encoding="utf-8")

        # (a) 規範から表を読めている(列挙はスクリプトに無い)
        lm = language_map(CONV_FIXTURE)
        ck("(a) ファイル区分を規範から読む", lm == [("CLAUDE.md", JA),
                                                (".claude/directions/*.md", EN),
                                                (".claude/scripts/**.py", EN),
                                                (".claude/scripts/*.json", EN)], str(lm))
        bn = banned_spellings(GLS_FIXTURE)
        ck("(a) 禁止表記を規範用語集から読む", set(bn) == {"関門", "デプロイ関門", "窓"}, str(bn))  # LA3-ok
        bb = bare_bans(GLS_FIXTURE)
        ck("(a) 単独で書かない語を規範用語集から読む(条件つきの行は読まない)",
           [w for w, _ in bb] == ["ゲート", "仕様書"], str([w for w, _ in bb]))  # LA3-ok
        # **語順を仮定しない** — 許される形が先に並ぶ行でも読める(2026-08-23 の独立検査 V-2)
        ck("(a) 書き方の欄の語順に依存しない",
           dict(bb)["仕様書"].pattern == "(?<!機能間連携)仕様書",  # LA3-ok
           dict(bb)["仕様書"].pattern)  # LA3-ok  # LA3-ok

        # (b) 英語のファイルに日本語の地の文 → LA1
        (root / "CLAUDE.md").write_text(
            "# x\n\nThe deploy gate is compound.\n\nこれは日本語の地の文である。\n",
            encoding="utf-8")
        (root / ".claude/directions/a.md").write_text("# a\n\n日本語だけの行である。\n",
                                                      encoding="utf-8")
        (root / ".claude/scripts/x.py").write_text("# 日本語のコメント\nx = 1\n", encoding="utf-8")
        cfg = {"migrated": ["CLAUDE.md", ".claude/directions/a.md", ".claude/scripts/x.py"]}
        (root / CONFIG).write_text(json.dumps(cfg), encoding="utf-8")

        def ids() -> set[str]:
            conv = (root / CONVENTIONS).read_text()
            gls = (root / GLOSSARY).read_text()
            mig = set(json.loads((root / CONFIG).read_text())["migrated"])
            f: list[tuple[str, str]] = [("LA4", d) for d in glossary_defects(gls)]
            for p, lang in targets(root, conv, mig):
                f += check_file(p, lang, banned_spellings(gls), root, bare_bans(gls))
            return {c for c, _ in f}

        ck("(b) 英語ファイルの日本語は LA1", "LA1" in ids(), str(ids()))

        # (c) 引用島は**地の文ではない**(LA1/LA2 は見ない)。
        # ただし **LA3 は引用島の中も見る** — 禁止表記が最も害を為すのは、バッククォートに
        # 入った「スクリプトが実際に印字する文面」だからである(check_file のコメント)。
        (root / "CLAUDE.md").write_text(
            "# x\n\nThe gate is 「関門」 in the old spelling, see 原則4 and `決定シート`.\n"  # LA3-ok
            "It writes `## 基本要件の点検` into the record.\n", encoding="utf-8")
        ck("(c) 引用・原則n・行内コードは地の文でない", "LA1" not in ids(), str(ids()))
        ck("(c) 引用島の中の禁止表記は LA3 が見る", "LA3" in ids(), str(ids()))
        (root / "CLAUDE.md").write_text(
            "# x\n\nThe deploy gate is compound.\n", encoding="utf-8")

        # (d) 日本語のファイルに英語の地の文 → LA2
        (root / ".claude/directions/a.md").write_text(
            "# a\n\nThis sentence is written in plain English prose.\n", encoding="utf-8")
        ck("(d) 日本語ファイルの英語は LA2", "LA2" in ids(), str(ids()))

        # (e) 頭字語・予約語の並びは英語の地の文ではない
        (root / ".claude/directions/a.md").write_text(
            "# a\n\n受け入れ基準は EARS(WHEN / IF THEN / WHILE / WHERE + SHALL)で書く。\n"
            "契約は OpenAPI 3.1 である。図は Mermaid。\n", encoding="utf-8")
        ck("(e) 頭字語の並びは誤検知しない", "LA2" not in ids(), str(ids()))

        # (f) 禁止表記は言語に関係なく LA3
        (root / ".claude/directions/a.md").write_text(
            "# a\n\nデプロイの可否は関門が決める。\n", encoding="utf-8")  # LA3-ok
        ck("(f) 禁止表記は LA3", "LA3" in ids(), str(ids()))
        # 免除は行単位 — 印を置いた行だけが LA3 から外れる(`LA3-ok`)
        (root / ".claude/directions/a.md").write_text(
            "# a\n\nデプロイの可否は関門が決める。  LA3-ok\n", encoding="utf-8")  # LA3-ok
        ck("(f) 印を置いた行は LA3 で見ない", not ids(), str(ids()))
        (root / ".claude/directions/a.md").write_text(
            "# a\n\nデプロイの可否はデプロイゲートが決める。\n", encoding="utf-8")
        ck("(f) 正しい表記なら通る", not ids(), str(ids()))

        # (f2) LA5 — 修飾語の無い語。**許される複合語は誤検知しない**のがこの検査の要である。
        (root / ".claude/directions/a.md").write_text(
            "# a\n\nゲートが失効した。\n", encoding="utf-8")  # LA3-ok
        ck("(f2) 修飾語の無い語は LA5", "LA5" in ids(), str(ids()))
        (root / ".claude/directions/a.md").write_text(
            "# a\n\nデプロイゲートと構築記録ゲートの両方が green である。\n", encoding="utf-8")
        ck("(f2) 許される複合語は LA5 を鳴らさない", not ids(), str(ids()))
        (root / ".claude/directions/a.md").write_text(
            "# a\n\n台帳を1行読む。\n", encoding="utf-8")
        ck("(f2) 条件つきの書き分けは LA5 の対象外", not ids(), str(ids()))
        (root / ".claude/directions/a.md").write_text(
            "# a\n\nゲートが失効した。  LA3-ok\n", encoding="utf-8")
        ck("(f2) 印を置いた行は LA5 でも見ない", not ids(), str(ids()))

        # (f3) 強調記号が語を割る形。**照合の前に記号だけを落とす**ので、
        # LA5 は誤検知せず、LA3 は見落とさない(2026-08-23 の独立検査 V-1)。
        (root / ".claude/directions/a.md").write_text(
            "# a\n\nデプロイ**ゲート**が red になる。\n", encoding="utf-8")
        ck("(f3) 強調記号で割れた複合語を LA5 が誤検知しない", not ids(), str(ids()))
        (root / ".claude/directions/a.md").write_text(
            "# a\n\n機能間連携**仕様書**を読む。\n", encoding="utf-8")
        ck("(f3) 同上(もう1語)", not ids(), str(ids()))
        (root / ".claude/directions/a.md").write_text(
            "# a\n\nデプロイの可否は関**門**が決める。\n", encoding="utf-8")  # LA3-ok
        ck("(f3) 強調記号で割れた禁止表記を LA3 が見落とさない", "LA3" in ids(), str(ids()))
        (root / ".claude/directions/a.md").write_text(
            "# a\n\nデプロイの可否はデプロイゲートが決める。\n", encoding="utf-8")

        # (g) Python はコメントと docstring だけを見る(コードは地の文ではない)
        (root / ".claude/scripts/x.py").write_text(
            'def f():\n    """日本語の説明。"""\n    return "this is a plain english string"\n',
            encoding="utf-8")
        ck("(g) Python の文字列は地の文でない", "LA2" not in ids(), str(ids()))
        # Python は LA1/LA2 の対象外である(誤検知が捕捉より多い — docstring 参照)。
        (root / ".claude/scripts/x.py").write_text(
            "# this comment is written in english\nx = 1\n", encoding="utf-8")
        ck("(g) Python の英語コメントは LA2 にしない", "LA2" not in ids(), str(ids()))
        (root / ".claude/scripts/x.py").write_text(
            "# デプロイの可否は関門が決める\nx = 1\n", encoding="utf-8")  # LA3-ok
        ck("(g) Python の禁止表記は LA3 で見る", "LA3" in ids(), str(ids()))
        (root / ".claude/scripts/x.py").write_text("# 日本語\nx = 1\n", encoding="utf-8")

        # (h) 移行していないファイルは見ない(段階導入)
        (root / ".claude/directions/b.md").write_text(
            "# b\n\nThis file is not migrated yet and must not be checked.\n", encoding="utf-8")
        ck("(h) 未移行のファイルは見ない", not ids(), str(ids()))

        # (i) 対象0件は 2(未検査を合格と見せない)
        (root / CONFIG).write_text(json.dumps({"migrated": []}), encoding="utf-8")
        ck("(i) 対象0件は 2", check(root) == 2)
        (root / CONFIG).write_text(json.dumps(cfg), encoding="utf-8")

        # (j) 規範用語集が壊れたら LA4(壊れると LA3 が黙って空振りする)
        (root / GLOSSARY).write_text(
            GLS_FIXTURE + "| 欠けた行 | en | 定義 | — | — |\n", encoding="utf-8")
        ck("(j) 6欄でない行は LA4", "LA4" in ids(), str(ids()))
        (root / GLOSSARY).write_text(GLS_FIXTURE, encoding="utf-8")

        # (l) 規範用語集そのものは LA1〜LA3 の対象外(日英が並ぶのが正しい形であり、禁止表記の宣言元)
        cfg2 = dict(cfg)
        cfg2["migrated"] = cfg["migrated"] + [GLOSSARY]
        (root / CONFIG).write_text(json.dumps(cfg2), encoding="utf-8")
        ck("(l) 規範用語集は LA1〜LA3 で落ちない", check(root) == 0)
        (root / CONFIG).write_text(json.dumps(cfg), encoding="utf-8")

        # (k) 規範が無ければ 2(黙って合格にしない)
        (root / CONVENTIONS).unlink()
        ck("(k) 言語規約が無ければ 2", check(root) == 2)

    for name, okc, _ in results:
        print(f"  {'PASS' if okc else 'FAIL'}  {name}")
    ng = [(n, note) for n, c, note in results if not c]
    if ng:
        print(f"\n{len(ng)} 件 FAIL", file=sys.stderr)
        for n, note in ng:
            print(f"--- {n}\n{note}", file=sys.stderr)
        return 1
    print(f"\n全 {len(results)} 項目 PASS")
    return 0


def main(argv: list[str]) -> int:
    args = argv[1:]
    if any(a in ("-h", "--help") for a in args):
        print(__doc__)          # 明示要求は 0。使い方エラーの 2 と区別する(tools-readme §2)
        return 0
    if args and args[0] == "--list":
        for cid, desc in CHECKS.items():
            print(f"{cid}  {desc}")
        return 0
    if args and args[0] == "--selftest":
        return selftest()
    root = Path.cwd()
    if "--root" in args:
        i = args.index("--root")
        if i + 1 >= len(args):
            print(__doc__, file=sys.stderr)
            return 2
        root = Path(args[i + 1])
        args = args[:i] + args[i + 2:]
    else:
        root = find_root(root)
    if args and args[0] == "--todo":
        return todo(root)
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    return check(root)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
