"""TypeScript / JavaScript 抽出器 (Tier 2) — tree-sitter による構文解析。

規範: .claude/directions/callgraphs.md / 契約: callgraph-schema.json

TS/JS はモジュールスコープなので、**import が解決の主役**である
(`import { x } from "./y"` の `y` を相対パスで解決すれば、`x()` は一意に決まる)。
Python の「同名照合」に頼らずに済むぶん、偽の ambiguous は出にくい。

この抽出器の主眼は、言語内の呼び出し関係だけでなく、
**HTTP クライアント呼び出しの URL リテラルを拾うこと**である。
それがフロントエンド → バックエンドの境界の辺の唯一の機械的な手掛かりになる
(directions §5.10)。ただし**それは候補であって確定ではない**。

`.vue` は SFC なので `<script>` ブロックだけを取り出して解析する。
"""

from __future__ import annotations

import re
from pathlib import Path

from . import base

TS_EXT = {".ts", ".mts", ".cts"}
TSX_EXT = {".tsx", ".jsx", ".js", ".mjs", ".cjs"}
VUE_EXT = {".vue"}
MODULE_SYMBOL = "<module>"
SCRIPT_BLOCK = re.compile(r"<script[^>]*>(.*?)</script>", re.S | re.I)

# ルート定義(Express / Fastify / Hono / NestJS のデコレータは別扱い)
ROUTE_METHODS = {"get": "GET", "post": "POST", "put": "PUT", "patch": "PATCH",
                 "delete": "DELETE", "head": "HEAD", "options": "OPTIONS", "all": "ANY",
                 "use": "ANY"}
ROUTER_HINTS = ("app", "router", "server", "api", "route")

# HTTP クライアント。第1引数(または第2引数)の URL リテラルを境界の候補として拾う
HTTP_CLIENTS = {"fetch", "axios", "request", "got", "ky", "superagent"}
HTTP_CLIENT_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "request"}

# 受け手の型が分からないときに内部シンボルと照合しない名前(組み込み・標準)
BUILTIN_METHODS = {
    "then", "catch", "finally", "map", "filter", "reduce", "forEach", "find", "some",
    "every", "push", "pop", "shift", "unshift", "slice", "splice", "concat", "join",
    "sort", "reverse", "includes", "indexOf", "keys", "values", "entries", "has",
    "add", "delete", "set", "clear", "toString", "valueOf", "trim", "split", "replace",
    "match", "test", "exec", "toFixed", "padStart", "padEnd", "startsWith", "endsWith",
    "toLowerCase", "toUpperCase", "json", "text", "blob", "log", "warn", "error", "info",
    "emit", "on", "off", "once", "next", "call", "apply", "bind", "assign", "stringify",
    "parse", "now", "from", "of", "all", "resolve", "reject", "race",
}


def _load_parsers():
    try:
        import tree_sitter_typescript as tst
        from tree_sitter import Language, Parser
    except ImportError as exc:
        raise RuntimeError(
            f"tree-sitter-typescript が無い({exc})。"
            "`python3 .claude/scripts/setup-tools.py` でキット専用 venv に導入すること") from exc

    def mk(lang):
        try:
            return Parser(Language(lang))
        except TypeError:                            # 古い API
            p = Parser()
            p.set_language(Language(lang))
            return p
    return mk(tst.language_typescript()), mk(tst.language_tsx())


def _txt(src: bytes, n) -> str:
    return src[n.start_byte:n.end_byte].decode("utf-8", "replace")


def _f(n, name):
    return n.child_by_field_name(name) if n is not None else None


def _find(node, kinds: set[str], out: list, include_self: bool = False) -> None:
    """指定種別を深さ優先で集める。

    `include_self` が要るのは `const f = () => api.get("/x")` の形。
    アロー関数の body が呼び出し式そのものなので、子だけ見ると取りこぼす。
    """
    if include_self and node.type in kinds:
        out.append(node)
    for c in node.children:
        if c.type in kinds:
            out.append(c)
        _find(c, kinds, out)


def _str_lit(src: bytes, n) -> str | None:
    if n is None:
        return None
    if n.type in {"string", "template_string"}:
        inner = _txt(src, n)[1:-1]
        return None if ("${" in inner and n.type == "template_string") else inner
    return None


# --------------------------------------------------------------------------- ファイル

class _TsFile:
    def __init__(self, rel: str, src: bytes, root):
        self.rel, self.src, self.root = rel, src, root
        self.imports: dict[str, tuple[str, str]] = {}   # ローカル名 → (解決先rel, 元の名前)
        self.defs: dict[str, str] = {}                  # 名前 → symbol_id
        self.methods: dict[tuple[str, str], str] = {}   # (クラス, メソッド) → sid


def _resolve_spec(rel: str, spec: str, known: set[str]) -> str | None:
    """`./y` `../a/b` `@/x` を実ファイルに解決する。外部パッケージなら None。"""
    if not spec.startswith((".", "/", "@/", "~/")):
        return None
    here = rel.rsplit("/", 1)[0] if "/" in rel else ""
    if spec.startswith(("@/", "~/")):
        cand_base = spec[2:]
        bases = [cand_base] + [f"{p}/{cand_base}" for p in ("src", "app", "frontend/src")]
    else:
        parts = [p for p in f"{here}/{spec}".split("/") if p and p != "."]
        stack: list[str] = []
        for p in parts:
            if p == "..":
                if stack:
                    stack.pop()
            else:
                stack.append(p)
        bases = ["/".join(stack)]
    for b in bases:
        for suffix in ("", ".ts", ".tsx", ".js", ".jsx", ".vue", "/index.ts", "/index.tsx",
                       "/index.js"):
            if (cand := b + suffix) in known:
                return cand
    return None


def _object_members(src: bytes, obj) -> list[tuple[str, object]]:
    """オブジェクトリテラルの、値が関数であるメンバを返す。"""
    out = []
    for pair in obj.children:
        if pair.type not in {"pair", "method_definition"}:
            continue
        k, v = _f(pair, "key"), _f(pair, "value")
        if pair.type == "method_definition":
            k, v = _f(pair, "name"), pair
        if k is None or v is None:
            continue
        if pair.type == "method_definition" or v.type in {"arrow_function", "function_expression"}:
            name = _txt(src, k).strip("'\"")
            out.append((name, v))
    return out


def _collect(rel: str, src: bytes, root, symbols: list[dict]) -> _TsFile:
    fi = _TsFile(rel, src, root)

    def add(name: str, kind: str, cls: str | None = None) -> str:
        qual = f"{cls}.{name}" if cls else name
        sid = base.symbol_id(rel, qual)
        symbols.append({"id": sid, "file": rel, "name": qual, "kind": kind,
                        "visibility": "private" if name.startswith("_") else "public"})
        return sid

    def walk(node, cls: str | None) -> None:
        for c in node.children:
            if c.type == "function_declaration":
                n = _f(c, "name")
                if n:
                    fi.defs[_txt(src, n)] = add(_txt(src, n), "function")
            elif c.type == "class_declaration":
                n = _f(c, "name")
                cname = _txt(src, n) if n else None
                if cname:
                    fi.defs[cname] = add(cname, "function")
                    body = _f(c, "body")
                    for m in (body.children if body else []):
                        if m.type in {"method_definition"}:
                            mn = _f(m, "name")
                            if mn:
                                fi.methods[(cname, _txt(src, mn))] = add(
                                    _txt(src, mn), "method", cname)
                        elif m.type == "public_field_definition":
                            # `public m = async () => {}` は TS で `this` 束縛を避ける定石。
                            # tree-sitter は method_definition ではなく public_field_definition
                            # で返すので、ここを拾わないとクラスのメソッドが丸ごと記号から落ちる。
                            # 落ちると、同名の別記号へ**一意に**解決されて確度「確定」の
                            # 偽の辺が出る(候補辺より有害)。
                            mn, mv = _f(m, "name"), _f(m, "value")
                            if mn is None or mv is None:
                                continue
                            if mv.type in {"arrow_function", "function_expression"}:
                                fi.methods[(cname, _txt(src, mn))] = add(
                                    _txt(src, mn), "method", cname)
                continue
            elif c.type in {"lexical_declaration", "variable_declaration"}:
                for d in c.children:
                    if d.type != "variable_declarator":
                        continue
                    n, v = _f(d, "name"), _f(d, "value")
                    if not (n and v is not None):
                        continue
                    if v.type in {"arrow_function", "function_expression"}:
                        fi.defs[_txt(src, n)] = add(_txt(src, n), "function")
                    elif v.type == "object":
                        # `export const authApi = { login: () => ... }` は TS で普通の形。
                        # ここを拾わないと API モジュールが丸ごと解析から落ちる。
                        for key, _fn in _object_members(src, v):
                            fi.methods[(_txt(src, n), key)] = add(key, "method", _txt(src, n))
            walk(c, cls)

    walk(root, None)

    imports: list = []
    _find(root, {"import_statement"}, imports)
    for imp in imports:
        spec = _str_lit(src, _f(imp, "source"))
        if spec is None:
            continue
        for clause in imp.children:
            if clause.type != "import_clause":
                continue
            for part in clause.children:
                if part.type == "identifier":                       # default import
                    fi.imports[_txt(src, part)] = (spec, "default")
                elif part.type == "named_imports":
                    for spec_node in part.children:
                        if spec_node.type != "import_specifier":
                            continue
                        nm = _f(spec_node, "name")
                        alias = _f(spec_node, "alias")
                        if nm:
                            fi.imports[_txt(src, alias or nm)] = (spec, _txt(src, nm))
                elif part.type == "namespace_import":
                    for ch in part.children:
                        if ch.type == "identifier":
                            fi.imports[_txt(src, ch)] = (spec, "*")
    return fi


# --------------------------------------------------------------------------- 解決

class _TsResolver:
    def __init__(self, files: dict[str, _TsFile]):
        self.files = files
        self.known = set(files)
        self.simple: dict[str, list[str]] = {}
        for fi in files.values():
            for name, sid in fi.defs.items():
                self.simple.setdefault(name, []).append(sid)
            for (_c, name), sid in fi.methods.items():
                self.simple.setdefault(name, []).append(sid)
        for k in self.simple:
            self.simple[k].sort()

    def via_import(self, fi: _TsFile, local: str) -> str | None:
        got = fi.imports.get(local)
        if not got:
            return None
        spec, orig = got
        target = _resolve_spec(fi.rel, spec, self.known)
        if target is None:
            return None
        tf = self.files[target]
        if orig in tf.defs:
            return tf.defs[orig]
        if orig in {"default", "*"} and len(tf.defs) == 1:
            return next(iter(tf.defs.values()))
        return None

    def by_simple(self, name: str) -> tuple[str | None, list[str]]:
        hits = self.simple.get(name, [])
        return (hits[0], []) if len(hits) == 1 else (None, hits)


def _resolve(call, src: bytes, fi: _TsFile, rv: _TsResolver, cls: str | None,
             params: set[str]) -> tuple[str | None, dict | None, bool]:
    fn = _f(call, "function")
    if fn is None:
        return None, None, True
    if fn.type in {"call_expression", "parenthesized_expression"}:
        return None, {"reason": "higher-order"}, False
    if fn.type == "subscript_expression":
        return None, {"reason": "dynamic"}, False

    if fn.type == "identifier":
        name = _txt(src, fn)
        if name in params:
            return None, {"reason": "higher-order"}, False
        if name in fi.defs:
            return fi.defs[name], None, False
        got = rv.via_import(fi, name)
        if got:
            return got, None, False
        return None, None, True

    if fn.type != "member_expression":
        return None, None, True

    obj, prop = _f(fn, "object"), _f(fn, "property")
    if prop is None:
        return None, None, True
    name = _txt(src, prop)

    if obj is not None and obj.type == "this" and cls:
        got = fi.methods.get((cls, name))
        if got:
            return got, None, False
        return None, None, True
    if obj is not None and obj.type == "identifier":
        oname = _txt(src, obj)
        if oname in fi.imports:                      # 名前空間 import 経由
            spec, _o = fi.imports[oname]
            target = _resolve_spec(fi.rel, spec, rv.known)
            if target is None:
                return None, None, True              # 外部パッケージ
            got = rv.files[target].defs.get(name)
            return (got, None, False) if got else (None, None, True)
        if oname in {"console", "JSON", "Math", "Object", "Array", "Promise", "Date"}:
            return None, None, True

    if name in BUILTIN_METHODS:
        return None, None, True

    got, cands = rv.by_simple(name)
    if got:
        return got, None, False
    if cands:
        return None, {"reason": "ambiguous", "candidates": cands}, False
    return None, None, True


# --------------------------------------------------------------------------- ルート / HTTP 呼び出し

def _scan_calls(node, src: bytes, fi: _TsFile, rv: _TsResolver, enclosing: str,
                endpoints: list, http_calls: list) -> None:
    calls: list = []
    _find(node, {"call_expression"}, calls, include_self=True)
    for call in calls:
        _scan_calls_one(call, src, enclosing, endpoints, http_calls)


def _scan_calls_one(call, src: bytes, enclosing: str, endpoints: list,
                    http_calls: list) -> None:
    """1つの呼び出しから、HTTP クライアント呼び出しとルート定義を拾う。"""
    fn = _f(call, "function")
    if fn is None or fn.type not in {"member_expression", "identifier"}:
        return
    argnode = _f(call, "arguments")
    args = [c for c in (argnode.children if argnode else []) if c.type not in {"(", ")", ","}]
    if not args:
        return

    if fn.type == "identifier":
        if _txt(src, fn) in HTTP_CLIENTS:
            url = next((u for u in (_str_lit(src, a) for a in args) if u), None)
            http_calls.append((enclosing, "ANY", url, _txt(src, fn)))
        return

    obj, prop = _f(fn, "object"), _f(fn, "property")
    if obj is None or prop is None:
        return
    oname = _txt(src, obj) if obj.type == "identifier" else ""
    meth = _txt(src, prop)
    low = meth.lower()

    # HTTP クライアント: axios.get("/x") / apiClient.post<T>("/x") / http.request("/x")
    # 受け手の名前は**部分一致**で見る。実データでは `apiClient` のような命名が普通で、
    # 完全一致の白名簿にすると境界の辺が1本も取れなかった。
    if low in HTTP_CLIENT_METHODS and (
            oname in HTTP_CLIENTS
            or any(h in oname.lower() for h in ("api", "client", "http", "axios",
                                                "fetch", "request", "gateway"))):
        url = next((u for u in (_str_lit(src, a) for a in args) if u), None)
        if url is None or url.startswith(("/", "http")):
            http_calls.append((enclosing, low.upper(), url, f"{oname}.{meth}"))
            return

    # サーバ側のルート定義: app.get("/x", handler)
    if low in ROUTE_METHODS and len(args) >= 2 and any(h in oname.lower() for h in ROUTER_HINTS):
        path = _str_lit(src, args[0])
        if path is None or not path.startswith("/"):
            return
        endpoints.append({
            "id": base.endpoint_id(ROUTE_METHODS[low], path), "protocol": "rest",
            "method": ROUTE_METHODS[low],
            "path_pattern": base.normalize_path_pattern(path),
            "path_key": base.path_key(path), "handler": enclosing,
            "source": f"{oname}.{meth}",
        })


# --------------------------------------------------------------------------- 入口

def extract(root: Path, cfg: dict, scope: Path | None = None) -> dict:
    lang_cfg = cfg["languages"]["typescript"]
    skipped: dict = {}
    files, vendored = base.collect_files(root, cfg, lang_cfg["extensions"], scope, skipped)
    p_ts, p_tsx = _load_parsers()

    infos: dict[str, _TsFile] = {}
    symbols: list[dict] = []
    unresolved: list[dict] = []

    for path in files:
        rel = path.resolve().relative_to(root).as_posix()
        raw = path.read_text(encoding="utf-8", errors="replace")
        if path.suffix in VUE_EXT:
            blocks = SCRIPT_BLOCK.findall(raw)
            if not blocks:
                continue
            raw = "\n".join(blocks)
        src = raw.encode("utf-8")
        parser = p_ts if path.suffix in TS_EXT else p_tsx
        try:
            tree = parser.parse(src)
        except Exception as exc:                     # pragma: no cover
            unresolved.append({"from": base.symbol_id(rel, "<file>"),
                               "expression": f"<解析失敗: {exc}>"[:120], "reason": "dynamic"})
            continue
        infos[rel] = _collect(rel, src, tree.root_node, symbols)

    rv = _TsResolver(infos)
    edges: list[dict] = []
    endpoints: list[dict] = []
    http_calls: list[tuple] = []
    external = 0

    for rel, fi in infos.items():
        units: list[tuple[str, str | None, object]] = []
        seen_calls: set[int] = set()

        def gather(node, cls):
            for c in node.children:
                if c.type == "function_declaration":
                    n = _f(c, "name")
                    if n:
                        units.append((_txt(fi.src, n), cls, c))
                    continue
                if c.type == "class_declaration":
                    n = _f(c, "name")
                    cname = _txt(fi.src, n) if n else None
                    body = _f(c, "body")
                    for m in (body.children if body else []):
                        if m.type == "method_definition":
                            mn = _f(m, "name")
                            if mn and cname:
                                units.append((f"{cname}.{_txt(fi.src, mn)}", cname, m))
                        elif m.type == "public_field_definition":
                            # 記号側(_collect)と対で必要。ここを落とすと記号だけ増えて
                            # メソッド本体から出る呼び出しが1本も辺にならない。
                            # unit に積むのは値のアロー関数ノード自体(parameters / body を持つ側)。
                            mn, mv = _f(m, "name"), _f(m, "value")
                            if (mn is not None and mv is not None and cname
                                    and mv.type in {"arrow_function", "function_expression"}):
                                units.append((f"{cname}.{_txt(fi.src, mn)}", cname, mv))
                    continue
                if c.type in {"lexical_declaration", "variable_declaration"}:
                    for d in c.children:
                        if d.type != "variable_declarator":
                            continue
                        n, v = _f(d, "name"), _f(d, "value")
                        if not (n and v is not None):
                            continue
                        if v.type in {"arrow_function", "function_expression"}:
                            units.append((_txt(fi.src, n), cls, v))
                        elif v.type == "object":
                            vn = _txt(fi.src, n)
                            for key, fnode in _object_members(fi.src, v):
                                units.append((f"{vn}.{key}", vn, fnode))
                    continue
                gather(c, cls)

        gather(fi.root, None)

        for qual, cls, node in units:
            sid = base.symbol_id(rel, qual)
            params: set[str] = set()
            plist = _f(node, "parameters")
            if plist is not None:
                for pnode in plist.children:
                    ident = pnode if pnode.type == "identifier" else _f(pnode, "pattern")
                    if ident is not None and ident.type == "identifier":
                        params.add(_txt(fi.src, ident))
            body = _f(node, "body") or node
            calls: list = []
            _find(body, {"call_expression"}, calls, include_self=True)
            for call in calls:
                target, unres, is_ext = _resolve(call, fi.src, fi, rv, cls, params)
                if target and target != sid:
                    edges.append({"from": sid, "to": target})
                elif unres:
                    f = _f(call, "function")
                    rec = {"from": sid, "expression": _txt(fi.src, f)[:100] if f else "<式>",
                           "reason": unres["reason"]}
                    if unres.get("candidates"):
                        rec["candidates"] = unres["candidates"]
                    unresolved.append(rec)
                elif is_ext:
                    external += 1
            _scan_calls(body, fi.src, fi, rv, sid, endpoints, http_calls)
            seen_calls.update(id(c) for c in calls)

        # 保険: どのユニットにも属さなかった呼び出しからも HTTP を拾う。
        # 取りこぼすと境界の辺が丸ごと消えるので、モジュール本体に帰属させてでも残す。
        rest: list = []
        _find(fi.root, {"call_expression"}, rest)
        leftovers = [c for c in rest if id(c) not in seen_calls]
        if leftovers:
            msid = base.symbol_id(rel, MODULE_SYMBOL)
            before = len(http_calls)
            for c in leftovers:
                _scan_calls_one(c, fi.src, msid, endpoints, http_calls)
            if len(http_calls) > before and not any(s["id"] == msid for s in symbols):
                symbols.append({"id": msid, "file": rel, "name": MODULE_SYMBOL,
                                "kind": "function", "visibility": "private"})

    # URL が変数で組み立てられていた HTTP 呼び出しは「未解決(境界)」として残す
    for frm, _m, url, expr in http_calls:
        if url is None:
            unresolved.append({"from": frm, "expression": f"{expr}(<非リテラルURL>)",
                               "reason": "boundary"})

    result = base.sort_lang_result({
        "tier": 2,
        "extractor": "tree-sitter-typescript",
        "external_call_count": external,
        "symbols": symbols,
        "edges": edges,
        "endpoints": endpoints,
        "unresolved": unresolved,
        "vendored_dirs": vendored,
        "skipped_files": skipped,
    })
    result["http_calls"] = sorted(
        {(f, m, u, e) for f, m, u, e in http_calls if u})
    return result
