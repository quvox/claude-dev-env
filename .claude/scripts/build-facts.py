#!/usr/bin/env python3
"""事実の生成器 — **同じ事実を2か所に手で書かない**ための道具。

**なぜ在るか**: 2026-08-26 の実測で、1つの検証の周が直した15件は**全件が「別の場所に正しい値が
あるのに、その写しが古くなっていた」**であり、1つの事実が12本の文書の46か所に手で書かれていた。
**写しは必ずずれる。** 検査がそれを毎周直すのは、生まれないようにしていないからである。

規範の正は `.claude/directions/conventions.md` の「同じ事実を2か所に手で書かない」の節である。
ここが持つのは**機械の側**だけ:

  (1) **機械の欄を埋める**(`update`)— 手で保守する文書の中の、道具が丸ごと書く区画。

          <!-- BEGIN GENERATED: build-facts.py id=<事実の id> -->
          …ここは手で書かない…
          <!-- END GENERATED: build-facts.py -->

      **`id=` は必須である** — どの事実を出す区画かが決まらなければ、埋めようがない。
      **終端に道具名を書く形は `build-index.py` と同じである**(`callgraphs.md` §4)。

  (2) **差分ゼロを確かめる**(`check`)— 生成し直した中身と文書の現状が1バイトも違わないこと。
      **違う = 誰かが写しを手で書いたか、実装が変わったのに欄を埋め直していない**、である。

  (3) **参照先が実在することを確かめる**(`check`)— 持ち主でない文書は、写さずに参照する。
      その形は次のとおりで、**この形だけを見る**:

          `<リポジトリ相対パス>` の「<節見出し>」が正である。(要旨: <60字以内の1文>)

      見るのは2つ — **パスが実在すること**と、**その節見出しがそのファイルに在ること**。
      **要旨が60字を超えたものは数えて出すだけである**(違反にしない)— あれは「写しへ
      戻り始めた」ことに気づくための計器であって、拒む門ではない。

**宣言は `docs/facts.json` に置く。** 1件1欄で、欄は4つ:

```json
{
  "facts": [
    {"id": "test-count",  "type": "count_files",
     "args": {"glob": "tests/**/*_test.py"}, "format": "{n}本"},
    {"id": "caller-count", "type": "count_matches",
     "args": {"glob": "src/**/*.py", "regex": "load_conf\\\\("}, "format": "{n}"},
    {"id": "default-path", "type": "capture",
     "args": {"file": "internal/conf/conf.go", "regex": "Default\\\\s*=\\\\s*\\"([^\\"]+)\\""},
     "format": "`{v}`"},
    {"id": "fr-table",    "type": "mirror_table",
     "args": {"file": "docs/01-requirements/functional.md", "heading": "## 機能要件"}}
  ]
}
```

**抽出器は組み込みの4つだけであり、任意のコマンドは決して実行しない** ★ — 宣言を書ける者が
任意のコマンドを走らせられるなら、それは宣言ではなく別のコードである。4つで、2026-08-26 に
ずれた15件のうち**13件**を覆う(残る2件は版番号の繰り上げと索引の作り直しで、前者は管理欄、
後者は `build-index.py` の仕事であり、どちらもこの道具の守備範囲ではない):

| type | 何を出すか | args | format |
|---|---|---|---|
| `count_files` | glob に合うファイルの数 | `glob` | `{n}`(既定 `{n}`) |
| `count_matches` | glob × 正規表現の一致の総数 | `glob`, `regex` | `{n}`(既定 `{n}`) |
| `capture` | 1ファイル × 正規表現の捕捉値 | `file`, `regex`, `group`(既定 1) | `{v}`(既定 `{v}`) |
| `mirror_table` | 上の層の文書の表の写し | `file`, `heading` | 使わない(表そのもの) |

**同じ入力なら同じバイト列が出る**(ファイルの一覧は辞書順に固定する。`callgraphs.md` §4 と
同じ理由 — さもないと生成のたびに差分が出て、生成物が検査の邪魔になる)。

使い方:
    python3 .claude/scripts/build-facts.py update      # 機械の欄を埋める
    python3 .claude/scripts/build-facts.py check       # 差分ゼロ + 参照先の実在
    python3 .claude/scripts/build-facts.py --selftest

終了コード: 0=違反なし 1=違反あり 2=使い方・解析エラー
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

FACTS = Path("docs/facts.json")
DOCS = Path("docs")

BEGIN_RE = re.compile(r"<!--\s*BEGIN GENERATED:\s*build-facts\.py\s+id=([\w.\-]+)\s*-->")
END_MARK = "<!-- END GENERATED: build-facts.py -->"
END_RE = re.compile(r"<!--\s*END GENERATED:\s*build-facts\.py\s*-->")
# 参照の形。**この形だけを見る** — 地の文の「〜が正である」を拾わないための括弧と鉤括弧である。
REF_RE = re.compile(r"`([\w./\-]+\.md)`\s*の\s*「([^」]+)」\s*が正である")
SUMMARY_RE = re.compile(r"(?:\(|\()要旨:\s*([^)\)]*)(?:\)|\))")
HEADING_RE = re.compile(r"(?m)^(#{1,6})\s+(.*?)\s*$")
SUMMARY_LIMIT = 60


def find_root(start: Path) -> Path:
    cur = start.resolve()
    for cand in (cur, *cur.parents):
        if (cand / "CLAUDE.md").is_file() and (cand / ".claude").is_dir():
            return cand
    return cur


def load_facts(root: Path) -> tuple[dict[str, dict], list[str]]:
    path = root / FACTS
    if not path.is_file():
        return {}, []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, [f"{FACTS}: 読めない({exc})"]
    errs: list[str] = []
    out: dict[str, dict] = {}
    for i, item in enumerate(data.get("facts", [])):
        fid = str(item.get("id", "")).strip()
        if not fid:
            errs.append(f"{FACTS}: {i} 件目に id が無い")
            continue
        if fid in out:
            errs.append(f"{FACTS}: id が重複している: {fid}")
            continue
        out[fid] = item
    return out, errs


def docs_files(root: Path) -> list[Path]:
    base = root / DOCS
    if not base.is_dir():
        return []
    return sorted(p for p in base.rglob("*.md") if p.is_file())


def headings(text: str) -> set[str]:
    """`## 見出し` の見出し文字列。`##` を付けた形と、付けない形の両方で引ける。"""
    out: set[str] = set()
    for m in HEADING_RE.finditer(text):
        title = m.group(2).strip()
        out.add(title)
        out.add(f"{m.group(1)} {title}")
    return out


def table_under(text: str, heading: str) -> str | None:
    """その見出しの下に最初に現れる markdown の表を、逐語で返す。"""
    want = heading.strip().lstrip("#").strip()
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if m and m.group(2).strip() == want:
            start = i + 1
            break
    if start is None:
        return None
    rows: list[str] = []
    for line in lines[start:]:
        if line.strip().startswith("|"):
            rows.append(line.rstrip())
        elif rows:
            break
        elif line.startswith("#"):
            return None
    return "\n".join(rows) if rows else None


def render(root: Path, spec: dict) -> tuple[str | None, str | None]:
    """(生成した中身, 誤りの説明)。どちらか一方だけが `None` でない。"""
    typ = spec.get("type", "")
    args = spec.get("args", {}) or {}
    fmt = spec.get("format")
    try:
        if typ == "count_files":
            g = args["glob"]
            n = len(sorted(p for p in root.glob(g) if p.is_file()))
            return (fmt or "{n}").replace("{n}", str(n)), None
        if typ == "count_matches":
            g, rx = args["glob"], re.compile(args["regex"])
            n = 0
            for p in sorted(root.glob(g)):
                if p.is_file():
                    n += len(rx.findall(p.read_text(encoding="utf-8", errors="replace")))
            return (fmt or "{n}").replace("{n}", str(n)), None
        if typ == "capture":
            p = root / args["file"]
            if not p.is_file():
                return None, f"capture: ファイルが無い: {args['file']}"
            m = re.search(args["regex"], p.read_text(encoding="utf-8", errors="replace"))
            if not m:
                return None, f"capture: 一致しない: {args['file']} / {args['regex']}"
            group = int(args.get("group", 1))
            return (fmt or "{v}").replace("{v}", m.group(group)), None
        if typ == "mirror_table":
            p = root / args["file"]
            if not p.is_file():
                return None, f"mirror_table: ファイルが無い: {args['file']}"
            tbl = table_under(p.read_text(encoding="utf-8", errors="replace"), args["heading"])
            if tbl is None:
                return None, (f"mirror_table: 見出しの下に表が無い: "
                              f"{args['file']} / {args['heading']}")
            return tbl, None
    except KeyError as exc:
        return None, f"{typ}: args に {exc} が無い"
    except re.error as exc:
        return None, f"{typ}: 正規表現が壊れている({exc})"
    except OSError as exc:
        return None, f"{typ}: 読めない({exc})"
    return None, f"知らない type: {typ or '(空)'}"


def regions(text: str) -> list[tuple[str, int, int, str]]:
    """(id, 中身の開始, 中身の終端, いまの中身)。終端の印が無い区画は返さない。"""
    out = []
    for m in BEGIN_RE.finditer(text):
        e = END_RE.search(text, m.end())
        if not e:
            continue
        body = text[m.end():e.start()]
        out.append((m.group(1), m.end(), e.start(), body))
    return out


def normalize(body: str) -> str:
    return body.strip("\n").strip()


def scan_refs(root: Path, path: Path, text: str) -> tuple[list[str], int]:
    """参照の実在検査。(違反の行, 60字を超えた要旨の数)。"""
    bad: list[str] = []
    longs = 0
    rel = path.relative_to(root)
    for m in REF_RE.finditer(text):
        target, heading = m.group(1), m.group(2).strip()
        tpath = root / target
        line = text[:m.start()].count("\n") + 1
        if not tpath.is_file():
            bad.append(f"{rel}:{line}: 参照先のファイルが無い: {target}")
            continue
        if heading not in headings(tpath.read_text(encoding="utf-8", errors="replace")):
            bad.append(f"{rel}:{line}: 参照先に節が無い: {target} の「{heading}」")
        tail = text[m.end():m.end() + 200]
        s = SUMMARY_RE.search(tail)
        if s and len(s.group(1).strip()) > SUMMARY_LIMIT:
            longs += 1
    return bad, longs


def run(root: Path, write: bool) -> tuple[int, list[str], list[str]]:
    """(違反の数, 違反の行, 数えただけの行)。"""
    facts, bad = load_facts(root)
    notes: list[str] = []
    seen: set[str] = set()
    long_total = 0

    for path in docs_files(root):
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(root)
        rs = regions(text)
        if BEGIN_RE.search(text) and len(rs) != len(BEGIN_RE.findall(text)):
            bad.append(f"{rel}: 機械の欄の終端({END_MARK})が無い")
        new = text
        for fid, s, e, body in reversed(rs):
            seen.add(fid)
            spec = facts.get(fid)
            if spec is None:
                bad.append(f"{rel}: 宣言に無い機械の欄: id={fid}({FACTS} に足すか、区画を消す)")
                continue
            out, err = render(root, spec)
            if err:
                bad.append(f"{rel}: id={fid}: {err}")
                continue
            if normalize(body) != normalize(out):
                if write:
                    new = new[:s] + "\n" + out + "\n" + new[e:]
                else:
                    bad.append(f"{rel}: id={fid}: 機械の欄が生成の結果と違う"
                               "(手で書いたか、埋め直していない)")
        if write and new != text:
            path.write_text(new, encoding="utf-8")
            notes.append(f"埋めた: {rel}")
        refbad, longs = scan_refs(root, path, text)
        bad.extend(refbad)
        long_total += longs

    unused = sorted(set(facts) - seen)
    if unused:
        notes.append(f"どの機械の欄からも使われていない宣言: {', '.join(unused)}"
                     "(数えるだけ。拒まない)")
    if long_total:
        notes.append(f"要旨が{SUMMARY_LIMIT}字を超えた参照: {long_total}件"
                     "(数えるだけ。写しへ戻り始めた印である)")
    return len(bad), bad, notes


def main(argv: list[str]) -> int:
    args = argv[1:]
    if "--selftest" in args:
        return selftest()
    if any(a in ("-h", "--help") for a in args):
        print(__doc__)
        return 0
    if len(args) != 1 or args[0] not in ("update", "check"):
        print(__doc__)
        return 2

    root = find_root(Path.cwd())
    write = args[0] == "update"
    n, bad, notes = run(root, write)
    print(f"## 事実の生成器({args[0]})")
    for line in notes:
        print(f"  --  {line}")
    if write:
        # 埋めた後に、参照の実在だけをもう一度見る(埋めても参照は直らない)
        n, bad, _ = run(root, False)
    for line in bad:
        print(f"  NG  {line}")
    if n:
        print(f"  違反 {n} 件")
        return 1
    print("  OK  機械の欄は生成の結果と一致し、参照先はすべて実在する")
    return 0


def selftest() -> int:
    import contextlib
    import io
    import os
    import tempfile

    previous = Path.cwd()

    def run_cli(*extra: str) -> tuple[int, str]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(["x", *extra])
        return code, buf.getvalue()

    def ck(label: str, cond: bool, got: str = "") -> None:
        if not cond:
            raise AssertionError(f"{label}: {got}")

    try:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".claude").mkdir()
            (root / "CLAUDE.md").write_text("x", encoding="utf-8")
            (root / "docs/01-requirements").mkdir(parents=True)
            (root / "docs/03-impl").mkdir(parents=True)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            os.chdir(root)

            ck("(a) 宣言も文書も無ければ 0", run_cli("check")[0] == 0)
            ck("(b) 引数なしは 2", run_cli()[0] == 2)
            ck("(b) 知らない引数は 2", run_cli("bogus")[0] == 2)

            for n in range(3):
                (root / f"tests/t{n}_test.py").write_text("x\n", encoding="utf-8")
            (root / "src/a.py").write_text("load_conf()\nload_conf()\n", encoding="utf-8")
            (root / "src/b.py").write_text(
                'DEFAULT = "/etc/x.conf"\nload_conf()\n', encoding="utf-8")
            (root / "docs/01-requirements/functional.md").write_text(
                "---\nid: fr\n---\n## 機能要件\n| ID | 要件 |\n|---|---|\n| FR-a-01 | あ |\n\nあと\n",
                encoding="utf-8")
            (root / FACTS).write_text(json.dumps({"facts": [
                {"id": "tests", "type": "count_files",
                 "args": {"glob": "tests/*_test.py"}, "format": "{n}本"},
                {"id": "callers", "type": "count_matches",
                 "args": {"glob": "src/*.py", "regex": r"load_conf\("}},
                {"id": "default", "type": "capture",
                 "args": {"file": "src/b.py", "regex": r'DEFAULT = "([^"]+)"'},
                 "format": "`{v}`"},
                {"id": "fr", "type": "mirror_table",
                 "args": {"file": "docs/01-requirements/functional.md",
                          "heading": "## 機能要件"}},
            ]}, ensure_ascii=False), encoding="utf-8")

            impl = root / "docs/03-impl/x.md"
            impl.write_text(
                "---\nid: impl-x\n---\n"
                "## 数\n"
                "<!-- BEGIN GENERATED: build-facts.py id=tests -->\n"
                "31本\n"
                "<!-- END GENERATED: build-facts.py -->\n"
                "<!-- BEGIN GENERATED: build-facts.py id=callers -->\n"
                "14\n"
                "<!-- END GENERATED: build-facts.py -->\n"
                "<!-- BEGIN GENERATED: build-facts.py id=default -->\n"
                "`/old/x.conf`\n"
                "<!-- END GENERATED: build-facts.py -->\n"
                "<!-- BEGIN GENERATED: build-facts.py id=fr -->\n"
                "| ID | 要件 |\n"
                "<!-- END GENERATED: build-facts.py -->\n",
                encoding="utf-8")

            code, out = run_cli("check")
            ck("(c) 古い写しを4件とも違反にする",
               code == 1 and out.count("機械の欄が生成の結果と違う") == 4, out)

            code, out = run_cli("update")
            ck("(d) update は 0 を返す", code == 0, out)
            body = impl.read_text(encoding="utf-8")
            ck("(d) count_files を埋めた", "3本" in body, body)
            ck("(d) count_matches を埋めた", "\n3\n" in body, body)
            ck("(d) capture を埋めた", "`/etc/x.conf`" in body, body)
            ck("(d) mirror_table を埋めた", "| FR-a-01 | あ |" in body, body)
            ck("(e) 埋めた後は差分ゼロ", run_cli("check")[0] == 0)
            before = impl.read_text(encoding="utf-8")
            run_cli("update")
            ck("(f) 2度目の update は1バイトも変えない",
               impl.read_text(encoding="utf-8") == before)

            # 宣言に無い区画は違反
            impl.write_text(body + "<!-- BEGIN GENERATED: build-facts.py id=ghost -->\n"
                                   "x\n<!-- END GENERATED: build-facts.py -->\n",
                            encoding="utf-8")
            code, out = run_cli("check")
            ck("(g) 宣言に無い機械の欄は違反", code == 1 and "宣言に無い機械の欄" in out, out)
            impl.write_text(body, encoding="utf-8")

            # 終端の印が無い区画
            impl.write_text(body + "<!-- BEGIN GENERATED: build-facts.py id=tests -->\n",
                            encoding="utf-8")
            code, out = run_cli("check")
            ck("(h) 終端の無い区画は違反", code == 1 and "終端" in out, out)
            impl.write_text(body, encoding="utf-8")

            # 参照の実在
            ref = root / "docs/03-impl/y.md"
            ref.write_text(
                "---\nid: impl-y\n---\n"
                "値は `docs/01-requirements/functional.md` の「## 機能要件」が正である。"
                "(要旨: 要件の一覧はあちらが持つ)\n", encoding="utf-8")
            ck("(i) 実在する参照は通る", run_cli("check")[0] == 0)
            ref.write_text(
                "値は `docs/01-requirements/functional.md` の「## 無い節」が正である。\n",
                encoding="utf-8")
            code, out = run_cli("check")
            ck("(j) 節が無い参照は違反", code == 1 and "参照先に節が無い" in out, out)
            ref.write_text("値は `docs/01-requirements/nope.md` の「## 機能要件」が正である。\n",
                           encoding="utf-8")
            code, out = run_cli("check")
            ck("(k) ファイルが無い参照は違反", code == 1 and "参照先のファイルが無い" in out, out)
            # 要旨の長さは数えるだけ
            long_summary = "あ" * (SUMMARY_LIMIT + 1)
            ref.write_text(
                "値は `docs/01-requirements/functional.md` の「## 機能要件」が正である。"
                f"(要旨: {long_summary})\n", encoding="utf-8")
            code, out = run_cli("check")
            ck("(l) 長い要旨は数えるだけで拒まない",
               code == 0 and f"要旨が{SUMMARY_LIMIT}字を超えた参照: 1件" in out, out)
            ref.unlink()

            # 壊れた宣言
            (root / FACTS).write_text("{", encoding="utf-8")
            code, out = run_cli("check")
            ck("(m) 壊れた宣言は違反", code == 1 and "読めない" in out, out)
    finally:
        os.chdir(previous)

    print("OK build-facts.py --selftest")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
