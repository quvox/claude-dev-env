#!/usr/bin/env python3
"""機能表とコールグラフから、機能間の関係を機械的に導出する。

規範: .claude/directions/features.md / 設計: .claude/scripts/callgraph-design.md §8

境界(=どこを1機能とみなすか)さえ機能表で決まっていれば、
**モジュール境界での呼び出し単位の関係性は機械的に出せる**。これがその実装である。

  ① 各機能に属する関数集合                     → --format json のみ
  ② 複数機能から到達される共有関数(境界の実体) → docs/03-impl/feature-graph.md
  ③ 機能間の辺と呼び出し箇所                    → 〃(relations の callees: の材料)
  ④ どの入口からも到達しない関数                → 〃

出力は **(callgraph, 機能表) の純関数**である(design §8.3.1)。
実装と機能表が変わらなければ1バイトも変わらない。

使い方(フロー分離後、生成先は**常に SSOT** — .claude/directions/callgraphs.md §3.1。
廃止されたフェーズモデルの staged 出力は retired):
    python3 .claude/scripts/cluster-features.py              # SSOT へ生成
    python3 .claude/scripts/cluster-features.py --out <dir>   # 出力先を明示(--check にも効く)
    python3 .claude/scripts/cluster-features.py --check       # 鮮度検査(書き換えない)
    python3 .claude/scripts/cluster-features.py --format json # 中間表現(①を含む)
    python3 .claude/scripts/cluster-features.py --from cg.json # 抽出をやり直さない
    python3 .claude/scripts/cluster-features.py --selftest     # 決定性の自己検査

終了コード: 0=成功 1=機能表とコードが食い違う / --check で古い 2=使い方・解析エラー
"""

from __future__ import annotations

import importlib.util
import json
import random
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from cgx import base       # noqa: E402
from cgx import features as ft  # noqa: E402


def load_callgraph(root: Path, cfg: dict, from_json: str | None) -> dict:
    if from_json:
        return json.loads((root / from_json).read_text(encoding="utf-8"))
    spec = importlib.util.spec_from_file_location(
        "build_callgraphs", _HERE / "build-callgraphs.py")
    mod = importlib.util.module_from_spec(spec)            # type: ignore[arg-type]
    spec.loader.exec_module(mod)                            # type: ignore[union-attr]
    langs = [l for l, s in cfg["languages"].items() if s.get("enabled")]
    result, _notes = mod.run_extractors(root, cfg, langs, None)
    return result


def run_selftest(root: Path, cfg: dict, cg: dict, feats: list[dict]) -> int:
    """2回実行して同一 / **入力順を入れ替えても同一**(design §8.3.1)。

    後者を入れないと「呼び出し箇所を先着1本にする」「入口の重複を先着で決める」という
    決定性を壊す実装ミスが素通りする。
    """
    print("## 決定性の自己検査")
    a = ft.render_graph(ft.cluster(cg, feats, cfg), cfg)
    b = ft.render_graph(ft.cluster(cg, list(feats), cfg), cfg)
    if a != b:
        print("  NG  2回の実行で出力が違う")
        return 1

    rng = random.Random(20260801)
    shuffled = list(feats)
    rng.shuffle(shuffled)
    shuffled_cg = json.loads(json.dumps(cg))
    for data in shuffled_cg.get("languages", {}).values():
        for key in ("symbols", "edges", "endpoints", "unresolved"):
            if key in data:
                rng.shuffle(data[key])
    if "boundaries" in shuffled_cg:
        rng.shuffle(shuffled_cg["boundaries"])
    c = ft.render_graph(ft.cluster(shuffled_cg, shuffled, cfg), cfg)
    if a != c:
        print("  NG  **入力順を入れ替えると出力が変わる**(探索順に依存している)")
        return 1

    if "\t" in a or a.rstrip("\n").endswith(" "):
        print("  NG  整形が揺れている")
        return 1
    print("  OK  2回の実行が一致 / 機能表とシンボルの入力順を変えても一致")
    return 0


def main(argv: list[str]) -> int:
    if any(a in ("-h", "--help") for a in argv[1:]):
        print(__doc__)   # 明示要求は 0。使い方エラーの 2 と区別する(tools-readme §2)
        return 0
    args = argv[1:]
    fmt, check, selftest, from_json, out_dir = "md", False, False, None, None
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--check":
            check = True
        elif a == "--selftest":
            selftest = True
        elif a in {"--format", "--from", "--out"} and i + 1 < len(args):
            # **次がフラグなら「値の欠落」である。** `--out $CG_OUT --check` を引用符無しで
            # 書き、`$CG_OUT` が空だと `--out --check` になる。飲み込むと `--check` という名の
            # ディレクトリへ**書き込みが走る**(実測。独立レビュー B)。fail-closed にする。
            if args[i + 1].startswith("--"):
                print(f"エラー: {a} の値が無い(次がフラグ)。"
                      f"`{a} <値>` の形で、値は**引用符で囲む**こと。")
                return 2
            i += 1
            if a == "--format":
                fmt = args[i]
            elif a == "--out":
                out_dir = args[i]
            else:
                from_json = args[i]
        elif a.startswith("--format="):
            fmt = a.split("=", 1)[1]
        elif a.startswith("--from="):
            from_json = a.split("=", 1)[1]
        elif a.startswith("--out="):
            # `=` 形も同じ扱い(上と同じ理由)
            out_dir = a.split("=", 1)[1]
            if out_dir.startswith("--"):
                print("エラー: --out= の値がフラグである(値の欠落)。"
                      "`--out=\"$CG_OUT\"` のように値を渡すこと(変数が空なら解決からやり直す)。")
                return 2
        else:
            print(__doc__)
            return 2
        i += 1
    if fmt not in {"md", "json"}:
        print(__doc__)
        return 2

    root = base.find_root()
    base.ensure_kit_venv(root)
    cfg = base.load_config(root)
    fcfg = ft.feature_cfg(cfg)

    feats, ferrors = ft.load_features(root, cfg)
    if selftest and (ferrors or not feats):
        # キット自身のリポジトリ等、機能表の無い環境で「写して作れ」と誤誘導しない
        print("対象なし: 機能表が無い/空のため、決定性の自己検査は実データで走らせられない。")
        print("  機能表のあるプロジェクトで実行すること(**未検査は合格ではない**)。")
        return 0
    if ferrors:
        print("## 機能表が読めない")
        for e in ferrors:
            print("  - " + e)
        return 2
    if not feats:
        print("## 機能表が空である")
        print(f"  {fcfg['path']} に機能の行が無い。")
        print("  → `python3 .claude/scripts/propose-features.py` で候補を出し、"
              "人間が合意してから再実行する(.claude/directions/features.md §7)。")
        return 2

    cg = load_callgraph(root, cfg, from_json)
    result = ft.cluster(cg, feats, cfg)
    if result.get("errors"):
        print("## 機能表とコールグラフが食い違っている(FT1)")
        print("  **誤ったクラスタを出すより止める。** 機能表の入口を直すか、"
              "コードを直してから再実行する。")
        for e in result["errors"]:
            print("  - " + e)
        return 1

    #
    # **空文字列は既定へ落とさない**(build-callgraphs.py と同じ理由・同じ判定)。
    # 解決の失敗が空文字列として渡ると、`if out_dir:` が偽になって
    # `fcfg["graph_output"]` = SSOT の `feature-graph.md` を書き換える
    # (KIT-empty-out-falls-back-to-ssot。この2本が同型の全件である)。
    if out_dir is not None and not out_dir.strip():
        print("エラー: --out が空である。`resolve-callgraph-out.py` の失敗をそのまま渡していないか"
              "(失敗は stderr にだけ出るので `$(...)` は空になる)。\n"
              "  正しい形: CG_OUT=$(python3 .claude/scripts/resolve-callgraph-out.py) \\\n"
              "              && python3 .claude/scripts/cluster-features.py --out \"$CG_OUT\"\n"
              "  (スクリプトの中では `|| exit 2` でよい。**対話シェルに貼ると端末ごと終了する**)")
        return 2
    if selftest:
        return run_selftest(root, cfg, cg, feats)

    if fmt == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    rendered = ft.render_graph(result, cfg)
    _b, _e = base.note_markers("cluster-features.py")
    if rendered.count(_b) > 1 or rendered.count(_e) > 1:
        print("エラー: 生成する内容にマーカーが混ざっている")
        return 2
    # フロー分離後、生成先は常に SSOT(`.claude/directions/callgraphs.md` §3.1)。
    # --out を使うときは `build-callgraphs.py --out` と同じ値を渡す(呼び出し側が
    # `resolve-callgraph-out.py` に決めさせる)。
    rel_out = fcfg["graph_output"]
    if out_dir:
        # 呼び出し側は build-callgraphs.py と同じ値(= callgraphs の生成先)を渡す。
        # feature-graph.md はその1つ上(03-impl 直下)に置くのが SSOT 側と同じ配置である。
        d = Path(out_dir)
        rel_out = str((d.parent if d.name == "callgraphs" else d) / Path(rel_out).name)
    out_path = (root / rel_out).resolve()
    # **リポジトリの外へは書かせない**(build-callgraphs.py:575-579 と同じ封じ込め)。
    # ここが無いと `--out ../escaped` や `--out /tmp/abs` で `root /` が消え、
    # 実測でリポジトリ外に feature-graph.md が生成された(独立レビュー B の実測。
    # build 側は同じ入力を拒むので、**壊れた値が渡ったときの被害範囲が2本で違っていた**)。
    try:
        out_path.relative_to(root)
    except ValueError:
        print(f"エラー: --out はリポジトリ内を指すこと: {out_dir}")
        return 2

    if check:
        current = out_path.read_text(encoding="utf-8") if out_path.is_file() else None
        # **注記は比較しない**(build-callgraphs.py と同じ理由・同じ関数)
        if current is not None and base.without_note(current) == base.without_note(rendered):
            print(f"最新: {rel_out}")
            return 0
        if current == rendered:
            print(f"最新: {rel_out}")
            return 0
        print(f"**古い**: {rel_out}"
              f"{'(まだ生成されていない)' if current is None else ''}")
        print("  → `python3 .claude/scripts/cluster-features.py` で再生成する"
              "(生成先は常に SSOT — callgraphs.md §3.1)。")
        return 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered, encoding="utf-8")
    c = result["counts"]
    print(f"## {rel_out} を生成した")
    print(f"  機能 {c['features']} / 機能間の辺 {c['edges']}"
          f"(確定 {c['confirmed_edges']} / 候補 {c['candidate_edges']})"
          f" / 共有関数 {c['shared']} / 未到達 {c['unreached']}")

    missing = ft.missing_entrypoints(cg, result["roots"], cfg)
    if missing:
        print()
        print(f"### FT2: 機能表に無いエントリポイント {len(missing)} 件(**機能の取りこぼし**)")
        for m in missing:
            print("  - " + m)
        print("  → 機能表に足すか、足さない理由を人間が決める。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
