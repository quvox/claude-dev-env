"""コールグラフ抽出器の共通基盤。

規範: .claude/directions/callgraphs.md
契約: .claude/scripts/callgraph-schema.json

ここに置くのは「抽出手段に依存しないもの」だけ:
設定の読み込み、対象ファイルの列挙、シンボルIDとパスの正規化、決定性のための整列。
"""

from __future__ import annotations

import json
import os
import re
import sys
from fnmatch import fnmatch
from pathlib import Path

# ベンダリングされた第三者ライブラリの目印。ヒットしたら**そのディレクトリ自身**を丸ごと
# 解析対象から外す。規範・既知ディレクトリ名を入れてはならない理由: .claude/directions/callgraphs.md §5.3。
# 既知ディレクトリ名(node_modules 等)と excludes の重複は _check_vendor_marker_overlap() が検査する。
DEFAULT_VENDOR_MARKERS = [
    "*.dist-info",      # Python: wheel/pip でインストールされた配布物
    "*.egg-info",
    "*.egg-link",
    "pyvenv.cfg",       # venv のルート(名前が任意でも pyvenv.cfg で検出できる)
    "modules.txt",       # Go: vendor/modules.txt(vendor/ 直下に置かれる)
    # Rust: cargo が展開した依存クレートの1つ1つの直下に置かれる目印。依存の置き場
    # (CARGO_HOME)をリポジトリの中に持つプロジェクトでは、ここで落とさないと第三者の
    # クレートが数万ファイル解析に入る(2026-10-31 に実測: `.cargo-home/registry` に約2万)
    ".cargo-ok",          # registry から展開したクレート
    ".cargo_vcs_info.json",
    ".cargo-checksum.json",  # `cargo vendor` の出力
]

CONFIG = ".claude/scripts/callgraph-config.json"
LOCAL_CONFIG = ".claude/scripts/callgraph-config.local.json"
KIT_VENV = ".claude/.venv"

# エンドポイントのパスパラメータ表記。照合キーを作るために {} へ潰す。
# FastAPI/Starlette: {id} / Flask: <int:id> / Gin,Echo: :id / ALB,APIGW: *
_PARAM_PATTERNS = [
    re.compile(r"^\{[^/]*\}$"),
    re.compile(r"^<[^/]*>$"),
    re.compile(r"^:[^/]+$"),
    re.compile(r"^\*+$"),
]


def find_root(start: Path | None = None) -> Path:
    cur = (start or Path.cwd()).resolve()
    for cand in [cur, *cur.parents]:
        if (cand / "CLAUDE.md").is_file() and (cand / ".claude").is_dir():
            return cand
    return cur


def ensure_kit_venv(root: Path | None = None) -> None:
    """キット専用 venv があり、今それで動いていなければ、そのインタプリタで自己再実行する。

    利用者(人間も AI も)が `python3 .claude/scripts/xxx.py` と打つだけで済むようにするため。
    venv を意識させると、必ずどこかで素の python3 で実行されて「依存が無い」と誤診断される。

    venv が無ければ何もしない — Python 抽出器は標準ライブラリだけで動くので、
    **依存ゼロの状態でも壊れない**のがこの体系の前提である。
    """
    root = root or find_root()
    venv = (root / KIT_VENV).resolve()
    py = venv / "bin" / "python3"
    if not py.is_file():
        return
    if Path(sys.prefix).resolve() == venv:
        return                                   # 既に venv の中
    if os.environ.get("CGX_NO_REEXEC"):
        return                                   # 意図的に素の環境で走らせたいとき
    os.execv(str(py), [str(py), *sys.argv])


def load_config(root: Path) -> dict:
    base_path = root / CONFIG
    if not base_path.is_file():
        raise SystemExit(f"エラー: 設定が無い: {CONFIG}")
    cfg = json.loads(base_path.read_text(encoding="utf-8"))
    local = root / LOCAL_CONFIG
    if local.is_file():
        loc = json.loads(local.read_text(encoding="utf-8"))
        for key in ("excludes", "test_markers", "tooling_markers",
                    "internal_roots", "source_roots", "vendor_markers"):
            if key in loc:
                cfg[key] = sorted(set(cfg.get(key, [])) | set(loc[key]))
        for key in ("output_dir", "include_tests", "include_tooling", "max_file_bytes"):
            if key in loc:
                cfg[key] = loc[key]
        for lang, spec in loc.get("languages", {}).items():
            cfg.setdefault("languages", {}).setdefault(lang, {}).update(spec)
        for section in ("features", "resources"):
            if section in loc:
                cfg.setdefault(section, {}).update(loc[section])
    _check_vendor_marker_overlap(cfg)
    return cfg


def _check_vendor_marker_overlap(cfg: dict) -> None:
    """vendor_markers に excludes と同名の既知ディレクトリ名を入れると、ヒットしたエントリの
    親ディレクトリが丸ごと消える(.claude/directions/callgraphs.md §5.3、
    .claude/improvements/KIT-vendor-marker-parent-exclusion.md)。再発を検査で捕まえる。"""
    excludes_names = {e.rstrip("/") for e in cfg.get("excludes", [])}
    markers = cfg.get("vendor_markers", DEFAULT_VENDOR_MARKERS)
    overlap = sorted(m for m in markers if "*" not in m and "?" not in m and m in excludes_names)
    if overlap:
        print(
            f"警告: vendor_markers と excludes に同名のエントリがある: {overlap}。"
            "vendor_markers 側のヒットは親ディレクトリを丸ごと除外する副作用があるので、"
            "既知のディレクトリ名は excludes だけに置くこと"
            "(.claude/directions/callgraphs.md §5.3)。",
            file=sys.stderr,
        )


def is_excluded(rel: str, excludes: list[str]) -> bool:
    return any(ex in rel for ex in excludes)


def is_test(rel: str, markers: list[str]) -> bool:
    """目印に当たるかを、**区切りを持たない目印だけ basename の接頭辞**として判定する。

    KIT-marker-substring-false-positives。単純な部分文字列照合だと、既定の `test_` が
    `src/contest_handler.py` や `src/latest_report.py` に当たって**本番コードを落とす**。
    除外は FT2(取りこぼし検出)より前の収集段階で起きるので、落ちたことに検査で気付けない。

    規則は目印の形で決まる(利用者が接頭辞と部分文字列を選べるようにするため):

    - 前後が `/` の目印(`/tests/` `/e2e/`)→ **ディレクトリセグメント**として一致。
      照合は `/` を足した `/{rel}` に対して行うので、**リポジトリ直下の `tests/` にも当たる**
      (KIT-leading-slash-dir-markers。`tests/conftest.py` が解析対象に残っていた)。
      `src/foo_e2e/x.ts` は `/e2e/` を含まないので当たらない。
    - それ以外で `/` か `.` を含む目印(`_test.` `.spec.` `.github/` `compose.yaml`)
      → **部分文字列**。区切りが入っているので誤爆しない。
    - どちらも含まない裸の目印(`test_` `Makefile`)→ **basename の接頭辞としてのみ**一致。
      `contest_handler.py` の basename は `test_` で始まらないので落ちなくなる
      (KIT-marker-substring-false-positives)。
    """
    name = rel.rsplit("/", 1)[-1]
    anchored = f"/{rel}"
    for m in markers:
        if len(m) > 1 and m.startswith("/") and m.endswith("/"):
            if m in anchored:
                return True
        elif "/" in m or "." in m:
            if m in rel:
                return True
        elif name.startswith(m):
            return True
    return False


def is_vendor_dir(entries: list[str], markers: list[str]) -> bool:
    """このディレクトリが第三者ライブラリの置き場かどうかを、中身の目印で判定する。"""
    return any(fnmatch(name, m) for name in entries for m in markers)


# ---- shell の字句走査(コメント除去とヒアドキュメント検出を1本の走査から出す)----
# KIT-shell-comment-strip / KIT-shell-heredoc-tracking。**落としすぎは致命的、落とし足りないのは
# 軽微**という非対称性で設計する: 実コードをコメントとして落とすと `}` `)` が消えて波括弧の
# 対応が崩れ、関数の範囲がファイル末尾まで暴走する。落とし損ねれば偽の辺が1本出るだけである。

_HEREDOC_STOP = set(" \t;&|<>()")


def scan_shell_line(line: str, drop_single_quoted: bool = True
                    ) -> tuple[str, list[tuple[str, bool]], bool]:
    r"""shell の1行を1回だけ走査し、(整えた行, ヒアドキュメントの終端語, 引用が閉じたか) を返す。

    `'…'` / `"…"` / `$( )` / `${ }` / `$(( ))` / 素の `(` を**スタック**で追う。
    `#` がコメントを始めるのは**単語の先頭**(行頭 / 空白 / `;&|(` の直後)にあり、かつ
    **引用・展開の外**にいるときだけ(`${#arr[@]}` / `$#` / `${v#pat}` / `"a # b"` の `#` は
    コメントではない)。ダブルクォートは中で `$( )` が効くので中身を落とさない。

    ヒアドキュメントは `<<` / `<<-` を引用・展開の外で見たときだけ開始とみなす
    (`<<<` はヒアストリングなので除く)。終端語は `EOF` / `'EOF'` / `"EOF"` / `\EOF` /
    連結(`'E'OF`)/ 空(`''`)を読む。返す真偽は「行末でスタックが空だったか」で、
    偽なら呼び出し元は**判断を放棄する**。
    """
    out: list[str] = []
    heredocs: list[tuple[str, bool]] = []
    stack: list[str] = []           # "'" / '"' / "$(" / "${" / "$((" / "("
    i, n = 0, len(line)
    word_start = True               # 次の文字が単語の先頭か

    def _in_quote() -> bool:
        return any(c in ("'", '"') for c in stack)

    while i < n:
        ch = line[i]
        top = stack[-1] if stack else ""

        if ch == "\\" and top != "'":
            out.append(line[i:i + 2])
            i += 2
            word_start = False
            continue

        if top == "'":
            if ch == "'":
                stack.pop()
                out.append(ch)
            elif not drop_single_quoted:
                out.append(ch)
            i += 1
            word_start = False
            continue

        # コメント: 単語の先頭 かつ 引用も展開も無いとき
        if ch == "#" and word_start and not stack:
            break

        if ch == "'":
            stack.append("'")
            out.append(ch)
            i += 1
            word_start = False
            continue
        if ch == '"':
            if top == '"':
                stack.pop()
            else:
                stack.append('"')
            out.append(ch)
            i += 1
            word_start = False
            continue

        if ch == "$" and line.startswith("$((", i):
            stack.append("$((")
            out.append("$((")
            i += 3
            word_start = False
            continue
        if ch == "$" and line.startswith("$(", i):
            stack.append("$(")
            out.append("$(")
            i += 2
            word_start = True       # `$( ` の直後は単語の先頭
            continue
        if ch == "$" and line.startswith("${", i):
            stack.append("${")
            out.append("${")
            i += 2
            word_start = False
            continue

        if ch == "(" and top != "'":
            stack.append("(")
            out.append(ch)
            i += 1
            word_start = True
            continue
        if ch == ")":
            if top == "$((" and line.startswith("))", i):
                stack.pop()
                out.append("))")
                i += 2
                word_start = False
                continue
            if top in ("$(", "("):
                stack.pop()
            out.append(ch)
            i += 1
            word_start = False
            continue
        if ch == "}":
            if top == "${":
                stack.pop()
            out.append(ch)
            i += 1
            word_start = False
            continue

        # ヒアドキュメント: 引用・展開・算術式の外だけ
        if ch == "<" and line.startswith("<<", i) and not _in_quote() and "$((" not in stack:
            if line.startswith("<<<", i):        # ヒアストリングは対象外
                out.append("<<<")
                i += 3
                word_start = False
                continue
            j = i + 2
            strip_tabs = False
            if j < n and line[j] == "-":
                strip_tabs = True
                j += 1
            while j < n and line[j] in " \t":
                j += 1
            delim_parts: list[str] = []
            got_any = False
            while j < n and line[j] not in _HEREDOC_STOP:
                c = line[j]
                if c in ("'", '"'):
                    q, j = c, j + 1
                    got_any = True
                    while j < n and line[j] != q:
                        delim_parts.append(line[j])
                        j += 1
                    j += 1                        # 閉じ引用を消費
                    continue
                if c == "\\" and j + 1 < n:
                    delim_parts.append(line[j + 1])
                    j += 2
                    got_any = True
                    continue
                delim_parts.append(c)
                j += 1
                got_any = True
            if got_any:
                heredocs.append(("".join(delim_parts), strip_tabs))
            out.append(line[i:j])
            i = j
            word_start = False
            continue

        out.append(ch)
        word_start = ch in " \t;&|("
        i += 1

    return "".join(out), heredocs, not stack


def strip_shell_noise(line: str) -> str:
    """shell の1行からコメントとシングルクォート文字列の中身を落とす(`scan_shell_line` の薄い包み)。

    **行内で閉じない引用・展開があれば、判断を放棄して原文をそのまま返す**
    (落としすぎるより落とさない)。
    """
    cleaned, _, balanced = scan_shell_line(line)
    return cleaned if balanced else line


def find_heredocs(line: str) -> list[tuple[str, bool]]:
    """この行が開くヒアドキュメントの (終端語, 先頭タブを剥がすか) を開いた順に返す。

    引用が閉じていない行は**何も返さない**(誤検出で以降の行を丸ごと解析対象から外すのが
    最悪の結果なので、検出しない側に倒す)。
    """
    _, heredocs, balanced = scan_shell_line(line, drop_single_quoted=False)
    return heredocs if balanced else []


def _read_shebang(path: Path) -> str:
    """先頭行を返す(`#!` で始まらなければ空文字)。読めないファイルは空文字。

    拡張子を持たない実行スクリプト(`claude-dev` / `scripts/vm` 等)を言語ごとに拾うための
    判定材料。**1行だけ**読む(巨大なバイナリを丸ごと読まないため)。
    """
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            first = f.readline(256)
    except OSError:
        return ""
    return first.rstrip("\n") if first.startswith("#!") else ""


def collect_files(root: Path, cfg: dict, extensions: list[str],
                  scope: Path | None = None,
                  skipped: dict | None = None,
                  filenames: list[str] | None = None,
                  shebangs: list[str] | None = None) -> tuple[list[Path], list[str]]:
    """(対象ファイル, ベンダリングとして除外したディレクトリ) を**辞書順で**返す。

    順序が実行ごとに揺れると決定性が壊れるので、必ず整列して返す。
    ベンダリングされた第三者ライブラリは**全言語共通で解析対象にしない**
    (.claude/directions/callgraphs.md §5.3)。除外したことは黙らず呼び出し元に返す。

    テストと開発ツール(Makefile / CI 定義 / compose 等)も解析対象にしない
    (判定基準は .claude/directions/features.md §0.1)。`skipped` に dict を渡すと
    `{"tests": [rel, ...], "tooling": [rel, ...]}` を積む — **黙って落とすと「網羅した」という
    誤読を生む**ので、呼び出し元はこれを index.md に出すこと。**パスまで出す**理由:
    目印の書き方を誤ると誤除外が起きうる(`is_test` の規則を参照)。
    件数だけでは誤除外を特定できない。

    `filenames` / `shebangs` は**拡張子を持たないファイル**を集めるための入口である
    (`Makefile`、`claude-dev` のような実行スクリプト)。`filenames` はファイル名の完全一致、
    `shebangs` は先頭行(`#!` 行)に対する正規表現。どちらも `extensions` との **OR** で判定する。
    既定は `None` = 従来どおり拡張子だけで集める(既存の呼び出し側の挙動を変えない)。
    """
    name_set = set(filenames or [])
    shebang_res = [re.compile(pat) for pat in (shebangs or [])]

    def _match(path: Path, fname: str) -> bool:
        """このファイルを対象にするか。拡張子 / ファイル名 / shebang の OR で判定する。"""
        if path.suffix in extensions:
            return True
        if fname in name_set:
            return True
        if shebang_res and not path.suffix:
            line = _read_shebang(path)
            return bool(line) and any(r.search(line) for r in shebang_res)
        return False

    excludes = cfg.get("excludes", [])
    test_markers = cfg.get("test_markers", [])
    tooling_markers = cfg.get("tooling_markers", [])
    vendor_markers = cfg.get("vendor_markers", DEFAULT_VENDOR_MARKERS)
    include_tests = cfg.get("include_tests", False)
    include_tooling = cfg.get("include_tooling", False)
    max_bytes = cfg.get("max_file_bytes", 1 << 20)
    roots = cfg.get("internal_roots") or ["."]

    seen: dict[str, Path] = {}
    vendored: set[str] = set()
    bases = [scope] if scope else [root / r for r in roots]

    for base_dir in bases:
        base_dir = base_dir.resolve()
        if not base_dir.exists():
            continue
        if base_dir.is_file():
            try:
                rel = base_dir.relative_to(root).as_posix()
            except ValueError:
                continue
            if _match(base_dir, base_dir.name) and not is_excluded(rel, excludes):
                # scope でファイルを名指しした場合は、明示的な指示として尊重する
                # (テスト/開発ツールのマーカーを適用しない。既存の挙動を変えない)
                seen[rel] = base_dir
            continue

        for dirpath, dirnames, filenames in os.walk(base_dir):
            here = Path(dirpath)
            try:
                rel_dir = here.relative_to(root).as_posix()
            except ValueError:
                dirnames[:] = []
                continue
            marker = "" if rel_dir == "." else rel_dir + "/"
            if marker and is_excluded(marker, excludes):
                dirnames[:] = []            # 降りない(node_modules を歩くだけで遅い)
                continue
            if is_vendor_dir([*dirnames, *filenames], vendor_markers):
                vendored.add(rel_dir)
                dirnames[:] = []
                continue
            dirnames.sort()                 # 決定性のため走査順も固定する
            for fname in sorted(filenames):
                path = here / fname
                if not _match(path, fname):
                    continue
                rel = f"{marker}{fname}"
                if is_excluded(rel, excludes):
                    continue
                if not include_tests and is_test(rel, test_markers):
                    if skipped is not None:
                        skipped.setdefault("tests", []).append(rel)
                    continue
                if not include_tooling and is_test(rel, tooling_markers):
                    if skipped is not None:
                        skipped.setdefault("tooling", []).append(rel)
                    continue
                try:
                    if path.stat().st_size > max_bytes:
                        continue
                except OSError:
                    continue
                seen[rel] = path

    return [seen[rel] for rel in sorted(seen)], sorted(vendored)


def symbol_id(rel_path: str, qualified_name: str) -> str:
    """`<repo相対パス>::<修飾名>`。**行番号は含めない**(決定性のため)。"""
    return f"{rel_path}::{qualified_name}"


def symbol_extensions(cfg: dict) -> set[str]:
    """シンボルを出す抽出器が、設定で有効になっていて名乗る拡張子の集合。

    **今回出たシンボルからは決めない** — それだと、抽出器の在る言語の最後のファイルを消した・
    改名しただけで、その拡張子の入口が全部「抽出器が無い」に化ける(独立検査の反例)。
    """
    from . import EXTRACTORS, NO_SYMBOLS
    out: set[str] = set()
    for lang, spec in (cfg.get("languages") or {}).items():
        if not spec.get("enabled") or lang not in EXTRACTORS or lang in NO_SYMBOLS:
            continue
        for e in (spec.get("extensions") or []):
            out.add(e if e.startswith(".") else "." + e)
    return out


def unextracted_symbol(sid: str, exts: set[str], cfg: dict,
                       root: Path | None = None) -> bool:
    """`sid` が**抽出器の無い言語のファイル**を指すシンボルIDか(KIT-callgraph-ft1-unsupported-lang)。

    そういう入口・`x-impl` は callgraph に無くて当然で、「実在しない」と言えば誤検出になる —
    **見られていないのではなく、見る道具が無い**。呼び出し側は照合せず「未検査」として数える。
    `exts` は `symbol_extensions(cfg)`。次のものは False を返し、従来どおり照合に回す:

    - `::` を持たない(エンドポイントID)・ファイル名に拡張子が無い — 判定できない
    - テスト・開発ツールの目印に当たる — FT1 が「機能ではない」と行き先を案内する相手である
    - そのファイルが無い — 消えた・綴りを誤った入口は FT1 のまま。**`root` を渡さなければ
      常に False**(実在を確かめられないなら照合する側へ倒す。省略で黙って未検査にしない)

    「言語」より少し広い — 実在する `.toml` や `.md` を指す入口も、シンボルを出す抽出器が無い
    ので未検査に入る。見る道具が無いことに変わりはないので、そう扱う。
    """
    if "::" not in sid:
        return False
    path = sid.split("::", 1)[0]
    name = path.rsplit("/", 1)[-1]
    if "." not in name or ("." + name.rsplit(".", 1)[-1]) in exts:
        return False
    if is_test(path, cfg.get("test_markers") or []) \
            or is_test(path, cfg.get("tooling_markers") or []):
        return False
    return root is not None and (root / path).is_file()


def normalize_path_pattern(path: str) -> str:
    """表示用のパス表記を整える(先頭スラッシュ・重複スラッシュ・末尾スラッシュ)。"""
    if not path:
        return "/"
    path = re.sub(r"/{2,}", "/", path)
    if not path.startswith("/"):
        path = "/" + path
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return path


def path_key(path: str) -> str:
    """照合用キー: パラメータ区間をすべて `{}` に潰す。

    FastAPI の `/users/{user_id}` と Gin の `/users/:user_id` と
    ALB の `/users/*` を同じキーにするためにある(directions/callgraphs.md §5.2)。
    """
    norm = normalize_path_pattern(path)
    out = []
    for seg in norm.split("/"):
        if any(p.match(seg) for p in _PARAM_PATTERNS):
            out.append("{}")
        else:
            out.append(seg)
    return "/".join(out) or "/"


def endpoint_id(method: str, path_pattern: str) -> str:
    return f"{(method or 'ANY').upper()} {normalize_path_pattern(path_pattern)}"


def endpoint_key(method: str, path_pattern: str) -> str:
    return f"{(method or 'ANY').upper()} {path_key(path_pattern)}"


def join_paths(*parts: str) -> str:
    joined = "/".join(p.strip("/") for p in parts if p and p.strip("/"))
    return normalize_path_pattern("/" + joined)


def sort_lang_result(result: dict) -> dict:
    """出力直前の整列。**コードポイント順**(ロケール非依存)で固定する。

    これを通っていない結果を出力してはならない — 決定性がここで担保される。
    """
    result["symbols"] = sorted(result.get("symbols", []), key=lambda s: s["id"])
    result["edges"] = sorted(
        {(e["from"], e["to"]) for e in result.get("edges", [])})
    result["edges"] = [{"from": f, "to": t} for f, t in result["edges"]]
    result["endpoints"] = sorted(result.get("endpoints", []),
                                 key=lambda e: (e["id"], e["handler"], e["source"]))
    for u in result.get("unresolved", []):
        if u.get("candidates"):
            u["candidates"] = sorted(set(u["candidates"]))
    # 同じ (呼び出し元, 式, 分類) は1行に畳む。行番号を持たないので重複が生じうる。
    dedup: dict[tuple, dict] = {}
    for u in result.get("unresolved", []):
        key = (u["from"], u["expression"], u["reason"])
        if key in dedup and u.get("candidates"):
            merged = sorted(set(dedup[key].get("candidates", [])) | set(u["candidates"]))
            dedup[key]["candidates"] = merged
        else:
            dedup.setdefault(key, u)
    result["unresolved"] = [dedup[k] for k in sorted(dedup)]
    return result


def escape_cell(value: str) -> str:
    """Markdown 表のセルとして安全な1行にする。"""
    if value is None or value == "":
        return "-"
    return str(value).replace("|", "\\|").replace("\n", " ").strip() or "-"


# --------------------------------------------------------------------------- 注記

# **注記は中身ではない。** 生成物の鮮度検査は全文一致で行うので、注記の文言を1字直すだけで
# 全プロジェクトの生成物が一斉に「古い」になっていた(実測: 注記1文字で7ファイル)。
# 注記を明示のマーカーで囲い、鮮度検査はそこを除いて比べる
# (KIT-generated-note-churns-every-artifact)。
#
# **`GENERATED` マーカー(build-index.py)とは仕事が違う。** あちらは「手書きの文書へ差し込む
# 生成部」を囲う。こちらは「全体が生成物のファイルの中で、**比較から外す注記**」を囲う。
# 囲う対象が逆なので、名前を分けている。
def note_markers(tool: str) -> tuple[str, str]:
    return (f"<!-- BEGIN NOTE: {tool} -->", f"<!-- END NOTE: {tool} -->")


NOTE_RE = re.compile(r"<!-- BEGIN NOTE: [\w./-]+ -->.*?<!-- END NOTE: [\w./-]+ -->\n?", re.S)


def without_note(text: str) -> str:
    """鮮度検査が比べる部分を返す(注記を除いたもの)。

    frontmatter は**中身**である(`symbols:` などコードで変わる)ので除かない。
    """
    return NOTE_RE.sub("", text)


def wrap_note(tool: str, body: str) -> str:
    """注記をマーカーで囲う。書くときは常に最新の注記を書くので、古いまま固定されない。"""
    begin, end = note_markers(tool)
    return f"{begin}\n{body}\n{end}"
