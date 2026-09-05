"""言語・プロセスを跨ぐ辺の結合。

規範: .claude/directions/callgraphs.md §5.10

**REST の呼び出し元はツールで特定できない**(機械の限界)。ここでやるのは、
機械にできる範囲で**候補**を出し、確度を付けて残すこと。そして
「呼び出し元が特定できなかったエンドポイント」を一覧にして AI に渡すこと。

  iac   : インフラのパス転送 → 転送先 → 言語側のシンボル(設定から辿れれば「確実」)
  iac   : インフラのパス → 言語側のエンドポイント(パスの正規化キーで突合)
  iac   : API 以外のイベント源(SQS/SNS/ストリーム/定時)→ ハンドラのシンボル
  http  : HTTP クライアントの URL リテラル → エンドポイント
  queue : publish 側のトピック名リテラル → そのキュー/トピックで起動されるハンドラ
"""

from __future__ import annotations

from . import base
from . import resources as res


def _pk(url: str) -> str:
    """クエリを落として正規化キーにする。"""
    return base.path_key((url or "").split("?", 1)[0])


def bind_event_sources(result: dict) -> None:
    """infra が拾った API 以外のイベント源を、infra のエントリポイントとして確定させる。

    **ハンドラが言語側に実在するかは、ここでしか判定できない**(infra 抽出器は
    他言語のシンボルを知らない)。実在しなければエンドポイントにはせず、
    未解決として残す — 空欄で落とすと「イベント源が無い」と誤読される(§5.5)。
    """
    sources = result.pop("_event_sources", [])
    if not sources:
        return
    infra = result.get("languages", {}).get("infra")
    if infra is None:
        return
    symbols: set[str] = set()
    for d in result.get("languages", {}).values():
        symbols |= {s["id"] for s in d.get("symbols", [])}

    for es in sources:
        hint = es.get("handler_hint") or ""
        eid = f"{es['protocol']} {es['type']}:{es['source']} @ {es['function']}"
        if hint and hint in symbols:
            infra["endpoints"].append({
                "id": eid, "protocol": es["protocol"], "method": "",
                "path_pattern": "", "path_key": "", "handler": hint,
                "source": es["origin"]})
        else:
            infra["unresolved"].append({
                "from": f"{es['origin']}::<event>",
                "expression": f"{eid} → {hint or '(ハンドラ未設定)'}",
                "reason": "boundary"})
    base.sort_lang_result(infra)


def join(result: dict) -> tuple[list[dict], list[str]]:
    """(boundaries, 呼び出し元が特定できなかったエンドポイント) を返す。"""
    boundaries: list[dict] = []
    symbols: set[str] = set()
    endpoints: dict[tuple[str, str], dict] = {}
    event_handlers: dict[str, list[dict]] = {}   # 資源名 → その資源で起動されるハンドラ

    entry_eps: list[dict] = []          # 外から叩かれる入口(REST + Lambda 等のハンドラ)
    for lang, d in result.get("languages", {}).items():
        symbols |= {s["id"] for s in d.get("symbols", [])}
        for ep in d.get("endpoints", []):
            if lang == "infra" and ep.get("handler"):
                # インフラ定義から辿れたイベント源は「呼び出し元不明」ではない
                boundaries.append({
                    "kind": "iac", "from": "", "to": ep["handler"], "confidence": "確実",
                    "evidence": f"{ep['id']}({ep['source']})"})
                name = ep["id"].split(":", 1)[-1].split(" @ ", 1)[0]
                event_handlers.setdefault(name, []).append(ep)
    for _lang, d in result.get("languages", {}).items():
        for ep in d.get("endpoints", []):
            if ep.get("protocol") == "rest" and ep.get("path_key"):
                endpoints[((ep.get("method") or "ANY").upper(), ep["path_key"])] = ep
                entry_eps.append(ep)
            elif ep.get("protocol") in {"event", "schedule"} and "#" not in ep.get("handler", ""):
                # 内部分岐(`#CREATE`)はディスパッチャ経由で到達するので入口ではない
                entry_eps.append(ep)

    routing = result.get("routing", [])
    matched_eps: set[tuple[str, str]] = set()

    for r in routing:
        m, t = r["match"], r["target"]
        key = (m.get("method", "ANY"), m.get("path_key", ""))
        hint = t.get("handler_hint") or ""

        # 1. 転送先のハンドラが言語側のシンボルとして実在する → 確実
        if hint and hint in symbols:
            boundaries.append({
                "kind": "iac", "from": "", "to": hint, "confidence": "確実",
                "evidence": f"{m['method']} {m['path_pattern']} → {t['type']}:{t['ref']} "
                            f"({r['source']})"})
            continue

        # 2. パスの正規化キーで言語側のエンドポイントと突合 → 候補
        hit = endpoints.get(key) or (endpoints.get(("ANY", key[1]))
                                     if key[0] != "ANY" else None)
        if hit is None and key[0] == "ANY":
            hit = next((ep for (mm, pk), ep in sorted(endpoints.items()) if pk == key[1]), None)
        if hit is not None:
            matched_eps.add(((hit.get("method") or "ANY").upper(), hit["path_key"]))
            boundaries.append({
                "kind": "iac", "from": "", "to": hit.get("handler") or hit["id"],
                "confidence": "候補",
                "evidence": f"{m['method']} {m['path_pattern']} ⇄ {hit['id']}"
                            f"(パスの正規化キー一致 / {r['source']})"})
            continue

        # 3. どちらでも辿れない
        boundaries.append({
            "kind": "iac", "from": "", "to": f"{t['type']}:{t['ref']}" if t["ref"] else "(不明)",
            "confidence": "未解決",
            "evidence": f"{m['method']} {m['path_pattern']} の転送先を言語側に結び付けられない "
                        f"({r['source']})"})

    # HTTP クライアントの URL リテラル → エンドポイント(**候補**。到達するかは分からない)
    for frm, meth, url, expr in result.get("_http_calls", []):
        key = ((meth or "ANY").upper(), _pk(url))
        hit = endpoints.get(key) or next(
            (ep for (mm, pk), ep in sorted(endpoints.items()) if pk == key[1]), None)
        routed = next((r for r in routing if r["match"]["path_key"] == key[1]), None)
        if hit is not None:
            boundaries.append({
                "kind": "http", "from": frm, "to": hit.get("handler") or hit["id"],
                "confidence": "候補",
                "evidence": f"{expr}(\"{url}\") ⇄ {hit['id']}(URL リテラル一致)"})
            matched_eps.add(((hit.get("method") or "ANY").upper(), hit["path_key"]))
        elif routed is not None:
            boundaries.append({
                "kind": "http", "from": frm,
                "to": routed["target"].get("handler_hint") or routed["target"]["ref"],
                "confidence": "候補",
                "evidence": f"{expr}(\"{url}\") ⇄ {routed['source']}(パス転送と一致)"})
        else:
            boundaries.append({
                "kind": "http", "from": frm, "to": url, "confidence": "未解決",
                "evidence": f"{expr}(\"{url}\") に対応するエンドポイントが見つからない"})

    # キュー / トピックの突合(directions §5.10 の queue)。
    # publish 側の名前リテラルと、そのキューで起動されるハンドラを結ぶ。
    # **これは呼び出し辺として本物である**(publish は必ず consumer に届く)ので、
    # 資源結合(P10 の resources.md)ではなくここに出す。ただし到達は非同期なので `候補`。
    for r in result.get("resources", []):
        if r["kind"] not in {"sqs", "sns"}:
            continue
        # キューURL(`https://sqs.../123456/my-queue`)と論理名の突合は末尾区間で行う
        targets = event_handlers.get(r["name"].rsplit("/", 1)[-1], [])
        for ref in r["refs"]:
            if ref["access"] not in {"write", "readwrite"}:
                continue
            for ep in targets:
                if ep["handler"] == ref["symbol"]:
                    continue
                boundaries.append({
                    "kind": "queue", "from": ref["symbol"], "to": ep["handler"],
                    "confidence": "候補",
                    "evidence": f"{r['key']} へ送信 ⇄ {ep['id']}"
                                f"(名前リテラル一致 / {ref['evidence'][:60]})"})

    reached = {b["to"] for b in boundaries if b["confidence"] in {"確実", "候補"}}
    orphans = sorted(
        ep["id"] for ep in entry_eps
        if ep.get("handler") not in reached
        and ((ep.get("method") or "ANY").upper(), ep.get("path_key", "")) not in matched_eps)

    boundaries.sort(key=lambda b: (b["kind"], b["confidence"], b["to"], b["evidence"]))
    return boundaries, orphans
