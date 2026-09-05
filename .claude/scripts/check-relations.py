#!/usr/bin/env python3
"""機能間連携仕様書 (docs/03-impl/relations/) の整合を機械検査する。

この検査が存在する理由: 機能にまたがる不整合は「読んで気づく」ことが最も苦手な種類の欠陥である。
呼び出し関係の対称性・参照先の実在・impl パスの実在は、宣言ではなく検査で担保する。
**機能表(docs/03-impl/features.md)との 1:1(FT3)はここでは検査しない** — その検査IDを実装する
のは callgraph-check.py 1本だけである(同じ規則を二度実装しない。inspection-21 V-2)。
仕様は .claude/directions/relations.md と features.md が正。

使い方:
    python3 .claude/scripts/check-relations.py
    python3 .claude/scripts/check-relations.py --warn-only   # 検出しても終了コード 0

終了コード: 0=合格 1=エラーあり 2=解析・使い方エラー
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# 機能表のパーサは cgx と共有する(inspection-17 判断3 — 2実装が食い違うと、片方だけが
# 「棄却した候補辺」の表を機能IDとして誤収穫する、の型の欠陥が再発する)。
from cgx.features import parse_features  # noqa: E402

RELATIONS_DIR = "docs/03-impl/relations"
FEATURES_PATH = "docs/03-impl/features.md"
DESIGN_SYSTEM = "docs/02-design/system.md"
DESIGN_DIR = "docs/02-design"
REQUIREMENTS_DIR = "docs/01-requirements"
IMPL_CONTRACTS_DIR = "docs/03-impl/contracts"

REQUIRED = ["id", "module", "kind", "sync", "impl", "callers", "callees",
            "contracts", "design", "requirements", "tests", "updated", "summary"]
KINDS = {"user-action", "event", "function-call", "rest-api", "tool", "other"}
SYNCS = {"sync", "async"}
EXTERNAL_PREFIXES = ("USER-", "EVENT-", "SCHEDULER-", "EXTERNAL-")
NONE_WORDS = {"なし", "none", "-", ""}

ID_RE = re.compile(r"^MODULE-[a-z0-9]+(-[a-z0-9]+)*$")


def read_text_safe(path: Path) -> str | None:
    """UTF-8 で読めなければ None。**落とさない** — 1ファイルの文字化けで検査結果が
    1件も出ない状態(fail-open と見分けが付かない)を作らないため。"""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def read_frontmatter(path: Path) -> tuple[dict[str, str], list[str]]:
    """(1行スカラーの辞書, 解析上の問題) を返す。"""
    problems: list[str] = []
    text = read_text_safe(path)
    if text is None:
        return {}, ["UTF-8 として読めない(検査できていない。**未検査は合格ではない**)"]
    if not text.startswith("---"):
        return {}, ["フロントマターがない"]
    fm: dict[str, str] = {}
    closed = False
    for line in text.splitlines()[1:]:
        if line.rstrip() == "---":
            closed = True
            break
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith((" ", "\t")):
            problems.append(f"1行主義に反する継続行がある: {line.strip()[:40]}")
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
        if not m:
            problems.append(f"解釈できない行: {line.strip()[:40]}")
            continue
        fm[m.group(1)] = m.group(2).strip()
    if not closed:
        problems.append("フロントマターが閉じていない")
    return fm, problems


def items(value: str) -> list[str]:
    """カンマ区切りの1行値をリストにする。「なし」等は空リスト。"""
    v = value.strip()
    if v.lower() in NONE_WORDS or v.startswith("なし"):
        return []
    return [p.strip() for p in v.split(",") if p.strip()]


def scan_ids(root: Path, rel_dir: str, pattern: re.Pattern[str],
             unreadable: list[str] | None = None) -> set[str]:
    """ディレクトリ配下の全 .md を grep して ID 集合を作る。

    **UTF-8 として読めないファイルで異常終了してはならない。** 落ちると検査結果が1件も出ず、
    「検査して問題なし」と区別が付かない(macOS の `._*` などが実際に混ざる。
    `KIT-check-relations-crashes-on-undecodable-files`)。読み飛ばした分は呼び出し元へ返し、
    **一覧に出して非ゼロ終了する** — 黙って飛ばすのは fail-open である。
    """
    found: set[str] = set()
    base = root / rel_dir
    if not base.is_dir():
        return found
    for path in sorted(base.rglob("*.md")):
        try:
            found.update(pattern.findall(path.read_text(encoding="utf-8")))
        except OSError:
            continue
        except UnicodeDecodeError:
            if unreadable is not None:
                unreadable.append(path.relative_to(root).as_posix())
    return found


def module_ids(root: Path) -> set[str]:
    """「## モジュール分割定義」節の表の1列目だけを定義として読む。

    ファイル全文の文字列 grep だと、却下した分割案や経緯の記述に現れる MOD-x まで
    「定義済み」に数え、module 実在検査が素通りする(inspection-17 M-22)。
    節スコープは read_feature_ids(cgx.features — 判断3)と同じ規則。見出しは原則9が守る。
    """
    path = root / DESIGN_SYSTEM
    if not path.is_file():
        return set()
    found: set[str] = set()
    in_section = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("#"):
            in_section = line.lstrip().lstrip("#").strip() == "モジュール分割定義"
            continue
        if not in_section:
            continue
        s = line.strip()
        if not s.startswith("|"):
            continue
        first = s.strip("|").split("|", 1)[0].strip().strip("`")
        m = re.fullmatch(r"MOD-[a-z0-9][a-z0-9-]*", first)
        if m:
            found.add(m.group(0))
    return found


def read_feature_ids(root: Path) -> tuple[set[str] | None, str]:
    """機能表の機能ID集合を返す。無ければ (None, 注記)。

    機能表を必須にはしない — 導入途中のリポジトリで検査が止まると、
    直したい他の不整合まで見えなくなる。ただし**無いことは必ず報告する**。
    """
    path = root / FEATURES_PATH
    if not path.is_file():
        return None, (f"注意: {FEATURES_PATH} が無いため機能表の行を数えられない。"
                      "`propose-features.py` で候補を出せる")
    text = read_text_safe(path)
    if text is None:
        return None, (f"注意: {FEATURES_PATH} が UTF-8 で読めないため機能表の行を数えられない"
                      "(**数えられないことは合格ではない**)")
    # 「## 機能一覧」の表だけを読む(cgx.features.parse_features — 判断3)。ファイル全体の
    # `|` 行を拾うと「棄却した候補辺」の表(1列目が `MODULE-a → MODULE-b`)まで機能IDに
    # 収穫し、規範どおりの棄却記録が偽エラーになる。書式エラーの裁定は cluster-features の
    # 仕事なので、ここでは ID の集合だけを使う。
    features, _errors = parse_features(text)
    ids = {f["id"] for f in features if f["id"].startswith("MODULE-")}
    if not ids:
        return None, (f"注意: {FEATURES_PATH} に機能の行が無い")
    return ids, ""


def main(argv: list[str]) -> int:
    if any(a in ("-h", "--help") for a in argv[1:]):
        print(__doc__)   # 明示要求は 0。使い方エラーの 2 と区別する(tools-readme §2)
        return 0
    flags = {a for a in argv[1:] if a.startswith("--")}
    if flags - {"--warn-only"} or [a for a in argv[1:] if not a.startswith("--")]:
        print(__doc__)
        return 2

    root = Path.cwd().resolve()
    for cand in [root, *root.parents]:
        if (cand / "CLAUDE.md").is_file() and (cand / ".claude").is_dir():
            root = cand
            break

    base = root / RELATIONS_DIR
    files = sorted(p for p in base.glob("MODULE-*.md") if p.is_file()) if base.is_dir() else []
    if not files:
        # **relations が0件でも、機能表に行が在れば「検査対象が空」であって合格ではない**
        # (母集団の片側が全部無い。1:1 そのものの裁定は callgraph-check.py の FT3 が持つ —
        # inspection-21 V-2)。ここで 0 を返すと「見ていない」と「問題なし」が同じになり、
        # verify 系の前提と /retrofit §0 の前提が空振りする。
        # 機能表も空・不在なら、それは導入途中の正当な状態なので従来どおり 0
        # (グリーンフィールド特例の正は .claude/directions/03-impl.md の一覧表)。
        why = f"{RELATIONS_DIR} が無い" if not base.is_dir() \
            else f"{RELATIONS_DIR} に MODULE-*.md が1件も無い"
        feature_ids, note = read_feature_ids(root)
        if feature_ids:
            print(f"NG    {why}。しかし機能表には機能が {len(feature_ids)} 件在る"
                  " — 検査対象が空なのに母集団が空でない。全件が未記述である:")
            for fid in sorted(feature_ids):
                print(f"  NG    {fid} — 対応する {RELATIONS_DIR}/{fid}.md が無い")
            print("\n→ `/relations <対象> --apply` で書くか、機能表の行を消すこと。")
            return 0 if "--warn-only" in flags else 1
        print(f"{why}。機能間連携仕様書が未作成"
              "(`/relations all --apply --bootstrap` が最初の一歩)。")
        if note:
            print(f"  {note}")
        return 0

    docs: dict[str, dict[str, str]] = {}
    errors: list[tuple[str, str]] = []   # (ファイル, 内容)
    warnings: list[tuple[str, str]] = []

    known_modules = module_ids(root)
    unreadable: list[str] = []
    known_contracts = scan_ids(root, IMPL_CONTRACTS_DIR, re.compile(r"CTR-[a-z0-9][a-z0-9-]*"),
                               unreadable)
    known_design = scan_ids(root, DESIGN_DIR, re.compile(r"DSN-[a-z0-9][a-z0-9-]*-\d+"), unreadable)
    known_reqs = scan_ids(root, REQUIREMENTS_DIR,
                          re.compile(r"(?:FR|NFR|UC|SR)-[a-z0-9-]*\d+"), unreadable)
    # 読み飛ばしは**必ず見えるところに出す**。ID の集合が欠けたまま照合すると
    # 「参照先が実在しない」の偽陽性になりうるので、合格扱いにはしない
    for rel_ in sorted(set(unreadable)):
        errors.append((rel_, "UTF-8 として読めないので走査から外した"
                             "(ID の集合が欠けている可能性がある)"))

    # --- 1st pass: 単体の妥当性 -------------------------------------------------
    for path in files:
        rel = path.relative_to(root).as_posix()
        fm, problems = read_frontmatter(path)
        for p in problems:
            errors.append((rel, p))
        for key in REQUIRED:
            if key not in fm:
                errors.append((rel, f"必須項目 `{key}` が無い"))
            elif not fm[key].strip():
                errors.append((rel, f"必須項目 `{key}` が空(該当なしなら「なし」と書く)"))

        doc_id = fm.get("id", "")
        if doc_id != path.stem:
            errors.append((rel, f"id `{doc_id}` がファイル名 `{path.stem}` と一致しない"))
        if doc_id and not ID_RE.match(doc_id):
            errors.append((rel, f"id の形式が不正: `{doc_id}`(MODULE-<kebab>)"))
        if doc_id in docs:
            errors.append((rel, f"id が重複している: `{doc_id}`"))
        if doc_id:
            docs[doc_id] = fm

        kind = fm.get("kind", "")
        if kind and kind not in KINDS:
            errors.append((rel, f"kind が不正: `{kind}`(許可: {'/'.join(sorted(KINDS))})"))
        sync = fm.get("sync", "")
        if sync and sync not in SYNCS:
            errors.append((rel, f"sync が不正: `{sync}`(sync|async)"))

        module = fm.get("module", "")
        if module and known_modules and module not in known_modules:
            errors.append((rel, f"module `{module}` が 02-design/system.md のモジュール分割定義に無い"))

        for spec in items(fm.get("impl", "")):
            if "::" not in spec and ":" in spec:
                errors.append((rel, f"impl の区切りが `:` になっている: `{spec}`"
                                    "(`path::symbol` が正。callgraphs のシンボルIDと同一表記にする)"))
            file_part = spec.split("::", 1)[0].strip()
            if not (root / file_part).exists():
                errors.append((rel, f"impl のパスが存在しない: `{file_part}`"))

        for ctr in items(fm.get("contracts", "")):
            if known_contracts and ctr not in known_contracts:
                errors.append((rel, f"contracts `{ctr}` が {IMPL_CONTRACTS_DIR} に無い"))
        for dsn in items(fm.get("design", "")):
            if known_design and dsn not in known_design:
                errors.append((rel, f"design `{dsn}` が 02-design に無い"))
        for req in items(fm.get("requirements", "")):
            if known_reqs and req not in known_reqs:
                errors.append((rel, f"requirements `{req}` が 01-requirements に無い"))

        if fm.get("tests", "").strip() in NONE_WORDS:
            errors.append((rel, "tests が空。テストが無いなら「なし(未実装)」と書く"))

        # `callees` ⇄ 本文の `### <ID>` 節は **1:1** である。
        #
        # **0個(欠落)も2個以上(重複)も、これまで機械では捕まらなかった。** 言及の有無だけを
        # 見ていたので、`callees` に ID があり本文のどこかに別の形で出ていれば WARN すら出ない。
        # 実測(2026-08-05、旧・変更指示の反映):入れ子の見出しを `sections:` に併記した結果、
        # **同じ節が逐語で2箇所に現れる**事故が2件、`### 節` そのものが無いのが2件あり、
        # 4件とも独立レビューが見つけて機械は1件も検出しなかった。
        # 重複は片方だけが更新されて乖離するので、**原則2 の担保は 1:1 に依存している**。
        body = read_text_safe(path)
        if body is None:
            continue                       # 上の read_frontmatter が既にエラーとして挙げている
        text = body.split("---", 2)[-1]
        for callee in items(fm.get("callees", "")):
            n = len(re.findall(r'^#{2,4}\s+`?' + re.escape(callee) + r'`?\s*$', text, re.M))
            if n == 0:
                if callee not in text:
                    warnings.append((rel, f"callees の `{callee}` が本文「連携先と連携内容」に書かれていない"))
                else:
                    warnings.append((rel, f"callees の `{callee}` は本文に出てくるが、"
                                          f"見出し(`### {callee}`)になっていない"))
            elif n > 1:
                errors.append((rel, f"callees の `{callee}` の節が本文に {n} 個ある"
                                    "(反映の二重挿入。どちらが最新か決められない)"))

    # --- 2nd pass: グラフの整合 -------------------------------------------------
    def valid_ref(ref: str) -> bool:
        return ref in docs or ref.startswith(EXTERNAL_PREFIXES)

    for doc_id, fm in docs.items():
        rel = f"{RELATIONS_DIR}/{doc_id}.md"
        callers = items(fm.get("callers", ""))
        callees = items(fm.get("callees", ""))

        for ref in callers + callees:
            if not valid_ref(ref):
                errors.append((rel, f"参照先 `{ref}` が実在せず、外部接頭辞"
                                    f"({'/'.join(EXTERNAL_PREFIXES)})でもない"))
        if doc_id in callers or doc_id in callees:
            errors.append((rel, "自分自身を callers/callees に含めている"))

        # 対称性: A.callees ∋ B ⟺ B.callers ∋ A
        for callee in callees:
            if callee in docs and doc_id not in items(docs[callee].get("callers", "")):
                errors.append((rel, f"非対称: `{callee}` の callers に `{doc_id}` が無い"))
        for caller in callers:
            if caller in docs and doc_id not in items(docs[caller].get("callees", "")):
                errors.append((rel, f"非対称: `{caller}` の callees に `{doc_id}` が無い"))

        if fm.get("kind") == "function-call" and not callers:
            errors.append((rel, "kind: function-call だが callers が空(到達不能コードの疑い)"))

    # --- 報告 -------------------------------------------------------------------
    # 機能表との 1:1(FT3)はここでは見ない。その検査IDの実装は callgraph-check.py 1本であり、
    # このスクリプトを走らせる3つのスキルはどれも callgraph-check.py を併走させる
    # (inspection-21 V-2 — 同じ規則を二度実装すると、片方だけが直されて黙って食い違う)。
    print(f"## 機能間連携仕様書の検査: {len(files)} ファイル / {len(docs)} ID")
    for label, coverage in (
        ("モジュール定義", known_modules), ("契約", known_contracts),
        ("設計ID", known_design), ("要件ID", known_reqs),
    ):
        if not coverage:
            print(f"  注意: {label} を1件も検出できなかったため、その参照検査はスキップした")

    if warnings:
        print(f"\n### 警告 {len(warnings)} 件")
        for rel, msg in warnings:
            print(f"  WARN  {rel} — {msg}")
    if errors:
        print(f"\n### エラー {len(errors)} 件")
        for rel, msg in errors:
            print(f"  NG    {rel} — {msg}")
        print("\n→ 機能間連携仕様書はコードと 1:1 でなければならない(CLAUDE.md 原則2)。")
        print("  自分で正解を決めず、実装と 02-design のどちらが正かを判断できない項目は人間に問うこと。")
        return 0 if "--warn-only" in flags else 1

    print("\n合格: 対称性・参照実在・impl パス・必須項目すべて問題なし。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
