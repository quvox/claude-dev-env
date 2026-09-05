#!/usr/bin/env python3
"""コード群から docs/03-impl/callgraphs/ を生成する。

**これは機能間連携仕様書ではない。** ツールで機械的に導出できる事実だけを書き出す場所である
(規範: .claude/directions/callgraphs.md、設計: .claude/scripts/callgraph-design.md)。

決定性が前提: 実装が変わらなければ出力は1バイトも変わらない。
行番号・タイムスタンプ・絶対パスを含めず、すべてコードポイント順に整列する。
抽出器のバージョンは index.md にだけ書く(言語ファイルに書くとツール更新で全ファイルが差分になる)。

使い方(フロー分離後、生成先は**常に SSOT**(docs/03-impl/callgraphs/)である —
.claude/directions/callgraphs.md §3.1。廃止されたフェーズモデルの staged 出力は retired):
    python3 .claude/scripts/build-callgraphs.py                    # SSOT へ生成
    python3 .claude/scripts/build-callgraphs.py --lang python
    python3 .claude/scripts/build-callgraphs.py --scope src/api  # 範囲を絞る(部分生成に注意)
    python3 .claude/scripts/build-callgraphs.py --check           # 再生成したら差分が出るか
    python3 .claude/scripts/build-callgraphs.py --format json     # 中間表現(下流はこれを読む)
    python3 .claude/scripts/build-callgraphs.py --selftest        # 決定性の不変則を自己検査
    python3 .claude/scripts/build-callgraphs.py --out <dir>       # 出力先を明示(書き込みと --check の両方)

--out の値を自分で決めたいときは `resolve-callgraph-out.py` に任せること(生成先の決め方が
また変わっても、変わるのはそこ1箇所である):

    CG_OUT=$(python3 .claude/scripts/resolve-callgraph-out.py) && python3 .claude/scripts/build-callgraphs.py --out "$CG_OUT"
(この形は対話シェルへ貼れる。スクリプトの中なら `|| exit 2` でよい)

終了コード: 0=成功(--check なら差分なし) 1=--check で差分あり 2=使い方・設定エラー
"""

from __future__ import annotations

import importlib
import json
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cgx import EXTRACTORS, PLANNED  # noqa: E402
from cgx import base                 # noqa: E402
from cgx import boundaries as _bnd   # noqa: E402
from cgx import resources as _res    # noqa: E402

GENERATED_NOTE = base.wrap_note(
    "build-callgraphs.py",
    "<!-- 生成物。手書き禁止。`python3 .claude/scripts/build-callgraphs.py` で再生成する\n"
    "     (生成先は常に SSOT — .claude/directions/callgraphs.md §3.1)。\n"
    "     辞書順に固定されており、実装が変わらなければこのファイルも変わらない。\n"
    "     **これは機能間連携仕様書ではない**(.claude/directions/callgraphs.md)。 -->"
)


# --------------------------------------------------------------------------- 抽出

def run_extractors(root: Path, cfg: dict, langs: list[str],
                   scope: Path | None) -> tuple[dict, list[str]]:
    result: dict = {"schema_version": "1", "languages": {}}
    notes: list[str] = []
    result["config"] = {
        "internal_roots": sorted(cfg.get("internal_roots", [])),
        "excludes": sorted(cfg.get("excludes", [])),
    }
    for lang in langs:
        if lang not in EXTRACTORS:
            notes.append(f"{lang}: 抽出器が未実装({PLANNED.get(lang, '未計画')})。この言語は出力されない")
            continue
        try:
            data = importlib.import_module(EXTRACTORS[lang]).extract(root, cfg, scope)
        except (ImportError, RuntimeError) as exc:
            # 依存ライブラリ(tree-sitter / PyYAML)は go / typescript / infra の**必須依存**で、
            # 縮退経路は無い — 欠けた地図で検査を完走させるより、ここで止まって直させる
            # (fail-closed。inspection-17 判断1)。traceback ではなく直し方を1行で言う。
            print(f"エラー: {lang} の抽出器を起動できない — {exc}", file=sys.stderr)
            print("直し方: python3 .claude/scripts/setup-tools.py を実行してキット専用 venv に"
                  "依存を導入する。その言語を解析しない選択は callgraph-config.local.json で "
                  f'"languages": {{"{lang}": {{"enabled": false}}}} と明示する', file=sys.stderr)
            raise SystemExit(2)
        # infra 抽出器は routing(パス転送)を返す。これは言語横断の情報なので最上位へ移す。
        routing = data.pop("routing", None)
        http = data.pop("http_calls", None)
        refs = data.pop("resource_refs", None)
        events = data.pop("event_sources", None)
        envs = data.pop("env_bindings", None)
        result["_iam_wildcard"] = result.get("_iam_wildcard", 0) + data.pop("iam_wildcard", 0)
        data.pop("scanned_files", None)
        if http:
            result.setdefault("_http_calls", []).extend(http)
        if refs:
            result.setdefault("_resource_refs", []).extend(refs)
        if events:
            result.setdefault("_event_sources", []).extend(events)
        if envs:
            result.setdefault("_env_bindings", []).extend(envs)
        if routing:
            result.setdefault("routing", []).extend(routing)
        result["languages"][lang] = data
    if result["languages"]:
        # 順序に意味がある: イベント源をエンドポイントに確定させ(ハンドラの実在判定が要る)、
        # 資源を集約してから(queue の突合が資源表を使う)、境界を結ぶ。
        _bnd.bind_event_sources(result)
        res_list, res_stats = _res.collect(result, cfg)
        if res_list:
            result["resources"] = res_list
        result["resource_stats"] = res_stats
        bnds, orphans = _bnd.join(result)
        for tmp in ("_http_calls", "_resource_refs", "_env_bindings", "_iam_wildcard"):
            result.pop(tmp, None)
        if bnds:
            result["boundaries"] = bnds
        if orphans:
            result["orphan_endpoints"] = orphans
    return result, notes


# --------------------------------------------------------------------------- 出力

def _table(headers: list[str], rows: list[list[str]]) -> list[str]:
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    if not rows:
        out.append("|" + "|".join(" (なし) " if i == 0 else " - "
                                  for i in range(len(headers))) + "|")
        return out
    out.extend("| " + " | ".join(base.escape_cell(c) for c in r) + " |" for r in rows)
    return out


def render_language(lang: str, data: dict) -> str:
    callees: dict[str, list[str]] = {}
    callers: dict[str, list[str]] = {}
    for e in data["edges"]:
        callees.setdefault(e["from"], []).append(e["to"])
        callers.setdefault(e["to"], []).append(e["from"])
    handlers = {e["handler"] for e in data["endpoints"] if e["handler"]}

    lines = [
        "---",
        f"id: {lang}",
        f"language: {lang}",
        f"tier: {data['tier']}",
        f"symbols: {len(data['symbols'])}",
        f"edges: {len(data['edges'])}",
        f"endpoints: {len(data['endpoints'])}",
        f"unresolved: {len(data['unresolved'])}",
        "---",
        "",
        GENERATED_NOTE,
        "",
        f"# {lang} コールグラフ (Tier {data['tier']})",
        "",
        "## エントリポイント",
        "",
    ]
    lines += _table(
        ["種別", "識別子", "正規化キー", "ハンドラ", "検出根拠"],
        [[e["protocol"], f"`{e['id']}`", f"`{e['path_key']}`",
          f"`{e['handler']}`" if e["handler"] else "(特定できず)", e["source"]]
         for e in data["endpoints"]])

    lines += ["", "## 関数表", ""]
    lines += _table(
        ["シンボル", "種別", "可視性", "呼び出す先", "呼び出し元"],
        [[f"`{s['id']}`", s["kind"], s["visibility"],
          ", ".join(f"`{c}`" for c in sorted(set(callees.get(s["id"], [])))) or "-",
          ", ".join(f"`{c}`" for c in sorted(set(callers.get(s["id"], []))))
          or ("(エントリポイント)" if s["id"] in handlers else "-")]
         for s in data["symbols"]])

    lines += ["", "## 解決できなかった呼び出し", "",
              "<!-- 空欄は「呼び出しが無い」を意味する。解決できなかったものは必ずここに出る。 -->",
              ""]
    lines += _table(
        ["呼び出し元", "呼び出し式", "分類", "候補"],
        [[f"`{u['from']}`", f"`{u['expression']}`", u["reason"],
          ", ".join(f"`{c}`" for c in u.get("candidates", [])) or "-"]
         for u in data["unresolved"]])
    lines.append("")
    return "\n".join(lines)


def top_directories(data: dict, depth: int = 3, top: int = 5) -> list[tuple[str, int, int]]:
    """シンボルが集中しているディレクトリ。ベンダリングされた第三者ライブラリの発見用。

    実データで、Lambda レイヤに同梱された urllib3 等がシンボルの 46% を占めていて
    誤った ambiguous を量産していた。**混ざっていること自体は誰も教えてくれない**ので、
    黙って数えて見せる(判断は人間がする)。
    """
    counts: dict[str, int] = {}
    total = len(data["symbols"])
    if total == 0:
        return []
    for s in data["symbols"]:
        parts = s["file"].split("/")
        if len(parts) > depth:
            key = "/".join(parts[:depth])
            counts[key] = counts.get(key, 0) + 1
    rows = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:top]
    return [(k, n, n * 100 // total) for k, n in rows]


def render_index(result: dict, notes: list[str]) -> str:
    langs = result["languages"]
    lines = [
        "---",
        "id: index",
        f"languages: {len(langs)}",
        "---",
        "",
        GENERATED_NOTE,
        "",
        "# コールグラフ 目次",
        "",
        "## 言語ごとの状態",
        "",
    ]
    lines += _table(
        ["言語", "Tier", "抽出器", "シンボル", "辺", "エンドポイント", "未解決", "外部呼び出し", "降格理由"],
        [[f"[{lang}]({lang}.md)", str(d["tier"]), d["extractor"],
          str(len(d["symbols"])), str(len(d["edges"])), str(len(d["endpoints"])),
          str(len(d["unresolved"])), str(d.get("external_call_count", 0)),
          d.get("degraded_reason", "-")]
         for lang, d in sorted(langs.items())])

    lines += ["", "## Tier の意味", "",
              "| Tier | 手段 | 保証 |", "|---|---|---|",
              "| 1 | 索引器・言語ツールチェーン | 型解決済み・跨ファイル正確 |",
              "| 2 | 構文解析 + 名前解決 | 同名衝突は `ambiguous` として候補列挙 |",
              "| 3 | 正規表現 | 定義とエンドポイントのみ。**呼び出し関係は不完全** |",
              "",
              "**Tier 3 の結果を「網羅した」と報告してはならない。**", ""]

    vendored: list[list[str]] = []
    for lang, d in sorted(langs.items()):
        for v in d.get("vendored_dirs", []):
            vendored.append([lang, f"`{v}/`"])
    lines += ["## 解析対象から外したもの", "",
              "<!-- ベンダリングされた第三者ライブラリ・テスト・開発ツールは解析対象にしない",
              "     (.claude/directions/callgraphs.md §5.3 / features.md §0.1)。",
              "     **黙って外すと「網羅した」という誤読を生む**のでここに出す。 -->", ""]
    lines += _table(["言語", "ディレクトリ(第三者ライブラリ)"], vendored)
    lines.append("")

    # **パスまで出す。** 目印の書き方を誤ると誤除外が起きる(`cgx/base.py` の `is_test`)。
    # 件数だけでは誤除外を特定できない。
    SHOWN = 10
    skipped_rows: list[list[str]] = []
    for lang, d in sorted(langs.items()):
        sk = d.get("skipped_files") or {}
        for cat, label in (("tests", "テスト"), ("tooling", "開発ツール"),
                          ("guards", "宣言したガード節"),
                          ("guard_misses", "**効かなかった宣言**")):
            paths = sorted(sk.get(cat) or [])
            if not paths:
                continue
            shown = ", ".join(f"`{p}`" for p in paths[:SHOWN])
            if len(paths) > SHOWN:
                shown += f" ほか {len(paths) - SHOWN} 件"
            skipped_rows.append([lang, label, str(len(paths)), shown])
    lines += ["<!-- 開発ツール = Makefile / CI 定義 / compose 等。判定は tooling_markers。",
              "     本番実行系から到達しないものは機能ではない(features.md §0.1)。",
              "     **ここに本番コードが並んでいたら誤除外である。** callgraph-config.local.json の",
              "     *_markers を絞ること。照合規則(目印の形で決まる)は directions/callgraphs.md",
              "     §5.9.1 の表を見る。",
              "     宣言したガード節 = dispatch_guards で入口から外した分岐(§5.7)。",
              "     **効かなかった宣言 = 綴り違いか、コードから消えたガードである。**",
              "     効いていないものが並んでいたら、宣言を直すか消すこと"
              "(黙って外さないための行である)。 -->", ""]
    lines += _table(["言語", "種別", "件数", "ファイル / 宣言"], skipped_rows)
    lines.append("")

    lines += ["## シンボルが集中しているディレクトリ", "",
              "<!-- 第三者ライブラリのベンダリングが混ざっていないかを見るための表。",
              "     混ざっていたら callgraph-config.local.json の excludes に入れること。 -->", ""]
    dir_rows: list[list[str]] = []
    for lang, d in sorted(langs.items()):
        for path, n, pct in top_directories(d):
            dir_rows.append([lang, f"`{path}/`", str(n), f"{pct}%"])
    lines += _table(["言語", "ディレクトリ", "シンボル", "割合"], dir_rows)
    lines.append("")

    cfg = result.get("config", {})
    lines += ["## 設定", "",
              f"- internal_roots: {', '.join(f'`{r}`' for r in cfg.get('internal_roots', [])) or '-'}",
              f"- excludes: {', '.join(f'`{r}`' for r in cfg.get('excludes', [])) or '-'}",
              ""]

    lines += ["## 注記", ""]
    lines += [f"- {n}" for n in notes] or ["- なし"]
    lines.append("")
    return "\n".join(lines)


def render_infra(result: dict) -> str:
    routing = result.get("routing", [])
    infra = result["languages"].get("infra", {})
    events = [e for e in infra.get("endpoints", [])
              if e["protocol"] in {"event", "schedule"}]
    lines = ["---", "id: infra", f"routes: {len(routing)}",
             f"event_sources: {len(events)}", "---", "", GENERATED_NOTE, "",
             "# インフラのパス転送", "",
             "<!-- サーバレス構成では REST のパスがコードではなくインフラ定義側にある。",
             "     ここが埋まらないと「このパスはどのハンドラに届くか」が永久に分からない。 -->", ""]
    lines += _table(["種別", "メソッド", "パス", "正規化キー", "転送先", "ハンドラの手掛かり", "定義元"],
                    [[r["kind"], r["match"]["method"], f"`{r['match']['path_pattern']}`",
                      f"`{r['match']['path_key']}`",
                      f"{r['target']['type']}:{r['target']['ref']}" if r["target"]["ref"] else "-",
                      f"`{r['target']['handler_hint']}`" if r["target"]["handler_hint"] else "-",
                      r["source"]] for r in routing])

    lines += ["", "## API 以外のイベント源", "",
              "<!-- キュー・トピック・ストリーム・定時起動で動く機能は、REST の経路を持たない。",
              "     ここを読まないと、その機能は永久に「呼び出し元不明」のままになる。",
              "     ハンドラが言語側に実在しなかったものは infra の未解決表に出る。 -->", ""]
    lines += _table(["種別", "識別子", "ハンドラ", "定義元"],
                    [[e["protocol"], f"`{e['id']}`", f"`{e['handler']}`", e["source"]]
                     for e in events])

    lines += ["", "## 解決できなかったインフラ定義", ""]
    lines += _table(["定義元", "内容", "分類"],
                    [[f"`{u['from']}`", u["expression"], u["reason"]]
                     for u in infra.get("unresolved", [])])
    lines.append("")
    return "\n".join(lines)


def render_boundaries(result: dict) -> str:
    bnds = result.get("boundaries", [])
    orphans = result.get("orphan_endpoints", [])
    lines = ["---", "id: boundaries", f"edges: {len(bnds)}",
             f"orphan_endpoints: {len(orphans)}", "---", "", GENERATED_NOTE, "",
             "# 言語・プロセスを跨ぐ辺(候補)", "",
             "<!-- **REST の呼び出し元はツールでは確定できない。** ここに出るのは候補であり、",
             "     確度を必ず持つ。埋めるのは AI の仕事(.claude/directions/callgraphs.md §5.10)。 -->",
             ""]
    lines += _table(["種別", "確度", "呼び出し元", "宛先", "根拠"],
                    [[b["kind"], b["confidence"], f"`{b['from']}`" if b["from"] else "(不明)",
                      f"`{b['to']}`", b["evidence"]] for b in bnds])
    lines += ["", "## 呼び出し元が特定できなかったエンドポイント", "",
              "<!-- これが AI に渡される宿題そのものである。 -->", ""]
    lines += _table(["エンドポイント"], [[f"`{o}`"] for o in orphans])
    lines.append("")
    return "\n".join(lines)


def render_resources(result: dict) -> str:
    """共有データストア結合(P10)。**呼び出し辺として存在しない連携**の材料である。"""
    rows = result.get("resources", [])
    st = result.get("resource_stats", {})
    lines = ["---", "id: resources", f"resources: {len(rows)}",
             f"refs: {st.get('refs', 0)}", "---", "", GENERATED_NOTE, "",
             "# 資源の参照(共有データストア結合)", "",
             "<!-- サーバレス/イベント駆動では、連携の相当部分が**呼び出し辺として原理的に",
             "     存在しない**。A が書き B が読むという結合は callgraph に一切出ないので、",
             "     ここで資源の側から拾う(.claude/directions/callgraphs.md §5.11)。",
             "     機能単位への畳み込みは feature-graph.md が行う。 -->", "",
             "資源名の `{}` は**変数で組み立てられた区間**である"
             "(`\"caseDataTbl\" + os.environ[\"HASHSALT\"]` → `caseDataTbl{}`)。",
             "`$VAR` は実資源に解決できなかった環境変数、`#Logical` は実名の分からない"
             "インフラ資源で、**どちらも結合のキーとしては十分に働く**。", "",
             "`permission` は IAM 由来で、**使っている証拠ではなく使える上界**である。", "",
             "## 資源と、それを触るシンボル", ""]
    body: list[list[str]] = []
    for r in rows:
        for ref in r["refs"]:
            body.append([f"`{r['key']}`", ref["access"], ref["confidence"],
                         f"`{ref['symbol']}`", ref["evidence"]])
    lines += _table(["資源", "アクセス", "確度", "シンボル", "根拠"], body)

    lines += ["", "## 資源とみなさなかった環境変数", "",
              "<!-- ここで絞らないと DEPLOY_ENV のような全モジュールが読む変数が",
              "     『全機能が触る資源』になって信号が埋もれる。**黙って落とさない**ために出す。",
              "     資源なら callgraph-config.json の resources.env_patterns に足すこと。 -->", ""]
    lines += _table(["環境変数", "参照数"],
                    [[f"`{name}`", str(n)] for name, n in st.get("dropped_env_names", [])])
    lines += ["",
              f"- 対象外にした環境変数: {st.get('dropped_env_distinct', 0)} 種 / "
              f"{st.get('dropped_env', 0)} 参照(上位のみ表示)",
              f"- 環境変数から実資源に解決できたもの: {st.get('env_resolved', 0)} 参照",
              f"- 資源を限定しない IAM 文(`Resource: '*'`)を持つ関数: "
              f"{st.get('iam_wildcard', 0)}(**上界として使えないので結合に入れていない**)",
              ""]
    return "\n".join(lines)


def render_all(result: dict, notes: list[str]) -> dict[str, str]:
    out = {"index.md": render_index(result, notes)}
    for lang, data in result["languages"].items():
        if lang == "infra":
            continue                      # infra は routing 表として別に描く
        out[f"{lang}.md"] = render_language(lang, data)
    if result.get("routing") or result["languages"].get("infra", {}).get("endpoints"):
        out["infra.md"] = render_infra(result)
    if result.get("boundaries") or result.get("orphan_endpoints"):
        out["boundaries.md"] = render_boundaries(result)
    if result.get("resources"):
        out["resources.md"] = render_resources(result)
    return out


# --------------------------------------------------------------------------- 自己検査

def _selftest_ts_fixture() -> list[str]:
    """TS 抽出器の回帰フィクスチャ。

    クラスプロパティに代入された関数(`public m = () => {}`)は TS で `this` 束縛を
    避けるための定石だが、tree-sitter は `method_definition` ではなく
    `public_field_definition` で返す。ここを落とすと記号が消えるだけでなく、
    **同名の別記号へ一意に解決されて確度「確定」の偽の辺が出る**(候補辺より有害)。
    一度きりのフィクスチャでは再発を検出できないので、恒久の検査として固定する。
    """
    try:
        from cgx import ts_treesitter as _ts
    except Exception as exc:                       # 抽出器が無い環境では検査しない
        return [f"typescript: 抽出器を読み込めない({exc})"]
    src = (b"export class Ctl {\n"
           b"  public loadAll = async () => { helper(); };\n"
           b"  private inner = () => { return 1; };\n"
           b"  normalMethod() { return 2; }\n"
           b"  public data = { a: 1 };\n"
           b"}\n"
           b"export const helper = () => { return 3; };\n")
    out: list[str] = []
    for label, parser in zip(("ts", "tsx"), _ts._load_parsers()):
        symbols: list[dict] = []
        _ts._collect("fixture.ts", src, parser.parse(src).root_node, symbols)
        got = {s["name"] for s in symbols}
        want = {"Ctl", "Ctl.loadAll", "Ctl.inner", "Ctl.normalMethod", "helper"}
        if missing := want - got:
            out.append(f"typescript({label}): フィクスチャの記号が欠落: {sorted(missing)}")
        if "Ctl.data" in got:
            out.append(f"typescript({label}): 関数でないフィールドを記号化している: Ctl.data")
    return out


_GO_FIXTURE = {
    "go.mod": "module example.com/fx\n\ngo 1.22\n",
    "alpha/alpha.go": ("package command\n\nfunc Run(args []string) int { return 0 }\n\n"
                       "func Handle(w int, r int) {}\n\n"
                       "type T struct{}\n\nfunc New() *T { return nil }\n\n"
                       "func (t *T) Do() int { return 7 }\n"),
    "bar/bar.go": "package baz\n\nfunc Shared() int { return 1 }\n",
    # `net/http` ではない `ServeMux`。**修飾を捨てると `net/http.ServeMux` と見分けが付かず**、
    # ホストを落とす側へ倒れて相対経路が化ける(2026-09-01 の実測)。恒久の題材として固定する。
    "myrouter/myrouter.go": ("package myrouter\n\ntype ServeMux struct{}\n\n"
                             "func (m *ServeMux) Handle(p string, h int) {}\n"),
    "named/named.go": "package bar\n\nfunc Shared() int { return 2 }\n",
    # `Handle` を2つ置くのは、6 を**最後の手段の索きの実装から独立させる**ためである。
    # 1つしか無いと、その索きがパッケージ関数を候補に含む実装へ戻ったとき、import の解決を
    # 落としても偶然に当たってしまい、検査が素通りする(直す前の実装が実際にそうだった)。
    "other/other.go": ("package other\n\nfunc F() int { return 3 }\n\n"
                       "func Handle(w int, r int) {}\n"),
    # `U.Do` は、`command.New()` の戻り型を取り逃したときに `Do` が2候補になって
    # 辺が立たなくなるようにするための相方である(7 を効かせるための配置)。
    "q/q.go": ("package qq\n\nfunc F() int { return 4 }\n\n"
               "type U struct{}\n\nfunc (u *U) Do() int { return 8 }\n"),
    "app/app.go": (
        'package app\n\nimport (\n\t"net/http"\n\th "net/http"\n\t"os/exec"\n\n\t"example.com/fx/alpha"\n'
        '\t"example.com/fx/bar"\n\t"example.com/fx/myrouter"\n\t"example.com/fx/named"\n\tq "example.com/fx/other"\n'
        '\t"example.com/fx/q"\n\n\t"github.com/go-chi/chi/v5"\n)\n\n'
        'type holder struct {\n\tF   func() int\n\tNew func() *qq.U\n}\n\n'
        'var registry map[string]holder\n\n'
        # 引数が同名のパッケージ変数を遮蔽する題材(両向き)
        'var shadowMux *http.ServeMux\n\n'
        'var shadowMux2 *myrouter.ServeMux\n\n'
        'func local() int { return 5 }\n\n'
        'func localNew() *qq.U { return nil }\n\n'
        # import の呼び名 `http` をローカル変数で覆うための型
        'type localFactory struct{}\n\n'
        'func (l localFactory) NewServeMux() *myrouter.ServeMux { return nil }\n\n'
        # 自前の生成器。戻り型の修飾が解ければ ServeMux と判る(`return_type_q`)
        'func NewServeMux() *http.ServeMux { return nil }\n\n'
        'func UseDeclName() int { return command.Run(nil) }\n\n'
        'func UseDeclOverTail() int { return bar.Shared() }\n\n'
        'func UseAlias() int { return q.F() }\n\n'
        'func UseShadowed() int {\n\tq := holder{F: local}\n\treturn q.F()\n}\n\n'
        'func UseUntypedShadow() int {\n\tq := registry["k"]\n\treturn q.F()\n}\n\n'
        'func UseCtor() int {\n\tx := command.New()\n\treturn x.Do()\n}\n\n'
        'func UseShadowedCtor() int {\n\tcommand := holder{New: localNew}\n'
        '\tx := command.New()\n\treturn x.Do()\n}\n\n'
        'func UseStdlib() error {\n\tcmd := exec.Command("ls")\n\treturn cmd.Run()\n}\n\n'
        'func Routes() {\n\tmux := http.NewServeMux()\n'
        '\tmux.HandleFunc("/ping", command.Handle)\n'
        '\tmux.HandleFunc("GET /pong", command.Handle)\n'
        '\tmux.Handle("POST example.com/hosted", nil)\n'
        '\tmux.HandleFunc("PROPFIND /dav", command.Handle)\n'
        '\tmux.HandleFunc("example.com/hosted2", command.Handle)\n'
        # 大文字でないメソッド。Go では合法だがこの抽出器は表せないので、**経路を作らずに落とす**
        '\tmux.Handle("get /lower", nil)\n'
        # 自前の生成器の戻り値。ここもホストを落とす
        '\tm2 := NewServeMux()\n'
        '\tm2.Handle("GET example.com/hosted5", nil)\n\n'
        '\tr := chi.NewRouter()\n'
        '\tr.Get("POST /nope", command.Handle)\n'
        '\tr.Handle("users/{id}", command.Handle)\n'
        # 外側の `mux` は ServeMux だが、入れ子で別のルータへ束ね直している。
        # 集合に `mux` が残っていると、ここの相対経路の頭を削る。
        '\tr.Route("/v1", func(r chi.Router) {\n'
        '\t\tmux := chi.NewRouter()\n'
        '\t\tmux.Handle("team/{tid}", command.Handle)\n'
        '\t})\n}\n\n'
        # ★ ここから下は「受け手が ServeMux かどうか」を**生成器を通さずに型だけで**
        # 判る側の題材である。`http.NewServeMux()` しか題材が無いと、型から判る経路が
        # 丸ごと壊れても検査が素通りする(2026-09-01 の実測でそれが起きた)。
        'type CustomServeMux struct{}\n\n'
        'func (c *CustomServeMux) Handle(p string, h int) {}\n\n'
        'func RoutesTyped(mux *http.ServeMux, cm *CustomServeMux,\n'
        '\t\tmr *myrouter.ServeMux, am *h.ServeMux) {\n'
        # 明示型の `*http.ServeMux`。生成器を通らないので**型から判る側**の題材である
        '\tmux.Handle("GET example.com/hosted3", nil)\n'
        # `import h "net/http"` の別名。**別名でもホストを落とす**
        '\tam.Handle("GET example.com/hosted4", nil)\n'
        # 名前に ServeMux を含むだけの独自ルータ。**ホストを落としてはならない**
        '\tcm.Handle("tenant/path", nil)\n'
        # 修飾が違うだけの同名型。**ここもホストを落としてはならない**
        '\tmr.Handle("tenant2/path2", nil)\n}\n\n'
        # ★ 型付きの外側 `mux` を、内側の関数リテラルで chi の変数が隠す。`_collect_locals` は
        # リテラルの中まで平らに集めるので、型の辞書を直接引くと**隠したのに外側の型が返り**、
        # 相対経路の頭が削れる(2026-09-01 の実測: `ANY /tenant3/path3` が `ANY /path3` に化けた)。
        'func RoutesShadow(mux *http.ServeMux, r chi.Router) {\n'
        '\tmux.Handle("GET example.com/hosted6", nil)\n'
        '\tr.Route("/v2", func(r chi.Router) {\n'
        '\t\tmux := chi.NewRouter()\n'
        '\t\tmux.Handle("tenant3/path3", nil)\n'
        '\t})\n}\n\n'
        # ★ 素の字句ブロックでの遮蔽。**ブロックを出たら外側の型が戻らなければならない。**
        # 同じ集合を渡していると遮蔽がブロックの外まで残り、`GET /after` が
        # `GET /example.com/after` に化ける(2026-09-01 の実測)。
        'func RoutesBlock(mux *http.ServeMux) {\n'
        '\t{\n'
        '\t\tmux := chi.NewRouter()\n'
        '\t\tmux.Handle("tenant4/path4", nil)\n'
        '\t}\n'
        '\tmux.Handle("GET example.com/after", nil)\n}\n\n'
        # ★ `if` の初期化文での遮蔽。`x := …` は if の中だけに効くので、**if を出たら戻る**
        'func RoutesIf(mux *http.ServeMux, cond bool) {\n'
        '\tif mux := chi.NewRouter(); cond {\n'
        '\t\tmux.Handle("tenant5/path5", nil)\n'
        '\t}\n'
        '\tmux.Handle("GET example.com/after2", nil)\n}\n\n'
        # ★ 外側と内側が**互いに違う明示型**を持つ遮蔽。収集は内側ブロックの中まで平らに
        # 見るので、走査の前に種を作ると内側の型が外側を上書きする(2026-09-01 の実測:
        # 外側の2件が `GET /example.com/before8` `GET /example.com/after8` に化けた)。
        'func RoutesTypedShadow(mux *http.ServeMux) {\n'
        '\tmux.Handle("GET example.com/before8", nil)\n'
        '\t{\n'
        '\t\tvar mux *myrouter.ServeMux\n'
        '\t\tmux.Handle("tenant8/path8", nil)\n'
        '\t}\n'
        '\tmux.Handle("GET example.com/after8", nil)\n}\n\n'
        # ★ 逆向き。外側が独自型、内側が `*http.ServeMux`。外側でホストを落としてはならず、
        # 内側では落とさなければならない
        'func RoutesTypedShadowRev(mux *myrouter.ServeMux) {\n'
        '\tmux.Handle("tenant9/path9", nil)\n'
        '\t{\n'
        '\t\tvar mux *http.ServeMux\n'
        '\t\tmux.Handle("GET example.com/hosted9", nil)\n'
        '\t}\n'
        '\tmux.Handle("tenant9b/path9b", nil)\n}\n\n'
        # ★ 引数が同名のパッケージ変数を遮蔽する。和集合で種を作ると遮蔽が効かない
        'func RoutesPkgShadow(shadowMux *myrouter.ServeMux) {\n'
        '\tshadowMux.Handle("tenant10/path10", nil)\n}\n\n'
        'func RoutesPkgShadowRev(shadowMux2 *http.ServeMux) {\n'
        '\tshadowMux2.Handle("GET example.com/hosted10", nil)\n}\n\n'
        # ★ 既知の生成器を通さない束縛(複合リテラル)。**まず消してから、証明できたら足す**
        'func RoutesLit(mux *http.ServeMux) {\n'
        '\t{\n'
        '\t\tmux := &myrouter.ServeMux{}\n'
        '\t\tmux.Handle("tenant11/path11", nil)\n'
        '\t}\n'
        '\tmux.Handle("GET example.com/after11", nil)\n}\n\n'
        'func RoutesLitMux() {\n'
        '\tmux := &http.ServeMux{}\n'
        '\tmux.Handle("GET example.com/hosted11", nil)\n}\n\n'
        # ★ 関数リテラルの引数が外側の名前を遮蔽する(両向き)
        'func RoutesClosure(mux *http.ServeMux, r chi.Router) {\n'
        '\tr.Route("/v3", func(mux chi.Router) {\n'
        '\t\tmux.Handle("tenant12/path12", nil)\n'
        '\t})\n'
        '\tmux.Handle("GET example.com/after12", nil)\n}\n\n'
        'func RoutesClosureRev(mux *myrouter.ServeMux) {\n'
        '\tfunc(mux *http.ServeMux) {\n'
        '\t\tmux.Handle("GET example.com/hosted12", nil)\n'
        '\t}(nil)\n'
        '\tmux.Handle("tenant12b/path12b", nil)\n}\n\n'
        # ★ 型を書かない `var`。**束縛なので、型が無くても集合へ反映しなければならない**
        'func RoutesVarNoType(mux *http.ServeMux) {\n'
        '\t{\n'
        '\t\tvar mux = &myrouter.ServeMux{}\n'
        '\t\tmux.Handle("tenant13/path13", nil)\n'
        '\t}\n'
        '\tmux.Handle("GET example.com/after13", nil)\n}\n\n'
        'func RoutesVarNoTypeMux() {\n'
        '\tvar mux = &http.ServeMux{}\n'
        '\tmux.Handle("GET example.com/hosted13", nil)\n}\n\n'
        # ★ 複数名の宣言。**左辺と右辺を位置で対応させる**。先頭だけを見て左辺全部に配ると、
        # 後ろの名前まで ServeMux になる(2026-09-01 の実測)。順序を逆にした形も置く
        'func RoutesMulti() {\n'
        '\thttpMux, customMux := &http.ServeMux{}, &myrouter.ServeMux{}\n'
        '\thttpMux.Handle("GET example.com/hosted14", nil)\n'
        '\tcustomMux.Handle("tenant14/path14", nil)\n}\n\n'
        'func RoutesMultiRev() {\n'
        '\tcustomMux2, httpMux2 := &myrouter.ServeMux{}, &http.ServeMux{}\n'
        '\tcustomMux2.Handle("tenant15/path15", nil)\n'
        '\thttpMux2.Handle("GET example.com/hosted15", nil)\n}\n\n'
        # `var` の側にも同じ位置対応が要る
        'func RoutesMultiVar() {\n'
        '\tvar httpMux3, customMux3 = &http.ServeMux{}, &myrouter.ServeMux{}\n'
        '\thttpMux3.Handle("GET example.com/hosted16", nil)\n'
        '\tcustomMux3.Handle("tenant16/path16", nil)\n}\n\n'
        # ★ 明示型の複数名。`_field` の先頭1つだけを見ると、2つ目の経路が丸ごと消える
        'func RoutesMultiTyped() {\n'
        '\tvar httpMux17, httpMux17b *http.ServeMux\n'
        '\thttpMux17.Handle("GET example.com/hosted17", nil)\n'
        '\thttpMux17b.Handle("GET example.com/hosted17b", nil)\n}\n\n'
        # ★ ローカル変数が import の呼び名 `http` を覆う。`http.NewServeMux()` はもう
        # `net/http` のものではないので、ホストを落としてはならない
        'func RoutesShadowImport() {\n'
        '\thttp := localFactory{}\n'
        '\tmux := http.NewServeMux()\n'
        '\tmux.Handle("tenant18/path18", nil)\n}\n\n'
        # ★ 別名束縛。証明済みの名前を束ね直しただけなら、証明は移らなければならない
        'func RoutesAlias(srcMux *http.ServeMux) {\n'
        '\taliasMux := srcMux\n'
        '\taliasMux.Handle("GET example.com/alias19", nil)\n'
        '\tvar aliasVar = srcMux\n'
        '\taliasVar.Handle("GET example.com/alias20", nil)\n}\n\n'
        # ★ 代入と入れ替え。代入も束縛が変わる場所であり、右辺は先に評価する
        'func RoutesAssign(srcMux *http.ServeMux, other *myrouter.ServeMux) {\n'
        '\tsrcMux, other = other, srcMux\n'
        '\tsrcMux.Handle("tenant21/path21", nil)\n'
        '\tother.Handle("GET example.com/alias21", nil)\n}\n'),
}


def _selftest_go_fixture(cfg: dict) -> list[str]:
    """Go 抽出器の名前解決の回帰フィクスチャ。

    ここが崩れると**確度「確定」の偽の辺**が出る。候補辺と違い機能表の棄却では抑止できず、
    偽の辺1本が到達集合を丸ごと汚して実装整合フローを構造的に green にできなくする
    (2026-08-31 の実測では `cmd.Run()` の1本が CG4 の重大度「高」を111件生んだ)。
    **一度きりの題材では再発を検出できない**ので、恒久の検査として固定する。

    固定するのは次の9つで、どれも「呼び名がどのパッケージを指すか」の順序に関わる:

    1. 標準ライブラリのメソッド呼び出しが、同名のパッケージ関数へ解決されないこと
    2. 宣言されたパッケージ名がパス末尾と違う import が解決できること
    3. 2 の宣言名が、別の import のパス末尾からの推測に**勝つ**こと
    4. 明示された別名が、同じ綴りのパス末尾からの推測に**勝つ**こと
    5. 関数の中のローカル変数が、同じ綴りの import を**覆う**こと
    6. 経路のハンドラ(`_handler_of`)側の import 解決も同じ順序で効いていること
    7. 型の推定(`_infer_type`)側の import 解決も同じ順序で効いていること
    8. 7 の側でも、ローカル変数が同じ綴りの import を覆うこと
    9. **型を推定できなかった**ローカル変数も、同じ綴りの import を覆うこと

    これに加えて、ルートの取り出しの形を1つ固定する — 名前解決とは別の型の壊れ方である:

    10. Go 1.22 以降の `net/http.ServeMux` の `[METHOD ][HOST]/[PATH]` 形を、メソッドと
        経路に分解すること — 標準の9種以外のメソッド(`"PROPFIND /dav"`)と、メソッドが
        無くホストだけが前に付く形(`"example.com/hosted2"`)も含む。分解を落とすと
        メソッドやホストが経路の中へ入り込み(`ANY /GET /pong`)、契約との突き合わせが
        1件も当たらなくなる(`ANY /GET /pong` のようにメソッドが経路の中へ残る型。
        2026-09-01 に実測)。
    11. **その分解を、分解してはいけない側へ広げないこと** — 呼び名がメソッドを決めている
        呼び(`r.Get("POST /nope", …)`)と、`ServeMux` ではないルータの相対経路
        (`r.Handle("users/{id}", …)`)である。後者でホストを落とす実装にすると、
        chi / gin / echo の入れ子の経路の先頭を削る。**入れ子で同じ名前を別のルータへ
        束ね直した側**(`mux := chi.NewRouter()`)も同じで、外側の判定が残ると削る。

    プロジェクトの設定に左右されないよう、**除外と配置の指定**(`excludes` などの4つと
    `internal_roots` / `source_roots`)は題材用の値に置き換えて走らせる。
    """
    try:
        from cgx import go_treesitter as _go
    except Exception as exc:                       # 抽出器が無い環境では検査しない
        return [f"go: 抽出器を読み込めない({exc})"]
    import copy as _copy
    import tempfile as _tempfile
    fcfg = _copy.deepcopy(cfg)
    for key in ("excludes", "vendor_markers", "test_markers", "tooling_markers"):
        fcfg[key] = []
    # **配置の設定も切り離す。** `internal_roots` を引き継ぐと、`["src"]` のような合法な
    # 設定のプロジェクトでは題材の `.go` が1つも対象にならず、正しい抽出器でも失敗する。
    fcfg["internal_roots"] = ["."]
    fcfg["source_roots"] = []
    try:
        with _tempfile.TemporaryDirectory() as td:
            for rel, body in _GO_FIXTURE.items():
                path = Path(td) / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(body, encoding="utf-8")
            result = _go.extract(Path(td), fcfg)
    except Exception as exc:                       # tree-sitter が無い環境では検査しない
        return [f"go: フィクスチャを抽出できない({exc})"]
    edges = {(e["from"], e["to"]) for e in result.get("edges", [])}
    out: list[str] = []
    want = [
        ("宣言されたパッケージ名で import を引けていない",
         ("app/app.go::UseDeclName", "alpha/alpha.go::Run"), True),
        ("宣言されたパッケージ名がパス末尾の推測に負けている",
         ("app/app.go::UseDeclOverTail", "named/named.go::Shared"), True),
        ("パス末尾の推測が宣言名を上書きしている",
         ("app/app.go::UseDeclOverTail", "bar/bar.go::Shared"), False),
        ("明示された別名で import を引けていない",
         ("app/app.go::UseAlias", "other/other.go::F"), True),
        ("パス末尾の推測が明示された別名を上書きしている",
         ("app/app.go::UseAlias", "q/q.go::F"), False),
        ("ローカル変数が同じ綴りの import に負けている",
         ("app/app.go::UseShadowed", "other/other.go::F"), False),
        ("宣言名 import 越しのコンストラクタの戻り型を取り逃している",
         ("app/app.go::UseCtor", "alpha/alpha.go::T.Do"), True),
        ("型の推定でローカル変数が同じ綴りの import に負けている",
         ("app/app.go::UseShadowedCtor", "alpha/alpha.go::T.Do"), False),
    ]
    for label, edge, should_exist in want:
        if (edge in edges) is not should_exist:
            out.append(f"go: {label}: {edge[0]} -> {edge[1]}")
    if bogus := sorted(e for e in edges if e[0] == "app/app.go::UseStdlib"):
        out.append(f"go: 標準ライブラリのメソッド呼び出しから偽の辺が出ている: {bogus}")
    if bogus := sorted(e for e in edges if e[0] == "app/app.go::UseShadowed"):
        out.append(f"go: ローカル変数が同じ綴りの import に覆われている: {bogus}")
    if bogus := sorted(e for e in edges if e[0] == "app/app.go::UseUntypedShadow"):
        out.append(f"go: 型を推定できないローカル変数が同じ綴りの import に覆われている: {bogus}")
    handlers = {e["path_pattern"]: e.get("handler", "")
                for e in result.get("endpoints", [])}
    if handlers.get("/ping") != "alpha/alpha.go::Handle":
        out.append("go: 経路のハンドラの import 解決が効いていない: "
                   f"/ping -> {handlers.get('/ping')!r}")
    ids = {e["id"] for e in result.get("endpoints", [])}
    for want_id in ("ANY /ping", "GET /pong", "POST /hosted",
                    "PROPFIND /dav", "ANY /hosted2"):
        if want_id not in ids:
            out.append("go: ServeMux の登録の形を分解できていない: "
                       f"{want_id} が無い(取れたのは {sorted(ids)})")
    # 生成器を通らない側 — **型から `net/http.ServeMux` と解けたときはホストを落とす**。
    # 題材が `http.NewServeMux()` だけだと、この3つが壊れても検出できない。
    for want_id in ("GET /hosted3",      # 明示型の引数 `mux *http.ServeMux`
                    "GET /hosted4",      # `import h "net/http"` の別名 `am *h.ServeMux`
                    "GET /hosted5",      # 自前の生成器 `NewServeMux() *http.ServeMux`
                    "GET /hosted6",      # 型付きの外側 `mux`(隠される前)
                    "GET /after",        # 字句ブロックを**出た後**に戻った外側 `mux`
                    "GET /after2",       # `if` の初期化文の遮蔽を**出た後**に戻った外側 `mux`
                    "GET /before8",      # 内側の明示型に上書きされていない外側(遮蔽の前)
                    "GET /after8",       # 同上(遮蔽の後)
                    "GET /hosted9",      # 外側が独自型で、内側だけが `*http.ServeMux`
                    "GET /hosted10",     # 引数が同名パッケージ変数(独自型)を遮蔽した側
                    "GET /after11",      # 複合リテラルの遮蔽を**出た後**に戻った外側
                    "GET /hosted11",     # `mux := &http.ServeMux{}`(生成器を通さない)
                    "GET /after12",      # リテラル引数の遮蔽を**出た後**に戻った外側
                    "GET /hosted12",     # リテラル引数が `*http.ServeMux` の側
                    "GET /after13",      # 型を書かない `var` の遮蔽を出た後
                    "GET /hosted13",     # `var mux = &http.ServeMux{}`
                    # 複数名の宣言。位置で対応させないと、どちらかが取り違う
                    "GET /hosted14", "GET /hosted15", "GET /hosted16",
                    # 明示型の複数名。2つ目に型が付かないと、この経路が消える
                    "GET /hosted17", "GET /hosted17b",
                    # 別名束縛。証明が移らないとホストが残る
                    "GET /alias19", "GET /alias20",
                    # 入れ替えの代入。右辺を先に評価しないと両方とも取り違う
                    "GET /alias21"):
        if want_id not in ids:
            out.append("go: 型から判る net/http.ServeMux でホストを落とせていない: "
                       f"{want_id} が無い(取れたのは {sorted(ids)})")
    for want_id in ("GET /POST /nope", "ANY /users/{id}", "ANY /team/{tid}",
                    # 名前に ServeMux を含むだけの独自ルータ。ホストを落とすと相対経路が化ける
                    "ANY /tenant/path",
                    # 修飾だけが違う同名型。末尾の名前で判定すると、ここが `/path2` に化ける
                    "ANY /tenant2/path2",
                    # 型付きの外側 `mux` を内側の chi 変数が隠した後。型の辞書を直接引くと
                    # 遮蔽が効かず、ここが `/path3` に化ける
                    "ANY /tenant3/path3",
                    # 素の字句ブロックの中。遮蔽が効かないとここが `/path4` に化ける
                    "ANY /tenant4/path4",
                    # `if` の初期化文での遮蔽の中
                    "ANY /tenant5/path5",
                    # 内側の明示型が独自型。ここでホストを落としてはならない
                    "ANY /tenant8/path8",
                    # 外側が独自型。内側の `*http.ServeMux` が漏れてはならない
                    "ANY /tenant9/path9", "ANY /tenant9b/path9b",
                    # 引数(独自型)が同名パッケージ変数(`*http.ServeMux`)を遮蔽した側
                    "ANY /tenant10/path10",
                    # 既知の生成器を通さない束縛。消し込みが無いと外側の判定が残る
                    "ANY /tenant11/path11",
                    # 関数リテラルの引数が外側の `*http.ServeMux` を隠した中
                    "ANY /v3/tenant12/path12", "ANY /tenant12b/path12b",
                    # 型を書かない `var` が外側を隠した中
                    "ANY /tenant13/path13",
                    # 複数名の宣言のうち、独自型に束ねた側
                    "ANY /tenant14/path14", "ANY /tenant15/path15",
                    "ANY /tenant16/path16",
                    # ローカル変数が import の呼び名 `http` を覆っている側
                    "ANY /tenant18/path18",
                    # 入れ替えの代入で独自型になった側
                    "ANY /tenant21/path21"):
        if want_id not in ids:
            out.append("go: 分解してはいけない側の経路に手を入れている: "
                       f"{want_id} が無い(取れたのは {sorted(ids)})")
    # ★ 大文字でないメソッドから経路を作ってはならない。`GET /lower` は実在しない辺を立て、
    # `ANY /lower` も同じである — `cgx/boundaries.py` は完全一致が無いと `ANY` へ落ちるので、
    # 本物の `GET /lower` の規則を吸い込む(2026-09-01 に実測)。**落とすのが正しい。**
    for bad_id in ("GET /lower", "ANY /lower", "ANY /get /lower"):
        if bad_id in ids:
            out.append("go: 大文字でないメソッドから偽の経路を作っている: "
                       f"{bad_id} が出ている(取れたのは {sorted(ids)})")
    # ホストが経路に残ったままの形。**実在しない経路を endpoint として出すことになる。**
    for bad_id in ("GET /example.com/hosted3", "GET /example.com/hosted4",
                   "GET /example.com/hosted5", "GET /example.com/hosted6",
                   # 遮蔽がスコープの外まで残った形
                   "GET /example.com/after", "GET /example.com/after2",
                   "GET /example.com/before8", "GET /example.com/after8",
                   "GET /example.com/hosted9", "GET /example.com/hosted10",
                   "GET /example.com/after11", "GET /example.com/hosted11",
                   "GET /example.com/after12", "GET /example.com/hosted12",
                   "GET /example.com/after13", "GET /example.com/hosted13",
                   "GET /example.com/hosted14", "GET /example.com/hosted15",
                   "GET /example.com/hosted16",
                   "GET /example.com/hosted17", "GET /example.com/hosted17b",
                   "GET /example.com/alias19", "GET /example.com/alias20",
                   "GET /example.com/alias21"):
        if bad_id in ids:
            out.append("go: ホストが経路に残っている: "
                       f"{bad_id} が出ている(取れたのは {sorted(ids)})")
    # 隠した後の相対経路の頭を削った形。**遮蔽が効いていない証拠である。**
    for bad_id in ("ANY /path3", "ANY /path4", "ANY /path5",
                   "ANY /path8", "ANY /path9", "ANY /path9b",
                   "ANY /path10", "ANY /path11", "ANY /v3/path12",
                   "ANY /path12b", "ANY /path13",
                   "ANY /path14", "ANY /path15", "ANY /path16", "ANY /path18",
                   "ANY /path21"):
        if bad_id in ids:
            out.append("go: 内側で束縛し直した名前に、外側の ServeMux の判定が残っている: "
                       f"{bad_id} が出ている(取れたのは {sorted(ids)})")
    return out


def run_selftest(root: Path, cfg: dict, langs: list[str], scope: Path | None) -> int:
    """決定性の不変則と、抽出器の回帰フィクスチャを検査する。

    (1) 2回抽出して完全一致するか
    (2) 出力される全配列がコードポイント順に並んでいるか
    (3) 出力に行番号・絶対パス・日付が混入していないか
    (4) TS 抽出器がクラスプロパティ形式のメソッドを記号化しているか
    (5) Go 抽出器の名前解決が偽の確定辺を作らないか(`_selftest_go_fixture`)
    """
    import re as _re

    first, _ = run_extractors(root, cfg, langs, scope)
    second, _ = run_extractors(root, cfg, langs, scope)
    failures: list[str] = []

    a = json.dumps(first, ensure_ascii=False, sort_keys=True)
    b = json.dumps(second, ensure_ascii=False, sort_keys=True)
    if a != b:
        failures.append("2回の抽出結果が一致しない(決定性が壊れている)")

    def sorted_by(items, key):
        vals = [key(x) for x in items]
        return vals == sorted(vals)

    for lang, d in first["languages"].items():
        if not sorted_by(d["symbols"], lambda s: s["id"]):
            failures.append(f"{lang}: symbols が整列されていない")
        if not sorted_by(d["edges"], lambda e: (e["from"], e["to"])):
            failures.append(f"{lang}: edges が整列されていない")
        if not sorted_by(d["endpoints"], lambda e: (e["id"], e["handler"], e["source"])):
            failures.append(f"{lang}: endpoints が整列されていない")
        if not sorted_by(d["unresolved"], lambda u: (u["from"], u["expression"], u["reason"])):
            failures.append(f"{lang}: unresolved が整列されていない")
        for s in d["symbols"]:
            if _re.search(r":\d+::", s["id"]) or s["id"].startswith("/"):
                failures.append(f"{lang}: シンボルIDに行番号か絶対パスが混入: {s['id']}")
                break

    failures += _selftest_ts_fixture()
    failures += _selftest_go_fixture(cfg)

    res_list = first.get("resources", [])
    if not sorted_by(res_list, lambda r: r["key"]):
        failures.append("resources が整列されていない")
    for r in res_list:
        if not sorted_by(r["refs"], lambda x: (x["symbol"], x["access"], x["evidence"])):
            failures.append(f"resources[{r['key']}].refs が整列されていない")
            break
        if r["name"].startswith("{}") or r["name"].endswith("{}"):
            # 先頭・末尾の `{}` を残すと、同じ資源が `orders` と `orders{}` に割れる
            failures.append(f"資源名の端に `{{}}` が残っている: {r['key']}")
            break

    rendered = render_all(first, [])
    for name, content in rendered.items():
        if _re.search(r"\b(19|20)\d{2}-\d{2}-\d{2}\b", content):
            failures.append(f"{name}: 日付が混入している(決定性が壊れる)")
        if str(root) in content:
            failures.append(f"{name}: 絶対パスが混入している")

    print("## 決定性の自己検査")
    print(f"  対象言語: {', '.join(sorted(first['languages'])) or '(なし)'}")
    if failures:
        for f in failures:
            print(f"  NG  {f}")
        return 1
    print("  OK  2回の抽出が一致 / 全配列が整列済み / 行番号・絶対パス・日付の混入なし")
    return 0


# --------------------------------------------------------------------------- 本体

def main(argv: list[str]) -> int:
    if any(a in ("-h", "--help") for a in argv[1:]):
        print(__doc__)   # 明示要求は 0。使い方エラーの 2 と区別する(tools-readme §2)
        return 0
    args = argv[1:]
    langs_arg: list[str] | None = None
    scope_arg: str | None = None
    out_arg: str | None = None
    fmt = "md"
    check = False
    selftest = False
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--check":
            check = True
        elif a == "--selftest":
            selftest = True
        elif a == "--format" and i + 1 < len(args):
            i += 1
            fmt = args[i]
        elif a.startswith("--format="):
            fmt = a.split("=", 1)[1]
        elif a == "--lang" and i + 1 < len(args):
            i += 1
            langs_arg = [x.strip() for x in args[i].split(",") if x.strip()]
        elif a.startswith("--lang="):
            langs_arg = [x.strip() for x in a.split("=", 1)[1].split(",") if x.strip()]
        elif a == "--scope" and i + 1 < len(args):
            i += 1
            scope_arg = args[i]
        elif a.startswith("--scope="):
            scope_arg = a.split("=", 1)[1]
        elif a == "--out" and i + 1 < len(args):
            # **次がフラグなら「値の欠落」である。** `--out $CG_OUT --check` を引用符無しで
            # 書き、`$CG_OUT` が空だと `--out --check` になる。飲み込むと `--check` という名の
            # ディレクトリへ**書き込みが走る**(実測。独立レビュー B)。fail-closed にする。
            if args[i + 1].startswith("--"):
                print("エラー: --out の値が無い(次がフラグ)。"
                      "`--out \"$CG_OUT\"` のように**引用符で囲む**こと。")
                return 2
            i += 1
            out_arg = args[i]
        elif a.startswith("--out="):
            # `=` 形も同じ扱い: 値がフラグなら欠落である(空白区切りだけ塞いでも
            # `--out=--check` が素通りして `--check/` へ書き込む。独立検証で実測)
            out_arg = a.split("=", 1)[1]
            if out_arg.startswith("--"):
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
    base.ensure_kit_venv(root)   # キット専用 venv があればそちらで自己再実行
    cfg = base.load_config(root)
    all_langs = [l for l, s in cfg["languages"].items() if s.get("enabled")]
    langs = langs_arg if langs_arg is not None else all_langs
    unknown = [l for l in langs if l not in cfg["languages"]]
    if unknown:
        print(f"エラー: 未知の言語: {', '.join(unknown)}")
        print(f"設定にあるのは: {', '.join(cfg['languages'])}")
        return 2

    scope = (root / scope_arg).resolve() if scope_arg else None
    if scope and not scope.exists():
        print(f"エラー: --scope が存在しない: {scope_arg}")
        return 2

    # **空文字列は既定へ落とさない。** `--out "$(resolve-callgraph-out.py)"` と1行で書くと、
    # 解決の失敗(使い方エラー → 終了コード2)が**空文字列**として渡る — 失敗は stderr に
    # しか出ないのでコマンド置換は空になる。`or` で黙って既定へ落とすと、書き手の意図
    # (明示した出力先)と違う場所へ書くことになる(実測で再現済み:
    # KIT-empty-out-falls-back-to-ssot)。fail-closed にここで止める。
    if out_arg is not None and not out_arg.strip():
        print("エラー: --out が空である。`resolve-callgraph-out.py` の失敗をそのまま渡していないか"
              "(失敗は stderr にだけ出るので `$(...)` は空になる)。\n"
              "  正しい形: CG_OUT=$(python3 .claude/scripts/resolve-callgraph-out.py) \\\n"
              "              && python3 .claude/scripts/build-callgraphs.py --out \"$CG_OUT\"\n"
              "  (スクリプトの中では `|| exit 2` でよい。**対話シェルに貼ると端末ごと終了する**)")
        return 2

    if selftest:
        return run_selftest(root, cfg, langs, scope)

    result, notes = run_extractors(root, cfg, langs, scope)
    if scope:
        notes.append(f"--scope {scope_arg} で部分生成した。**この出力は全体を網羅していない**")
    if langs_arg is not None and set(langs_arg) != set(all_langs):
        notes.append(f"--lang で {', '.join(sorted(langs_arg))} のみ生成した")

    if fmt == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    # --out はタスク進行中に SSOT を書かないために在る(directions/callgraphs.md §3.1)。
    # リポジトリ相対で受け取り、root の外へは書かせない(タスク配下か docs/ 配下しか使わない)。
    #
    out_rel = out_arg or cfg.get("output_dir", "docs/03-impl/callgraphs")
    out_dir = (root / out_rel).resolve()
    try:
        out_dir.relative_to(root)
    except ValueError:
        print(f"エラー: --out はリポジトリ内を指すこと: {out_rel}")
        return 2
    rendered = render_all(result, notes)
    # **中身にマーカーが混ざると切り出しが壊れる。** 黙って捨てるより止める(§3-4)。
    _b, _e = base.note_markers("build-callgraphs.py")
    for _name, _c in rendered.items():
        if _c.count(_b) > 1 or _c.count(_e) > 1:
            print(f"エラー: 生成する内容にマーカーが混ざっている: {_name}")
            return 2

    if check:
        diffs = []
        for name, content in sorted(rendered.items()):
            path = out_dir / name
            current = path.read_text(encoding="utf-8") if path.is_file() else None
            # **注記は比較しない。** 文言を1字直しただけで全プロジェクトの生成物が
            # 一斉に古くなる(実測: 1文字で7ファイル)。KIT-generated-note-churns-every-artifact
            if current is not None and base.without_note(current) == base.without_note(content):
                continue
            if current != content:
                diffs.append(name if current is not None else f"{name} (未作成)")
        stale = sorted(p.name for p in out_dir.glob("*.md")) if out_dir.is_dir() else []
        orphans = [n for n in stale if n not in rendered]
        print(f"## コールグラフの鮮度検査: {out_rel}")
        if not diffs and not orphans:
            print("最新。再生成しても差分は出ない。")
            return 0
        for d in diffs:
            print(f"  差分: {d}")
        for o in orphans:
            print(f"  余分: {o}(対象言語から外れたか、抽出器が無い — 生成印を持つものは"
                  "再生成が削除する)")
        # **案内はそのままコピーして打てる形にする**(原則11)。
        # 値は shlex.quote で囲む — 空白を含むパスで貼り付けが落ちていた(独立レビュー B の実測)。
        regen = "python3 .claude/scripts/build-callgraphs.py"
        if out_arg:
            regen = ("python3 .claude/scripts/build-callgraphs.py --out "
                     + shlex.quote(out_arg))
        print(f"\n→ callgraphs が実装と食い違っている。`{regen}` で再生成すること。")
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, content in sorted(rendered.items()):
        path = out_dir / name
        if not path.is_file() or path.read_text(encoding="utf-8") != content:
            path.write_text(content, encoding="utf-8")
            written.append(name)
    # **余分(今回の生成集合に無い旧ファイル)は再生成が消す**(inspection-17 M-18)。
    # 対象言語から外れた言語ファイル等が残ると --check が「余分」を出し続け、出口が
    # 禁止された手作業しか無かった。消すのは自分の生成印を持つファイルだけ —
    # 生成ディレクトリに紛れ込んだ手書きファイルを黙って消さない(それは「余分」として残る)。
    removed = []
    manual_orphans = []
    for path in sorted(out_dir.glob("*.md")):
        if path.name in rendered:
            continue
        if _b in path.read_text(encoding="utf-8", errors="replace"):
            path.unlink()
            removed.append(path.name)
        else:
            manual_orphans.append(path.name)
    print(f"## コールグラフ生成: {out_rel}")
    if out_arg is None:
        print("  生成先の根拠: --out 省略 → SSOT(docs/03-impl/callgraphs)へ直書き"
              "(フロー分離後の生成先は常に SSOT — callgraphs.md §3.1)")
    if result.get("routing"):
        print(f"  infra: パス転送 {len(result['routing'])} 件 / 境界の辺 "
              f"{len(result.get('boundaries', []))} 件 / 呼び出し元不明のエンドポイント "
              f"{len(result.get('orphan_endpoints', []))} 件")
    for lang, data in sorted(result["languages"].items()):
        print(f"  {lang}: Tier {data['tier']} / シンボル {len(data['symbols'])}"
              f" / 辺 {len(data['edges'])} / エンドポイント {len(data['endpoints'])}"
              f" / 未解決 {len(data['unresolved'])}")
    for v in sorted({v for data in result["languages"].values()
                     for v in data.get("vendored_dirs", [])}):
        print(f"  除外(第三者ライブラリ): {v}/")
    print(f"  書き換え: {', '.join(written) if written else 'なし(既に最新)'}")
    if removed:
        print(f"  削除(生成集合から外れた旧生成物): {', '.join(removed)}")
    for m in manual_orphans:
        print(f"  余分: {m}(生成印が無いので消さない — 手書き禁止の場所である。移すか消すこと)")
    for n in notes:
        print(f"  注記: {n}")
    print("\n→ これは機能間連携仕様書ではない。機能単位への集約は `/relations` が行う。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
