"""shell(bash / sh / zsh)コールグラフ抽出器 — Tier 3(正規表現)。

規範: .claude/directions/callgraphs.md / 検討記録: .claude/improvements/KIT-shell-make-extraction.md

**Tier 3 である。呼び出し関係は不完全であり、「網羅した」と報告してはならない**(§5.8)。
shell は変数展開・`eval`・動的な関数名で静的解決が原理的に不完全なので、
tree-sitter を使っても Tier 2 は名乗れない。取りこぼしは FT2 / CG4 と
コード精読で埋める設計である(relations/SKILL.md §4)。

抽出するもの:

| 抽出物 | ID |
|---|---|
| 関数定義 `name() {` / `function name {` | `claude-dev::container_name` |
| スクリプト本体(1ファイル1つの合成シンボル) | `claude-dev::main` |
| トップレベル `case "$1" in` の各ラベル | `claude-dev::main#start`(§5.7) |
| 2階層目 `case "$2" in` のラベル | `claude-dev::main#ssh-keys.reset`(決定 F) |
| エンドポイント | `dispatch start @ claude-dev::main`(protocol: cli。決定 A') |
| 入口を持たない実行スクリプト | `dispatch <script> @ scripts/vm-up.sh::main`(決定 E。**protocol: main** — 種別を主張しない) |

**catch-all(`*` を含むラベル)は入口にしない**(決定 D)。`*` は未知入力への
フォールバックであって機能ではない。外した件数は `unresolved` ではなく
呼び出し元へ返して index に出す。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from . import base

EXTRACTOR = "shell-regex"

# 関数定義。`^\s*` を許すのでネストした定義も拾う(KIT メモ 指摘6)。
_FUNC = re.compile(r"^[ \t]*(?:function[ \t]+)?([A-Za-z_][A-Za-z0-9_]*)[ \t]*\(\)[ \t]*\{")
_FUNC_KW = re.compile(r"^[ \t]*function[ \t]+([A-Za-z_][A-Za-z0-9_]*)[ \t]*\{")

# `case "${1:-help}" in` / `case "$1" in` / `case $1 in`
_CASE = re.compile(r"^([ \t]*)case[ \t]+\"?\$\{?(\d+)(?::-[^}]*)?\}?\"?[ \t]+in\b")
# ラベル行 `start)` / `a|b)` / `help|*)`。行頭の `;;` や `esac` と区別する。
_LABEL = re.compile(r"^([ \t]*)([^()\s;][^()]*?)\)[ \t]*$")
_ESAC = re.compile(r"^[ \t]*esac\b")
_CASE_SEP = re.compile(r"^[ \t]*(;;|;&|;;&)[ \t]*$")

# リテラルパスの source。変数展開のものは未解決へ回す(指摘16)。
_SOURCE = re.compile(r"^[ \t]*(?:source|\.)[ \t]+([^\s;|&]+)")
_DYNAMIC_CALL = re.compile(r"(?:^|[;&|(]|\$\()[ \t]*(?:eval[ \t]+|\"?\$\{?[A-Za-z_][A-Za-z0-9_]*\}?\"?[ \t]*$)")

def _heredoc_body_lines(lines: list[str]) -> tuple[set[int], list[str]]:
    """ヒアドキュメント本文(と終端語の行)の行番号 と、終端語が見つからなかったものの一覧。

    本文は実行されるコードではない(別言語のこともある)。素通しすると:
    波括弧が対応しなくなって関数の範囲が暴走し、本文の `g() {` が関数定義として拾われ、
    本文に現れた語が呼び出しとして辺になる(KIT-shell-heredoc-tracking)。

    **終端語が見つからないまま末尾に達したら、そのヒアドキュメントは無かったことにする**
    (行を落とさない)。誤検出でファイルの残り全部を解析対象から外すのが最悪の結果だから。
    落とし損ねれば従来どおりの精度に戻るだけである。落とせなかったことは呼び出し元が警告する。

    終端の判定: `<<EOF` はその行が終端語ちょうど(末尾の空白は許容)、
    `<<-EOF` は先頭のタブを剥がして比較する。

    既知の限界: `ssh host <<EOF … EOF` のように**別ホストで実行される**本文の呼び出しも
    落ちる。終端語が動的(`<<$VAR`)なものは検出できない。
    """
    body: set[int] = set()
    unterminated: list[str] = []
    i, n = 0, len(lines)
    while i < n:
        delims = base.find_heredocs(lines[i])
        i += 1
        for delim, strip_tabs in delims:        # 1行に複数開くことがある(`cmd <<A <<B`)
            start, closed = i, False
            while i < n:
                raw = lines[i]
                got = raw.lstrip("\t").rstrip() if strip_tabs else raw.rstrip()
                i += 1
                if got == delim:
                    closed = True
                    break
            if closed:
                body.update(range(start, i))
            else:                               # 終端が無い → 何も落とさず、行位置も戻す
                unterminated.append(delim)
                i = start
    return body, unterminated


def _strip_noise(line: str) -> str:
    """コメントとシングルクォート文字列を落とす。**辺の誤検出を減らすため**。

    実体は `base.strip_shell_noise`(shell と Makefile のレシピ行で共有する)。
    `#` を「行頭からの正規表現」で切ると `${#arr[@]}` の `#` を食って `}` を失い、
    関数の範囲がファイル末尾まで暴走する(KIT-shell-comment-strip)。
    """
    return base.strip_shell_noise(line)


def _scan_file(rel: str, text: str) -> dict:
    """1ファイルを走査して、関数・ディスパッチ・行の帰属を返す。"""
    lines = text.splitlines()
    # ヒアドキュメント本文は解析対象外。**行番号は保ったまま空行に潰す**
    # (帰属 `_owner_of` と分岐の範囲が行番号で動くため、行を削ってはならない)。
    heredoc, unterminated_heredocs = _heredoc_body_lines(lines)
    lines = ["" if i in heredoc else raw for i, raw in enumerate(lines)]
    funcs: dict[str, int] = {}              # 関数名 -> 定義行(0-based)
    func_ranges: list[tuple[str, int, int]] = []

    # --- 関数定義とその範囲(素朴な波括弧の対応。Tier 3 の限界として許容する)
    unbalanced: list[str] = []
    for i, raw in enumerate(lines):
        line = _strip_noise(raw)
        m = _FUNC.match(line) or _FUNC_KW.match(line)
        if not m:
            continue
        name = m.group(1)
        depth, end, closed = 0, i, False
        for j in range(i, len(lines)):
            body = _strip_noise(lines[j])
            depth += body.count("{") - body.count("}")
            end = j
            # 1行で閉じる定義(`f() { echo x; }`)は**その行で終わり**。
            # `j > i` を条件にすると次の行まで範囲に飲み込み、呼び出し元が自分自身になって
            # 辺が `dst != src` で落ちる(フィクスチャ `outer -> _nested` で実測)。
            if depth <= 0:
                closed = True
                break
        # 閉じないまま末尾に達した = 波括弧の対応が取れていない。範囲はファイル全体になり、
        # その中の呼び出しがこの関数に誤って帰属する。**沈黙させない**(KIT-shell-comment-strip 案2)。
        # 範囲そのものは変えない(「次の定義で打ち切る」案はネスト定義とヒアドキュメントを
        # 誤認するため却下した)。
        if not closed:
            unbalanced.append(name)
        funcs.setdefault(name, i)
        func_ranges.append((name, i, end))

    # --- トップレベル case のラベル(1階層目と2階層目)
    branches: list[tuple[str, int, int]] = []   # (合成値, 開始行, 終了行)
    dropped_catchall: list[str] = []
    i = 0
    while i < len(lines):
        m = _CASE.match(_strip_noise(lines[i]))
        if not m or m.group(2) != "1":
            i += 1
            continue
        outer_indent = m.group(1)
        i += 1
        while i < len(lines):
            line = _strip_noise(lines[i])
            if _ESAC.match(line) and line.index("esac") <= len(outer_indent):
                break
            lm = _LABEL.match(line)
            if not lm:
                i += 1
                continue
            label = lm.group(2).strip().strip('"\'')
            start = i
            # ラベルの本文範囲(次の `;;` / 次のラベル / esac まで)
            j, depth = i + 1, 0
            while j < len(lines):
                body = _strip_noise(lines[j])
                if depth == 0 and (_CASE_SEP.match(body) or _ESAC.match(body)):
                    break
                depth += body.count("case ") - len(_ESAC.findall(body) or [])
                j += 1
            end = min(j, len(lines) - 1)
            if "*" in label:                      # 決定 D: catch-all は入口にしない
                dropped_catchall.append(label)
            else:
                value = "|".join(sorted({p.strip() for p in label.split("|") if p.strip()}))
                # 2階層目(決定 F): この本文の中に `case "$2" in` があれば親を前置する
                nested = _nested_labels(lines, start, end)
                if nested:
                    for nv, ns, ne in nested:
                        branches.append((f"{value}.{nv}", ns, ne))
                    branches.append((value, start, end))
                else:
                    branches.append((value, start, end))
            i = max(end, i + 1)
        i += 1

    return {"funcs": funcs, "func_ranges": func_ranges, "branches": branches,
            "dropped_catchall": dropped_catchall, "unbalanced": unbalanced,
            "heredoc": heredoc, "unterminated_heredocs": unterminated_heredocs}


def _nested_labels(lines: list[str], start: int, end: int) -> list[tuple[str, int, int]]:
    """`case "$2" in` の各ラベル。決定 F(親を前置するので値だけ返す)。"""
    out: list[tuple[str, int, int]] = []
    k = start
    while k <= end:
        m = _CASE.match(_strip_noise(lines[k]))
        if m and m.group(2) != "1":
            k += 1
            while k <= end:
                line = _strip_noise(lines[k])
                if _ESAC.match(line):
                    break
                lm = _LABEL.match(line)
                if lm:
                    label = lm.group(2).strip().strip('"\'')
                    if "*" not in label:
                        j = k + 1
                        while j <= end and not _CASE_SEP.match(_strip_noise(lines[j])):
                            j += 1
                        value = "|".join(sorted({p.strip() for p in label.split("|") if p.strip()}))
                        out.append((value, k, min(j, end)))
                k += 1
        k += 1
    return out


def _owner_of(line_no: int, func_ranges: list[tuple[str, int, int]],
              branches: list[tuple[str, int, int]], main_id: str, rel: str) -> str:
    """その行の呼び出しを帰属させる最も近い名前付きシンボル(§5.1)。

    優先順位: 関数定義の中 > case 分岐の中 > スクリプト本体(`::main`)。
    分岐の前後の共通処理は `::main` に残る(§5.7)。
    """
    best: tuple[int, str] | None = None
    for name, s, e in func_ranges:
        if s <= line_no <= e and (best is None or s > best[0]):
            best = (s, base.symbol_id(rel, name))
    if best:
        return best[1]
    for value, s, e in branches:
        if s <= line_no <= e and (best is None or s > best[0]):
            best = (s, f"{main_id}#{value}")
    return best[1] if best else main_id


def extract(root: Path, cfg: dict, scope: Path | None = None) -> dict:
    spec = cfg.get("languages", {}).get("shell", {})
    skipped: dict = {}
    files, vendored = base.collect_files(
        root, cfg,
        spec.get("extensions", [".sh", ".bash"]),
        scope,
        skipped,
        filenames=spec.get("filenames", []),
        shebangs=spec.get("shebangs", [r"\b(ba|z|da)?sh\b"]),
    )

    symbols: list[dict] = []
    edges: list[dict] = []
    endpoints: list[dict] = []
    unresolved: list[dict] = []
    external = 0
    dropped_catchall = 0
    scanned = 0

    parsed: dict[str, dict] = {}
    texts: dict[str, str] = {}
    for path in files:
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        scanned += 1
        texts[rel] = text
        parsed[rel] = _scan_file(rel, text)

    # 波括弧の対応が取れなかった関数を**必ず可視化する**(生成物には出さないので決定性に触れない)。
    # 放置すると、その関数がファイル末尾まで範囲を広げて他の呼び出しを吸い、
    # 「共有関数なし」という正常な出力と見分けがつかなくなる(KIT-shell-comment-strip)。
    for rel in sorted(parsed):
        if names := parsed[rel].get("unbalanced"):
            print(f"⚠️  shell: {rel} で波括弧の対応が取れない関数: {', '.join(sorted(names))}"
                  f" — 範囲がファイル末尾まで伸び、呼び出しの帰属が誤る可能性がある",
                  file=sys.stderr)
        if delims := parsed[rel].get("unterminated_heredocs"):
            print(f"⚠️  shell: {rel} で終端語が見つからないヒアドキュメント: "
                  f"{', '.join(sorted(delims))} — 本文を解析対象から外せていない",
                  file=sys.stderr)

    # --- シンボル
    for rel, info in parsed.items():
        main_id = base.symbol_id(rel, "main")
        symbols.append({"id": main_id, "file": rel, "name": "main",
                        "kind": "handler", "visibility": "private"})
        for name in sorted(info["funcs"]):
            symbols.append({"id": base.symbol_id(rel, name), "file": rel, "name": name,
                            "kind": "function", "visibility": "private"})
        for value, _s, _e in info["branches"]:
            symbols.append({"id": f"{main_id}#{value}", "file": rel,
                            "name": f"main#{value}", "kind": "handler",
                            "visibility": "private"})
        dropped_catchall += len(info["dropped_catchall"])

    # --- エンドポイント
    for rel, info in parsed.items():
        main_id = base.symbol_id(rel, "main")
        if info["branches"]:
            for value, _s, _e in info["branches"]:
                endpoints.append({
                    "id": f"dispatch {value} @ {main_id}",
                    "protocol": "cli",
                    "path_pattern": f"/{Path(rel).name}/{value.replace('.', '/')}",
                    "path_key": f"/{Path(rel).name}/{value.replace('.', '/')}",
                    "handler": f"{main_id}#{value}",
                    "source": rel,
                })
        else:
            # 決定 E: ディスパッチを持たない実行スクリプトは「1本 = 1入口」。
            # **protocol は `main`** ★(2026-08-25。Go の `func main` と同じ理由)。分岐を持つ
            # スクリプト(上の枝)は `case "$1"` が**引数を捌いている証拠**なので `cli` でよいが、
            # 分岐が無いスクリプトについて分かるのは「実行される1本である」ことだけで、
            # コンテナの起動用か対話的な道具かは決まらない(vpnsys-op の実測:
            # `docker/hub/entrypoint.sh` は `kind: event` の機能の実体だった)。
            # `main` は種別を主張しない値なので CG6 の突き合わせから外れる
            # (`callgraph-check.py` の `KIND_AGNOSTIC_PROTOCOLS`)。
            endpoints.append({
                "id": f"dispatch {Path(rel).name} @ {main_id}",
                "protocol": "main",
                "path_pattern": f"/{Path(rel).name}",
                "path_key": f"/{Path(rel).name}",
                "handler": main_id,
                "source": rel,
            })

    # --- 辺(指摘13: 先頭語ではなく行内のトークン一致で拾う)
    for rel, info in parsed.items():
        main_id = base.symbol_id(rel, "main")
        known = dict(info["funcs"])
        # ヒアドキュメント本文は実行されるコードではないので、辺の抽出からも外す
        code = ["" if i in info["heredoc"] else raw
                for i, raw in enumerate(texts[rel].splitlines())]
        # リテラルパスの source で読んだファイルの関数も解決対象に加える
        for raw in code:
            sm = _SOURCE.match(_strip_noise(raw))
            if not sm:
                continue
            target = sm.group(1).strip('"\'')
            if "$" in target:
                unresolved.append({"from": main_id, "expression": f"source {target}"[:120],
                                   "reason": "dynamic"})
                continue
            cand = (root / target).resolve()
            try:
                crel = cand.relative_to(root).as_posix()
            except ValueError:
                continue
            if crel in parsed:
                for name in parsed[crel]["funcs"]:
                    known.setdefault(name, -1)

        if not known:
            continue
        pattern = re.compile(r"(?<![A-Za-z0-9_.-])(" + "|".join(
            sorted((re.escape(n) for n in known), key=len, reverse=True)) + r")(?![A-Za-z0-9_-])")

        for idx, raw in enumerate(code):
            line = _strip_noise(raw)
            if not line.strip():
                continue
            if _FUNC.match(line) or _FUNC_KW.match(line):
                continue                      # 定義行そのものは呼び出しではない
            src = _owner_of(idx, info["func_ranges"], info["branches"], main_id, rel)
            for m in pattern.finditer(line):
                name = m.group(1)
                dst_file = rel if known.get(name, -1) >= 0 else None
                if dst_file is None:
                    for crel, cinfo in parsed.items():
                        if name in cinfo["funcs"]:
                            dst_file = crel
                            break
                if dst_file is None:
                    continue
                dst = base.symbol_id(dst_file, name)
                if dst != src:
                    edges.append({"from": src, "to": dst})
            if _DYNAMIC_CALL.search(line):
                unresolved.append({"from": src, "expression": line.strip()[:120],
                                   "reason": "dynamic"})
            external += len(re.findall(r"(?:^|[;&|]|\$\()[ \t]*([a-z][a-z0-9_-]*)[ \t]", line))

    result = base.sort_lang_result({
        "tier": 3,
        "extractor": EXTRACTOR,
        "degraded_reason": "正規表現のみ(shell は変数展開・eval で静的解決が原理的に不完全)",
        "external_call_count": external,
        "symbols": symbols,
        "edges": edges,
        "endpoints": endpoints,
        "unresolved": unresolved,
        "vendored_dirs": vendored,
        "scanned_files": scanned,
        "skipped_files": skipped,
    })
    result["dropped_catchall"] = dropped_catchall
    return result
