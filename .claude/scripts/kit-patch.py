#!/usr/bin/env python3
"""kit-patch.py — キットの改造を控え、本流へ渡すパッチとして出す。

このキットは配布物である。各プロジェクトの `.claude/` は展開されたコピーであり、
**どの状態から改造したのかを記録した場所がどこにも無い**。だから改善を本流へ戻せない。

このツールは、改造する側が改造の直前に自分の姿を控え、あとで差分をパッチにする。
外部のパス(本流のチェックアウト等)を前提にしない。キットの中だけで完結する。

    python3 .claude/scripts/kit-patch.py status                # 改造前に1回。控えが無ければここで取る
    python3 .claude/scripts/kit-patch.py diff --slug <slug>    # 控え → 現在 の unified diff(★成果物)
                                                               #   置き場は道具が決め、絶対パスで出す
    python3 .claude/scripts/kit-patch.py files                 # キットの構成要素を名前順に列挙する
    python3 .claude/scripts/kit-patch.py snapshot              # 控えを取り直す(通常は上の2つが自動でやる)
    python3 .claude/scripts/kit-patch.py --selftest            # 自己検査

`files` は配布側(tarball を作る Makefile 等)が「何を固めるか」を決めるためにある。
**配布と差分抽出で同じ展開ロジックを使う**ことが要点で、両側にリストを書くと必ずずれる。

**控えの取り直しは自動である。** 手で「控えを取り直す」と判断する操作(旧 `snapshot --force`)は
廃止した — 意味を覚えていられない操作は必ず忘れられ、忘れると過去の変更が相乗りしたパッチが出る。
代わりに、取り直すべき瞬間を2つとも機械が知っている:

  * `diff` がパッチを書いたら(`--slug` / `-o`)、**その場で控えを取り直す**(= 次の改善の基準)。
  * 新しい配布物を上書き展開したら `.claude/kit-manifest.json` の指紋が変わる。
    それを見た `status` が**控えを取り直す**(前の版の控えは基準にならない)。

前提は **改善を溜めないこと**。パッチは1本ずつ本流のリポジトリへ**運ぶ**(複製ではなく移動)。
`diff` はパッチを書いた時点で `.claude/improvements/` の作業跡を消す — プロジェクトに残った
改善のメモは、次の配布物と同期したあとに「本流に無いキットの持ち物」として残り続ける。

本流への適用は人間が行う。このツールは**実行すべきコマンド文字列を出すところまで**であり、
本流のリポジトリには触れない(そもそも到達できない)。

依存ゼロ(標準ライブラリのみ)。
"""

from __future__ import annotations

import argparse
import datetime as _dt
import difflib
import fnmatch
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

SNAPSHOT_NAME = ".claude/.kit-snapshot.tar.gz"
DIST_NAME = ".claude/scripts/kit-dist.json"
MANIFEST_NAME = ".claude/kit-manifest.json"
IMPROVEMENTS_DIR = ".claude/improvements"
PATCHES_DIR = ".claude/improvements/patches"
META_MEMBER = "__kit_snapshot__.json"


# ---------------------------------------------------------------- キットの範囲

def kit_root(start: Path | None = None) -> Path:
    """このスクリプトの位置からキットのルート(CLAUDE.md と .claude/ がある場所)を出す。"""
    here = (start or Path(__file__).resolve()).parent
    # <root>/.claude/scripts/kit-patch.py
    return here.parent.parent


def load_dist(root: Path) -> dict:
    p = root / DIST_NAME
    if not p.is_file():
        die(f"{DIST_NAME} が無い。キットの同梱リストが無いと差分の対象を決められない。")
    with p.open(encoding="utf-8") as f:
        d = json.load(f)
    if not d.get("include"):
        die(f"{DIST_NAME} の include が空。")
    return d


def excluded(rel: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel, pat) for pat in patterns)


def collect(root: Path, dist: dict) -> dict[str, bytes]:
    """include に載ったものを {キット相対パス: 中身} で集める。allowlist。

    **配布・控え・差分の3者が、同じ1つの定義(kit-dist.json の include)から出る。**
    以前は控えと差分だけが `.claude/improvements/`(改善の検討メモ)を追加で集め、メモを
    パッチに同梱して本流へ戻していた。その仕組みごと廃止した:

      * 適用されなかった検討は「入らなかった」が結論である(`/kit-improve` §2)。
      * プロジェクトに残ったメモは、新しい配布物と同期したあとも消えず、本流にも
        プロジェクトにも属さない持ち物として次の差分や取り残し判定に混ざる。

    改善の作業跡は、パッチが書けた時点で `cleanup_improvements()` が消す。
    """
    inc = list(dist["include"])
    exc = dist.get("exclude", [])
    out: dict[str, bytes] = {}
    for entry in inc:
        if entry.endswith("/"):
            base = root / entry.rstrip("/")
            if not base.is_dir():
                continue
            for p in sorted(base.rglob("*")):
                if not p.is_file() or p.is_symlink():
                    continue
                rel = p.relative_to(root).as_posix()
                if not excluded(rel, exc):
                    out[rel] = p.read_bytes()
        else:
            p = root / entry
            if p.is_file() and not excluded(entry, exc):
                out[entry] = p.read_bytes()
    return dict(sorted(out.items()))


# ---------------------------------------------------------------- 控え

def snapshot_path(root: Path) -> Path:
    return root / SNAPSHOT_NAME


def kit_fingerprint(root: Path) -> str | None:
    """この版のキットの指紋。`.claude/kit-manifest.json`(版ごとの確定一覧 + sha256)を hash する。

    **プロジェクト側で誰もこのファイルを手で書かない**(作るのは本流の `kit-manifest.py update`)。
    だから指紋が変わった = 新しい配布物を上書き展開した、と言い切れる。控えがどの版のものかを
    キット自身に持たせる唯一の手段であり、これが「控えを取り直す操作を人間に覚えさせない」の
    土台である。マニフェストを持たないキットでは None(入れ替わりは検知できない)。
    """
    p = root / MANIFEST_NAME
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def files_fingerprint(files: dict[str, bytes]) -> str | None:
    """集めた側のマニフェストから指紋を出す(`--from <tarball>` の控えは、その tarball の版が正)。"""
    data = files.get(MANIFEST_NAME)
    return hashlib.sha256(data).hexdigest() if data is not None else None


def read_snapshot(root: Path) -> tuple[dict[str, bytes], dict]:
    sp = snapshot_path(root)
    if not sp.is_file():
        die("控えが無い。先に `python3 .claude/scripts/kit-patch.py status` を実行すること"
            "(status が控えを取る)。\n"
            "  (控えを推測で代用すると『差分なし』を誤って報告することになる)")
    files: dict[str, bytes] = {}
    meta: dict = {}
    with tarfile.open(sp, "r:gz") as tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            data = tf.extractfile(m).read()
            if m.name == META_MEMBER:
                meta = json.loads(data.decode("utf-8"))
            else:
                files[m.name] = data
    return dict(sorted(files.items())), meta


def write_snapshot(root: Path, files: dict[str, bytes], source: str) -> Path:
    sp = snapshot_path(root)
    sp.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        "taken_at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "files": len(files),
        "source": source,
        # どの版を基準にした控えか(kit_fingerprint の docstring)。控えの中身に入っている
        # マニフェストを正とする — `--from <tarball>` のときは現物ではなくその tarball の版。
        "kit": files_fingerprint(files) or kit_fingerprint(root),
    }
    payload = dict(files)
    payload[META_MEMBER] = json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8")
    with tarfile.open(sp, "w:gz") as tf:
        for name in sorted(payload):
            data = payload[name]
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mtime = 0  # 決定性
            info.mode = 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            tf.addfile(info, io.BytesIO(data))
    return sp


def baseline(root: Path, dist: dict) -> tuple[dict[str, bytes] | None, dict, dict[str, str], bool]:
    """控えの状態を1回で出す: (控えの中身, メタ, 未回収の変更, 配布物が入れ替わったか)。

    控えが無ければ第1要素が None(呼ぶ側が取るか止まるかを決める)。**入れ替わりの判定を
    ここ1箇所に閉じる** — `status` は取り直し、`diff` は止まる、と扱いが違うので、判定が
    2箇所に散ると片方だけ直る型の欠陥になる。
    """
    if not snapshot_path(root).is_file():
        return None, {}, {}, False
    old, meta = read_snapshot(root)
    _, changed, _ = make_diff(old, collect(root, dist))
    fp = kit_fingerprint(root)
    redistributed = bool(fp and meta.get("kit") and fp != meta["kit"])
    return old, meta, changed, redistributed


def leftover_patches(root: Path, keep: Path | None = None) -> list[str]:
    """本流へ渡し終えていないパッチ。**パッチは複製ではなく移動**なので、残っていれば未転送。"""
    d = root / PATCHES_DIR
    if not d.is_dir():
        return []
    kept = keep.resolve() if keep else None
    return sorted(p.relative_to(root).as_posix() for p in d.glob("*.patch")
                  if p.is_file() and p.resolve() != kept)


def cleanup_improvements(root: Path, keep: Path | None) -> tuple[list[str], list[str]]:
    """改善の作業跡を片付ける。返すのは (消したもの, 残っている未転送のパッチ)。

    **成果物はパッチ1本だけである。** パッチが書けた時点で、検討メモ・下書き・作業ログといった
    「改善の取り組みに関する情報」は役目を終える。プロジェクトに残すと、新しい配布物と同期した
    あとも消えずに残り(上書き展開は削除をしない)、本流にもプロジェクトにも属さない持ち物として
    次の差分・`kit-manifest.py check` の判定・次の改善の読み物に混ざる。

    `*.patch` は消さない(本流へ渡す実物であり、git 管理外で戻せない)。今回書いたもの以外が
    残っていたら、未転送として名指しして返す。空になったディレクトリは畳む。
    """
    base = root / IMPROVEMENTS_DIR
    removed: list[str] = []
    if base.is_dir():
        kept = keep.resolve() if keep else None
        for p in sorted(base.rglob("*")):
            if not p.is_file() or p.is_symlink():
                continue
            if p.suffix == ".patch" or p.resolve() == kept:
                continue
            p.unlink()
            removed.append(p.relative_to(root).as_posix())
        for d in sorted((p for p in base.rglob("*") if p.is_dir()), reverse=True):
            if not any(d.iterdir()):
                d.rmdir()
        if not any(base.iterdir()):
            base.rmdir()
    return removed, leftover_patches(root, keep)


def source_files(root: Path, dist: dict, src: str | None) -> tuple[dict[str, bytes], str]:
    """控えの中身を、自分自身 / 別ディレクトリ / tarball のいずれかから作る。"""
    if src is None:
        return collect(root, dist), "self"
    p = Path(src).expanduser().resolve()
    if p.is_dir():
        return collect(p, dist), str(p)
    if p.is_file() and p.name.endswith((".tar.gz", ".tgz")):
        with tempfile.TemporaryDirectory() as td:
            with tarfile.open(p, "r:gz") as tf:
                tf.extractall(td)          # noqa: S202 — 自分の配布物のみを対象にする
            return collect(Path(td), dist), str(p)
    die(f"--from に指定されたものが読めない(ディレクトリでも .tar.gz でもない): {src}")


# ---------------------------------------------------------------- 差分

def is_binary(data: bytes) -> bool:
    return b"\x00" in data[:8192]


def decode(data: bytes) -> list[str] | None:
    try:
        return data.decode("utf-8").splitlines(keepends=True)
    except UnicodeDecodeError:
        return None


def make_diff(old: dict[str, bytes], new: dict[str, bytes]) -> tuple[str, dict, list[str]]:
    """unified diff を作る。決定性のため名前順・ラベルに時刻を入れない。"""
    chunks: list[str] = []
    changed: dict[str, str] = {}
    skipped: list[str] = []
    for rel in sorted(set(old) | set(new)):
        a, b = old.get(rel), new.get(rel)
        if a == b:
            continue
        if (a is not None and is_binary(a)) or (b is not None and is_binary(b)):
            skipped.append(rel)
            continue
        alines = decode(a) if a is not None else []
        blines = decode(b) if b is not None else []
        if alines is None or blines is None:
            skipped.append(rel)
            continue
        # 末尾に改行が無いテキストは difflib がそのまま出すので、git apply が読める形に整える
        alines = _ensure_nl(alines)
        blines = _ensure_nl(blines)
        fromfile = f"a/{rel}" if a is not None else "/dev/null"
        tofile = f"b/{rel}" if b is not None else "/dev/null"
        d = list(difflib.unified_diff(alines, blines, fromfile=fromfile, tofile=tofile, n=3))
        if not d:
            continue
        chunks.extend(d)
        changed[rel] = "追加" if a is None else ("削除" if b is None else "変更")
    return "".join(chunks), changed, skipped


def _ensure_nl(lines: list[str]) -> list[str]:
    if lines and not lines[-1].endswith("\n"):
        lines = lines[:-1] + [lines[-1] + "\n"]
    return lines


# [その他] は「キットの構成要素として分類できなかったもの」= プロジェクト固有の改造の疑い、
# として読まれる(report() の注記)。だから**キットの持ち物はここに漏らさず載せる**。
# `.claude/settings.json`(許可リスト)と `.claude/.gitignore` はキットの設定であって
# プロジェクトの改造ではない。
# `.claude/kit-manifest.json` は**わざと載せない** — あれは配布側が版ごとに作り直すもので、
# プロジェクトから手で戻ってくるのは異常である([その他] に出て目に付くのが正しい)。
NORM_PREFIXES = ("CLAUDE.md", "AGENTS.md", ".claude/directions/", ".claude/skills/",
                 ".claude/templates/", ".claude/tools-readme.md", ".claude/settings.json",
                 ".claude/.gitignore")


def classify(changed: dict[str, str]) -> dict[str, list[str]]:
    """3群に分ける。**[検討メモ] 群は廃止した** — `.claude/improvements/` は集めない
    (`collect()` の docstring)。万一パッチに現れたら [その他] に出て目に付くのが正しい。"""
    groups = {"規範": [], "スクリプト": [], "その他": []}
    for rel in changed:
        if rel.startswith(NORM_PREFIXES):
            groups["規範"].append(rel)
        elif rel.startswith(".claude/scripts/"):
            groups["スクリプト"].append(rel)
        else:
            groups["その他"].append(rel)
    return groups


# ---------------------------------------------------------------- 出力

def die(msg: str, code: int = 2) -> None:
    print(f"エラー: {msg}", file=sys.stderr)
    sys.exit(code)


def report(root: Path, changed: dict[str, str], skipped: list[str], out: Path | None) -> None:
    """変更の要約と、渡し方を出す。

    **パッチの在り処は絶対パスで言う。** 相対パス(`-o` に渡した文字列)だけを出していたが、
    受け取る人間の cwd はこのキットのルートとは限らず、「どこにできたのか」を探させていた。
    """
    e = sys.stderr
    groups = classify(changed)
    print(f"\n## 変更 {len(changed)} 件", file=e)
    for name, rels in groups.items():
        if not rels:
            continue
        print(f"\n  [{name}]", file=e)
        for rel in sorted(rels):
            print(f"    {changed[rel]}  {rel}", file=e)
    if skipped:
        print("\n  [バイナリ・非UTF8のため差分に含めなかったもの]", file=e)
        for rel in skipped:
            print(f"    {rel}", file=e)
    if groups["その他"]:
        print("\n  ※ [その他] はキットの構成要素として分類できなかったもの。"
              "プロジェクト固有の改造が混ざっていないか確認すること。", file=e)
    if out is None:
        print("\n  ※ -o を付けていないので、パッチは標準出力へ出しただけで**残っていない**"
              "(控えの取り直しも作業跡の片付けもしていない)。"
              f"\n     `-o {root / PATCHES_DIR}/KIT-<slug>.patch` で書き出すこと。", file=e)
    patch = out if out is not None else Path(f"{root / PATCHES_DIR}/KIT-<slug>.patch")
    print(f"""
## 本流へ渡す(人間が運ぶ。このプロジェクトからは本流に触れない)

  1. **できたパッチはここに在る**(これを本流のリポジトリの inbox/ へ移す):

    {patch}
        →  <claude-md のパス>/inbox/

    **転送手段は問わない**(この道具は関知しない。同じホストなら mv でよい)。
    **複製ではなく移動**である — 渡したらこのプロジェクト側からは消すこと
    (残っている間は `status` が「未転送のパッチ」として出す)。

  2. 本流(claude-md)のリポジトリで当てる:

    make patch DRYRUN=1   # inbox/ のパッチが当たるかだけ見る
    make patch            # 当てる

  KIT= は本流にキットが2つ以上あるときだけ要る(1つなら検出される)。
  本流とプロジェクトが同じホストなら `make patch FROM={root}` でも当てられる。

  **`git apply` を手で打たないこと。** 本流のリポジトリ直下には配布対象ではない作業用の
  `.claude/` が同居していて、素の `git apply -p1` はそちらへ当たる —
  「直したのに配布物に入らない」で終わる。`make patch` は宛先を `--directory=<KIT>` で
  明示し、キットの外を触るパッチを弾く。
""", file=e)


# ---------------------------------------------------------------- サブコマンド

def cmd_snapshot(args) -> int:
    """控えを取り直す。**通常は `status` と `diff` が自動で取るので、これを打つ場面は少ない。**

    `--from` は「基準はこれだ」と人が名指しする救済路なので、無条件で上書きする。
    それ以外で未回収の変更を踏み潰す操作は用意しない(旧 `--force`)— 踏み潰したい変更が
    あるならまず `diff` でパッチにする。捨てるつもりなら `--from <キットのルート>`。
    """
    root = kit_root()
    dist = load_dist(root)
    if getattr(args, "force", False):
        die("--force は廃止した。控えの取り直しは自動である:\n"
            "  * `diff -o <パッチ>` が成功したら、その場で取り直す(次の改善の基準)。\n"
            "  * 新しい配布物を上書き展開した後は `status` が取り直す。\n"
            "  どちらでもなく未回収の変更を捨てたいときだけ: snapshot --from " + str(root))
    if args.frm is None:
        _, meta, changed, redistributed = baseline(root, dist)
        if changed and not redistributed:
            die(f"未回収の変更が {len(changed)} 件ある({meta.get('taken_at')} の控え)。\n"
                "  先に `diff --slug <slug>` でパッチにすること"
                "(diff は成功したら控えを自動で取り直す)。\n"
                f"  この変更を捨てるつもりなら、現物を基準として上書きする: snapshot --from {root}")
    files, source = source_files(root, dist, args.frm)
    p = write_snapshot(root, files, source)
    print(f"控えた: {p.relative_to(root)} ({len(files)} ファイル, source={source})", file=sys.stderr)
    return 0


def cmd_diff(args) -> int:
    root = kit_root()
    dist = load_dist(root)
    # **パッチの置き場は道具が持つ。** 呼ぶ側(スキル・手順書・人間の記憶)に書き写させると、
    # 「どこにできるのか」を探す手間と、置き場の食い違いが同時に生まれる。
    if getattr(args, "slug", None):
        if args.out:
            die("--slug と -o は同時に使えない(出力先が2つになる)。"
                "置き場を道具に決めさせるなら --slug だけにすること。")
        args.out = str(root / PATCHES_DIR / f"KIT-{args.slug}.patch")
    old, meta, _, redistributed = baseline(root, dist)
    if old is None:
        die("控えが無い。先に `python3 .claude/scripts/kit-patch.py status` を実行すること"
            "(status が控えを取る)。\n"
            "  (控えを推測で代用すると『差分なし』を誤って報告することになる)")
    if redistributed:
        die(f"控えは前の版のもの({meta.get('taken_at')})。新しい配布物を上書き展開したあとに\n"
            "  このまま差分を取ると、**本流側の変更が丸ごとパッチに乗る**。\n"
            "  `status` を実行して控えを取り直し(取り直しはそこで自動で起きる)、\n"
            "  その後の編集分だけをパッチにすること。")
    new = collect(root, dist)
    text, changed, skipped = make_diff(old, new)
    if not changed:
        print(f"差分なし({meta.get('taken_at')} の控えと一致)。パッチは作らない。", file=sys.stderr)
        return 0
    # 先頭の注記。最初の `---` より前の行は git apply も patch(1) も読み飛ばすので安全。
    # **控えの日時をパッチ自身に刻む**のが要点: 古い控えのまま出した差分を、受け取った人間が
    # 「今回の改善だけ」と誤解するのを防ぐ(この日時が改善の開始時刻と合わない差分は疑うこと)。
    # **キット名を刻む。** 本流には規範が複数在り、同名のファイルを持つ — 名乗らないパッチは、
    # 当てる人間が総当たりで宛先を探すことになる(2026-08-22 に実際に起きた)。
    # **宛先の取り違えは、当てた側でも当てられた側でも気付かれない唯一の事故である。**
    kit_name = dist.get("kit")
    head = f"# kit-patch.py — 変更 {len(changed)} 件\n"
    if kit_name:
        head += f"# キット: {kit_name}\n"
    else:
        print("注意: kit-dist.json に `kit`(このキットの名前)が無いので、パッチは宛先を"
              "名乗れない。\n  本流では `make patch KIT=<キット名>` の指定が要る。",
              file=sys.stderr)
    text = (head
            + f"# 控え: {meta.get('taken_at')} (source={meta.get('source')}, "
            f"{meta.get('files')} ファイル)\n"
            f"# 適用: git apply -p1 <このファイル>(キットのルートで)\n") + text
    print(f"控えの日時: {meta.get('taken_at')} (source={meta.get('source')})\n"
          "  ※ この日時が今回の改善の開始時刻と合わないなら、"
          "前回の控えのまま差分を取っている(過去の変更が混ざる)。", file=sys.stderr)
    if args.out:
        outp = Path(args.out)
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(text, encoding="utf-8")
        outp = outp.resolve()   # 以降は絶対パスで言う(在り処を探させない)
        print(f"書いた: {outp} ({len(text.splitlines())} 行)", file=sys.stderr)
        # パッチが書けた = 成果物が在る。ここが「改善1件の終わり」なので、後始末を機械が済ませる。
        removed, left = cleanup_improvements(root, outp)
        write_snapshot(root, new, f"diff:{outp.name}")
        print(f"控えを取り直した: 今の姿が次の改善の基準になる(手で取り直す操作は無い)\n"
              "  ※ このパッチを本流へ渡さないと、この改善は次の差分に出ない。"
              "出し直すには `snapshot --from <展開に使った tarball>`。\n"
              "     だから改善は溜めずに1本ずつ返すこと。", file=sys.stderr)
        if removed:
            print(f"改善の作業跡を削除した: {len(removed)} 件"
                  "(成果物はパッチ1本。残すと次の配布物と同期したあとに居残る)", file=sys.stderr)
            for rel in removed:
                print(f"    {rel}", file=sys.stderr)
        if left:
            print(f"未転送のパッチが {len(left)} 本ある。先に本流へ渡すこと"
                  "(残っていると、どれが未反映か判らなくなる):", file=sys.stderr)
            for rel in left:
                print(f"    {root / rel}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    report(root, changed, skipped, outp if args.out else None)
    return 0


def cmd_files(args) -> int:
    """キットの構成要素を名前順で標準出力へ。配布側が `tar -T` の入力にする。"""
    root = kit_root()
    for rel in collect(root, load_dist(root)):
        sys.stdout.write(rel + ("\0" if args.null else "\n"))
    return 0


def cmd_status(args) -> int:
    """控えの状態を出す。**足りなければここで整える**(改造前に打つ唯一のコマンド)。

    控えが無い/前の版のものである、という2つの状態は、人間が意味を覚えていなくても機械が
    判る。だから「取り直すべきか」を人間に判断させない — 判断させていた間、その操作は
    忘れられ、過去の変更が相乗りしたパッチが出ていた。
    """
    root = kit_root()
    dist = load_dist(root)
    cur = collect(root, dist)
    e = sys.stderr
    print(f"キットのルート : {root}", file=e)
    print(f"同梱リスト     : {DIST_NAME} (include {len(dist['include'])} 件)", file=e)
    print(f"現在のファイル : {len(cur)} 件", file=e)
    print(f"パッチの置き場 : {root / PATCHES_DIR}/KIT-<slug>.patch"
          "  ← `diff --slug <slug>` がここに書く", file=e)
    old, meta, changed, redistributed = baseline(root, dist)
    if old is None:
        write_snapshot(root, cur, "self")
        print("控え           : 無かったので今の姿を控えた(ここが基準になる)", file=e)
        print("  ※ すでにキットを編集していたなら、その編集は控えの中に入った = 差分に出ない。\n"
              "     展開に使った配布 tarball があるなら、それを基準に取り直すこと:\n"
              "       python3 .claude/scripts/kit-patch.py snapshot --from <tarball>", file=e)
    elif redistributed:
        write_snapshot(root, cur, "self")
        print(f"控え           : 前の版のものだった({meta.get('taken_at')})ので取り直した", file=e)
        print("  ※ 新しい配布物を上書き展開した後である(kit-manifest.json の指紋が変わった)。\n"
              "     取り直さないと、本流側の変更が丸ごと次のパッチに乗る。ここが新しい基準。", file=e)
        if changed:
            print(f"  ※ 前の控えとの差 {len(changed)} 件は、この取り直しで基準側に入った"
                  "(上書き展開で消えた編集も含む)。", file=e)
    else:
        print(f"控え           : {meta.get('taken_at')} / {meta.get('files')} ファイル "
              f"/ source={meta.get('source')}", file=e)
        print(f"未回収の変更   : {len(changed)} 件"
              + ("(先に `diff --slug <slug>` でパッチにすること)" if changed else ""), file=e)
    left = leftover_patches(root)
    if left:
        print(f"未転送のパッチ : {len(left)} 本(本流へ渡したらプロジェクト側には残さない)", file=e)
        for rel in left:
            print(f"    {root / rel}", file=e)
    return 0


# ---------------------------------------------------------------- 自己検査

def _w(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")


def selftest() -> int:
    """意図的に壊したフィクスチャで、出すべきものを出し、出してはならないものを出さないことを示す。"""
    ok = True

    def check(label: str, cond: bool) -> None:
        nonlocal ok
        print(f"  {'OK ' if cond else 'NG '} {label}", file=sys.stderr)
        ok = ok and cond

    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "kit"
        # キットの模型。実物と同じ位置関係(<root>/.claude/scripts/)にする。
        _w(root / "CLAUDE.md", "rule A\nrule B\n")
        _w(root / ".claude/directions/relations.md", "norm 1\n")
        _w(root / ".claude/skills/x/SKILL.md", "skill\n")
        _w(root / ".claude/improvements/KIT-a.md", "memo\n")
        _w(root / ".claude/improvements/patches/KIT-old.patch", "--- a/x\n+++ b/x\n")
        _w(root / ".claude/kit-manifest.json", '{"files":{"CLAUDE.md":"aaa"}}\n')
        _w(root / ".claude/scripts/keep.py", "print(1)\n")
        _w(root / ".claude/scripts/x.local.json", '{"a":1}\n')
        _w(root / ".claude/scripts/__pycache__/k.pyc", "junk\n")
        # include に無いもの(実行状態・資格情報の模型)
        _w(root / ".claude/sessions/s1.json", "session\n")
        _w(root / ".claude/history.jsonl", "hist\n")
        _w(root / ".claude/.credentials.json", '{"token":"SECRET"}\n')
        _w(root / "docs/03-impl/index.md", "ssot\n")
        dist = json.loads((Path(__file__).parent / "kit-dist.json").read_text(encoding="utf-8")) \
            if (Path(__file__).parent / "kit-dist.json").is_file() else None
        if dist is None:
            die("selftest: 同じディレクトリに kit-dist.json が無い")
        _w(root / DIST_NAME, json.dumps(dist, ensure_ascii=False, indent=2))

        base = collect(root, dist)
        check("(e) include に無い実行状態・資格情報を集めない",
              not any(k.startswith((".claude/sessions", ".claude/history", ".claude/.credentials"))
                      for k in base))
        check("(d) *.local.json を集めない", ".claude/scripts/x.local.json" not in base)
        check("(f) __pycache__ を集めない", not any("__pycache__" in k for k in base))
        check("docs/ を集めない", not any(k.startswith("docs/") for k in base))
        check("(j) 改善の作業跡(.claude/improvements/)を集めない",
              not any(k.startswith(".claude/improvements") for k in base))

        # 改造する
        _w(root / "CLAUDE.md", "rule A\nrule B modified\n")                 # (a)
        _w(root / ".claude/directions/new.md", "norm 2\n")                  # (b)
        _w(root / ".claude/improvements/KIT-b.md", "new memo\n")            # (j)
        (root / ".claude/skills/x/SKILL.md").unlink()                       # (c)
        _w(root / ".claude/scripts/x.local.json", '{"a":2}\n')              # (d)
        _w(root / ".claude/sessions/s1.json", "session changed\n")          # (e)
        _w(root / ".claude/.credentials.json", '{"token":"SECRET2"}\n')     # (e)
        _w(root / "docs/03-impl/index.md", "ssot changed\n")                # (e)
        _w(root / ".claude/scripts/__pycache__/k.pyc", "junk2\n")           # (f)

        new = collect(root, dist)
        text, changed, _ = make_diff(base, new)
        check("(a) 既存ファイルの変更が出る", changed.get("CLAUDE.md") == "変更")
        check("(b) 新規ファイルが出る", changed.get(".claude/directions/new.md") == "追加")
        check("(c) 削除が出る", changed.get(".claude/skills/x/SKILL.md") == "削除")
        check("(j) 改善の作業跡はパッチに乗らない",
              not any(k.startswith(".claude/improvements") for k in changed))
        check("(d) *.local.json の変更は出ない", ".claude/scripts/x.local.json" not in changed)
        check("(e) 実行状態・資格情報・docs/ の変更は出ない",
              not any(k.startswith((".claude/sessions", ".claude/history",
                                    ".claude/.credentials", "docs/")) for k in changed))
        check("(e) 資格情報の中身がパッチ本文に現れない", "SECRET" not in text)
        check("(f) __pycache__ の変更は出ない", not any("__pycache__" in k for k in changed))
        check("新規ファイルは /dev/null から始まる", "--- /dev/null" in text)
        check("削除は /dev/null で終わる", "+++ /dev/null" in text)

        # (h) 決定性
        t2, _, _ = make_diff(base, new)
        check("(h) 2回実行して同一バイト列", text == t2)

        # (g) 控えが無い状態
        r2 = Path(td) / "kit2"
        shutil.copytree(root, r2)
        code = subprocess.run(
            [sys.executable, "-c",
             "import sys;sys.path.insert(0,%r);import importlib.util as u;"
             "s=u.spec_from_file_location('m',%r);m=u.module_from_spec(s);s.loader.exec_module(m);"
             "m.read_snapshot(__import__('pathlib').Path(%r))"
             % (str(Path(__file__).parent), str(Path(__file__)), str(r2))],
            capture_output=True, text=True)
        check("(g) 控えが無ければ非0で止まる(『差分なし』と言わない)",
              code.returncode != 0 and "控えが無い" in code.stderr)

        # (i) 往復: 出したパッチを基準ツリーに当てると現在のツリーと一致する
        if shutil.which("git"):
            r3 = Path(td) / "kit3"
            r3.mkdir()
            for rel, data in base.items():
                p = r3 / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(data)
            pf = Path(td) / "rt.patch"
            # 先頭注記を付けた状態で当たること(cmd_diff が実際に書く形)
            pf.write_text("# kit-patch.py — 変更 3 件\n# 控え: 1970-01-01T00:00:00+00:00\n" + text,
                          encoding="utf-8")
            res = subprocess.run(["git", "apply", "-p1", str(pf)], cwd=r3,
                                 capture_output=True, text=True)
            applied = collect(r3, dist) if res.returncode == 0 else {}
            expect = {k: v for k, v in new.items()}
            check("(i) 出したパッチを当てると現在のツリーと一致する(往復)",
                  res.returncode == 0 and applied == expect)
        else:
            print("  --  (i) git が無いので往復検証はスキップ", file=sys.stderr)

        # --- 控えの取り直しを人間に判断させない仕組み(旧 snapshot --force の置き換え) ---

        # (k) 控えが無い状態を baseline() が言い分ける(die しない = 呼ぶ側が取れる)
        r4 = Path(td) / "kit4"
        shutil.copytree(root, r4)
        (r4 / SNAPSHOT_NAME).unlink(missing_ok=True)
        old4, _, _, _ = baseline(r4, dist)
        check("(k) 控えが無ければ baseline() は None を返す", old4 is None)

        # (l) 配布物の入れ替わりを kit-manifest.json の指紋で検知する。
        #     **ここが自動取り直しの唯一の根拠**なので、指紋が変わらない/変わるの両方を見る。
        write_snapshot(r4, collect(r4, dist), "self")
        _w(r4 / "CLAUDE.md", "rule A\nrule B edited locally\n")   # 手元の改造は入れ替わりではない
        _, _, ch4, redist4 = baseline(r4, dist)
        check("(l) 手元の改造は『入れ替わり』にしない", bool(ch4) and not redist4)
        _w(r4 / ".claude/kit-manifest.json", '{"files":{"CLAUDE.md":"bbb"}}\n')  # 新しい版を上書き展開
        _, _, _, redist5 = baseline(r4, dist)
        check("(l) マニフェストが変わったら入れ替わりと判る", redist5)

        # (m) マニフェストを持たないキットでは入れ替わりを主張しない(誤検知しない)
        r5 = Path(td) / "kit5"
        shutil.copytree(root, r5)
        (r5 / ".claude/kit-manifest.json").unlink()
        write_snapshot(r5, collect(r5, dist), "self")
        _, _, _, redist6 = baseline(r5, dist)
        check("(m) マニフェストが無ければ入れ替わりと言わない", not redist6)

        # (n) パッチが書けたら作業跡を消す。**パッチは消さない**(本流へ渡す実物)。
        keep = r5 / PATCHES_DIR / "KIT-now.patch"
        _w(keep, "--- a/CLAUDE.md\n+++ b/CLAUDE.md\n")
        _w(r5 / ".claude/improvements/KIT-a.md", "memo\n")
        _w(r5 / ".claude/improvements/notes/draft.md", "draft\n")
        removed, left = cleanup_improvements(r5, keep)
        check("(n) 検討メモと下書きを消す",
              {".claude/improvements/KIT-a.md", ".claude/improvements/notes/draft.md"}
              <= set(removed) and not any(r.endswith(".patch") for r in removed))
        check("(n) 今回のパッチは残す", keep.is_file())
        check("(n) 空になったディレクトリを畳む", not (r5 / ".claude/improvements/notes").exists())
        check("(n) 未転送の旧パッチを名指しする",
              left == [".claude/improvements/patches/KIT-old.patch"])
        check("(n) 旧パッチは消さない(git 管理外で戻せない)",
              (r5 / PATCHES_DIR / "KIT-old.patch").is_file())

        # (o) 作業跡が無いときに空振りしない(improvements/ 自体が無いキット)
        r6 = Path(td) / "kit6"
        shutil.copytree(root, r6)
        shutil.rmtree(r6 / ".claude/improvements")
        check("(o) improvements/ が無くても落ちない", cleanup_improvements(r6, None) == ([], []))

    print(f"\nselftest: {'PASS' if ok else 'FAIL'}", file=sys.stderr)
    return 0 if ok else 1


# ---------------------------------------------------------------- 入口

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="kit-patch.py",
        description="キットの改造を控え、本流へ渡すパッチとして出す(外部パスに依存しない)")
    ap.add_argument("--selftest", action="store_true", help="自己検査を実行する")
    sub = ap.add_subparsers(dest="cmd")

    s = sub.add_parser("snapshot", help="控えを取り直す(通常は status / diff が自動でやる)")
    s.add_argument("--from", dest="frm", metavar="DIR|TARBALL",
                   help="基準を名指しする救済路(既に改造済みのキットを後追いで記録する)。"
                        "無条件で上書きする。既定は自分自身")
    # 廃止した旧オプション。**受け付けて理由を言う**(argparse の「unrecognized arguments」だけでは
    # 何が起きたのか判らず、手や古い手順書が打ち続ける)。
    s.add_argument("--force", action="store_true", help=argparse.SUPPRESS)
    s.set_defaults(func=cmd_snapshot)

    d = sub.add_parser("diff", help="控え → 現在 の unified diff を出す(書き出すと控えも取り直す)")
    d.add_argument("--slug", metavar="SLUG",
                   help="改善の slug。出力先を道具が決める "
                        f"({PATCHES_DIR}/KIT-<slug>.patch)。**通常はこちらを使う**")
    d.add_argument("-o", "--out", metavar="FILE", help="出力先を明示する。省略時は標準出力")
    d.set_defaults(func=cmd_diff)

    f = sub.add_parser("files", help="キットの構成要素を名前順に列挙する(配布側の tar -T 用)")
    f.add_argument("-0", "--null", action="store_true", help="NUL 区切りで出す")
    f.set_defaults(func=cmd_files)

    t = sub.add_parser("status", help="控えの状態(無い/前の版ならここで取り直す)・未回収の変更件数")
    t.set_defaults(func=cmd_status)

    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if not getattr(args, "func", None):
        ap.print_help(sys.stderr)
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
