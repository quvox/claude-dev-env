"""Go 抽出器 (Tier 2) — tree-sitter による構文解析 + パッケージ単位の名前解決。

規範: .claude/directions/callgraphs.md / 契約: callgraph-schema.json

Go は Python より名前解決が有利である:
  ・**未修飾の呼び出しは同一パッケージ内で必ず解決する**(パッケージスコープ)。
  ・`pkg.Func()` の `pkg` は import 宣言で一意に決まる。
  ・メソッドのレシーバ型が構文から分かる。
したがって Tier2 でも実用的な精度が出る。それでも解けないもの(インターフェース越しの呼び出し、
無名関数の引き回し)は**未解決として全件残す**(directions §5.5)。

ルート抽出は net/http.ServeMux / chi / gin / echo / gorilla mux に対応する。**プレフィックスの合成は必須**で、
`r.Route("/v1", func(r chi.Router){...})` や `v1 := r.Group("/v1")` を辿らないと、
ALB や API Gateway のパス転送設定と突き合わせられない(design §2.3)。
"""

from __future__ import annotations

import re
from fnmatch import fnmatch
from pathlib import Path

from . import base
from . import resources as res

# HTTP メソッドとしてルートを定義する呼び出し(chi は Get/Post、gin/echo は GET/POST)
ROUTE_METHODS = {
    "get": "GET", "post": "POST", "put": "PUT", "patch": "PATCH", "delete": "DELETE",
    "head": "HEAD", "options": "OPTIONS", "connect": "CONNECT", "trace": "TRACE",
    "any": "ANY", "handle": "ANY", "handlefunc": "ANY", "method": "ANY",
}
# Go 1.22 以降の `net/http.ServeMux` は、登録の文字列そのものに
# `[METHOD ][HOST]/[PATH]` を取る(`mux.HandleFunc("GET /ws", h)`)。分解しないと
# メソッドが経路の中に残り(`ANY /GET /ws`)、契約側の `GET /ws` と1件も突き合わない。
# メソッドは標準の9種に限らない(WebDAV の `PROPFIND`、UPnP の `M-SEARCH` …)。
# 綴りの許しは Go 側の検査(`validMethod` = RFC 7230 の token)に合わせるが、
# **大文字で始まるものだけを取る**: 要求のメソッドとの比較は大小を区別するので、
# 小文字で登録された経路はそもそも1件も当たらず、そこまで緩めると得るものが無いまま
# 普通の文字列を誤って分解する側にだけ倒れる。
# Go で**字句スコープを作る**ノード。ここへ降りるときは、名前の遮蔽が外へ漏れないように
# 束縛の集合を複製する。`block` は素の `{ }` と関数本体・関数リテラルの本体、残りは
# 初期化文が自分の中だけに効く文である(`if x := f(); …` の `x` は if の外に無い)。
SCOPE_NODES = {
    "block", "if_statement", "for_statement", "select_statement",
    "expression_switch_statement", "type_switch_statement",
    "expression_case", "type_case", "default_case", "communication_case",
}

# 登録の第1引数からメソッドを取る。**大文字のものだけをメソッドと見る。**
#
# ★ ここは Go の文法より**狭い**。Go の `validMethod` は `isToken`(RFC 7230 の token)なので
# `mux.HandleFunc("get /x", h)` も合法であり、メソッド `get` の経路になる。それでも小文字を
# 取らないのは、**この抽出器の下流が全言語一律でメソッドを大文字へ正規化する**からである
# (`cgx/base.py` の `endpoint_id` / `endpoint_key`、および `cgx/boundaries.py` の突き合わせ)。
# `get` を取ると id は `GET /x` になり、**実在しない `GET /x` へ呼び出し側が繋がる偽の辺**を
# 生む。かといって `ANY` にしても同じで、`cgx/boundaries.py` は完全一致が無いと `ANY` へ
# 落ちるので、本物の `GET /x` の規則を吸い込む(2026-09-01 に実測)。
# **だから小文字のメソッドは経路を作らずに落とす**(`_split_servemux_pattern` の「落とす」)。
# **直すなら正規化の側であり、そこは全言語・全生成物に及ぶのでここではない。**
METHOD_UPPER_RE = re.compile(r"^([A-Z][-A-Z0-9!#$%&'*+.^_`|~]*)[ \t]+(.*)$")

# 入れ子でプレフィックスを足すもの
PREFIX_CALLS = {"route", "mount", "group", "with", "handle"}
ROUTER_FACTORIES = {"NewRouter", "New", "Default", "NewServeMux", "NewRoute"}
# ルータを返すパッケージ。`store.New()` を「ルータ生成」と誤解しないための絞り込み
ROUTER_PKGS = {"chi", "gin", "echo", "mux", "httprouter", "http", "fiber"}
# 型名がこれらを含むならルータとみなす(chi.Router / gin.Engine / gin.RouterGroup / echo.Echo …)
ROUTER_TYPE_HINTS = ("router", "mux", "engine", "echo", "servemux")

# 受け手の型が分からないときに内部シンボルと照合しない名前(標準ライブラリの常用メソッド)。
# Python 版と同じ理由 — 同名衝突で偽の ambiguous を量産するのを防ぐ(directions §5.6)。
STDLIB_METHODS = {
    "Error", "String", "Write", "WriteString", "WriteHeader", "Read", "Close", "Flush",
    "Done", "Err", "Value", "Deadline", "Context", "Header", "Bytes", "Len", "Cap",
    "Lock", "Unlock", "RLock", "RUnlock", "Wait", "Add", "Sub", "Now", "Format", "Parse",
    "Scan", "Next", "Sprintf", "Printf", "Println", "Fatal", "Fatalf", "Sprint",
    "Marshal", "Unmarshal", "Encode", "Decode", "Set", "Get", "Del", "Exec", "Query",
    "Begin", "Commit", "Rollback", "Seek", "Copy", "Equal", "Contains", "Split", "Join",
    "TrimSpace", "ToLower", "ToUpper", "Unix", "UnixNano", "Before", "After", "Since",
}


# --------------------------------------------------------------------------- 準備

def _load_parser():
    """tree-sitter は版によって API が動くので、適合はここ1箇所に閉じる(design §5 リスク)。"""
    try:
        import tree_sitter_go
        from tree_sitter import Language, Parser
    except ImportError as exc:
        raise RuntimeError(
            f"tree-sitter が無い({exc})。`python3 .claude/scripts/setup-tools.py` で"
            "キット専用 venv に導入すること") from exc
    lang = Language(tree_sitter_go.language())
    try:
        return Parser(lang)
    except TypeError:                                # 古い API
        p = Parser()
        p.set_language(lang)
        return p


def _txt(src: bytes, node) -> str:
    return src[node.start_byte:node.end_byte].decode("utf-8", "replace")


def _field(node, name):
    return node.child_by_field_name(name) if node is not None else None


def _children(node, kind: str):
    return [c for c in node.children if c.type == kind] if node is not None else []


def _find(node, kinds: set[str], out: list) -> None:
    """指定種別のノードを深さ優先で集める(関数リテラルの中にも降りる)。"""
    for c in node.children:
        if c.type in kinds:
            out.append(c)
        _find(c, kinds, out)


def _strip_ptr(t: str) -> str:
    return t.lstrip("*&").split(".")[-1].strip()


def _qualified_type(t: str, fi: "_GoFile") -> str:
    """型の綴りを、**パッケージのパスまで解いた形**にする。`*h.ServeMux` → `net/http.ServeMux`。

    `_strip_ptr` は修飾を捨てるので、そこを通った型では `net/http.ServeMux` と
    `myrouter.ServeMux` を、`ServeMux` と `CustomServeMux` を見分けられない。**見分けが
    必要なところはこちらを使う。** 呼び名は `fi.imports`(ローカル名 → import パス)で解くので、
    `import h "net/http"` のような別名も解ける。**解くのは import が見えているこのファイルの
    中だけ**なので、型を集めた場所で1度だけ解いて持ち回る。
    修飾が無いもの(同じパッケージの型)と、解けなかったものは元の綴りのまま返す。
    """
    t = t.strip().lstrip("*&").strip()
    local, dot, name = t.rpartition(".")
    if not dot:
        return t
    path = fi.imports.get(local)
    return f"{path}.{name}" if path else t


def _unquote(s: str) -> str:
    return s.strip().strip('"').strip("`")


# --------------------------------------------------------------------------- ファイル情報

class _GoFile:
    def __init__(self, rel: str, src: bytes, root_node, pkg_path: str, pkg_name: str):
        self.rel, self.src, self.root = rel, src, root_node
        self.pkg_path, self.pkg_name = pkg_path, pkg_name
        self.imports: dict[str, str] = {}          # ローカル名 → import パス
        # **明示された別名だけ**。書かれているので確実であり、**推測に上書きされてはならない**。
        self.import_alias: dict[str, str] = {}
        # **別名を書いていない import のパスだけ**。既定のローカル名は「パスの末尾」ではなく
        # **被 import 側が宣言したパッケージ名**なので、末尾と違う構成(`.../lib` が
        # `package command` を宣言する)では `imports` の鍵が実際の呼び名と食い違う。
        # 全ファイルを読んだ後でしか直せない(宣言名は向こうのファイルに在る)ので、
        # ここでは候補だけを残し、`_GoResolver.pkg_by_local` が引き直す。
        self.import_noalias: list[str] = []
        # 関数名 → (sid, 戻り型, **修飾を解いた**戻り型)。3つ目は `_qualified_type` 済みで、
        # 「その戻り値は `net/http.ServeMux` か」を後から判るようにするためだけに在る。
        self.funcs: dict[str, tuple] = {}
        self.methods: dict[tuple[str, str], str] = {}   # (型, メソッド) → sid
        self.struct_fields: dict[str, dict[str, str]] = {}  # 型 → {フィールド: 型}
        self.var_types: dict[str, str] = {}        # パッケージ変数 → 型(`_strip_ptr` 済み)
        # 同じ変数 → **修飾を解いた**型(`_qualified_type`)。見分けが要るところはこちらを見る
        self.var_types_q: dict[str, str] = {}
        # 関数値の振り分け表。変数名 → その表に並ぶ関数名
        # (`var handlers = map[string]func(*env) int{"post": cmdPost, …}`)。
        # Go の CLI では定型で、これを解かないと `handlers[x](…)` から先の辺が丸ごと落ち、
        # 実際は到達可能な関数が「到達不能コード」に見える(KIT-go-func-value-dispatch-table)。
        self.dispatch: dict[str, list[str]] = {}


def _module_paths(root: Path) -> list[tuple[str, str]]:
    """(go.mod のあるディレクトリ(repo相対), module パス) を深い順に返す。"""
    out = []
    for gomod in root.rglob("go.mod"):
        rel_dir = gomod.parent.relative_to(root).as_posix()
        # rel_dir == "." はリポジトリ直下(正常)。隠しディレクトリだけを弾く
        if any(part.startswith(".") for part in rel_dir.split("/") if part != ".") \
                or "/vendor/" in f"/{rel_dir}/":
            continue
        for line in gomod.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("module "):
                out.append((rel_dir, line.split(None, 1)[1].strip()))
                break
    return sorted(out, key=lambda kv: -len(kv[0]))


def _pkg_path_of(rel: str, modules: list[tuple[str, str]]) -> str:
    d = rel.rsplit("/", 1)[0] if "/" in rel else ""
    for mod_dir, mod_path in modules:
        base_dir = "" if mod_dir == "." else mod_dir
        if d == base_dir:
            return mod_path
        if base_dir and d.startswith(base_dir + "/"):
            return f"{mod_path}/{d[len(base_dir) + 1:]}"
        if not base_dir:
            return f"{mod_path}/{d}" if d else mod_path
    return d


def _collect_file(rel: str, src: bytes, tree, modules) -> _GoFile:
    root = tree.root_node
    pkg_name = ""
    for c in root.children:
        if c.type == "package_clause":
            for ch in c.children:
                if ch.type == "package_identifier":
                    pkg_name = _txt(src, ch)
    fi = _GoFile(rel, src, root, _pkg_path_of(rel, modules), pkg_name)

    specs: list = []
    _find(root, {"import_spec"}, specs)
    for spec in specs:
        path = _unquote(_txt(src, _field(spec, "path"))) if _field(spec, "path") else ""
        alias_node = _field(spec, "name")
        # `github.com/go-chi/chi/v5` のパッケージ名は v5 ではなく chi(Go のバージョン接尾辞の慣習)
        seg = path.rsplit("/", 1)[-1]
        if re.fullmatch(r"v\d+", seg) and "/" in path:
            seg = path.rsplit("/", 2)[-2]
        local = _txt(src, alias_node) if alias_node else seg
        if path and local not in {"_", "."}:
            fi.imports[local] = path
            if alias_node is None:
                fi.import_noalias.append(path)
            else:
                fi.import_alias[local] = path

    for node in root.children:
        if node.type == "function_declaration":
            name_node = _field(node, "name")
            if not name_node:
                continue
            name = _txt(src, name_node)
            rnode = _field(node, "result")
            raw_rt = _txt(src, rnode) if rnode else ""
            fi.funcs[name] = (base.symbol_id(rel, name),
                              _strip_ptr(raw_rt) if raw_rt else "",
                              _qualified_type(raw_rt, fi) if raw_rt else "")
        elif node.type == "method_declaration":
            recv = _field(node, "receiver")
            name_node = _field(node, "name")
            if not (recv and name_node):
                continue
            rtype = ""
            for decl in _children(recv, "parameter_declaration"):
                tnode = _field(decl, "type")
                if tnode:
                    rtype = _strip_ptr(_txt(src, tnode))
            name = _txt(src, name_node)
            if rtype:
                fi.methods[(rtype, name)] = base.symbol_id(rel, f"{rtype}.{name}")
        elif node.type == "type_declaration":
            for spec in _children(node, "type_spec"):
                tname_node, tnode = _field(spec, "name"), _field(spec, "type")
                if not (tname_node and tnode and tnode.type == "struct_type"):
                    continue
                fields: dict[str, str] = {}
                # struct_type は body フィールドを持たない。実体は field_declaration_list の中。
                flist = next((c for c in tnode.children
                              if c.type == "field_declaration_list"), tnode)
                for fd in _children(flist, "field_declaration"):
                    ftype = _field(fd, "type")
                    if not ftype:
                        continue
                    tv = _strip_ptr(_txt(src, ftype))
                    names = [c for c in fd.children if c.type == "field_identifier"]
                    for n in names:
                        fields[_txt(src, n)] = tv
                fi.struct_fields[_txt(src, tname_node)] = fields
        elif node.type == "var_declaration":
            for spec in _children(node, "var_spec"):
                tnode, nnode = _field(spec, "type"), _field(spec, "name")
                if tnode and nnode:
                    fi.var_types[_txt(src, nnode)] = _strip_ptr(_txt(src, tnode))
                    fi.var_types_q[_txt(src, nnode)] = _qualified_type(_txt(src, tnode), fi)
                if nnode:
                    names = _dispatch_targets(spec, src)
                    if names:
                        fi.dispatch[_txt(src, nnode)] = names
    return fi


def _unwrap_lit(node):
    """`literal_element` の包みを剥がす。

    この文法では複合リテラルの要素は、`keyed_element` の**キーも値も**
    `literal_element` に包まれている(実測: `[('literal_element', '"post"'), (':', ':'),
    ('literal_element', 'cmdPost')]`)。剥がさないと `node.type` での分岐が常に外れる。
    """
    while node is not None and node.type == "literal_element":
        node = node.children[0] if node.children else None
    return node


def _dispatch_targets(spec, src: bytes) -> list[str]:
    """`map[...]func(…)…{…}` / `[]func(…)…{…}` の値の位置に並ぶ**識別子**を返す。

    返すのは名前だけで、シンボルへの解決は `_resolve` が行う(パッケージ解決が要るため)。
    キーが実行時に決まるので、これは**確定辺ではなく候補**である。
    候補は `unresolved.reason=ambiguous` の `candidates` に載せる —
    `cgx/features.py` の `edge_sets()` がそこから確度「候補」の辺を作るからで、
    辺のスキーマには確度の欄が無い(`callgraph-schema.json` の edges は from/to のみ)。
    """
    val = _field(spec, "value")
    if val is None:
        return []
    lits: list = []
    _find(val, {"composite_literal"}, lits)
    out: list[str] = []
    for lit in lits:
        tnode = _field(lit, "type")
        if tnode is None or "func(" not in _txt(src, tnode).replace(" ", ""):
            continue                          # 関数値のコンテナだけを対象にする
        body = _field(lit, "body") or lit
        for el in body.children:
            if el.type == "keyed_element":    # map: "post": cmdPost
                cand = _field(el, "value")
                if cand is None:
                    kids = [c for c in el.children if c.type not in {":", ","}]
                    cand = kids[1] if len(kids) >= 2 else None
            elif el.type == "literal_element":  # slice: []func(){fn, …}
                cand = el
            else:
                continue
            cand = _unwrap_lit(cand)
            if cand is not None and cand.type == "identifier":
                name = _txt(src, cand)
                if name not in out:
                    out.append(name)
    return out


# --------------------------------------------------------------------------- 解決

class _GoResolver:
    def __init__(self, files: dict[str, _GoFile]):
        self.files = files
        self.pkg_funcs: dict[str, dict[str, tuple]] = {}
        self.pkg_methods: dict[str, dict[tuple[str, str], str]] = {}
        self.pkg_fields: dict[str, dict[str, dict[str, str]]] = {}
        # **単純名の索きにはメソッドだけを入れる。パッケージ関数は入れない。** ★
        # この索きが引かれるのは `x.Name()` の形(セレクタ)で、受け手の型が分からなかった
        # ときだけである(`_resolve` の 6)。Go の `x.Name` の `Name` は **`x` の型の
        # メソッドかフィールド**であって、パッケージ直下の関数ではない — 関数を呼ぶ
        # 修飾された形 `pkg.Func()` は import 表を持つ 1 の分岐が先に返すからである。
        # ここに関数を混ぜると、**標準ライブラリのメソッド呼び出しが同名のパッケージ関数へ
        # 確度「確定」で解決される**(実測 2026-08-31: `cmd.Run()`(`*exec.Cmd`)が製品の
        # `func Run(...)` へ解決され、その1本から偽の到達辺が111本生えて
        # `callgraph-check.py` CG4 の重大度「高」を埋め、実装整合フローが構造的に green に
        # できなくなった)。**確定辺は棄却で抑止できない**ので、名前だけを根拠にした
        # 確定はここで断つ。
        # **取りこぼしは在る。承知の上の取引である**(規則4 と同じ形 —
        # `directions/callgraphs.md` §5.6): フィールドが関数値を持ち、そこにパッケージ直下の
        # 関数が代入されていることは在る(`table["x"].Run()`)。それは名前の束縛ではなく
        # 値の流れなので、受け手の型が分からないその形からは辺を引かない。
        # 偽の確定辺1本が到達集合を丸ごと汚すのに対し、
        # こちらは静かな偽陰性1本なので、この取引を採る。
        self.simple_methods: dict[str, list[str]] = {}
        for fi in files.values():
            self.pkg_funcs.setdefault(fi.pkg_path, {}).update(fi.funcs)
            self.pkg_methods.setdefault(fi.pkg_path, {}).update(fi.methods)
            self.pkg_fields.setdefault(fi.pkg_path, {}).update(fi.struct_fields)
            for (_t, name), sid in fi.methods.items():
                self.simple_methods.setdefault(name, []).append(sid)
        for k in self.simple_methods:
            self.simple_methods[k].sort()
        self.internal_pkgs = set(self.pkg_funcs) | set(self.pkg_methods)
        # 内部パッケージが**宣言している**名前(`package <名前>`)。import の既定の呼び名は
        # これであって、パスの末尾ではない(`_GoFile.import_noalias`)。
        # **通常のファイルの宣言を先に採る** ★ — 同じディレクトリに `package foo_test` を
        # 宣言する外部テストパッケージが在り、`include_tests: true` でそれがパス順で先に来ると、
        # そのディレクトリの呼び名が `foo_test` として登録され、**`foo.F()` が引けなくなる**
        # (独立検査 2026-09-01)。既定では対象外なので普段は当たらないが、設定1つで当たる。
        # **判定に使うのはファイル名(`_test.go`)であって宣言名ではない** — `_test` で終わる
        # 宣言名は通常のパッケージにも合法に付けられるので、名前で切ると正しい宣言まで落ちる。
        # 通常のファイルが1つも無いパッケージだけ、テストのファイルの宣言で埋める。
        self.pkg_decl_names: dict[str, str] = {}
        for fi in files.values():
            if fi.pkg_name and not fi.rel.endswith("_test.go"):
                self.pkg_decl_names.setdefault(fi.pkg_path, fi.pkg_name)
        for fi in files.values():
            if fi.pkg_name:
                self.pkg_decl_names.setdefault(fi.pkg_path, fi.pkg_name)
        self._alias: dict[str, str | None] = {}

    def resolve_pkg(self, path: str) -> str | None:
        """import パスを内部パッケージのキーに解決する。

        go.mod が読めない/module 名と配置が対応しない場合の保険として、
        **末尾一致**でも引く(`example.com/app/internal/store` → `internal/store`)。
        曖昧なら解決しない(誤った辺を作らない)。
        """
        if path in self._alias:
            return self._alias[path]
        got: str | None = path if path in self.internal_pkgs else None
        if got is None:
            hits = [p for p in self.internal_pkgs if p and (path == p or path.endswith("/" + p))]
            if len(hits) == 1:
                got = hits[0]
            elif len(hits) > 1:
                got = max(hits, key=len) if len({len(h) for h in hits}) == len(hits) else None
        self._alias[path] = got
        return got

    def is_internal_pkg(self, path: str) -> bool:
        return self.resolve_pkg(path) is not None

    def func_in_pkg(self, pkg: str, name: str) -> str | None:
        key = self.resolve_pkg(pkg) or pkg
        hit = self.pkg_funcs.get(key, {}).get(name)
        return hit[0] if hit else None

    def return_type(self, pkg: str, name: str) -> str:
        key = self.resolve_pkg(pkg) or pkg
        hit = self.pkg_funcs.get(key, {}).get(name)
        return hit[1] if hit else ""

    def return_type_q(self, pkg: str, name: str) -> str:
        """戻り型を**修飾を解いた形**で返す(`_qualified_type`)。解いたのは宣言した側の
        ファイルなので、呼ぶ側の import が違っていても `net/http.ServeMux` と判る。"""
        key = self.resolve_pkg(pkg) or pkg
        hit = self.pkg_funcs.get(key, {}).get(name)
        return hit[2] if hit and len(hit) > 2 else ""

    def method(self, pkg: str, typ: str, name: str) -> str | None:
        key = self.resolve_pkg(pkg) or pkg
        return self.pkg_methods.get(key, {}).get((typ, name))

    def field_type(self, pkg: str, typ: str, field: str) -> str:
        key = self.resolve_pkg(pkg) or pkg
        return self.pkg_fields.get(key, {}).get(typ, {}).get(field, "")

    def pkg_by_local(self, fi: "_GoFile", local: str) -> str | None:
        """呼び名 `local` が指している import パスを引き直す。

        `fi.imports` の鍵はパスの末尾なので、**宣言されたパッケージ名が末尾と違う**構成では
        引けない。そこを引き直さないと `command.Run()` が「import 由来」と見なされず、
        最後の手段の索きへ落ちる(そこは関数を候補にしないので、**正しい辺が消える**)。
        **別名の書かれた import は見ない** — 別名が書かれていれば呼び名はそれで確定している。
        """
        for path in fi.import_noalias:
            key = self.resolve_pkg(path)
            if key is not None and self.pkg_decl_names.get(key) == local:
                return path
        return None

    def import_of(self, fi: "_GoFile", local: str) -> str | None:
        """呼び名 `local` が指している import パス。**確かなものから順に見る。**

        `fi.imports` の鍵は**パスの末尾からの推測**なので、いちばん弱い。先に見ると、
        別名で束縛された呼び名や、宣言名で束縛された呼び名を推測が上書きする —
        `m/a` が `package bar` を、`m/bar` が `package baz` を宣言していると、
        `bar.F()` の行き先は `m/a` なのに `m/bar` を返す(独立検査 2026-09-01 の実測)。
        """
        got = fi.import_alias.get(local)      # 1. 明示された別名。書かれているので確実
        if got:
            return got
        got = self.pkg_by_local(fi, local)    # 2. 内部パッケージが宣言している名前
        if got:
            return got
        return fi.imports.get(local)          # 3. パスの末尾からの推測(外部は宣言名を読めない)

    def by_simple_method(self, name: str) -> tuple[str | None, list[str]]:
        """メソッド名だけで索く(セレクタの呼び出しの最後の手段)。

        **パッケージ関数は候補にもしない** — 理由は `__init__` の `simple_methods`。
        """
        hits = self.simple_methods.get(name, [])
        return (hits[0], []) if len(hits) == 1 else (None, hits)


def _method_across(rv: "_GoResolver", from_pkg: str, typ: str,
                   name: str) -> tuple[str | None, list[str]]:
    """型名 `typ` のメソッド `name` を、呼び出し元のパッケージ→内部パッケージ全体の順に探す。

    **合致が2つ以上のパッケージに在るときは確定させない。** `_strip_ptr` は型から
    パッケージ修飾を落とす(`*pkg.T` → `T`)ので、同じ型名と同じメソッド名を持つ
    パッケージが2つ在ると、内部パッケージを整列順に舐める探索は**辞書順で先に来たほうを
    確定辺として立てる** — 型の根拠は1つも無いのに、である。
    **確定辺は棄却で抑止できない**(`callgraph-check.py` CG4 は確度「候補」の辺だけを
    棄却記録で抑止する)ので、こうして立った偽の辺は重大度「高」のまま残り続け、
    実装整合フローを構造的に green にできなくする。

    返り値は (確定した symbol_id, 候補一覧)。合致が1つのパッケージだけなら確定させ、
    2つ以上なら候補一覧を返す — 呼び出し側はそれを `unresolved`(`reason: "ambiguous"`)
    へ回す。候補として出た辺は確度が「候補」になるので、棄却でき、CG4 の重大度も「中」に
    なる。**候補を捨てて1つに決めることはしない。**

    **呼び出し元のパッケージに合致が在れば、そこで確定させる。** ★ 曖昧さを数えるのは
    その先だけである — Go では修飾の無い型名(`var s Service`)は**定義上その場の
    パッケージの型**なので、同じ名前の型が他のパッケージに在ることは根拠を1つも揺るがさない。
    ここを合致の数だけで判定すると、**これまで正しく確定できていた辺まで候補へ落ち**、
    経路のハンドラも特定できなくなって、このヘルパが直そうとしたのと同じ
    「構造的に green にできない」状態を別の口から作る(独立検査 2026-08-25 の実測)。

    **この優先は、修飾されていた型にも掛かってしまう。** ★ `_strip_ptr` は
    `*other.Service` を `Service` にするので、**修飾が在ったかどうかは、ここへ届いていない**。
    だから呼び出し元のパッケージが同名の型と同名のメソッドを持っていると、`other.Service` の
    呼び出しでも呼び出し元のほうへ確定辺が立つ — 上の「定義上その場のパッケージの型」は、
    修飾の無い型にしか成り立たない主張である。**これはこの手当てが持ち込んだものではなく、
    `_strip_ptr` が修飾を捨てていることから来る先在の誤り**(手当ての前も同じ辺を立てていた。
    2026-08-25 に実測)であり、根治は `_method_across` ではなく型の集め方の側に在る —
    修飾を `sc.vars` / `fi.var_types` / `fi.struct_fields` まで運び、修飾が在るときは
    このヘルパを通さずそのパッケージだけを引く形にする。
    """
    own = rv.method(from_pkg, typ, name)
    if own:
        return own, []
    hits: list[str] = []
    for pkg in sorted(rv.internal_pkgs):
        if pkg == from_pkg:
            continue
        got = rv.method(pkg, typ, name)
        if got and got not in hits:
            hits.append(got)
    if len(hits) == 1:
        return hits[0], []
    return None, hits


class _Scope:
    """1つの関数・メソッドの解決文脈。"""
    def __init__(self, fi: _GoFile, rv: _GoResolver, recv: tuple[str, str] | None):
        self.fi, self.rv = fi, rv
        self.recv = recv                    # (レシーバ変数名, 型)
        self.vars: dict[str, str] = {}      # ローカル変数 → 型(`_strip_ptr` 済み)
        # 同じ変数 → **修飾を解いた**型(`_GoFile.var_types_q` と同じ理由)
        self.vars_q: dict[str, str] = {}
        self.params: set[str] = set()


def _infer_type(node, src: bytes, sc: _Scope) -> str:
    """右辺の式から型名を推定する。分からなければ空文字。"""
    if node is None:
        return ""
    if node.type == "unary_expression":
        return _infer_type(_field(node, "operand"), src, sc)
    if node.type == "composite_literal":
        t = _field(node, "type")
        return _strip_ptr(_txt(src, t)) if t else ""
    if node.type == "call_expression":
        fn = _field(node, "function")
        if fn is None:
            return ""
        if fn.type == "identifier":
            return sc.rv.return_type(sc.fi.pkg_path, _txt(src, fn))
        if fn.type == "selector_expression":
            op, fld = _field(fn, "operand"), _field(fn, "field")
            if op is not None and op.type == "identifier" and fld is not None:
                oname = _txt(src, op)
                # ここも `_resolve` と同じ順序である。**覆いの判定も同じく先に置く** —
                # 落とすと、同じ綴りのローカル変数を通した生成が import 先の
                # コンストラクタと見なされ、偽の確定辺になる。
                pkg = (None if _shadows_import(oname, sc)
                       else sc.rv.import_of(sc.fi, oname))
                if pkg and sc.rv.is_internal_pkg(pkg):
                    return sc.rv.return_type(pkg, _txt(src, fld))
        return ""
    if node.type == "identifier":
        return sc.vars.get(_txt(src, node), "")
    return ""


def _collect_locals(body, src: bytes, sc: _Scope) -> None:
    decls: list = []
    _find(body, {"short_var_declaration", "var_spec", "assignment_statement"}, decls)
    for d in decls:
        left, right = _field(d, "left"), _field(d, "right")
        spec_lefts = None
        if d.type == "var_spec":
            tnode, nnode = _field(d, "type"), _field(d, "name")
            if tnode and nnode:
                # **`var a, b *T` は `_field` では先頭しか取れない。** 直下の識別子すべてに
                # 同じ型を付ける — 付け漏らすと2つ目以降が `_is_router_var` を通らず、
                # その名前で登録した経路が丸ごと消える(2026-09-01 に実測)。
                for c in [x for x in d.children if x.type == "identifier"] or [nnode]:
                    sc.vars[_txt(src, c)] = _strip_ptr(_txt(src, tnode))
                # **ここで `vars_q` へ入れてはならない。** この収集は関数リテラルや内側
                # ブロックの中まで1つの `sc` に平らに集めるので、内側の `var mux *X` が
                # 外側の型を上書きしてしまう(2026-09-01 に実測)。修飾型が要るのは
                # 「その名前は ServeMux か」の判定だけであり、そちらは走査の順に
                # `_walk_routes` が字句スコープ単位で見る。
                continue
            # **`var a, b = x, y` の `name` は繰り返しのフィールド**なので、`_field` では
            # 先頭しか取れない。直下の識別子を全部取る(型は `type_identifier` などの
            # 別ノードなので混ざらない)。先頭だけを見ると、2つ目以降の名前が型を持たず、
            # ルータとしても拾われなくなる(2026-09-01 に実測)。
            spec_lefts = [c for c in d.children if c.type == "identifier"]
            left, right = (spec_lefts[0] if spec_lefts else None), _field(d, "value")
        if left is None or right is None:
            continue
        lefts = spec_lefts if spec_lefts else (
            [c for c in left.children if c.type == "identifier"]
            if left.type == "expression_list"
            else ([left] if left.type == "identifier" else []))
        rights = [c for c in right.children if c.type not in {","}] if right.type == "expression_list" \
            else [right]
        for i, ln in enumerate(lefts):
            rn = rights[i] if i < len(rights) else (rights[0] if len(rights) == 1 else None)
            t = _infer_type(rn, src, sc)
            name = _txt(src, ln)
            if t:
                sc.vars[name] = t
            else:
                # **型が分からなくても名前は載せる** ★ — この表は型の索きであると同時に
                # **`_shadows_import` が見る「この関数で束縛されている名前」の表**でもある。
                # 載せないと、型を推定できない束縛(`q := registry["k"]`)が同じ綴りの import を
                # 覆えず、`q.F()` が import 先のパッケージ関数へ**確度「確定」**で解決される
                # (独立検査 2026-09-01)。**既に型が入っている名前は上書きしない。**
                sc.vars.setdefault(name, "")


def _dispatch_calls(body, src: bytes, sc: _Scope, sid: str) -> list[dict]:
    """関数値の振り分け表からの呼び出し(`handlers[key](args)`)を未解決の候補として返す。

    **`call_expression` として現れない。** tree-sitter-go は `X[Y](Z)` を
    ジェネリック型の実体化と解釈し、`type_conversion_expression`(型は `generic_type`)にする。
    そのため通常の呼び出し走査には1件も出てこず、辺が丸ごと落ちる
    (KIT-go-func-value-dispatch-table。「候補が無い」のではなく「呼び出しに見えていない」)。
    `index_expression` 形で来る場合も同じ扱いにする。
    """
    fi, rv = sc.fi, sc.rv
    if not fi.dispatch:
        return []
    out: list[dict] = []
    nodes: list = []
    _find(body, {"type_conversion_expression", "call_expression"}, nodes)
    for node in nodes:
        tnode = _field(node, "type") or _field(node, "function")
        if tnode is None:
            continue
        if tnode.type == "generic_type":
            base_node = _field(tnode, "type") or next(
                (c for c in tnode.children if c.type in {"type_identifier", "identifier"}), None)
        elif tnode.type == "index_expression":
            base_node = _field(tnode, "operand")
        else:
            continue
        if base_node is None:
            continue
        table = fi.dispatch.get(_txt(src, base_node))
        if not table:
            continue
        cands: list[str] = []
        for nm in table:
            got = rv.func_in_pkg(fi.pkg_path, nm)
            if got and got not in cands:
                cands.append(got)
        if cands:
            out.append({"from": sid, "expression": _txt(src, node)[:100],
                        "reason": "ambiguous", "candidates": cands})
    return out


def _shadows_import(opname: str, sc: _Scope) -> bool:
    """その呼び名が、関数の中の何かに束縛されているか。

    Go では**ローカル変数・引数・レシーバが import の呼び名を覆う**(同じ綴りの import が
    在っても、その関数の中では覆ったほうが正しい)。だから import の表を引くより先に
    ここを見る。パッケージ直下の変数は覆わない — 同じファイルで import と同じ名前を
    宣言することは Go ではできないので、そもそも衝突しない。

    **見えるのは `_collect_locals` が集めた範囲だけである。** 集めるのは短い変数宣言・
    `var` の指定・代入と、いちばん外側の引数とレシーバであり、`range` の変数・型スイッチの
    束縛・クロージャの引数・名前付き戻り値は入っていない。
    **型を推定できなかった束縛もこの表に載る**(空の型で載る。`_collect_locals`)—
    覆いの判定は名前だけを見るので、型が分からないことは覆わない理由にならない。

    **`sc.vars` は関数まるごとの表であって、字句スコープではない**(`_collect_locals` は
    入れ子のブロックにもクロージャにも降りる)。だから内側のブロックだけで宣言された名前も
    関数の外側まで覆い、`if q := NewH(); true { q.F() }` の後ろに在る `q.F()`(こちらは
    import の `q`)の辺が落ちる。**承知の上で採っている**: 覆いを見ないと、同じ綴りの
    ローカル変数を通した呼び出しが import 先の関数へ**確度「確定」**で解決される — 静かな
    偽陰性1本と、到達集合を丸ごと汚す偽の確定辺1本の取引であり、規則5 と同じ向きの選択で
    ある(`directions/callgraphs.md` §5.6)。

    **穴は両向きに残っている。**(a) 表が関数まるごとなので、**覆いすぎて**外側の
    `pkg.F()` を落とす。(b) 集める形が上の範囲だけなので、`range` などで束縛された名前は
    **覆い足りず**、import 先の関数へ確定してしまう。どちらも直す先は `_collect_locals` の
    側であって、このヘルパではない。
    """
    return bool(opname in sc.vars or opname in sc.params
                or (sc.recv and opname == sc.recv[0]))


def _resolve(call, src: bytes, sc: _Scope) -> tuple[str | None, dict | None, bool]:
    """(symbol_id, 未解決レコード, 外部か)。"""
    fn = _field(call, "function")
    if fn is None:
        return None, None, True
    fi, rv = sc.fi, sc.rv
    if fn.type == "index_expression":            # ジェネリクスの実体化 Query[row](...)
        operand = _field(fn, "operand") or fn
        # **関数値の振り分け表からの呼び出し**。どのキーが来るかは静的に決まらないので、
        # 表に並ぶ全関数を候補として返す(確度「候補」)。ここを外すと `handlers[x](…)` は
        # 「別パッケージの関数」と同じ扱い(外部)になり、辺が1本も出ない。
        if operand.type == "identifier":
            table = fi.dispatch.get(_txt(src, operand))
            if table:
                cands = []
                for nm in table:
                    got = rv.func_in_pkg(fi.pkg_path, nm)
                    if got and got not in cands:
                        cands.append(got)
                if cands:
                    return None, {"reason": "ambiguous", "candidates": cands}, False
        fn = operand

    if fn.type == "identifier":
        name = _txt(src, fn)
        if name in sc.params:
            return None, {"reason": "higher-order"}, False
        got = rv.func_in_pkg(fi.pkg_path, name)      # Go は未修飾ならパッケージスコープ
        if got:
            return got, None, False
        return None, None, True                       # 組み込み or 別パッケージのドット import

    if fn.type != "selector_expression":
        if fn.type in {"call_expression", "parenthesized_expression"}:
            return None, {"reason": "higher-order"}, False
        return None, None, True

    op, fld = _field(fn, "operand"), _field(fn, "field")
    if fld is None:
        return None, None, True
    name = _txt(src, fld)

    if op is not None and op.type == "identifier":
        opname = _txt(src, op)
        # 1. import されたパッケージ(**別名 → 宣言名 → 末尾の推測**の順。`import_of`)。
        #    **関数の中で覆われているなら見ない**(`_shadows_import`)
        pkg = None if _shadows_import(opname, sc) else rv.import_of(fi, opname)
        if pkg:
            if not rv.is_internal_pkg(pkg):
                return None, None, True               # 標準ライブラリ・サードパーティ
            got = rv.func_in_pkg(pkg, name)
            return (got, None, False) if got else (None, None, True)
        # 2. レシーバ
        if sc.recv and opname == sc.recv[0]:
            got = rv.method(fi.pkg_path, sc.recv[1], name)
            if got:
                return got, None, False
            ftype = rv.field_type(fi.pkg_path, sc.recv[1], name)
            if ftype:
                return None, None, True               # フィールドの呼び出しではない
            return None, None, True
        # 3. 型が分かっているローカル変数・パッケージ変数
        vtype = sc.vars.get(opname) or fi.var_types.get(opname)
        if vtype:
            got, cands = _method_across(rv, fi.pkg_path, vtype, name)
            if got:
                return got, None, False
            if cands:                          # 同じ型名が複数のパッケージに在る
                return None, {"reason": "ambiguous", "candidates": cands}, False
            return None, None, True
        if opname in sc.params:
            return None, {"reason": "higher-order"}, False

    # 4. レシーバのフィールド越し(s.repo.Save())
    if op is not None and op.type == "selector_expression":
        inner_op, inner_fld = _field(op, "operand"), _field(op, "field")
        if (inner_op is not None and inner_op.type == "identifier" and inner_fld is not None
                and sc.recv and _txt(src, inner_op) == sc.recv[0]):
            ftype = rv.field_type(fi.pkg_path, sc.recv[1], _txt(src, inner_fld))
            if ftype:
                got, cands = _method_across(rv, fi.pkg_path, ftype, name)
                if got:
                    return got, None, False
                if cands:                      # 同じ型名が複数のパッケージに在る
                    return None, {"reason": "ambiguous", "candidates": cands}, False
                return None, None, True

    # 5. 標準ライブラリの常用メソッド名は照合しない
    if name in STDLIB_METHODS:
        return None, None, True

    # 6. 最後の手段。**メソッド名としてだけ索く**(パッケージ関数へは解決しない。`_GoResolver`)
    got, cands = rv.by_simple_method(name)
    if got:
        return got, None, False
    if cands:
        return None, {"reason": "ambiguous", "candidates": cands}, False
    return None, None, True


# --------------------------------------------------------------------------- ルート

def _split_servemux_pattern(pattern: str,
                            servemux: bool) -> tuple[str | None, str | None]:
    """`"GET /ws"` を `("GET", "/ws")` に分ける。

    返すものは3つの形しかない: 分けられたら `(メソッド, 経路)`、メソッドが無ければ
    `(None, 経路)`、**表せない形なら `(None, None)`**(下の「落とす」)。

    Go 1.22 以降の文法は `[METHOD ][HOST]/[PATH]` で、**METHOD と HOST はそれぞれ独立に
    省略できる**(`net/http/pattern.go` の `parsePattern`)。

    `servemux` は「受け手が `net/http.ServeMux` だと分かっているか」である。**ホストを
    落とすのはそのときだけ**である: chi / gin / echo は入れ子の中で `"users/{id}"` の
    ような相対経路を許すので、受け手を知らないまま最初の `/` の手前を落とすと、
    ホストではなく経路の先頭を削ることになる。

    **メソッドは大文字のものだけを取る**(`METHOD_UPPER_RE` の注記。Go の文法より狭い)。
    受け手が ServeMux だと分かっていて、なお空白で区切られた先頭が大文字でないときは、
    **経路を返さない**(`(None, None)`)。Go の文法ではそれはメソッドであり、この抽出器は
    それを表せないので、**推測で `ANY` の経路を作らずに未解決として落とす** —
    `ANY` にすると `cgx/boundaries.py` の突き合わせが本物の `GET` の規則を吸い込む。
    """
    m = METHOD_UPPER_RE.match(pattern)
    method = m.group(1) if m else None
    rest = m.group(2).lstrip(" \t") if m else pattern
    if method is None and not servemux:
        return None, pattern
    if method is None and servemux:
        # 最初の `/` の手前に空白が在れば、Go の文法ではその手前はメソッドである
        # (`[METHOD ][HOST]/[PATH]`)。大文字でないので上の正規表現が取れなかった。
        head = pattern.split("/", 1)[0]
        if head.strip() and (" " in head or "\t" in head):
            return None, None          # 大文字でないメソッド。表せないので落とす
    if servemux:
        i = rest.find("/")
        # `/` が無いものと、手前に `{` を含むものは Go 自身が不正として撥ねる形である
        # (ホストにパラメータは書けない)。ホストと決めつけずにそのまま返す。
        if i >= 0 and "{" not in rest[:i]:
            rest = rest[i:]
    return method, rest


def _is_net_http_servemux_type(typ: str) -> bool:
    """**修飾を解いた**型名が `net/http.ServeMux` か(`_qualified_type` を通した文字列を渡す)。

    部分一致でも、末尾の名前だけでも判ってはならない。`"servemux" in typ` は
    `CustomServeMux` に当たり、末尾だけを見ると `myrouter.ServeMux` に当たる。当たると
    ホストを落とす側へ倒れ、独自ルータの相対経路(`"tenant/path"`)が `/path` に化ける。
    """
    return typ == "net/http.ServeMux"


def _is_servemux_literal(node, src: bytes, fi: "_GoFile") -> bool:
    """右辺が `&http.ServeMux{}` / `http.ServeMux{}` か。生成器を通さずに作る形である。

    `var x = …` の `value` は式そのものではなく `expression_list` なので、先に開く
    (短変数宣言の側は呼ぶ前に開いている)。
    """
    n = node
    if n is not None and n.type == "expression_list":
        n = n.children[0] if n.children else None
    if n is not None and n.type == "unary_expression":
        n = _field(n, "operand") or n
    if n is None or n.type != "composite_literal":
        return False
    t = _field(n, "type")
    return t is not None and _is_net_http_servemux_type(_qualified_type(_txt(src, t), fi))


def _binds_servemux(node, src: bytes, sc: "_Scope", servemux_vars: set[str]) -> bool:
    """この式は `net/http.ServeMux` を作って返すか。**証明できたときだけ真。**

    覚える形は4つ: **証明済みの名前そのもの**(別名束縛)、複合リテラル(`&http.ServeMux{}`)、
    `net/http` の `NewServeMux()` の呼び(呼び名は `fi.imports` で解くので
    `import h "net/http"` の `h.NewServeMux()` も当たる)、戻り型が `net/http.ServeMux` と
    解けた自前の生成器の呼び。
    """
    n = node
    if n is not None and n.type == "expression_list":
        n = n.children[0] if n.children else None
    if n is not None and n.type == "identifier":
        # **別名束縛。** 既に証明済みの名前をそのまま束ね直しただけなら、証明は移る
        # (`aliasMux := srcMux`)。移さないと別名の側でホストが経路に残る(2026-09-01 に実測)。
        return _txt(src, n) in servemux_vars
    if _is_servemux_literal(n, src, sc.fi):
        return True
    if n is None or n.type != "call_expression":
        return False
    f = _field(n, "function")
    if f is None:
        return False
    if f.type == "selector_expression":
        fld, op = _field(f, "field"), _field(f, "operand")
        if fld is None or _txt(src, fld) != "NewServeMux":
            return False
        if op is None or op.type != "identifier":
            return False
        # **import の表を引く前に、その呼び名が関数の中で覆われていないかを見る**
        # (`_infer_type` と同じ順序)。`http := localFactory{}` のように覆われていれば、
        # `http.NewServeMux()` は `net/http` のものではない(2026-09-01 に実測)。
        opname = _txt(src, op)
        if _shadows_import(opname, sc):
            return False
        return sc.fi.imports.get(opname) == "net/http"
    if f.type == "identifier":
        return _is_net_http_servemux_type(
            sc.rv.return_type_q(sc.fi.pkg_path, _txt(src, f)))
    return False


def _rebind(names: list[str], values: list, src: bytes, sc: "_Scope",
            servemux_vars: set[str]) -> None:
    """左辺の名前と右辺の式を**位置で対応させて**集合を更新する。

    **消すのは無条件、足すのは証明できたときだけ。** 先頭だけを見て左辺全部に配ると、
    `httpMux, customMux := &http.ServeMux{}, &myrouter.ServeMux{}` の後者まで真になる
    (2026-09-01 に実測)。個数が合わないとき(`a, b := f()` のような多値の受け)は
    対応が付かないので、消すに留める。
    """
    paired = values if len(values) == len(names) else []
    # **右辺は先に全部評価する。** Go は右辺を先に評価するので、`a, b = b, a` のような
    # 入れ替えでは、消した名前を右辺が参照することがある。
    hits = [_binds_servemux(v, src, sc, servemux_vars) for v in paired]
    for i, nm in enumerate(names):
        servemux_vars.discard(nm)
        if hits and hits[i]:
            servemux_vars.add(nm)


def _expr_list(node) -> list:
    """`expression_list` の中の式を並びのまま返す(区切りの `,` を落とす)。"""
    if node is None:
        return []
    if node.type != "expression_list":
        return [node]
    return [c for c in node.children if c.type != ","]


def _is_servemux_var(name: str, sc: _Scope, servemux_vars: set[str]) -> bool:   # noqa: ARG001
    """このローカル名は `net/http.ServeMux` か。ホストを落としてよいかがこれで決まる。

    答えは `servemux_vars` だけが持つ。そこに入るのは2つで、**どちらも推測ではなく、
    綴りから `net/http` まで解けたものである**: 宣言された型が `net/http.ServeMux` の名前
    (`_walk_routes` の入口で種にする。`_qualified_type` が `import` の別名まで解いてある)と、
    生成器から辿れた名前。**型の辞書をここで直接引いてはならない** — 引くと内側での
    束縛し直しが遮蔽されず、`mux := chi.NewRouter()` で隠した後も外側の型が返る。
    """
    return name in servemux_vars


def _walk_routes(node, src: bytes, sc: _Scope, var_prefix: dict[str, str],
                 enclosing: str, endpoints: list[dict], unresolved: list[dict],
                 servemux_vars: set[str] | None = None) -> None:
    """net/http.ServeMux / chi / gin / echo のルート定義を、プレフィックスを合成しながら拾う。

    `ServeMux` の登録は文字列そのものに `[METHOD ][HOST]/[PATH]` を取るので、
    `_split_servemux_pattern` が分解する(ホストを落とすのは受け手の型が
    `net/http.ServeMux` だと解けたときだけ)。
    """
    if servemux_vars is None:
        # **入口の種は、この関数の外側で決まっている名前だけ** — パッケージ変数と、
        # この関数の引数である。以降この集合が「その名前は ServeMux か」の唯一の答えで、
        # **内側の束縛し直しはこの集合から消すことで遮蔽される**(下の `discard` と、
        # 字句スコープごとの複製)。**関数の中の `var x *T` を種に混ぜてはならない** —
        # 収集が内側ブロックの中まで平らに見るので、走査を始める前から外側の型を
        # 上書きしてしまう(2026-09-01 に実測)。中の宣言は下の `var_declaration` の枝が
        # 走査の順に反映する。
        servemux_vars = {n for n, t in sc.fi.var_types_q.items()
                         if _is_net_http_servemux_type(t)}
        # **引数は同名のパッケージ変数を遮蔽する。** 和集合にすると、独自型の引数が
        # 同名の `*http.ServeMux` のパッケージ変数を隠しても真のまま残る(2026-09-01 に実測)。
        for n, t in sc.vars_q.items():
            if _is_net_http_servemux_type(t):
                servemux_vars.add(n)
            else:
                servemux_vars.discard(n)
    for child in node.children:
        if child.type == "assignment_statement":
            # `mux = chi.NewRouter()` / `a, b = b, a`。**代入も束縛が変わる場所である。**
            # 左辺が識別子でないもの(`x.f = y`)は名前の束縛ではないので落ちる。
            al, ar = _field(child, "left"), _field(child, "right")
            _rebind([_txt(src, c) for c in al.children if c.type == "identifier"]
                    if al is not None else [], _expr_list(ar), src, sc, servemux_vars)
        if child.type == "var_declaration":
            # `var mux *http.ServeMux` / `var mux *myrouter.ServeMux`。**走査の順に**、
            # いま居る字句スコープの集合へ反映する(足すか、消すか)。
            for spec in _children(child, "var_spec"):
                tnode = _field(spec, "type")
                # **名前は1つとは限らない**(`var a, b *http.ServeMux` / `var a, b = x, y`)。
                # `_field(spec, "name")` は先頭しか返さないので、直下の識別子を全部取る
                # (型は `type_identifier` などの別ノードなので混ざらない)。
                names = [_txt(src, c) for c in spec.children if c.type == "identifier"]
                if not names:
                    continue
                if tnode is not None:
                    # 型を書いた宣言は、並んだ名前すべてがその型である
                    hit = _is_net_http_servemux_type(
                        _qualified_type(_txt(src, tnode), sc.fi))
                    for nm in names:
                        servemux_vars.add(nm) if hit else servemux_vars.discard(nm)
                else:
                    _rebind(names, _expr_list(_field(spec, "value")), src, sc, servemux_vars)
        if child.type == "short_var_declaration":
            left, right = _field(child, "left"), _field(child, "right")
            rn = right.children[0] if right is not None and right.children else right
            # **集合の更新はこの1箇所だけで行う**(下の枝は `var_prefix` だけを触る)。
            # 左辺と右辺を位置で対応させ、消すのは無条件、足すのは証明できたときだけ。
            _rebind([_txt(src, c) for c in left.children if c.type == "identifier"]
                    if left else [], _expr_list(right), src, sc, servemux_vars)
            if rn is not None and rn.type == "call_expression":
                f = _field(rn, "function")
                names = [c for c in left.children if c.type == "identifier"] if left else []
                if f is not None and f.type == "selector_expression":
                    fld = _field(f, "field")
                    op = _field(f, "operand")
                    if fld is not None and _txt(src, fld).lower() == "group" and names:
                        arg = _first_string_arg(rn, src)
                        parent = var_prefix.get(_txt(src, op), "") if op is not None \
                            and op.type == "identifier" else ""
                        var_prefix[_txt(src, names[0])] = base.join_paths(parent, arg or "")
                    elif (fld is not None and _txt(src, fld) in ROUTER_FACTORIES and names
                          and op is not None and op.type == "identifier"
                          and _txt(src, op) in ROUTER_PKGS):
                        var_prefix[_txt(src, names[0])] = ""
                elif f is not None and f.type == "identifier" and names \
                        and _txt(src, f) in ROUTER_FACTORIES:
                    rtype = sc.rv.return_type(sc.fi.pkg_path, _txt(src, f))
                    if any(h in rtype.lower() for h in ROUTER_TYPE_HINTS):
                        var_prefix[_txt(src, names[0])] = ""

        if child.type == "call_expression":
            f = _field(child, "function")
            if f is not None and f.type == "selector_expression":
                op, fld = _field(f, "operand"), _field(f, "field")
                if fld is not None:
                    meth = _txt(src, fld)
                    low = meth.lower()
                    opname = _txt(src, op) if op is not None and op.type == "identifier" else ""
                    if not opname or not _is_router_var(opname, sc, var_prefix):
                        _walk_routes(child, src, sc, var_prefix, enclosing, endpoints,
                                     unresolved, servemux_vars)
                        continue
                    base_pfx = var_prefix.get(opname, "")
                    args = _args(child)
                    if low in PREFIX_CALLS and any(a.type == "func_literal" for a in args):
                        sub = base.join_paths(base_pfx, _first_string_arg(child, src) or "")
                        lit = next(a for a in args if a.type == "func_literal")
                        inner = dict(var_prefix)
                        inner_mux = set(servemux_vars)
                        for pname in _closure_params(lit, src):
                            inner[pname] = sub
                        # **リテラルの引数も外側の名前を遮蔽する。** 複製した集合にも
                        # 反映しないと、`func(mux chi.Router)` が外側の `*http.ServeMux` を
                        # 隠しても真のまま残る(2026-09-01 に実測)。向きは他と同じ —
                        # 消すのは無条件、足すのは `net/http.ServeMux` と解けたときだけ。
                        for pname, ptype in _closure_param_types(lit, src):
                            if _is_net_http_servemux_type(_qualified_type(ptype, sc.fi)):
                                inner_mux.add(pname)
                            else:
                                inner_mux.discard(pname)
                        _walk_routes(_field(lit, "body") or lit, src, sc, inner,
                                     enclosing, endpoints, unresolved, inner_mux)
                        continue
                    if low == "mount":
                        sub = base.join_paths(base_pfx, _first_string_arg(child, src) or "")
                        unresolved.append({
                            "from": enclosing,
                            "expression": f"{_txt(src, op) if op else '?'}.Mount(\"{sub}\", …)",
                            "reason": "dynamic",
                        })
                    elif low in ROUTE_METHODS and args:
                        path = _first_string_arg(child, src)
                        if path is None:
                            unresolved.append({
                                "from": enclosing,
                                "expression": f"{_txt(src, op) if op else '?'}.{meth}(<非リテラル>)",
                                "reason": "dynamic"})
                        else:
                            method = ROUTE_METHODS[low]
                            if method == "ANY":
                                # 呼び名がメソッドを決めていないときだけ文字列を見る。
                                # `r.Get(...)` の側の文字列は経路だけである。
                                found, path = _split_servemux_pattern(
                                    path, _is_servemux_var(opname, sc, servemux_vars))
                                if path is None:
                                    unresolved.append({
                                        "from": enclosing,
                                        "expression": f"{_txt(src, op) if op else '?'}"
                                                      f".{meth}(<大文字でないメソッド>)",
                                        "reason": "dynamic"})
                                    continue
                                if found:
                                    method = found
                            full = base.join_paths(base_pfx, path)
                            handler, hsrc, hcands = _handler_of(args, src, sc, enclosing)
                            if not handler and hcands:
                                unresolved.append({
                                    "from": enclosing,
                                    "expression": f"{_txt(src, op) if op else '?'}.{meth}"
                                                  f"(<ハンドラ>)",
                                    "reason": "ambiguous",
                                    "candidates": hcands})
                            endpoints.append({
                                "id": base.endpoint_id(method, full),
                                "protocol": "rest", "method": method,
                                "path_pattern": base.normalize_path_pattern(full),
                                "path_key": base.path_key(full),
                                "handler": handler,
                                "source": f".{meth}{hsrc}",
                            })
        # **字句スコープへ降りるときは集合を複製する**(`SCOPE_NODES`)。中での束縛し直し
        # (`{ mux := chi.NewRouter() … }`)はそのスコープの中だけの遮蔽であり、同じ集合を
        # 渡すと**スコープを出た後まで遮蔽が残って**外側の `net/http.ServeMux` を見失う
        # (2026-09-01 に実測)。**関数リテラルは引数も遮蔽する**ので、複製したうえで
        # 引数を重ねる(上の `PREFIX_CALLS` の枝は自分で同じことをして `continue` する)。
        if child.type == "func_literal":
            sub_mux = set(servemux_vars)
            for pname, ptype in _closure_param_types(child, src):
                if _is_net_http_servemux_type(_qualified_type(ptype, sc.fi)):
                    sub_mux.add(pname)
                else:
                    sub_mux.discard(pname)
        elif child.type in SCOPE_NODES:
            sub_mux = set(servemux_vars)
        else:
            sub_mux = servemux_vars
        _walk_routes(child, src, sc, var_prefix, enclosing, endpoints, unresolved, sub_mux)


def _is_router_var(name: str, sc: _Scope, var_prefix: dict[str, str]) -> bool:
    """このローカル名はルータか。**これを見ないと `repo.Delete(ctx,id)` を経路と誤検出する。**"""
    if name in var_prefix:
        return True
    typ = (sc.vars.get(name) or sc.fi.var_types.get(name) or "").lower()
    return any(h in typ for h in ROUTER_TYPE_HINTS)


def _args(call) -> list:
    a = _field(call, "arguments")
    return [c for c in a.children if c.type not in {"(", ")", ","}] if a else []


def _first_string_arg(call, src: bytes) -> str | None:
    for a in _args(call):
        if a.type in {"interpreted_string_literal", "raw_string_literal"}:
            return _unquote(_txt(src, a))
    return None


def _closure_param_types(lit, src: bytes) -> list[tuple[str, str]]:
    """関数リテラルの引数を `(名前, 型の綴り)` で返す。型が書かれていなければ空文字。

    `_closure_params` と分けてあるのは、あちらの返り値(名前だけ)を使う側が
    プレフィックスの合成だけを見ているからである。**遮蔽の判定には型が要る。**
    """
    out: list[tuple[str, str]] = []
    plist = _field(lit, "parameters")
    for decl in _children(plist, "parameter_declaration"):
        tnode = _field(decl, "type")
        typ = _txt(src, tnode) if tnode is not None else ""
        for c in decl.children:
            if c.type == "identifier":
                out.append((_txt(src, c), typ))
    return out


def _closure_params(lit, src: bytes) -> list[str]:
    out = []
    plist = _field(lit, "parameters")
    for decl in _children(plist, "parameter_declaration"):
        for c in decl.children:
            if c.type == "identifier":
                out.append(_txt(src, c))
    return out


def _handler_of(args, src: bytes, sc: _Scope, enclosing: str,
                depth: int = 0) -> tuple[str, str, list[str]]:
    """引数からハンドラのシンボルを引く。返り値は (シンボル, 注記, 候補一覧)。

    ミドルウェアで包まれている形(`h.guard(roles, h.delete)` / `mw.Auth(h.Handle)`)が普通なので、
    **呼び出しの中の引数まで辿る**。辿らないと実データでハンドラの3割が未特定になった。

    **候補一覧は、特定できなかった理由が「同名の型が複数のパッケージに在る」ときだけ埋まる。**
    呼び出し側(`_walk_routes`)がそれを未解決の表へ `reason: "ambiguous"` として入れる —
    **解決できなかったものを黙って落とさない**(`callgraphs.md` §5.5)。包んでいる呼び出しの
    中で特定できなかったときも、内側が挙げた候補をそのまま外へ運ぶ。
    """
    pending: list[str] = []                  # 内側・前の引数が挙げた候補(最初の1件を運ぶ)
    for a in args:
        if a.type == "func_literal":
            return enclosing, "(クロージャ)", []
        if a.type == "call_expression" and depth < 3:
            wrapper = _field(a, "function")
            got, _note, cands = _handler_of(_args(a), src, sc, enclosing, depth + 1)
            if got:
                label = _txt(src, wrapper)[:40] if wrapper is not None else "?"
                return got, f"(経由: {label})", []
            if cands and not pending:
                pending = cands
        if a.type == "selector_expression":
            op, fld = _field(a, "operand"), _field(a, "field")
            if op is not None and fld is not None:
                name = _txt(src, fld)
                opname = _txt(src, op) if op.type == "identifier" else ""
                vtype = sc.vars.get(opname) or sc.fi.var_types.get(opname) or ""
                if not vtype and sc.recv and opname == sc.recv[0]:
                    vtype = sc.recv[1]
                if vtype:
                    got, cands = _method_across(sc.rv, sc.fi.pkg_path, vtype, name)
                    if got:
                        return got, "", []
                    if cands:
                        # 合致が複数パッケージに在る。**ここで打ち切る** — 下の import 名の
                        # 照合と単純名の照合へ進むと、ローカル変数が import 名を隠している
                        # ときに同名のパッケージ関数を誤って確定しうる。候補は捨てず、
                        # 呼び出し側が未解決の表へ入れる。
                        return "", "(ハンドラ未特定)", cands
                pkg = (None if _shadows_import(opname, sc)
                       else sc.rv.import_of(sc.fi, opname))
                if pkg and sc.rv.is_internal_pkg(pkg):
                    got = sc.rv.func_in_pkg(pkg, name)
                    if got:
                        return got, "", []
                got, _c = sc.rv.by_simple_method(name)   # セレクタなのでメソッドだけ
                if got:
                    return got, "", []
        if a.type == "identifier":
            got = sc.rv.func_in_pkg(sc.fi.pkg_path, _txt(src, a))
            if got:
                return got, "", []
    return "", "(ハンドラ未特定)", pending


# --------------------------------------------------------------------------- 資源参照(P10)

def _res_consts(fi: _GoFile, rcfg: dict, into: dict) -> None:
    """`TableUsers TableName = "users"` のような**資源名の定数**を集める。

    Go では資源名がリテラルで散らばらず定数表に集約されるのが普通で、
    呼び出し側には `dynamodb.TableDailyReports` しか現れない。ここを読まないと
    Go のリポジトリでは資源結合が1本も取れない(実データで確認した)。
    """
    decls: list = []
    _find(fi.root, {"const_declaration"}, decls)
    for decl in decls:
        for spec in _children(decl, "const_spec"):
            nnode, vnode, tnode = (_field(spec, "name"), _field(spec, "value"),
                                   _field(spec, "type"))
            if not (nnode and vnode):
                continue
            name = _txt(fi.src, nnode)
            ctype = _txt(fi.src, tnode) if tnode else ""
            kind = _res_const_kind(name, ctype, rcfg)
            if not kind:
                continue
            value = _txt(fi.src, vnode)
            # const_spec の value は expression_list のことがある
            lit = _unquote(value.split(",")[0].strip())
            entry = (kind, lit if lit and not lit.startswith('"') else f"#{name}")
            into[name] = entry
            into[f"{fi.pkg_name}.{name}"] = entry


def _res_const_kind(name: str, ctype: str, rcfg: dict) -> str:
    """定数が資源名かどうかを、宣言された型か名前で決める。"""
    kinds = {"Table": "dynamodb", "Bucket": "s3", "Queue": "sqs",
             "Topic": "sns", "Stream": "kinesis"}
    for pat in rcfg["const_type_patterns"]:
        if fnmatch(ctype, pat):
            return kinds.get(pat.replace("Name", ""), "other")
    for pat in rcfg["const_name_patterns"]:
        if fnmatch(name, pat):
            return kinds.get(pat.rstrip("*"), "other")
    return ""


def _res_go_parts(node, src: bytes, consts: dict) -> list:
    """Go の式をリテラル片の並びに分解する。`aws.String("x")` の包みは剥がす。"""
    if node is None:
        return [None]
    t = node.type
    if t in {"interpreted_string_literal", "raw_string_literal"}:
        return [_unquote(_txt(src, node))]
    if t == "binary_expression":
        return (_res_go_parts(_field(node, "left"), src, consts)
                + _res_go_parts(_field(node, "right"), src, consts))
    if t in {"identifier", "selector_expression"}:
        got = consts.get(_txt(src, node))
        return [got[1]] if got else [None]
    if t == "call_expression":
        fn = _txt(src, _field(node, "function") or node)
        if fn.endswith((".String", ".ToString", ".Ptr")):
            args = _args(node)
            if args:
                return _res_go_parts(args[0], src, consts)
    return [None]


def _res_scan_go(body, src: bytes, sid: str, consts: dict, rcfg: dict, out: list) -> None:
    kwargs = rcfg["kind_by_kwarg"]

    def add(kind, name, access, evidence):
        if name:
            out.append(res.make_ref(sid, kind, name, access, "確実", evidence[:100]))

    calls: list = []
    _find(body, {"call_expression"}, calls)
    for call in calls:
        fnode = _field(call, "function")
        op = _txt(src, _field(fnode, "field")) if (
            fnode is not None and fnode.type == "selector_expression") else _txt(src, fnode or call)
        if op in {"Getenv", "LookupEnv"}:
            var = _first_string_arg(call, src)
            if var:
                add("env", f"${var}", "read", f"os.{op}(\"{var}\")")
            continue
        for arg in _args(call):
            if arg.type not in {"identifier", "selector_expression"}:
                continue
            got = consts.get(_txt(src, arg))
            if got:
                add(got[0], got[1], res.access_of(op), f"{op}(… {_txt(src, arg)} …)")

    lits: list = []
    _find(body, {"literal_value", "composite_literal"}, lits)
    for lit in lits:
        for el in _children(lit, "keyed_element"):
            kids = [c for c in el.children if c.type not in {":", ","}]
            if len(kids) < 2:
                continue
            # キーも値も `literal_element` に包まれている(`_unwrap_lit`)。
            # 値を剥がさないと下の型判定が常に外れ、複合リテラル経由の資源参照が
            # 1件も取れない。キーは `_txt` が同じ文字列を返すので包みのままでよい。
            key, value = _txt(src, kids[0]), _unwrap_lit(kids[1])
            if value is None:
                continue
            kind = kwargs.get(key)
            if kind:
                add(kind, res.norm_name(_res_go_parts(value, src, consts)), "unknown",
                    f"{key}: {_txt(src, value)}")
                continue
            got = consts.get(_txt(src, value)) if value.type in {
                "identifier", "selector_expression"} else None
            if got:
                add(got[0], got[1], "unknown", f"{key}: {_txt(src, value)}")


# --------------------------------------------------------------------------- 入口

def extract(root: Path, cfg: dict, scope: Path | None = None) -> dict:
    lang_cfg = cfg["languages"]["go"]
    skipped: dict = {}
    files, vendored = base.collect_files(root, cfg, lang_cfg["extensions"], scope, skipped)
    parser = _load_parser()
    modules = _module_paths(root)

    infos: dict[str, _GoFile] = {}
    symbols: list[dict] = []
    unresolved: list[dict] = []

    for path in files:
        rel = path.resolve().relative_to(root).as_posix()
        src = path.read_bytes()
        try:
            tree = parser.parse(src)
        except Exception as exc:                     # pragma: no cover
            unresolved.append({"from": base.symbol_id(rel, "<file>"),
                               "expression": f"<解析失敗: {exc}>"[:120], "reason": "dynamic"})
            continue
        fi = _collect_file(rel, src, tree, modules)
        infos[rel] = fi
        for name, (sid, _r, *_q) in fi.funcs.items():
            symbols.append({"id": sid, "file": rel, "name": name, "kind": "function",
                            "visibility": "public" if name[:1].isupper() else "private"})
        for (typ, name), sid in fi.methods.items():
            symbols.append({"id": sid, "file": rel, "name": f"{typ}.{name}", "kind": "method",
                            "visibility": "public" if name[:1].isupper() else "private"})

    rv = _GoResolver(infos)
    edges: list[dict] = []
    endpoints: list[dict] = []

    # `package main` の `func main` は**このバイナリの入口**である(KIT-shell-make-extraction 案4)。
    # HTTP の経路と同じ「入口」なので、エンドポイントとして出す。これを出さないと、
    # バイナリとして配布される Go の入口が機械に1件も見えない。
    #
    # **protocol は `main`** — `cli` ではない。`func main` から分かるのは「これは実行ファイルの
    # 入口である」ことだけで、その実行ファイルが対話的な CLI 道具なのか、常駐する定時処理なのか、
    # HTTP サーバなのかは**この位置からは決まらない**。`cli` と出すと抽出器が持っていない知識を
    # 主張することになり、`kind: event` の機能(定時起動のジョブ)が CG6「kind と実際の種別(cli)が
    # 食い違う」から構造的に抜けられなくなる。`main` は**種別の証拠にならない protocol** であり、
    # CG6 はこれを突き合わせに使わない(`callgraph-check.py` の `KIND_AGNOSTIC_PROTOCOLS`)。
    for rel in sorted(infos):
        fi = infos[rel]
        if fi.pkg_name != "main" or "main" not in fi.funcs:
            continue
        sid = fi.funcs["main"][0]
        endpoints.append({
            "id": f"dispatch main @ {sid}",
            "protocol": "main",
            "path_pattern": base.normalize_path_pattern(rel),
            "path_key": base.path_key(rel),
            "handler": sid,
            "source": rel,
        })

    resource_refs: list[dict] = []
    rcfg = res.cfg_of(cfg)
    external = 0

    # 資源名の定数表はリポジトリ全体で1つにする(`dynamodb.TableUsers` は
    # 定義パッケージの外から参照されるのが普通なので、ファイル単位では引けない)。
    res_consts: dict[str, tuple[str, str]] = {}
    if rcfg["enabled"]:
        for _rel, fi in sorted(infos.items()):
            _res_consts(fi, rcfg, res_consts)

    for rel, fi in infos.items():
        for node in fi.root.children:
            if node.type not in {"function_declaration", "method_declaration"}:
                continue
            name_node = _field(node, "name")
            if not name_node:
                continue
            name = _txt(fi.src, name_node)
            recv = None
            if node.type == "method_declaration":
                rtype = ""
                for decl in _children(_field(node, "receiver"), "parameter_declaration"):
                    tnode, nnode = _field(decl, "type"), _field(decl, "name")
                    if tnode:
                        rtype = _strip_ptr(_txt(fi.src, tnode))
                    if nnode:
                        recv = (_txt(fi.src, nnode), rtype)
                if recv is None and rtype:
                    recv = ("_", rtype)
                sid = base.symbol_id(rel, f"{rtype}.{name}")
            else:
                sid = base.symbol_id(rel, name)

            sc = _Scope(fi, rv, recv)
            plist = _field(node, "parameters")
            for decl in _children(plist, "parameter_declaration"):
                tnode = _field(decl, "type")
                is_func = tnode is not None and tnode.type in {"function_type", "func_literal"}
                for c in decl.children:
                    if c.type != "identifier":
                        continue
                    pname = _txt(fi.src, c)
                    if is_func:
                        sc.params.add(pname)      # 関数を受け取る引数だけが高階呼び出しになりうる
                    elif tnode is not None:
                        # 引数の型が分かれば、`w.WriteHeader()` は型経由で解決できる。
                        # ここを入れないと、引数レシーバの呼び出しが全部「高階」に化ける。
                        sc.vars[pname] = _strip_ptr(_txt(fi.src, tnode))
                        sc.vars_q[pname] = _qualified_type(_txt(fi.src, tnode), fi)
            body = _field(node, "body")
            if body is None:
                continue
            _collect_locals(body, fi.src, sc)

            calls: list = []
            _find(body, {"call_expression"}, calls)
            for call in calls:
                target, unres, is_ext = _resolve(call, fi.src, sc)
                if target and target != sid:
                    edges.append({"from": sid, "to": target})
                elif unres:
                    f = _field(call, "function")
                    rec = {"from": sid,
                           "expression": _txt(fi.src, f)[:100] if f else "<式>",
                           "reason": unres["reason"]}
                    if unres.get("candidates"):
                        rec["candidates"] = unres["candidates"]
                    unresolved.append(rec)
                elif is_ext:
                    external += 1

            unresolved.extend(_dispatch_calls(body, fi.src, sc, sid))
            _walk_routes(body, fi.src, sc, {}, sid, endpoints, unresolved)
            if rcfg["enabled"]:
                _res_scan_go(body, fi.src, sid, res_consts, rcfg, resource_refs)

    out = base.sort_lang_result({
        "tier": 2,
        "extractor": "tree-sitter-go",
        "external_call_count": external,
        "symbols": symbols,
        "edges": edges,
        "endpoints": endpoints,
        "unresolved": unresolved,
        "vendored_dirs": vendored,
        "skipped_files": skipped,
    })
    out["resource_refs"] = res.sort_refs(resource_refs)
    return out
