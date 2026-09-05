"""Python 抽出器 (Tier 2) — 標準ライブラリの ast だけで動く。外部依存ゼロ。

規範: .claude/directions/callgraphs.md / 契約: callgraph-schema.json

方針:
  ・**対象コードを import しない**(NFR-5)。副作用を起こさないため静的解析のみ。
  ・シンボルはモジュール直下の関数・クラスのメソッド・モジュール本体(`<module>`)、
    および**内部分岐の合成シンボル**(`lambda_handler#CREATE` のような cmd 分岐)。
    **入れ子関数と無名関数は独立シンボルにせず、囲っている名前付きシンボルに帰属**させる
    (directions §5.1)。
  ・解決できなかった呼び出しは分類して全件残す(directions §5.5)。空欄で落とさない。
  ・internal_roots の外(標準ライブラリ・サードパーティ)への呼び出しは件数だけ数える(§5.4)。

**受け手の出所を先に決める**のがこの抽出器の肝である。実データ(2000シンボル規模)では、
出所を見ずに「同名の内部シンボル」へ照合しにいくと、`os.environ.get` / `f.read` /
`zlib.decompress` のような標準ライブラリ呼び出しが片っ端に ambiguous になり、未解決の94%を
占めて信号が埋もれた。だから §解決 では次の順に確定させる:
  1. import 由来で外部と分かるもの   → 外部(照合しない)
  2. self / super / ローカル変数の型 → 内部として精密に解決
  3. 組み込み型のメソッド名          → 外部(照合しない)
  4. それ以外                        → 最後の手段として同名照合(曖昧なら候補を全部出す)
"""

from __future__ import annotations

import ast
import warnings
from pathlib import Path

try:                                                     # Python 3.11+
    import tomllib
except ModuleNotFoundError:                              # pragma: no cover
    tomllib = None                                       # pyproject.toml は読まない(入口が減るだけ)

from . import base
from . import resources as res

ROUTE_METHODS ={"get", "post", "put", "patch", "delete", "head", "options", "trace"}
ROUTER_FACTORIES = {"APIRouter", "FastAPI", "Blueprint", "Flask"}
PREFIX_KWARGS = ("prefix", "url_prefix")
MODULE_SYMBOL = "<module>"

# 受け手の型が分からないとき、この名前のメソッド呼び出しは**内部シンボルと照合しない**。
# 組み込み型(dict/list/str/bytes/file/set)のメソッドであり、同名の内部関数に当たると
# 大量の偽 ambiguous を生むため。「解決できなかった」ではなく「外部」に分類する。
BUILTIN_METHODS = {
    # dict
    "get", "items", "keys", "values", "setdefault", "popitem",
    # list / set / 共通
    "append", "extend", "insert", "remove", "pop", "clear", "sort", "reverse",
    "index", "count", "copy", "update", "add", "discard",
    # str / bytes
    "encode", "decode", "format", "join", "split", "rsplit", "splitlines",
    "strip", "lstrip", "rstrip", "replace", "startswith", "endswith",
    "lower", "upper", "title", "capitalize", "zfill", "find", "rfind",
    "isdigit", "isalpha", "isnumeric", "isspace", "hex",
    # file / stream / context
    "read", "readline", "readlines", "write", "writelines", "seek", "tell",
    "flush", "close", "fileno",
    # datetime / decimal など、よく使う標準型
    "strftime", "strptime", "isoformat", "timestamp", "astimezone", "quantize",
    # threading / queue
    "acquire", "release", "wait", "notify", "put", "task_done",
}

# 上の名前でも、リポジトリ内で**明示的に定義されている**場合に照合したいことはある。
# ただし既定では照合しない(実データでは偽陽性の方が桁違いに多い)。


# --------------------------------------------------------------------------- 収集

def _const_str(node) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _kwarg(call: ast.Call, names: tuple[str, ...]) -> str | None:
    for kw in call.keywords:
        if kw.arg in names:
            return _const_str(kw.value)
    return None


def _module_candidates(rel: str) -> list[str]:
    """`src/api/auth.py` → ['src.api.auth', 'api.auth', 'auth']。

    Python のモジュール名は sys.path 依存で静的には一意に決まらないので、
    末尾から順に候補を作り、**最長一致を優先**して解決する。
    """
    parts = rel[:-3].split("/")
    if parts[-1] == "__init__":
        parts = parts[:-1]
    if not parts:
        return []
    return [".".join(parts[i:]) for i in range(len(parts))]


def _root_name(node) -> str | None:
    """属性チェーンの根にある Name を返す(`os.environ.get` → `os`)。"""
    while isinstance(node, (ast.Attribute, ast.Subscript)):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


class _FileInfo:
    def __init__(self, rel: str, tree: ast.Module):
        self.rel = rel
        self.tree = tree
        self.imports: dict[str, tuple[str, str]] = {}   # local名 → ("module"|"symbol", dotted)
        self.classes: dict[str, dict] = {}              # クラス名 → {bases, methods, attrs}
        self.functions: dict[str, str] = {}             # 関数名 → symbol_id
        self.routers: dict[str, dict] = {}              # 変数名 → {prefix, framework}
        self.dispatch: dict[str, list[tuple[str, list]]] = {}   # 関数名 → [(値, 本文)]
        self.module_ctors: dict[str, str] = {}          # モジュール変数 → クラス名
        self.module_aliases: dict[str, str] = {}        # モジュール変数 → 別のローカル名
        self.str_sets: dict[str, list[str]] = {}        # モジュール定数名 → 文字列の集合


def _collect_imports(fi: _FileInfo) -> None:
    pkg = fi.rel[:-3].split("/")
    pkg = pkg[:-1] if pkg[-1] != "__init__" else pkg[:-2]

    for node in ast.walk(fi.tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                fi.imports[a.asname or a.name.split(".")[0]] = (
                    "module", a.name if a.asname else a.name.split(".")[0])
                fi.imports[a.name] = ("module", a.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:                      # 相対 import
                bmod = pkg[: len(pkg) - node.level + 1] if node.level > 1 else pkg
                mod = ".".join([*bmod, node.module]) if node.module else ".".join(bmod)
            else:
                mod = node.module or ""
            for a in node.names:
                if a.name == "*":
                    continue
                fi.imports[a.asname or a.name] = ("symbol", f"{mod}.{a.name}" if mod else a.name)


def _collect_str_sets(tree: ast.Module) -> dict[str, list[str]]:
    """モジュール直下の「文字列の集合」定数を集める(`cmd in OPERATION_CMDS` の解決用)。

    対応する形: `list` / `tuple` / `set` / `dict`(キー)/ `frozenset(...)` 等の呼び出し。
    要素・キーが**文字列定数への名前参照**でもよい —— 実コードでは cmd 名を定数へ括り出す
    書き方が普通で(`CMD_TO_EVENT = {CMD_CONFIRM_APPLICATION: ...}`)、ここを解かないと
    名前付き集合は解決できない。
    """
    scalars: dict[str, str] = {}
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 \
                and isinstance(stmt.targets[0], ast.Name):
            s = _const_str(stmt.value)
            if s:
                scalars[stmt.targets[0].id] = s

    def as_str(node) -> str | None:
        s = _const_str(node)
        if s:
            return s
        if isinstance(node, ast.Name):
            return scalars.get(node.id)
        if isinstance(node, ast.Attribute):
            return scalars.get(node.attr)
        return None

    out: dict[str, list[str] | tuple[str, str]] = {}

    def literal_strs(node):
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            vals = [v for v in (as_str(e) for e in node.elts) if v]
            return vals or None
        if isinstance(node, ast.Dict):
            vals = [v for v in (as_str(k) for k in node.keys) if v]
            return vals or None
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in ("frozenset", "set", "list", "tuple") and node.args):
            inner = literal_strs(node.args[0])
            if inner:
                return inner
            if isinstance(node.args[0], ast.Name):
                return ("__ref__", node.args[0].id)      # 1段だけ参照を辿る
        return None

    for stmt in tree.body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 \
                and isinstance(stmt.targets[0], ast.Name):
            got = literal_strs(stmt.value)
            if got:
                out[stmt.targets[0].id] = got
    for k, v in list(out.items()):
        if isinstance(v, tuple):
            ref = out.get(v[1])
            out[k] = ref if isinstance(ref, list) else None
    return {k: v for k, v in out.items() if isinstance(v, list)}


def _find_dispatch(fn, dispatch_vars: set[str],
                   str_sets: dict[str, list[str]] | None = None) -> list[tuple[str, list]]:
    """`if cmd == "X": ... elif cmd == "Y": ...` / `match cmd: case "X":` を拾う。

    「app.py で cmd などで分岐している場合はそれぞれの cmd も
    1つの機能とみなす」という要求を機械的に満たすための検出。名目上の関数ではなく、
    **実質的な機能実装ごとに1シンボル**にする。

    拾える形(`.claude/directions/callgraphs.md` §5.7):

    - `cmd == "X"` / `cmd in ["A", "B"]` / `match cmd: case "X":`
    - **複合ガード** `cmd == "X" and <他の条件>` — 追加条件は分岐の前提であって別の cmd ではない
    - **ネストした分岐** — `try:` / `with` / `for` / `while` / 非分岐の `if` の内側
    - **名前付き集合** `cmd in OPERATION_CMDS` — `str_sets` で解決できる場合だけ

    同じ分岐値が複数回現れる場合(ガード違いの対など)は**本文を連結して1つに畳む**。
    分けると同一シンボルIDが2つでき、`symbols` / `endpoints` が重複する
    (`base.sort_lang_result` は重複除去しない)。
    """
    str_sets = str_sets or {}
    found: list[tuple[str, list]] = []

    def branch_value(test) -> str | None:
        if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And):
            for v in test.values:                        # 複合ガード
                got = branch_value(v)
                if got:
                    return got
            return None
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.left, ast.Name) and test.left.id in dispatch_vars):
            return None
        op, comp = test.ops[0], test.comparators[0]
        if isinstance(op, ast.Eq):
            return _const_str(comp)
        if isinstance(op, ast.In):
            if isinstance(comp, (ast.List, ast.Tuple, ast.Set)):
                vals = sorted({v for v in (_const_str(e) for e in comp.elts) if v})
                return "|".join(vals) if vals else None
            name = comp.id if isinstance(comp, ast.Name) else (
                comp.attr if isinstance(comp, ast.Attribute) else None)
            if name and str_sets.get(name):
                return "|".join(sorted(set(str_sets[name])))
        return None

    def scan_if(node) -> None:
        cur = node
        while isinstance(cur, ast.If):
            val = branch_value(cur.test)
            if val:
                found.append((val, cur.body))
            else:
                walk(cur.body)                  # 分岐でないなら中を掘る
            if len(cur.orelse) == 1 and isinstance(cur.orelse[0], ast.If):
                cur = cur.orelse[0]             # elif チェーン
            else:
                walk(cur.orelse)                # else 本文
                cur = None

    def walk(body) -> None:
        for stmt in body or []:
            if isinstance(stmt, ast.If):
                scan_if(stmt)
            elif isinstance(stmt, ast.Match) and isinstance(stmt.subject, ast.Name) \
                    and stmt.subject.id in dispatch_vars:
                for case in stmt.cases:
                    pat = case.pattern
                    val = _const_str(pat.value) if isinstance(pat, ast.MatchValue) else None
                    if val:
                        found.append((val, case.body))
            elif isinstance(stmt, ast.Try):
                walk(stmt.body)
                for h in stmt.handlers:
                    walk(h.body)
                walk(stmt.orelse)
                walk(stmt.finalbody)
            elif isinstance(stmt, (ast.With, ast.AsyncWith, ast.For, ast.AsyncFor, ast.While)):
                walk(stmt.body)

    walk(getattr(fn, "body", []))

    merged: dict[str, list] = {}
    for value, body in found:                   # 同じ値は本文を連結して1つに畳む
        merged.setdefault(value, []).extend(body)
    return [(v, merged[v]) for v in sorted(merged)]


def _visible_str_sets(fi: _FileInfo, infos: dict[str, _FileInfo]) -> dict[str, list[str]]:
    """このファイルから見える「文字列集合」定数を集める(自分 + **import したモジュール**)。

    ディレクトリ内の `.py` を一括マージしてはならない —— import と無関係な同名定数
    (各 `drv_dynamodb_*.py` が持つ `indices` など)を拾い、どれが勝つかが読み込み順で
    決まる。実際の import を辿れば衝突の余地が無い。
    """
    out = dict(fi.str_sets)
    here = fi.rel.rsplit("/", 1)[0] if "/" in fi.rel else ""
    for kind, dotted in fi.imports.values():
        mod = dotted.split(".")[0] if kind == "module" else dotted.rsplit(".", 1)[0]
        if not mod:
            continue
        cand = f"{here}/{mod.replace('.', '/')}.py" if here else f"{mod.replace('.', '/')}.py"
        other = infos.get(cand)
        if other is not None and other is not fi:
            for k, v in other.str_sets.items():
                out.setdefault(k, v)
    return out


def _drop_declared_guards(rel: str, qual: str, branches: list[tuple[str, list]],
                          guards: set[str], hits: set[str] | None = None
                          ) -> list[tuple[str, list]]:
    r"""**宣言されたガード節を分岐から外す** ★(2026-08-25。ct_matchsupport の課題票 243)。

    `cmd in <集合>` という綴りは、**機能の分岐**でも**要求を弾く前段**でも同じ形になる:

        # 前段(実在しない入口を1つ作る)                # 本物のハンドラ(VIP だけ別扱い)
        if route == APPLICANT and cmd in IDENTIFIED \    if tenant == "vip" and cmd in ("A","B"):
                and not p.get("applicationDataId"):          return vip_batch(p)
            return err(...)                            if cmd == "A": return ordinary_a(p)
        elif cmd == "CHECK_PAYMENT": ...               if cmd == "B": return ordinary_b(p)

    **どちらも「追加条件つき」で「値が細かい分岐にも在る」。** 形では区別できず、
    自動で落とすと右の本物の入口が消える(2026-08-25 の独立検査が反例で示した)。
    **区別しているのは「その分岐が機能か」という意味であり、それは人間の合意事項である**
    (`features.md` — 機能表の行は人間のもの)。だから**宣言で落とす**:

        // callgraph-config.local.json
        "languages": {"python": {"dispatch_guards": [
          "backend/.../app.py::lambda_handler#CHECK_PAYMENT|PAY_BY_CONVENI|PAY_BY_CREDIT_CARD"
        ]}}

    書く文字列は **FT2 の指摘がそのまま印字するハンドラのID**である(コピーして貼れる)。
    落とした本文は**ディスパッチャ本体に残る** — `_without_branches` が差分で本体を作るので、
    ガードの中の呼び出し(エラー応答など)は辺として消えない。**畳み込みは要らない。**

    **効くのは「値」の単位である** ★(2026-08-25 の独立検査・2周目)。同じ値の分岐は
    `_find_dispatch` が**先に1つへ畳んでいる**ので、`#A` を宣言すると
    `if tenant == "vip" and cmd == "A"` と `if cmd == "A"` の**両方**が落ちる。
    **だから、値が本物の分岐と同じガードを宣言してはならない** — そしてその必要も無い:
    値が同じなら合成される入口は1つで、**偽の入口はそもそも生まれず**、ガードの中の
    呼び出しはその機能に帰属して正しい。**宣言してよいのは、FT2 が偽物として指摘した値だけ**
    である(その値は機能表に行を持たない)。

    **照合しなかった宣言は `hits` の差として呼び出し側へ返り、生成物の表に出る** —
    綴り違い(パス・関数名・値の順序)や、コードから消えたガードを黙って見逃さないためである。
    """
    if not guards:
        return branches
    out: list[tuple[str, list]] = []
    for v, b in branches:
        key_ = f"{rel}::{qual}#{v}"
        if key_ in guards:
            if hits is not None:
                hits.add(key_)
            continue
        out.append((v, b))
    return out


def _collect_defs(fi: _FileInfo, symbols: list[dict], dispatch_vars: set[str],
                  str_sets: dict[str, list[str]] | None = None,
                  guards: set[str] | None = None,
                  guard_hits: set[str] | None = None) -> None:
    def add(qual: str, kind: str) -> str:
        sid = base.symbol_id(fi.rel, qual)
        simple = qual.split(".")[-1].split("#")[0]
        dunder = simple.startswith("__") and simple.endswith("__")
        symbols.append({
            "id": sid, "file": fi.rel, "name": qual, "kind": kind,
            "visibility": "private" if simple.startswith("_") and not dunder else "public",
        })
        return sid

    has_module_call = any(
        isinstance(n, ast.Call)
        for stmt in fi.tree.body
        if not isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        for n in ast.walk(stmt)
    )
    if has_module_call:
        add(MODULE_SYMBOL, "function")

    for stmt in fi.tree.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fi.functions[stmt.name] = add(stmt.name, "function")
            branches = _drop_declared_guards(
                fi.rel, stmt.name, _find_dispatch(stmt, dispatch_vars, str_sets),
                guards or set(), guard_hits)
            if branches:
                fi.dispatch[stmt.name] = branches
                for value, _body in branches:
                    add(f"{stmt.name}#{value}", "handler")
        elif isinstance(stmt, ast.ClassDef):
            bases = [b.id for b in stmt.bases if isinstance(b, ast.Name)]
            bases += [b.attr for b in stmt.bases if isinstance(b, ast.Attribute)]
            methods: dict[str, str] = {}
            for sub in stmt.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    kind = "constructor" if sub.name == "__init__" else "method"
                    methods[sub.name] = add(f"{stmt.name}.{sub.name}", kind)
                    branches = _drop_declared_guards(
                        fi.rel, f"{stmt.name}.{sub.name}",
                        _find_dispatch(sub, dispatch_vars, str_sets), guards or set(),
                        guard_hits)
                    if branches:
                        fi.dispatch[f"{stmt.name}.{sub.name}"] = branches
                        for value, _body in branches:
                            add(f"{stmt.name}.{sub.name}#{value}", "handler")
            fi.classes[stmt.name] = {"bases": bases, "methods": methods, "attrs": {}}


def _collect_routers(fi: _FileInfo) -> None:
    for stmt in fi.tree.body:
        if not isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            continue
        targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
        value = stmt.value
        if not isinstance(value, ast.Call):
            continue
        fn = value.func
        factory = fn.id if isinstance(fn, ast.Name) else fn.attr if isinstance(fn, ast.Attribute) else None
        if factory not in ROUTER_FACTORIES:
            continue
        prefix = _kwarg(value, PREFIX_KWARGS) or ""
        framework = "flask" if factory in {"Blueprint", "Flask"} else "fastapi"
        for t in targets:
            if isinstance(t, ast.Name):
                fi.routers[t.id] = {"prefix": prefix, "framework": framework}


def _collect_module_level(fi: _FileInfo) -> None:
    """モジュール直下の `x = SomeClass()` と `x = 別名` を拾う。

    実データでは `drv_dynamodb = drv_dynamodb_journalTbl`(import 済みモジュールの別名)や
    モジュールレベルのシングルトン生成が多く、これを見ないと `drv_dynamodb.create()` が
    延々と同名照合に落ちて偽 ambiguous になる。
    """
    for stmt in fi.tree.body:
        if not isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            continue
        targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
        value = stmt.value
        for tgt in targets:
            if not isinstance(tgt, ast.Name):
                continue
            if isinstance(value, ast.Call):
                ctor = value.func
                name = ctor.id if isinstance(ctor, ast.Name) else \
                    ctor.attr if isinstance(ctor, ast.Attribute) else None
                if name:
                    fi.module_ctors[tgt.id] = name
            elif isinstance(value, ast.Name):
                fi.module_aliases[tgt.id] = value.id


def _collect_self_attrs(fi: _FileInfo) -> None:
    """`self.x = SomeClass()` を拾い、`self.x.method()` を解決できるようにする。"""
    for cls, info in fi.classes.items():
        for stmt in fi.tree.body:
            if not (isinstance(stmt, ast.ClassDef) and stmt.name == cls):
                continue
            for sub in stmt.body:
                if not isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for node in ast.walk(sub):
                    if not (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)):
                        continue
                    ctor = node.value.func
                    name = ctor.id if isinstance(ctor, ast.Name) else \
                        ctor.attr if isinstance(ctor, ast.Attribute) else None
                    if not name:
                        continue
                    for tgt in node.targets:
                        if (isinstance(tgt, ast.Attribute) and isinstance(tgt.value, ast.Name)
                                and tgt.value.id == "self"):
                            info["attrs"][tgt.attr] = name


# --------------------------------------------------------------------------- 解決

class _Resolver:
    def __init__(self, infos: dict[str, _FileInfo], symbols: list[dict]):
        self.infos = infos
        self.by_id = {s["id"]: s for s in symbols}
        self.module_map: dict[str, list[str]] = {}
        for rel in infos:
            for cand in _module_candidates(rel):
                self.module_map.setdefault(cand, []).append(rel)
        for k in self.module_map:
            self.module_map[k].sort()
        self.simple_index: dict[str, list[str]] = {}
        self.class_index: dict[str, list[str]] = {}
        for s in symbols:
            simple = s["name"].split(".")[-1]
            if simple != MODULE_SYMBOL and "#" not in simple:
                self.simple_index.setdefault(simple, []).append(s["id"])
        for rel, fi in infos.items():
            for cls in fi.classes:
                self.class_index.setdefault(cls, []).append(rel)
        for d in (self.simple_index, self.class_index):
            for k in d:
                d[k].sort()

    def module_to_rel(self, dotted: str, from_rel: str | None = None) -> str | None:
        """dotted なモジュール名をリポジトリ内の相対パスに解決する。

        同名モジュールが複数あるとき、**呼び出し元と同じディレクトリのものを優先する**。
        フラットな import(`import drv_userpool`)は Python では実行スクリプトの
        ディレクトリが最優先なので、これが実際の解決規則である。

        これが無いと、Lambda を1関数1ディレクトリに置いて同名ドライバを各所に
        コピーしている構成(実データで踏んだ)で、**跨ファイルの辺が丸ごと落ちる**。
        しかも未解決にも出ない黙った偽陰性になる。
        """
        parts = dotted.split(".")
        here = from_rel.rpartition("/")[0] if from_rel else None
        for i in range(len(parts), 0, -1):
            hits = self.module_map.get(".".join(parts[:i]))
            if not hits:
                continue
            if len(hits) == 1:
                return hits[0]
            if here is not None:
                same = [h for h in hits if h.rpartition("/")[0] == here]
                if len(same) == 1:
                    return same[0]
        return None

    def in_file(self, rel: str, name: str) -> str | None:
        fi = self.infos.get(rel)
        if not fi:
            return None
        if name in fi.functions:
            return fi.functions[name]
        if name in fi.classes:                      # クラス呼び出し = コンストラクタ
            return fi.classes[name]["methods"].get("__init__")
        return None

    def find_class(self, name: str, prefer_rel: str | None = None) -> tuple[str, str] | None:
        """クラス名からその定義ファイルを引く。同名が複数なら諦める(曖昧を作らない)。"""
        if prefer_rel and name in self.infos.get(prefer_rel, _EMPTY).classes:
            return (prefer_rel, name)
        hits = self.class_index.get(name, [])
        return (hits[0], name) if len(hits) == 1 else None

    def method_of_class(self, rel: str, cls: str, meth: str, depth: int = 0) -> str | None:
        fi = self.infos.get(rel)
        if not fi or cls not in fi.classes or depth > 5:
            return None
        info = fi.classes[cls]
        if meth in info["methods"]:
            return info["methods"][meth]
        for b in info["bases"]:                     # 基底クラスをリポジトリ内で辿る
            found = self.find_class(b, rel)
            if found:
                got = self.method_of_class(found[0], found[1], meth, depth + 1)
                if got:
                    return got
        return None

    def by_simple_name(self, name: str) -> tuple[str | None, list[str]]:
        hits = self.simple_index.get(name, [])
        if len(hits) == 1:
            return hits[0], []
        return None, hits


_EMPTY = _FileInfo("", ast.Module(body=[], type_ignores=[]))


def _deref(fi: _FileInfo, local: str, depth: int = 0) -> str:
    """モジュールレベルの別名を辿る(`drv_dynamodb = drv_dynamodb_journalTbl`)。"""
    seen = {local}
    while local in fi.module_aliases and depth < 5:
        nxt = fi.module_aliases[local]
        if nxt in seen:
            break
        seen.add(nxt)
        local = nxt
        depth += 1
    return local


def _module_ref(fi: _FileInfo, rv: _Resolver, local: str) -> str | None:
    """ローカル名がリポジトリ内モジュールを指しているなら、その相対パスを返す。"""
    local = _deref(fi, local)
    imp = fi.imports.get(local)
    if not imp:
        return None
    kind, dotted = imp
    if kind == "module":
        return rv.module_to_rel(dotted, fi.rel)
    whole = rv.module_map.get(dotted)
    if whole and len(whole) == 1:
        return whole[0]
    if whole:                                    # 同名が複数 → 同一ディレクトリを優先
        here = fi.rel.rpartition("/")[0]
        same = [h for h in whole if h.rpartition("/")[0] == here]
        if len(same) == 1:
            return same[0]
    return None


def _is_external_import(fi: _FileInfo, rv: _Resolver, local: str) -> bool:
    """import 済みだが、リポジトリ内のどのモジュールでもない = 外部と確定できる。

    これが `zlib.decompress` や `copy.copy` や `os.environ.get` を同名照合から外す。
    """
    local = _deref(fi, local)
    imp = fi.imports.get(local)
    if not imp:
        return False
    if _module_ref(fi, rv, local) is not None:
        return False
    kind, dotted = imp
    if kind == "symbol":
        mod = dotted.rpartition(".")[0]
        if mod and rv.module_to_rel(mod, fi.rel) is not None:
            return False       # 内部モジュールのシンボル
    return True


def _local_types(node, rel: str, cls: str | None, rv: _Resolver,
                 fi: _FileInfo) -> tuple[dict[str, tuple[str, str]], set[str]]:
    """関数内のローカル変数の型を推定する。

    (変数名 → (定義ファイル, クラス名), 外部と分かっている変数名)。
    `x = SomeClass()` / `def f(x: SomeClass)` / `with open(...) as f` を見る。
    型注釈も代入も無ければ何も言わない — **推測しない**。
    """
    types: dict[str, tuple[str, str]] = {}
    external: set[str] = set()
    conflict: set[str] = set()

    def note(name: str, ctor_name: str | None, from_call_external: bool) -> None:
        if ctor_name:
            found = rv.find_class(ctor_name, rel)
            if found:
                if name in types and types[name] != found:
                    conflict.add(name)
                types[name] = found
                return
        if from_call_external:
            external.add(name)

    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        a = node.args
        for arg in (*a.posonlyargs, *a.args, *a.kwonlyargs):
            ann = arg.annotation
            ann_name = ann.id if isinstance(ann, ast.Name) else \
                ann.attr if isinstance(ann, ast.Attribute) else None
            if ann_name:
                found = rv.find_class(ann_name, rel)
                if found:
                    types[arg.arg] = found

    for sub in ast.walk(node) if node is not None else []:
        if isinstance(sub, (ast.Assign, ast.AnnAssign)) and isinstance(sub.value, ast.Call):
            ctor = sub.value.func
            ctor_name = ctor.id if isinstance(ctor, ast.Name) else \
                ctor.attr if isinstance(ctor, ast.Attribute) else None
            root = _root_name(ctor)
            ext = bool(root and _is_external_import(fi, rv, root)) or \
                (isinstance(ctor, ast.Name) and ctor.id in {"open", "dict", "list", "set", "tuple"})
            targets = sub.targets if isinstance(sub, ast.Assign) else [sub.target]
            for tgt in targets:
                if isinstance(tgt, ast.Name):
                    note(tgt.id, ctor_name, ext)
        elif isinstance(sub, ast.AnnAssign) and isinstance(sub.target, ast.Name):
            ann = sub.annotation
            ann_name = ann.id if isinstance(ann, ast.Name) else None
            if ann_name:
                found = rv.find_class(ann_name, rel)
                if found:
                    types[sub.target.id] = found
        elif isinstance(sub, (ast.With, ast.AsyncWith)):
            for item in sub.items:
                if not isinstance(item.optional_vars, ast.Name):
                    continue
                ctx = item.context_expr
                if isinstance(ctx, ast.Call):
                    ctor = ctx.func
                    ctor_name = ctor.id if isinstance(ctor, ast.Name) else \
                        ctor.attr if isinstance(ctor, ast.Attribute) else None
                    root = _root_name(ctor)
                    ext = (isinstance(ctor, ast.Name) and ctor.id == "open") or \
                        bool(root and _is_external_import(fi, rv, root))
                    note(item.optional_vars.id, ctor_name, ext)

    for name in conflict:
        types.pop(name, None)
    return types, external


# --------------------------------------------------------------------------- 呼び出し抽出

def _walk_calls(node, out: list[ast.Call]) -> None:
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if child is not node:
                continue
        if isinstance(child, ast.Call):
            out.append(child)
        _walk_calls(child, out)


def _stmt_calls(stmts) -> list[ast.Call]:
    out: list[ast.Call] = []
    for stmt in stmts:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.extend(_stmt_calls(getattr(stmt, "body", [])))   # 入れ子は畳み込む
            continue
        if isinstance(stmt, ast.Call):
            out.append(stmt)
        _walk_calls(stmt, out)
    return out


def _without_branches(stmts, branch_stmt_ids: set[int]):
    """分岐本文に属する文を除いた文の並びを返す(複合文の中も辿る)。

    `if cmd == "A": ...` の本文は合成シンボルの持ち物なので、
    ディスパッチャ本体の呼び出しとして二重に数えない
    (`.claude/directions/callgraphs.md` §5.7「分岐から先の呼び出しは分岐に帰属する」
    「分岐の前後にある共通処理はディスパッチャ本体に残る」)。

    **`if` 以外の複合文にも降りる。** `_find_dispatch` は `try:` / `with` / `for` /
    `while` の内側の分岐も拾うので、ここが `if` しか辿らないと分岐本文が本体から
    除去されず、同じ呼び出しがディスパッチャと分岐の両方に帰属する(二重計上)。
    """
    out = []
    for stmt in stmts:
        if id(stmt) in branch_stmt_ids:
            continue
        if isinstance(stmt, ast.If):
            kept_body = _without_branches(stmt.body, branch_stmt_ids)
            kept_else = _without_branches(stmt.orelse, branch_stmt_ids)
            if kept_body or kept_else:
                clone = ast.If(test=stmt.test, body=kept_body, orelse=kept_else)
                out.append(clone)
            else:
                out.append(ast.Expr(value=stmt.test))   # 条件式の中の呼び出しは残す
            continue
        if isinstance(stmt, ast.Try):
            clone = ast.Try(
                body=_without_branches(stmt.body, branch_stmt_ids),
                handlers=[ast.ExceptHandler(type=h.type, name=h.name,
                                            body=_without_branches(h.body, branch_stmt_ids))
                          for h in stmt.handlers],
                orelse=_without_branches(stmt.orelse, branch_stmt_ids),
                finalbody=_without_branches(stmt.finalbody, branch_stmt_ids))
            out.append(clone)
            continue
        if isinstance(stmt, (ast.With, ast.AsyncWith)):
            cls = type(stmt)
            out.append(cls(items=stmt.items,
                           body=_without_branches(stmt.body, branch_stmt_ids)))
            continue
        if isinstance(stmt, (ast.For, ast.AsyncFor)):
            cls = type(stmt)
            out.append(cls(target=stmt.target, iter=stmt.iter,
                           body=_without_branches(stmt.body, branch_stmt_ids),
                           orelse=_without_branches(stmt.orelse, branch_stmt_ids)))
            continue
        if isinstance(stmt, ast.While):
            out.append(ast.While(test=stmt.test,
                                 body=_without_branches(stmt.body, branch_stmt_ids),
                                 orelse=_without_branches(stmt.orelse, branch_stmt_ids)))
            continue
        out.append(stmt)
    return out


def _param_names(node) -> frozenset[str]:
    if node is None or not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return frozenset()
    a = node.args
    names = [x.arg for x in (*a.posonlyargs, *a.args, *a.kwonlyargs)]
    if a.vararg:
        names.append(a.vararg.arg)
    if a.kwarg:
        names.append(a.kwarg.arg)
    return frozenset(names)


def _expr_text(call: ast.Call) -> str:
    try:
        return ast.unparse(call.func)
    except Exception:                                # pragma: no cover
        return "<式>"


class _Ctx:
    """1シンボル分の解決文脈。"""
    def __init__(self, rel: str, cls: str | None, fi: _FileInfo, rv: _Resolver,
                 params: frozenset[str], types: dict, external: set[str]):
        self.rel, self.cls, self.fi, self.rv = rel, cls, fi, rv
        self.params, self.types, self.external = params, types, external


def _resolve_call(call: ast.Call, c: _Ctx) -> tuple[str | None, dict | None, bool]:
    """(解決したsymbol_id, 未解決レコード, 外部呼び出しか) を返す。"""
    fn = call.func
    rv, fi, rel = c.rv, c.fi, c.rel

    if isinstance(fn, ast.Subscript):
        return None, {"reason": "dynamic"}, False
    if isinstance(fn, ast.Call):
        if isinstance(fn.func, ast.Name) and fn.func.id == "super":
            pass                                     # super() は下の Attribute 経路で扱う
        return None, {"reason": "higher-order"}, False

    # --- 素の名前呼び出し -------------------------------------------------
    if isinstance(fn, ast.Name):
        if fn.id in {"getattr", "setattr", "eval", "exec", "__import__"}:
            return None, {"reason": "reflection"}, False
        if fn.id in c.params:
            return None, {"reason": "higher-order"}, False
        got = rv.in_file(rel, fn.id)
        if got:
            return got, None, False
        if fn.id in fi.classes:                      # 内部クラスだが __init__ が無い
            return None, None, False
        imp = fi.imports.get(fn.id)
        if imp and imp[0] == "symbol":
            mod, _, name = imp[1].rpartition(".")
            target_rel = rv.module_to_rel(mod, fi.rel) if mod else None
            if target_rel:
                got = rv.in_file(target_rel, name)
                if got:
                    return got, None, False
                got = rv.method_of_class(target_rel, name, "__init__")
                if got:
                    return got, None, False
                if name in rv.infos[target_rel].classes:
                    return None, None, False
        return None, None, True

    if not isinstance(fn, ast.Attribute):
        return None, None, True

    attr, val = fn.attr, fn.value

    # --- 1. import 由来で外部と確定できる ---------------------------------
    root = _root_name(val)
    if root and _is_external_import(fi, rv, root):
        target_rel = _module_ref(fi, rv, root)
        if target_rel is None:
            return None, None, True                  # 標準ライブラリ・サードパーティ

    # --- 2. self / super / ローカル変数の型 -------------------------------
    if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) and val.func.id == "super":
        if c.cls:
            info = fi.classes.get(c.cls, {})
            for b in info.get("bases", []):
                found = rv.find_class(b, rel)
                if found:
                    got = rv.method_of_class(found[0], found[1], attr)
                    if got:
                        return got, None, False
        return None, None, True

    if isinstance(val, ast.Name):
        if val.id in {"self", "cls"} and c.cls:
            got = rv.method_of_class(rel, c.cls, attr)
            if got:
                return got, None, False
            return None, None, True                  # 継承先や動的属性。外部扱いで雑音にしない
        if val.id in c.types:
            crel, cname = c.types[val.id]
            got = rv.method_of_class(crel, cname, attr)
            if got:
                return got, None, False
            return None, None, True                  # 型は分かっていて、そのメソッドは無い
        if val.id in c.external:
            return None, None, True
        mod_ctor = fi.module_ctors.get(_deref(fi, val.id))
        if mod_ctor:
            found = rv.find_class(mod_ctor, rel)
            if found:
                got = rv.method_of_class(found[0], found[1], attr)
                if got:
                    return got, None, False
            return None, None, True
        target_rel = _module_ref(fi, rv, val.id)
        if target_rel is not None:
            got = rv.in_file(target_rel, attr)
            if got:
                return got, None, False
            return None, None, True
        imp = fi.imports.get(val.id)
        if imp and imp[0] == "symbol":
            mod, _, name = imp[1].rpartition(".")
            cls_rel = rv.module_to_rel(mod, fi.rel) if mod else None
            if cls_rel and name in rv.infos.get(cls_rel, _EMPTY).classes:
                got = rv.method_of_class(cls_rel, name, attr)
                if got:
                    return got, None, False
                return None, None, True
        if val.id in fi.classes:                     # ローカルクラスの静的呼び出し
            got = rv.method_of_class(rel, val.id, attr)
            if got:
                return got, None, False
            return None, None, True

    # self.attr.method()
    if (isinstance(val, ast.Attribute) and isinstance(val.value, ast.Name)
            and val.value.id == "self" and c.cls):
        ctor_name = fi.classes.get(c.cls, {}).get("attrs", {}).get(val.attr)
        if ctor_name:
            found = rv.find_class(ctor_name, rel)
            if found:
                got = rv.method_of_class(found[0], found[1], attr)
                if got:
                    return got, None, False
            return None, None, True

    # --- 3. 組み込み型のメソッド名 ----------------------------------------
    if attr in BUILTIN_METHODS:
        return None, None, True

    # --- 4. 最後の手段: 同名照合 ------------------------------------------
    got, candidates = rv.by_simple_name(attr)
    if got:
        return got, None, False
    if candidates:
        return None, {"reason": "ambiguous", "candidates": candidates}, False
    return None, None, True


# --------------------------------------------------------------------------- ルート

def resolve_router_ref(rel: str, node, infos: dict[str, _FileInfo],
                       rv: _Resolver) -> tuple[str, str] | None:
    fi = infos.get(rel)
    if fi is None:
        return None
    if isinstance(node, ast.Name):
        if node.id in fi.routers:
            return (rel, node.id)
        imp = fi.imports.get(node.id)
        if imp and imp[0] == "symbol":
            mod, _, name = imp[1].rpartition(".")
            target = rv.module_to_rel(mod, fi.rel) if mod else None
            if target and name in infos[target].routers:
                return (target, name)
        return None
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        target = _module_ref(fi, rv, node.value.id)
        if target and node.attr in infos[target].routers:
            return (target, node.attr)
    return None


def _router_chain_prefixes(infos: dict[str, _FileInfo], rv: _Resolver) -> dict[tuple[str, str], list[str]]:
    edges: list[tuple[tuple[str, str], tuple[str, str], str]] = []
    children: set[tuple[str, str]] = set()

    for rel, fi in infos.items():
        for node in ast.walk(fi.tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                continue
            if node.func.attr not in {"include_router", "register_blueprint"}:
                continue
            parent = resolve_router_ref(rel, node.func.value, infos, rv)
            if not parent or not node.args:
                continue
            child = resolve_router_ref(rel, node.args[0], infos, rv)
            if not child:
                continue
            edges.append((parent, child, _kwarg(node, PREFIX_KWARGS) or ""))
            children.add(child)

    all_routers = {(rel, var) for rel, fi in infos.items() for var in fi.routers}
    prefixes: dict[tuple[str, str], set[str]] = {r: set() for r in all_routers}
    for r in all_routers - children:
        prefixes[r].add("")
    for r in children:
        prefixes.setdefault(r, set())

    for _ in range(len(all_routers) + 1):
        changed = False
        for parent, child, pfx in edges:
            own = infos[parent[0]].routers[parent[1]]["prefix"]
            for base_pfx in list(prefixes.get(parent, {""})) or [""]:
                cand = base.join_paths(base_pfx, own, pfx)
                cand = "" if cand == "/" else cand
                if cand not in prefixes[child]:
                    prefixes[child].add(cand)
                    changed = True
        if not changed:
            break
    return {k: sorted(v) if v else [""] for k, v in prefixes.items()}


def _methods_kwarg(call: ast.Call) -> list[str]:
    for kw in call.keywords:
        if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple, ast.Set)):
            out = [_const_str(e) for e in kw.value.elts]
            return sorted({m.upper() for m in out if m})
    return []


def _extract_routes(infos: dict[str, _FileInfo], rv: _Resolver,
                    chain: dict[tuple[str, str], list[str]],
                    endpoints: list[dict], unresolved: list[dict]) -> None:
    for rel, fi in infos.items():
        for stmt in fi.tree.body:
            targets = []
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                targets.append((stmt.name, stmt))
            elif isinstance(stmt, ast.ClassDef):
                for sub in stmt.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        targets.append((f"{stmt.name}.{sub.name}", sub))
            for qual, node in targets:
                handler = base.symbol_id(rel, qual)
                for dec in node.decorator_list:
                    if not (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)):
                        continue
                    var = dec.func.value
                    ref = resolve_router_ref(rel, var, infos, rv)
                    if ref is None:
                        continue
                    var_label = var.id if isinstance(var, ast.Name) else ref[1]
                    attr = dec.func.attr
                    if attr in ROUTE_METHODS:
                        methods = [attr.upper()]
                    elif attr in {"route", "api_route"}:
                        methods = _methods_kwarg(dec) or ["GET"]
                    elif attr == "websocket":
                        methods = ["WS"]
                    else:
                        continue
                    if not dec.args or _const_str(dec.args[0]) is None:
                        unresolved.append({
                            "from": handler,
                            "expression": f"@{var_label}.{attr}(<非リテラル>)",
                            "reason": "dynamic",
                        })
                        continue
                    route = _const_str(dec.args[0])
                    own = infos[ref[0]].routers[ref[1]]["prefix"]
                    for pre in chain.get(ref, [""]):
                        full = base.join_paths(pre, own, route)
                        for m in methods:
                            endpoints.append({
                                "id": base.endpoint_id(m, full),
                                "protocol": "rest", "method": m,
                                "path_pattern": base.normalize_path_pattern(full),
                                "path_key": base.path_key(full),
                                "handler": handler,
                                "source": f"@{var_label}.{attr}",
                            })


def _extract_entrypoints(infos: dict[str, _FileInfo], entry_fns: set[str],
                         endpoints: list[dict]) -> None:
    """Lambda 等のハンドラ関数と、**その中の** cmd 分岐をエントリポイントとして出す。

    **分岐のエントリポイント化は `entrypoint_functions` に属する関数に限る。**
    合成シンボル(`<関数名>#<値>`)は分岐すべてに作るが(呼び出しの帰属に必要=§5.7。
    **`dispatch_guards` で宣言した分岐だけは作らない** — `_drop_declared_guards`)、
    エントリポイントにするのはハンドラの分岐だけである。内部ヘルパの分岐まで入口にすると、
    機能ではないもの(再試行ラッパ・URL を選ぶ関数など)が FT2「高」で機能表への行追加を
    要求してしまう。ハンドラ名が既定と違うプロジェクトは `entrypoint_functions` に足す。
    """
    for rel, fi in sorted(infos.items()):
        for name, sid in sorted(fi.functions.items()):
            if name in entry_fns:
                endpoints.append({
                    "id": f"handler {rel}::{name}", "protocol": "event", "method": "",
                    "path_pattern": "", "path_key": "", "handler": sid,
                    "source": f"def {name}",
                })
        for fnname, branches in sorted(fi.dispatch.items()):
            if fnname.split(".")[-1] not in entry_fns:
                continue
            for value, _body in branches:
                endpoints.append({
                    "id": f"dispatch {value} @ {rel}::{fnname}", "protocol": "event",
                    "method": "", "path_pattern": "", "path_key": "",
                    "handler": base.symbol_id(rel, f"{fnname}#{value}"),
                    "source": f"{fnname} の内部分岐",
                })


def _extract_console_scripts(root: Path, infos: dict[str, _FileInfo],
                             endpoints: list[dict]) -> None:
    """`pyproject.toml` の `[project.scripts]` / `[project.gui-scripts]` を入口として出す。

    **`console_scripts` が生む実行ファイルは、CLI として配られる Python プロジェクトの
    唯一の外からの入口である。**REST のルートと Lambda のハンドラだけを拾っていると、
    そうしたプロジェクトはエントリポイント 0 件になり、種別 `tool` の機能に対して
    CG6 が毎回「中」を出す(実測 2026-08-10。02 の分割定義・機能表・relations の3者は
    `tool` で一致していて、種別を変えても真になるものは何も無い状態だった)。
    到達可能性の起点にもなるので、`main` から辿れるだけのシンボルが CG2
    (到達不能コード候補)から正しく外れる。

    `entrypoint_functions` の設定で代用しない — あちらは関数名だけを見るので、
    同名の内部ヘルパまで入口に化ける。`pyproject.toml` は宣言そのものである。
    """
    path = root / "pyproject.toml"
    if tomllib is None or not path.is_file():
        return
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:                                    # 壊れた TOML で抽出全体を落とさない
        return
    project = data.get("project") or {}
    scripts = {**(project.get("scripts") or {}), **(project.get("gui-scripts") or {})}
    # `src/` レイアウト(`src/pkg/mod.py`)も素の配置(`pkg/mod.py`)も、末尾一致で同じに引ける。
    by_module = {rel[:-3].replace("/", ".").removesuffix(".__init__"): (rel, fi)
                 for rel, fi in infos.items() if rel.endswith(".py")}
    for name, target in sorted(scripts.items()):
        module, _, func = str(target).partition(":")
        if not func:
            continue
        hit = next((v for mod, v in sorted(by_module.items())
                    if mod == module or mod.endswith("." + module)), None)
        if hit is None:
            continue
        rel, fi = hit
        sid = fi.functions.get(func.split(".")[0])
        if not sid:
            continue
        endpoints.append({
            "id": f"console_script {name}", "protocol": "cli", "method": "",
            "path_pattern": name, "path_key": name, "handler": sid,
            "source": f'pyproject.toml [project.scripts] {name} = "{target}"',
        })


# --------------------------------------------------------------------------- 資源参照(P10)

def _res_str_parts(node) -> list:
    """文字列式を**リテラル片の並び**に分解する。非リテラル区間は None。

    `"caseDataTbl" + os.environ.get("HASHSALT","")` → `["caseDataTbl", None]`
    → `resources.norm_name` が `caseDataTbl{}` にする。実データで支配的な
    「リテラルの接頭辞 + 環境ごとの接尾辞」が、これで環境をまたいで一致する。
    """
    if isinstance(node, ast.Constant):
        return [node.value] if isinstance(node.value, str) else [None]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _res_str_parts(node.left) + _res_str_parts(node.right)
    if isinstance(node, ast.JoinedStr):
        out: list = []
        for v in node.values:
            out += _res_str_parts(v) if isinstance(v, ast.Constant) else [None]
        return out
    return [None]


def _res_env_var(node) -> str | None:
    """`os.environ["X"]` / `os.environ.get("X")` / `os.getenv("X")` の X を返す。"""
    if isinstance(node, ast.Subscript):
        val = node.value
        if isinstance(val, ast.Attribute) and val.attr == "environ":
            return _const_str(node.slice)
        return None
    if isinstance(node, ast.Call):
        fn = node.func
        if not isinstance(fn, ast.Attribute) or not node.args:
            return None
        if fn.attr == "get" and isinstance(fn.value, ast.Attribute) and fn.value.attr == "environ":
            return _const_str(node.args[0])
        if fn.attr in {"getenv", "environ"} and _root_name(fn.value) == "os":
            return _const_str(node.args[0])
    return None


def _res_name_expr(node, kind: str) -> tuple[str, str] | None:
    """資源名を表す式から (種別, 名前) を取る。

    式そのものが環境変数の読み出しなら `env:$VAR` として返す。実資源への解決は
    infra の `Environment.Variables` が引き受ける。ここで `$VAR` に落としておかないと、
    `Table(os.environ["AUDIT_TABLE"])` は名前が取れず**丸ごと消える**。
    """
    var = _res_env_var(node)
    if var:
        return ("env", f"${var}")
    name = res.norm_name(_res_str_parts(node))
    return (kind, name) if name else None


def _res_factory(call: ast.Call, factories: dict) -> tuple[str, str] | None:
    """`dynamodb.Table("x")` のような受け手生成呼び出しから (種別, 正規化名) を取る。"""
    fn = call.func
    attr = fn.attr if isinstance(fn, ast.Attribute) else (fn.id if isinstance(fn, ast.Name) else "")
    kind = factories.get(attr)
    if not kind or not call.args:
        return None
    return _res_name_expr(call.args[0], kind)


def _res_bindings(stmts, factories: dict, into: dict, bound: set) -> None:
    """`table = dynamodb.Table("x")` を「変数 → 資源」の束縛として集める。

    **束縛そのものは資源参照として出さない。** 出すのは実際の操作
    (`table.query(...)`)の側である。モジュール直下の生成を参照として数えると、
    ドライバモジュールの数だけ `<module>` 由来の参照が並び、どの機能にも
    属さない雑音になる(実データではこれが支配的な形だった)。
    """
    for stmt in stmts:
        if not isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            continue
        value = stmt.value
        if not isinstance(value, ast.Call):
            continue
        got = _res_factory(value, factories)
        if not got:
            continue
        targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
        for t in targets:
            if isinstance(t, ast.Name):
                into[t.id] = got
                bound.add(id(value))


def _res_scan(nodes, sid: str, bindings: dict, rcfg: dict,
              bound: set, out: list) -> None:
    """1シンボル分の資源参照を集める。同じものが重複しても `resources.collect` が畳む。"""
    kwargs, factories = rcfg["kind_by_kwarg"], rcfg["kind_by_factory"]

    def add(kind: str, name: str, access: str, conf: str, node) -> None:
        if name:
            out.append(res.make_ref(sid, kind, name, access, conf,
                                    _res_text(node)))

    for top in nodes:
        for node in ast.walk(top):
            var = _res_env_var(node)
            if var:
                # 環境変数を読んだこと自体は、その資源をどう使うかを何も言わない。
                # **黙って read にしない。** 使い方は操作の側(下)で決まる。
                add("env", f"${var}", "unknown", "確実", node)
                continue
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            op = fn.attr if isinstance(fn, ast.Attribute) else (
                fn.id if isinstance(fn, ast.Name) else "")

            for kw in node.keywords:                      # TableName= / Bucket= …
                kind = kwargs.get(kw.arg or "")
                if kind:
                    got = _res_name_expr(kw.value, kind)
                    if got:
                        add(got[0], got[1], res.access_of(op), "確実", node)

            if isinstance(fn, ast.Attribute):
                recv = fn.value
                if isinstance(recv, ast.Name) and recv.id in bindings:
                    kind, name = bindings[recv.id]        # table.query(...)
                    add(kind, name, res.access_of(op), "確実", node)
                elif isinstance(recv, ast.Call):          # .Table("x").put_item(...)
                    got = _res_factory(recv, factories)
                    if got:
                        add(got[0], got[1], res.access_of(op), "確実", node)

            if id(node) not in bound:                     # 束縛されない生成だけ
                got = _res_factory(node, factories)
                if got:
                    add(got[0], got[1], "unknown", "候補", node)


def _res_text(node) -> str:
    """根拠の1行表記。**引数は畳む。**

    引数まで書くと `table.query(KeyConditionExpression=..., ExclusiveStartKey=...)` の
    ような呼び出しが引数の違いだけで別行になり、同じ資源の同じ操作が何行にも増える
    (実データで1関数から4行出た)。資源と操作が分かればよい。
    """
    try:
        if isinstance(node, ast.Call):
            return f"{ast.unparse(node.func)}(…)"[:100]
        return ast.unparse(node)[:100]
    except Exception:                                    # pragma: no cover
        return "<式>"


# --------------------------------------------------------------------------- 入口

def extract(root: Path, cfg: dict, scope: Path | None = None) -> dict:
    lang_cfg = cfg["languages"]["python"]
    entry_fns = set(lang_cfg.get("entrypoint_functions", []))
    dispatch_vars = set(lang_cfg.get("dispatch_variables", []))
    # **宣言されたガード節**(実在しない入口を作る前段。`_drop_declared_guards` が正)
    guards = set(lang_cfg.get("dispatch_guards", []))
    guard_hits: set[str] = set()            # 実際に落とせた宣言(差が「効かなかった宣言」)
    skipped: dict = {}
    files, vendored = base.collect_files(root, cfg, lang_cfg["extensions"], scope, skipped)

    infos: dict[str, _FileInfo] = {}
    unresolved: list[dict] = []
    symbols: list[dict] = []

    for path in files:
        rel = path.resolve().relative_to(root).as_posix()
        try:
            with warnings.catch_warnings():
                # 対象コードの SyntaxWarning(不正なエスケープ等)を自分の出力に混ぜない
                warnings.simplefilter("ignore")
                tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=rel)
        except (SyntaxError, ValueError) as exc:
            unresolved.append({                      # NFR-4: 黙って落とさない
                "from": base.symbol_id(rel, MODULE_SYMBOL),
                "expression": f"<解析失敗: {exc}>"[:120], "reason": "dynamic",
            })
            continue
        fi = _FileInfo(rel, tree)
        _collect_imports(fi)
        fi.str_sets = _collect_str_sets(tree)
        infos[rel] = fi

    # 定義の収集は全ファイルを読んでから行う(名前付き集合の解決に import 先が要る)
    for fi in infos.values():
        _collect_defs(fi, symbols, dispatch_vars, _visible_str_sets(fi, infos),
                      guards, guard_hits)
        _collect_routers(fi)

    for fi in infos.values():
        _collect_module_level(fi)
        _collect_self_attrs(fi)

    rv = _Resolver(infos, symbols)
    edges: list[dict] = []
    resource_refs: list[dict] = []
    rcfg = res.cfg_of(cfg)
    external = 0

    for rel, fi in infos.items():
        # 資源の変数束縛はファイル単位。モジュール直下で作った受け手
        # (`table = dynamodb.Table("x")`)は、その中の全関数から見える。
        file_bindings: dict[str, tuple[str, str]] = {}
        bound_calls: set[int] = set()
        if rcfg["enabled"]:
            _res_bindings(fi.tree.body, rcfg["kind_by_factory"], file_bindings, bound_calls)
        units: list[tuple[str, str | None, object, list]] = []
        module_calls: list[ast.Call] = []
        for stmt in fi.tree.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                units.append((stmt.name, None, stmt, None))
            elif isinstance(stmt, ast.ClassDef):
                for sub in stmt.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        units.append((f"{stmt.name}.{sub.name}", stmt.name, sub, None))
                    else:
                        _walk_calls(sub, module_calls)
            else:
                if isinstance(stmt, ast.Call):
                    module_calls.append(stmt)
                _walk_calls(stmt, module_calls)

        if module_calls and base.symbol_id(rel, MODULE_SYMBOL) in rv.by_id:
            units.append((MODULE_SYMBOL, None, None, module_calls))

        for qual, cls, node, explicit in list(units):
            sid = base.symbol_id(rel, qual)
            branches = fi.dispatch.get(qual, [])
            branch_stmts = {id(s) for _v, body in branches for s in body}
            types, ext_vars = _local_types(node, rel, cls, rv, fi)
            ctx = _Ctx(rel, cls, fi, rv, _param_names(node), types, ext_vars)

            if explicit is not None:
                calls = explicit
                res_stmts: list = explicit
            elif branches:
                # 分岐の本文は合成シンボルに帰属させ、共通の前処理だけを本体に残す
                res_stmts = _without_branches(node.body, branch_stmts)
                calls = _stmt_calls(res_stmts)
            else:
                res_stmts = list(getattr(node, "body", []))
                calls = _stmt_calls(res_stmts)

            # デコレータは定義時に実行される呼び出しである — 本体だけを歩くと
            # `@retry(3)` の Call が辺にも未解決にも出ず、「空欄 = 呼び出し無し」
            # (callgraphs.md §5.5)の保証が黙って破れる。`@retry(3)` はその Call を、
            # 素形 `@app.task`(括弧なし)は `app.task(f)` 相当の Call を合成して数える。
            if node is not None and getattr(node, "decorator_list", None):
                dec_calls: list[ast.Call] = []
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Call):
                        dec_calls.append(dec)
                        _walk_calls(dec, dec_calls)      # 引数の中の Call も本体と同じ扱い
                    elif isinstance(dec, (ast.Name, ast.Attribute)):
                        dec_calls.append(ast.Call(func=dec, args=[], keywords=[]))
                calls = dec_calls + calls

            if rcfg["enabled"]:
                local = dict(file_bindings)
                _res_bindings(res_stmts, rcfg["kind_by_factory"], local, bound_calls)
                _res_scan(res_stmts, sid, local, rcfg, bound_calls, resource_refs)

            for call in calls:
                target, unres, is_external = _resolve_call(call, ctx)
                if target and target != sid:
                    edges.append({"from": sid, "to": target})
                elif unres:
                    rec = {"from": sid, "expression": _expr_text(call), "reason": unres["reason"]}
                    if unres.get("candidates"):
                        rec["candidates"] = unres["candidates"]
                    unresolved.append(rec)
                elif is_external:
                    external += 1

            for value, body in branches:
                bsid = base.symbol_id(rel, f"{qual}#{value}")
                edges.append({"from": sid, "to": bsid})
                if rcfg["enabled"]:
                    blocal = dict(file_bindings)
                    _res_bindings(body, rcfg["kind_by_factory"], blocal, bound_calls)
                    _res_scan(body, bsid, blocal, rcfg, bound_calls, resource_refs)
                for call in _stmt_calls(body):
                    target, unres, is_external = _resolve_call(call, ctx)
                    if target and target != bsid:
                        edges.append({"from": bsid, "to": target})
                    elif unres:
                        rec = {"from": bsid, "expression": _expr_text(call),
                               "reason": unres["reason"]}
                        if unres.get("candidates"):
                            rec["candidates"] = unres["candidates"]
                        unresolved.append(rec)
                    elif is_external:
                        external += 1

    endpoints: list[dict] = []
    chain = _router_chain_prefixes(infos, rv)
    _extract_routes(infos, rv, chain, endpoints, unresolved)
    _extract_entrypoints(infos, entry_fns, endpoints)
    _extract_console_scripts(root, infos, endpoints)

    out = base.sort_lang_result({
        "tier": 2,
        "extractor": "python-ast (stdlib)",
        "external_call_count": external,
        "symbols": symbols,
        "edges": edges,
        "endpoints": endpoints,
        "unresolved": unresolved,
        "vendored_dirs": vendored,
        "skipped_files": {
            **skipped,
            # **黙って外さない。** 落とした宣言と、**照合しなかった宣言**の両方を生成物へ出す
            # (綴り違い・コードから消えたガードを見逃さないため。独立検査 2026-08-25)。
            **({"guards": sorted(guard_hits)} if guard_hits else {}),
            **({"guard_misses": sorted(guards - guard_hits)} if guards - guard_hits else {}),
        },
    })
    out["resource_refs"] = res.sort_refs(resource_refs)
    return out
