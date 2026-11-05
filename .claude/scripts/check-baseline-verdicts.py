#!/usr/bin/env python3
"""過去の構築記録の `非該当` を、クロージャの中身に照らして疑う計器。

`baseline.md` §1 の1 は、基本要件の適用を**宣言したクロージャに対して**判定することを
求めている。だが判定は `/build` 段1 で、クロージャを宣言したのと同じ息で書かれるため、
書き手は「このタスクが**何を足したか**」を見ており、「宣言したクロージャに**何が在るか**」を
見ていない。両者が食い違うのは、クロージャが**ファイルまるごと**を含むときである。

**これが生まれる前、`verified` になった過去の記録は誰の目にも入らなかった。**
その隙間で、同型の誤りが9度再発した(うち2度は「直したつもりで隣を見落とした」型である)。

これはその隙間を埋める目であり、**全状態の記録を読む**(`verified` を含む。そこが要点である)。
**誰が何を見るかの分担は `baseline.md` §1 の4 が正である — ここでは言い直さない。**

★ 過去の記録は**その記録の `commit:` 時点の中身**に照らす。いまの作業ツリーに照らすと、
  後から同じファイルへ機能が増えれば偽陽性になり、移動・削除されれば見逃しになる。
  `commit:` が無い/引けないときだけ作業ツリーへ落とし、そのことを数えて印字する。

これは**計器である**(`.claude/directions/core.md` §3)。数えて印字するだけで、疑いの有無では何も拒まない。
拒むのは及第ライン(`stamps.py check`)だけであり、疑いは裁定ではない — 裁定は人間か F3 が行う。

★ 取りこぼしを数える: 疑いの件数だけでなく、**検査できなかった行**(パターン未設定の BR、
走査できるファイルがクロージャに1つも無い行)と、**部分的にしか検査できていない行**
(**証拠が見つからず、かつ**クロージャの一部を実物へ解決できなかった行 — 疑いが立った行は
既に名指されているので数えない)も必ず印字する。
1件を指して終わる計器は、その隣を見落としたことを黙る。

使い方:
    python3 .claude/scripts/check-baseline-verdicts.py              # 全記録
    python3 .claude/scripts/check-baseline-verdicts.py <slug|path>  # 1記録
    python3 .claude/scripts/check-baseline-verdicts.py --state verified
    python3 .claude/scripts/check-baseline-verdicts.py --worktree   # commit を見ず作業ツリー
    python3 .claude/scripts/check-baseline-verdicts.py --quiet      # 要約だけ
    python3 .claude/scripts/check-baseline-verdicts.py --selftest

★ 裁定の控え: 疑いは裁定ではないので、**裁定し終えた行を控える口**を持つ
(`baseline-evidence.json` / `.local.json` の `adjudicated`)。これが無いと、
覆らなかった同じ疑いが毎回の F3 で全件出てきて、**新しい疑いがその中に埋もれる**
(実測 2026-09-01: 22行が2回続けて同じ裁定を要求した)。`skip_globs` はファイル単位
なので行単位の裁定には使えない。書き方は1件につき1つの表:

    "adjudicated": [
      {"record": "2026-08-31-relay-teardown.md", "br": "BR-06",
       "path": "src/stream/*.go", "pattern": "crypto/rand",
       "match": "crypto/rand",
       "why": "内部管理用のセッション名の生成で、利用者の秘密ではない"}
    ]

`record` と `br` は必須、`path` / `pattern` / `match` は省略時 `*`。
**`record` と `path` はグロブ、`pattern` と `match` は完全一致**(`*` だけが「どれでも」)。
`pattern` は当たった証拠の正規表現、`match` はそこに当たった文字列で、**どちらもこの計器が
印字するものをそのまま写す。** 省くとそのパスのその BR を丸ごと黙らせるので、
1つのファイルに無害な一致と本物の一致が同居することを考えて、**既定に頼らず書くこと。**
**`why` が空の項目は適用しない**(理由の無い黙らせは、次に読む者が覆せない)。
外した行数は必ず印字する — **黙って消すことはしない。**

終了コード: 0=疑いの有無によらず正常に走った(計器) 2=使い方・前提エラー
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from fnmatch import fnmatch
from pathlib import Path, PurePosixPath

RECORDS = Path("docs/build-records")
BASELINE = Path(".claude/directions/baseline.md")
CONFIG = Path(".claude/scripts/baseline-evidence.json")
LOCAL = Path(".claude/scripts/baseline-evidence.local.json")

BR_ROW = re.compile(r"^\|\s*\**\s*(BR-\d{2})\s*\**\s*\|")
# 先頭の `.` を許す — `.env.example` や `.github/workflows/ci.yml` は普通のクロージャの
# 構成要素であり、これを弾くと**黙って走査から落ちる**(実測: 10件が落ちていた)
CLOSURE_PATH = re.compile(r"^[-*]\s+`([^`]+)`|^[-*]\s+(\S+)")
CLOSURE_BARE = re.compile(r"[\w.][\w./+-]*\Z")
PRUNE = {".git", "node_modules", "vendor", "dist", "build", "__pycache__",
         ".venv", "venv", "target", ".next", "coverage"}
MAX_BYTES = 2_000_000


def find_root(start: Path) -> Path:
    cur = start.resolve()
    for cand in (cur, *cur.parents):
        if (cand / "CLAUDE.md").is_file() and (cand / ".claude").is_dir():
            return cand
    return cur


def load_config(root: Path) -> tuple[dict, dict, dict, list[str], list[dict]]:
    """既定 + local を和集合でマージ(critical-config.json と同じ考え方)。

    返すのは (evidence, weak, context, skip_globs, adjudicated)。
    """
    raw: dict[str, dict[str, list]] = {"evidence": {}, "weak": {}, "context": {}}
    skips: list[str] = []
    adj: list[dict] = []
    for rel in (CONFIG, LOCAL):
        path = root / rel
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            print(f"警告: {rel} を読めない({e})", file=sys.stderr)
            continue
        for grp in raw:
            for br, pats in (data.get(grp) or {}).items():
                if isinstance(pats, list):
                    raw[grp].setdefault(br, []).extend(
                        p for p in pats if isinstance(p, str))
        v = data.get("skip_globs")
        if isinstance(v, list):
            skips += [s for s in v if isinstance(s, str)]
        v = data.get("adjudicated")
        if isinstance(v, list):
            for it in v:
                if not isinstance(it, dict):
                    continue
                rec, br = it.get("record"), it.get("br")
                why = (it.get("why") or "").strip()
                if not (isinstance(rec, str) and isinstance(br, str)):
                    print(f"警告: {rel} の adjudicated に record/br が無い項目がある",
                          file=sys.stderr)
                    continue
                if not why:
                    # 理由の無い黙らせは適用しない。**安全側は「疑いを出す」ほう**である
                    print(f"警告: {rel} の adjudicated {rec}/{br} に why が無いので"
                          f"適用しない(理由の無い裁定は次に読む者が覆せない)",
                          file=sys.stderr)
                    continue
                adj.append({"record": rec, "br": br,
                            "path": it.get("path") or "*",
                            "pattern": it.get("pattern") or "*",
                            "match": it.get("match") or "*", "why": why})

    def compile_group(group: dict) -> dict:
        out: dict[str, list] = {}
        for br, pats in group.items():
            got = []
            for p in pats:
                try:
                    got.append((p, re.compile(p, re.M)))
                except re.error as e:
                    print(f"警告: {br} のパターンが正規表現として壊れている: {p} ({e})",
                          file=sys.stderr)
            if got:
                out[br] = got
        return out

    return (compile_group(raw["evidence"]), compile_group(raw["weak"]),
            compile_group(raw["context"]), sorted(set(skips)), adj)


def baseline_ids(root: Path) -> list[str]:
    path = root / BASELINE
    if not path.is_file():
        return []
    ids: list[str] = []
    for line in path.read_text(errors="replace").splitlines():
        m = BR_ROW.match(line.strip())
        if m and m.group(1) not in ids:
            ids.append(m.group(1))
    return ids


def section(text: str, name: str) -> str | None:
    m = re.search(rf"^##[^\n]*{re.escape(name)}[^\n]*$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    return m.group(1) if m else None


def frontmatter_commit(text: str) -> str | None:
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return None
    g = re.search(r"(?m)^commit:\s*([0-9a-f]{7,40})\s*$", m.group(1))
    return g.group(1) if g else None


def build_index(root: Path) -> dict[str, list[Path]]:
    """作業ツリー用の索引。**os.walk で枝ごと刈る** — rglob は列挙してから捨てるので、
    node_modules や vendor の中まで歩いてしまい、費用がファイル総数に比例する。"""
    idx: dict[str, list[Path]] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in PRUNE]
        for name in filenames:
            idx.setdefault(name, []).append(Path(dirpath) / name)
    return idx


class Tree:
    """記録の `commit:` 時点のファイル一覧と中身。

    **抱えるのは1コミットぶんだけである** — 記録は1本ずつ順に処理され、1記録は1コミットを
    指すので、それ以上を持ち越しても当たらない。全コミットぶん溜めると、大きなリポジトリで
    「キャッシュ」が記録数 × 全ファイル名 + 全クロージャの中身になる。"""

    def __init__(self, root: Path):
        self.root = root
        self._commit: str | None = None
        self._names: list[str] | None = None
        self._sizes: dict[str, int] = {}
        self._blobs: dict[str, str | None] = {}

    def _git(self, args: list[str]) -> str | None:
        try:
            r = subprocess.run(["git", *args], cwd=self.root,
                               capture_output=True, text=True, errors="replace")
        except OSError:
            return None
        return r.stdout if r.returncode == 0 else None

    def files(self, commit: str) -> list[str] | None:
        if commit != self._commit:
            self._commit = commit
            self._blobs = {}                      # コミットが変わったら中身も捨てる
            self._sizes = {}
            # `-l` は大きさも出す。**読む前に大きさが判る**ので、
            # 大きな blob を標準出力へ吸い上げてから捨てる、という無駄が消える
            # `-z` は NUL 区切りで**パスを C 引用しない** — 引用されるとタブや空白を含む
            # パスが実物へ解決できなくなる。`-l` は大きさも出すので、読む前に落とせる。
            out = self._git(["ls-tree", "-r", "-l", "-z", commit])
            if out is None:
                self._names = None
            else:
                names = []
                for rec in out.split("\0"):
                    m = re.match(r"^\S+\s+(\S+)\s+\S+\s+(\S+)\t(.*)$", rec, re.S)
                    if not m:
                        continue
                    kind, size, name = m.group(1), m.group(2), m.group(3)
                    # **blob 以外は証拠になりえない** — submodule の gitlink は大きさが `-` で、
                    # `git show <commit>:<path>` を打つとそのコミットの説明文が返る。
                    # ソースでないものを証拠にしないため、索引に入れない
                    if kind != "blob":
                        continue
                    names.append(name)
                    if size.isdigit():
                        self._sizes[name] = int(size)
                self._names = names
        return self._names

    def resolve(self, commit: str, rel: str) -> str | None:
        files = self.files(commit)
        if files is None:
            return None
        if rel in files:
            return rel
        cands = [f for f in files if f.endswith("/" + rel)]
        return cands[0] if len(cands) == 1 else None

    def read(self, commit: str, path: str) -> str | None:
        self.files(commit)                        # コミットを合わせる(必要なら捨てる)
        if path not in self._blobs:
            # 作業ツリー側の st_size と同じく**バイト数**で見る。**読む前に落とす** —
            # 読んでから長さを見るのでは、ピークのメモリも読取の費用も抑えられない
            if self._sizes.get(path, 0) > MAX_BYTES:
                self._blobs[path] = None
            else:
                self._blobs[path] = self._git(["show", f"{commit}:{path}"])
        return self._blobs[path]


def resolve_worktree(root: Path, rel: str, idx: dict[str, list[Path]]) -> Path | None:
    direct = root / rel
    if direct.is_file():
        # 記号リンク等でリポジトリの外へ出ていないことまで確かめる。
        # **resolve() は ValueError だけを投げるのではない** — 輪になった記号リンクで
        # RuntimeError、権限や I/O の異常で OSError が出る。落ちると終了コードが 1 になり、
        # docstring が約束した 0/2 が破れるので、解決できなかった扱いにする
        try:
            direct.resolve().relative_to(root.resolve())
        except (ValueError, RuntimeError, OSError):
            return None
        return direct
    name = rel.rsplit("/", 1)[-1]
    cands = []
    for cand in idx.get(name, []):
        as_rel = str(cand.relative_to(root))
        if not (as_rel.endswith("/" + rel) or as_rel == rel):
            continue
        # **こちらの枝にも root 内判定が要る** — 記号リンクは接頭辞を省いた書き方でも
        # 辿れるので、direct 分岐だけを塞いでも外へ出る道が残る
        try:
            cand.resolve().relative_to(root.resolve())
        except ValueError:
            continue        # root の外だと**確定した** → 候補から外すのが正しい
        except (RuntimeError, OSError):
            # **判定できなかった**のであって、外だと判ったのではない。ここで候補を
            # 黙って捨てると、残った候補が「唯一」になり、失敗も、接頭辞省略が本来
            # 持っていた曖昧さも隠れる。行ごと未解決にして死角に数えさせる
            return None
        cands.append(cand)
    return cands[0] if len(cands) == 1 else None


def safe_rel(rel: str) -> bool:
    """クロージャのパスとして受け取ってよい形か。

    先頭の `.` を許したこと(`.env.example` のため)の裏で、`../outside.txt` も
    受理されるようになっていた。クロージャはリポジトリの中のものだけを指すので、
    **上へ出る形と絶対パスは、解決を試みる前に断る**。"""
    if not rel or rel.startswith(("/", "~")):
        return False
    return ".." not in PurePosixPath(rel).parts


def norm_rel(rel: str) -> str:
    """`./src/x.go` を `src/x.go` にする。

    正規化しないと、作業ツリー側は読めるのに commit のツリーとは一致せず、
    **同じ正当なパスの結果が走らせ方で変わる**。"""
    parts = [p for p in PurePosixPath(rel).parts if p != "."]
    return "/".join(parts)


def skipped(rel: str, skips: list[str]) -> bool:
    return any(fnmatch(rel, g) or fnmatch(rel.rsplit("/", 1)[-1], g) for g in skips)


def adjudged(record: str, br: str, rel: str, pattern: str, text: str,
             adj: list[dict]) -> str | None:
    """裁定済みとして控えてある疑いなら、その理由を返す。無ければ None。

    鍵は4つ — (記録のファイル名, BR, 証拠の在ったクロージャのパス, 当たった証拠のパターン)
    に、**当たった文字列**を加えた5つである。**行番号は鍵にしない** —
    記録に1行足すだけで全部の控えが外れるからである。

    ★ パターンと当たった文字列まで鍵に入れるのは、**1つのファイルに無害な一致と本物の
    一致が同居する**からである。パスだけを鍵にすると、無害なほうを裁定したつもりで本物まで
    消える(`crypto/rand` を裁定したら、同じファイルの利用者向けトークン生成も消えた)。
    同じ正規表現が同じファイルで2度当たる場合もあるので、**当たった文字列が最後の鍵**である。

    ★ `match` は**印字用に切り詰める前の全文**である(印字は 48 文字で切るが、鍵は切らない)。

    ★ **同じ文字列が同じファイルで2度当たるときは、区別しない** — それは意図である。
    区別できる鍵は行番号か出現の順番しか無く、どちらも記録やコードに1行足せばずれる
    (順番のほうが悪い: 黙って別の一致を指し直すので、外れたことにも気づけない)。
    **同じファイルの、同じ BR の、同じ証拠文字列は、同じ証拠の類である** —
    裁定する人間が見るのはファイルであって、何度目の一致かではない。
    なお、この計器が1つの判定行について印字する疑いは**もともと1件だけ**なので、
    2件目の同一文字列は裁定の有無にかかわらず表に出たことがない。

    ★ `record` と `path` はグロブだが、**`pattern` と `match` は完全一致で見る**
    (`*` だけが「どれでも」の意味を持つ)。この2つの値は正規表現と、そこに当たった
    実際の文字列であり、**グロブとして解釈すると `[A-Z]+` が自分自身に一致しない** —
    控えたはずの裁定が黙って効かなくなる(実測)。
    """
    for it in adj:
        if (fnmatch(record, it["record"]) and br == it["br"]
                and fnmatch(rel, it["path"])
                and it["pattern"] in ("*", pattern)
                and it["match"] in ("*", text)):
            return it["why"]
    return None


def line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def scan_record(root: Path, path: Path, cfg, idx: dict, tree: Tree,
                use_commit: bool = True) -> tuple[list, dict]:
    ev, weak, ctx, skips, adj = cfg
    # コメントは落とすが **行数は保つ** — 記録の行番号をそのまま報告するためである
    # (落として詰めると、複数行コメントを持つ記録だけ行番号がずれて名指しが外れる)
    text = re.sub(r"<!--.*?-->",
                  lambda m: "\n" * m.group(0).count("\n"),
                  path.read_text(encoding="utf-8", errors="replace"), flags=re.S)
    lines = text.splitlines()

    commit = frontmatter_commit(text) if use_commit else None
    at_commit = bool(commit and tree.files(commit) is not None)

    # クロージャを実物(可能なら commit 時点)へ解決し、中身を1回だけ読む
    loaded: list[tuple[str, str]] = []
    unresolved: list[str] = []
    for raw in (section(text, "影響範囲") or "").splitlines():
        line = raw.strip()
        m = CLOSURE_PATH.match(line)
        if not m:
            # パスのつもりで書かれた行が解析できないなら、**黙って捨てない** —
            # 捨てた行のぶんだけ、この計器は自分の死角を小さく見せることになる
            if re.match(r"^[-*]\s+\S", line):
                unresolved.append(line[:60])
            continue
        rel = (m.group(1) or m.group(2)).strip()
        if not safe_rel(rel) or (m.group(1) is None and not CLOSURE_BARE.match(rel)):
            unresolved.append(rel)      # 黙って捨てず、死角として数える
            continue
        rel = norm_rel(rel)
        if skipped(rel, skips):
            continue
        body = None
        if at_commit:
            got = tree.resolve(commit, rel)
            if got:
                body = tree.read(commit, got)
        else:
            got = resolve_worktree(root, rel, idx)
            if got:
                try:
                    if got.stat().st_size <= MAX_BYTES:
                        body = got.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    body = None
        (loaded.append((rel, body)) if body is not None else unresolved.append(rel))

    stat = {"rows": 0, "na": 0, "nopat": 0, "noclosure": 0, "partial": 0,
            # ★ 裁定済みとして控えから外した行。**0 でない限り必ず印字する** —
            # 黙って減った疑いは、直った疑いと見分けが付かない
            "adjudicated": 0,
            "unresolved": len(unresolved), "unresolved_paths": unresolved,
            # ★ この記録に**判定行が在った** BR。行が無い BR は `非該当` にもならないので
            # 走査の対象にすらならず、疑いにも取りこぼしにも現れない(`baseline.md` §4.3)。
            # `nosection` は**点検の節ごと無い**記録 — 原因が違う(あれは BRC5 の違反であって
            # 「後から足した項目」ではない)ので、混ぜて数えると片方がもう片方を隠す
            "seen": set(), "nosection": 0,
            "at_commit": 1 if at_commit else 0,
            # 利用者が --worktree で切ったのは縮退ではない。数えるのは**引けなかった**ときだけ
            "no_commit": 1 if (use_commit and not at_commit) else 0}

    body_start = None
    for i, ln in enumerate(lines):
        if re.match(r"^##[^\n]*基本要件の点検", ln):
            body_start = i
            break
    if body_start is None:
        stat["nosection"] = 1
        return [], stat

    ctx_cache: dict[str, bool] = {}

    def has_context(br: str) -> bool:
        if br not in ctx_cache:
            pats = ctx.get(br, [])
            ctx_cache[br] = any(rx.search(b) for _, b in loaded for _, rx in pats)
        return ctx_cache[br]

    hits: list = []
    for i in range(body_start, len(lines)):
        ln = lines[i]
        if i > body_start and ln.startswith("## "):
            break
        g = BR_ROW.match(ln.strip())
        if not g:
            continue
        br = g.group(1)
        stat["rows"] += 1
        stat["seen"].add(br)
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        verdict = (cells[1] if len(cells) > 1 else "").strip("`* 　")
        if not verdict.startswith("非該当"):
            continue
        stat["na"] += 1
        strong, wk = ev.get(br), weak.get(br)
        if not strong and not wk:
            stat["nopat"] += 1
            continue
        if not loaded:
            stat["noclosure"] += 1
            continue

        # ★ 裁定済みの証拠は**その1件を飛ばすだけ**で、行を消してはならない。
        # 最初に当たった1件で打ち切ると、同じ行の**別ファイルにある未裁定の証拠**まで
        # 道連れに消える(内部用の乱数を裁定したら、利用者向けのトークン生成の疑いも消えた)
        adj_seen = 0

        def pick(pats, kind):
            nonlocal adj_seen
            for rel, body in loaded:
                for src, rx in pats:
                    # **`search` で1件目だけを見ない** — 同じ正規表現が同じファイルで
                    # 2度当たることが在り、1件目を裁定すると2件目が走査されずに消える
                    for m in rx.finditer(body):
                        # ★ 鍵には**切り詰めていない**当たり文字列を渡す。印字用の
                        # 48 文字で鍵にすると、49 文字目以降だけが違う2つの一致が
                        # 同じ鍵になり、片方の裁定が他方まで黙らせる(実測)
                        if adjudged(path.name, br, rel, src,
                                    m.group(0).strip(), adj):
                            adj_seen += 1
                            continue       # この一致だけを飛ばし、**次の一致も見る**
                        return (br, rel, body, m, src, kind)
            return None

        found = pick(strong or [], "evidence")
        # 弱い証拠は context が要る。**context は同じファイルではなくクロージャ全体で見る** —
        # 適用はクロージャに対して判定するものであり(`baseline.md` §1 の1)、
        # 画面が `onClick={deleteUser}` を持ち別ファイルが `deleteUser(` を定義する分割は普通である
        if not found and wk and has_context(br):
            found = pick(wk, "weak+context")

        if found:
            _, rel, body, m, src, kind = found
            hits.append({"br": br, "row": i + 1, "path": rel,
                         "hit_line": line_of(body, m.start()),
                         "text": m.group(0).strip()[:48], "pattern": src,
                         "kind": kind, "at_commit": at_commit})
        else:
            if adj_seen:
                # 見つかった証拠が、見つかったぶんは全部裁定済みだった行
                stat["adjudicated"] += 1
            if unresolved:
                # ★ 一部でも解決できていないなら「検査済み」と言ってはならない。
                # **裁定済みであることは、これを免除しない** — 読めなかったパスの中に
                # 未裁定の証拠が在りうるので、裁定を先に見て打ち切ると死角が消える
                stat["partial"] += 1
    return hits, stat


def run(root: Path, targets: list[Path], quiet: bool, use_commit: bool) -> int:
    cfg = load_config(root)
    ev, weak, _ctx, _skips, _adj = cfg
    ids = baseline_ids(root)
    if not ids:
        print(f"前提エラー: {BASELINE} §2 の `| BR-nn |` 行が読めない", file=sys.stderr)
        return 2
    missing = [b for b in ids if b not in ev and b not in weak]
    idx = build_index(root) if not use_commit else {}
    tree = Tree(root)

    keys = ("rows", "na", "nopat", "noclosure", "partial", "unresolved",
            "at_commit", "no_commit", "nosection", "adjudicated")
    total = dict.fromkeys(keys, 0)
    all_hits, unresolved_paths = [], []
    from collections import Counter
    norow: Counter = Counter()
    for path in targets:
        hits, stat = scan_record(root, path, cfg, idx, tree, use_commit)
        if stat["no_commit"] and use_commit and not idx:
            idx = build_index(root)                     # 落ちた記録が出た時点で1回だけ
            hits, stat = scan_record(root, path, cfg, idx, tree, use_commit)
        for k in keys:
            total[k] += stat[k]
        unresolved_paths += [(path.name, p) for p in stat["unresolved_paths"]]
        if not stat["nosection"]:            # 節ごと無い記録は下で別に数える
            for b in ids:
                if b not in stat["seen"]:
                    norow[b] += 1
        if hits and not quiet:
            print(f"疑い  {path.relative_to(root)}: {len(hits)} 行"
                  f"{'' if hits[0]['at_commit'] else '(commit を引けず作業ツリーに照らした)'}")
            for h in sorted(hits, key=lambda x: x["br"]):
                print(f"  {h['br']}  記録 :{h['row']} の `非該当` に対し、"
                      f"クロージャの {h['path']}:{h['hit_line']} が "
                      f"「{h['text']}」を持つ")
        all_hits += [(path.name, h) for h in hits]

    print()
    print(f"記録 {len(targets)}本 / BR 行 {total['rows']} / `非該当` {total['na']} / "
          f"**疑い {len(all_hits)}行**({len({r for r, _ in all_hits})}記録)")
    if all_hits:
        c = Counter(h["br"] for _, h in all_hits)
        print("  BR 別: " + " ".join(f"{k}={v}" for k, v in sorted(c.items())))
    if total["adjudicated"]:
        print(f"裁定済みとして疑いから外した: {total['adjudicated']}行"
              f"({CONFIG.name} の `adjudicated`。理由はそこに書いてある)")
    # ★ 取りこぼしを数える — 疑いの数だけを見て「片付いた」と読ませない
    print(f"検査できなかった `非該当`: {total['nopat'] + total['noclosure']}行"
          f"(パターン未設定の BR {total['nopat']} / 走査できるファイルがクロージャに"
          f"1つも無い {total['noclosure']})")
    print(f"部分的にしか検査できていない `非該当`: {total['partial']}行"
          f"(クロージャの一部を実物へ解決できず、証拠を取り落としている可能性がある)")
    scanned = len(targets) - total["nosection"]
    if norow:
        print("判定行が無い BR: " + " ".join(f"{k}={v}本" for k, v in sorted(norow.items()))
              + f"(点検の節を持つ記録 {scanned}本中)")
        print("  — 行が無ければ `非該当` も無く、この計器はその BR について"
              "その記録を**見ていない**。足したばかりの項目がここに出るのは正常である"
              f"({BASELINE.name} §4.3)。遡って埋め直さない。")
    if total["nosection"]:
        print(f"`## 基本要件の点検` の節が無い記録: {total['nosection']}本"
              " — 上の数え方の外である。**これは BRC5 の違反であって、"
              "「後から足した項目」ではない**(`check-buildrecord.py` が拒む)。")
    if missing:
        print(f"  パターンを持たない BR: {', '.join(missing)}"
              f" — {CONFIG.name}(または .local.json)に足すまで、この BR の"
              f"`非該当` は誰も見ていない")
    if unresolved_paths:
        print(f"  実物へ解決できなかったクロージャのパス: {len(unresolved_paths)}件"
              f"(例 {unresolved_paths[0][1]} @ {unresolved_paths[0][0]})")
    if total["no_commit"]:
        print(f"  `commit:` を引けず作業ツリーに照らした記録: {total['no_commit']}本"
              f"(その分、後の変更による偽陽性と、移動・削除による見逃しが起きうる)")
    print("これは計器である(`.claude/directions/core.md` §3)。疑いは裁定ではない — "
          "各行を、その記録が宣言したクロージャのファイル全体に照らして判定し直すこと"
          "(`baseline.md` §1 の1)。")
    return 0


def selftest() -> int:
    import tempfile
    ok = True
    with tempfile.TemporaryDirectory() as td:
        # リポジトリは一時ディレクトリの**子**に作る。root.parent へ fixture を書くと
        # 共有の /tmp を汚し、既存ファイルを壊し、並行実行とぶつかる(実測で1件汚した)
        base = Path(td)
        root = base / "repo"
        root.mkdir()
        (root / "CLAUDE.md").write_text("x")
        (root / ".claude/scripts").mkdir(parents=True)
        (root / ".claude/directions").mkdir(parents=True)
        (root / BASELINE).write_text(
            "## 2. 一覧\n| ID | 名前 |\n|---|---|\n| BR-09 | 認証試行の抑止 |\n"
            "| BR-06 | 乱数 |\n| BR-10 | サイト外からの要求の拒否 |\n", encoding="utf-8")
        (root / CONFIG).write_text(json.dumps({
            "skip_globs": ["*.md"],
            "evidence": {"BR-09": ["(?i)\\bAuthenticate\\b"]},
            "weak": {"BR-10": ["\\b(delete|create)[A-Z]\\w*\\("]},
            "context": {"BR-10": ["onClick\\s*="]},
        }), encoding="utf-8")
        (root / "internal/peer").mkdir(parents=True)
        (root / "internal/peer/account.go").write_text(
            "package peer\nfunc (r *Registry) Authenticate(name string) error { return nil }\n")
        (root / "cmd").mkdir()
        (root / "cmd/cli.go").write_text("package main\nfunc createUser() {}\nvar x = createUser\n")
        (root / RECORDS).mkdir(parents=True)

        rec = ("---\nslug: a\nstate: verified\n---\n"
               "## 影響範囲(closure)\n\n"
               "<!-- 1行1パス。\n     触った文書とコードを全部書く。\n     3行目 -->\n"
               "- internal/peer/account.go\n- docs/x.md\n\n"
               "## 基本要件の点検\n\n| ID | 判定 | 理由 | 落とし先 |\n|---|---|---|---|\n"
               "| BR-09 | 非該当 | 秘密を突き合わせる経路に触らない | - |\n"
               "| BR-06 | 非該当 | 乱数を作らない | - |\n")
        (root / RECORDS / "a.md").write_text(rec, encoding="utf-8")
        want_row = next(i + 1 for i, l in enumerate(rec.splitlines())
                        if l.startswith("| BR-09"))

        cfg = load_config(root)
        idx = build_index(root)
        tree = Tree(root)
        hits, stat = scan_record(root, root / RECORDS / "a.md", cfg, idx, tree, False)

        if len(hits) != 1 or hits[0]["br"] != "BR-09":
            print(f"NG 偽の BR-09 非該当を検出できない: {hits}"); ok = False
        elif hits[0]["path"] != "internal/peer/account.go":
            print(f"NG 接頭辞を省いたパスの解決に失敗: {hits}"); ok = False
        elif hits[0]["row"] != want_row:
            print(f"NG 記録の行番号がずれている: {hits[0]['row']} != {want_row}"); ok = False
        if stat["na"] != 2 or stat["nopat"] != 1:
            print(f"NG 取りこぼしの計数が合わない: {stat}"); ok = False
        # ★ 記録に判定行が無い BR は「見ていない」— 走査にも取りこぼしにも現れないので、
        # 在った行のほうを数えて突き合わせる(`baseline.md` §4.3)
        if stat["seen"] != {"BR-09", "BR-06"} or stat["nosection"] != 0:
            print(f"NG 判定行の在る BR の集合が合わない(BR-10 は行が無い): "
                  f"{stat['seen']} / nosection={stat['nosection']}"); ok = False

        # ★ 点検の節ごと無い記録を、「後から足した項目」の欠落と混ぜない — 原因が違う
        (root / RECORDS / "nosec.md").write_text(
            "---\nslug: nosec\nstate: verified\n---\n"
            "## 影響範囲(closure)\n\n- cmd/cli.go\n", encoding="utf-8")
        _h2, s2 = scan_record(root, root / RECORDS / "nosec.md", cfg, idx, tree, False)
        if s2["nosection"] != 1 or s2["seen"]:
            print(f"NG 点検節の無い記録を判定行の欠落と混ぜている: {s2}"); ok = False
        if any(h["path"].endswith(".md") for h in hits):
            print("NG 文書を証拠にしている"); ok = False

        # ★ 裁定済みの控え(`adjudicated`)— 覆らなかった疑いを毎回出し直さない
        adj_cfg = json.loads((root / CONFIG).read_text(encoding="utf-8"))
        adj_cfg["adjudicated"] = [
            {"record": "a.md", "br": "BR-09", "path": "internal/**",
             "why": "内部の突き合わせであって利用者の秘密ではない"},
            {"record": "a.md", "br": "BR-06", "why": ""},        # why 無し = 適用しない
        ]
        (root / CONFIG).write_text(json.dumps(adj_cfg), encoding="utf-8")
        import contextlib, io
        with contextlib.redirect_stderr(io.StringIO()) as warned:   # why 無しの警告を捕まえる
            cfg_adj = load_config(root)
        if "why が無い" not in warned.getvalue():
            print("NG why の無い控えを黙って受け入れている"); ok = False
        h_adj, st_adj = scan_record(root, root / RECORDS / "a.md", cfg_adj, idx, tree, False)
        if h_adj or st_adj["adjudicated"] != 1:
            print(f"NG 裁定済みの控えが効かない: {h_adj} adjudicated={st_adj['adjudicated']}")
            ok = False
        # 鍵が1つでも違えば効かない(BR 違い / 記録違い / パス違い)
        for key, val in (("br", "BR-06"), ("record", "zzz.md"), ("path", "cmd/**")):
            one = {"record": "a.md", "br": "BR-09", "path": "internal/**",
                   "why": "x"}
            one[key] = val
            adj_cfg["adjudicated"] = [one]
            (root / CONFIG).write_text(json.dumps(adj_cfg), encoding="utf-8")
            h_n, st_n = scan_record(root, root / RECORDS / "a.md",
                                    load_config(root), idx, tree, False)
            if len(h_n) != 1 or st_n["adjudicated"] != 0:
                print(f"NG {key} が違う控えで疑いを消している: {h_n}"); ok = False
        (root / CONFIG).write_text(json.dumps(
            {k: v for k, v in adj_cfg.items() if k != "adjudicated"}), encoding="utf-8")
        cfg = load_config(root)

        # ★ 裁定は**その1件を飛ばすだけ**。同じ行の別ファイルの未裁定の証拠は残る
        (root / "cmd/auth2.go").write_text(
            "package main\nfunc Authenticate() {}\n", encoding="utf-8")
        (root / RECORDS / "k.md").write_text(
            "---\nslug: k\nstate: verified\n---\n"
            "## 影響範囲(closure)\n\n- internal/peer/account.go\n- cmd/auth2.go\n\n"
            "## 基本要件の点検\n\n| ID | 判定 | 理由 | 落とし先 |\n|---|---|---|---|\n"
            "| BR-09 | 非該当 | 秘密を突き合わせる経路が無い | - |\n", encoding="utf-8")
        adj_cfg["adjudicated"] = [{"record": "k.md", "br": "BR-09",
                                   "path": "internal/**", "why": "内部の突き合わせ"}]
        (root / CONFIG).write_text(json.dumps(adj_cfg), encoding="utf-8")
        idx = build_index(root)
        h_k, st_k = scan_record(root, root / RECORDS / "k.md",
                                load_config(root), idx, tree, False)
        if len(h_k) != 1 or h_k[0]["path"] != "cmd/auth2.go" or st_k["adjudicated"] != 0:
            print(f"NG 裁定した1件が、同じ行の別ファイルの疑いまで消している: "
                  f"{h_k} adjudicated={st_k['adjudicated']}"); ok = False
        # 全部が裁定済みなら、その行は消えて数えられる
        adj_cfg["adjudicated"] = [{"record": "k.md", "br": "BR-09",
                                   "path": "*", "why": "どちらも内部の突き合わせ"}]
        (root / CONFIG).write_text(json.dumps(adj_cfg), encoding="utf-8")
        h_k2, st_k2 = scan_record(root, root / RECORDS / "k.md",
                                  load_config(root), idx, tree, False)
        if h_k2 or st_k2["adjudicated"] != 1:
            print(f"NG 全部裁定済みの行が消えない/数えられない: "
                  f"{h_k2} adjudicated={st_k2['adjudicated']}"); ok = False
        (root / CONFIG).write_text(json.dumps(
            {k: v for k, v in adj_cfg.items() if k != "adjudicated"}), encoding="utf-8")
        cfg = load_config(root)

        # ★ 同じファイルに無害な一致と本物の一致が同居しても、片方の裁定で行を消さない
        adj_cfg["evidence"] = {"BR-09": ["(?i)\\bAuthenticate\\b", "Secret\\w*\\("]}
        (root / "cmd/two.go").write_text(
            "package main\nfunc Authenticate() {}\nfunc SecretMint() {}\n", encoding="utf-8")
        (root / RECORDS / "m.md").write_text(
            "---\nslug: m\nstate: verified\n---\n"
            "## 影響範囲(closure)\n\n- cmd/two.go\n\n"
            "## 基本要件の点検\n\n| ID | 判定 | 理由 | 落とし先 |\n|---|---|---|---|\n"
            "| BR-09 | 非該当 | 秘密を突き合わせる経路が無い | - |\n", encoding="utf-8")
        adj_cfg["adjudicated"] = [{"record": "m.md", "br": "BR-09", "path": "cmd/two.go",
                                   "pattern": "(?i)\\bAuthenticate\\b",
                                   "why": "内部の突き合わせ"}]
        (root / CONFIG).write_text(json.dumps(adj_cfg), encoding="utf-8")
        idx = build_index(root)
        h_m, _st_m = scan_record(root, root / RECORDS / "m.md",
                                 load_config(root), idx, tree, False)
        if len(h_m) != 1 or h_m[0]["pattern"] != "Secret\\w*\\(":
            print(f"NG 同じファイルの別パターンの疑いまで裁定で消している: {h_m}"); ok = False

        # ★ 同じ正規表現が同じファイルで2度当たるとき、片方の裁定で他方を消さない。
        # 最後の鍵は**当たった文字列**である
        adj_cfg["evidence"] = {"BR-09": ["Secret\\w*\\("]}
        (root / "cmd/twice.go").write_text(
            "package main\nfunc SecretMint() {}\nfunc SecretVerify() {}\n", encoding="utf-8")
        (root / RECORDS / "q.md").write_text(
            "---\nslug: q\nstate: verified\n---\n"
            "## 影響範囲(closure)\n\n- cmd/twice.go\n\n"
            "## 基本要件の点検\n\n| ID | 判定 | 理由 | 落とし先 |\n|---|---|---|---|\n"
            "| BR-09 | 非該当 | 秘密を突き合わせる経路が無い | - |\n", encoding="utf-8")
        adj_cfg["adjudicated"] = [{"record": "q.md", "br": "BR-09", "path": "cmd/twice.go",
                                   "pattern": "Secret\\w*\\(", "match": "SecretMint(",
                                   "why": "内部管理用の採番であって利用者の秘密ではない"}]
        (root / CONFIG).write_text(json.dumps(adj_cfg), encoding="utf-8")
        idx = build_index(root)
        h_q, _ = scan_record(root, root / RECORDS / "q.md",
                             load_config(root), idx, tree, False)
        if len(h_q) != 1 or h_q[0]["text"] != "SecretVerify(":
            print(f"NG 同じ正規表現の2件目の一致が、1件目の裁定で消えている: {h_q}"); ok = False

        # ★ 鍵は切り詰めない — 49 文字目以降だけが違う2つの一致を同じ鍵にしない
        long1, long2 = "Secret" + "M" * 45 + "X", "Secret" + "M" * 45 + "Y"
        (root / "cmd/long.go").write_text(
            f"package main\nfunc {long1}() {{}}\nfunc {long2}() {{}}\n", encoding="utf-8")
        (root / RECORDS / "p.md").write_text(
            "---\nslug: p\nstate: verified\n---\n"
            "## 影響範囲(closure)\n\n- cmd/long.go\n\n"
            "## 基本要件の点検\n\n| ID | 判定 | 理由 | 落とし先 |\n|---|---|---|---|\n"
            "| BR-09 | 非該当 | 秘密を突き合わせる経路が無い | - |\n", encoding="utf-8")
        adj_cfg["evidence"] = {"BR-09": ["Secret\\w*\\("]}
        adj_cfg["adjudicated"] = [{"record": "p.md", "br": "BR-09", "path": "cmd/long.go",
                                   "pattern": "Secret\\w*\\(", "match": long1 + "(",
                                   "why": "こちらの一致だけを裁定した"}]
        (root / CONFIG).write_text(json.dumps(adj_cfg), encoding="utf-8")
        idx = build_index(root)
        h_p, _ = scan_record(root, root / RECORDS / "p.md",
                             load_config(root), idx, tree, False)
        if len(h_p) != 1 or not h_p[0]["text"].startswith("Secret"):
            print(f"NG 先頭48文字が同じ2つの一致を、1件の裁定で両方消している: {h_p}")
            ok = False

        # ★ `pattern` は完全一致で見る — グロブにすると `[A-Z]+` が自分自身に当たらない
        adj_cfg["evidence"] = {"BR-09": ["Secret[A-Z]\\w*\\("]}
        adj_cfg["adjudicated"] = [{"record": "q.md", "br": "BR-09", "path": "*",
                                   "pattern": "Secret[A-Z]\\w*\\(",
                                   "why": "角括弧を含む正規表現でも控えが効くこと"}]
        (root / CONFIG).write_text(json.dumps(adj_cfg), encoding="utf-8")
        h_r, st_r = scan_record(root, root / RECORDS / "q.md",
                                load_config(root), idx, tree, False)
        if h_r or st_r["adjudicated"] != 1:
            print(f"NG 角括弧を含む正規表現の控えが効いていない(グロブ解釈): "
                  f"{h_r} adjudicated={st_r['adjudicated']}"); ok = False
        adj_cfg["evidence"] = {"BR-09": ["(?i)\\bAuthenticate\\b"]}

        # ★ 未解決のパスが在る行は、裁定済みでも「検査済み」と言わない
        (root / RECORDS / "n.md").write_text(
            "---\nslug: n\nstate: verified\n---\n"
            "## 影響範囲(closure)\n\n- cmd/two.go\n- cmd/does-not-exist.go\n\n"
            "## 基本要件の点検\n\n| ID | 判定 | 理由 | 落とし先 |\n|---|---|---|---|\n"
            "| BR-09 | 非該当 | 秘密を突き合わせる経路が無い | - |\n", encoding="utf-8")
        adj_cfg["adjudicated"] = [{"record": "n.md", "br": "BR-09", "path": "cmd/two.go",
                                   "why": "どちらの一致も内部の突き合わせ"}]
        (root / CONFIG).write_text(json.dumps(adj_cfg), encoding="utf-8")
        h_n, st_n = scan_record(root, root / RECORDS / "n.md",
                                load_config(root), idx, tree, False)
        if h_n or st_n["adjudicated"] != 1 or st_n["partial"] != 1:
            print(f"NG 未解決のパスが在るのに裁定で死角を消している: {h_n} "
                  f"adjudicated={st_n['adjudicated']} partial={st_n['partial']}"); ok = False
        (root / CONFIG).write_text(json.dumps(
            {k: v for k, v in adj_cfg.items() if k != "adjudicated"}), encoding="utf-8")
        cfg = load_config(root)

        # ★ `index.md` は記録ではない — 数えると「点検の節が無い記録」を偽って印字する
        (root / RECORDS / "index.md").write_text("# 索引\n", encoding="utf-8")
        rec_dir = root / RECORDS
        listed = sorted(q.name for q in rec_dir.glob("*.md") if q.name != "index.md")
        if "index.md" in listed:
            print("NG index.md を構築記録として数えている"); ok = False

        # 弱い証拠は context 無しでは発火しない(CLI の createUser( は BR-10 でない)
        (root / RECORDS / "c.md").write_text(
            "---\nslug: c\nstate: verified\n---\n"
            "## 影響範囲(closure)\n\n- cmd/cli.go\n\n"
            "## 基本要件の点検\n\n| ID | 判定 | 理由 | 落とし先 |\n|---|---|---|---|\n"
            "| BR-10 | 非該当 | ブラウザから呼ばれる経路が無い | - |\n", encoding="utf-8")
        h_cli, _ = scan_record(root, root / RECORDS / "c.md", cfg, idx, tree, False)
        if h_cli:
            print(f"NG context 無しで弱い証拠が発火した: {h_cli}"); ok = False
        # context が在れば発火する
        (root / "page.tsx").write_text("export const P = () => <b onClick={() => createUser()}/>\n")
        (root / RECORDS / "d.md").write_text(
            "---\nslug: d\nstate: verified\n---\n"
            "## 影響範囲(closure)\n\n- page.tsx\n\n"
            "## 基本要件の点検\n\n| ID | 判定 | 理由 | 落とし先 |\n|---|---|---|---|\n"
            "| BR-10 | 非該当 | ブラウザから呼ばれる経路が無い | - |\n", encoding="utf-8")
        idx = build_index(root)
        h_web, _ = scan_record(root, root / RECORDS / "d.md", cfg, idx, tree, False)
        if len(h_web) != 1 or h_web[0]["kind"] != "weak+context":
            print(f"NG context 付きの弱い証拠が発火しない: {h_web}"); ok = False

        # ★ バッククォートで囲んだ、空白を含むパスを切り落とさない
        (root / "a dir").mkdir()
        (root / "a dir/my file.go").write_text("package x\nfunc Authenticate() {}\n")
        (root / RECORDS / "h.md").write_text(
            "---\nslug: h\nstate: verified\n---\n"
            "## 影響範囲(closure)\n\n- `a dir/my file.go`\n\n"
            "## 基本要件の点検\n\n| ID | 判定 | 理由 | 落とし先 |\n|---|---|---|---|\n"
            "| BR-09 | 非該当 | 秘密を突き合わせる経路が無い | - |\n", encoding="utf-8")
        idx = build_index(root)
        h_sp, st_sp = scan_record(root, root / RECORDS / "h.md", cfg, idx, tree, False)
        if len(h_sp) != 1 or st_sp["unresolved"] != 0:
            print(f"NG 空白を含むパスを解決できない: {h_sp} {st_sp}"); ok = False

        # ★ リポジトリの外を指すパスは、解決を試みる前に断る(死角としては数える)
        (root / RECORDS / "j.md").write_text(
            "---\nslug: j\nstate: verified\n---\n"
            "## 影響範囲(closure)\n\n- ../outside.go\n- /etc/passwd\n\n"
            "## 基本要件の点検\n\n| ID | 判定 | 理由 | 落とし先 |\n|---|---|---|---|\n"
            "| BR-09 | 非該当 | 秘密を突き合わせる経路が無い | - |\n", encoding="utf-8")
        (base / "outside.go").write_text("func Authenticate() {}\n")
        h_out, st_out = scan_record(root, root / RECORDS / "j.md", cfg,
                                    build_index(root), tree, False)
        if h_out:
            print(f"NG リポジトリの外を証拠にしている: {h_out}"); ok = False
        if st_out["unresolved"] != 2:
            print(f"NG 外を指すパスを死角として数えていない: {st_out}"); ok = False

        # ★ containment を判定できない候補が在ったら、行ごと未解決にする
        #   (残った候補を「唯一」として返すと、失敗も接頭辞省略の曖昧さも隠れる)
        (root / "loopdir").mkdir()
        try:
            os.symlink(root / "loopdir/loop1", root / "loopdir/dup.go")
            os.symlink(root / "loopdir/dup.go", root / "loopdir/loop1")
            (root / "a dir/dup.go").write_text("func Authenticate() {}\n")
            if resolve_worktree(root, "dup.go", build_index(root)) is not None:
                print("NG 判定不能の候補を捨てて別の候補を返している"); ok = False
        except OSError:
            print("    (記号リンクを作れないので候補の判定不能の検査は飛ばした)")

        # ★ weak と context がクロージャの別ファイルに分かれていても発火する
        (root / "handlers.ts").write_text("export function createUser() {}\n")
        (root / "view.tsx").write_text("export const V = () => <b onClick={createUser}/>\n")
        (root / RECORDS / "g.md").write_text(
            "---\nslug: g\nstate: verified\n---\n"
            "## 影響範囲(closure)\n\n- handlers.ts\n- view.tsx\n\n"
            "## 基本要件の点検\n\n| ID | 判定 | 理由 | 落とし先 |\n|---|---|---|---|\n"
            "| BR-10 | 非該当 | ブラウザから呼ばれる経路が無い | - |\n", encoding="utf-8")
        idx = build_index(root)
        h_split, _ = scan_record(root, root / RECORDS / "g.md", cfg, idx, tree, False)
        if len(h_split) != 1 or h_split[0]["kind"] != "weak+context":
            print(f"NG weak と context がファイルをまたぐと発火しない: {h_split}"); ok = False

        # ★ 解決できたパスと解決できないパスが混ざったら「検査済み」にしない
        (root / RECORDS / "e.md").write_text(
            "---\nslug: e\nstate: verified\n---\n"
            "## 影響範囲(closure)\n\n- cmd/cli.go\n- nowhere/gone.go\n\n"
            "## 基本要件の点検\n\n| ID | 判定 | 理由 | 落とし先 |\n|---|---|---|---|\n"
            "| BR-09 | 非該当 | 秘密を突き合わせる経路が無い | - |\n", encoding="utf-8")
        _, st_mix = scan_record(root, root / RECORDS / "e.md", cfg, idx, tree, False)
        if st_mix["partial"] != 1 or st_mix["unresolved"] != 1:
            print(f"NG 混在クロージャを部分的として数えていない: {st_mix}"); ok = False

        # `該当` の行は疑わない
        (root / RECORDS / "b.md").write_text(
            "---\nslug: b\nstate: verified\n---\n"
            "## 影響範囲(closure)\n\n- internal/peer/account.go\n\n"
            "## 基本要件の点検\n\n| ID | 判定 | 理由 | 落とし先 |\n|---|---|---|---|\n"
            "| BR-09 | 該当 | ログインを触る | FR-x-1 |\n", encoding="utf-8")
        hits2, _ = scan_record(root, root / RECORDS / "b.md", cfg, idx, tree, False)
        if hits2:
            print(f"NG `該当` の行を疑っている: {hits2}"); ok = False

        # ★ commit 時点の中身に照らす(作業ツリーの後の変更に引きずられない)
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@e",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@e"}
        def git(*a):
            # 署名も hook も、この検査が見たいものと関係が無い。手元の設定を持ち込むと
            # 読取の機能と無関係なところで偽の NG が出る
            return subprocess.run(
                ["git", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=",
                 "-c", "user.name=t", "-c", "user.email=t@e", *a],
                cwd=root, capture_output=True, text=True, env=env)
        have_git = True
        try:
            have_git = git("init", "-q").returncode == 0
        except OSError:
            have_git = False
        if not have_git:
            print("    (git が使えないので commit 時点の検査は飛ばした)")
        else:
            def must(label, r):
                nonlocal ok
                if r.returncode != 0:
                    print(f"NG 自己検査の下ごしらえに失敗({label}): {r.stderr.strip()[:80]}")
                    ok = False
                return r.returncode == 0
            must("add", git("add", "-A")); must("commit", git("commit", "-qm", "x"))
            sha = git("rev-parse", "HEAD").stdout.strip()
            # 後から作業ツリーへ Authenticate を足す = commit 時点には無い
            (root / "cmd/cli.go").write_text(
                "package main\nfunc createUser() {}\nfunc Authenticate() {}\n")
            (root / RECORDS / "f.md").write_text(
                f"---\nslug: f\nstate: verified\ncommit: {sha}\n---\n"
                "## 影響範囲(closure)\n\n- cmd/cli.go\n\n"
                "## 基本要件の点検\n\n| ID | 判定 | 理由 | 落とし先 |\n|---|---|---|---|\n"
                "| BR-09 | 非該当 | 秘密を突き合わせる経路が無い | - |\n", encoding="utf-8")
            t2 = Tree(root)
            h_at, st_at = scan_record(root, root / RECORDS / "f.md", cfg, {}, t2, True)
            if h_at:
                print(f"NG commit 時点でなく作業ツリーに照らしている: {h_at}"); ok = False
            if st_at["at_commit"] != 1:
                print(f"NG commit を引けていない: {st_at}"); ok = False
            h_wt, _ = scan_record(root, root / RECORDS / "f.md", cfg,
                                  build_index(root), t2, False)
            if len(h_wt) != 1:
                print(f"NG --worktree で今の中身を見ていない: {h_wt}"); ok = False

            # ★ gitlink(submodule)は証拠にしない。`git show <commit>:<path>` を打つと
            #   そのコミットの説明文が返るので、blob 以外は索引に入れないこと自体を試す
            sub = git("rev-parse", "HEAD").stdout.strip()
            # **失敗を成功と見分ける** — 黙って飛ばすと、試していない検査が合格として出る
            if must("update-index", git("update-index", "--add", "--cacheinfo",
                                        f"160000,{sub},vendor/mod")) \
                    and must("commit(gitlink)", git("commit", "-qm", "gitlink")):
                sha2 = git("rev-parse", "HEAD").stdout.strip()
                (root / RECORDS / "i.md").write_text(
                    f"---\nslug: i\nstate: verified\ncommit: {sha2}\n---\n"
                    "## 影響範囲(closure)\n\n- vendor/mod\n\n"
                    "## 基本要件の点検\n\n| ID | 判定 | 理由 | 落とし先 |\n|---|---|---|---|\n"
                    "| BR-09 | 非該当 | 秘密を突き合わせる経路が無い | - |\n",
                    encoding="utf-8")
                h_gl, st_gl = scan_record(root, root / RECORDS / "i.md", cfg, {},
                                          Tree(root), True)
                if h_gl:
                    print(f"NG gitlink を証拠にしている: {h_gl}"); ok = False
                if st_gl["unresolved"] != 1:
                    print(f"NG gitlink を未解決として数えていない: {st_gl}"); ok = False

    # ★ 配布する設定そのものを試す — context が散文に当たらないこと。
    #   これを試さないと、緩い印を足した瞬間に、無関係な別ファイルの weak と合成される
    real = find_root(Path(__file__).parent)
    if (real / CONFIG).is_file():
        _ev, _wk, rctx, _sk, _aj = load_config(real)
        prose = ("// Vue accepts v-on:EVENT and @click\n"
                 "# 使い方: cmd <target> を渡す\n"
                 "生成物は `<slug>.md` である\n"
                 "if i<len(xs) { }\n")
        for br, pats in rctx.items():
            for src, rx in pats:
                if rx.search(prose):
                    print(f"NG 配布する context が散文に当たる({br}): {src}"); ok = False
    print("OK check-baseline-verdicts: 偽の非該当の検出 / 接頭辞省略パスの解決 / "
          "判定行の無い BR の識別 / 点検節の無い記録の区別 / "
          "取りこぼしの計数 / 文書の除外 / 該当行の不干渉 / 行番号の保存 / "
          "弱い証拠は context 必須(クロージャ全体で判定) / 混在クロージャは部分的 / "
          "空白を含むパス / gitlink を証拠にしない / commit 時点の中身 / "
          "リポジトリの外を読まない / 判定不能の候補は行ごと未解決 / "
          "配布する context の正規表現が代表的な散文に当たらない / "
          "裁定済みの控え(鍵は記録・BR・パス・パターン・当たった文字列の5つ / pattern と match は完全一致(グロブにしない。match は切り詰めない全文)/ why 無しは適用しない / "
          "裁定は当たった1件だけを飛ばし、同じ行の別ファイル・同じファイルの別パターンの"
          "証拠は残す / 未解決パスが在れば裁定済みでも partial に数える) / "
          "index.md を構築記録に数えない"
          if ok else "NG selftest 失敗")
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    root = find_root(Path(__file__).parent)
    if "--selftest" in argv:
        return selftest()
    quiet = "--quiet" in argv
    use_commit = "--worktree" not in argv
    argv = [a for a in argv if a not in ("--quiet", "--worktree")]
    state = None
    if "--state" in argv:
        i = argv.index("--state")
        if i + 1 >= len(argv):
            print("使い方: --state <building|awaiting-verify|verified>", file=sys.stderr)
            return 2
        state = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]

    rec_dir = root / RECORDS
    if not rec_dir.is_dir():
        print(f"前提エラー: {RECORDS} が無い", file=sys.stderr)
        return 2
    if argv:
        targets = []
        for a in argv:
            p = Path(a)
            cand = p if p.is_file() else rec_dir / f"{p.stem}.md"
            if not cand.is_file():
                print(f"前提エラー: 記録が見つからない: {a}", file=sys.stderr)
                return 2
            targets.append(cand)
    else:
        # `index.md` は記録ではなく索引である(`build-index.py` が生成する)。
        # 数に入れると「点検の節が無い記録が1本ある」と**偽を印字する** —
        # `check-buildrecord.py --all` は同じ除外を持つので終了コード0で通り、
        # 2つの計器が同じ状態について反対のことを言う(実測 2026-09-01)
        targets = sorted(p for p in rec_dir.glob("*.md") if p.name != "index.md")
    if state:
        targets = [t for t in targets
                   if re.search(rf"(?m)^state:\s*{re.escape(state)}\s*$",
                                t.read_text(errors="replace"))]
    return run(root, targets, quiet, use_commit)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
