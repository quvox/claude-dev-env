#!/usr/bin/env python3
"""機能間連携グラフへの問い合わせ。コードを読まずに波及を出すための道具。

なぜあるか: 「この関数を変えると何が壊れるか」を調べるためにコードを探し回るのが、コンテキストを
食い潰して精度を落とす主因だった。呼び出し関係は既に machine-readable なので、grep ではなく
グラフとして問い合わせる。

使い方:
    python3 .claude/scripts/relations-query.py --list [--module MOD-auth] [--kind rest-api]
    python3 .claude/scripts/relations-query.py --callers MODULE-auth-login      # 直接の呼び出し元
    python3 .claude/scripts/relations-query.py --callees MODULE-auth-login      # 直接の呼び出し先
    python3 .claude/scripts/relations-query.py --upstream MODULE-x [--depth 3]  # 推移的な呼び出し元
    python3 .claude/scripts/relations-query.py --downstream MODULE-x [--depth 3]
    python3 .claude/scripts/relations-query.py --impact src/auth.py             # ★波及
    python3 .claude/scripts/relations-query.py --path MODULE-a MODULE-b         # 呼び出し経路
    python3 .claude/scripts/relations-query.py --graph [--module MOD-auth]      # Mermaid
    python3 .claude/scripts/relations-query.py --health                         # 構造の健全性
    python3 .claude/scripts/relations-query.py --requirement FR-auth-01         # 要件→実装

共通オプション: --format json / --depth N(既定 3)
終了コード: 0=成功 2=使い方・解析エラー
"""

from __future__ import annotations

import json
import re
import sys
from collections import deque
from pathlib import Path

RELATIONS_DIR = "docs/03-impl/relations"
NONE_WORDS = {"なし", "none", "-", ""}
HUB_THRESHOLD = 7          # callees がこれを超えるモジュールは肥大の兆候
MODULE_DOC_THRESHOLD = 15  # 1モジュールの本数がこれを超えたら 02 の分割定義を見直す合図


def find_root(start: Path) -> Path:
    cur = start.resolve()
    for cand in [cur, *cur.parents]:
        if (cand / "CLAUDE.md").is_file() and (cand / ".claude").is_dir():
            return cand
    return cur


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


def items(value: str) -> list[str]:
    v = (value or "").strip()
    if v.lower() in NONE_WORDS or v.startswith("なし"):
        return []
    return [p.strip() for p in v.split(",") if p.strip()]


def load(root: Path) -> dict[str, dict]:
    base = root / RELATIONS_DIR
    docs: dict[str, dict] = {}
    if not base.is_dir():
        return docs
    for path in sorted(base.glob("MODULE-*.md")):
        fm = read_frontmatter(path)
        mid = fm.get("id", path.stem)
        docs[mid] = {
            "id": mid, "path": path,
            "module": fm.get("module", ""), "kind": fm.get("kind", ""),
            "sync": fm.get("sync", ""), "summary": fm.get("summary", ""),
            "impl": items(fm.get("impl", "")),
            "callers": items(fm.get("callers", "")),
            "callees": items(fm.get("callees", "")),
            "contracts": items(fm.get("contracts", "")),
            "requirements": items(fm.get("requirements", "")),
            "design": items(fm.get("design", "")),
            "tests": items(fm.get("tests", "")),
        }
    return docs


def traverse(docs: dict[str, dict], start: list[str], key: str, depth: int) -> list[tuple[int, str]]:
    """幅優先で推移的に辿る。(距離, ID) を距離順で返す。"""
    seen = set(start)
    out: list[tuple[int, str]] = []
    q = deque((s, 0) for s in start)
    while q:
        node, d = q.popleft()
        if d >= depth:
            continue
        for nxt in docs.get(node, {}).get(key, []):
            if nxt in seen:
                continue
            seen.add(nxt)
            out.append((d + 1, nxt))
            if nxt in docs:
                q.append((nxt, d + 1))
    return out


def find_path(docs: dict[str, dict], src: str, dst: str) -> list[str] | None:
    prev: dict[str, str] = {}
    q = deque([src])
    seen = {src}
    while q:
        node = q.popleft()
        if node == dst:
            chain = [node]
            while chain[-1] != src:
                chain.append(prev[chain[-1]])
            return list(reversed(chain))
        for nxt in docs.get(node, {}).get("callees", []):
            if nxt not in seen:
                seen.add(nxt)
                prev[nxt] = node
                q.append(nxt)
    return None


def row(docs: dict[str, dict], mid: str, extra: str = "") -> str:
    d = docs.get(mid)
    if not d:
        return f"| `{mid}` | (外部) | - | - | {extra} |"
    return (f"| `{mid}` | {d['module']} | {d['kind']}/{d['sync']} | "
            f"{d['summary']} | {extra} |")


def header() -> None:
    print("| ID | モジュール | 種別/同期 | 概要 | 備考 |")
    print("|---|---|---|---|---|")


def main(argv: list[str]) -> int:
    if any(a in ("-h", "--help") for a in argv[1:]):
        print(__doc__)   # 明示要求は 0。使い方エラーの 2 と区別する(tools-readme §2)
        return 0
    args = argv[1:]
    if not args:
        print(__doc__)
        return 2

    opts: dict[str, list[str]] = {}
    i = 0
    while i < len(args):
        a = args[i]
        if not a.startswith("--"):
            print(f"エラー: 位置引数は取らない: {a}")
            return 2
        # `--key=value` 形も受ける(relations.md §6.1「Both forms are accepted everywhere」。
        # 値側の `=` は保全する — callgraph-check.py と同じ分解)
        if "=" in a:
            key, val = a[2:].split("=", 1)
            opts[key] = [val]
            i += 1
            continue
        key = a[2:]
        vals: list[str] = []
        i += 1
        while i < len(args) and not args[i].startswith("--"):
            vals.append(args[i])
            i += 1
        opts[key] = vals

    as_json = "format" in opts and opts["format"] and opts["format"][0] == "json"
    try:
        depth = int(opts.get("depth", ["3"])[0])
    except (ValueError, IndexError):
        # 不正値・値なしを未捕捉 traceback にしない(使い方エラーは 2 — tools-readme §2)
        print("エラー: --depth は整数で渡す(例: --depth 3)", file=sys.stderr)
        return 2
    if depth < 0:
        print("エラー: --depth は 0 以上", file=sys.stderr)
        return 2

    root = find_root(Path.cwd())
    docs = load(root)
    if not docs:
        print(f"{RELATIONS_DIR} に MODULE-*.md が無い。"
              "ブラウンフィールド導入なら `/relations all --apply --bootstrap` が最初の一歩。",
              file=sys.stderr)
        # --list の「0件」は正当な答えなので、消費側が読める空の答えを stdout に出す。
        # 個別IDへの問いは答えられていない(fail-open にしない)
        if "list" in opts:
            print(json.dumps({"list": []}) if as_json else "## 一覧(0 件)")
            return 0
        return 2

    result: dict = {}

    if "list" in opts:
        mod = opts.get("module", [None])[0]
        kind = opts.get("kind", [None])[0]
        sel = [d for d in docs.values()
               if (not mod or d["module"] == mod) and (not kind or d["kind"] == kind)]
        result = {"list": [d["id"] for d in sel]}
        if not as_json:
            print(f"## 一覧({len(sel)} 件"
                  + (f" / module={mod}" if mod else "") + (f" / kind={kind}" if kind else "") + ")")
            header()
            for d in sorted(sel, key=lambda x: (x["module"], x["id"])):
                print(row(docs, d["id"], f"impl: {len(d['impl'])} / tests: {len(d['tests'])}"))

    elif "callers" in opts or "callees" in opts:
        key = "callers" if "callers" in opts else "callees"
        mid = opts[key][0]
        if mid not in docs:
            print(f"エラー: {mid} が存在しない。一覧: "
                  "`python3 .claude/scripts/relations-query.py --list`"
                  "(`--module MOD-xxx` で絞れる)", file=sys.stderr)
            return 2
        refs = docs[mid][key]
        result = {key: refs}
        if not as_json:
            label = "呼び出し元" if key == "callers" else "呼び出す先"
            print(f"## {mid} の直接の{label}({len(refs)} 件)")
            header()
            for r in refs:
                print(row(docs, r))

    elif "upstream" in opts or "downstream" in opts:
        key = "callers" if "upstream" in opts else "callees"
        mid = opts["upstream" if "upstream" in opts else "downstream"][0]
        if mid not in docs:
            print(f"エラー: {mid} が存在しない。一覧: `python3 .claude/scripts/relations-query.py --list`(`--module MOD-xxx` で絞れる)", file=sys.stderr)
            return 2
        found = traverse(docs, [mid], key, depth)
        result = {"transitive": [{"distance": d, "id": n} for d, n in found]}
        if not as_json:
            label = "上流(推移的な呼び出し元)" if key == "callers" else "下流(推移的な呼び出し先)"
            print(f"## {mid} の{label} / 深さ {depth} まで({len(found)} 件)")
            header()
            for dist, n in found:
                print(row(docs, n, f"距離 {dist}"))

    elif "impact" in opts:
        target = opts["impact"][0]
        direct = [d["id"] for d in docs.values()
                  if any(p.split("::", 1)[0] == target
                         or p.split("::", 1)[0].startswith(target.rstrip("/") + "/")
                         for p in d["impl"])]
        upstream = traverse(docs, direct, "callers", depth)
        reqs = sorted({r for m in direct for r in docs[m]["requirements"]}
                      | {r for _, n in upstream if n in docs for r in docs[n]["requirements"]})
        ctrs = sorted({c for m in direct for c in docs[m]["contracts"]})
        # 直接のテストだけでは足りない。この実装を経由する上流のテストこそ、
        # 変更で壊れることを検出する層である(結合・E2E がそこに載っている)。
        tests_direct = sorted({t for m in direct for t in docs[m]["tests"]
                               if not t.startswith("なし")})
        tests_upstream = sorted({t for _, n in upstream if n in docs
                                 for t in docs[n]["tests"] if not t.startswith("なし")}
                                - set(tests_direct))
        tests = tests_direct + tests_upstream
        result = {"direct": direct, "upstream": [n for _, n in upstream],
                  "requirements": reqs, "contracts": ctrs,
                  "tests_direct": tests_direct, "tests_upstream": tests_upstream}
        if not as_json:
            print(f"## `{target}` を変更したときの波及")
            print(f"\n### 直接この実装を持つ機能({len(direct)} 件)")
            if direct:
                header()
                for m in direct:
                    print(row(docs, m))
            else:
                print("なし。**このパスを impl に持つ機能間連携仕様書が無い** — "
                      "03-impl の欠落かもしれない(`relations-coverage.py` で確認すること)。")
            print(f"\n### 波及する呼び出し元({len(upstream)} 件 / 深さ {depth} まで)")
            if upstream:
                header()
                for dist, n in upstream:
                    print(row(docs, n, f"距離 {dist}"))
            else:
                print("なし")
            print(f"\n### 関係する要件({len(reqs)} 件)\n{', '.join(reqs) or 'なし'}")
            print(f"\n### 関係する契約({len(ctrs)} 件)\n{', '.join(ctrs) or 'なし'}")
            print(f"\n### 走らせるべきテスト({len(tests)} 件)")
            for t in tests_direct:
                print(f"- `{t}`(直接)")
            for t in tests_upstream:
                print(f"- `{t}`(呼び出し元経由)")
            if not tests:
                print("なし。**テストが無い範囲を変更しようとしている** — 先にテストを足すこと。")
            elif not tests_direct:
                print("\n**この実装を直接検証するテストが無い**(上流経由でしか触れられていない)。")

    elif "path" in opts:
        if len(opts["path"]) != 2:
            print("エラー: --path は2つの ID を取る")
            return 2
        src, dst = opts["path"]
        chain = find_path(docs, src, dst)
        result = {"path": chain}
        if not as_json:
            if chain:
                print(f"## {src} → {dst} の呼び出し経路")
                print(" → ".join(f"`{c}`" for c in chain))
                print(f"\n経路長: {len(chain) - 1} ホップ")
            else:
                print(f"## {src} から {dst} への呼び出し経路は存在しない")

    elif "graph" in opts:
        mod = opts.get("module", [None])[0]
        sel = {k: v for k, v in docs.items() if not mod or v["module"] == mod}
        lines = ["```mermaid", "graph LR"]
        externals = set()
        for d in sel.values():
            safe = d["id"].replace("-", "_")
            lines.append(f'  {safe}["{d["id"]}"]')
        for d in sel.values():
            safe = d["id"].replace("-", "_")
            for c in d["callees"]:
                if c in sel:
                    lines.append(f"  {safe} --> {c.replace('-', '_')}")
                elif not mod or c not in docs:
                    externals.add(c)
                    lines.append(f"  {safe} --> {c.replace('-', '_')}")
            for c in d["callers"]:
                if c not in docs:
                    externals.add(c)
                    lines.append(f"  {c.replace('-', '_')} --> {safe}")
        for e in sorted(externals):
            lines.append(f'  {e.replace("-", "_")}(["{e}"])')
        lines.append("```")
        result = {"mermaid": "\n".join(lines)}
        if not as_json:
            print(f"## 連携図" + (f"({mod})" if mod else ""))
            print("\n".join(lines))

    elif "health" in opts:
        hubs = [(d["id"], len(d["callees"])) for d in docs.values()
                if len(d["callees"]) > HUB_THRESHOLD]
        orphans = [d["id"] for d in docs.values()
                   if not d["callers"] and d["kind"] == "function-call"]
        untested = [d["id"] for d in docs.values()
                    if not [t for t in d["tests"] if not t.startswith("なし")]]
        no_req = [d["id"] for d in docs.values() if not d["requirements"]]
        per_module: dict[str, int] = {}
        for d in docs.values():
            per_module[d["module"]] = per_module.get(d["module"], 0) + 1
        big = {m: n for m, n in per_module.items() if n > MODULE_DOC_THRESHOLD}
        cycles = []
        for d in docs.values():
            for c in d["callees"]:
                if c in docs and find_path(docs, c, d["id"]):
                    pair = tuple(sorted([d["id"], c]))
                    if pair not in cycles:
                        cycles.append(pair)
        result = {"hubs": hubs, "orphans": orphans, "untested": untested,
                  "no_requirement": no_req, "oversized_modules": big, "cycles": cycles}
        if not as_json:
            print(f"## 構造の健全性({len(docs)} 本 / {len(per_module)} モジュール)")
            print(f"\n### モジュールごとの本数")
            print("| モジュール | 本数 | 判定 |")
            print("|---|---|---|")
            for m, n in sorted(per_module.items(), key=lambda x: -x[1]):
                verdict = f"**{MODULE_DOC_THRESHOLD} 本超。02 の分割定義の見直しを提案すること**" if n > MODULE_DOC_THRESHOLD else "-"
                print(f"| {m or '(未設定)'} | {n} | {verdict} |")
            print(f"\n### 呼び出し先が多い機能(> {HUB_THRESHOLD})")
            for mid, n in sorted(hubs, key=lambda x: -x[1]) or []:
                print(f"- `{mid}`: {n} 件 — 機能が大きすぎる可能性")
            if not hubs:
                print("なし")
            print(f"\n### 呼び出し元が無い function-call({len(orphans)} 件)")
            print(", ".join(f"`{o}`" for o in orphans) or "なし")
            if orphans:
                print("→ 到達不能コードの疑い。**削ってよいかを自分で決めない**(動的呼び出しの可能性)。")
            print(f"\n### 循環({len(cycles)} 件)")
            for a, b in cycles:
                print(f"- `{a}` ⇄ `{b}`")
            if not cycles:
                print("なし")
            print(f"\n### テストが無い機能({len(untested)} 件)")
            print(", ".join(f"`{u}`" for u in untested) or "なし")
            print(f"\n### 対応要件が無い機能({len(no_req)} 件)")
            print(", ".join(f"`{n}`" for n in no_req) or "なし")
            if no_req:
                print("→ 要件に紐づかない実装。設計外の実装か、トレーサビリティの欠落。")

    elif "requirement" in opts:
        rid = opts["requirement"][0]
        sel = [d for d in docs.values() if rid in d["requirements"]]
        result = {"requirement": rid, "modules": [d["id"] for d in sel]}
        if not as_json:
            print(f"## {rid} を実装している機能({len(sel)} 件)")
            if sel:
                header()
                for d in sel:
                    print(row(docs, d["id"], f"tests: {len(d['tests'])}"))
                tests = sorted({t for d in sel for t in d["tests"] if not t.startswith("なし")})
                print(f"\n### 検証しているテスト({len(tests)} 件)")
                for t in tests:
                    print(f"- `{t}`")
                if not tests:
                    print("なし。**この要件は未検証(テスト未実装)** である。")
            else:
                print("なし。**要件に対応する実装が無い** — 未実装か、トレーサビリティの欠落。")

    else:
        print(__doc__)
        return 2

    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
