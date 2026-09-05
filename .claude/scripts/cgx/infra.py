"""インフラ抽出器 — API Gateway / ALB のパス転送設定を読む。

規範: .claude/directions/callgraphs.md / 契約: callgraph-schema.json

**なぜ要るか**: サーバレス構成では、REST のパスがコードではなく**インフラ定義側**にある。
`Path: /pref` と `Handler: app.lambda_handler` を読んで初めて、
「`POST /pref` は `.../app.py::lambda_handler` に届く」が分かる。
言語側の抽出器だけでは、この辺は永久に埋まらない。

対応する形式:
  ・SAM / CloudFormation(YAML): Serverless::Function の Events、ApiGatewayV2::Route、
    ApiGateway::Method、ElasticLoadBalancingV2::ListenerRule
  ・OpenAPI: `x-amazon-apigateway-integration` を持つものだけ(持たないものは「契約」であって
    インフラではない。契約は check-contracts.py の担当)
  ・Terraform: python-hcl2 が入っていれば。無ければ**その旨を未解決として報告**する

出力は中間表現の `routing`(パス → 転送先)。言語側のシンボルとの結合は boundaries.py が行う。
"""

from __future__ import annotations

import posixpath
from pathlib import Path

from . import base
from . import resources as res

CFN_MARKERS = ("AWSTemplateFormatVersion", "Transform", "Resources")
LAMBDA_TYPES = {"AWS::Serverless::Function", "AWS::Lambda::Function"}
HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "ANY"}

# API 以外のイベントソース(P10)。**ここを読まないと、キュー・ストリーム・定時起動で
# 動く機能が「呼び出し元不明のエンドポイント」のまま宿題として残り続ける。**
# 値は (プロトコル, イベント源を指すプロパティ名) — プロパティが無い型は "" にする。
SAM_EVENT_SOURCES = {
    "Schedule": ("schedule", "Schedule"),
    "ScheduleV2": ("schedule", "ScheduleExpression"),
    "SQS": ("event", "Queue"),
    "SNS": ("event", "Topic"),
    "DynamoDB": ("event", "Stream"),
    "Kinesis": ("event", "Stream"),
    "S3": ("event", "Bucket"),
    "EventBridgeRule": ("event", "EventBusName"),
    "CloudWatchEvent": ("event", "EventBusName"),
    "Cognito": ("event", "UserPool"),
    "IoTRule": ("event", "Sql"),
    "MSK": ("event", "Stream"),
    "MQ": ("event", "Broker"),
}


def _yaml():
    import yaml

    class Loader(yaml.SafeLoader):
        pass

    # CloudFormation の短縮形(!Ref / !GetAtt / !Sub …)を素通しする。
    # これが無いと CFN テンプレートは1つも読めない。
    def passthrough(loader, suffix, node):
        if isinstance(node, yaml.ScalarNode):
            return f"!{suffix} {node.value}"
        if isinstance(node, yaml.SequenceNode):
            return f"!{suffix} " + ",".join(str(v) for v in loader.construct_sequence(node, True))
        return f"!{suffix}"

    Loader.add_multi_constructor("!", passthrough)
    return yaml, Loader


def _ref_name(value) -> str:
    """`!Ref Foo` / `!GetAtt Foo.Arn` から論理IDを取り出す。"""
    s = str(value or "")
    if s.startswith("!"):
        s = s.split(None, 1)[1] if " " in s else ""
    return s.split(".")[0].strip()


def _handler_hint(tpl_rel: str, props: dict) -> str:
    """CodeUri と Handler から、言語側のシンボルIDと同じ形の手掛かりを作る。

    `CodeUri: lambda/x` + `Handler: app.lambda_handler`
      → `<テンプレートのディレクトリ>/lambda/x/app.py::lambda_handler`
    Go や provided ランタイムのように Handler がバイナリ名の場合は CodeUri までにする。
    """
    handler = str(props.get("Handler") or "").strip()
    prefix = _code_prefix(tpl_rel, props)
    if not handler or "." not in handler:
        return prefix
    mod, _, func = handler.rpartition(".")
    runtime = str(props.get("Runtime") or "")
    if runtime.startswith(("python", "")) and mod:
        return f"{prefix}/{mod.replace('.', '/')}.py::{func}" if prefix else f"{mod}.py::{func}"
    return prefix


def _add(routing: list, kind: str, method: str, path: str, ttype: str,
         ref: str, hint: str, source: str) -> None:
    routing.append({
        "kind": kind,
        "match": {"method": (method or "ANY").upper(),
                  "path_pattern": base.normalize_path_pattern(path),
                  "path_key": base.path_key(path)},
        "target": {"type": ttype, "ref": ref, "handler_hint": hint},
        "source": source,
    })


# --------------------------------------------------------------------------- 資源(P10)

def _code_prefix(tpl_rel: str, props: dict) -> str:
    """この関数のコードが置かれているリポジトリ相対のディレクトリ。

    ハンドラをシンボルIDに結ぶためと、環境変数の束縛を「どのコードに効くか」で
    絞るために要る。**`..` を必ず畳む** — `CodeUri: ../svc/x` は SAM の普通の書き方で、
    畳まないと `infra/../svc/x/app.py::h` になって実シンボルに一致しない。
    """
    code = str(props.get("CodeUri") or props.get("Code") or "").strip().strip("/")
    tpl_dir = tpl_rel.rsplit("/", 1)[0] if "/" in tpl_rel else ""
    joined = "/".join(p for p in (tpl_dir, code) if p)
    return posixpath.normpath(joined).lstrip("./") if joined else ""


def _declared_resources(resources: dict) -> dict[str, tuple[str, str]]:
    """論理ID → (種別, 実名)。実名が引けなければ `#<論理ID>` を名前にする。

    **解決できなくても捨てない** — 論理IDそのものが結合のキーとして十分に働く
    (同じテーブルを指す2つの参照は、実名が分からなくても同じ論理IDに集まる)。
    """
    out: dict[str, tuple[str, str]] = {}
    for name, spec in sorted(resources.items()):
        if not isinstance(spec, dict):
            continue
        got = res.CFN_RESOURCE_TYPES.get(spec.get("Type", ""))
        if not got:
            continue
        kind, prop = got
        raw = str((spec.get("Properties") or {}).get(prop) or "").strip()
        out[name] = (kind, raw if raw and not raw.startswith("!") else f"#{name}")
    return out


def _res_target(value, declared: dict, require_declared: bool = False) -> tuple[str, str]:
    """CFN の値(`!Ref X` / `!GetAtt X.Arn` / ARN 文字列)を (種別, 名前) に寄せる。

    `require_declared` を立てると、**このテンプレートで資源として宣言されている論理ID**
    しか受け付けない。環境変数の束縛にはこれが要る — 実データでは
    `DEPLOY_ENV: !Ref DeployEnv`(Parameter)が普通にあり、未知の論理IDを資源と
    みなすと「全モジュールが触る資源」に化けて env_patterns の絞り込みも素通りする。
    """
    s = str(value or "").strip()
    if not s:
        return ("", "")
    if s.startswith("!"):
        logical = _ref_name(s)
        if logical in declared:
            return declared[logical]
        if require_declared:
            return ("", "")
        return ("other", f"#{logical}") if logical else ("", "")
    if require_declared:
        return ("", "")
    if s.startswith("arn:"):
        parts = s.split(":")
        kind = res.IAM_SERVICE_KINDS.get(parts[2] if len(parts) > 2 else "", "other")
        return (kind, parts[-1].split("/")[-1])
    return ("", "")


def _scan_iam(rel: str, fn_name: str, handler: str, props: dict, declared: dict,
              refs: list, wildcard: list) -> None:
    """IAM を**上界**として読む。使っている証拠ではなく、使える範囲である。

    `Resource: '*'` は資源を識別しないので使わない(**件数だけ数えて報告する**)。
    実データでは `dynamodb:*` × `Resource: '*'` が普通に出てきて、そのまま使うと
    「全機能が全資源を触る」という無意味な結合になる。
    """
    stmts: list = []
    for pol in props.get("Policies") or []:
        if isinstance(pol, dict):
            if isinstance(pol.get("Statement"), list):
                stmts += pol["Statement"]
            doc = pol.get("PolicyDocument") or {}
            if isinstance(doc, dict) and isinstance(doc.get("Statement"), list):
                stmts += doc["Statement"]
    for st in stmts:
        if not isinstance(st, dict) or st.get("Effect") != "Allow":
            continue
        actions = st.get("Action") or []
        actions = actions if isinstance(actions, list) else [actions]
        services = {str(a).split(":")[0] for a in actions}
        kinds = {res.IAM_SERVICE_KINDS[s] for s in services if s in res.IAM_SERVICE_KINDS}
        if not kinds:
            continue
        targets = st.get("Resource") or []
        targets = targets if isinstance(targets, list) else [targets]
        for t in targets:
            if str(t).strip() == "*":
                wildcard.append(f"{rel}::{fn_name}")
                continue
            kind, name = _res_target(t, declared)
            if not name:
                continue
            refs.append(res.make_ref(handler, kind if kind else sorted(kinds)[0], name,
                                     "permission", "候補",
                                     f"IAM: {', '.join(sorted(actions))[:60]} ({rel}::{fn_name})"))


# --------------------------------------------------------------------------- CFN / SAM

def _scan_cfn(rel: str, doc: dict, routing: list, out: dict) -> None:
    resources = doc.get("Resources") or {}
    if not isinstance(resources, dict):
        return
    declared = _declared_resources(resources)
    lambdas: dict[str, tuple[str, dict]] = {}
    for name, spec in resources.items():
        if isinstance(spec, dict) and spec.get("Type") in LAMBDA_TYPES:
            lambdas[name] = (name, spec.get("Properties") or {})

    for name, spec in sorted(resources.items()):
        if not isinstance(spec, dict):
            continue
        rtype = spec.get("Type", "")
        props = spec.get("Properties") or {}

        if rtype in LAMBDA_TYPES:
            hint = _handler_hint(rel, props)
            prefix = _code_prefix(rel, props)
            for ev_name, ev in sorted((props.get("Events") or {}).items()):
                if not isinstance(ev, dict):
                    continue
                etype = ev.get("Type") or ""
                ep = ev.get("Properties") or {}
                if etype in {"Api", "HttpApi"}:
                    _add(routing, "apigw", str(ep.get("Method") or "ANY"),
                         str(ep.get("Path") or "/"), "lambda", name,
                         hint, f"{rel}::{name}.Events.{ev_name}")
                    continue
                got = SAM_EVENT_SOURCES.get(etype)
                if not got:
                    continue
                protocol, prop = got
                src_kind, src_name = _res_target(ep.get(prop), declared) if prop else ("", "")
                label = src_name or str(ep.get(prop) or ev_name)
                out["event_sources"].append({
                    "type": etype, "protocol": protocol, "source": label,
                    "handler_hint": hint, "function": name,
                    "origin": f"{rel}::{name}.Events.{ev_name}"})
                if src_name and src_kind:
                    # 「この関数はこの資源から起動される」= 読み取り側の結合
                    out["resource_refs"].append(res.make_ref(
                        hint, src_kind, src_name, "read", "確実",
                        f"{etype} イベント源 ({rel}::{name}.Events.{ev_name})"))

            # 環境変数の束縛。コードの `os.environ["X"]` をここで実資源に寄せる
            env = ((props.get("Environment") or {}).get("Variables") or {})
            if isinstance(env, dict):
                for var, value in sorted(env.items()):
                    kind, rname = _res_target(value, declared, require_declared=True)
                    if rname:
                        out["env_bindings"].append({
                            "var": str(var), "kind": kind, "name": rname,
                            "prefix": prefix, "source": f"{rel}::{name}.Environment"})
            _scan_iam(rel, name, hint, props, declared,
                      out["resource_refs"], out["iam_wildcard"])

        elif rtype == "AWS::Events::Rule":
            expr = str(props.get("ScheduleExpression") or "").strip()
            for tgt in props.get("Targets") or []:
                if not isinstance(tgt, dict):
                    continue
                logical = _ref_name(tgt.get("Arn"))
                fprops = lambdas.get(logical, (None, {}))[1]
                if logical not in lambdas:
                    continue
                out["event_sources"].append({
                    "type": "Schedule" if expr else "EventBridgeRule",
                    "protocol": "schedule" if expr else "event",
                    "source": expr or name, "handler_hint": _handler_hint(rel, fprops),
                    "function": logical, "origin": f"{rel}::{name}"})

        elif rtype == "AWS::Lambda::EventSourceMapping":
            logical = _ref_name(props.get("FunctionName"))
            src_kind, src_name = _res_target(props.get("EventSourceArn"), declared)
            if logical in lambdas:
                fprops = lambdas[logical][1]
                hint = _handler_hint(rel, fprops)
                out["event_sources"].append({
                    "type": "EventSourceMapping", "protocol": "event",
                    "source": src_name or logical, "handler_hint": hint,
                    "function": logical, "origin": f"{rel}::{name}"})
                if src_name and src_kind:
                    out["resource_refs"].append(res.make_ref(
                        hint, src_kind, src_name, "read", "確実",
                        f"EventSourceMapping ({rel}::{name})"))

        elif rtype == "AWS::ApiGatewayV2::Route":
            key = str(props.get("RouteKey") or "")
            meth, _, path = key.partition(" ")
            target = _ref_name(props.get("Target"))
            _add(routing, "apigw", meth, path or "/", "other", target, "",
                 f"{rel}::{name}")

        elif rtype == "AWS::ApiGateway::Method":
            meth = str(props.get("HttpMethod") or "ANY")
            res_ref = _ref_name(props.get("ResourceId"))
            integ = props.get("Integration") or {}
            uri = str(integ.get("Uri") or "")
            _add(routing, "apigw", meth, f"/{res_ref}", "other", uri[:80], "",
                 f"{rel}::{name}(パスは論理IDから推定)")

        elif rtype == "AWS::ElasticLoadBalancingV2::ListenerRule":
            paths, host = [], ""
            for cond in props.get("Conditions") or []:
                if not isinstance(cond, dict):
                    continue
                if cond.get("Field") == "path-pattern":
                    vals = cond.get("Values") or (cond.get("PathPatternConfig") or {}).get("Values")
                    paths += [str(v) for v in (vals or [])]
                if cond.get("Field") == "host-header":
                    vals = cond.get("Values") or (cond.get("HostHeaderConfig") or {}).get("Values")
                    host = str((vals or [""])[0])
            tg = ""
            for act in props.get("Actions") or []:
                if isinstance(act, dict) and act.get("TargetGroupArn"):
                    tg = _ref_name(act["TargetGroupArn"])
            for p in paths or ["/*"]:
                entry_src = f"{rel}::{name}" + (f"(Host: {host})" if host else "")
                _add(routing, "alb", "ANY", p, "target-group", tg, "", entry_src)


# --------------------------------------------------------------------------- OpenAPI(apigw 統合つき)

def _scan_openapi(rel: str, doc: dict, routing: list) -> None:
    pre = ""
    for s in doc.get("servers") or []:
        url = str(s.get("url", ""))
        if url.startswith("/"):
            pre = url.rstrip("/")
            break
    for raw_path, item in (doc.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        for meth, op in item.items():
            if meth.upper() not in HTTP_METHODS or not isinstance(op, dict):
                continue
            integ = op.get("x-amazon-apigateway-integration") or {}
            uri = str(integ.get("uri") or "")
            _add(routing, "apigw", meth, base.join_paths(pre, str(raw_path)),
                 "lambda" if "lambda" in uri else "other", uri[:100],
                 str(op.get("x-impl") or ""), f"{rel}::{raw_path}")


# --------------------------------------------------------------------------- Terraform

def _scan_terraform(root: Path, files: list[Path], routing: list,
                    unresolved: list) -> None:
    try:
        import hcl2
    except ImportError:
        unresolved.append({
            "from": "docs/03-impl/callgraphs/infra.md::<terraform>",
            "expression": f"<Terraform {len(files)} ファイルを読めない>",
            "reason": "dynamic",
        })
        return
    for path in files:
        rel = path.relative_to(root).as_posix()
        try:
            with path.open(encoding="utf-8") as fh:
                doc = hcl2.load(fh)
        except Exception:
            continue
        for block in doc.get("resource", []):
            for rtype, bodies in block.items():
                for bname, body in bodies.items():
                    if rtype == "aws_apigatewayv2_route":
                        key = str(body.get("route_key") or "")
                        meth, _, p = key.partition(" ")
                        _add(routing, "apigw", meth, p or "/", "other",
                             str(body.get("target") or "")[:80], "", f"{rel}::{rtype}.{bname}")
                    elif rtype == "aws_lb_listener_rule":
                        conds = body.get("condition") or []
                        conds = conds if isinstance(conds, list) else [conds]
                        paths = []
                        for c in conds:
                            pp = (c or {}).get("path_pattern") or {}
                            paths += list((pp or {}).get("values") or [])
                        act = (body.get("action") or [{}])
                        act = act[0] if isinstance(act, list) else act
                        for p in paths or ["/*"]:
                            _add(routing, "alb", "ANY", str(p), "target-group",
                                 str(act.get("target_group_arn") or "")[:80], "",
                                 f"{rel}::{rtype}.{bname}")


# --------------------------------------------------------------------------- 入口

def extract(root: Path, cfg: dict, scope: Path | None = None) -> dict:
    lang_cfg = cfg["languages"]["infra"]
    skipped: dict = {}
    files, vendored = base.collect_files(root, cfg, lang_cfg["extensions"], scope, skipped)
    routing: list[dict] = []
    unresolved: list[dict] = []
    out: dict = {"event_sources": [], "env_bindings": [], "resource_refs": [],
                 "iam_wildcard": []}
    scanned = 0

    tf_files = [p for p in files if p.suffix == ".tf"]
    if tf_files:
        _scan_terraform(root, tf_files, routing, unresolved)
        scanned += len(tf_files)

    yaml, Loader = _yaml()
    for path in files:
        if path.suffix not in {".yaml", ".yml", ".json"}:
            continue
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        is_cfn = any(m in text for m in CFN_MARKERS) and "AWS::" in text
        is_openapi = "x-amazon-apigateway-integration" in text
        if not (is_cfn or is_openapi):
            continue                    # 素の OpenAPI は「契約」であってインフラではない
        try:
            doc = yaml.load(text, Loader=Loader) if path.suffix != ".json" else __import__("json").loads(text)
        except Exception as exc:
            unresolved.append({"from": f"{rel}::<file>",
                               "expression": f"<解析失敗: {exc}>"[:120], "reason": "dynamic"})
            continue
        if not isinstance(doc, dict):
            continue
        scanned += 1
        if is_cfn:
            _scan_cfn(rel, doc, routing, out)
        if is_openapi:
            _scan_openapi(rel, doc, routing)

    routing.sort(key=lambda r: (r["match"]["method"], r["match"]["path_key"], r["source"]))
    result = base.sort_lang_result({
        "tier": 2,
        "extractor": "infra (CFN/SAM/OpenAPI/Terraform)",
        "external_call_count": 0,
        "symbols": [],
        "edges": [],
        "endpoints": [],
        "unresolved": unresolved,
        "vendored_dirs": vendored,
        "skipped_files": skipped,
        "routing": routing,
        "scanned_files": scanned,
    })
    result["event_sources"] = sorted(
        out["event_sources"], key=lambda e: (e["protocol"], e["type"], e["source"],
                                             e["function"], e["origin"]))
    result["env_bindings"] = sorted(
        {(b["var"], b["kind"], b["name"], b["prefix"], b["source"])
         for b in out["env_bindings"]})
    result["env_bindings"] = [
        dict(zip(("var", "kind", "name", "prefix", "source"), t))
        for t in result["env_bindings"]]
    result["resource_refs"] = res.sort_refs(out["resource_refs"])
    result["iam_wildcard"] = len(set(out["iam_wildcard"]))
    return result
