#!/usr/bin/env python3
"""各 index.md をフロントマターから再生成する。

index.md を手書きしてはならない(CLAUDE.md 原則10)。目次は必ず実ファイルのフロントマターから
機械的に作る。手書きの目次は必ず古くなり、「ある」と書いてあるものが無い状態を生む。

使い方:
    python3 .claude/scripts/build-index.py            # 全 index を再生成
    python3 .claude/scripts/build-index.py --check     # 差分があるか検査のみ(CI 用)
    python3 .claude/scripts/build-index.py --only-missing  # **まだ無い index だけ**作る
    python3 .claude/scripts/build-index.py relations   # 特定の対象だけ(下表の name)

`--only-missing` は `/setup` のためのものである。**既存の docs/ を1バイトも変えない**という
初期設定の約束と、既に在る index への追記・更新が食い違っていた(2026-09-13。C2-7)。
`--check` とは同時に指定できない(検査と生成は別の仕事である)。

機械の欄(手で保守する文書の中の、道具が丸ごと書く区画 — `conventions.md` §4)は次の印の
あいだだけを置き換える。印の外(フロントマター・手書きの前置き)は保持する。
ファイルが無い場合は最小の雛形を作って機械の欄を入れる。

    <!-- BEGIN GENERATED: build-index.py -->
    <!-- END GENERATED: build-index.py -->
    (旧終端 `<!-- END GENERATED -->` も読める)

終了コード: 0=成功(--check なら差分なし) 1=--check で差分あり 2=使い方・解析エラー
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

BEGIN = "<!-- BEGIN GENERATED: build-index.py -->"
END = "<!-- END GENERATED: build-index.py -->"
# **読むときは旧終端(ツール名なし)も受ける。** 1つのファイルに2つのツールが書く場面で
# 取り違えないよう終端にもツール名を入れたが、既存の index.md は旧形を持つ。両方受ければ
# **一度きりの差分すら出さずに移行できる**(KIT-generated-note-churns-every-artifact)。
# **`END_OURS` は「この道具の区画の終端」だけに当たる** ★ — 別の道具の終端
# (`<!-- END GENERATED: build-facts.py -->` など)には当たらない。
# 区画の同居は `conventions.md` §4 が認めているので、**他人の終端を自分のものとして
# 拾ってはならない**(2026-09-13。C2-8)。
END_OURS = re.compile(r"<!-- END GENERATED(?:: build-index\.py)? -->")
# 生成する内容にマーカーが混ざっていないかを見るときだけ、**どの道具の終端でも**拾う。
END_ANY = re.compile(r"<!-- END GENERATED(?:: [\w.-]+)? -->")

# name: (対象ディレクトリ, 出力する index, 走査パターン, 見出し, 列定義)
# 列定義は (列見出し, フロントマターのキー or 特殊キー) の並び。
# 特殊キー: "__name__" = ファイル名(リンク付き)
TARGETS: dict[str, dict] = {
    "relations": {
        "dir": "docs/03-impl/relations",
        "index": "docs/03-impl/relations/index.md",
        "glob": "MODULE-*.md",
        "title": "機能間連携仕様書 一覧",
        "columns": [
            ("ID", "__name__"),
            ("モジュール", "module"),
            ("種別", "kind"),
            ("同期", "sync"),
            ("呼び出し元", "callers"),
            ("呼び出す先", "callees"),
            ("概要", "summary"),
        ],
        "sort": ("module", "id"),
    },
    "impl": {
        "dir": "docs/03-impl",
        "index": "docs/03-impl/index.md",
        "glob": "**/*.md",
        "title": "03-impl 目次",
        "columns": [
            ("ファイル", "__name__"),
            ("version", "version"),
            ("更新", "updated"),
            ("概要", "summary"),
        ],
        # relations / contracts / tests / callgraphs は専用 index が持つ。
        # callgraphs/index.md は build-callgraphs.py の生成物なので、こちらは一切触らない。
        "exclude_dirs": ["relations", "contracts", "tests", "callgraphs"],
        # feature-graph.md は cluster-features.py の生成物(版も検証済み記録も持たない導出物)なので
        # 目次に載せない。**features.md は載せる** — 人間が合意した境界の定義であり、
        # relations 層と一体で検証済みになる(.claude/directions/features.md §3)。
        "exclude_files": ["feature-graph.md"],
        "sort": ("id",),
    },
    "tests": {
        "dir": "docs/03-impl/tests",
        "index": "docs/03-impl/tests/index.md",
        "glob": "*.md",
        "title": "テスト実装仕様 一覧",
        "columns": [
            ("ファイル", "__name__"),
            ("対象", "scope"),
            ("実装済み/未検証/テスト対象外", "__testcounts__"),
            ("version", "version"),
            ("更新", "updated"),
            ("概要", "summary"),
        ],
        "sort": ("id",),
    },
    "impl-contracts": {
        "dir": "docs/03-impl/contracts",
        "index": "docs/03-impl/contracts/index.md",
        "glob": "**/*.md",
        "title": "実装されている契約 一覧",
        "columns": [("ID", "__name__"), ("種別", "kind"), ("概要", "summary")],
        "sort": ("id",),
    },
    "design-contracts": {
        "dir": "docs/02-design/contracts",
        "index": "docs/02-design/contracts/index.md",
        "glob": "**/*.md",
        "title": "設計上の契約 一覧",
        "columns": [("ID", "__name__"), ("種別", "kind"), ("概要", "summary")],
        "sort": ("id",),
    },
    "requests-decisions": {
        "dir": "docs/00-requests/decisions",
        "index": "docs/00-requests/decisions/index.md",
        "glob": "*.md",
        "title": "要求レベルの決定事項 目次",
        "columns": [("ファイル", "__name__"), ("件数(決定/委任/要確認)", "__counts__"), ("概要", "summary")],
        "sort": ("id",),
    },
    "requirements-decisions": {
        "dir": "docs/01-requirements/decisions",
        "index": "docs/01-requirements/decisions/index.md",
        "glob": "*.md",
        "title": "要件レベルの決定事項 目次",
        "columns": [("ファイル", "__name__"), ("件数(決定/委任/要確認)", "__counts__"), ("概要", "summary")],
        "sort": ("id",),
    },
    "issues": {
        "dir": "docs/issues",
        "index": "docs/issues/index.md",
        "glob": "[0-9]*.md",
        "title": "課題 一覧(未タスク化 + 追跡中)",
        "columns": [
            ("ID", "__name__"),
            ("種別", "type"),
            ("重大度", "severity"),
            # 起点層 = 直しが始まる層。見つけた場所(found_in)ではない
            # (規範は .claude/directions/issues-pendings.md §1、検査は CS20)
            ("起点層", "origin_layer"),
            ("発見", "found"),
            ("関連", "related"),
            ("概要", "summary"),
        ],
        "sort": ("id",),
    },
    "feedbacks": {
        "dir": "docs/feedbacks",
        "index": "docs/feedbacks/index.md",
        "glob": "[0-9]*.md",
        "title": "気づき 一覧",
        "columns": [("ID", "__name__"), ("日付", "date"), ("概要", "summary")],
        "sort": ("id",),
    },
    "build-records": {
        "dir": "docs/build-records",
        "index": "docs/build-records/index.md",
        "glob": "*.md",
        "title": "構築記録 一覧",
        "columns": [
            ("slug", "slug"),
            ("状態", "state"),
            ("critical", "critical"),
            ("更新", "updated"),
            ("概要", "summary"),
        ],
        "sort": ("id",),
    },
}


def read_frontmatter(path: Path) -> dict[str, str]:
    """トップレベルの1行スカラーだけを拾う(この体系のフロントマターは1行主義)。"""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    if not text.startswith("---"):
        return {}
    out: dict[str, str] = {}
    for line in text.splitlines()[1:]:
        if line.rstrip() == "---":
            break
        if not line or line.startswith((" ", "\t", "#")):
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return out


def decision_counts(path: Path) -> str:
    """決定事項ファイルの 決定/委任/要確認 の件数を数える。"""
    try:
        body = path.read_text(encoding="utf-8")
    except OSError:
        return "-"
    n_dec = len(re.findall(r"区分:\s*決定", body))
    n_del = len(re.findall(r"区分:\s*委任", body))
    n_ask = len(re.findall(r"区分:\s*要確認", body))
    return f"{n_dec}/{n_del}/{n_ask}"


# 表の見出し行の目印。状態の3語と語頭が一致してしまう列名がここに来る。
HEADER_CELLS = {"状態", "テスト対象外とする理由", "テスト", "テストID", "対象", "レベル", "実装済み?"}


def strip_emphasis(cell: str) -> str:
    """セルから Markdown の強調と前後の空白を落とす。`**未検証(…)**` → `未検証(…)`。"""
    c = cell.strip()
    while len(c) > 4 and c.startswith(("**", "__")) and c.endswith(("**", "__")):
        c = c[2:-2].strip()
    return c.strip("*_ ")


def test_counts(path: Path) -> str:
    """テスト対応表の 状態 列を数える。

    状態列の語彙の正は .claude/directions/03-impl.md「tests/」である(4語 — 「実装済み」
    「未検証(テスト未実装)」「テスト対象外」と、退役の印の「廃止(<理由>)」)。
    進捗に数えるのは前の3語だけで、「廃止(...)」は母集団から外れる
    (02 の「適用外」は充足列の別語彙で、ここには現れない)。だから数えるだけで進捗が出る。

    **セルの強調(`**未検証(テスト未実装)**`)を落としてから見る。** 落とさないと
    `"**未検証…".startswith("未検証")` が False になり、**その行が1件も数えられない**。
    生成物の進捗が黙って 0 になるので、読み手は「未検証が無い」と読む
    (KIT-build-index-status-count-breaks-on-emphasis。実測で 4+1+1+1 行が消え、
    現行 SSOT でも「対象外 2 件」が 1 と表示されていた)。
    **表の見出し行も数えない** — 「テスト対象外とする理由」のような列名が語頭一致してしまう。
    """
    try:
        body = path.read_text(encoding="utf-8")
    except OSError:
        return "-"
    done = todo = skip = 0
    for line in body.splitlines():
        line = line.strip()
        # 表の行だけを数える。見出し・コメント・説明文に出てくる同じ語を数えない
        # (数えると、雛形の注意書きだけで「未検証 4 件」のような嘘が出る)。
        if not line.startswith("|") or set(line) <= set("|- :"):
            continue
        cells = [strip_emphasis(c) for c in line.strip("|").split("|")]
        if any(c in HEADER_CELLS for c in cells):
            continue                            # 表の見出し行
        for cell in cells:
            if cell.startswith("実装済み"):
                done += 1
            elif cell.startswith("未検証"):
                todo += 1
            elif cell.startswith("テスト対象外"):
                skip += 1
            else:
                continue
            break   # 1行につき状態は1つ
    if not (done or todo or skip):
        return "-"
    return f"{done} / **{todo}** / {skip}" if todo else f"{done} / 0 / {skip}"


def cell(value: str) -> str:
    """表のセルとして安全な1行にする。"""
    if not value:
        return "-"
    return value.replace("|", "\\|").replace("\n", " ").strip() or "-"


def collect(root: Path, name: str, cfg: dict) -> list[tuple[Path, dict]]:
    base = root / cfg["dir"]
    if not base.is_dir():
        return []
    index_path = (root / cfg["index"]).resolve()
    exclude_dirs = set(cfg.get("exclude_dirs", []))
    exclude_files = set(cfg.get("exclude_files", []))
    rows: list[tuple[Path, dict]] = []
    for path in sorted(base.glob(cfg["glob"])):
        if not path.is_file() or path.suffix != ".md":
            continue
        if path.resolve() == index_path or path.name == "index.md":
            continue
        rel_parts = path.relative_to(base).parts
        if rel_parts and rel_parts[0] in exclude_dirs:
            continue
        if path.name in exclude_files:
            continue
        fm = read_frontmatter(path)
        fm.setdefault("id", path.stem)
        rows.append((path, fm))
    key = cfg.get("sort", ("id",))
    rows.sort(key=lambda r: tuple(r[1].get(k, "") for k in key))
    return rows


def render(root: Path, cfg: dict, rows: list[tuple[Path, dict]]) -> str:
    index_dir = (root / cfg["index"]).parent
    cols = cfg["columns"]
    lines = [f"| {' | '.join(c[0] for c in cols)} |",
             f"|{'|'.join('---' for _ in cols)}|"]
    for path, fm in rows:
        cells = []
        for _, key in cols:
            if key == "__name__":
                try:
                    link = path.relative_to(index_dir).as_posix()
                except ValueError:
                    link = path.relative_to(root).as_posix()
                label = fm.get("id") or path.stem
                cells.append(f"[{label}]({link})")
            elif key == "__counts__":
                cells.append(decision_counts(path))
            elif key == "__testcounts__":
                cells.append(test_counts(path))
            else:
                cells.append(cell(fm.get(key, "")))
        lines.append(f"| {' | '.join(cells)} |")
    if not rows:
        lines.append(f"|{'|'.join(' (なし) ' if i == 0 else ' - ' for i in range(len(cols)))}|")
    lines.append("")
    lines.append(f"件数: {len(rows)}")
    return "\n".join(lines)


def write_index(root: Path, cfg: dict, block: str, check_only: bool) -> tuple[bool, str]:
    """(変更あり?, メッセージ) を返す。"""
    path = root / cfg["index"]
    # 中身にマーカーが混ざると切り出しが壊れる。黙って捨てるより止める(§3-4)
    if BEGIN in block or END_ANY.search(block):
        raise SystemExit(f"エラー: 生成する内容にマーカーが混ざっている: {cfg['index']}")
    generated = f"{BEGIN}\n\n{block}\n\n{END}"
    if path.is_file():
        old = path.read_text(encoding="utf-8")
        if BEGIN in old:
            head, rest = old.split(BEGIN, 1)
            # **終端は BEGIN より後ろで、自分の区画のものだけを探す** ★ — 文書の頭から
            # 探すと、前に居る別の道具の区画の終端を拾い、それが BEGIN の後ろには
            # 無いので分割に失敗して例外で止まる(2026-09-13。C2-8)。
            m_end = END_OURS.search(rest)
            if m_end is None:
                raise SystemExit(
                    f"エラー: 機械の欄の終端が無い: {cfg['index']} — "
                    f"BEGIN の後ろに `{END}` を置くこと"
                    "(旧終端 `<!-- END GENERATED -->` も読む)")
            new = f"{head}{generated}{rest[m_end.end():]}"
        else:
            new = old.rstrip() + "\n\n" + generated + "\n"
    else:
        new = f"# {cfg['title']}\n\n<!-- このファイルは build-index.py が生成する。手書きしない。 -->\n\n{generated}\n"
    # **終端の形だけの違いは「変更」ではない。** 終端にツール名を入れた移行で、中身が
    # 1バイトも変わっていない index が一斉に「差分あり」になった(実測: 1件 → 10件)。
    # 正規化して比べれば移行の churn はゼロで、次に中身が動いたとき自然に新形へ移る。
    # **正規化するのは自分の終端だけである** — 他の道具の区画まで正規化して比べると、
    # あちらの終端が変わった差分を「変更なし」と読む(C2-8)。
    current = path.read_text(encoding="utf-8") if path.is_file() else None
    if current is not None and END_OURS.sub(END, new) == END_OURS.sub(END, current):
        return False, f"変更なし: {cfg['index']}"
    if not check_only:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new, encoding="utf-8")
    return True, f"{'差分あり' if check_only else '更新'}: {cfg['index']}"


def find_root(start: Path) -> Path:
    cur = start.resolve()
    for cand in [cur, *cur.parents]:
        if (cand / "CLAUDE.md").is_file() and (cand / ".claude").is_dir():
            return cand
    return cur


def main(argv: list[str]) -> int:
    if any(a in ("-h", "--help") for a in argv[1:]):
        print(__doc__)   # 明示要求は 0。使い方エラーの 2 と区別する(tools-readme §2)
        return 0
    flags = {a for a in argv[1:] if a.startswith("--")}
    names = [a for a in argv[1:] if not a.startswith("--")]
    if flags - {"--check", "--only-missing"}:
        print(__doc__)
        return 2
    if {"--check", "--only-missing"} <= flags:
        print("エラー: --check と --only-missing は同時に指定できない")
        return 2
    unknown = [n for n in names if n not in TARGETS]
    if unknown:
        print(f"エラー: 未知の対象: {', '.join(unknown)}")
        print(f"指定できるのは: {', '.join(TARGETS)}")
        return 2

    root = find_root(Path.cwd())
    check_only = "--check" in flags
    only_missing = "--only-missing" in flags
    selected = names or list(TARGETS)
    changed = 0

    print("## index 再生成"
          + ("(--check: 検査のみ)" if check_only else "")
          + ("(--only-missing: まだ無いものだけ)" if only_missing else ""))
    for name in selected:
        cfg = TARGETS[name]
        if not (root / cfg["dir"]).is_dir():
            print(f"  skip {name} — {cfg['dir']} が無い")
            continue
        # **既に在る index には触らない。** 初期設定の「既存の docs/ を1バイトも変えない」を
        # 守るための口である(C2-7)。古いままの index は後続の通常作業が直す。
        if only_missing and (root / cfg["index"]).is_file():
            print(f"  skip {name} — {cfg['index']} は既に在る(--only-missing)")
            continue
        rows = collect(root, name, cfg)
        did, msg = write_index(root, cfg, render(root, cfg, rows), check_only)
        changed += 1 if did else 0
        print(f"  {msg} ({len(rows)} 件)")

    if check_only and changed:
        print(f"\n→ {changed} 件の index が実ファイルと食い違っている。build-index.py を実行すること。")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
