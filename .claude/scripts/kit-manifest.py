#!/usr/bin/env python3
"""kit-manifest.py — キットが「この版は何でできているか」を持ち、上書き展開の取り残しを特定する。

配布物は前置ディレクトリ無しの tar.gz で、導入は `tar -xzf` の**上書き展開**である。
tar は上書きはするが**削除はしない**。だから前の版にあって今の版で消えた/改名されたファイルは、
展開しても消えずにそのまま残る。残ったスキルやスクリプトは Claude Code からは現役に見えるので、
**廃止したはずの規範が生き続ける**。

`kit-dist.json` は allowlist の「型」であって、その版が実際に何であったかの記録ではない。
展開先でこれを展開しても、取り残しと現役の区別はつかない(どちらも `.claude/skills/` に居る)。
そこで**版ごとに確定したファイル一覧を現物として持ち歩く**のがこのマニフェストである。

    files    : この版を構成するファイルと sha256
    retired  : **過去の版にはあったが、この版には無い**パス(累積)

`retired` があるので、展開先に居る見知らぬファイルを3つに割れる:

  - `retired` に載っている     → **旧版の取り残し**。消してよい(出所がキットだと判っている)
  - `files` にあって中身が違う → 改造されたか壊れている
  - どちらにも無い             → **そのプロジェクトの持ち物**。キットは手を出さない

マニフェスト自身は展開で上書きされるので、展開後は常に「新しい版の」マニフェストになる。
その一覧に無く `retired` に載っているものが取り残しである、という判定が成り立つ。

使い方:

    # 配布する側(キット本流)で
    python3 .claude/scripts/kit-manifest.py update           # マニフェストを作り直す
    python3 .claude/scripts/kit-manifest.py update --check    # 鮮度検査(古ければ非0。CI/make check 用)

    # 導入した側(展開したプロジェクト)で、tar -xzf の直後に
    python3 .claude/scripts/kit-manifest.py check             # 取り残し・改造・欠落・管理外を出す
    python3 .claude/scripts/kit-manifest.py check --strict    # 改造(差異)でも失敗させる

    python3 .claude/scripts/kit-manifest.py --selftest        # 自己検査

終了コード: 0=問題なし 1=取り残しか欠落あり(--strict なら改造も) 2=前提・使い方エラー

**版も日時も持たない。** 配布物はバイト単位で再現可能であることを売りにしており(Makefile)、
生成のたびに変わる値をキットの中に置くとそれが壊れる。どの版かは git が知っている。

`kit-dist.json` の展開は **`kit-patch.py` が正**である。ここには書き写さない(2つ持つと必ずずれる)。
依存ゼロ(標準ライブラリのみ)。
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

MANIFEST_NAME = ".claude/kit-manifest.json"

COMMENT = [
    "この版のキットを構成するファイルと sha256。**手で書かない。**",
    "`python3 .claude/scripts/kit-manifest.py update` が作り直す。",
    "",
    "retired = 過去の版にはあったが、この版には無いパス(累積)。上書き展開は削除をしないので、",
    "これが無いと『旧版の取り残し』と『プロジェクト独自のファイル』を区別できない。",
    "",
    "何がキットの構成要素かの正は kit-dist.json の include。これはその版での確定結果である。",
    "マニュフェスト自身は自分を hash できないので files に載らない。",
    "版番号も生成日時も持たない(配布物の再現性を壊すため。どの版かは git が知っている)。",
]


# ---------------------------------------------------------------- kit-patch.py の再利用

def _load_kit_patch(scripts_dir: Path):
    """`kit-dist.json` の展開ロジックを kit-patch.py から借りる。

    ハイフン入りの名前なので普通の import はできない。**同じ展開を2箇所に持たない**ことが
    要点であり、この読み込みの回りくどさはその対価である。
    """
    p = scripts_dir / "kit-patch.py"
    if not p.is_file():
        die(f"{p} が無い。同梱リストを展開できない(kit-dist.json の正は kit-patch.py が持つ)。")
    spec = importlib.util.spec_from_file_location("_kit_patch", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def collect_kit(root: Path) -> dict[str, bytes]:
    """include を展開して {キット相対パス: 中身}。マニフェスト自身は除く。"""
    kp = _load_kit_patch(root / ".claude" / "scripts")
    files = kp.collect(root, kp.load_dist(root))
    files.pop(MANIFEST_NAME, None)
    return files


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------- マニフェストの読み書き

def manifest_path(root: Path) -> Path:
    return root / MANIFEST_NAME


def read_manifest(root: Path) -> dict | None:
    p = manifest_path(root)
    if not p.is_file():
        return None
    try:
        with p.open(encoding="utf-8") as f:
            m = json.load(f)
    except json.JSONDecodeError as e:
        die(f"{MANIFEST_NAME} が壊れている: {e}")
    if not isinstance(m.get("files"), dict):
        die(f"{MANIFEST_NAME} に files が無い(壊れている)。")
    return m


def build_manifest(root: Path, previous: dict | None) -> dict:
    """現物からマニフェストを組む。retired は前のマニフェストから積み上げる。"""
    files = {rel: sha256(data) for rel, data in collect_kit(root).items()}
    old_files = set((previous or {}).get("files", {}))
    old_retired = set((previous or {}).get("retired", []))
    # 前の版にあって今は無いものを足し、復活したものは落とす。
    retired = sorted((old_retired | old_files) - set(files))
    return {
        "_comment": COMMENT,
        "files": dict(sorted(files.items())),
        "retired": retired,
    }


def dump(m: dict) -> str:
    return json.dumps(m, ensure_ascii=False, indent=2) + "\n"


# ---------------------------------------------------------------- update

def cmd_update(args) -> int:
    root = resolve_root(args)
    previous = read_manifest(root)
    fresh = build_manifest(root, previous)

    if args.check:
        if previous is None:
            print(f"NG  {MANIFEST_NAME} が無い(`update` を実行すること)", file=sys.stderr)
            return 1
        # _comment は説明文なので鮮度の判定に混ぜない。
        same = (previous.get("files") == fresh["files"]
                and previous.get("retired", []) == fresh["retired"])
        if same:
            print(f"OK  {MANIFEST_NAME} は現物と一致 ({len(fresh['files'])} ファイル"
                  f" / retired {len(fresh['retired'])} 件)", file=sys.stderr)
            return 0
        added = sorted(set(fresh["files"]) - set(previous.get("files", {})))
        gone = sorted(set(previous.get("files", {})) - set(fresh["files"]))
        moved = sorted(p for p in set(fresh["files"]) & set(previous.get("files", {}))
                       if fresh["files"][p] != previous["files"][p])
        print(f"NG  {MANIFEST_NAME} が古い(`update` を実行すること)", file=sys.stderr)
        for label, items in (("追加", added), ("削除", gone), ("変更", moved)):
            if items:
                print(f"    {label} {len(items)} 件: {', '.join(items[:5])}"
                      + (" ..." if len(items) > 5 else ""), file=sys.stderr)
        return 1

    manifest_path(root).write_text(dump(fresh), encoding="utf-8")
    newly = sorted(set(fresh["retired"]) - set((previous or {}).get("retired", [])))
    print(f"OK  {MANIFEST_NAME} を更新 ({len(fresh['files'])} ファイル"
          f" / retired {len(fresh['retired'])} 件)", file=sys.stderr)
    if newly:
        print(f"    今回 retired に入った: {', '.join(newly)}", file=sys.stderr)
    return 0


# ---------------------------------------------------------------- check

def classify(root: Path, m: dict) -> dict[str, list[str]]:
    """展開先の現物をマニフェストと突き合わせて4つに割る。"""
    actual = {rel: sha256(data) for rel, data in collect_kit(root).items()}
    files = m.get("files", {})
    retired = set(m.get("retired", []))

    stale, modified, missing, unknown = [], [], [], []
    for rel, h in actual.items():
        if rel in files:
            if files[rel] != h:
                modified.append(rel)
        elif rel in retired:
            stale.append(rel)
        else:
            unknown.append(rel)
    for rel in files:
        if rel not in actual:
            missing.append(rel)
    return {"stale": sorted(stale), "modified": sorted(modified),
            "missing": sorted(missing), "unknown": sorted(unknown)}


def cmd_check(args) -> int:
    root = resolve_root(args)
    m = read_manifest(root)
    if m is None:
        print(f"NG  {MANIFEST_NAME} が無い。**マニフェストを持たない版から上書きされた可能性がある**"
              f"(取り残しを特定できない)。", file=sys.stderr)
        return 1

    r = classify(root, m)
    print(f"## キットの取り残し検査: {root}", file=sys.stderr)
    print(f"   マニフェスト: {len(m['files'])} ファイル / retired {len(m.get('retired', []))} 件",
          file=sys.stderr)

    if r["stale"]:
        print(f"\n  NG  旧版の取り残し {len(r['stale'])} 件"
              f"(**キット由来だと判っている。消してよい**)", file=sys.stderr)
        for p in r["stale"]:
            print(f"        {p}", file=sys.stderr)
        print("      → " + " ".join(["rm"] + r["stale"]), file=sys.stderr)
    else:
        print("  OK  旧版の取り残しなし", file=sys.stderr)

    if r["missing"]:
        print(f"\n  NG  欠落 {len(r['missing'])} 件(展開漏れか、誤って消された)", file=sys.stderr)
        for p in r["missing"]:
            print(f"        {p}", file=sys.stderr)

    if r["modified"]:
        head = "NG " if args.strict else "-- "
        print(f"\n  {head} 差異 {len(r['modified'])} 件"
              f"(このプロジェクトで改造したか、壊れている)", file=sys.stderr)
        for p in r["modified"]:
            print(f"        {p}", file=sys.stderr)
        print("      → 改造したなら `kit-patch.py diff` で本流へ戻す。"
              "心当たりが無いなら壊れている", file=sys.stderr)

    if r["unknown"]:
        print(f"\n  --  キット管理外 {len(r['unknown'])} 件"
              f"(このプロジェクトの持ち物。**触らない**)", file=sys.stderr)
        for p in r["unknown"]:
            print(f"        {p}", file=sys.stderr)

    if args.json:
        json.dump(r, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")

    if r["stale"] or r["missing"]:
        return 1
    if args.strict and r["modified"]:
        return 1
    return 0


# ---------------------------------------------------------------- 雑

def die(msg: str, code: int = 2) -> None:
    print(f"エラー: {msg}", file=sys.stderr)
    sys.exit(code)


def resolve_root(args) -> Path:
    """キットのルート(CLAUDE.md と .claude/ がある場所)。--root が無ければ自分の位置から。"""
    if getattr(args, "root", None):
        root = Path(args.root).resolve()
    else:
        root = Path(__file__).resolve().parent.parent.parent
    if not (root / ".claude").is_dir():
        die(f"{root} に .claude/ が無い(キットのルートではない)。")
    return root


# ---------------------------------------------------------------- 自己検査

def _w(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")


def _fixture(base: Path, skills: list[str]) -> Path:
    """kit-patch.py ごと持つ最小のキットを作る(展開ロジックを借りているので現物が要る)。"""
    root = base
    _w(root / "CLAUDE.md", "# kit\n")
    _w(root / ".claude" / "scripts" / "kit-dist.json", json.dumps({
        "include": ["CLAUDE.md", ".claude/kit-manifest.json", ".claude/skills/"],
        "exclude": ["*/__pycache__/*", "*.pyc"],
    }))
    real = Path(__file__).resolve().parent
    for name in ("kit-patch.py", "kit-manifest.py"):
        _w(root / ".claude" / "scripts" / name, (real / name).read_text(encoding="utf-8"))
    for s in skills:
        _w(root / ".claude" / "skills" / s / "SKILL.md", f"---\nname: {s}\n---\n")
    return root


def selftest() -> int:
    import tempfile

    ok, ng = 0, 0

    def check(cond: bool, label: str) -> None:
        nonlocal ok, ng
        if cond:
            ok += 1
            print(f"  OK  {label}")
        else:
            ng += 1
            print(f"  NG  {label}")

    class A:
        pass

    with tempfile.TemporaryDirectory() as td:
        # --- 版1: スキル a, b
        v1 = _fixture(Path(td) / "v1", ["a", "b"])
        a = A(); a.root = str(v1); a.check = False
        cmd_update(a)
        m1 = read_manifest(v1)
        check(m1 is not None and MANIFEST_NAME not in m1["files"],
              "マニフェストは自分自身を files に載せない")
        check(".claude/skills/a/SKILL.md" in m1["files"], "版1 が a を持つ")
        check(m1["retired"] == [], "版1 の retired は空")

        # --- 鮮度検査
        a.check = True
        check(cmd_update(a) == 0, "update --check: 作った直後は合格")
        _w(v1 / ".claude" / "skills" / "a" / "SKILL.md", "---\nname: a\n---\n変更\n")
        check(cmd_update(a) == 1, "update --check: 現物が変わったら非0")
        a.check = False
        cmd_update(a)

        # --- 版2: b を廃止し c を新設(= 本流での改版)
        v2 = _fixture(Path(td) / "v2", ["a", "c"])
        (v2 / ".claude" / "kit-manifest.json").write_text(
            dump(read_manifest(v1)), encoding="utf-8")   # 版1 のマニフェストを引き継ぐ
        b = A(); b.root = str(v2); b.check = False
        cmd_update(b)
        m2 = read_manifest(v2)
        check(".claude/skills/b/SKILL.md" in m2["retired"],
              "版2 で消えた b が retired に積まれる")
        check(".claude/skills/c/SKILL.md" in m2["files"], "版2 が c を持つ")

        # --- 版1 の上へ版2 を上書き展開したのと同じ状態を作る
        #     (a と c は新しく、b は消えずに残る)
        dst = Path(td) / "dst"
        _fixture(dst, ["a", "b"])                     # 版1 が入っている
        _w(dst / ".claude" / "skills" / "c" / "SKILL.md", "---\nname: c\n---\n")   # 版2 が上書き
        (dst / ".claude" / "kit-manifest.json").write_text(dump(m2), encoding="utf-8")
        _w(dst / ".claude" / "skills" / "own" / "SKILL.md", "---\nname: own\n---\n")  # 独自のもの

        r = classify(dst, m2)
        check(r["stale"] == [".claude/skills/b/SKILL.md"],
              "取り残し(旧版の b)だけを取り残しと判定する")
        check(r["unknown"] == [".claude/skills/own/SKILL.md"],
              "プロジェクト独自のものは取り残しにしない")
        check(r["missing"] == [], "欠落なし")
        check(r["modified"] == [], "差異なし")

        c = A(); c.root = str(dst); c.strict = False; c.json = False
        check(cmd_check(c) == 1, "check: 取り残しがあれば非0")

        # --- 取り残しを消せば合格する
        (dst / ".claude" / "skills" / "b" / "SKILL.md").unlink()
        (dst / ".claude" / "skills" / "b").rmdir()
        check(cmd_check(c) == 0, "check: 取り残しを消せば合格")

        # --- 改造は既定では落とさず、--strict で落ちる
        _w(dst / ".claude" / "skills" / "a" / "SKILL.md", "---\nname: a\n---\n改造\n")
        check(cmd_check(c) == 0, "check: 改造は既定では失敗にしない")
        c.strict = True
        check(cmd_check(c) == 1, "check --strict: 改造でも失敗する")

        # --- 欠落は既定でも落とす
        c.strict = False
        (dst / ".claude" / "skills" / "c" / "SKILL.md").unlink()
        check(cmd_check(c) == 1, "check: 欠落があれば非0")

        # --- 復活したファイルは retired から落ちる
        v3 = _fixture(Path(td) / "v3", ["a", "b", "c"])
        (v3 / ".claude" / "kit-manifest.json").write_text(dump(m2), encoding="utf-8")
        d = A(); d.root = str(v3); d.check = False
        cmd_update(d)
        check(read_manifest(v3)["retired"] == [], "復活したファイルは retired から落ちる")

    print(f"\n{ok} OK / {ng} NG")
    return 0 if ng == 0 else 1


# ---------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="kit-manifest.py",
        description="キットの構成マニフェストを作り、上書き展開の取り残しを特定する。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("使い方:", 1)[-1],
    )
    ap.add_argument("--selftest", action="store_true", help="自己検査")
    sub = ap.add_subparsers()

    u = sub.add_parser("update", help="マニフェストを現物から作り直す(配布する側)")
    u.add_argument("--root", help="キットのルート(既定: このスクリプトの位置から)")
    u.add_argument("--check", action="store_true",
                   help="書き換えずに鮮度だけ見る。古ければ非0")
    u.set_defaults(func=cmd_update)

    c = sub.add_parser("check", help="展開先の取り残し・改造・欠落・管理外を出す(導入した側)")
    c.add_argument("--root", help="キットのルート(既定: このスクリプトの位置から)")
    c.add_argument("--strict", action="store_true", help="差異(改造)でも失敗させる")
    c.add_argument("--json", action="store_true", help="分類を JSON でも出す")
    c.set_defaults(func=cmd_check)

    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if not getattr(args, "func", None):
        ap.print_help(sys.stderr)
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
