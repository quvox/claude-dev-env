#!/usr/bin/env python3
"""構築記録(`docs/build-records/<slug>.md`)の機械検査。**F1 の構築記録ゲート。**

構築記録は「検証を後回しにする者が払う頭金」である(規範: .claude/directions/build-record.md)。
verify 系フローはこの記録を**突き合わせ可能な主張**として読むので、形が崩れた記録は
検証の網に穴を開ける。検査は fail-closed — 「検査したが違反が無い」と「何も検査していない」を
同じ出力にしない。

検査(IDの正はこのファイルの CHECKS だけ。--list で出る):
  BRC1  frontmatter: slug がファイル名と一致 / state が building・awaiting-verify・verified の
        いずれか / started・updated が ISO 日時 / origin が明記され derived か human-report
        (欠落を derived に既定しない — human-report だけに許される問いの経路が黙って消える)/
        **building 以外の state は commit に実在する git commit を持つ**(promote と
        F4 の犯人探しが commit に紐づくため。git が引けない環境では形式だけ見る)
  BRC2  重要な変更のフラグ(`critical:`)が true / false で明記されている。**false なのにクロージャのパスが
        critical-config.json のパターンに掛かるものは違反**(fail-closed — 未記入や誤記入で
        認証・決済・不可逆・個人情報・監査への接触が検証の優先順位と独立レビューの対象から漏れる穴を塞ぐ)。
        true をパターン不一致で咎めることはない(安全側の申告は上書きしない)
  BRC3  `## 影響範囲(closure)` に1行1パスで1件以上ある(空のクロージャは「何を検証すれば
        よいか」を verify 系に渡せない)
  BRC6  `## 影響範囲(closure)` に**パスとして読めない行**がある。先頭が `.` のパスも、
        バッククォートで囲んだ空白入りの名前も読む。**読めない行を黙って捨てない** —
        捨てると、その1本だけが検証の範囲からも BRC2 の照合からも消えるのに、
        他の行が在るぶん BRC3 は通ってしまう(fail-closed)
  BRC8  `commit:` が名指す作業コミットで**変わったファイルが、影響範囲に1本残らず在る**
        (2026-09-23)。影響範囲は人が書いて人が読むので、抜けても書いた本人にも読んだ側にも
        見えない — 抜けたファイルは検証の範囲から黙って消える(実測: 1周で3回。E2E の台本の
        抜けと取り違え)。比べる相手は git なので、ここは機械が持つ。
        **数えないもの**: 構築記録・決定シート・履歴・課題票・索引(`index.md`)・台帳
        (`residual*.md` / `pendings.md` / `reverification.md`)・`.gitkeep` — どれも SSOT でも
        コードでもなく、出口の手順が作り直す帳簿である(索引は `docs/` の下のものだけ)。
        **この作業が書いたのではないファイル**(人間が着手前に置いた要望や資料が同じコミットに
        入ったもの — 最初のコミットでは着手前から在ったものが全部入る)は、影響範囲ではなく
        `## 作業コミットに入れた入力` に理由つきで申告すれば数えない。**申告は書いて残す行為
        なので、書き忘れ(この検査が止めたい抜け)では起きない。** それでも理由は機械には
        確かめられないので、**申告できる場所を機械で絞る**: その作業コミットで**新しく入った**
        ファイル(書き換え・削除・改名は、前から追跡されていたものに作業が触ったのだから申告
        できない)で、かつ **`docs/` の下の、SSOT の4階層と `docs/ux/` の外の、文書か画像**
        (.md / .txt / .pdf / 画像の拡張子)だけである —
        コード・テスト・設定・SSOT は、理由を書いても申告では外せない。理由の無い行・
        理由が差し込み記号のままの行・影響範囲と重なる行も落とす。
        **見るのは `commit:` の1コミット(マージなら第一親との差分)だけである**:
        1つの作業が複数のコミットに分かれると、
        それより前のコミットの抜けは映らない(下限を引き上げる検査であって、完全ではない)。
        `awaiting-verify` の記録には常に掛ける。`verified` の記録は、この検査より前に
        始まったものだけを免除する(BRC7 と同じ切り方 — `state` で切ると「verified にすれば
        落とせる」経路になる)。git が引けない環境と、浅い clone の境界のコミットでは飛ばす
        (BRC1 の commit の実在と同じ倒れ方)
  BRC4  `## 主張` が突き合わせ可能である: 雛形の差し込み記号が残っていない・コマンドと
        最終行の逐語引用(バッククォート)が1つ以上ある・外部挙動の宣言行がある
        (裸の ✓ は散文であって主張ではない — build-record.md §2)
  BRC5  基本要件の点検: `.claude/directions/baseline.md` §2 の全 BR-nn に 該当 / 非該当 の
        判定行がある。該当は落とし先まで(**どこが落とし先かは項目ごとに違う** —
        `baseline.md` §2 の「既定の落とし先」の欄が正である。ここが見るのは、
        書かれた落とし先が実体 — ID・契約・パス — を指しているかだけである)。
        **空欄・「-」・雛形のままは未判定であって非該当ではない**。
        **理由の欄は共通理由を指してよい**(`baseline.md` §1 の3)— 欄が `R1` だけなら、
        同じ節の `- R1: BR-03 / BR-06 — 理由` の行を引き、**その行がその BR を
        名指していること**まで見る(名指しの無い参照は、適用条件を項目ごとに見ていない
        一括の非該当と区別が付かない)

使い方:
    python3 .claude/scripts/check-buildrecord.py <slug | path>
    python3 .claude/scripts/check-buildrecord.py --all
    python3 .claude/scripts/check-buildrecord.py --list
    python3 .claude/scripts/check-buildrecord.py --selftest

終了コード: 0=合格 1=違反あり 2=使い方・前提エラー
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path, PurePosixPath

RECORDS = Path("docs/build-records")
BASELINE = Path(".claude/directions/baseline.md")
CONFIG = Path(".claude/scripts/critical-config.json")
# BRC7 の節を雛形へ足した日 ★ — **これより前に始まった記録は持っていないので免除する。**
# 日付で切るのは、`state` で切ると「verified にすれば落とせる」経路になるからである。
BRC7_SINCE = "2026-09-15"
# BRC8 を足した日。**これより前に始まった `verified` の記録だけを免除する**(`awaiting-verify` は
# 検証がまだなので、古くても掛ける — 抜けを見つけたいのはまさにそこである)。
BRC8_SINCE = "2026-09-23"
# BRC8 が数えない帳簿(SSOT でもコードでもなく、`/build` §5 の出口が作り直すもの)。
# **索引は `docs/` の下の `index.md` だけである** — そこは生成物で手書きが禁じられている
# (原則10)。`docs/` の外の `index.md`(`web/help/index.md` など)は製品のファイルであり、数える。
BRC8_LEDGER = re.compile(
    r"^docs/(?:.+/)?index\.md$|(?:^|/)\.gitkeep$"
    r"|^docs/(?:build-records|sheets|histories|issues)/"
    r"|^docs/(?:residual(?:-\d+)?|pendings|reverification)\.md$")
# 作業コミットに入ったが、この作業が書いたのではないファイルを申告する節(2026-09-23 の2巡目)。
# **節の名前に「影響範囲」を含めない** — `section()` は見出しの部分一致で最初の節を返すので、
# 含めるとクロージャを読む道具(この検査・`check-baseline-verdicts.py`)がこちらを読みうる。
BRC8_INPUT_SECTION = "作業コミットに入れた入力"
# **申告できるのは `docs/` の下だけで、そのうち SSOT の4階層と UX 文書は除く** ★(独立レビュー
# review-232347 の高)— 理由の自由文しか歯止めが無い申告を、コード・テスト・設定まで
# 許すと、書いた製品コードを「入力」と書くだけで BRC8 からも BRC2(影響範囲だけを見る)
# からも外せる。人間が着手前に置く要望や資料は `docs/` に置かれる(`docs/idea.md` など)。
# 着手前から在ったコードが作業コミットに入るのは、**git 管理を始める最初のコミットを
# 作業に兼ねたとき**であり、それは申告ではなく、作業の前に人間が最初のコミットを作って
# 避ける(`/setup` は `git init` だけでコミットしない — 最初のコミットの中身は人間が決める)。
# **場所だけでなく種類でも絞る** ★(同 2巡目の高)— `docs/` の下にもコード・テスト・設定は
# 置けるので(`docs/conf.py` など)、**文書と画像の拡張子だけ**を受け取る。
# **大小文字を無視するのは拡張子だけである** ★(同 3巡目の中)— git は `DOCS/` を `docs/` と
# 別の場所として扱うので、場所まで無視すると `docs/` の外を許してしまう。**禁じる側は大小を
# 無視する**(`docs/UX/` も `docs/01-Requirements/` も禁じる側に倒す — fail-closed)。
BRC8_INPUT_OK = re.compile(r"^docs/.+\.(?i:md|markdown|txt|pdf|png|jpe?g|gif|webp)$")
BRC8_NOT_INPUT = re.compile(r"^docs/(?:00-requests|01-requirements|02-design|03-impl|ux)/", re.I)
LOCAL = Path(".claude/scripts/critical-config.local.json")

CHECKS = {
    "BRC1": "frontmatter が壊れている(slug 不一致 / state 不正 / 日時が ISO でない / "
            "origin 欠落・不正 / building 以外なのに commit が実在しない)",
    "BRC2": "重要な変更のフラグ(critical:)が無い、または false なのにクロージャが critical パターンに掛かる",
    "BRC3": "影響範囲(closure)が空(1行1パスで、触った文書とコードを全部書く)",
    "BRC4": "主張が突き合わせ可能でない(雛形のまま / コマンドと最終行の逐語引用が無い / "
            "外部挙動の宣言が無い)",
    "BRC5": "基本要件(BR-nn)の判定が欠けている・未判定のまま・該当なのに落とし先が無い・"
            "理由が未定義の共通理由を指している・共通理由がその BR を名指していない",
    "BRC6": "影響範囲(closure)にパスとして読めない行がある(空白を含む名前はバッククォートで囲む)",
    "BRC7": "独立した目(@review / @qa)が挙げた指摘のうち直さなかったものの節が無い、または理由の書かれていない行がある",
    "BRC8": "作業コミット(commit:)で変わったファイルが影響範囲(closure)に無い"
            "(構築記録・履歴・課題票・索引・台帳は数えない。この作業が書いたのではない入力は"
            "「作業コミットに入れた入力」の節に理由つきで申告する)、またはその申告が正しくない",
}

STATES = {"building", "awaiting-verify", "verified"}
ORIGINS = {"derived", "human-report"}
PLACEHOLDER = re.compile(r"<[^<>\n]{0,60}>")
BR_ROW = re.compile(r"^\|\s*\**\s*(BR-\d{2})\s*\**\s*\|")
BR_UNDECIDED = {"", "-", "—", "未定", "未判定", "TBD", "なし", "?"}
BR_LANDING = re.compile(r"docs/|[\w./-]+\.\w+|\b(?:FR|NFR|AC|E2E|MODULE|MOD|PLAN|CTR|D0|D1)-")
# 共通理由(baseline.md §1 の3)。定義は `- R1: BR-03 / BR-06 — 理由`、参照は欄が `R1` だけ
BR_SHARED = re.compile(r"^[-*]\s*\**\s*`?(R\d+)`?\**\s*[:：]\s*(.*)$")
BR_SHARED_REF = re.compile(r"^\**\s*`?(R\d+)`?\s*\**$")
BR_IN_TEXT = re.compile(r"BR-\d{2}")
# 共通理由の**本文**。覆う BR の名前と区切りを落として、なお中身が残るかを見る —
# `- R1: BR-01 —` のような、名前だけで理由の無い定義を「書いてある」と数えないため
# (理由の欄を直に空にすれば拒むのに、参照を挟むと通る、という抜け道を塞ぐ)。
# 区切りに **Markdown の装飾も含める** ★ — 含めないと ``- R1: `BR-01` —`` の
# バッククォートや `**` が「理由の本文」として残り、本文が空のまま通る(2026-09-13)。
BR_SHARED_SEP = re.compile(r"[-—–/,、:：。`*_~\s]+")
# **先頭の `.` を許し、バッククォートで囲めば空白を含む名前も終端まで読む。**
# `check-baseline-verdicts.py` の同名の式と**同じ形である** — 同じクロージャを読む道具が
# 別々の書式を受けると、同じ記録が道具によって別のパスの集合になる(2026-09-13。C2-6)。
# 囲まない行は最初の空白までがパスで、その後ろは注釈として読み飛ばす。
# **囲まない名前は、空白までを1つのまとまりとして最後まで読む** ★ — 途中で切れる形にすると、
# `src/a+b/auth.py` が `src/a` になって**残りが黙って消える**(そこが `auth` を含んでいても
# BRC2 の照合に掛からない)。読み切った名前が下の形に収まらなければ、**捨てずに違反にする。**
CLOSURE_PATH = re.compile(r"^[-*]\s+`([^`]+)`|^[-*]\s+(\S+)")
CLOSURE_BARE = re.compile(r"[\w.][\w./+-]*\Z")
CLOSURE_ITEM = re.compile(r"^[-*]\s+\S")


def find_root(start: Path) -> Path:
    cur = start.resolve()
    for cand in (cur, *cur.parents):
        if (cand / "CLAUDE.md").is_file() and (cand / ".claude").is_dir():
            return cand
    return cur


def critical_patterns(root: Path) -> list[str]:
    out: list[str] = []
    # **和集合でマージする**(check-lane 前身と同じ考え方)★ — local 側に空の一覧や短い一覧を
    # 書いても、既定の語は1つも減らない。**local で「絞る」ことはできない** ので、BRC2 の
    # 案内文にそう書いてはならない(inspection-27 C-9)。
    for rel in (CONFIG, LOCAL):
        path = root / rel
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        v = data.get("critical_path_patterns")
        if isinstance(v, list):
            out += [s for s in v if isinstance(s, str) and s]
    return sorted(set(out))


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    return {m.group(1): m.group(2).strip('`"\'')
            for m in re.finditer(r"(?m)^(\w[\w-]*):\s*(.*?)\s*$", parts[1])}


def section(text: str, name: str) -> str | None:
    m = re.search(rf"^##[^\n]*{re.escape(name)}[^\n]*$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    return m.group(1) if m else None


def safe_rel(rel: str) -> bool:
    """クロージャのパスとして受け取ってよい形か(`check-baseline-verdicts.py` と同じ判定)。

    先頭の `.` を許した裏で `../outside.txt` も受理される。クロージャはリポジトリの中の
    ものだけを指すので、**上へ出る形と絶対パスは断る**。"""
    if not rel or rel.startswith(("/", "~")):
        return False
    return ".." not in PurePosixPath(rel).parts


def norm_rel(rel: str) -> str:
    """`./src/x.go` を `src/x.go` にする(`check-baseline-verdicts.py` と同じ正規化)。"""
    parts = [p for p in PurePosixPath(rel).parts if p != "."]
    return "/".join(parts)


def closure_paths(text: str) -> tuple[list[str], list[str]]:
    """(読めたパス, 読めなかった行)。

    **読めない行を黙って捨てない** ★(2026-09-13。C2-6)— 捨てると、その1本だけが
    検証の範囲からも BRC2 の照合からも消えるのに、他の行が1つでも在れば BRC3 は通る。
    空白を含む名前はバッククォートで囲む(``- `src/my app/auth.py` ``)。囲まない行は
    最初の空白までがパスで、その後ろは注釈として読み飛ばす。"""
    body = section(text, "影響範囲") or ""
    out, bad = [], []
    for raw in body.splitlines():
        line = raw.strip()
        m = CLOSURE_PATH.match(line)
        if not m:
            if CLOSURE_ITEM.match(line) and not PLACEHOLDER.search(line):
                bad.append(line[:60])
            continue
        rel = (m.group(1) or m.group(2)).strip()
        # **差し込み記号を見るのは名前の側だけである** ★ — 行の全体を見ると、
        # `- src/a.py — <説明>` が注釈のせいで丸ごと捨てられる(名前は読めている)。
        if PLACEHOLDER.search(rel):
            continue
        if not safe_rel(rel) or (m.group(1) is None and not CLOSURE_BARE.match(rel)):
            bad.append(line[:60])
            continue
        out.append(norm_rel(rel))
    return out, bad


def input_paths(text: str, closure: set[str]) -> tuple[set[str], list[str]]:
    """(申告された入力のパス, 申告として受け取れない行の説明)。

    `## 作業コミットに入れた入力` の1行1パスを、影響範囲と同じ書式で読む。**理由を必須にする**
    (区切りは BRC7 と同じ — 全角のダッシュか、空白で囲んだハイフン)— 何を入れたかだけで
    なぜ書いていないかが無い申告は、読む側が確かめられない。**理由が雛形の差し込み記号の
    ままの行も理由とは数えない**(review-232347 の中)。**読めない行を黙って捨てない**
    (BRC6 と同じ倒れ方)。「なし」の1行と、節が無いことは、どちらも申告0件である。
    **作業コミットで新しく入ったかは、ここでは見ない** — git を引く側(BRC8 の本体)が見る。"""
    body = section(text, BRC8_INPUT_SECTION) or ""
    out: set[str] = set()
    bad: list[str] = []
    for raw in body.splitlines():
        line = raw.strip()
        if not CLOSURE_ITEM.match(line) or line.lstrip("-* ").strip() in ("なし", "無し"):
            continue
        m = CLOSURE_PATH.match(line)
        rel = (m.group(1) or m.group(2)).strip() if m else ""
        if PLACEHOLDER.search(rel):
            continue
        if not safe_rel(rel) or (m.group(1) is None and not CLOSURE_BARE.match(rel)):
            bad.append(f"パスとして読めない「{line[:60]}」")
            continue
        rel = norm_rel(rel)
        reason = line[m.end():]
        if not re.search(r"(?:\s[—–]\s*|\s-\s+)\S", reason) or PLACEHOLDER.search(reason):
            bad.append(f"理由が無いか雛形のまま「{rel}」"
                       "(形式は - <パス> — <この作業が書いていない理由>)")
        elif not BRC8_INPUT_OK.search(rel) or BRC8_NOT_INPUT.search(rel):
            bad.append(f"「{rel}」は入力として申告できない(申告できるのは docs/ の下の、"
                       "SSOT の4階層と docs/ux/ の外の、文書か画像 — .md / .txt / .pdf / 画像 — "
                       "だけ)— 影響範囲に書く")
        elif rel in closure:
            bad.append(f"「{rel}」が影響範囲にも在る — 触ったなら影響範囲だけに書く")
        else:
            out.add(rel)
    return out, bad


def commit_ok(root: Path, value: str) -> tuple[bool, str]:
    """形式(7〜40桁の16進)と、引ける環境では git 上の実在を見る。"""
    if not re.fullmatch(r"[0-9a-f]{7,40}", value or ""):
        return False, f"「{value or '空'}」は commit の形をしていない"
    import subprocess
    try:
        r = subprocess.run(["git", "cat-file", "-e", f"{value}^{{commit}}"],
                           cwd=root, capture_output=True)
    except OSError:
        return True, ""                       # git が無い環境では形式検査まで
    if r.returncode != 0:
        # git はあるがリポジトリ外・浅い clone 等でも失敗しうる — repo かどうかで見分ける
        probe = subprocess.run(["git", "rev-parse", "--git-dir"], cwd=root, capture_output=True)
        if probe.returncode != 0:
            return True, ""
        return False, f"「{value}」は git に実在しない"
    return True, ""


def commit_files(root: Path, value: str, added_only: bool = False) -> list[str] | None:
    """そのコミットが変えたファイル(根からの相対パス)。確かめられなければ None。

    - **マージコミットは第一親との差分を取る** — 親を指定しない `diff-tree` はマージに
      何も返さず、全変更を見逃す(2026-09-23 の独立レビュー)。
    - **浅い clone の境界のコミットは None**(飛ばす)— 親が切られているので、空の木との
      差分として全ファイルが返り、実際の変更と区別が付かない。
    - **改名は新しい名前だけを出す**(`-M`)— 旧名はもう木に無い。ただし改名と判定するのは
      git の類似度であり、**大きく書き換えた改名は旧名の削除+新名の追加として出る**。
      そのときは旧名も影響範囲に書く(消したのと同じ扱いである)。
    - 改名でない削除は出す — 消したテストやコードは、後の検証が知るべき変更である。
    - `added_only` は**そのコミットで新しく入ったファイルだけ**を出す(改名・書き換え・削除は
      出ない)— 入力の申告を受け取ってよい相手である(BRC8)。"""
    import subprocess

    def git(*a: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", *a], cwd=root, capture_output=True)
    try:
        r = git("rev-list", "--parents", "-n", "1", value)
    except OSError:
        return None
    if r.returncode != 0:
        return None
    ids = r.stdout.decode().split()
    if len(ids) >= 2:
        span = [ids[1], ids[0]]                      # 第一親との差分(マージも同じ)
    else:
        shallow = git("rev-parse", "--is-shallow-repository").stdout.decode().strip()
        if shallow == "true":
            return None                              # 最初のコミットか境界か見分けない
        span = ["--root", ids[0]]
    r = git("diff-tree", "--no-commit-id", "--name-only", "-r", "-M", "--relative", "-z",
            *(["--diff-filter=A"] if added_only else []), *span)
    if r.returncode != 0:
        return None
    return [p for p in r.stdout.decode("utf-8", "replace").split("\0") if p]


def iso_ok(value: str) -> bool:
    try:
        datetime.fromisoformat(value)
        return True
    except ValueError:
        return False


def baseline_ids(root: Path) -> list[str] | None:
    path = root / BASELINE
    if not path.is_file():
        return None
    ids: list[str] = []
    for line in path.read_text(errors="replace").splitlines():
        m = BR_ROW.match(line.strip())
        if m and m.group(1) not in ids:
            ids.append(m.group(1))
    return ids or None


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def check_record(root: Path, path: Path) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    text = re.sub(r"<!--.*?-->", "", path.read_text(encoding="utf-8", errors="replace"),
                  flags=re.S)
    fm = frontmatter(text)

    # BRC1
    if fm.get("slug", "") != path.stem:
        out.append(("BRC1", f"slug 「{fm.get('slug', '')}」がファイル名 {path.stem} と違う"))
    if fm.get("state", "") not in STATES:
        out.append(("BRC1", f"state 「{fm.get('state', '')}」は "
                            "building / awaiting-verify / verified のどれでもない"))
    for k in ("started", "updated"):
        if not iso_ok(fm.get(k, "")):
            out.append(("BRC1", f"{k} が ISO 日時でない: 「{fm.get(k, '')}」"))
    if fm.get("origin", "") not in ORIGINS:
        out.append(("BRC1", f"origin 「{fm.get('origin', '')}」が無いか、derived / human-report の"
                            "どちらでもない(欠落を derived に既定しない)"))
    if fm.get("state") in ("awaiting-verify", "verified"):
        ok, why = commit_ok(root, fm.get("commit", ""))
        if not ok:
            out.append(("BRC1", f"state: {fm.get('state')} なのに commit が不正: {why}"
                                "(promote と F4 の犯人探しは commit に紐づく)"))

    # BRC7: 直さなかった指摘に理由が在るか ★(2026-09-15。inspection-28 A-6)
    #
    # 独立した目(`@review` / `@qa`)は**採否を決めない**決まりなので、決めるのは指摘を
    # 受けた当人である。当人が決めてよいこと自体は変えないが、**決めた理由が残っていなければ
    # 後から誰も検分できない** — 進行役は docs/ も製品コードも開かないので、
    # 中身から確かめられる第三者がこの規範には居ない。
    #
    # **見るのは形だけである**: 節が在ること、そして各行が「— 理由」を持つこと。
    # **理由が妥当かどうかは見ない**(それは人が読む側に残る)。
    # **「なし」の1行は正当である** — 直さなかった指摘が無いという申告であり、
    # 空欄(書き忘れ)と区別が付く。
    body = section(text, "直さなかった指摘")
    if body is None:
        # **この節より前に始まった記録だけを免除する** ★(2026-09-15 の2巡目に絞った)—
        # 節は 2026-09-15 に雛形へ足したので、**それより前に始まった記録は持っていない。**
        # 持っていないことを違反にすると、過去の記録を全部書き換えるまで出口が閉じる。
        # **`state: verified` だけで免除すると、今日から作る記録も
        # 「verified にすれば節を落とせる」経路になる** ので、日付で切る。
        # 読めない日付は免除しない(fail-closed)。
        started = str(fm.get("started", ""))
        if not (started and started[:10] < BRC7_SINCE):
            out.append(("BRC7", "`## 直さなかった指摘(独立レビュー・探索的QA)` の節が無い"
                                "(雛形に在る。1件も無いなら「なし」と書く — "
                                "空欄は「無かった」と「書き忘れ」を区別しない)"))
    else:
        rows = [l.strip() for l in body.splitlines()
                if l.strip().startswith(("-", "*")) and not l.strip().startswith("<!--")]
        rows = [r.lstrip("-* ").strip() for r in rows]
        rows = [r for r in rows if r]
        if not rows:
            out.append(("BRC7", "`## 直さなかった指摘` が空である(1件も無いなら「なし」と書く)"))
        for r in rows:
            if r in ("なし", "無し"):
                continue
            # **理由の区切りは、全角のダッシュか、空白で囲んだハイフンだけである** ★
            # (2026-09-15 の2巡目)— 単に `-` を探すと、`client-side` のような語の中の
            # ハイフンを区切りと読んで、理由の無い行が通る。
            if not re.search(r"(?:\s[—–]\s*|\s-\s+)\S", r):
                out.append(("BRC7", f"直さなかった指摘に理由が無い: 「{r[:60]}」"
                                    " — 形式は <出どころ> <重大度> <要旨> — <直さなかった理由>"))

    # BRC3 / BRC6(BRC2 がクロージャを読むので先に)
    paths, unreadable = closure_paths(text)
    if not paths:
        out.append(("BRC3", "`## 影響範囲(closure)` に実パスが1件も無い"))
    if unreadable:
        out.append(("BRC6", "`## 影響範囲(closure)` にパスとして読めない行がある: "
                            f"{' / '.join(unreadable[:3])}"
                            " — 空白を含む名前はバッククォートで囲み(- `src/my app/x.py`)、"
                            "注釈はパスの後ろへ置く。リポジトリの外を指す形は書けない"))

    # BRC8: 作業コミットが変えたファイルが影響範囲に在るか ★(2026-09-23)
    state = fm.get("state", "")
    started = str(fm.get("started", ""))
    brc8_due = state == "awaiting-verify" or (
        state == "verified" and not (started and started[:10] < BRC8_SINCE))
    commit = fm.get("commit", "")
    listed = set(paths)
    inputs, bad_inputs = input_paths(text, listed) if brc8_due else (set(), [])
    for why in bad_inputs:
        out.append(("BRC8", f"`## {BRC8_INPUT_SECTION}` の申告が正しくない: {why}"))
    if brc8_due and commit_ok(root, commit) == (True, ""):
        changed = commit_files(root, commit)
        if changed is not None:
            missing = sorted(p for p in changed
                             if p not in listed and p not in inputs
                             and not BRC8_LEDGER.search(p))
            if missing:
                out.append(("BRC8", f"作業コミット {commit[:7]} で変わったのに影響範囲に無い: "
                                    f"{' / '.join(missing[:5])}"
                                    f"{f' ほか {len(missing) - 5} 本' if len(missing) > 5 else ''}"
                                    " — 影響範囲へ足して記録をコミットし直す(amend しない)。"
                                    "この作業が書いたのではない入力(人間が着手前に docs/ へ置いた要望など)なら、"
                                    f"`## {BRC8_INPUT_SECTION}` に理由つきで書く。"
                                    "走らせただけのテストは変わったファイルに出ないので、ここには来ない"))
            added = commit_files(root, commit, added_only=True)
            stray = sorted(inputs - set(added if added is not None else changed))
            if stray:
                out.append(("BRC8", f"`## {BRC8_INPUT_SECTION}` に、作業コミット {commit[:7]} で"
                                    f"新しく入ったのではないファイルが在る: {' / '.join(stray[:5])}"
                                    " — 申告できるのは、そのコミットで新しく入ったものだけである"
                                    "(書き換え・削除・改名は作業が触ったのだから影響範囲に書く。"
                                    "先回りの申告を検査の抜け道にしない)"))

    # BRC2
    critical = fm.get("critical", "")
    if critical not in ("true", "false"):
        out.append(("BRC2", f"critical が true / false で書かれていない: 「{critical}」"))
    elif critical == "false":
        pats = critical_patterns(root)
        hits = [p for p in paths for pat in pats if pat.lower() in p.lower()]
        if hits:
            out.append(("BRC2", f"critical: false だがクロージャが critical パターンに掛かる: "
                                f"{', '.join(sorted(set(hits))[:3])} — **true に直す。**"
                                "local 設定は既定のパターンに足すだけで、絞ることはできない"
                                "(和集合でマージする)。非該当だと考えるなら、その根拠を主張に"
                                "書いたうえで人間の裁定を待つ — この検査を設定で外す道は無い"))

    # BRC4
    claims = section(text, "主張")
    if claims is None or not PLACEHOLDER.sub("", claims).strip().strip("-* \n"):
        out.append(("BRC4", "`## 主張` が無いか空(触ったテスト green / 外部挙動 / "
                            "critical 接触を、後で突き合わせ可能な形で宣言する)"))
    else:
        if PLACEHOLDER.search(claims):
            out.append(("BRC4", "主張に雛形の差し込み記号(<…>)が残っている"))
        if "`" not in claims:
            out.append(("BRC4", "主張にコマンドと最終行の逐語引用(バッククォート)が1つも無い"
                                "(裸の ✓ は散文 — build-record.md §2)"))
        # **値まで読む** ★(2026-09-04)— 語の存在だけを見ていた間、この行は誰にも
        # 読まれていなかった。成果物の版の桁はここから決まる(`flows.md` §9)。
        # **判定は `stamps.py` の1箇所が持つ**(原則10。同じ規則を二度実装しない) —
        # 入口(ここ)と出口(リリース)で規則がずれると、出口を通った記録がリリースを止める。
        try:
            import stamps
            kind = stamps.behaviour_change(text)            # **入力も同じにする**(節だけを読む)
        except Exception as exc:
            # **黙って旧い検査へ戻らない** ★ — 戻れば「語が在るか」だけになり、
            # 3値でない値が出口を抜けてリリースで止まる(独立検査 2026-09-04)。
            out.append(("BRC4", f"外部挙動の変化の判定器(stamps.py)を読めない: {exc}"))
            kind = None
        if kind == "不明":
            out.append(("BRC4", "外部挙動の変化が3つの値のどれでもない"
                                "(なし / あり(後方互換。…)/ あり(互換を壊す。…))"))

    # BRC5
    ids = baseline_ids(root)
    if ids is None:
        out.append(("BRC5", "baseline.md §2 が読めない(基本要件の一覧が無い)"))
    else:
        body = section(text, "基本要件の点検")
        rows: dict[str, list[str]] = {}
        shared: dict[str, tuple[set[str], str]] = {}
        for line in (body or "").splitlines():
            g = BR_ROW.match(line.strip())
            if g and g.group(1) not in rows:
                rows[g.group(1)] = _cells(line)
                continue
            s = BR_SHARED.match(line.strip())
            if s:
                rest = BR_IN_TEXT.sub("", s.group(2))
                rest = BR_SHARED_SEP.sub("", PLACEHOLDER.sub("", rest)).strip()
                shared[s.group(1)] = (set(BR_IN_TEXT.findall(s.group(2))), rest)
        for br in ids:
            cells = rows.get(br)
            if cells is None:
                out.append(("BRC5", f"{br} の判定行が無い"))
                continue
            verdict = (cells[1] if len(cells) > 1 else "").strip("`* 　")
            why = cells[2] if len(cells) > 2 else ""
            land = cells[3] if len(cells) > 3 else ""
            if PLACEHOLDER.search(verdict) or not (verdict.startswith("該当")
                                                   or verdict.startswith("非該当")):
                out.append(("BRC5", f"{br} の判定が 該当 / 非該当 のどちらでもない: "
                                    f"「{verdict}」(空欄・雛形のままは未判定)"))
                continue
            if why in BR_UNDECIDED or PLACEHOLDER.search(why):
                out.append(("BRC5", f"{br} の理由が空(理由の無い非該当は未判定と"
                                    "区別できない)"))
            ref = BR_SHARED_REF.match(why)
            if ref:
                entry = shared.get(ref.group(1))
                covered, body = entry if entry else (None, "")
                if covered is None:
                    out.append(("BRC5", f"{br} の理由が未定義の共通理由を指している: "
                                        f"「{ref.group(1)}」(同じ節に "
                                        f"`- {ref.group(1)}: BR-nn / BR-mm — 理由` の行を置く)"))
                elif not body:
                    out.append(("BRC5", f"{br} が指している共通理由 {ref.group(1)} に理由の本文が"
                                        "無い(覆う BR を並べただけでは、理由の欄を空にしたのと"
                                        "同じである)"))
                elif br not in covered:
                    out.append(("BRC5", f"{br} が共通理由 {ref.group(1)} を指しているが、"
                                        f"{ref.group(1)} は {br} を名指していない"
                                        "(共通理由は覆う BR を全部名指しする — "
                                        "項目ごとに適用条件を見たことの証拠である)"))
            if verdict.startswith("該当") and (land in BR_UNDECIDED
                                               or PLACEHOLDER.search(land)
                                               or not BR_LANDING.search(land)):
                out.append(("BRC5", f"{br} は該当なのに落とし先が実体を指していない: "
                                    f"「{land}」(ID・契約・パスのいずれかを指すこと。"
                                    f"どこへ降ろすかは baseline.md §2 の欄)"))
    return out


def run(root: Path, targets: list[Path]) -> int:
    total = 0
    for path in targets:
        found = check_record(root, path)
        total += len(found)
        if found:
            print(f"NG  {path.relative_to(root)}: {len(found)} 件")
            for cid, msg in found:
                print(f"  {cid}  {msg}")
        else:
            print(f"OK  {path.relative_to(root)}")
    return 1 if total else 0


def main(argv: list[str]) -> int:
    args = argv[1:]
    if "--selftest" in args:
        return selftest()
    if "--list" in args:
        for cid, desc in CHECKS.items():
            print(f"{cid}: {desc}")
        return 0
    if not args or any(a in ("-h", "--help") for a in args):
        print(__doc__)
        return 0 if args else 2
    root = find_root(Path.cwd())
    if args[0] == "--all":
        base = root / RECORDS
        targets = sorted(p for p in base.glob("*.md")
                         if p.name != "index.md") if base.is_dir() else []
        if not targets:
            print("構築記録なし(docs/build-records/ が空)")
            return 0
        return run(root, targets)
    cand = Path(args[0])
    if not cand.is_file():
        cand = root / RECORDS / f"{args[0]}.md"
    if not cand.is_file():
        print(f"エラー: 構築記録が見つからない: {args[0]}", file=sys.stderr)
        return 2
    return run(root, [cand.resolve()])


def selftest() -> int:
    import contextlib, io, os, tempfile
    previous = Path.cwd()
    quiet = contextlib.redirect_stdout(io.StringIO())
    with tempfile.TemporaryDirectory() as td, quiet:
        root = Path(td)
        (root / ".claude/scripts").mkdir(parents=True)
        (root / ".claude/directions").mkdir(parents=True)
        (root / "CLAUDE.md").write_text("x", encoding="utf-8")
        (root / BASELINE).write_text(
            "## 2. 一覧\n| ID | 名前 |\n|---|---|\n| BR-01 | a |\n| BR-02 | b |\n",
            encoding="utf-8")
        (root / CONFIG).write_text(json.dumps({"critical_path_patterns": ["auth"]}),
                                   encoding="utf-8")
        rec = root / RECORDS; rec.mkdir(parents=True)
        os.chdir(root)
        good = ("---\nslug: add-x\nstate: building\ncritical: false\norigin: derived\n"
                "started: 2026-08-19T09:00:00+09:00\nupdated: 2026-08-19T09:00:00+09:00\n---\n"
                "## 影響範囲(closure)\n- docs/01-requirements/functional.md\n- src/x.py\n"
                "## 主張\n- 触ったモジュールのテスト: green(`pytest tests/x` → `3 passed`)\n"
                "- 外部挙動の変化: なし\n"
                "## 基本要件の点検\n| ID | 判定 | 理由 | 落とし先 |\n|---|---|---|---|\n"
                "| BR-01 | 非該当 | 認証に触れない | - |\n"
                "| BR-02 | 該当 | 入力を受ける | FR-x-01-1 |\n"
                "## 直さなかった指摘(独立レビュー・探索的QA)\n- なし\n")
        # 宣言が2行在るものは拒む(先頭だけを採らない)
        (rec / "add-x.md").write_text(
            good.replace("- 外部挙動の変化: なし",
                         "- 外部挙動の変化: なし\n- 外部挙動の変化: あり(互換を壊す。x)"),
            encoding="utf-8")
        assert main(["x", "add-x"]) == 1, "宣言が2行在るのに先頭だけを採った"
        (rec / "add-x.md").write_text(good, encoding="utf-8")
        assert main(["x", "add-x"]) == 0, "正しい記録が落ちた"
        # --- BRC7(2026-09-15。inspection-28 A-6)
        (rec / "add-x.md").write_text(
            good.replace("- なし", "- @review 中 テストの名前が実装を写している"),
            encoding="utf-8")
        assert main(["x", "add-x"]) == 1, "理由の無い行が通った(BRC7)"
        # 語の中のハイフンを区切りと読まない(2026-09-15 の2巡目)
        (rec / "add-x.md").write_text(
            good.replace("- なし", "- @review 中 client-side の表記がそろっていない"),
            encoding="utf-8")
        assert main(["x", "add-x"]) == 1, "語の中のハイフンを理由の区切りと読んだ(BRC7)"
        # 既に閉じた記録(state: verified)は節が無くても止めない
        old_rec = (good.replace("started: 2026-08-19", "started: 2026-08-19")
                       .replace("## 直さなかった指摘(独立レビュー・探索的QA)\n- なし\n", ""))
        (rec / "add-x.md").write_text(old_rec, encoding="utf-8")
        assert not any(c == "BRC7" for c, _ in check_record(root, rec / "add-x.md")), \
            "この節より前に始まった記録を止めた(BRC7)"
        new_rec = old_rec.replace("started: 2026-08-19", "started: 2026-10-01")
        (rec / "add-x.md").write_text(new_rec, encoding="utf-8")
        assert any(c == "BRC7" for c, _ in check_record(root, rec / "add-x.md")), \
            "節を足した後に始まった記録が、節なしで通った(BRC7)"
        vrf = new_rec.replace("state: building", "state: verified\ncommit: " + "a" * 40)
        (rec / "add-x.md").write_text(vrf, encoding="utf-8")
        assert any(c == "BRC7" for c, _ in check_record(root, rec / "add-x.md")), \
            "verified にすれば節を落とせてしまう(BRC7)"
        (rec / "add-x.md").write_text(
            good.replace("- なし",
                         "- @review 中 テストの名前が実装を写している — 次の周で書き直す"),
            encoding="utf-8")
        assert main(["x", "add-x"]) == 0, "理由の在る行が落ちた(BRC7)"
        (rec / "add-x.md").write_text(good, encoding="utf-8")
        # 外部挙動の変化は3値である(2026-09-04)。**値まで読む** — 版の桁がここから決まる
        for ok in ("なし", "あり(後方互換。画面を1つ足した)", "あり(互換を壊す。引数を必須にした)"):
            (rec / "add-x.md").write_text(
                good.replace("- 外部挙動の変化: なし", f"- 外部挙動の変化: {ok}"), encoding="utf-8")
            assert main(["x", "add-x"]) == 0, f"正しい値が落ちた: {ok}"
        for ng in ("あり", "あり(画面を1つ足した)", "たぶん無い",
                   "あり(後方互換XYZ)", "あり(互換を壊す。)", "あり(後方互換。説明なし"):
            (rec / "add-x.md").write_text(
                good.replace("- 外部挙動の変化: なし", f"- 外部挙動の変化: {ng}"), encoding="utf-8")
            assert main(["x", "add-x"]) == 1, f"3値のどれでもない値を通した: {ng}"
        (rec / "add-x.md").write_text(good, encoding="utf-8")
        # クロージャの読み取り(C2-6): 先頭の `.` とバッククォート囲みは読める
        # (auth を含む名前はここでは使わない — BRC2 が critical: false を咎めて別の理由で落ちる)
        for ok_path in ("- .github/workflows/ci.yml", "- `src/my app/main.py`",
                        "- src/x.py — 追記"):
            (rec / "add-x.md").write_text(
                good.replace("- src/x.py", ok_path), encoding="utf-8")
            assert main(["x", "add-x"]) == 0, f"正しいクロージャの行が落ちた: {ok_path}"
        # 読めない行は黙って捨てず BRC6 で落ちる(他に読める行が在っても)
        for ng_path in ("- ../outside.txt", "- /etc/passwd"):
            (rec / "add-x.md").write_text(
                good.replace("- src/x.py", "- src/x.py\n" + ng_path), encoding="utf-8")
            assert main(["x", "add-x"]) == 1, f"読めない行を黙って捨てた: {ng_path}"
        (rec / "add-x.md").write_text(good, encoding="utf-8")
        # critical: false + auth パスは落ちる(fail-closed)
        (rec / "add-x.md").write_text(good.replace("src/x.py", "src/auth/login.py"),
                                      encoding="utf-8")
        assert main(["x", "add-x"]) == 1, "critical パターンを見逃した"
        # critical: true は咎めない
        (rec / "add-x.md").write_text(
            good.replace("critical: false", "critical: true")
                .replace("src/x.py", "src/auth/login.py"), encoding="utf-8")
        assert main(["x", "add-x"]) == 0, "true 申告が咎められた"
        # BR の欠落・未判定は落ちる
        (rec / "add-x.md").write_text(good.replace("| BR-02 | 該当 | 入力を受ける | FR-x-01-1 |\n",
                                                   ""), encoding="utf-8")
        assert main(["x", "add-x"]) == 1, "BR 欠落を見逃した"
        (rec / "add-x.md").write_text(good.replace("非該当 | 認証に触れない", "<該当/非該当> | <>"),
                                      encoding="utf-8")
        assert main(["x", "add-x"]) == 1, "雛形のままを見逃した"
        # 共通理由(baseline.md §1 の3)— 定義が在り、その BR を名指していれば通る
        (rec / "add-x.md").write_text(
            good.replace("## 基本要件の点検\n",
                         "## 基本要件の点検\n\n- R1: BR-01 — 認証に触れる経路が無い\n\n")
                .replace("| BR-01 | 非該当 | 認証に触れない |", "| BR-01 | 非該当 | R1 |"),
            encoding="utf-8")
        assert main(["x", "add-x"]) == 0, "定義済みの共通理由の参照が落ちた"
        # 定義の無い参照は落ちる
        (rec / "add-x.md").write_text(
            good.replace("| BR-01 | 非該当 | 認証に触れない |", "| BR-01 | 非該当 | R9 |"),
            encoding="utf-8")
        assert main(["x", "add-x"]) == 1, "未定義の共通理由の参照を見逃した"
        # 覆う BR を名指していない共通理由は落ちる(一括非該当の禁止)
        (rec / "add-x.md").write_text(
            good.replace("## 基本要件の点検\n",
                         "## 基本要件の点検\n\n- R1: BR-02 — 入力を受けない\n\n")
                .replace("| BR-01 | 非該当 | 認証に触れない |", "| BR-01 | 非該当 | R1 |"),
            encoding="utf-8")
        assert main(["x", "add-x"]) == 1, "覆う BR を名指していない共通理由を通した"
        # 覆う BR を並べただけで理由の本文が無い定義は落ちる(欄を空にしたのと同じ)
        (rec / "add-x.md").write_text(
            good.replace("## 基本要件の点検\n",
                         "## 基本要件の点検\n\n- R1: BR-01 —\n\n")
                .replace("| BR-01 | 非該当 | 認証に触れない |", "| BR-01 | 非該当 | R1 |"),
            encoding="utf-8")
        assert main(["x", "add-x"]) == 1, "理由の本文が無い共通理由を通した"
        # 装飾を本文と数えない(`- R1: `BR-01` —` / `- R1: **BR-01** —`)
        for decorated in ("- R1: `BR-01` —", "- R1: **BR-01** —"):
            (rec / "add-x.md").write_text(
                good.replace("## 基本要件の点検\n",
                             f"## 基本要件の点検\n\n{decorated}\n\n")
                    .replace("| BR-01 | 非該当 | 認証に触れない |", "| BR-01 | 非該当 | R1 |"),
                encoding="utf-8")
            assert main(["x", "add-x"]) == 1, f"装飾を理由の本文と数えた: {decorated}"
        (rec / "add-x.md").write_text(good, encoding="utf-8")
        # クロージャ: 囲まない名前は空白まで読み切る。注釈の差し込み記号で名前を捨てない
        got, bad = closure_paths("## 影響範囲(closure)\n- src/a+b/auth.py\n"
                                 "- src/a.py — <説明>\n- `src/my app/x.py`\n"
                                 "- ** 変な行\n- ../outside.txt\n")
        assert got == ["src/a+b/auth.py", "src/a.py", "src/my app/x.py"], got
        assert len(bad) == 2, bad
        # origin 欠落は落ちる(既定しない)
        (rec / "add-x.md").write_text(good.replace("origin: derived\n", ""), encoding="utf-8")
        assert main(["x", "add-x"]) == 1, "origin 欠落を見逃した"
        # awaiting-verify なのに commit が無いのは落ちる
        (rec / "add-x.md").write_text(good.replace("state: building", "state: awaiting-verify"),
                                      encoding="utf-8")
        assert main(["x", "add-x"]) == 1, "commit 無しの awaiting-verify を見逃した"
        # 主張に逐語引用が無いのは落ちる
        (rec / "add-x.md").write_text(
            good.replace("- 触ったモジュールのテスト: green(`pytest tests/x` → `3 passed`)",
                         "- 触ったモジュールのテスト green"), encoding="utf-8")
        assert main(["x", "add-x"]) == 1, "逐語引用の無い主張を見逃した"
        # state 不正・クロージャ空も落ちる
        (rec / "add-x.md").write_text(good.replace("state: building", "state: done"),
                                      encoding="utf-8")
        assert main(["x", "add-x"]) == 1, "state 不正を見逃した"
        (rec / "add-x.md").write_text(good.replace("- docs/01-requirements/functional.md\n", "")
                                      .replace("- src/x.py\n", ""), encoding="utf-8")
        assert main(["x", "add-x"]) == 1, "空クロージャを見逃した"
        # --- BRC8(2026-09-23): 作業コミットが変えたファイルは影響範囲に在る
        import shutil, subprocess
        if shutil.which("git"):
            def git(*a: str) -> str:
                return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t",
                                       "-c", "commit.gpgsign=false", *a], cwd=root,
                                      capture_output=True, text=True, check=True).stdout.strip()
            def brc8(body: str) -> list[str]:
                (rec / "add-x.md").write_text(body, encoding="utf-8")
                return [m for c, m in check_record(root, rec / "add-x.md") if c == "BRC8"]
            (rec / "add-x.md").write_text(good, encoding="utf-8")
            git("init", "-q"); git("add", "-A"); git("commit", "-qm", "base")
            for rel in ("src/x.py", "docs/01-requirements/functional.md", "tests/e2e/x.spec.ts",
                        "docs/histories/2026-09-23-add-x.md", "docs/03-impl/index.md"):
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text("x\n", encoding="utf-8")
                git("add", rel)
            git("commit", "-qm", "work")
            sha = git("rev-parse", "HEAD")
            closed = good.replace("state: building", f"state: awaiting-verify\ncommit: {sha}")
            hit = brc8(closed)
            assert hit and "tests/e2e/x.spec.ts" in hit[0], f"台本の抜けを見逃した(BRC8): {hit}"
            assert "histories" not in hit[0] and "index.md" not in hit[0], \
                f"帳簿(履歴・索引)まで求めた(BRC8): {hit}"
            # この作業が書いたのではない入力は、理由つきの申告で数えない(2026-09-23 の2巡目)
            sec = f"\n## {BRC8_INPUT_SECTION}\n\n"
            (root / "docs/idea.md").write_text("x\n", encoding="utf-8")
            git("add", "docs/idea.md"); git("commit", "--amend", "-qm", "work")
            sha = git("rev-parse", "HEAD")
            closed = good.replace("state: building", f"state: awaiting-verify\ncommit: {sha}")
            full = closed.replace("- src/x.py\n", "- src/x.py\n- tests/e2e/x.spec.ts — 台本\n")
            hit = brc8(full)
            assert hit and "docs/idea.md" in hit[0], f"申告の無い入力を見逃した(BRC8): {hit}"
            assert not brc8(full + sec + "- docs/idea.md — 人間が着手前に置いた要望\n"), \
                "理由つきで申告した入力を止めた(BRC8)"
            assert brc8(full + sec + "- docs/idea.md\n"), "理由の無い申告を通した(BRC8)"
            dodge = closed + sec + ("- docs/idea.md — 要望\n"
                                    "- tests/e2e/x.spec.ts — 読んだだけ\n")
            assert any("tests/e2e/x.spec.ts" in m for m in brc8(dodge)), \
                "テストを入力として申告させた(BRC8。抜けの隠し場所になる)"
            # コードは理由を書いても申告で外せない(review-232347 の高)
            code = full.replace("- src/x.py\n", "") + sec + ("- docs/idea.md — 要望\n"
                                                              "- src/x.py — 前から在った\n")
            assert any("src/x.py" in m for m in brc8(code)), \
                "コードを入力として申告させた(BRC8。BRC2 の照合からも消える)"
            assert brc8(full + sec + "- docs/idea.md — <この作業が書いていない理由>\n"), \
                "理由が差し込み記号のままの申告を通した(BRC8)"
            assert brc8(full + sec + "- docs/idea.md — 要望\n- docs/other.md — 先回り\n"), \
                "作業コミットに入っていない申告を通した(BRC8)"
            # 書き換えたファイルは、docs/ の下でも申告できない(新しく入ったものだけ)
            (root / "docs/idea.md").write_text("y\n", encoding="utf-8")
            git("add", "docs/idea.md"); git("commit", "-qm", "edit idea")
            edited = full.replace(sha, git("rev-parse", "HEAD")) + sec + "- docs/idea.md — 要望\n"
            assert any("新しく入った" in m for m in brc8(edited)), \
                "書き換えたファイルを入力として申告させた(BRC8)"
            git("reset", "-q", "--hard", sha)
            assert brc8(full + sec + "- docs/idea.md — 要望\n- src/x.py — 重ねた\n"), \
                "影響範囲と重なる申告を通した(BRC8)"
            (rec / "add-x.md").write_text(full + sec + "- docs/idea.md — 人間が着手前に置いた要望\n",
                                          encoding="utf-8")
            assert main(["x", "add-x"]) == 0, "抜けの無い記録が落ちた(BRC8)"
            vrf_old = closed.replace("state: awaiting-verify", "state: verified")
            assert not brc8(vrf_old), "この検査より前に始まった verified の記録を止めた(BRC8)"
            vrf_new = vrf_old.replace("started: 2026-08-19", "started: 2026-10-01")
            assert brc8(vrf_new), "verified にすれば抜けを落とせてしまう(BRC8)"
            # 改名は新しい名前だけを求める
            git("mv", "src/x.py", "src/y.py"); git("commit", "-qm", "rename")
            sha2 = git("rev-parse", "HEAD")
            renamed = (full.replace(sha, sha2).replace("- src/x.py\n", "- src/y.py\n")
                           .replace("- tests/e2e/x.spec.ts — 台本\n", ""))
            assert not brc8(renamed), "改名の旧名まで求めた(BRC8)"
            assert brc8(renamed.replace("- src/y.py\n", "")), "改名先の抜けを見逃した(BRC8)"
            # docs/ の外の index.md は製品のファイルであり、数える
            (root / "web/help").mkdir(parents=True)
            (root / "web/help/index.md").write_text("x\n", encoding="utf-8")
            git("add", "web/help/index.md"); git("commit", "-qm", "help")
            hit = brc8(renamed.replace(sha2, git("rev-parse", "HEAD")))
            assert hit and "web/help/index.md" in hit[0], "docs/ の外の index.md を帳簿と見た(BRC8)"
            # マージコミットは第一親との差分を見る(素通りさせない)
            main_branch = git("rev-parse", "--abbrev-ref", "HEAD")
            git("checkout", "-qb", "side")
            (root / "src/z.py").write_text("z\n", encoding="utf-8")
            git("add", "src/z.py"); git("commit", "-qm", "side")
            git("checkout", "-q", main_branch); git("merge", "-q", "--no-ff", "-m", "m", "side")
            merged = renamed.replace(sha2, git("rev-parse", "HEAD"))
            hit = brc8(merged)
            assert hit and "src/z.py" in hit[0], f"マージコミットの変更を見逃した(BRC8): {hit}"
            # 浅い clone の境界は飛ばす(空の木との差分で全ファイルを求めない)
            with tempfile.TemporaryDirectory() as td2:
                subprocess.run(["git", "clone", "-q", "--depth", "1", f"file://{root}", td2],
                               check=True, capture_output=True)
                assert commit_files(Path(td2), git("rev-parse", "HEAD")) is None, \
                    "浅い clone の境界で全ファイルを返した(BRC8)"
            # 作業コミットがリポジトリの最初のコミット(親なし)のとき — 着手前から在った入力が
            # 全部入る。この周の実例(docs/idea.md)の回帰試験(review-232347 の低)
            git("checkout", "-q", "--orphan", "first"); git("read-tree", "--empty")
            (root / "src/r.py").write_text("r\n", encoding="utf-8")
            (root / "docs/conf.py").write_text("c\n", encoding="utf-8")
            git("add", "src/r.py", "docs/idea.md", "docs/conf.py"); git("commit", "-qm", "first")
            sha3 = git("rev-parse", "HEAD")
            assert sorted(commit_files(root, sha3) or []) == \
                ["docs/conf.py", "docs/idea.md", "src/r.py"], "最初のコミットの変更を取り損ねた(BRC8)"
            first = good.replace("state: building", f"state: awaiting-verify\ncommit: {sha3}") \
                        .replace("- src/x.py\n", "- src/r.py\n- docs/conf.py\n")
            # docs/ の下でも、コードや設定は申告で外せない(review-232347 の2巡目の高)
            conf = first.replace("- docs/conf.py\n", "") + sec + ("- docs/idea.md — 要望\n"
                                                                  "- docs/conf.py — 前から在った\n")
            assert any("docs/conf.py" in m for m in brc8(conf)), \
                "docs/ の下の設定を入力として申告させた(BRC8)"
            # 場所の大小は区別し(git が別の場所と見る)、拡張子の大小だけを無視する(同 3巡目の中)
            assert BRC8_INPUT_OK.search("docs/Idea.MD") and not BRC8_INPUT_OK.search("DOCS/idea.md"), \
                "申告できる場所の大小の扱いが違う(BRC8)"
            assert BRC8_NOT_INPUT.search("docs/UX/a.md") and BRC8_NOT_INPUT.search("docs/01-Requirements/a.md"), \
                "大小の違う SSOT の層を申告させた(BRC8)"
            hit = brc8(first)
            assert hit and "docs/idea.md" in hit[0] and "src/r.py" not in hit[0], \
                f"最初のコミットで申告の無い入力を見逃した(BRC8): {hit}"
            assert not brc8(first + sec + "- docs/idea.md — 人間が着手前に置いた要望\n"), \
                "最初のコミットで、理由つきで申告した入力を止めた(BRC8)"
        os.chdir(previous)
    print("OK check-buildrecord: 合格/critical fail-closed/true尊重/BR欠落/雛形/共通理由/origin/commit/主張/state/クロージャ/外部挙動の3値/作業コミットとの突き合わせ")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
