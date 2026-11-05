"""共有データストア結合(P10)— 呼び出し辺の無い連携を機械で拾う。

規範: .claude/directions/callgraphs.md §5.11 / 設計: .claude/scripts/callgraph-design.md §9

**サーバレス/イベント駆動では、連携の相当部分が呼び出し辺として原理的に存在しない。**
A がテーブルに書き、B が読む。呼び出しは1本も無いが、B は A の書式に依存している。
この結合は callgraph にも boundaries にも出ないので、CG4(取りこぼし検出)の網に
一切かからない。ここはその穴を埋める。

中心にあるのは1つの判断である:

  **資源の識別子は「触り方の名前」でよい。**
  文字列リテラルでも、環境変数名でも、定数名でもよい。実名に解決できたらそちらに寄せるが、
  **解決できなくても捨てない** — 同じ環境変数を読む2つのモジュールは、実体が何であれ結合して
  いる。これは「偽陰性より偽陽性の方がマシ」(directions/features.md §5)に対する正しい
  振る舞いであり、かつ最も安上がりでもある。
"""

from __future__ import annotations

from collections import defaultdict
from fnmatch import fnmatch

# 操作名 → アクセス種別。**言語をまたいで同じ語彙で判定する** — SDK もリポジトリ内の
# ラッパも、動詞は驚くほど共通している(get/put/query/scan/publish/send)。
# 照合は「小文字化して `_` を落とし、最長の接頭辞で決める」。
_ACCESS_PREFIXES = (
    ("batchget", "read"), ("batchwrite", "write"),
    ("transactget", "read"), ("transactwrite", "write"),
    ("describe", "read"), ("download", "read"), ("upload", "write"),
    ("get", "read"), ("query", "read"), ("scan", "read"), ("list", "read"),
    ("head", "read"), ("read", "read"), ("load", "read"), ("fetch", "read"),
    ("select", "read"), ("count", "read"), ("exists", "read"), ("receive", "read"),
    ("find", "read"), ("search", "read"),
    ("put", "write"), ("update", "write"), ("delete", "write"), ("write", "write"),
    ("create", "write"), ("save", "write"), ("insert", "write"), ("upsert", "write"),
    ("send", "write"), ("publish", "write"), ("copy", "write"), ("remove", "write"),
    ("add", "write"), ("append", "write"), ("archive", "write"), ("purge", "write"),
    ("register", "write"), ("store", "write"),
)
_ACCESS_SORTED = tuple(sorted(_ACCESS_PREFIXES, key=lambda kv: -len(kv[0])))

# 引数の名前から資源の種別が決まるもの(AWS SDK の共通語彙)。
DEFAULT_KIND_BY_KWARG = {
    "TableName": "dynamodb", "SourceTableName": "dynamodb", "TargetTableName": "dynamodb",
    "Bucket": "s3", "BucketName": "s3",
    "QueueUrl": "sqs", "QueueName": "sqs",
    "TopicArn": "sns", "TopicName": "sns",
    "StreamName": "kinesis", "DeliveryStreamName": "kinesis",
}
# 受け手を作る呼び出し(`dynamodb.Table("x")` / `s3.Bucket("y")`)。
DEFAULT_KIND_BY_FACTORY = {
    "Table": "dynamodb", "Bucket": "s3", "Queue": "sqs", "Topic": "sns",
    "get_queue_by_name": "sqs",
}
# 実資源に解決できなかった環境変数のうち、**資源とみなすもの**。
# ここで絞らないと `DEPLOY_ENV` / `LOG_LEVEL` のような全モジュールが読む変数が
# 「全機能が触る資源」になり、信号が雑音に埋もれる(P1.5 で学んだのと同じ失敗)。
# **絞った分は必ず件数を報告する**(黙った偽陰性を作らない)。
DEFAULT_ENV_PATTERNS = (
    "*TABLE*", "*BUCKET*", "*QUEUE*", "*TOPIC*", "*STREAM*", "*_ARN", "*ARN_*",
    "*DATABASE*", "*_DB", "DB_*", "*_DSN", "*ENDPOINT*", "*_URL", "*URI*",
)
# CFN の資源型 → 種別 と、実名を持つプロパティ名。
CFN_RESOURCE_TYPES = {
    "AWS::DynamoDB::Table": ("dynamodb", "TableName"),
    "AWS::Serverless::SimpleTable": ("dynamodb", "TableName"),
    "AWS::S3::Bucket": ("s3", "BucketName"),
    "AWS::SQS::Queue": ("sqs", "QueueName"),
    "AWS::SNS::Topic": ("sns", "TopicName"),
    "AWS::Kinesis::Stream": ("kinesis", "Name"),
}
# IAM の Action 接頭辞 → 種別。
IAM_SERVICE_KINDS = {"dynamodb": "dynamodb", "s3": "s3", "sqs": "sqs",
                     "sns": "sns", "kinesis": "kinesis"}


def cfg_of(cfg: dict) -> dict:
    r = dict(cfg.get("resources") or {})
    r.setdefault("enabled", True)
    r.setdefault("kind_by_kwarg", DEFAULT_KIND_BY_KWARG)
    r.setdefault("kind_by_factory", DEFAULT_KIND_BY_FACTORY)
    r.setdefault("env_patterns", list(DEFAULT_ENV_PATTERNS))
    r.setdefault("const_name_patterns", ["Table*", "Bucket*", "Queue*", "Topic*", "Stream*"])
    r.setdefault("const_type_patterns", ["TableName", "BucketName", "QueueName", "TopicName"])
    # 「広域共有資源」の閾値。**指摘の絞り込みにしか効かない**(資源表そのものは閾値に依存しない)。
    # 割合だけで判定すると、機能が3件しかないリポジトリで「2機能が触る = 67%」が
    # 広域扱いになって指摘が全部消える。**絶対数の下限を必ず併用する。**
    r.setdefault("ubiquitous_ratio", 0.5)
    r.setdefault("ubiquitous_min", 8)
    r.setdefault("pairs_shown", 6)
    return r


# --------------------------------------------------------------------------- 名前

def access_of(op: str) -> str:
    """操作名からアクセス種別を決める。分からなければ `unknown`(黙って read にしない)。"""
    key = (op or "").lower().replace("_", "")
    for prefix, access in _ACCESS_SORTED:
        if key.startswith(prefix):
            return access
    return "unknown"


def merge_access(a: str, b: str) -> str:
    if a == b:
        return a
    used = {a, b} - {"permission", "unknown"}
    if "readwrite" in used or used == {"read", "write"}:
        return "readwrite"
    if used:
        return used.pop()
    return "unknown" if "unknown" in {a, b} else "permission"


def norm_name(parts: list) -> str:
    """リテラル片の並びを1つの正規化名にする。**非リテラル区間は `{}` に潰す**。

    `"multiCaseMemberTbl" + os.environ.get("HASHSALT","")` → `multiCaseMemberTbl`

    ★ **先頭と末尾の `{}` は落とす。** 実データで支配的なのは「リテラル名 + 環境ごとの
      接頭辞/接尾辞」であり、同じ資源が片方では `orders`、もう片方では `orders{}` と
      出ると**同じテーブルが別資源に割れて結合が消える**。落とすことで一致する。
      内側の `{}` は落とさない(`a{}b` と `ab` は別物とみなす)。
      エンドポイントの `path_key`(§5.2)と同じ考え方であり、同じ記号を使う。
    """
    out: list[str] = []
    for p in parts:
        if p is None:
            if not out or out[-1] != "{}":
                out.append("{}")
        elif p != "":
            out.append(str(p))
    name = "".join(out).strip()
    while name.startswith("{}"):
        name = name[2:].lstrip("-_./:")
    while name.endswith("{}"):
        name = name[:-2].rstrip("-_./:")
    return name


def make_ref(symbol: str, kind: str, name: str, access: str,
             confidence: str, evidence: str) -> dict:
    return {"symbol": symbol, "kind": kind, "name": name, "access": access,
            "confidence": confidence, "evidence": evidence}


def key_of(ref: dict) -> str:
    return f"{ref['kind']}:{ref['name']}"


_REF_FIELDS = ("symbol", "kind", "name", "access", "confidence", "evidence")


def sort_refs(refs: list[dict]) -> list[dict]:
    """抽出器の出口で重複を落として整列する(base.sort_lang_result と同じ役割)。"""
    uniq = {tuple(r[f] for f in _REF_FIELDS) for r in refs}
    return [dict(zip(_REF_FIELDS, t)) for t in sorted(uniq)]


# --------------------------------------------------------------------------- 解決

def _resolve_env(refs: list[dict], env_bindings: list[dict]) -> tuple[list[dict], int]:
    """`env:$VAR` を infra の `Environment.Variables` で実資源に寄せる。

    まず**そのシンボルのパスを含む CodeUri 配下の束縛**を探し(Lambda を1関数1
    ディレクトリに置く構成ならこれで当たる)、無ければ**全体で一意に決まる場合だけ**
    使う。後者は確度を上げないための妥協ではなく、共有ドライバのように CodeUri の外に
    置かれたコードを取りこぼさないための選択である(「無い」の主張は広く)。
    """
    by_var: dict[str, set[tuple[str, str]]] = defaultdict(set)
    scoped: dict[str, list[tuple[str, str, str, str]]] = defaultdict(list)
    for b in env_bindings:
        if not b.get("kind"):
            continue
        by_var[b["var"]].add((b["kind"], b["name"]))
        scoped[b["var"]].append((b.get("prefix", ""), b["kind"], b["name"], b["source"]))

    resolved = 0
    out: list[dict] = []
    for ref in refs:
        if ref["kind"] != "env" or not ref["name"].startswith("$"):
            out.append(ref)
            continue
        var = ref["name"][1:]
        path = ref["symbol"].split("::", 1)[0]
        hit = None
        for prefix, kind, name, source in sorted(scoped.get(var, [])):
            if prefix and path.startswith(prefix):
                hit = (kind, name, source)
                break
        if hit is None and len(by_var.get(var, ())) == 1:
            kind, name = next(iter(by_var[var]))
            source = sorted(s for _p, k, n, s in scoped[var] if (k, n) == (kind, name))[0]
            hit = (kind, name, source)
        if hit is None:
            out.append(ref)
            continue
        kind, name, source = hit
        resolved += 1
        out.append(make_ref(ref["symbol"], kind, name, ref["access"], "候補",
                            f"{ref['evidence']} → {kind}:{name}(環境変数 {var} / {source})"))
    return out, resolved


def _keep_env(name: str, patterns: list[str]) -> bool:
    var = name[1:] if name.startswith("$") else name
    return any(fnmatch(var.upper(), p.upper()) for p in patterns)


# --------------------------------------------------------------------------- 集約

def collect(result: dict, cfg: dict) -> tuple[list[dict], dict]:
    """中間表現から `resources[]` を組み立てる。(資源, 統計) を返す。

    入力は抽出器が積んだ `_resource_refs` / `_env_bindings`。どちらも最上位の一時キーで、
    ここで消費される(`_http_calls` と同じ扱い)。
    """
    rcfg = cfg_of(cfg)
    refs: list[dict] = list(result.get("_resource_refs", []))
    env_bindings: list[dict] = list(result.get("_env_bindings", []))
    stats: dict = {"raw_refs": len(refs), "env_bindings": len(env_bindings),
                   "iam_wildcard": int(result.get("_iam_wildcard", 0))}

    refs, resolved = _resolve_env(refs, env_bindings)
    stats["env_resolved"] = resolved

    kept: list[dict] = []
    dropped: dict[str, int] = defaultdict(int)
    for ref in refs:
        if not ref.get("name"):
            continue
        if ref["kind"] == "env" and not _keep_env(ref["name"], rcfg["env_patterns"]):
            dropped[ref["name"].lstrip("$")] += 1
            continue
        kept.append(ref)
    stats["dropped_env"] = sum(dropped.values())
    stats["dropped_env_names"] = sorted(dropped.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
    stats["dropped_env_distinct"] = len(dropped)

    grouped: dict[str, dict] = {}
    for ref in kept:
        key = key_of(ref)
        entry = grouped.setdefault(key, {"key": key, "kind": ref["kind"],
                                         "name": ref["name"], "_refs": {}})
        # 同じ (シンボル, 根拠) は1本に畳む。行番号を持たないので重複が生じうる。
        rk = (ref["symbol"], ref["evidence"])
        prev = entry["_refs"].get(rk)
        if prev is None:
            entry["_refs"][rk] = dict(ref)
        else:
            prev["access"] = merge_access(prev["access"], ref["access"])
            if prev["confidence"] != "確実" and ref["confidence"] == "確実":
                prev["confidence"] = "確実"

    resources: list[dict] = []
    for key in sorted(grouped):
        entry = grouped[key]
        rows = [entry["_refs"][rk] for rk in sorted(entry["_refs"])]
        rows.sort(key=lambda r: (r["symbol"], r["access"], r["evidence"]))
        resources.append({"key": key, "kind": entry["kind"], "name": entry["name"],
                          "refs": [{"symbol": r["symbol"], "access": r["access"],
                                    "confidence": r["confidence"], "evidence": r["evidence"]}
                                   for r in rows]})

    stats["resources"] = len(resources)
    stats["refs"] = sum(len(r["refs"]) for r in resources)
    stats["unresolved_names"] = sum(1 for r in resources
                                    if r["name"].startswith(("$", "#")) or "{}" in r["name"])
    return resources, stats


# --------------------------------------------------------------------------- 機能への畳み込み

def couplings(cluster: dict, cg: dict, cfg: dict) -> dict:
    """資源ごとに「触る機能」を出し、**呼び出し辺で繋がっていない機能対**を数える。

    ★ 出力は**資源ごとに1行**である。機能対を全部並べると資源1つで O(n²) 行になり、
      実データでは読めない大きさになる。対の総数は必ず出し、代表だけを表示する。

    ★ `permission`(IAM 由来)は結合に数えない。**使っている証拠ではなく使える上界**であり、
      混ぜると「権限があるだけ」の対が指摘に化ける。資源表には残す。
    """
    rcfg = cfg_of(cfg)
    resources = cg.get("resources", [])
    closure = cluster.get("closure", {})
    # 分母は**辿れた機能だけ**。入口が抽出器の無い言語で未検査の機能(closure が空)を数えると、
    # 辿れた機能の大半が触る資源でも広域共有の比率に届かず、CG7 の抑止が効かなくなる
    total_features = sum(1 for fid in cluster.get("features", []) if closure.get(fid)) or 1

    sym_feats: dict[str, set[str]] = defaultdict(set)
    for fid, syms in sorted(closure.items()):
        for s in syms:
            sym_feats[s].add(fid)

    linked: set[tuple[str, str]] = set()
    for e in cluster.get("edges", []):
        linked.add((e["from"], e["to"]))
        linked.add((e["to"], e["from"]))

    rows: list[dict] = []
    orphan_refs = 0
    for r in resources:
        by_feat: dict[str, str] = {}
        for ref in r["refs"]:
            if ref["access"] == "permission":
                continue
            fids = sym_feats.get(ref["symbol"], ())
            if not fids:
                orphan_refs += 1
                continue
            for fid in fids:
                by_feat[fid] = merge_access(by_feat.get(fid, "unknown"), ref["access"])
        if len(by_feat) < 2:
            continue
        feats = sorted(by_feat)
        pairs = [(a, b) for i, a in enumerate(feats) for b in feats[i + 1:]
                 if (a, b) not in linked]
        writers = [f for f in feats if by_feat[f] in {"write", "readwrite"}]
        ubiquitous = (len(feats) >= int(rcfg["ubiquitous_min"])
                      and len(feats) / total_features >= float(rcfg["ubiquitous_ratio"]))
        rows.append({
            "key": r["key"], "kind": r["kind"], "name": r["name"],
            "features": {f: by_feat[f] for f in feats},
            "writers": writers,
            "readers": [f for f in feats if by_feat[f] in {"read", "readwrite"}],
            "unlinked_pairs": pairs,
            "ubiquitous": ubiquitous,
            # 書き込みが絡む結合は「片方の書式に他方が依存する」ので中。
            # 読み取りだけなら共有された読み取りモデルであり、参考に落とす。
            "severity": ("参考" if not writers else "中"),
        })

    rows.sort(key=lambda r: (-len(r["unlinked_pairs"]), r["key"]))
    findings = [r for r in rows if r["unlinked_pairs"] and not r["ubiquitous"]]
    return {
        "resources": rows,
        "findings": findings,
        "orphan_refs": orphan_refs,
        "counts": {
            "coupled_resources": len(rows),
            "finding_resources": len(findings),
            "ubiquitous": sum(1 for r in rows if r["ubiquitous"]),
            "unlinked_pairs": sum(len(r["unlinked_pairs"]) for r in rows),
            "orphan_refs": orphan_refs,
        },
    }
