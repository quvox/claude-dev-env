#!/usr/bin/env python3
"""コードからエントリポイント候補を機械的に列挙する。

なぜあるか: 機能間連携仕様書の取りこぼしは「読み落とし」で起きる。リポジトリ全体を読んで探すのは
コンテキストを食い、しかも見落とす。このスクリプトは候補を先に絞り込み、AI が読むべき場所だけを
指す。**再現率を優先しており、誤検出は AI が捨てる前提**(取りこぼしの方が高くつく)。

検出パターンは .claude/scripts/entrypoint-patterns.json。プロジェクト固有のパターンは
.claude/scripts/entrypoint-patterns.local.json に同じ形式で書くとマージされる。

使い方:
    python3 .claude/scripts/scan-entrypoints.py                 # リポジトリ全体
    python3 .claude/scripts/scan-entrypoints.py src/api          # 範囲を絞る
    python3 .claude/scripts/scan-entrypoints.py --format json    # 機械処理向け
    python3 .claude/scripts/scan-entrypoints.py --include-tests  # テストも対象にする
    python3 .claude/scripts/scan-entrypoints.py --include-tooling # 開発ツールも対象にする
    python3 .claude/scripts/scan-entrypoints.py --kind rest-api,event

出力(既定 table): kind / path:line / symbol / 由来パターン
終了コード: 0=成功 2=使い方・設定エラー
"""

from __future__ import annotations

import json
import re
import sys
from fnmatch import fnmatch
from pathlib import Path

import os  # noqa: E402  (ベンダリング検出のディレクトリ走査で使う)

CONFIG = ".claude/scripts/entrypoint-patterns.json"
# cgx/base.py の DEFAULT_VENDOR_MARKERS と同じ方針。二重管理を避けるため import する。
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from cgx.base import DEFAULT_VENDOR_MARKERS as VENDOR_MARKERS  # type: ignore
except Exception:                                    # pragma: no cover
    VENDOR_MARKERS = ["*.dist-info", "*.egg-info", "*.egg-link", "pyvenv.cfg", "modules.txt"]
# **テスト判定は退避を持たない。** 目印の照合規則が2つあると、片方だけ直った状態で
# 「収集段階で黙って落ちる」という気付けない差になる(KIT-marker-substring-false-positives)。
# ここは cgx が読めなければ落ちてよい(cgx/ はこのファイルと同梱で配られる)。
from cgx.base import is_test  # noqa: E402  # type: ignore
LOCAL_CONFIG = ".claude/scripts/entrypoint-patterns.local.json"


def find_root(start: Path) -> Path:
    cur = start.resolve()
    for cand in [cur, *cur.parents]:
        if (cand / "CLAUDE.md").is_file() and (cand / ".claude").is_dir():
            return cand
    return cur


def load_config(root: Path) -> dict:
    base_path = root / CONFIG
    if not base_path.is_file():
        raise SystemExit(f"エラー: 設定が無い: {CONFIG}")
    cfg = json.loads(base_path.read_text(encoding="utf-8"))
    local = root / LOCAL_CONFIG
    if local.is_file():
        loc = json.loads(local.read_text(encoding="utf-8"))
        cfg["excludes"] = sorted(set(cfg.get("excludes", [])) | set(loc.get("excludes", [])))
        cfg["test_markers"] = sorted(set(cfg.get("test_markers", [])) | set(loc.get("test_markers", [])))
        cfg["tooling_markers"] = sorted(set(cfg.get("tooling_markers", []))
                                        | set(loc.get("tooling_markers", [])))

        for lang, spec in loc.get("languages", {}).items():
            if lang in cfg["languages"]:
                cfg["languages"][lang]["extensions"] = sorted(
                    set(cfg["languages"][lang]["extensions"]) | set(spec.get("extensions", [])))
                cfg["languages"][lang]["patterns"].extend(spec.get("patterns", []))
            else:
                cfg["languages"][lang] = spec

    # **除外マーカーの正は callgraph-config(.local).json 側にもある。** 2つの設定ファイルで
    # 別々に持つと、片方にだけ足した開発ツールがここで再検出されて「機能の取りこぼし」に見える。
    # 和集合にして、どちらに書いても効くようにする(directions/callgraphs.md §5.9.1)。
    try:
        from cgx import base as _cgx_base                      # noqa: PLC0415
        cg_cfg = _cgx_base.load_config(root)
    except Exception:                                          # pragma: no cover
        cg_cfg = {}
    for key in ("excludes", "test_markers", "tooling_markers"):
        if cg_cfg.get(key):
            cfg[key] = sorted(set(cfg.get(key, [])) | set(cg_cfg[key]))
    return cfg


def compile_patterns(cfg: dict) -> dict[str, list[tuple]]:
    """拡張子 -> [(kind, compiled, symbol_group, note, path_contains)]"""
    by_ext: dict[str, list[tuple]] = {}
    for lang, spec in cfg["languages"].items():
        compiled = []
        for pat in spec["patterns"]:
            try:
                rx = re.compile(pat["regex"])
            except re.error as exc:
                raise SystemExit(f"エラー: {lang} の regex が不正: {pat['regex']!r} ({exc})")
            compiled.append((pat["kind"], rx, pat.get("symbol_group", 0),
                             pat.get("note", ""), pat.get("path_contains")))
        for ext in spec["extensions"]:
            by_ext.setdefault(ext, []).extend(compiled)
    return by_ext


def is_excluded(rel: str, excludes: list[str]) -> bool:
    return any(ex in rel for ex in excludes)


def nearby_symbol(lines: list[str], idx: int) -> str:
    """デコレータ等でシンボルを捕捉できないとき、直後の定義行から名前を拾う。"""
    for line in lines[idx + 1: idx + 6]:
        m = re.search(r"^\s*(?:async\s+)?(?:def|func|function|class)\s+([A-Za-z_$][\w$]*)", line)
        if m:
            return m.group(1)
        m = re.search(r"^\s*(?:public|private|protected)?\s*[\w<>\[\],\s]*\s+([A-Za-z_$][\w$]*)\s*\(", line)
        if m:
            return m.group(1)
    return "(不明)"


def scan(root: Path, scope: Path, cfg: dict, include_tests: bool,
         kinds: set[str] | None, include_tooling: bool = False) -> list[dict]:
    by_ext = compile_patterns(cfg)
    excludes = cfg.get("excludes", [])
    markers = cfg.get("test_markers", [])
    tooling_markers = cfg.get("tooling_markers", [])
    max_bytes = cfg.get("max_file_bytes", 1 << 20)
    hits: list[dict] = []

    # ベンダリングされた第三者ライブラリは全言語共通で対象にしない
    # (.claude/directions/callgraphs.md §5.3)。cgx/base.py と同じ目印を使う。
    vendor_markers = cfg.get("vendor_markers", VENDOR_MARKERS)
    vendor_roots: list[str] = []
    if scope.is_dir():
        for dirpath, dirnames, filenames in os.walk(scope):
            here = Path(dirpath)
            if any(fnmatch(n, m) for n in (*dirnames, *filenames) for m in vendor_markers):
                try:
                    vendor_roots.append(here.relative_to(root).as_posix() + "/")
                except ValueError:
                    pass
                dirnames[:] = []

    files = [scope] if scope.is_file() else sorted(scope.rglob("*"))
    for path in files:
        if not path.is_file() or path.suffix not in by_ext:
            continue
        rel = path.relative_to(root).as_posix()
        if is_excluded(rel, excludes) or any(rel.startswith(v) for v in vendor_roots):
            continue
        if not include_tooling and is_test(rel, tooling_markers):
            continue
        if not include_tests and is_test(rel, markers):
            continue
        try:
            if path.stat().st_size > max_bytes:
                continue
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue

        for i, line in enumerate(lines):
            for kind, rx, group, note, path_contains in by_ext[path.suffix]:
                if kinds and kind not in kinds:
                    continue
                if path_contains and not any(p in rel for p in path_contains):
                    continue
                m = rx.search(line)
                if not m:
                    continue
                # label = パターンが捕捉した文字列(ルートパス・コマンド名・cmd の値)
                # symbol = コードの識別子。デコレータ等では直後の定義行から拾う。
                # 両方持たせるのは、relations の impl が書くのは symbol の方だが、
                # 人間が読んで意味が分かるのは label の方だから(突き合わせは両方で行う)。
                label = ""
                if group and group <= len(m.groups()):
                    label = (m.group(group) or "").strip()
                symbol = nearby_symbol(lines, i)
                if symbol == "(不明)":
                    symbol = label or "(不明)"
                hits.append({
                    "kind": kind,
                    "path": rel,
                    "line": i + 1,
                    "symbol": symbol,
                    "label": label,
                    "note": note,
                    "source_line": line.strip()[:120],
                    "is_test": is_test(rel, markers),
                })
    # 同じ path:line に複数パターンが当たった場合は最初の1つだけ残す
    seen: set[tuple[str, int]] = set()
    out = []
    for h in hits:
        key = (h["path"], h["line"])
        if key in seen:
            continue
        seen.add(key)
        out.append(h)
    out.sort(key=lambda h: (h["path"], h["line"]))
    return out


def main(argv: list[str]) -> int:
    if any(a in ("-h", "--help") for a in argv[1:]):
        print(__doc__)   # 明示要求は 0。使い方エラーの 2 と区別する(tools-readme §2)
        return 0
    # **argv を1回だけ歩いて、値と位置引数を同時に確定する。**
    # 2回に分けて `--` の有無で振り分けると `--format json` の `json` が位置引数側に落ち、
    # 走査対象パスとして食われる。使い方欄(:14,:17)はスペース区切りで書いてあるので、
    # そのとおり打つと必ず失敗していた(KIT-two-scripts-accept-only-the-equals-form)。
    VALUED = {"--format", "--kind"}
    args: list[str] = []
    flags: dict[str, object] = {}
    i = 1
    while i < len(argv):
        a = argv[i]
        if a in VALUED and i + 1 < len(argv):
            flags[a] = argv[i + 1]; i += 2; continue      # 値を argv から消費する
        if a.startswith("--") and "=" in a:
            k, v = a.split("=", 1); flags[k] = v; i += 1; continue
        if a.startswith("--"):
            flags[a] = True; i += 1; continue
        args.append(a); i += 1

    if set(flags) - {"--format", "--kind", "--include-tests", "--include-tooling"}:
        print(__doc__)
        return 2
    fmt = flags.get("--format", "table")
    if fmt is True:
        fmt = "json"                                       # `--format` 単独は従来どおり json
    kinds: set[str] | None = None
    kv = flags.get("--kind")
    if isinstance(kv, str):
        kinds = {k.strip() for k in kv.split(",") if k.strip()}
    elif kv is True:                                       # 値の無い `--kind` は使い方エラー
        print(__doc__)
        return 2
    include_tests = flags.get("--include-tests", False) is True
    include_tooling = flags.get("--include-tooling", False) is True
    if fmt not in {"table", "tsv", "json"} or len(args) > 1:
        print(__doc__)
        return 2

    root = find_root(Path.cwd())
    scope = (root / args[0]).resolve() if args else root
    if not scope.exists():
        print(f"エラー: 対象が存在しない: {args[0]}")
        return 2

    cfg = load_config(root)
    hits = scan(root, scope, cfg, include_tests, kinds, include_tooling)

    if fmt == "json":
        print(json.dumps(hits, ensure_ascii=False, indent=2))
        return 0
    if fmt == "tsv":
        for h in hits:
            print(f"{h['kind']}\t{h['path']}:{h['line']}\t{h['symbol']}\t{h['note']}")
        return 0

    print(f"## エントリポイント候補: {scope.relative_to(root) if scope != root else '(リポジトリ全体)'}")
    print(f"検出 {len(hits)} 件"
          + ("" if include_tests else " / テストは除外(--include-tests で含める)")
          + ("" if include_tooling else " / 開発ツールは除外(--include-tooling で含める)"))
    if not hits:
        print("\n候補が1件も出なかった。パターンがこのスタックを覆っていない可能性がある。")
        print("→ .claude/scripts/entrypoint-patterns.local.json にパターンを追加すること。")
        print("  検出漏れを『エントリポイントが無い』と解釈してはならない。")
        return 0

    by_kind: dict[str, list[dict]] = {}
    for h in hits:
        by_kind.setdefault(h["kind"], []).append(h)
    for kind in sorted(by_kind):
        rows = by_kind[kind]
        print(f"\n### {kind} ({len(rows)} 件)")
        print("| 場所 | シンボル | 識別子(ルート/コマンド等) | 由来 |")
        print("|---|---|---|---|")
        for h in rows:
            label = f"`{h['label']}`" if h["label"] and h["label"] != h["symbol"] else "-"
            print(f"| `{h['path']}:{h['line']}` | `{h['symbol']}` | {label} | {h['note']} |")

    print("\n---")
    print("これは**候補**である。粒度の判断(1機能=1仕様ドキュメント、内部ヘルパは畳み込む、")
    print("モジュール境界で分ける)は .claude/directions/relations.md に従って行うこと。")
    print("誤検出は捨ててよいが、**捨てた理由をレポートに書く**こと。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
