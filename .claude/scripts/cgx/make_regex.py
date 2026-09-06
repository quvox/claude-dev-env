"""Makefile コールグラフ抽出器 — Tier 3(正規表現)。

規範: .claude/directions/callgraphs.md / 検討記録: .claude/improvements/KIT-shell-make-extraction.md

**Tier 3 である。** レシピは shell なので、レシピ内の呼び出しは
`shell` 抽出器と同じ限界を持つ。ここで解決するのは「ターゲット間の関係」だけである。

| 抽出物 | ID |
|---|---|
| ターゲット | `Makefile::build` |
| エンドポイント | `dispatch build @ Makefile::build`(handler は実在シンボル。指摘15) |
| 辺(依存) | `Makefile::build` → `Makefile::images` |
| 辺(再帰 make) | レシピ行の `$(MAKE) other` / `make other` |
| 境界 | レシピ行が呼ぶスクリプトのパス(`boundaries.md` の材料) |

特殊ターゲット(`.PHONY` など先頭が `.` のもの)とパターンルール(`%` を含むもの)、
変数代入(`X := y`)は**ターゲットにしない**。
"""

from __future__ import annotations

import re
from pathlib import Path

from . import base

EXTRACTOR = "make-regex"

# `build: dep1 dep2` — 代入(`:=` `::=` `?=` `+=`)は除く。
_TARGET = re.compile(r"^([A-Za-z0-9_][A-Za-z0-9_./-]*)[ \t]*:(?![=:])[ \t]*(.*)$")
_RECIPE = re.compile(r"^\t(.*)$")
_SUBMAKE = re.compile(r"(?:\$\(MAKE\)|\bmake\b)[ \t]+([A-Za-z0-9_][A-Za-z0-9_./-]*)")
_SCRIPT = re.compile(r"(?<![\w/.-])((?:\./)?[A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:sh|bash|py))\b")
# **非レシピ行**の `#`。make のコメントは語の途中でも始まるので、この素朴な規則が正しい。
# レシピ行(タブ始まり)は make が `#` を除去せずシェルへ渡すため、shell の規則
# (`base.strip_shell_noise`)を使う(KIT-shell-comment-strip 案3)。
# 対象外の既知の限界: `.RECIPEPREFIX` を変えた Makefile、ターゲット行の `;` 以降の
# インラインレシピ、`SHELL` に非 shell を指定した Makefile。
_COMMENT = re.compile(r"(?<!\\)#.*$")


def extract(root: Path, cfg: dict, scope: Path | None = None) -> dict:
    spec = cfg.get("languages", {}).get("make", {})
    # `Makefile` は tooling_markers の既定に入っている(他言語の解析からは開発ツールとして
    # 外す)が、この抽出器は**その開発ツール自身を解析する側**である。自分の対象まで
    # tooling で落とすと、既定設定では make.md にターゲットが構造的に1件も載らない
    # (inspection-17 M-21)。ここだけ include_tooling を立てて集める。
    skipped: dict = {}
    files, vendored = base.collect_files(
        root, {**cfg, "include_tooling": True},
        spec.get("extensions", [".mk"]),
        scope,
        skipped,
        filenames=spec.get("filenames", ["Makefile", "makefile", "GNUmakefile"]),
    )

    symbols: list[dict] = []
    edges: list[dict] = []
    endpoints: list[dict] = []
    unresolved: list[dict] = []
    external = 0
    scanned = 0

    for path in files:
        rel = path.relative_to(root).as_posix()
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        scanned += 1

        targets: list[tuple[str, list[str], int]] = []
        for i, raw in enumerate(lines):
            if raw.startswith("\t"):
                continue
            line = _COMMENT.sub("", raw)
            m = _TARGET.match(line)
            if not m:
                continue
            name = m.group(1)
            if name.startswith(".") or "%" in name:
                continue
            deps = [d for d in m.group(2).split() if d and not d.startswith("$")]
            targets.append((name, deps, i))

        known = {name for name, _d, _i in targets}
        for name, deps, start in targets:
            sid = base.symbol_id(rel, name)
            symbols.append({"id": sid, "file": rel, "name": name,
                            "kind": "handler", "visibility": "public"})
            endpoints.append({
                "id": f"dispatch {name} @ {sid}",
                "protocol": "cli",
                "path_pattern": f"/{Path(rel).name}/{name}",
                "path_key": f"/{Path(rel).name}/{name}",
                "handler": sid,
                "source": rel,
            })
            for dep in deps:
                if dep in known:
                    edges.append({"from": sid, "to": base.symbol_id(rel, dep)})

            # レシピ本文(次の非レシピ行まで)
            for j in range(start + 1, len(lines)):
                rm = _RECIPE.match(lines[j])
                if not rm:
                    if lines[j].strip() and not lines[j].startswith("\t"):
                        break
                    continue
                body = base.strip_shell_noise(rm.group(1))
                for sm in _SUBMAKE.finditer(body):
                    if sm.group(1) in known:
                        edges.append({"from": sid, "to": base.symbol_id(rel, sm.group(1))})
                for scm in _SCRIPT.finditer(body):
                    target = scm.group(1).lstrip("./")
                    unresolved.append({
                        "from": sid,
                        "expression": f"{target}(レシピからのスクリプト呼び出し)"[:120],
                        "reason": "boundary",
                    })
                external += len(re.findall(r"(?:^|[;&|]|\$\()[ \t]*([a-z][a-z0-9_-]*)[ \t]", body))

    return base.sort_lang_result({
        "tier": 3,
        "extractor": EXTRACTOR,
        "degraded_reason": "正規表現のみ(レシピ本文は shell と同じ限界を持つ)",
        "external_call_count": external,
        "symbols": symbols,
        "edges": edges,
        "endpoints": endpoints,
        "unresolved": unresolved,
        "vendored_dirs": vendored,
        "scanned_files": scanned,
        "skipped_files": skipped,
    })
