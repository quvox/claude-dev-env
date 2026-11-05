"""Rust 抽出器 (Tier 2) — tree-sitter による構文解析 + クレート・モジュール単位の名前解決。

規範: .claude/directions/callgraphs.md / 契約: callgraph-schema.json

Rust は名前解決の手掛かりが構文に多い:
  ・**モジュールの木が構文と配置で決まる**(`mod x;` → `x.rs` / `x/mod.rs`)。
    `crate::` `super::` `self::` はその木の上の位置なので、`use` 宣言から一意に引ける。
  ・`impl Foo { fn m(&self) }` の受け手の型が構文に在る。`self.m()` は型経由で解決できる。
  ・引数と `let` の型注釈、`Foo::new()` の戻り型(`Self`)、構造体のフィールドの型から、
    `x.m()` / `self.repo.m()` の受け手の型を推定できる。
それでも解けないもの(トレイトオブジェクト越しの呼び出しで実装が複数あるもの、
関数を値として受け取った引数の呼び出し、マクロの中のメソッド呼び出し)は**未解決として残す**
(directions §5.5)。

経路の抽出は axum(`Router::new().route("/p", get(h))`・`.nest("/v1", …)`)、
actix-web(`#[get("/p")]` の属性・`web::scope("/v1").service(h)`・`web::resource("/p").route(…)`)、
rocket(`#[get("/p")]` と `.mount("/v1", routes![…])`)に対応する。**接頭辞の合成は必須**で、
`nest` / `scope` / `mount` を辿らないと API Gateway や ALB のパス転送と突き合わせられない
(design §2.3)。接頭辞を与える関数が別の関数から呼ばれる形(`.nest("/api", api_routes())`、
`.configure(config)`)も、呼んだ側の接頭辞を足して辿る。

**読まないもの**(index.md の除外と同じ扱い。黙って落とさない):
  ・`#[cfg(test)]` / `#[test]` の付いた項目 — テストのコードである(`features.md` §0.1)。
    除外した項目の数は `skipped_files.tests` に `<ファイル>#cfg(test)` の形で積む。
  ・クレート直下の `examples/` `benches/` と `build.rs` — 配布物の入口ではない。
    `skipped_files.tooling` に積む。
  ・マクロの中身は構文木にならない(`token_tree`)。**パスの形の関数呼び出し
    (`foo(…)` / `a::b(…)` / `Self::m(…)` / `self.m(…)`)だけは字句で拾う** — 拾わないと
    `tokio::select!` や `json!` の中からしか呼ばれない関数が「どこからも到達しない」に化ける。
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from . import base
from . import resources as res

# 経路を定義する HTTP メソッド名(axum の `get(h)`、actix の `web::get()`・`#[get]`、rocket の `#[get]`)
ROUTE_METHODS = {
    "get": "GET", "post": "POST", "put": "PUT", "patch": "PATCH", "delete": "DELETE",
    "head": "HEAD", "options": "OPTIONS", "trace": "TRACE", "connect": "CONNECT",
    "any": "ANY",
}
# actix の `web::route()` / rocket の `#[route]` はメソッドを別に持つ(無ければ ANY)
ANY_ROUTE = {"route", "method"}

# 受け手の型が分からないときに内部シンボルと照合しない名前(標準ライブラリ・常用トレイトのメソッド)。
# Go / TS 版と同じ理由 — 同名衝突で**確度「確定」の偽の辺**を作らない(directions §5.6)。
STD_METHODS = {
    "clone", "to_owned", "to_string", "into", "try_into", "from", "as_ref", "as_mut",
    "borrow", "borrow_mut", "deref", "unwrap", "expect", "unwrap_or", "unwrap_or_else",
    "unwrap_or_default", "ok", "err", "ok_or", "ok_or_else", "map", "map_err", "and_then",
    "or_else", "is_some", "is_none", "is_ok", "is_err", "iter", "iter_mut", "into_iter",
    "collect", "filter", "filter_map", "find", "any", "all", "fold", "count", "sum", "max",
    "min", "rev", "zip", "enumerate", "chain", "take", "skip", "next", "last", "first",
    "len", "is_empty", "push", "pop", "insert", "remove", "get", "get_mut", "contains",
    "contains_key", "extend", "clear", "join", "split", "trim", "lines", "chars", "bytes",
    "as_str", "as_bytes", "parse", "format", "write", "write_all", "read", "read_to_string",
    "flush", "lock", "read_line", "send", "recv", "await", "spawn", "sort", "sort_by",
    "dedup", "retain", "keys", "values", "entry", "or_insert", "or_default", "starts_with",
    "ends_with", "replace", "to_lowercase", "to_uppercase", "eq", "cmp", "partial_cmp",
    "hash", "fmt", "default", "new", "build", "finish", "with_capacity", "drain", "copied",
    "cloned", "flatten", "flat_map", "take_while", "skip_while", "position", "windows",
    "chunks", "as_slice", "to_vec", "into_inner", "set", "take_mut", "poll", "wait",
    "unwrap_err", "context", "with_context", "json", "text", "status", "header", "body",
}
# 中身の型を素通しする包み(`Arc<Repo>` の `repo.m()` は `Repo::m` へ解く)
WRAPPER_TYPES = {
    "Box", "Arc", "Rc", "RefCell", "Cell", "Mutex", "RwLock", "Option", "Data", "State",
    "Extension", "Json", "Weak", "Pin", "ManuallyDrop", "Cow",
}
# HTTP クライアント(境界の候補)。受け手の名前の部分一致で見る(TS 版と同じ理由)
HTTP_CLIENT_HINTS = ("client", "http", "reqwest", "api", "gateway")
HTTP_CLIENT_METHODS = {"get", "post", "put", "patch", "delete", "head", "request"}
# 環境変数の読み取り
ENV_FUNCS = {"var", "var_os"}
ENV_MODULES = {"env", "dotenvy", "dotenv", "std::env"}

MACRO_CALL_LIMIT = 200           # 1つのマクロから字句で拾う呼び出しの上限(暴走防止)
PREFIX_LIMIT = 16                # 1関数あたりの接頭辞の組み合わせの上限(爆発防止)


# --------------------------------------------------------------------------- 準備

def _load_parser():
    """tree-sitter は版によって API が動くので、適合はここ1箇所に閉じる(design §5 リスク)。"""
    try:
        import tree_sitter_rust
        from tree_sitter import Language, Parser
    except ImportError as exc:
        raise RuntimeError(
            f"tree-sitter-rust が無い({exc})。`python3 .claude/scripts/setup-tools.py` で"
            "キット専用 venv に導入すること") from exc
    lang = Language(tree_sitter_rust.language())
    try:
        return Parser(lang)
    except TypeError:                                # 古い API
        p = Parser()
        p.set_language(lang)
        return p


def _txt(src: bytes, node) -> str:
    return src[node.start_byte:node.end_byte].decode("utf-8", "replace")


def _f(node, name):
    return node.child_by_field_name(name) if node is not None else None


def _find(node, kinds: set[str], out: list) -> None:
    for c in node.children:
        if c.type in kinds:
            out.append(c)
        _find(c, kinds, out)


def _args(call) -> list:
    a = _f(call, "arguments")
    return [c for c in (a.children if a is not None else []) if c.is_named
            and c.type not in {"line_comment", "block_comment", "attribute_item"}]


def _str_lit(src: bytes, node) -> str | None:
    """文字列リテラルの中身。`r"…"` と `"…".to_string()` / `String::from("…")` も剥がす。"""
    if node is None:
        return None
    if node.type in {"string_literal", "raw_string_literal"}:
        parts = [c for c in node.children if c.type == "string_content"]
        if parts:
            return "".join(_txt(src, p) for p in parts)
        t = _txt(src, node)
        m = re.match(r'^r#*"(.*)"#*$', t, re.S) or re.match(r'^"(.*)"$', t, re.S)
        return m.group(1) if m else None
    if node.type == "reference_expression":
        return _str_lit(src, _f(node, "value"))
    if node.type == "call_expression":
        fn = _f(node, "function")
        if fn is not None and fn.type == "field_expression":
            if _txt(src, _f(fn, "field")) in {"to_string", "to_owned", "into"}:
                return _str_lit(src, _f(fn, "value"))
        if fn is not None and _txt(src, fn) in {"String::from", "str::to_string"}:
            a = _args(node)
            return _str_lit(src, a[0]) if a else None
    return None


def _segments(src: bytes, node) -> list[str] | None:
    """パス式を区間の並びにする(`crate::a::B` → [crate, a, B])。解けない形は None。"""
    if node is None:
        return None
    t = node.type
    if t in {"identifier", "type_identifier", "field_identifier", "crate", "self", "super",
             "metavariable"}:
        return [_txt(src, node)]
    if t in {"scoped_identifier", "scoped_type_identifier"}:
        name = _f(node, "name")
        path = _f(node, "path")
        head = _segments(src, path) if path is not None else []
        if head is None or name is None:
            return None
        return head + [_txt(src, name)]
    if t == "generic_type":
        return _segments(src, _f(node, "type"))
    if t == "generic_function":
        return _segments(src, _f(node, "function"))
    return None                                         # `<T as Tr>::m` など


def _attr_list(item) -> list:
    """項目の直前に並ぶ `#[…]`(兄弟ノード)を返す。tree-sitter は属性を兄弟として置く。"""
    out = []
    prev = item.prev_named_sibling
    while prev is not None and prev.type in {"attribute_item", "line_comment", "block_comment"}:
        if prev.type == "attribute_item":
            out.append(prev)
        prev = prev.prev_named_sibling
    return list(reversed(out))


def _attr_name(src: bytes, attr_item) -> str:
    a = next((c for c in attr_item.children if c.type == "attribute"), None)
    if a is None or not a.children:
        return ""
    return _txt(src, a.children[0])


def _is_test_item(src: bytes, item) -> bool:
    for a in _attr_list(item):
        name = _attr_name(src, a)
        body = _txt(src, a)
        if name in {"test", "tokio::test", "rstest", "async_std::test", "actix_rt::test",
                    "actix_web::test", "sqlx::test"}:
            return True
        if name == "cfg" and re.search(r"\btest\b", body) and "not(test)" not in body:
            return True
    return False


def _is_pub(node) -> bool:
    return any(c.type == "visibility_modifier" for c in node.children)


# --------------------------------------------------------------------------- クレートとモジュールの木

class _Target:
    """1つのビルド対象(ライブラリ1つ、またはバイナリ1つ)。モジュールの木の根を持つ。"""

    def __init__(self, tid: str, crate_dir: str, root_rel: str, kind: str, lib_name: str):
        self.tid, self.crate_dir, self.root_rel = tid, crate_dir, root_rel
        self.kind, self.lib_name = kind, lib_name


def _read_cargo(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def _discover_targets(root: Path, rels: list[str]) -> list[_Target]:
    """`.rs` を含むクレート(`Cargo.toml` の `[package]`)ごとに、ライブラリとバイナリの根を決める。"""
    crate_dirs: set[str] = set()
    for rel in rels:
        parts = rel.split("/")[:-1]
        for i in range(len(parts), -1, -1):
            d = "/".join(parts[:i])
            if (root / d / "Cargo.toml").is_file() if d else (root / "Cargo.toml").is_file():
                data = _read_cargo(root / d / "Cargo.toml" if d else root / "Cargo.toml")
                if "package" in data:
                    crate_dirs.add(d)
                    break
    known = set(rels)
    out: list[_Target] = []
    for d in sorted(crate_dirs):
        pre = f"{d}/" if d else ""
        data = _read_cargo(root / pre / "Cargo.toml")
        pkg = (data.get("package") or {}).get("name", d.rsplit("/", 1)[-1] or "crate")
        lib = data.get("lib") or {}
        lib_name = str(lib.get("name") or pkg).replace("-", "_")
        lib_path = pre + str(lib.get("path") or "src/lib.rs")
        if lib_path in known:
            out.append(_Target(f"{pre}#lib", d, lib_path, "lib", lib_name))
        bins: dict[str, str] = {}
        if f"{pre}src/main.rs" in known:
            bins[pkg] = f"{pre}src/main.rs"
        for rel in sorted(known):
            if rel.startswith(f"{pre}src/bin/"):
                tail = rel[len(f"{pre}src/bin/"):]
                if "/" not in tail:
                    bins.setdefault(tail[:-3], rel)
                elif tail.count("/") == 1 and tail.endswith("/main.rs"):
                    bins.setdefault(tail.split("/")[0], rel)
        for b in data.get("bin") or []:
            if isinstance(b, dict) and b.get("path") and pre + str(b["path"]) in known:
                bins[str(b.get("name") or b["path"])] = pre + str(b["path"])
        for name, rel in sorted(bins.items()):
            out.append(_Target(f"{pre}#bin:{name}", d, rel, "bin", lib_name))
    return out


def _child_dir(rel: str, is_root: bool) -> str:
    """`mod x;` を探すディレクトリ。根と `mod.rs` は自分の置き場、それ以外は `<stem>/`。"""
    d, _, name = rel.rpartition("/")
    if is_root or name == "mod.rs":
        return d
    return f"{d}/{name[:-3]}" if d else name[:-3]


# --------------------------------------------------------------------------- 収集(1パス目)

class _Mod:
    def __init__(self, key, rel: str, parent):
        self.key, self.rel, self.parent = key, rel, parent
        self.fns: dict[str, str] = {}
        self.types: dict[str, tuple] = {}
        self.mods: dict[str, tuple] = {}
        self.uses: dict[str, list[str]] = {}
        self.globs: list[list[str]] = []
        self.consts: dict[str, str] = {}


class _Type:
    def __init__(self, key, kind: str):
        self.key, self.kind = key, kind
        self.fields: dict[str, object] = {}           # フィールド名 → 型ノード(src と組)
        self.methods: dict[str, str] = {}
        self.traits: list[tuple] = []                 # 実装しているトレイトの型キー
        self.generics: set[str] = set()               # 構造体の型引数(`struct S<T>` の `T`)


class _Unit:
    """本体を持つ関数1つ。"""

    def __init__(self, sid, node, mod, rel, src, self_type, attrs):
        self.sid, self.node, self.mod, self.rel, self.src = sid, node, mod, rel, src
        self.self_type, self.attrs = self_type, attrs


class _World:
    def __init__(self):
        self.mods: dict[tuple, _Mod] = {}
        self.types: dict[tuple, _Type] = {}
        self.libs: dict[str, tuple] = {}              # ライブラリ名 → その根のモジュールキー
        self.roots: dict[str, tuple] = {}             # target id → 根のモジュールキー
        self.units: list[_Unit] = []
        self.symbols: list[dict] = []
        self.sids: set[str] = set()
        self.ret_self: set[str] = set()               # 戻り型が Self(か包んだもの)の関数
        self.ret_type: dict[str, tuple] = {}          # 関数 → 戻り型の (型ノード, src, mod)
        self.by_name: dict[str, list[str]] = {}       # メソッド名 → sid(全型)
        self.trait_impls: dict[tuple, list[str]] = {}  # (トレイト型キー, メソッド名) → 実装の sid
        self.raw_impls: list[tuple] = []
        self.raw_fields: list[tuple] = []
        self.test_items: dict[str, int] = {}

    def add_symbol(self, rel: str, qual: str, kind: str, public: bool) -> str:
        sid = base.symbol_id(rel, qual)
        n = 2
        while sid in self.sids:                       # 同じ修飾名(トレイトの同名メソッド等)
            sid = base.symbol_id(rel, f"{qual}#{n}")
            n += 1
        self.sids.add(sid)
        self.symbols.append({"id": sid, "file": rel, "name": sid.split("::", 1)[1],
                             "kind": kind, "visibility": "public" if public else "private"})
        return sid


def _parse_use(src: bytes, node, prefix: list[str], out: dict, globs: list) -> None:
    t = node.type
    if t in {"identifier", "scoped_identifier", "crate", "self", "super"}:
        segs = _segments(src, node)
        if segs is None:
            return
        full = prefix + segs
        if segs == ["self"]:
            full = prefix
        if full:
            out[full[-1]] = full
    elif t == "use_as_clause":
        segs = _segments(src, _f(node, "path"))
        alias = _f(node, "alias")
        if segs is not None and alias is not None and _txt(src, alias) != "_":
            full = prefix + segs if segs != ["self"] else prefix
            out[_txt(src, alias)] = full
    elif t == "scoped_use_list":
        p = _f(node, "path")
        segs = _segments(src, p) if p is not None else []
        lst = _f(node, "list")
        if segs is not None and lst is not None:
            _parse_use(src, lst, prefix + segs, out, globs)
    elif t == "use_list":
        for c in node.named_children:
            _parse_use(src, c, prefix, out, globs)
    elif t == "use_wildcard":
        kids = [c for c in node.named_children]
        segs = _segments(src, kids[0]) if kids else []
        if segs is not None:
            globs.append(prefix + segs)


def _collect_items(w: _World, rel: str, src: bytes, container, mod: _Mod,
                   qual_prefix: str, child_dir: str, files: dict, trees: dict,
                   target, pending: list) -> None:
    for item in container.named_children:
        t = item.type
        if t in {"attribute_item", "line_comment", "block_comment", "inner_attribute_item"}:
            continue
        if _is_test_item(src, item):
            w.test_items[rel] = w.test_items.get(rel, 0) + 1
            continue
        if t == "function_item":
            n = _f(item, "name")
            if n is None:
                continue
            name = _txt(src, n)
            sid = w.add_symbol(rel, qual_prefix + name, "function", _is_pub(item))
            mod.fns.setdefault(name, sid)
            _note_ret(w, sid, item, src, mod, None)
            if _f(item, "body") is not None:
                w.units.append(_Unit(sid, item, mod, rel, src, None, _attr_list(item)))
        elif t in {"struct_item", "enum_item", "union_item", "trait_item", "type_item"}:
            n = _f(item, "name")
            if n is None:
                continue
            name = _txt(src, n)
            key = (mod.key, name)
            mod.types.setdefault(name, key)
            ty = w.types.setdefault(key, _Type(key, t))
            if t == "struct_item":
                tp = _f(item, "type_parameters")
                for c in (tp.named_children if tp is not None else []):
                    gname = _f(c, "name") if c.type != "type_identifier" else c
                    if gname is not None:
                        ty.generics.add(_txt(src, gname))
                body = _f(item, "body")
                for fd in (body.named_children if body is not None else []):
                    if fd.type == "field_declaration":
                        fn_, ft = _f(fd, "name"), _f(fd, "type")
                        if fn_ is not None and ft is not None:
                            ty.fields[_txt(src, fn_)] = (ft, src, mod)
            elif t == "trait_item":
                body = _f(item, "body")
                for m in (body.named_children if body is not None else []):
                    if m.type != "function_item" or _is_test_item(src, m):
                        continue
                    mn = _f(m, "name")
                    if mn is None:
                        continue
                    sid = w.add_symbol(rel, f"{qual_prefix}{name}.{_txt(src, mn)}", "method",
                                       _is_pub(item))
                    ty.methods.setdefault(_txt(src, mn), sid)
                    w.by_name.setdefault(_txt(src, mn), []).append(sid)
                    _note_ret(w, sid, m, src, mod, key)
                    if _f(m, "body") is not None:
                        w.units.append(_Unit(sid, m, mod, rel, src, key, _attr_list(m)))
        elif t == "impl_item":
            w.raw_impls.append((item, src, rel, mod, qual_prefix))
        elif t in {"const_item", "static_item"}:
            n, v = _f(item, "name"), _f(item, "value")
            lit = _str_lit(src, v)
            if n is not None and lit is not None:
                mod.consts[_txt(src, n)] = lit
        elif t == "use_declaration":
            arg = _f(item, "argument")
            if arg is not None:
                _parse_use(src, arg, [], mod.uses, mod.globs)
        elif t == "mod_item":
            n = _f(item, "name")
            if n is None:
                continue
            name = _txt(src, n)
            key = (mod.key[0], mod.key[1] + (name,))
            sub = w.mods.get(key) or _Mod(key, rel, mod.key)
            w.mods[key] = sub
            mod.mods[name] = key
            body = _f(item, "body")
            if body is not None:
                _collect_items(w, rel, src, body, sub, f"{qual_prefix}{name}.",
                               f"{child_dir}/{name}" if child_dir else name, files, trees,
                               target, pending)
            else:
                path_attr = None
                for a in _attr_list(item):
                    m = re.search(r'path\s*=\s*"([^"]+)"', _txt(src, a))
                    if m and _attr_name(src, a) == "path":
                        path_attr = m.group(1)
                cands = []
                if path_attr:
                    base_dir = rel.rpartition("/")[0]
                    cands.append(f"{base_dir}/{path_attr}" if base_dir else path_attr)
                pre = f"{child_dir}/" if child_dir else ""
                cands += [f"{pre}{name}.rs", f"{pre}{name}/mod.rs"]
                hit = next((c for c in cands if c in files), None)
                if hit is not None:
                    pending.append((hit, sub, target))


def _note_ret(w: _World, sid: str, fn_node, src: bytes, mod: _Mod, self_type) -> None:
    rt = _f(fn_node, "return_type")
    if rt is None:
        return
    text = _txt(src, rt)
    if re.search(r"\bSelf\b", text):
        w.ret_self.add(sid)
    w.ret_type[sid] = (rt, src, mod)


# --------------------------------------------------------------------------- 名前解決

class _Resolver:
    def __init__(self, w: _World):
        self.w = w

    def lookup(self, mkey, name: str, depth: int = 0):
        if depth > 12 or mkey not in self.w.mods:
            return None
        m = self.w.mods[mkey]
        if name in m.fns:
            return ("fn", m.fns[name])
        if name in m.types:
            return ("type", m.types[name])
        if name in m.mods:
            return ("mod", m.mods[name])
        if name in m.uses:
            return self.resolve(mkey, m.uses[name], None, depth + 1)
        for g in m.globs:
            got = self.resolve(mkey, g, None, depth + 1)
            if got and got[0] == "mod" and got[1] != mkey:
                hit = self.lookup(got[1], name, depth + 1)
                if hit:
                    return hit
            elif got and got[0] == "type":            # `use Enum::*` — 列挙子
                return None
        return None

    def parent(self, mkey):
        m = self.w.mods.get(mkey)
        return m.parent if m is not None else None

    def resolve(self, mkey, segs: list[str], self_type, depth: int = 0):
        """パスを ("fn", sid) / ("type", key) / ("mod", key) / ("member", type_key, name) に解く。
        外部(標準ライブラリ・依存クレート)なら None。"""
        if not segs or depth > 12:
            return None
        first, rest = segs[0], segs[1:]
        if first == "crate":
            cur = ("mod", (mkey[0], ()))
        elif first == "self":
            cur = ("mod", mkey)
        elif first == "super":
            cur = ("mod", self.parent(mkey))
            while rest and rest[0] == "super" and cur[1] is not None:
                cur = ("mod", self.parent(cur[1]))
                rest = rest[1:]
            if cur[1] is None:
                return None
        elif first == "Self":
            if self_type is None:
                return None
            cur = ("type", self_type)
        else:
            cur = self.lookup(mkey, first, depth)
            if cur is None and first in self.w.libs:
                cur = ("mod", self.w.libs[first])
            if cur is None:
                return None
        for s in rest:
            kind = cur[0]
            if kind == "mod":
                cur = self.lookup(cur[1], s, depth + 1)
                if cur is None:
                    return None
            elif kind == "type":
                ty = self.w.types.get(cur[1])
                if ty is not None and s in ty.methods:
                    cur = ("fn", ty.methods[s])
                else:
                    cur = ("member", cur[1], s)
            else:
                return None
        return cur

    def type_of(self, type_node, src: bytes, mkey, self_type, depth: int = 0):
        """型ノードを内部の型キーに解く。包み(`Arc<T>` 等)は剥がす。外部なら None。"""
        n = type_node
        while n is not None and depth < 8:
            depth += 1
            t = n.type
            if t in {"reference_type", "pointer_type"}:
                n = _f(n, "type")
                continue
            if t in {"abstract_type", "dynamic_type"}:
                n = _f(n, "trait")
                continue
            if t == "generic_type":
                base_segs = _segments(src, _f(n, "type")) or []
                if base_segs and base_segs[-1] in WRAPPER_TYPES:
                    args = _f(n, "type_arguments")
                    inner = [c for c in (args.named_children if args is not None else [])
                             if c.type not in {"lifetime"}]
                    n = inner[0] if inner else None
                    continue
                got = self.resolve(mkey, base_segs, self_type) if base_segs else None
                return got[1] if got and got[0] == "type" else None
            if t in {"type_identifier", "scoped_type_identifier", "identifier",
                     "scoped_identifier"}:
                segs = _segments(src, n)
                if segs == ["Self"]:
                    return self_type
                got = self.resolve(mkey, segs, self_type) if segs else None
                return got[1] if got and got[0] == "type" else None
            return None
        return None

    def method(self, type_key, name: str) -> tuple[str | None, list[str]]:
        """型(またはトレイト)のメソッドを引く。(一意の sid, 候補) を返す。"""
        ty = self.w.types.get(type_key)
        if ty is None:
            return None, []
        if name in ty.methods:
            return ty.methods[name], []
        for tr in ty.traits:                           # トレイトの既定実装
            trt = self.w.types.get(tr)
            if trt is not None and name in trt.methods:
                return trt.methods[name], []
        if ty.kind == "trait_item":                     # トレイトオブジェクト越し
            impls = sorted(set(self.w.trait_impls.get((type_key, name), [])))
            if len(impls) == 1:
                return impls[0], []
            return None, impls
        return None, []


def _finish_impls(w: _World, rv: _Resolver) -> None:
    """`impl` のメソッドを記号にし、型に結びつける(型は全ファイルの収集後でないと引けない)。"""
    for item, src, rel, mod, qual_prefix in w.raw_impls:
        tnode = _f(item, "type")
        trnode = _f(item, "trait")
        segs = _segments(src, tnode) if tnode is not None else None
        tname = segs[-1] if segs else _txt(src, tnode) if tnode is not None else "?"
        tkey = rv.type_of(tnode, src, mod.key, None) if tnode is not None else None
        if tkey is None:                                 # 外部の型への impl(またはトレイト経由)
            tkey = (("?", rel), tname)
        ty = w.types.setdefault(tkey, _Type(tkey, "struct_item"))
        trkey = None
        if trnode is not None:
            trsegs = _segments(src, trnode)
            got = rv.resolve(mod.key, trsegs, None) if trsegs else None
            trkey = got[1] if got and got[0] == "type" else None
            if trkey is not None and trkey not in ty.traits:
                ty.traits.append(trkey)
        body = _f(item, "body")
        for m in (body.named_children if body is not None else []):
            if m.type != "function_item" or _is_test_item(src, m):
                if m.type == "function_item":
                    w.test_items[rel] = w.test_items.get(rel, 0) + 1
                continue
            mn = _f(m, "name")
            if mn is None:
                continue
            name = _txt(src, mn)
            public = _is_pub(m) or trnode is not None
            sid = w.add_symbol(rel, f"{qual_prefix}{tname}.{name}", "method", public)
            ty.methods.setdefault(name, sid)
            w.by_name.setdefault(name, []).append(sid)
            if trkey is not None:
                w.trait_impls.setdefault((trkey, name), []).append(sid)
            _note_ret(w, sid, m, src, mod, tkey)
            if _f(m, "body") is not None:
                w.units.append(_Unit(sid, m, mod, rel, src, tkey, _attr_list(m)))
    for k in w.by_name:
        w.by_name[k] = sorted(set(w.by_name[k]))


# --------------------------------------------------------------------------- 関数本体の解析

class _Scope:
    """1つの関数の中の束縛(位置つき)と、推定できた型。"""

    def __init__(self, u: _Unit, rv: _Resolver):
        self.u, self.rv = u, rv
        self.binds: dict[str, list[int]] = {}         # 名前 → 束縛された位置(バイト)
        self.types: dict[str, tuple] = {}             # 名前 → 型キー
        self.lets: dict[str, list] = {}               # 名前 → let の右辺ノード
        self.ext: set[str] = set()                    # 型が外部(依存クレート・標準)と明示された名前
        self.generics: set[str] = _generic_names(u)

    def bound(self, name: str, at: int) -> bool:
        return any(p <= at for p in self.binds.get(name, []))

    def bind(self, name: str, at: int) -> None:
        self.binds.setdefault(name, []).append(at)


def _pattern_names(src: bytes, pat, out: list) -> None:
    if pat is None:
        return
    if pat.type == "identifier":
        out.append(_txt(src, pat))
        return
    for i, c in enumerate(pat.children):
        # `State(st)` の `State` / `Some(x)` の `Some` は型の名前であって束縛ではない
        if pat.type == "tuple_struct_pattern" and pat.field_name_for_child(i) == "type":
            continue
        if pat.type == "struct_pattern" and pat.field_name_for_child(i) == "type":
            continue
        if c.type in {"identifier", "tuple_struct_pattern", "tuple_pattern", "struct_pattern",
                      "field_pattern", "reference_pattern", "ref_pattern", "mut_pattern",
                      "slice_pattern", "or_pattern", "captured_pattern", "shorthand_field_identifier"}:
            if c.type == "shorthand_field_identifier":
                out.append(_txt(src, c))
            else:
                _pattern_names(src, c, out)


def _build_scope(u: _Unit, rv: _Resolver) -> _Scope:
    sc = _Scope(u, rv)
    src = u.src
    params = _f(u.node, "parameters")
    for p in (params.named_children if params is not None else []):
        if p.type != "parameter":
            continue
        pat, ty = _f(p, "pattern"), _f(p, "type")
        names: list[str] = []
        _pattern_names(src, pat, names)
        for nm in names:
            sc.bind(nm, 0)
        if ty is None:
            continue
        tkey = rv.type_of(ty, src, u.mod.key, u.self_type)
        if tkey is not None and len(names) == 1:
            sc.types[names[0]] = tkey
        elif len(names) == 1 and _is_external_type(ty, src, u, rv, sc.generics):
            sc.ext.add(names[0])
    body = _f(u.node, "body")
    if body is None:
        return sc
    nodes: list = []
    _find(body, {"let_declaration", "for_expression", "closure_parameters", "let_condition",
                 "match_arm"}, nodes)
    for n in nodes:
        names = []
        if n.type == "closure_parameters":
            for p in n.named_children:
                _pattern_names(src, _f(p, "pattern") if p.type == "parameter" else p, names)
        elif n.type == "match_arm":
            pat = _f(n, "pattern")
            _pattern_names(src, pat, names)
        else:
            _pattern_names(src, _f(n, "pattern"), names)
        # 束縛が効き始める位置。**`let` は文の後、`if let` / `for` は右辺の後**からである —
        # `let Some(route) = route(…) else {…}` の右辺の `route` は同じ綴りの関数を指す
        # (先頭から効かせると、その呼び出しが「関数を値で受けた変数の呼び出し」に化けて辺が消える。
        # 2026-10-31 に実プロジェクトで実測)
        if n.type in {"let_declaration"}:
            at = n.end_byte
        elif n.type in {"let_condition", "for_expression"}:
            v = _f(n, "value")
            at = v.end_byte if v is not None else n.start_byte
        else:
            at = n.start_byte
        for nm in names:
            sc.bind(nm, at)
        if n.type == "let_declaration" and len(names) == 1:
            nm = names[0]
            val = _f(n, "value")
            if val is not None:
                sc.lets.setdefault(nm, []).append(val)
            tnode = _f(n, "type")
            tkey = rv.type_of(tnode, src, u.mod.key, u.self_type) if tnode is not None else None
            if tkey is None and val is not None:
                tkey = _expr_type(val, src, u, rv, sc)
            if tkey is not None:
                sc.types[nm] = tkey
                sc.ext.discard(nm)
            else:
                sc.types.pop(nm, None)                  # 後の束縛が前の型推定を覆う
                if tnode is not None and _is_external_type(tnode, src, u, rv, sc.generics):
                    sc.ext.add(nm)
                else:
                    sc.ext.discard(nm)
    return sc


def _generic_names(u: _Unit) -> set[str]:
    """関数と、それを囲む `impl` の型引数の名前(`T` など)。外部の型と取り違えないために使う。"""
    out: set[str] = set()
    nodes = [u.node]
    par = u.node.parent
    if par is not None and par.parent is not None and par.parent.type in {"impl_item", "trait_item"}:
        nodes.append(par.parent)
    for n in nodes:
        tp = _f(n, "type_parameters")
        for c in (tp.named_children if tp is not None else []):
            name = _f(c, "name") if c.type != "type_identifier" else c
            if name is not None:
                out.add(_txt(u.src, name))
    return out


def _is_external_type(type_node, src: bytes, u: _Unit, rv: _Resolver, generics: set[str]) -> bool:
    """型の注釈が**外部の型**(依存クレート・標準ライブラリ・組み込み型)を指すと言い切れるか。

    `client: aws_sdk_dynamodb::Client` のフィールドや引数の `client.get_item()` を、同じ名前の
    内部メソッドへ名前だけで結ばないためにある(2026-11-01 に実プロジェクトで、AWS の SDK の
    `get_item` が内部の `Store.get_item` に結ばれ、重大度「高」の偽の取りこぼしが出た)。
    型引数(`T`)・`Self`・`impl`/`dyn` のトレイト・包みの中が解けないものは「言い切れない」とする。
    """
    n = type_node
    for _ in range(8):
        if n is None:
            return False
        t = n.type
        if t in {"reference_type", "pointer_type"}:
            n = _f(n, "type")
            continue
        if t == "primitive_type":
            return True
        if t == "generic_type":
            segs = _segments(src, _f(n, "type")) or []
            if segs and segs[-1] in WRAPPER_TYPES:
                args = _f(n, "type_arguments")
                inner = [c for c in (args.named_children if args is not None else [])
                         if c.type != "lifetime"]
                n = inner[0] if inner else None
                continue
            break
        break
    if n is None or n.type not in {"type_identifier", "scoped_type_identifier", "generic_type"}:
        return False
    segs = _segments(src, n) or []
    if not segs or segs[0] in {"Self", "crate", "self", "super"} or segs[-1] in generics:
        return False
    if len(segs) == 1 and segs[0] in generics:
        return False
    return rv.resolve(u.mod.key, segs, u.self_type) is None


def _known_external(recv, src: bytes, u: _Unit, rv: _Resolver, sc: _Scope) -> bool:
    """受け手の型が外部だと**注釈から**分かっているか(引数・`let`・構造体のフィールド)。"""
    if recv is None:
        return False
    if recv.type == "identifier":
        return _txt(src, recv) in sc.ext
    if recv.type == "field_expression":
        owner = _expr_type(_f(recv, "value"), src, u, rv, sc)
        ty = rv.w.types.get(owner) if owner is not None else None
        fld = _f(recv, "field")
        if ty is None or fld is None or _txt(src, fld) not in ty.fields:
            return False
        ft, fsrc, fmod = ty.fields[_txt(src, fld)]
        if rv.type_of(ft, fsrc, fmod.key, owner) is not None:
            return False
        fu = _Unit("", None, fmod, "", fsrc, owner, [])
        return _is_external_type(ft, fsrc, fu, rv, ty.generics)
    return False


def _expr_type(node, src: bytes, u: _Unit, rv: _Resolver, sc: _Scope | None):
    """式の型を推定する(`T::new()` / `T { … }` / `self.field` / 引数・変数)。分からなければ None。"""
    if node is None:
        return None
    t = node.type
    if t in {"try_expression", "await_expression", "reference_expression",
             "parenthesized_expression"}:
        kids = [c for c in node.named_children]
        return _expr_type(kids[0], src, u, rv, sc) if kids else None
    if t == "struct_expression":
        segs = _segments(src, _f(node, "name"))
        got = rv.resolve(u.mod.key, segs, u.self_type) if segs else None
        return got[1] if got and got[0] == "type" else None
    if t == "self":
        return u.self_type
    if t == "identifier" and sc is not None:
        return sc.types.get(_txt(src, node))
    if t == "field_expression":
        owner = _expr_type(_f(node, "value"), src, u, rv, sc)
        ty = rv.w.types.get(owner) if owner is not None else None
        fld = _f(node, "field")
        if ty is not None and fld is not None and _txt(src, fld) in ty.fields:
            ft, fsrc, fmod = ty.fields[_txt(src, fld)]
            return rv.type_of(ft, fsrc, fmod.key, owner)
        return None
    if t == "call_expression":
        fn = _f(node, "function")
        if fn is not None and fn.type == "field_expression":
            # `x.clone()` / `x.unwrap()` は型を保つとみなす(包みの剥がしと同じ近似)
            fld = _txt(src, _f(fn, "field")) if _f(fn, "field") is not None else ""
            if fld in {"clone", "unwrap", "expect", "to_owned", "lock", "read", "write",
                       "borrow", "borrow_mut", "as_ref"}:
                return _expr_type(_f(fn, "value"), src, u, rv, sc)
            return None
        segs = _segments(src, fn)
        if not segs:
            return None
        got = rv.resolve(u.mod.key, segs, u.self_type)
        if got and got[0] == "fn":
            if got[1] in rv.w.ret_self:
                # `T::new()` — T は呼び出しのパスの1つ手前
                owner = rv.resolve(u.mod.key, segs[:-1], u.self_type) if len(segs) > 1 else None
                if owner and owner[0] == "type":
                    return owner[1]
            ret = rv.w.ret_type.get(got[1])
            if ret is not None:
                rt, rsrc, rmod = ret
                return rv.type_of(rt, rsrc, rmod.key, None)
        if got and got[0] == "type":                    # タプル構造体の生成 `T(x)`
            return got[1]
    return None


def _resolve_call(call, src: bytes, u: _Unit, rv: _Resolver, sc: _Scope
                  ) -> tuple[str | None, dict | None, bool]:
    """(呼び先 sid, 未解決レコード, 外部か)。"""
    fn = _f(call, "function")
    if fn is None:
        return None, None, True
    if fn.type == "generic_function":
        fn = _f(fn, "function")
        if fn is None:
            return None, None, True
    t = fn.type
    if t in {"call_expression", "parenthesized_expression", "closure_expression"}:
        return None, {"reason": "higher-order"}, False
    if t == "index_expression":
        return None, {"reason": "dynamic"}, False
    if t == "identifier":
        name = _txt(src, fn)
        if sc.bound(name, call.start_byte):
            return None, {"reason": "higher-order"}, False
        got = rv.resolve(u.mod.key, [name], u.self_type)
        if got and got[0] == "fn":
            return got[1], None, False
        return None, None, True
    if t == "scoped_identifier":
        segs = _segments(src, fn)
        if segs is None:                                 # `<T as Tr>::m()`
            return None, {"reason": "dynamic"}, False
        got = rv.resolve(u.mod.key, segs, u.self_type)
        if got and got[0] == "fn":
            return got[1], None, False
        if got and got[0] == "member":
            hit, cands = rv.method(got[1], got[2])
            if hit:
                return hit, None, False
            if cands:
                return None, {"reason": "ambiguous", "candidates": cands}, False
        return None, None, True
    if t == "field_expression":
        fld = _f(fn, "field")
        if fld is None:
            return None, None, True
        name = _txt(src, fld)
        recv = _f(fn, "value")
        rtype = _expr_type(recv, src, u, rv, sc)
        if rtype is not None:
            hit, cands = rv.method(rtype, name)
            if hit:
                return hit, None, False
            if cands:
                return None, {"reason": "ambiguous", "candidates": cands}, False
            if rv.w.types.get(rtype) is not None and rtype[0][0] != "?":
                return None, None, True                   # 内部の型だが該当なし = 標準のトレイト等
        if name in STD_METHODS or _external_root(recv, src, u, rv, sc) \
                or _known_external(recv, src, u, rv, sc):
            return None, None, True
        hits = rv.w.by_name.get(name, [])
        if len(hits) == 1:
            return hits[0], None, False
        if hits:
            return None, {"reason": "ambiguous", "candidates": hits}, False
        return None, None, True
    return None, None, True


def _external_root(recv, src: bytes, u: _Unit, rv: _Resolver, sc: _Scope,
                   depth: int = 0) -> bool:
    """メソッドの連鎖の根が**外部のパス**(依存クレート・標準ライブラリ)か。

    `aws_config::defaults(…).load()` の `load` を、同じ名前の内部メソッドの候補として
    報告しないためにある(2026-10-31 に実プロジェクトで、6候補の未解決が並んだ)。
    根が内部の関数・ローカル変数・`self` なら False(名前だけの照合へ回す)。
    """
    n = recv
    for _ in range(64):
        if n is None:
            return False
        t = n.type
        if t in {"try_expression", "await_expression", "parenthesized_expression",
                 "reference_expression"}:
            kids = n.named_children
            n = kids[0] if kids else None
            continue
        if t == "field_expression":
            n = _f(n, "value")
            continue
        if t == "call_expression":
            fn = _f(n, "function")
            if fn is not None and fn.type == "field_expression":
                n = _f(fn, "value")
                continue
            n = fn
            continue
        if t in {"scoped_identifier", "identifier", "generic_function"}:
            segs = _segments(src, n)
            if not segs:
                return False
            if len(segs) == 1:
                # `let c = reqwest::Client::builder();` で束ねた変数なら、その右辺の根を見る。
                # それ以外の単独の名前は内部関数か、型の分からない変数でありうる
                vals = [v for v in sc.lets.get(segs[0], []) if v.end_byte <= n.start_byte]
                if vals and depth < 4:
                    return _external_root(vals[-1], src, u, rv, sc, depth + 1)
                return False
            if segs[0] in {"crate", "self", "super", "Self"}:
                return False
            return rv.resolve(u.mod.key, segs, u.self_type) is None
        return False
    return False


def _macro_calls(tt, src: bytes) -> list[tuple[list[str], bool, int]]:
    """マクロの token_tree から、パスの形の呼び出しを字句で拾う。
    ([区間], self 経由のメソッド呼び出しか, 位置) を返す。"""
    out: list = []
    kids = list(tt.children)
    i = 0
    while i < len(kids) and len(out) < MACRO_CALL_LIMIT:
        c = kids[i]
        if c.type == "token_tree":
            out += _macro_calls(c, src)
            i += 1
            continue
        if c.type in {"identifier", "self", "super", "crate"}:
            segs = [_txt(src, c)]
            j = i + 1
            while j + 1 < len(kids) and kids[j].type == "::" and kids[j + 1].type in {
                    "identifier", "self", "super", "crate"}:
                segs.append(_txt(src, kids[j + 1]))
                j += 2
            if j < len(kids) and kids[j].type == "token_tree" and _txt(src, kids[j])[:1] == "(":
                prev = kids[i - 1] if i > 0 else None
                prev2 = kids[i - 2] if i > 1 else None
                is_bang = j < len(kids) and _txt(src, kids[j - 1]) == "!"
                if prev is not None and prev.type == "." :
                    if prev2 is not None and prev2.type == "self" and len(segs) == 1:
                        out.append((segs, True, c.start_byte))
                elif not is_bang:
                    out.append((segs, False, c.start_byte))
            i = j if j > i + 1 else i + 1
            continue
        i += 1
    return out


# --------------------------------------------------------------------------- 経路

def _call_name(src: bytes, call) -> tuple[str, object]:
    """呼び出しの名前(メソッド名・関数名の末尾)と、メソッドなら受け手のノード。"""
    fn = _f(call, "function")
    if fn is None:
        return "", None
    if fn.type == "generic_function":
        fn = _f(fn, "function")
    if fn is not None and fn.type == "field_expression":
        fld = _f(fn, "field")
        return (_txt(src, fld) if fld is not None else ""), _f(fn, "value")
    segs = _segments(src, fn) or []
    return (segs[-1] if segs else ""), None


def _chain_root(src: bytes, call):
    """メソッドの連鎖 `a().b().c()` の根の呼び出し(`a()`)。根が呼び出しでなければ None。"""
    cur = call
    while True:
        name, recv = _call_name(src, cur)
        if recv is None:
            return cur
        if recv.type != "call_expression":
            return None
        cur = recv


def _scope_prefix(src: bytes, call) -> str | None:
    """連鎖の根が `web::scope("/p")` / `scope("/p")` / `Scope::new("/p")` なら "/p"。"""
    root = _chain_root(src, call)
    if root is None:
        return None
    fn = _f(root, "function")
    segs = _segments(src, fn) or []
    if segs and (segs[-1] == "scope" or segs[-2:] == ["Scope", "new"]):
        a = _args(root)
        return _str_lit(src, a[0]) if a else None
    return None


def _local_prefixes(node, src: bytes, sc: _Scope, depth: int = 0) -> list[str]:
    """関数の中で `node` に掛かる接頭辞(関数の外から来る分は含まない)。"""
    if depth > 6:
        return [""]
    acc = [""]
    cur = node
    while cur is not None and cur.id != sc.u.node.id:
        par = cur.parent
        if par is None:
            break
        if par.type == "arguments":
            call = par.parent
            name, recv = _call_name(src, call)
            args = _args(call)
            pre = None
            if name in {"nest", "mount"} and len(args) >= 2 and args[1].id == cur.id:
                pre = _str_lit(src, args[0])
            elif name in {"service", "configure"} and recv is not None:
                pre = _scope_prefix(src, call)
            if pre:
                acc = [base.join_paths(pre, a) for a in acc]
        if par.type == "let_declaration" and _f(par, "value") is not None \
                and _f(par, "value").id == cur.id:
            names: list[str] = []
            _pattern_names(src, _f(par, "pattern"), names)
            if len(names) == 1:
                uses = _ident_uses(sc.u.node, src, names[0], par.end_byte)
                outs: list[str] = []
                for use in uses:
                    for up in _local_prefixes(use, src, sc, depth + 1):
                        outs += [base.join_paths(up, a) for a in acc]
                if outs:
                    return sorted(set(outs))[:PREFIX_LIMIT]
        cur = par
    return acc


_IDENT_CACHE: dict[int, list] = {}


def _ident_uses(fn_node, src: bytes, name: str, after: int) -> list:
    """関数の中で、`after` より後に `name` が**引数として**現れる位置。識別子の一覧は関数ごとに1度だけ集める。"""
    ids = _IDENT_CACHE.get(fn_node.id)
    if ids is None:
        ids = []
        _find(fn_node, {"identifier"}, ids)
        _IDENT_CACHE[fn_node.id] = ids
    return [i for i in ids if i.start_byte > after and i.parent is not None
            and i.parent.type == "arguments" and _txt(src, i) == name]


def _method_router(src: bytes, expr, u: _Unit, rv: _Resolver, sc: _Scope
                   ) -> list[tuple[str, str]]:
    """`get(h).post(h2)`(axum)/ `web::get().to(h)`(actix)から (メソッド, ハンドラ sid) を取る。

    見るのは**メソッドの連鎖と、関数の形の呼び出しの引数だけ**で、クロージャの中には降りない
    (ハンドラ本体の `client.get(…)` を経路と取り違えない)。
    """
    out: list = []
    calls: list = []

    def walk(n) -> None:
        if n.type == "closure_expression":
            return
        if n.type == "call_expression":
            calls.append(n)
        for c in n.children:
            walk(c)
    walk(expr)
    for c in calls:
        name, recv = _call_name(src, c)
        if recv is not None and recv.type != "call_expression":
            continue                                    # `x.get(…)` — 連鎖でないメソッドは経路でない
        args = _args(c)
        low = name.lower()
        if name in {"to", "to_async"} and args:
            root = _chain_root(src, c)
            rname = _call_name(src, root)[0] if root is not None and root.id != c.id else ""
            meth = ROUTE_METHODS.get(rname, "ANY")
            out.append((meth, _handler_of(args[0], src, u, rv, sc)))
        elif low in ROUTE_METHODS and args:
            out.append((ROUTE_METHODS[low], _handler_of(args[0], src, u, rv, sc)))
        elif name == "on" and len(args) >= 2:
            m = re.search(r"\b(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS|TRACE)\b", _txt(src, args[0]))
            out.append((m.group(1) if m else "ANY", _handler_of(args[1], src, u, rv, sc)))
    return out


def _handler_of(node, src: bytes, u: _Unit, rv: _Resolver, sc: _Scope) -> str:
    """経路のハンドラ。関数への参照なら解いた sid、クロージャ等なら定義している関数自身。"""
    segs = _segments(src, node)
    if segs and not (len(segs) == 1 and sc.bound(segs[0], node.start_byte)):
        got = rv.resolve(u.mod.key, segs, u.self_type)
        if got and got[0] == "fn":
            return got[1]
        if got and got[0] == "member":
            hit, _c = rv.method(got[1], got[2])
            if hit:
                return hit
        return ""
    return u.sid


def _attr_routes(src: bytes, attrs: list) -> list[tuple[str, str]]:
    """`#[get("/p")]` / `#[route("/p", method = "GET")]` から (メソッド, パス)。"""
    out = []
    for a in attrs:
        name = _attr_name(src, a).rsplit("::", 1)[-1]
        if name not in ROUTE_METHODS and name not in ANY_ROUTE:
            continue
        attr = next((c for c in a.children if c.type == "attribute"), None)
        tt = _f(attr, "arguments") if attr is not None else None
        if tt is None:
            continue
        lits = [c for c in tt.named_children if c.type in {"string_literal", "raw_string_literal"}]
        if not lits:
            continue
        path = _str_lit(src, lits[0]) or ""
        path = path.split("?", 1)[0]                    # rocket の問い合わせ部 `?<q>`
        if not path.startswith("/"):
            continue
        if name in ROUTE_METHODS:
            out.append((ROUTE_METHODS[name], path))
        else:
            meths = [(_str_lit(src, x) or "").upper() for x in lits[1:]]
            meths = [m for m in meths if re.fullmatch(r"[A-Z]+", m)]
            for m in meths or ["ANY"]:
                out.append((m, path))
    return out


# --------------------------------------------------------------------------- 資源

def _res_parts(node, src: bytes, consts: dict) -> list:
    lit = _str_lit(src, node)
    if lit is not None:
        return [lit]
    if node is not None and node.type in {"identifier", "scoped_identifier"}:
        segs = _segments(src, node) or []
        got = consts.get(segs[-1]) if segs else None
        return [got] if got is not None else [None]
    if node is not None and node.type == "reference_expression":
        return _res_parts(_f(node, "value"), src, consts)
    return [None]


def _snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


# --------------------------------------------------------------------------- 入口

def extract(root: Path, cfg: dict, scope: Path | None = None) -> dict:
    lang_cfg = cfg["languages"]["rust"]
    skipped: dict = {}
    files, vendored = base.collect_files(root, cfg, lang_cfg["extensions"], scope, skipped)
    rels_all = [p.resolve().relative_to(root).as_posix() for p in files]

    if not rels_all:
        # `.rs` が1つも無いなら tree-sitter-rust を要求しない(Rust を含まないプロジェクトの
        # venv が古いだけで build-callgraphs が止まらないようにする)
        return base.sort_lang_result({
            "tier": 2, "extractor": "tree-sitter-rust", "external_call_count": 0,
            "symbols": [], "edges": [], "endpoints": [], "unresolved": [],
            "vendored_dirs": vendored, "skipped_files": skipped,
        }) | {"resource_refs": []}

    parser = _load_parser()
    _IDENT_CACHE.clear()                              # ノードの id は木ごとに振られるので持ち越さない
    targets = _discover_targets(root, rels_all)
    crate_dirs = {t.crate_dir for t in targets}

    # クレート直下の examples/ benches/ と build.rs は配布物の入口ではない
    rels: list[str] = []
    path_of: dict[str, Path] = {}
    for p, rel in zip(files, rels_all):
        tooling = False
        for d in crate_dirs:
            pre = f"{d}/" if d else ""
            if rel.startswith(pre):
                tail = rel[len(pre):]
                if tail == "build.rs" or tail.startswith(("examples/", "benches/")):
                    tooling = True
        if tooling:
            skipped.setdefault("tooling", []).append(rel)
            continue
        rels.append(rel)
        path_of[rel] = p

    trees: dict[str, tuple] = {}
    unresolved: list[dict] = []
    for rel in rels:
        src = path_of[rel].read_bytes()
        try:
            trees[rel] = (src, parser.parse(src))
        except Exception as exc:                     # pragma: no cover
            unresolved.append({"from": base.symbol_id(rel, "<file>"),
                               "expression": f"<解析失敗: {exc}>"[:120], "reason": "dynamic"})

    w = _World()
    files_set = set(trees)
    assigned: set[str] = set()
    # 根から `mod x;` を辿ってファイルをモジュールの木に載せる
    for tg in targets:
        if tg.root_rel not in trees:
            continue
        rkey = (tg.tid, ())
        w.roots[tg.tid] = rkey
        if tg.kind == "lib":
            w.libs.setdefault(tg.lib_name, rkey)
    for tg in targets:
        if tg.root_rel not in trees:
            continue
        rkey = (tg.tid, ())
        rootmod = w.mods.setdefault(rkey, _Mod(rkey, tg.root_rel, None))
        pending = [(tg.root_rel, rootmod, tg)]
        while pending:
            rel, mod, target = pending.pop()
            if (rel, mod.key) in assigned or rel not in trees:
                continue
            assigned.add((rel, mod.key))
            assigned.add(rel)
            src, tree = trees[rel]
            is_root = rel == target.root_rel
            _collect_items(w, rel, src, tree.root_node, mod, "", _child_dir(rel, is_root),
                           files_set, trees, target, pending)
    # 木から外れたファイル(Cargo.toml が無い・どの `mod` にも宣言されていない)は単独で読む
    orphans = sorted(r for r in trees if r not in assigned)
    for rel in orphans:
        key = (f"{rel}#file", ())
        mod = _Mod(key, rel, None)
        w.mods[key] = mod
        src, tree = trees[rel]
        _collect_items(w, rel, src, tree.root_node, mod, "", _child_dir(rel, True),
                       files_set, trees, None, [])

    rv = _Resolver(w)
    _finish_impls(w, rv)
    for rel, n in sorted(w.test_items.items()):
        skipped.setdefault("tests", []).append(f"{rel}#cfg(test) {n} 項目")

    consts: dict[str, str] = {}
    dup: set[str] = set()
    for key in sorted(w.mods):
        for name, val in w.mods[key].consts.items():
            if name in consts and consts[name] != val:
                dup.add(name)
            consts.setdefault(name, val)
    for name in dup:                                  # 同名で値の違う定数は名前だけでは引けない
        consts.pop(name, None)

    rcfg = res.cfg_of(cfg)
    builder_kind = {_snake(k): v for k, v in rcfg["kind_by_kwarg"].items()}
    edges: list[dict] = []
    endpoints: list[dict] = []
    http_calls: list[tuple] = []
    resource_refs: list[dict] = []
    external = 0

    # 経路の材料(接頭辞は関数をまたいで合成するので、全関数を見てから組み立てる)
    route_sites: list[tuple] = []                     # (unit sid, 局所の接頭辞, method, path, handler, source)
    attr_handlers: dict[str, list[tuple[str, str]]] = {}
    registrations: dict[str, list[tuple[str, list[str]]]] = {}   # 属性ハンドラ sid → [(登録した関数, 局所の接頭辞)]
    fn_refs: dict[str, list[tuple[str, list[str]]]] = {}         # 関数 sid → [(参照した関数, 局所の接頭辞)]

    for u in sorted(w.units, key=lambda x: x.sid):
        sc = _build_scope(u, rv)
        src = u.src
        body = _f(u.node, "body")
        ar = _attr_routes(src, u.attrs)
        if ar:
            attr_handlers[u.sid] = ar
        calls: list = []
        _find(body, {"call_expression"}, calls)
        for call in calls:
            target, unres, is_ext = _resolve_call(call, src, u, rv, sc)
            if target and target != u.sid:
                edges.append({"from": u.sid, "to": target})
                fn_refs.setdefault(target, []).append((u.sid, _local_prefixes(call, src, sc)))
            elif unres:
                f = _f(call, "function")
                rec = {"from": u.sid, "expression": " ".join(_txt(src, f).split())[:100]
                       if f is not None else "<式>", "reason": unres["reason"]}
                if unres.get("candidates"):
                    rec["candidates"] = unres["candidates"]
                unresolved.append(rec)
            elif is_ext:
                external += 1

            name, recv = _call_name(src, call)
            args = _args(call)
            # 関数を値として渡す参照(`get(h)` / `service_fn(handler)` / `.configure(cfg)`)も辺にする。
            # 呼び出しではないが、そこから先へ制御が渡るのは確かで、落とすとハンドラが全部
            # 「どこからも到達しない」に化ける
            for a in args:
                if a.type not in {"identifier", "scoped_identifier"}:
                    continue
                segs = _segments(src, a)
                if not segs or (len(segs) == 1 and sc.bound(segs[0], a.start_byte)):
                    continue
                got = rv.resolve(u.mod.key, segs, u.self_type)
                ref = got[1] if got and got[0] == "fn" else None
                if ref is None and got and got[0] == "member":
                    ref = rv.method(got[1], got[2])[0]
                if ref and ref != u.sid:
                    edges.append({"from": u.sid, "to": ref})
                    lp = _local_prefixes(a, src, sc)
                    if name in {"service", "configure"} and recv is not None:
                        registrations.setdefault(ref, []).append((u.sid, lp))
                    fn_refs.setdefault(ref, []).append((u.sid, lp))

            # axum: .route("/p", get(h)) / actix: .route("/p", web::get().to(h))
            if name == "route" and recv is not None and len(args) >= 2:
                path = _str_lit(src, args[0])
                if path is not None and path.startswith("/"):
                    sp = _scope_prefix(src, call) or ""
                    lp = _local_prefixes(call, src, sc)
                    for meth, h in _method_router(src, args[1], u, rv, sc) or [("ANY", "")]:
                        route_sites.append((u.sid, [base.join_paths(x, sp) for x in lp],
                                            meth, path, h, f".route({path!r})"))
            # actix: web::resource("/p").route(web::get().to(h)) / .to(h)
            if name in {"resource"} and recv is None and args:
                path = _str_lit(src, args[0])
                if path is not None and path.startswith("/"):
                    lp = _local_prefixes(call, src, sc)
                    got_any = False
                    cur = call
                    while cur.parent is not None and cur.parent.type == "field_expression" \
                            and cur.parent.parent is not None \
                            and cur.parent.parent.type == "call_expression":
                        cur = cur.parent.parent
                        cname, _r = _call_name(src, cur)
                        cargs = _args(cur)
                        if cname == "route" and cargs:
                            for meth, h in _method_router(src, cargs[0], u, rv, sc):
                                route_sites.append((u.sid, lp, meth, path, h,
                                                    f"web::resource({path!r})"))
                                got_any = True
                        elif cname in {"to", "to_async"} and cargs:
                            route_sites.append((u.sid, lp, "ANY", path,
                                                _handler_of(cargs[0], src, u, rv, sc),
                                                f"web::resource({path!r})"))
                            got_any = True
                    if not got_any:
                        route_sites.append((u.sid, lp, "ANY", path, "", f"web::resource({path!r})"))
            # rocket: .mount("/p", routes![a, b])
            if name == "mount" and recv is not None and len(args) >= 2 \
                    and args[1].type == "macro_invocation":
                pre = _str_lit(src, args[0]) or ""
                lp = [base.join_paths(x, pre) for x in _local_prefixes(call, src, sc)]
                tt = next((c for c in args[1].children if c.type == "token_tree"), None)
                for segs, _self, _at in (_macro_paths(tt, src) if tt is not None else []):
                    got = rv.resolve(u.mod.key, segs, u.self_type)
                    if got and got[0] == "fn":
                        registrations.setdefault(got[1], []).append((u.sid, lp))
                        edges.append({"from": u.sid, "to": got[1]})

            # HTTP クライアント(境界の候補)
            low = name.lower()
            if recv is not None and low in HTTP_CLIENT_METHODS:
                rtxt = _txt(src, recv).lower()
                if any(h in rtxt for h in HTTP_CLIENT_HINTS) and args:
                    urlnode = args[1] if low == "request" and len(args) >= 2 else args[0]
                    url = _str_lit(src, urlnode)
                    meth = low.upper() if low != "request" else "ANY"
                    if url is None or url.startswith(("/", "http")):
                        http_calls.append((u.sid, meth, url, f"{_txt(src, recv)[:40]}.{name}"))
            elif recv is None and low in HTTP_CLIENT_METHODS:
                segs = _segments(src, _f(call, "function")) or []
                if segs[:1] == ["reqwest"] and args:
                    url = _str_lit(src, args[0])
                    http_calls.append((u.sid, low.upper(), url, "::".join(segs)))

            # 資源: 環境変数 / AWS SDK の builder(`.table_name("users")`)
            if rcfg["enabled"]:
                segs = _segments(src, _f(call, "function")) or []
                if recv is None and segs and segs[-1] in ENV_FUNCS and \
                        "::".join(segs[:-1]) in ENV_MODULES and args:
                    var = _str_lit(src, args[0])
                    if var:
                        resource_refs.append(res.make_ref(u.sid, "env", f"${var}", "read",
                                                          "確実", f"{'::'.join(segs)}(\"{var}\")"))
                if recv is not None and name in builder_kind and args:
                    nm = res.norm_name(_res_parts(args[0], src, consts))
                    op = ""
                    r = recv
                    while r is not None and r.type == "call_expression":
                        op_name, r2 = _call_name(src, r)
                        if r2 is None or r2.type != "call_expression":
                            op = op_name
                            break
                        r = r2
                    if nm:
                        resource_refs.append(res.make_ref(
                            u.sid, builder_kind[name], nm, res.access_of(op), "確実",
                            f"{op}().{name}({_txt(src, args[0])[:40]})"))

        # マクロの中のパスの形の呼び出し(字句で拾う)
        macros: list = []
        _find(body, {"macro_invocation"}, macros)
        for mac in macros:
            tt = next((c for c in mac.children if c.type == "token_tree"), None)
            if tt is None:
                continue
            for segs, via_self, at in _macro_calls(tt, src):
                if via_self:
                    if u.self_type is None:
                        continue
                    hit, _c = rv.method(u.self_type, segs[0])
                    if hit and hit != u.sid:
                        edges.append({"from": u.sid, "to": hit})
                    continue
                if len(segs) == 1 and sc.bound(segs[0], at):
                    continue
                got = rv.resolve(u.mod.key, segs, u.self_type)
                ref = got[1] if got and got[0] == "fn" else None
                if ref is None and got and got[0] == "member":
                    ref = rv.method(got[1], got[2])[0]
                if ref and ref != u.sid:
                    edges.append({"from": u.sid, "to": ref})

    # 関数をまたいだ接頭辞: F の経路は、F を参照した関数 G の接頭辞 + その場の接頭辞の下に在る
    memo: dict[str, list[str]] = {}

    busy: set[str] = set()

    def prefixes(sid: str) -> list[str]:
        """呼び出し元を遡って接頭辞を集める。**結果は関数ごとに1度だけ求めて覚える** —
        覚えないと、呼び出しの階層が深い実プロジェクトで遡りが指数的に膨らむ(2026-10-31 に実測)。
        循環(相互再帰)は、遡り中の関数を「接頭辞なし」として打ち切る。"""
        if sid in memo:
            return memo[sid]
        sites = [s for s in fn_refs.get(sid, []) if s[0] != sid]
        if not sites:
            memo[sid] = [""]
            return memo[sid]
        busy.add(sid)
        out: set[str] = set()
        for g, lps in sites:
            gps = [""] if g in busy else prefixes(g)
            for gp in gps:
                for lp in lps:
                    out.add(base.join_paths(gp, lp) if (gp or lp) else "")
        busy.discard(sid)
        memo[sid] = sorted(out)[:PREFIX_LIMIT] or [""]
        return memo[sid]

    def add_ep(meth: str, path: str, handler: str, source: str) -> None:
        pat = base.normalize_path_pattern(path)
        endpoints.append({
            "id": base.endpoint_id(meth, pat), "protocol": "rest", "method": meth,
            "path_pattern": pat, "path_key": base.path_key(pat),
            "handler": handler, "source": source,
        })

    for sid, lps, meth, path, h, source in route_sites:
        for gp in prefixes(sid):
            for lp in lps:
                add_ep(meth, base.join_paths(gp, lp, path), h, source)

    for hsid, routes in sorted(attr_handlers.items()):
        regs = registrations.get(hsid, [])
        pres: set[str] = set()
        for g, lps in regs:
            for gp in prefixes(g):
                for lp in lps:
                    pres.add(base.join_paths(gp, lp) if (gp or lp) else "")
        for meth, path in routes:
            for pre in sorted(pres) or [""]:
                add_ep(meth, base.join_paths(pre, path), hsid, f"#[{meth.lower()}({path!r})]")

    # バイナリの入口(`fn main`)。Go の `package main` と同じく protocol は `main`
    # (種別を主張しない。理由は go_treesitter.py の同じ箇所)
    for tg in targets:
        if tg.kind != "bin" or tg.tid not in w.roots:
            continue
        sid = w.mods[w.roots[tg.tid]].fns.get("main")
        if sid is None:
            continue
        endpoints.append({
            "id": f"dispatch main @ {sid}", "protocol": "main",
            "path_pattern": base.normalize_path_pattern(tg.root_rel),
            "path_key": base.path_key(tg.root_rel), "handler": sid, "source": tg.root_rel,
        })

    for frm, _m, url, expr in http_calls:
        if url is None:
            unresolved.append({"from": frm, "expression": f"{expr}(<非リテラルURL>)",
                               "reason": "boundary"})

    out = base.sort_lang_result({
        "tier": 2,
        "extractor": "tree-sitter-rust",
        "external_call_count": external,
        "symbols": w.symbols,
        "edges": edges,
        "endpoints": endpoints,
        "unresolved": unresolved,
        "vendored_dirs": vendored,
        "skipped_files": skipped,
    })
    out["http_calls"] = sorted({(f, m, u, e) for f, m, u, e in http_calls if u})
    out["resource_refs"] = res.sort_refs(resource_refs)
    return out


def _macro_paths(tt, src: bytes) -> list[tuple[list[str], bool, int]]:
    """`routes![a, m::b]` の中のパスを並べる(呼び出しの括弧を要求しない版)。"""
    out = []
    cur: list[str] = []
    start = 0
    for c in tt.children:
        if c.type in {"identifier", "self", "super", "crate"}:
            if not cur:
                start = c.start_byte
            cur.append(_txt(src, c))
        elif c.type == "::":
            continue
        else:
            if cur:
                out.append((cur, False, start))
            cur = []
    if cur:
        out.append((cur, False, start))
    return out
