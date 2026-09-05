#!/usr/bin/env python3
"""キット専用のツール環境を用意し、利用可能な精度(Tier)を報告する。

方針(.claude/directions/callgraphs.md §5.9):
  ・**pip は必ずキット専用 venv (.claude/.venv) の中で使う。** システムの Python にも、
    対象プロジェクトの環境にも何も入れない。ツール側の都合でプロジェクトを変えない。
  ・**Tier2(既定)は venv の中だけで完結する。** ホストの言語ツールチェーンを要求しない。
  ・**ホストのツールチェーンを使う任意ツールは opt-in。**
    このスクリプトは**検出するだけで、既定では何もインストールしない**。
    `--host-tools` を明示されたときだけ、**プロジェクトが既に持っている** Go / Node を使って
    `.claude/.tools/` の中にだけ入れる(グローバルにも sudo でも入れない)。
  ・**任意ツール(--host-tools)はどれが無くても動かなくなることはない。** 精度が
    Tier2 → Tier3 と落ちるだけで、落ちたことは必ず報告される。
  ・**必須依存(venv の tree-sitter・PyYAML)が無いときは違う。** Go / TypeScript / infra の
    解析は縮退せず、build-callgraphs.py が起動時に直し方を1行言って終了コード2で止まる
    (正規表現の縮退経路は存在しない — inspection-17 判断1)。

使い方:
    python3 .claude/scripts/setup-tools.py             # venv を用意して依存を入れる
    python3 .claude/scripts/setup-tools.py --check      # 何も変更せず現状だけ報告
    python3 .claude/scripts/setup-tools.py --host-tools # 任意ツールも .claude/.tools/ に入れる
    python3 .claude/scripts/setup-tools.py --clean      # .venv と .tools を削除

終了コード: 0=成功 1=用意できなかったものがある 2=使い方・環境エラー
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

VENV_DIR = ".claude/.venv"
TOOLS_DIR = ".claude/.tools"
REQUIREMENTS = ".claude/scripts/requirements.txt"
LOCKFILE = ".claude/scripts/requirements.lock"

# ホストのツールチェーンを使う任意ツール。**キットは入れ方を知っているだけで、既定では入れない。**
# installer は「プロジェクトが既に持っているツールチェーン」を使うものだけを書く。
# 無くても Tier2 は成立する(代替があるか、精度が落ちるだけ)。
HOST_TOOLS = {
    "hcl2json": {
        "language": "infra",
        "needs": "go",
        "install": ["go", "install", "github.com/tmccombs/hcl2json@latest"],
        "note": "Terraform 用。python-hcl2(venv)でも代替できるので必須ではない",
    },
}


def find_root(start: Path | None = None) -> Path:
    cur = (start or Path.cwd()).resolve()
    for cand in [cur, *cur.parents]:
        if (cand / "CLAUDE.md").is_file() and (cand / ".claude").is_dir():
            return cand
    return cur


def wanted_requirements(root: Path) -> list[str]:
    path = root / REQUIREMENTS
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.append(line)
    return out


def venv_python(root: Path) -> Path:
    return root / VENV_DIR / "bin" / "python3"


def run(cmd: list[str], cwd: Path, merge_err: bool = True) -> tuple[int, str]:
    """既定では stdout と stderr を連結して返す(失敗の理由は stderr にしか出ないため)。

    **`merge_err=False` は、出力そのものを機械が読むときに使う。** `pip freeze` の結果は
    そのまま `requirements.lock` の中身になるので、pip の警告(キャッシュ不可の環境で出る
    `WARNING: The directory ... is not owned by the current user`)が混ざると、
    **依存の一覧に日本語でも版でもない行が固定される**(2026-08-31 に実測)。
    """
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=900)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    out = (p.stdout + p.stderr) if merge_err else p.stdout
    return p.returncode, out.strip()


# --------------------------------------------------------------------------- venv

def ensure_venv(root: Path, reqs: list[str], check_only: bool) -> tuple[bool, list[str]]:
    """(用意できたか, メッセージ)。依存が無ければ venv も作らない。"""
    msgs: list[str] = []
    py = venv_python(root)

    if not reqs:
        if py.is_file():
            msgs.append(f"venv: 存在するが依存が0件({REQUIREMENTS} が空)。`--clean` で消してよい")
        else:
            msgs.append("venv: **不要**(現在の依存は0件。Python 抽出器は標準ライブラリだけで動く)")
        return True, msgs

    if not py.is_file():
        if check_only:
            msgs.append(f"venv: **未作成**(依存 {len(reqs)} 件が要る) → `setup-tools.py` を実行すること")
            return False, msgs
        code, out = run([sys.executable, "-m", "venv", str(root / VENV_DIR)], root)
        if code != 0:
            msgs.append(f"venv: 作成に失敗した — {out.splitlines()[-1] if out else '原因不明'}")
            msgs.append("  Debian/Ubuntu なら `apt install python3-venv` が要る可能性がある"
                        "(これはホスト側の作業)")
            return False, msgs
        msgs.append(f"venv: 作成した({VENV_DIR})")

    if check_only:
        code, out = run([str(py), "-m", "pip", "freeze"], root, merge_err=False)
        have = {l.split("==")[0].lower() for l in out.splitlines() if "==" in l}
        missing = [r for r in reqs if r.split("=")[0].split("[")[0].strip().lower() not in have]
        if missing:
            msgs.append(f"venv: 依存が不足 — {', '.join(missing)}")
            return False, msgs
        msgs.append(f"venv: 最新(依存 {len(reqs)} 件)")
        return True, msgs

    # **必ず requirements.txt を対象にする。** lock だけを見ると、requirements.txt に足した
    # 新しい依存が永遠に入らない(lock が古い状態を固定してしまう)。
    # lock は「制約」として渡す — 既存の版は固定したまま、新しいものだけ解決される。
    lock = root / LOCKFILE
    cmd = [str(py), "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
           "-r", str(root / REQUIREMENTS)]
    if lock.is_file():
        cmd += ["-c", str(lock)]
    code, out = run(cmd, root)
    relocked = False
    if code != 0 and lock.is_file():
        code, out = run(cmd[:-2], root)      # 制約が矛盾したら制約なしで解決し直す
        relocked = code == 0
    if code != 0:
        msgs.append("venv: 依存のインストールに失敗した。pip の出力(末尾):")
        for line in (out.splitlines()[-10:] if out else ["(出力なし。原因不明)"]):
            msgs.append("  " + line)
        msgs.append(f"  再現: {py} -m pip install -r {root / REQUIREMENTS}")
        return False, msgs

    code, out = run([str(py), "-m", "pip", "freeze"], root, merge_err=False)
    if code == 0:
        lock.write_text(out + "\n", encoding="utf-8")
        msgs.append(f"venv: 依存を導入し、実際のバージョンを {LOCKFILE} に固定した")
        if relocked:
            # 固定していた版が動いたことを黙らせない(原則8と同型)
            msgs.append(f"  注意: {LOCKFILE} の制約が矛盾したため制約なしで解決し直し、"
                        f"lock を更新した。差分: git diff {LOCKFILE}")
    return True, msgs


# --------------------------------------------------------------------------- 任意ツール

def tools_bin(root: Path) -> list[Path]:
    return [root / TOOLS_DIR / "bin", root / TOOLS_DIR / "node_modules" / ".bin"]


def which_tool(root: Path, name: str) -> str | None:
    for d in tools_bin(root):
        cand = d / name
        if cand.is_file() and os.access(cand, os.X_OK):
            return str(cand)
    return shutil.which(name)


def survey_host_tools(root: Path) -> list[dict]:
    rows = []
    for name, spec in sorted(HOST_TOOLS.items()):
        rows.append({
            "tool": name,
            "language": spec["language"],
            "found": which_tool(root, name),
            "toolchain": spec["needs"],
            "toolchain_found": shutil.which(spec["needs"]) is not None,
            "note": spec["note"],
        })
    return rows


def install_host_tools(root: Path, rows: list[dict]) -> list[str]:
    msgs: list[str] = []
    (root / TOOLS_DIR / "bin").mkdir(parents=True, exist_ok=True)
    for row in rows:
        if row["found"]:
            msgs.append(f"{row['tool']}: 既にある({row['found']})")
            continue
        if not row["toolchain_found"]:
            msgs.append(f"{row['tool']}: **入れない** — `{row['toolchain']}` がホストに無い。"
                        "キットはツールチェーンをインストールしない(ホスト側の判断)")
            continue
        spec = HOST_TOOLS[row["tool"]]
        # 出力先は**絶対パス**に解決する。相対のままだと cwd(ソースディレクトリ)側に
        # 書かれてしまい、「導入した」と報告しながら実際には所定の場所に無い状態になる。
        binpath = str((root / TOOLS_DIR / "bin").resolve())
        install = [a.replace("{BIN}", binpath) for a in spec["install"]]
        env = os.environ.copy()
        if spec["needs"] == "go":
            env["GOBIN"] = str(root / TOOLS_DIR / "bin")
            env.setdefault("GOFLAGS", "-mod=mod")
        try:
            p = subprocess.run(install, cwd=root / spec.get("cwd", "."), env=env,
                               capture_output=True, text=True, timeout=900)
        except (OSError, subprocess.TimeoutExpired) as exc:
            msgs.append(f"{row['tool']}: 失敗 — {exc}")
            continue
        if p.returncode != 0:
            tail = (p.stdout + p.stderr).strip().splitlines()
            msgs.append(f"{row['tool']}: 失敗 — {tail[-1] if tail else '原因不明'}")
            continue
        if which_tool(root, row["tool"]):
            msgs.append(f"{row['tool']}: {TOOLS_DIR} に導入した(グローバルには入れていない)")
        else:
            msgs.append(f"{row['tool']}: **導入したはずだが見つからない**"
                        f"(想定: {TOOLS_DIR}/bin/{row['tool']})")
    return msgs


# --------------------------------------------------------------------------- 報告

def tier_table(root: Path, reqs: list[str]) -> list[list[str]]:
    cfg_path = root / ".claude/scripts/callgraph-config.json"
    enabled: dict[str, bool] = {}
    if cfg_path.is_file():
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        enabled = {k: bool(v.get("enabled")) for k, v in cfg.get("languages", {}).items()}

    have_venv = venv_python(root).is_file() or not reqs
    rows = []
    for lang in sorted(enabled):
        if not enabled[lang]:
            rows.append([lang, "-", "設定で無効"])
        elif lang == "python":
            rows.append([lang, "2", "標準ライブラリの ast のみ。**外部依存なし**"])
        elif lang == "infra":
            rows.append([lang, "2", "YAML/JSON は venv、Terraform は hcl2json か python-hcl2"])
        elif lang in ("shell", "make"):
            # 正規表現抽出器しか無いので**常に Tier 3**。外部依存が無いので venv の有無に依らない。
            rows.append([lang, "3", "正規表現のみ(**呼び出し関係は不完全**)。**外部依存なし**"])
        elif have_venv and reqs:
            rows.append([lang, "2", "venv の tree-sitter"])
        else:
            # 正規表現の縮退経路は**存在しない**(inspection-17 判断1)。venv が無ければ
            # build-callgraphs は起動時に止まる — 嘘の Tier を報告しない。
            rows.append([lang, "×", "**venv が無いと動かない(build-callgraphs が起動時に"
                                    "止まる)** — setup-tools.py を実行すること"])
    return rows


def main(argv: list[str]) -> int:
    if any(a in ("-h", "--help") for a in argv[1:]):
        print(__doc__)   # 明示要求は 0。使い方エラーの 2 と区別する(tools-readme §2)
        return 0
    flags = set(argv[1:])
    if flags - {"--check", "--host-tools", "--clean"}:
        print(__doc__)
        return 2

    root = find_root()
    reqs = wanted_requirements(root)

    if "--clean" in flags:
        removed = []
        for d in (root / VENV_DIR, root / TOOLS_DIR):
            if d.exists():
                shutil.rmtree(d)
                removed.append(str(d.relative_to(root)))
        print("## ツール環境の削除")
        print("  削除: " + (", ".join(removed) if removed else "なし"))
        print("  → `setup-tools.py` でいつでも再構築できる。")
        return 0

    check_only = "--check" in flags
    print("## キット専用ツール環境" + ("(--check: 変更しない)" if check_only else ""))
    print(f"  場所: {VENV_DIR} / {TOOLS_DIR}(どちらも git 管理外)")
    print("  **対象プロジェクトの環境には何も入れない。**")
    print()

    ok, msgs = ensure_venv(root, reqs, check_only)
    for m in msgs:
        print("  " + m)

    host_tools = survey_host_tools(root)
    print()
    print("### ホストのツールチェーンを使う任意ツール(opt-in。既定では入れない)")
    print("| ツール | 用途 | 状態 | 必要なツールチェーン | 備考 |")
    print("|---|---|---|---|---|")
    for r in host_tools:
        state = f"あり(`{r['found']}`)" if r["found"] else "なし"
        tc = "あり" if r["toolchain_found"] else f"**{r['toolchain']} が無い**"
        print(f"| {r['tool']} | {r['language']} | {state} | {tc} | {r['note']} |")

    if "--host-tools" in flags and not check_only:
        print()
        print("### 任意ツールの導入")
        for m in install_host_tools(root, host_tools):
            print("  " + m)

    print()
    print("### 各言語が得られる精度")
    print("| 言語 | Tier | 根拠 |")
    print("|---|---|---|")
    for row in tier_table(root, reqs):
        print(f"| {row[0]} | {row[1]} | {row[2]} |")

    print()
    print("**Tier 3 の結果を「網羅した」と報告してはならない**"
          "(.claude/directions/callgraphs.md §5.8)。")
    if not check_only:
        # 生成先は常に SSOT(callgraphs.md §3.1 — 廃止されたフェーズモデルの staged 出力は retired)
        print("\n→ 次: python3 .claude/scripts/build-callgraphs.py\n"
              "  (venv があれば自動でそちらのインタプリタで走る)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
