#!/usr/bin/env python3
"""コードのエントリポイントと機能間連携仕様書の網羅を突き合わせる。

check-relations.py が「仕様ドキュメント集合の内部整合」を見るのに対し、こちらは
**コードとの網羅性**を見る。03-impl はコードの合わせ鏡なので、片側にしか無いものは全部指摘。

  未記載: コードにエントリポイントがあるのに、それを impl に含む MODULE-* が無い
  古い記述: MODULE-* の impl が指すファイルが存在しない
  未参照: MODULE-* の impl が指すファイルは在るが、そこにエントリポイント候補が無い(要確認)

使い方:
    python3 .claude/scripts/relations-coverage.py               # リポジトリ全体
    python3 .claude/scripts/relations-coverage.py src/api        # 範囲を絞る
    python3 .claude/scripts/relations-coverage.py --format json
    python3 .claude/scripts/relations-coverage.py --warn-only    # 検出しても終了コード 0

終了コード: 0=網羅されている 1=未記載または古い記述がある 2=使い方・設定エラー
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from scan_entrypoints import find_root, load_config, scan  # type: ignore
except ImportError:                                            # ファイル名がハイフンのため
    import importlib.util
    _spec = importlib.util.spec_from_file_location(
        "scan_entrypoints", Path(__file__).resolve().parent / "scan-entrypoints.py")
    _mod = importlib.util.module_from_spec(_spec)               # type: ignore
    _spec.loader.exec_module(_mod)                              # type: ignore
    find_root, load_config, scan = _mod.find_root, _mod.load_config, _mod.scan

RELATIONS_DIR = "docs/03-impl/relations"


def read_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    fm: dict[str, str] = {}
    for line in text.splitlines()[1:]:
        if line.rstrip() == "---":
            break
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip()
    return fm


def impl_entries(value: str) -> list[tuple[str, str]]:
    """`path::symbol, path::symbol` を [(path, symbol)] にする。symbol 省略可。"""
    out = []
    for part in value.split(","):
        part = part.strip()
        if not part or part.startswith("なし"):
            continue
        if "::" in part:
            p, s = part.split("::", 1)
            out.append((p.strip(), s.strip()))
        else:
            out.append((part, ""))
    return out


def main(argv: list[str]) -> int:
    if any(a in ("-h", "--help") for a in argv[1:]):
        print(__doc__)   # 明示要求は 0。使い方エラーの 2 と区別する(tools-readme §2)
        return 0
    # **argv を1回だけ歩いて、値と位置引数を同時に確定する。**
    # 2回に分けて `--` の有無で振り分けると `--format json` の `json` が位置引数側に落ち、
    # 走査対象パスとして食われる(`エラー: 対象が存在しない: json`)。
    # 使い方欄(:14)はスペース区切りで書いてあるので、そのとおり打つと必ず失敗していた
    # (KIT-two-scripts-accept-only-the-equals-form)。
    VALUED = {"--format"}
    args, flags, i = [], {}, 1
    while i < len(argv):
        a = argv[i]
        if a in VALUED and i + 1 < len(argv):
            flags[a] = argv[i + 1]; i += 2; continue      # 値を argv から消費する
        if a.startswith("--") and "=" in a:
            k, v = a.split("=", 1); flags[k] = v; i += 1; continue
        if a.startswith("--"):
            flags[a] = True; i += 1; continue
        args.append(a); i += 1
    fmt = flags.get("--format", "table")
    if fmt is True:
        fmt = "json"                                       # `--format` 単独は従来どおり json
    if set(flags) - {"--warn-only", "--format"} or fmt not in {"table", "json"} or len(args) > 1:
        print(__doc__)
        return 2

    root = find_root(Path.cwd())
    scope = (root / args[0]).resolve() if args else root
    if not scope.exists():
        print(f"エラー: 対象が存在しない: {args[0]}")
        return 2

    rel_dir = root / RELATIONS_DIR
    docs: dict[str, dict] = {}
    if rel_dir.is_dir():
        for path in sorted(rel_dir.glob("MODULE-*.md")):
            fm = read_frontmatter(path)
            docs[fm.get("id", path.stem)] = {
                "impl": impl_entries(fm.get("impl", "")),
                "module": fm.get("module", ""),
                "kind": fm.get("kind", ""),
                "summary": fm.get("summary", ""),
            }

    # 逆引き索引: ファイル -> [(MODULE-ID, symbol)]
    by_file: dict[str, list[tuple[str, str]]] = {}
    missing_files: list[tuple[str, str]] = []
    for mid, d in docs.items():
        for p, s in d["impl"]:
            by_file.setdefault(p, []).append((mid, s))
            if not (root / p).exists():
                missing_files.append((mid, p))

    cfg = load_config(root)
    hits = scan(root, scope, cfg, include_tests=False, kinds=None)

    uncovered: list[dict] = []
    covered: list[dict] = []
    for h in hits:
        owners = by_file.get(h["path"], [])
        if not owners:
            uncovered.append({**h, "reason": "このファイルを impl に含む MODULE-* が無い"})
            continue
        symbols = {s for _, s in owners if s}
        # scan 側は symbol(コードの識別子)と label(ルートパス等)の両方を持つ。
        # relations の impl が書くのは通常 symbol だが、ルート定義だけで関数名が取れない
        # 言語もあるので、**どちらか一方でも一致すれば記載ありとみなす**。
        candidates = {h.get("symbol", ""), h.get("label", "")} - {"", "(不明)"}
        if symbols and candidates and not (candidates & symbols):
            uncovered.append({**h, "reason":
                              f"ファイルは {', '.join(m for m, _ in owners)} が持つが、"
                              f"`{'` / `'.join(sorted(candidates))}` のどれも impl に無い"})
        else:
            covered.append({**h, "owners": [m for m, _ in owners]})

    # 「要確認」は本来エントリポイントであるべき kind だけに出す。
    # kind: function-call は他の機能から呼ばれる内部連携なので、エントリポイントの
    # パターンに当たらないのが正常であり、ここに出すと大量の雑音になる。
    ENTRY_KINDS = {"user-action", "event", "rest-api", "tool"}
    scanned_files = {h["path"] for h in hits}
    unreferenced = [
        (mid, p) for mid, d in docs.items() for p, _ in d["impl"]
        if d["kind"] in ENTRY_KINDS
        and (root / p).exists() and p not in scanned_files
        and (scope == root or str((root / p).resolve()).startswith(str(scope)))
    ]

    if fmt == "json":
        print(json.dumps({
            "uncovered": uncovered, "missing_files": missing_files,
            "unreferenced": unreferenced, "covered_count": len(covered),
            "relations_count": len(docs),
        }, ensure_ascii=False, indent=2))
        # --warn-only は table と json で同じに効く(inspection-17 M-17)
        if "--warn-only" in flags:
            return 0
        return 0 if not uncovered and not missing_files else 1

    target = scope.relative_to(root) if scope != root else "(リポジトリ全体)"
    print(f"## 網羅性の突き合わせ: {target}")
    print(f"機能間連携仕様書 {len(docs)} 本 / エントリポイント候補 {len(hits)} 件 "
          f"(記載あり {len(covered)} / 未記載 {len(uncovered)})")

    if not docs:
        print("\n機能間連携仕様書が1本も無い。ブラウンフィールド導入なら `/relations all --apply --bootstrap` が最初の一歩。")

    if uncovered:
        print(f"\n### 未記載 {len(uncovered)} 件(コードにあるが仕様ドキュメントに無い)")
        print("| kind | 場所 | シンボル | 理由 |")
        print("|---|---|---|---|")
        for h in uncovered:
            print(f"| {h['kind']} | `{h['path']}:{h['line']}` | `{h['symbol']}` | {h['reason']} |")

    if missing_files:
        print(f"\n### 古い記述 {len(missing_files)} 件(impl のパスが存在しない)")
        print("| MODULE-ID | 存在しないパス |")
        print("|---|---|")
        for mid, p in missing_files:
            print(f"| {mid} | `{p}` |")

    if unreferenced:
        print(f"\n### 要確認 {len(unreferenced)} 件(impl のファイルにエントリポイント候補が無い)")
        print("パターン未対応か、実質的な機能ではない可能性がある。**削ってよいかを自分で決めない。**")
        print("| MODULE-ID | パス |")
        print("|---|---|")
        for mid, p in unreferenced:
            print(f"| {mid} | `{p}` |")

    if not uncovered and not missing_files:
        print("\n合格: 検出できたエントリポイントはすべて機能間連携仕様書に記載されている。")
        print("(パターンが覆っていないスタックは検出できない。"
              "`scan-entrypoints.py` の候補が 0 件の領域は手で確認すること。)")
        return 0

    print("\n→ 未記載は 03-impl の欠落、古い記述はコードとの乖離である(CLAUDE.md 原則2)。")
    print("  どちらが正かを自分で決めず、判断できないものは人間に問うこと。")
    return 0 if "--warn-only" in flags else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
