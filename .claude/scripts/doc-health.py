#!/usr/bin/env python3
"""仕様ドキュメントの再検証候補と履歴逆引きを生成・計測する。

使い方:
    python3 .claude/scripts/doc-health.py             # 2つの生成物を更新
    python3 .claude/scripts/doc-health.py --check     # 差分検査のみ(CI向け)
    python3 .claude/scripts/doc-health.py --health    # 書き込まず健全性を表示
    python3 .claude/scripts/doc-health.py --as-of=YYYY-MM-DD          # 残務から落ちる候補を並べる(書かない)
    python3 .claude/scripts/doc-health.py --as-of=YYYY-MM-DD --sweep --record=docs/histories/<履歴>.md
                                                       # 候補を docs/residual.md から落とす(--record 必須)
    python3 .claude/scripts/doc-health.py --append-residual="- YYYY-MM-DD <path:節> <一文>"
                                                       # 残務へ1行、錠の下で追記する(同じ鍵が在れば何も書かない)
    python3 .claude/scripts/doc-health.py --resolve-residual="<落とす行の逐語>" \
        --verdict="<直した | 不要と裁定(理由)>" --record=docs/histories/<履歴>.md
                                                       # 解消した1行を、記録を残してから落とす(同じ錠)
    python3 .claude/scripts/doc-health.py --rotate     # 残務が 50 行以上ならローテーションする
    python3 .claude/scripts/doc-health.py --next-issue-id    # 課題票の次の番号を錠の下で払い出す(印字するだけ)
    python3 .claude/scripts/doc-health.py --next-pending-id  # 棚上げ(P-nnn)の次の番号を同じく払い出す
    python3 .claude/scripts/doc-health.py --selftest  # 内蔵fixture

生成物:
    docs/reverification.md      再検証候補 + 鮮度確認の候補(棚上げ・課題票)
    docs/histories/index.md

既存SSOTと確定済み履歴は一切書き換えない。終了コードは 0=成功、1=--checkで差分あり、
2=使い方または解析不能。個々の壊れた参照は生成物に「判定不能」と残し、母集団から黙って
落とさない。

**鮮度確認の候補は判定結果ではない。** 棚上げの解消条件と課題票の closes_when が既に
満たされているかは、内容を読まなければ決まらない(多くは実システムの実行が要る)。ここは
「AI に読ませるべき対象」を機械で並べるだけで、発火の判定は /verify-docs A2 と /build
§1-4・§2★ が行う。**今日の日付は使わない** — 生成物は入力が同じなら同じバイト列になる
(経過日数は読む側が記録日から出す。件数の推移は生成物自身の git 履歴が持っている)。
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import re
import sys
import tempfile

try:
    import fcntl                      # 錠(POSIX のみ。無ければ排他なしで動く — stamps.py と同じ)
except ImportError:                   # pragma: no cover
    fcntl = None
from dataclasses import dataclass
from pathlib import Path

SPEC_DIRS = ("00-requests", "01-requirements", "02-design", "03-impl")
REVERIFY_OUT = Path("docs/reverification.md")
HISTORY_OUT = Path("docs/histories/index.md")
PENDINGS_IN = Path("docs/pendings.md")     # 棚上げ(P-nnn)だけ
RESIDUAL_IN = Path("docs/residual.md")     # 残務(1件1行)。issues-pendings.md §2.1
ISSUES_IN = Path("docs/issues")
GENERATED_NOTE = "<!-- このファイルは doc-health.py が生成する。手書きしない。 -->"
ID_RE = re.compile(
    r"\b(?:RQ-[a-z0-9-]+-\d+|AC-\d+|D[01]-[a-z0-9-]+-\d+|"
    r"FR-[a-z0-9-]+-\d+(?:-\d+)?|NFR-[a-z0-9-]+-\d+|UC-\d+|SR-\d+|"
    r"MOD-[a-z0-9-]+|DSN-[a-z0-9-]+|PLAN-[a-z0-9-]+|CTR-[A-Za-z0-9_.-]+|"
    r"E2E-\d+|MODULE-[a-z0-9-]+|EXTERNAL-[A-Za-z0-9_.-]+|P-\d+)\b"
)
DOC_RE = re.compile(r"docs/(?:00-requests|01-requirements|02-design|03-impl)/[^\s`|),]+\.md")


@dataclass(frozen=True)
class Against:
    doc: str
    version: str


@dataclass(frozen=True)
class Reverification:
    downstream: str
    upstream: str
    verified_version: str
    current_version: str
    status: str
    detail: str = "-"


@dataclass(frozen=True)
class Staleness:
    """記録した時点の事実であり、今も成立しているかを誰も見ていない記録の1件。"""
    kind: str          # 棚上げ / issue
    ident: str
    recorded: str      # 決めた日 / found。**記録日であって最終確認日ではない**
    condition: str     # どうなったら解消が必要か / closes_when
    related: str
    note: str = "-"


@dataclass(frozen=True)
class HistoryRow:
    history: str
    date: str
    task: str
    origin: str
    summary: str
    documents: tuple[str, ...]
    ids: tuple[str, ...]
    issue: str
    parse_note: str = "-"
    recovery: str = "-"


def find_root(start: Path) -> Path:
    cur = start.resolve()
    for candidate in (cur, *cur.parents):
        if (candidate / "CLAUDE.md").is_file() and (candidate / ".claude").is_dir():
            return candidate
    return cur


def split_frontmatter(path: Path) -> tuple[dict[str, str], list[Against], str | None]:
    """単純な規範frontmatterを読む。未知キーは許容し、壊れ方は note で返す。"""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {}, [], f"読取不能: {exc}"
    if not text.startswith("---\n"):
        return {}, [], "frontmatterなし"
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, [], "frontmatter未閉鎖"
    lines = parts[1].splitlines()
    scalars: dict[str, str] = {}
    for line in lines:
        if line.startswith((" ", "\t", "#")) or not line.strip():
            continue
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
        if match:
            scalars[match.group(1)] = match.group(2).strip().strip("'\"")

    against: list[Against] = []
    verified_at = next((i for i, line in enumerate(lines) if line.startswith("verified:")), None)
    if verified_at is not None:
        block: list[str] = []
        for line in lines[verified_at + 1:]:
            if line.strip() and not line.startswith((" ", "\t")):
                break
            block.append(line.strip())
        in_against = False
        pending: str | None = None
        for line in block:
            if line.startswith("against:"):
                in_against = True
            elif in_against:
                inline = re.match(r"^-\s*\{\s*doc:\s*([^,}]+),\s*version:\s*([^}]+)\}", line)
                if inline:
                    against.append(Against(clean(inline.group(1)), clean(inline.group(2))))
                elif line.startswith("- doc:"):
                    pending = clean(line.split(":", 1)[1])
                elif line.startswith("version:") and pending:
                    against.append(Against(pending, clean(line.split(":", 1)[1])))
                    pending = None
        if pending:
            return scalars, against, f"againstのversion欠落: {pending}"
    return scalars, against, None


def clean(value: str) -> str:
    return value.strip().strip("'\"").split(" #", 1)[0].strip()


def major_minor(value: str) -> tuple[int, int] | None:
    match = re.match(r"^(\d+)\.(\d+)(?:\.\d+)?$", value)
    return (int(match.group(1)), int(match.group(2))) if match else None


def specification_files(root: Path) -> list[Path]:
    result: list[Path] = []
    for name in SPEC_DIRS:
        base = root / "docs" / name
        if not base.is_dir():
            continue
        for path in base.rglob("*.md"):
            rel = path.relative_to(root).as_posix()
            if "/callgraphs/" in rel or path.name == "index.md" or path.name == "feature-graph.md":
                continue
            result.append(path)
    return sorted(result)


def collect_reverification(root: Path) -> tuple[list[Reverification], int]:
    rows: list[Reverification] = []
    parse_errors = 0
    for path in specification_files(root):
        rel = path.relative_to(root).as_posix()
        _, against, note = split_frontmatter(path)
        if note:
            parse_errors += 1
        for item in against:
            upstream = root / item.doc
            if not upstream.is_file():
                rows.append(Reverification(rel, item.doc, item.version, "-", "判定不能", "上流が存在しない"))
                continue
            fm, _, up_note = split_frontmatter(upstream)
            current = fm.get("version", "-")
            old_mm, new_mm = major_minor(item.version), major_minor(current)
            if up_note or old_mm is None or new_mm is None:
                detail = up_note or "version形式不正"
                rows.append(Reverification(rel, item.doc, item.version, current, "判定不能", detail))
            elif old_mm == new_mm:
                rows.append(Reverification(rel, item.doc, item.version, current, "最新"))
            else:
                rows.append(Reverification(rel, item.doc, item.version, current, "再検証候補"))
    return rows, parse_errors


def strip_comments(text: str) -> str:
    """HTMLコメントを落とす。**雛形の書式例が本物のエントリに見えるのを防ぐ**
    (pendings.md は空のとき `## P-001 <一行タイトル>` をコメント内に持っている)。"""
    return re.sub(r"<!--[\s\S]*?-->", "", text)


def mask_comments(text: str) -> str:
    """HTMLコメントを**同じ長さの空白**に置き換える(行の数も位置も動かさない)。

    `strip_comments` はコメントを丸ごと落とすので行番号がずれる。**残務の行は行番号で消す**ので、
    読む側と消す側が別のモデルでコメントを扱うと番号がずれ、**履歴に記録したのとは別の行が
    消える**(2026-08-25 の独立検査で実測: 記録は「対象が消えた行」なのに、実際に消えたのは
    その1つ前の生きている行だった)。**この設計が禁じている「消えたが、どこにも記録されて
    いない行」がそこから作れる**ので、残務を見る3つ — 読む(`collect_residual`)・消す
    (`sweep_residual`)・頭を切る(`rotate_residual`)— はすべてこちらを使う。
    """
    return re.sub(r"<!--[\s\S]*?-->",
                  lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)


def collect_pendings(root: Path) -> list[Staleness]:
    """棚上げ(P-nnn)を並べる。**残務は別のファイルであり、ここでは読まない**
    (`collect_residual`。置き場は issues-pendings.md §2.1 が正)。"""
    path = root / PENDINGS_IN
    if not path.is_file():
        return []
    try:
        text = strip_comments(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return [Staleness("棚上げ", "-", "-", "-", "-", f"読取不能: {exc}")]

    rows: list[Staleness] = []
    current: str | None = None
    fields: dict[str, str] = {}
    last: str | None = None       # 折り返しの続きをどの項目に足すか

    def flush() -> None:
        if current is None:
            return
        missing = [label for label in ("決めた日", "どうなったら解消が必要か") if not fields.get(label)]
        rows.append(Staleness(
            "棚上げ", current, fields.get("決めた日", "-"),
            fields.get("どうなったら解消が必要か", "-"), fields.get("関連", "-"),
            "判定不能: " + "/".join(missing) + "が空" if missing else "-"))

    for line in text.splitlines():
        stripped = line.strip()
        heading = re.match(r"^##\s+(P-\d+)\b(.*)$", stripped)
        if heading:
            flush()
            current, fields, last = heading.group(1), {}, None
            continue
        if current is not None:
            item = re.match(r"^-\s*([^:：]+)[:：]\s*(.*)$", stripped)
            if item:
                last = item.group(1).strip()
                fields[last] = item.group(2).strip()
            elif last and stripped and line[:1].isspace():
                # 折り返しの続き。**条件文を途中で切らない** — 一覧が原文と違うと読む側が誤る。
                fields[last] = (fields[last] + " " + stripped).strip()
            elif not stripped:
                last = None
    flush()
    return sorted(rows, key=lambda row: row.ident)


def collect_residual(root: Path) -> tuple[list[str], str]:
    """残務(`docs/residual.md`)の**行そのもの**と最古の日付を返す。

    **生成物に残務の行を出さないのは規範である**(issues-pendings.md §2.1: 検証は残務を
    読み直さない)。行を返すのは掃除(`sweep_residual`)とローテーション(`rotate_residual`)の
    ためだけで、`render_reverification` は今までどおり件数と最古しか受け取らない。

    **押し出された `docs/residual-NNN.md` は読まない** ★(2026-08-25 の裁定)。
    """
    path = root / RESIDUAL_IN
    if not path.is_file():
        return [], "-"
    try:
        text = mask_comments(path.read_text(encoding="utf-8"))
    except OSError:
        return [], "-"
    leftovers: list[str] = []
    in_leftovers = False
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^##\s+残務", stripped):
            in_leftovers = True
            continue
        if stripped.startswith("## "):
            in_leftovers = False
            continue
        if in_leftovers and re.match(r"^-\s+\d{4}-\d{2}-\d{2}\b", stripped):
            leftovers.append(stripped)
    dates = sorted(re.match(r"^-\s+(\d{4}-\d{2}-\d{2})", line).group(1) for line in leftovers)
    return leftovers, dates[0] if dates else "-"


def collect_issues(root: Path) -> list[Staleness]:
    base = root / ISSUES_IN
    if not base.is_dir():
        return []
    rows: list[Staleness] = []
    # 母集団は check-backlog / stamps と同じ「index.md 以外の *.md 全部」に揃える
    # (inspection-17 低位: `[0-9]*.md` だと連番でない issue がこの計器からだけ消え、
    # デプロイゲートと計器で数字が食い違う)。
    for path in sorted(base.glob("*.md")):
        if path.name == "index.md":
            continue
        fm, _, note = split_frontmatter(path)
        closes = fm.get("closes_when", "")
        detail = note or ("判定不能: closes_whenが空" if not closes else "-")
        rows.append(Staleness(
            "issue", fm.get("id", path.stem), fm.get("found", "-"), closes or "-",
            fm.get("related", "-"), detail))
    return rows


def collect_histories(root: Path) -> list[HistoryRow]:
    base = root / "docs/histories"
    if not base.is_dir():
        return []
    rows: list[HistoryRow] = []
    for path in sorted(base.glob("*.md")):
        if path.name == "index.md":
            continue
        fm, _, note = split_frontmatter(path)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            text, note = "", f"読取不能: {exc}"
        documents = tuple(sorted(set(DOC_RE.findall(text))))
        ids = tuple(sorted(set(ID_RE.findall(text))))
        # 新形式は critical: true|false(旧形式の lane: critical も互換で読む)
        critical = fm.get("critical", "")
        if not critical:
            critical = {"critical": "true"}.get(fm.get("lane", ""), "")
            if fm.get("lane", "") in ("fast", "standard", "light", "full"):
                critical = "false"
        rows.append(HistoryRow(
            history=path.relative_to(root).as_posix(), date=fm.get("date", "-"),
            task=fm.get("record", fm.get("task", "-")), origin=fm.get("origin_layer", "-"),
            summary=fm.get("summary", "-"), documents=documents, ids=ids,
            issue=fm.get("issue", "-"), parse_note=note or "-",
            recovery=recovery_status(text, critical)))
    return rows


def recovery_status(text: str, critical: str) -> str:
    """critical: true の新規履歴の復旧記録を警告する。critical/lane の無い旧履歴は互換対象。"""
    if critical in ("", "-"):
        return "旧形式(判定対象外)"
    if critical != "true":
        return "適用外"
    match = re.search(r"^### ロールバック・復旧記録\s*$([\s\S]*?)(?=^## |\Z)", text, re.MULTILINE)
    if not match:
        return "警告: critical復旧記録なし"
    body = re.sub(r"<!--[\s\S]*?-->", "", match.group(1))
    data_rows: list[list[str]] = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or set(stripped) <= set("|- :"):
            continue
        cells = [value.strip() for value in stripped.strip("|").split("|")]
        if cells and cells[0] == "理由ID":
            continue
        data_rows.append(cells)
    if not data_rows:
        return "警告: critical復旧記録が空"
    # **`<>` はセル全体一致で見る。** 部分一致だと SQL の不等号(`delivery_state <> 'delivered'`)を
    # 雛形の空欄と誤認し、逐語で制約を引いた復旧記録を「未記入」と警告する。
    # `<YYYY-MM-DD>` と `<コマンド>` は雛形がセルの中に埋め込んで書く(`templates/history.md` の
    # 確認日の欄・結果の欄)ので、こちらは部分一致のままにする。
    embedded = ("<YYYY-MM-DD>", "<コマンド>")
    for cells in data_rows:
        if len(cells) < 7:
            continue
        if any(cell.strip() == "<>" for cell in cells):
            continue
        if any(token in " ".join(cells) for token in embedded):
            continue
        return "記録済み"
    return "警告: critical復旧記録が未記入"


def md_cell(value: str) -> str:
    return (value or "-").replace("|", "\\|").replace("\n", " ")


def render_reverification(rows: list[Reverification], parse_errors: int,
                          staleness: list[Staleness], leftovers: int, leftover_oldest: str) -> str:
    lines = ["# 再検証候補", "", GENERATED_NOTE, "",
             "上流文書のMAJOR.MINORが検証時から動いた下流文書を可視化する。候補は無効ではないが、上流変更を未確認である。", "",
             "| 下流文書 | 変更した上流 | 検証時version | 現在version | 状態 | 詳細 |",
             "|---|---|---|---|---|---|"]
    visible = [row for row in rows if row.status != "最新"]
    for row in visible:
        lines.append("| " + " | ".join(md_cell(v) for v in (
            row.downstream, row.upstream, row.verified_version, row.current_version, row.status, row.detail)) + " |")
    if not visible:
        lines.append("| (なし) | - | - | - | 最新 | - |")
    counts = {status: sum(row.status == status for row in rows) for status in ("最新", "再検証候補", "判定不能")}
    lines += ["", "## 集計", "",
              f"- 参照総数: {len(rows)}", f"- 最新: {counts['最新']}",
              f"- 再検証候補: {counts['再検証候補']}", f"- 判定不能: {counts['判定不能']}",
              f"- 仕様文書frontmatterの解析警告: {parse_errors}", ""]
    lines += render_staleness(staleness, leftovers, leftover_oldest)
    return "\n".join(lines)


def render_staleness(rows: list[Staleness], leftovers: int, leftover_oldest: str) -> list[str]:
    """棚上げと issue の「今も成立しているか」を読むための一覧。判定は書かない。"""
    lines = ["## 鮮度確認の候補(棚上げ・課題票)", "",
             "記録した時点の事実であり、今も成立しているかは機械には決められない。**ここは判定結果ではなく、"
             "AI が内容を読むべき対象の一覧である**(発火の判定は /verify-docs A2 と /build §1)。",
             "記録日は起票・決定の日であって最終確認日ではない。経過は読む側が記録日から出す。", "",
             "| 種別 | ID | 記録日 | 解消・完了の条件 | 関連 | 解析 |",
             "|---|---|---|---|---|---|"]
    for row in rows:
        lines.append("| " + " | ".join(md_cell(v) for v in (
            row.kind, row.ident, row.recorded, row.condition, row.related, row.note)) + " |")
    if not rows:
        lines.append("| (なし) | - | - | - | - | - |")
    pendings = [row for row in rows if row.kind == "棚上げ"]
    issues = [row for row in rows if row.kind == "issue"]
    lines += ["", "### 集計", "",
              f"- 棚上げ: {len(pendings)}(最古の記録日 {oldest(pendings)})",
              f"- issue: {len(issues)}(最古の記録日 {oldest(issues)})",
              f"- 条件が読めない(判定不能): {sum(row.note != '-' for row in rows)}",
              # 残務は行を出さない(issues-pendings.md §2.1: 検証は読み直さない)。件数と最古だけ。
              f"- 残務: {leftovers} 行(最古 {leftover_oldest})", ""]
    return lines


def oldest(rows: list[Staleness]) -> str:
    dates = sorted(row.recorded for row in rows if re.match(r"^\d{4}-\d{2}-\d{2}$", row.recorded))
    return dates[0] if dates else "-"


def render_history_index(rows: list[HistoryRow]) -> str:
    lines = ["# 履歴 逆引き索引", "", GENERATED_NOTE, "",
             "現行文書、仕様ID、task、issueから確定済み履歴へ辿るための生成索引。抽出できない旧形式は推測で補わない。", "",
             "| 履歴 | 日付 | task | 起点層 | 概要 | 更新文書 | 仕様・機能ID | issue | 復旧記録 | 解析 |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for row in rows:
        link = Path(row.history).name
        values = (f"[{link}]({link})", row.date, row.task, row.origin, row.summary,
                  "<br>".join(row.documents) or "-", "<br>".join(row.ids) or "-", row.issue,
                  row.recovery, row.parse_note)
        lines.append("| " + " | ".join(md_cell(v) for v in values) + " |")
    if not rows:
        lines.append("| (なし) | - | - | - | - | - | - | - | - | - |")
    unindexed = sum(not row.documents and not row.ids for row in rows)
    broken = sum(row.parse_note != "-" for row in rows)
    recovery_warnings = sum(row.recovery.startswith("警告:") for row in rows)
    lines += ["", "## 集計", "", f"- 履歴数: {len(rows)}",
              f"- 文書・IDを索引化できない履歴: {unindexed}", f"- 解析警告: {broken}",
              f"- critical復旧記録の警告: {recovery_warnings}", ""]
    return "\n".join(lines)


def desired_outputs(root: Path) -> tuple[dict[Path, str], list[Reverification], list[HistoryRow], int, list[Staleness]]:
    reverification, parse_errors = collect_reverification(root)
    histories = collect_histories(root)
    pendings = collect_pendings(root)
    leftovers, leftover_oldest = collect_residual(root)
    staleness = pendings + collect_issues(root)
    outputs = {
        root / REVERIFY_OUT: render_reverification(
            reverification, parse_errors, staleness, len(leftovers), leftover_oldest),
        root / HISTORY_OUT: render_history_index(histories),
    }
    return outputs, reverification, histories, parse_errors, staleness


# ---------------------------------------------------------------- 残務の掃除
# **ここから下は生成器の外側である。** desired_outputs は「入力が同じなら同じバイト列」を
# 守るために今日の日付を持たない(冒頭の docstring)。失効判定は日付を要るので、
# `--as-of` で**外から明示的に渡された日付**だけを使い、生成物には一切触れない。
# 書き換える先は手書きの原本 docs/residual.md ただ1つで、`--sweep` か `--rotate` を
# 明示したときだけである(`--rotate` は1行も落とさない — issues-pendings.md §2.1 (2))。

# **50 は上限ではなく、ローテーションの引き金である**(issues-pendings.md §2.1)。
# 2026-08-25 の裁定で、行数の上限(50行)と 90日の恒久受容を廃止した — 落ちるのは
# 「同じ鍵の重複」と「対象が実在しない行」だけであり、**多くなった分は落とさずに押し出す**。
RESIDUAL_ROTATE_AT = 50
LEFTOVER_RE = re.compile(r"^-\s+(\d{4}-\d{2}-\d{2})\s+(\S+)\s*(.*)$")


def leftover_key(line: str) -> str:
    """残務の同一性。**`path:節` だけでは同じ節の別の問題を捨てる**(原則8 違反)ので、
    一文も正規化して鍵に含める(issues-pendings.md §2.1)。"""
    m = LEFTOVER_RE.match(line.strip())
    if not m:
        return line.strip()
    where, what = m.group(2), re.sub(r"\s+", " ", m.group(3)).strip().rstrip("。.")
    return f"{where}|{what}"


def leftover_recorded(line: str) -> str:
    """残務行の**記録日**(順序と期限の鍵)。書式は**日付が先頭**で固定され、同じ鍵の行が既に在れば
    **新しい日付すら書かない**(issues-pendings.md §2.1)。1行が持つ日付は記録した日ただ1つであり、
    後から動かない。**一文の中にたまたま現れる日付は鍵にしない** — 拾うと「〜の裁定が」のように
    日付を引用した行の記録日が、その引用の日付に化ける(最古の表示がそこで狂う)。
    書式に合わない行は空文字を返す(呼ぶ側が無判定として扱う)。"""
    m = LEFTOVER_RE.match(line.strip())
    return m.group(1) if m else ""


# 残務行の `path` の後ろに来る**節の区切り**。規範(issues-pendings.md §2.1)が定める形は
# `path:節` だが、実際の行は `` `path`(注記) `` `` `path`「節」 `` `` `path`・同 `` のように
# 日本語の括弧や中黒でも節を書く。**区切りを `:` だけと決め打つと、節が path に貼り付いたまま
# 実在検査に渡り、実在する文書が「もう無い」と判定されて消える。**
_LEFTOVER_SECTION_SEP = re.compile(r"[:：(（「『【〔・]")
# 集合を指す書き方(glob・ブレース展開)。**1本のパスに解決できないので「不在」と結論できない。**
_LEFTOVER_GLOB = re.compile(r"[*?\[\]{}]")


def leftover_target(where: str) -> str:
    """残務行の `path:節` から **path だけ**を取り出す。取り出せなければ空文字。

    **バッククォートは節を切る前に外す。** `` `docs/a.md`:節 `` を先に `.split(":")` すると
    ``docs/a.md` `` という**末尾にバッククォートが付いた偽のパス**が残り、実在する文書が
    「対象が実在しない」として掃除の候補になる(2026-08-22 実測: 「不在」判定 47 件のうち
    **1件も本当に消えた文書は無く**、23 件がこの末尾バッククォート、18 件が `:` 以外の
    区切り、6 件が集合を指す書き方だった)。

    **誤りの向きが対称でないので、迷ったら「実在する」側へ倒す。** 実在するのに「不在」と
    したら記録が消える(issues-pendings.md §2.1 が禁じる無記録の消去)。逆に不在なのに
    「実在する」としても、残るのは行1本である(多くなった分はローテーションが引き取る)。
    """
    t = _LEFTOVER_SECTION_SEP.split(where.replace("`", ""), 1)[0].strip()
    return "" if _LEFTOVER_GLOB.search(t) else t


def sweep_candidates(root: Path, leftovers: list[str]) -> list[tuple[int, str, str]]:
    """落とす候補を (行番号, 行, 理由) で返す。順序は規範どおり —
    (0) 同一鍵の重複 → (a) path が実在しない。**この2つだけである**
    (2026-08-25 の裁定で、90日の恒久受容と行数の上限を廃止した。issues-pendings.md §2.1)。
    **判定するだけで、書き換えない。**

    **行番号を返すのは必須である。** 行の文字列で集合を作って削除すると、完全に同一の行が2本
    あるとき「2本目だけが候補」なのに**両方消える** — 原則8 が禁じる無記録の消去になる。
    """
    out: list[tuple[int, str, str]] = []
    dropped: set[int] = set()
    seen: dict[str, int] = {}
    for i, line in enumerate(leftovers):
        key = leftover_key(line)
        if key in seen:
            out.append((i, line, f"重複(同じ鍵の先行行が在る: {leftovers[seen[key]].strip()[:60]})"))
            dropped.add(i)
        else:
            seen[key] = i
    for i, line in enumerate(leftovers):
        if i in dropped:
            continue
        m = LEFTOVER_RE.match(line.strip())
        if not m:
            continue
        target = leftover_target(m.group(2))
        if target.startswith("docs/") and not (root / target).exists():
            out.append((i, line, f"対象が実在しない: {target}"))
            dropped.add(i)
    return out


def sweep_residual(root: Path, as_of: str, apply: bool, record: Path | None = None
                   ) -> tuple[int, list[tuple[int, str, str]]]:
    """候補を出し、`apply` のときだけ `docs/residual.md` から落とす。

    **記録が先、削除が後である。** `apply` には `record`(履歴ファイル)が要り、落とした行は
    **原本を書き換える前に**そこへ追記される。逆順にすると、途中で止まったときに
    「消えたが、どこにも残っていない」行ができる。`docs/reverification.md` は毎回まるごと
    生成し直されるので記録先にならない(規範: issues-pendings.md §2.1)。

    **`as_of` が決めるのは履歴に書く実行日だけで、どの行が落ちるかには効かない** ★ —
    2026-08-25 の裁定で 90日の恒久受容が廃止され、日付で落ちる行が無くなった。
    それでも外から渡させるのは、この生成器が「今日」を持たないという設計を崩さないためである。

    削除は**行番号**で行う。完全に同一の行が2本あるとき、文字列一致だと両方消える。
    """
    path = root / RESIDUAL_IN
    if not path.is_file():
        return 0, []
    if not apply:
        leftovers, _ = collect_residual(root)
        return len(leftovers), sweep_candidates(root, leftovers)
    if record is None:
        raise ValueError("apply には record(履歴ファイル)が要る")
    # **落とすときは、数えるところから書き戻すところまでを錠の中に置く** ★
    # (2026-09-13。追記 `--append-residual` と押し出し `--rotate` と同じ錠である)。
    # 外に置くと、**数えた後・書き戻す前**に入った追記を、古い本文で上書きして消す。
    # 行番号で落とす仕組みなので、そのあいだに行が増えると落とす行もずれる。
    with _lock(root):
        return _sweep_locked(root, path, as_of, record)


def _sweep_locked(root: Path, path: Path, as_of: str, record: Path
                  ) -> tuple[int, list[tuple[int, str, str]]]:
    """`sweep_residual` の中身。**錠を持った状態でだけ呼ぶ。**"""
    leftovers, _ = collect_residual(root)
    cands = sweep_candidates(root, leftovers)
    if not cands:
        return len(leftovers), cands

    # 1) 先に履歴へ追記する
    lines = [f"\n## 残務から落とした行({as_of} 実行)\n",
             "この一覧は `doc-health.py --as-of --sweep` が落とした行である。"
             "落ちるのは**同じ鍵の重複**と**対象が実在しない行**の2つだけで、"
             "落としたこと自体が決定であって、指摘でも新しい issue でもない"
             "(`.claude/directions/issues-pendings.md` §2.1)。\n"]
    for _, line, why in cands:
        lines.append(f"- {line.strip()}\n  - 理由: {why}\n")
    record.parent.mkdir(parents=True, exist_ok=True)
    with record.open("a", encoding="utf-8") as handle:
        handle.write("".join(lines))

    # 2) そのあとで原本から落とす(行番号で)
    # **判定はマスクした側、書き出すのは原文の行である** — `collect_residual` と同じ
    # コメントのモデルで数えなければ番号がずれ、記録した行とは別の行が消える。
    raw_text = path.read_text(encoding="utf-8")
    raw_lines = raw_text.splitlines()
    masked_lines = mask_comments(raw_text).splitlines()
    drop_idx = {i for i, _, _ in cands}
    out, seen, in_leftovers = [], 0, False
    for line, masked in zip(raw_lines, masked_lines):
        stripped = masked.strip()
        if re.match(r"^##\s+残務", stripped):
            in_leftovers = True
        elif stripped.startswith("## "):
            in_leftovers = False
        if in_leftovers and re.match(r"^-\s+\d{4}-\d{2}-\d{2}\b", stripped):
            hit = seen in drop_idx
            seen += 1
            if hit:
                continue
        out.append(line)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return len(leftovers), cands


def residual_ledger_gap(root: Path) -> str:
    """残務の台帳が使える形かを見て、駄目なら理由を1行で返す(使えるなら空文字)。

    見るのは2つ。**どちらも「0行」と読んではならない**(`check-backlog.py` と同じ fail-closed —
    数えられなかったのであって、少なかったのではない):

    - `docs/residual.md` が無い(2026-08-25 より前の版から上げたプロジェクト)
    - `docs/pendings.md` に `## 残務` の節がまだ在る(移行の手が半分で止まっている)

    2つ目を見るのは、**`cp` だけして行の移し替えを忘れると、既存の行が全部見えないまま
    「残務 0 行」で通ってしまう**からである(2026-08-25 の独立検査で実測)。
    移行の手順は `.claude/directions/issues-pendings.md` §2.1 が正である。
    """
    where = "`.claude/directions/issues-pendings.md` §2.1 の「旧い版から上げたとき」"
    if not (root / RESIDUAL_IN).is_file():
        return f"残務の台帳が無い: {RESIDUAL_IN}(/setup が作るもの。移行の手順は {where})"
    old = root / PENDINGS_IN
    if old.is_file():
        for line in mask_comments(old.read_text(encoding="utf-8")).splitlines():
            if re.match(r"^##\s+残務", line.strip()):
                return (f"{PENDINGS_IN} に `## 残務` の節がまだ在る — 移行が途中である"
                        f"(その行は誰からも見えない)。手順は {where}")
    return ""


LOCK_FILE = Path(".claude/state/doc-health.lock")   # 錠の実体。中身は使わない
IDS_STATE = Path(".claude/state/ids.json")          # 払い出した番号の控え {"issue": N, "pending": N}


@contextlib.contextmanager
def _lock(root: Path):
    """ローテーションと採番を排他する(stamps.py の `state_lock` と同じ形)。

    どちらも read-modify-write であり、2本が重なると **同じ連番を2度払い出す**(採番)か、
    **同じ中身の押し出しが2つできる / 空の押し出しができる**(ローテーション)。規範は
    これらの衝突を機械で塞ぐと決めた(2026-09-05。正は issues-pendings.md §2.2・§3。
    **複数の作業を並走させる艦隊キットでは**、この錠が「残務・先送りの行は並走の直列化理由に
    しない」と決めた代わりでもある — そちらの正は艦隊キットの orchestration.md §3.4。
    単独運用キットに §3.4 は無いが、錠は同じに要る)。
    """
    path = root / LOCK_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    if fcntl is None:                  # pragma: no cover — POSIX 以外
        yield
        return
    with open(path, "a+", encoding="utf-8") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def _scan_used_ids(root: Path, kind: str) -> int:
    """使用済みの番号の最大値を実物から集める。

    連番は**再利用しない**(issues-pendings.md §2.2・§3)。台帳や課題票は解消時に消えるので、
    現物の最大値だけでは足りない — 履歴と 02 に残る参照も見る(規範が手作業の走査に
    指定していた範囲と同じ)。**それでも消え切った番号はありうる**ので、最終の守りは
    `ids.json` の控え(払い出した最大値。単調に増える)との max である。
    """
    used = 0
    if kind == "issue":
        d = root / "docs/issues"
        for q in (d.glob("*.md") if d.is_dir() else []):
            m = re.match(r"(\d{3})-", q.name)
            if m:
                used = max(used, int(m.group(1)))
        scan_dirs = [root / "docs/histories"]
        pat = re.compile(r"issues/(\d{3})-")
    else:
        scan_dirs = [root / "docs/histories", root / "docs/02-design"]
        pat = re.compile(r"P-(\d{3})")
        f = root / "docs/pendings.md"
        if f.is_file():
            for m in pat.finditer(f.read_text(encoding="utf-8")):
                used = max(used, int(m.group(1)))
    for d in scan_dirs:
        if not d.is_dir():
            continue
        for q in d.rglob("*.md"):
            try:
                text = q.read_text(encoding="utf-8")
            except OSError:            # pragma: no cover — 読めない1本で採番を止めない
                continue
            for m in pat.finditer(text):
                used = max(used, int(m.group(1)))
    return used


def next_id(root: Path, kind: str) -> str:
    """課題票(issue)/ 棚上げ(pending)の次の番号を**錠の下で払い出す**。

    読む → 最大を決める → 控えを進める、を1つの錠の中で行うので、並走する2本が同じ番号を
    受け取ることはない。控え(`ids.json`)は単調に増え、**実物が全部消えた番号も再発行しない**。

    **控えが読めない・形が壊れているときは、黙って数え直さずに失敗する** ★ — 壊れた控えを
    0 と読めば、実物の消えた番号を再発行する(独立確認 2026-09-05)。直すのは人間である。
    **復旧する値は「過去に払い出した最大」以上と確かめられるものにする** — それより小さい値に
    すると、実物の消えた番号を再発行しうる。確かめられないなら、履歴と 02 を走査して
    見つかる最大 + 十分な余裕を置くか、判断できるまで止まる。
    書込みは一時ファイル経由の置き換え(途中で落ちても壊れた控えを残さない)。
    """
    assert kind in ("issue", "pending"), kind
    with _lock(root):
        state_path = root / IDS_STATE
        state: dict = {}
        if state_path.is_file():
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
                if not isinstance(state, dict):
                    raise ValueError(f"辞書でない: {type(state).__name__}")
                for k, v in state.items():
                    if k not in ("issue", "pending"):
                        continue
                    if type(v) is not int:
                        # isinstance では bool(int の派生型)が通る — 2周目の独立確認で実測
                        raise ValueError(f"{k} が整数でない: {v!r}")
                    if not (0 <= v <= 999):
                        # 負数は max() が実物の走査へ黙って倒し、消えた番号を再発行する —
                        # 範囲も契約の一部である(独立確認 2026-09-05 の再現)
                        raise ValueError(f"{k} が 0..999 の外: {v!r}")
            except (ValueError, OSError) as e:
                raise SystemExit(f"エラー: 採番の控え({state_path})が壊れている: {e}。"
                                 f"黙って数え直すと消えた番号を再発行するので、失敗する。"
                                 f"人間が中身を直すこと(形は {{\"issue\": N, \"pending\": N}})") from e
        nxt = max(_scan_used_ids(root, kind), int(state.get(kind, 0) or 0)) + 1
        if nxt > 999:
            # 連番は3桁である(issues-pendings.md)。走査も検査(CS27)も3桁を前提に
            # しているので、**桁を増やす判断を採番が勝手にしない** — 控えを進める前に止まる。
            raise SystemExit(f"エラー: {kind} の連番が 999 を超える。3桁の上限である — "
                             f"桁を増やすかどうかは人間の判断である(issues-pendings.md)")
        state[kind] = nxt
        state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = state_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        os.replace(tmp, state_path)
        return f"{nxt:03d}"


def rotate_residual(root: Path, apply: bool = True) -> tuple[int, Path | None]:
    """残務が `RESIDUAL_ROTATE_AT` 行以上なら、ファイルをローテーションする。

    `docs/residual.md` の中身を `docs/residual-<3桁の連番>.md` へ**複写してから、元を空にする**
    (**先に改名しない** — そのあいだに落ちると台帳が消えたまま残り、打ち直しても戻らない)。
    書き手から見えるのは「番号の付いた名前へ移り、同じ名前の新しいファイルが在る」ことである。新しいほうは**元のファイルの、残務の行より前の部分**(見出しと書式の
    注記)をそのまま引き継ぐ — 雛形をこのスクリプトが知らずに済み、書き手が見る形も変わらない。

    **1行も落とさない。** だから掃除(`sweep_residual`)と違って `--record` も権限の制限も
    要らない(規範: issues-pendings.md §2.1 (2))。**押し出したファイルはどのフローも読まない。**

    戻り値は (ローテーションする前の行数, 押し出した先のパス or None)。50 未満なら何もしない。
    """
    path = root / RESIDUAL_IN
    if not path.is_file():
        return 0, None
    leftovers, _ = collect_residual(root)
    if len(leftovers) < RESIDUAL_ROTATE_AT:
        return len(leftovers), None
    # 連番は既存の最大 + 1。**歯抜けが在っても詰めない** — 番号は順序であって数量ではない。
    # **glob から「元を空にする」までを錠で包む**(2026-09-05 — 2本が重なると、同じ中身の
    # 押し出しが2つできるか、空の押し出しができる。錠の理由の全文は _lock の docstring)。
    with _lock(root):
        return _rotate_locked(root, path, apply)


def _rotate_locked(root: Path, path: Path, apply: bool) -> tuple[int, Path | None]:
    leftovers, _ = collect_residual(root)
    if len(leftovers) < RESIDUAL_ROTATE_AT:
        return len(leftovers), None
    used = [int(q.stem.rsplit("-", 1)[1]) for q in path.parent.glob("residual-*.md")
            if q.stem.rsplit("-", 1)[-1].isdigit()]
    dest = path.parent / f"residual-{max(used, default=0) + 1:03d}.md"
    if not apply:
        return len(leftovers), dest
    # 残務の行より前(見出しと注記)を、新しいファイルの頭として引き継ぐ。
    # **`## 残務` の見出しそのものは頭に含める** — 無ければ次に書く者の行き先が消える。
    # **コメントの中の `## 残務` で切らない** ★ — 雛形の注記が行頭に `##` を持つと、そこで
    # 切った頭は `<!--` を閉じないまま新しいファイルへ入り、以後の残務行がコメントに沈む。
    # 判定は `mask_comments` に任せる(読む側と同じモデルであることが要点である)。
    text = path.read_text(encoding="utf-8")
    raw_lines = text.splitlines()
    head: list[str] = []
    found = False
    for line, masked in zip(raw_lines, mask_comments(text).splitlines()):
        head.append(line)
        if re.match(r"^##\s+残務", masked.strip()):
            found = True
            break
    if not found:
        # ここへ来るなら、行を数えた側(`collect_residual`)と見出しの探し方が食い違っている。
        # **黙って「押し出した」と名乗らない** — 名乗ると、1行も片付かないまま押し出しの
        # 写しだけが増え続ける(2026-08-25 の独立検査で実測)。
        raise ValueError("残務の見出し(## 残務)が見つからない: " + str(path))
    # **押し出しは「複写してから元を空にする」順である** ★ — 先に改名すると、そのあいだに
    # 落ちたとき `docs/residual.md` が消えたまま残り、`--rotate` を打ち直しても戻らない
    # (`check-backlog.py` は台帳の欠落を fail-closed で拒むので、次の `/build` が入口で止まる)。
    # この順なら、落ちても台帳は在り、押し出しの写しが1本余分にできるだけである。
    dest.write_text(text, encoding="utf-8")
    # **複写のあいだに足された行を、切り詰めた新しいファイルへ引き継ぐ** ★(独立確認
    # 2026-09-05: 追記は錠を取らないので、読んでから空にするまでに他のフローが1行足すと、
    # その行が元からも押し出し先からも消えていた)。再読して増分を運ぶ — 残る競合の区間は
    # この再読から書込みまでに縮む(錠を取らない書き手をゼロにはできない。規範は
    # issues-pendings.md §2.1 — 追記は1行の append なのでこの区間で実際に失う確率は小さい)。
    current = path.read_text(encoding="utf-8")
    carried = _carry_new_lines(text, current)
    body = ("\n".join(carried) + "\n") if carried else "なし\n"
    path.write_text("\n".join(head) + "\n\n" + body, encoding="utf-8")
    return len(leftovers), dest


def _carry_new_lines(snapshot: str, current: str) -> list[str]:
    """複写(snapshot)の後に足された行を返す。追記は末尾への append が前提である。"""
    if current == snapshot:
        return []
    snap_lines = snapshot.splitlines()
    cur_lines = current.splitlines()
    # 末尾追記なら、current は snapshot を接頭辞に持つ
    if cur_lines[:len(snap_lines)] == snap_lines:
        return [l for l in cur_lines[len(snap_lines):] if l.strip()]
    # 前提が崩れていたら(途中への挿入・削除)、集合差で拾う — 順序は current に従う
    snap_set = set(snap_lines)
    return [l for l in cur_lines if l.strip() and l not in snap_set]


def append_residual(root: Path, line: str) -> tuple[str, int]:
    """残務の行を1本、**錠の下で**追記する。戻り値は (結果, 追記後の行数)。

    結果は `"追記"` か `"重複"` のどちらかである。

    **読取りから書戻しまでを `_lock` で包む** ★(2026-09-12 の検査 A2-6)。包まないと、
    押し出し(`_rotate_locked`)が**複写してから元を空にするまで**のあいだに足した行が、
    押し出し先にも新しい台帳にも残らない。2026-09-05 に `_carry_new_lines` で区間を
    「再読から書込みまで」に縮めたが、**錠を取らない書き手が居るかぎり区間は消えない** —
    書き手が全員この関数を通れば、区間そのものが無くなる(規範: issues-pendings.md §2.1)。

    **鍵の重複もここで見る。** 規範は「同じ鍵が在るなら何も書かない」と定めているが、
    各フローが grep してから書く形だと、**その grep と書込みのあいだ**で同じ競合が起きる。
    """
    path = root / RESIDUAL_IN
    if not path.is_file():
        raise SystemExit(f"エラー: 残務の台帳が無い: {RESIDUAL_IN}"
                         "(/setup が作るもの。issues-pendings.md §2.1)")
    entry = line.strip()
    if not LEFTOVER_RE.match(entry):
        raise SystemExit("エラー: 残務の行の形が違う。"
                         "`- <YYYY-MM-DD> <path:節> <一文>` で渡す"
                         "(日付が先頭なのは飾りではない。issues-pendings.md §2.1)")
    with _lock(root):
        leftovers, _ = collect_residual(root)
        key = leftover_key(entry)
        if any(leftover_key(existing) == key for existing in leftovers):
            return "重複", len(leftovers)
        raw_text = path.read_text(encoding="utf-8")
        raw_lines = raw_text.splitlines()
        masked_lines = mask_comments(raw_text).splitlines()
        # 節の範囲を出す。**判定はマスクした側である** — コメントの中の `##` で切ると、
        # 書いた行がコメントの内側へ落ちて誰からも見えなくなる(_rotate_locked と同じ理由)。
        start = end = None
        for i, masked in enumerate(masked_lines):
            stripped = masked.strip()
            if start is None:
                if re.match(r"^##\s+残務", stripped):
                    start = i
                continue
            if stripped.startswith("## "):
                end = i
                break
        if start is None:
            raise ValueError("残務の見出し(## 残務)が見つからない: " + str(path))
        if end is None:
            end = len(raw_lines)
        # 空の台帳の印(「なし」)は、行が1本でも入った時点で落とす。
        body = [x for x in raw_lines[start + 1:end] if x.strip() and x.strip() != "なし"]
        body.append(entry)
        out = raw_lines[:start + 1] + [""] + body + [""] + raw_lines[end:]
        path.write_text("\n".join(out).rstrip("\n") + "\n", encoding="utf-8")
    return "追記", len(leftovers) + 1


def resolve_residual(root: Path, key_line: str, verdict: str, record: Path
                     ) -> tuple[str, int]:
    """解消した残務の1行を、記録を残してから台帳から落とす。**追記・押し出しと同じ錠を取る。**

    **直接 `docs/residual.md` を開いて消さない** ★(2026-09-13 の検査 A2-6)—
    錠を取らない書き手が1つでも居れば、その書き手が読んでから書き戻すまでのあいだに
    入った追記が、古い本文で上書きされて消える。**追記だけを錠に入れても塞がらない。**

    `key_line` は落とす行の逐語(先頭の `- ` は在っても無くてもよい)。
    `verdict` は「直した」「不要と裁定(理由)」のような、**なぜ落とすか**である。
    戻り値は (結果, 残った行数)。結果は `削除` か `不在`(その行が無かった)。
    """
    path = root / RESIDUAL_IN
    if not path.is_file():
        raise SystemExit(f"エラー: 残務の台帳が無い: {RESIDUAL_IN}"
                         "(/setup が作るもの。issues-pendings.md §2.1)")
    if not verdict.strip():
        raise SystemExit("エラー: --resolve-residual には --verdict=<なぜ落とすか> が要る"
                         "(理由の無い削除は、記録から見て事故と区別が付かない)")
    raw = key_line.strip()
    want = leftover_key(raw if raw.startswith("- ") else "- " + raw)
    with _lock(root):
        leftovers, _ = collect_residual(root)
        hit = [x for x in leftovers if leftover_key(x) == want]
        if not hit:
            return "不在", len(leftovers)
        record.parent.mkdir(parents=True, exist_ok=True)
        with record.open("a", encoding="utf-8") as handle:   # **記録が先、削除が後**
            handle.write(f"\n## 残務から落とした行(解消)\n")
            for x in hit:
                body = x.strip()
                handle.write(f"{body if body.startswith('- ') else '- ' + body}\n"
                             f"  - 判定: {verdict.strip()}\n")
        raw_text = path.read_text(encoding="utf-8")
        raw_lines = raw_text.splitlines()
        masked_lines = mask_comments(raw_text).splitlines()
        out, in_leftovers, dropped = [], False, 0
        for line, masked in zip(raw_lines, masked_lines):
            stripped = masked.strip()
            if re.match(r"^##\s+残務", stripped):
                in_leftovers = True
            elif stripped.startswith("## "):
                in_leftovers = False
            if (in_leftovers and re.match(r"^-\s+\d{4}-\d{2}-\d{2}\b", stripped)
                    and leftover_key(stripped) == want):
                dropped += 1
                continue
            out.append(line)
        path.write_text("\n".join(out).rstrip("\n") + "\n", encoding="utf-8")
    return "削除", len(leftovers) - dropped


def health(rows: list[Reverification], histories: list[HistoryRow], parse_errors: int,
           staleness: list[Staleness]) -> str:
    candidates = sum(row.status == "再検証候補" for row in rows)
    unknown = sum(row.status == "判定不能" for row in rows) + parse_errors
    unindexed = sum(not row.documents and not row.ids for row in histories)
    broken_history = sum(row.parse_note != "-" for row in histories)
    recovery_warnings = sum(row.recovery.startswith("警告:") for row in histories)
    pendings = [row for row in staleness if row.kind == "棚上げ"]
    issues = [row for row in staleness if row.kind == "issue"]
    return "\n".join(("## 仕様ドキュメント健全性(警告のみ)",
        f"- 再検証候補: {candidates}", f"- 再検証の判定不能・解析警告: {unknown}",
        f"- 履歴: {len(histories)}", f"- 文書・IDを索引化できない履歴: {unindexed}",
        f"- 履歴の解析警告: {broken_history}",
        f"- critical復旧記録の警告: {recovery_warnings}",
        # 件数の推移(`.claude/directions/core.md` §3 の「issue 純増」)は、生成物 docs/reverification.md 自身の
        # git 履歴が持つ。ここで今日の日付を使うと生成物の決定性が壊れるので使わない。
        f"- 鮮度確認の候補(棚上げ): {len(pendings)}(最古 {oldest(pendings)})",
        f"- 鮮度確認の候補(課題票): {len(issues)}(最古 {oldest(issues)})",
        f"- 鮮度の条件が読めない: {sum(row.note != '-' for row in staleness)}"))


def selftest() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".claude").mkdir(); (root / "CLAUDE.md").write_text("# fixture\n")
        req = root / "docs/01-requirements/a.md"; req.parent.mkdir(parents=True)
        req.write_text("---\nid: req\nversion: 1.2.0\n---\n# FR-x-01\n")
        design = root / "docs/02-design/a.md"; design.parent.mkdir(parents=True)
        design.write_text("---\nid: design\nversion: 1.0.0\nverified:\n  at: 2026-01-01\n  version: 1.0.0\n  against:\n    - {doc: docs/01-requirements/a.md, version: 1.1.0}\n---\n# design\n")
        history = root / "docs/histories/2026-01-01-x.md"; history.parent.mkdir(parents=True)
        history.write_text("---\nid: h\ndate: 2026-01-01\nrecord: docs/build-records/x.md\ncritical: true\norigin_layer: 01\nissue: 001-bug-x\nsummary: x\n---\n# x\n## 変更理由\n### R-01 fixture\n| docs/01-requirements/a.md | FR-x-01 MODULE-x |\n## 実施した移行\n### ロールバック・復旧記録\n| 理由ID | 不可逆点 | 条件 | 手順 | 復元元 | 確認日 | 結果 |\n|---|---|---|---|---|---|---|\n| R-01 | なし(可逆) | 常時 | revert | backup | 2026-01-01 | `test` → 成功 |\n")
        # 棚上げ2件(1件は解消条件が空 = 判定不能)、残務2行(**別ファイル**)、雛形のコメント内の
        # 書式例が本物に見えないこと、を1つの fixture で見る。
        (root / "docs/pendings.md").write_text(
            "<!-- 書式: ## P-001 <一行タイトル> / - 決めた日: <YYYY-MM-DD> -->\n"
            "# 棚上げ事項\n\n"
            "## P-003 MFA のバックアップコードは未実装\n"
            "- 決めた日: 2026-02-01\n- 決めた人: 人間\n- 何が不完全か: x\n- なぜ今は OK か: y\n"
            "- どうなったら解消が必要か: 外部監査が始まったとき\n"
            "  または利用者が1000人を超えたとき\n"        # 折り返しの続きを拾うか
            "- 関連: FR-auth-05-3\n\n"
            "## P-004 条件を書き忘れた棚上げ\n- 決めた日: 2026-03-01\n- 関連: なし\n")
        # **残務は別のファイルである**(issues-pendings.md §2.1。2026-08-25 の裁定)
        (root / "docs/residual.md").write_text(
            "<!-- 書式: - <YYYY-MM-DD> <path:節> <一文> -->\n"
            "# 残務\n\n"
            "## 残務(文書整合ほか)\n\n"
            "- 2026-01-15 docs/02-design/a.md:§2 表の穴\n"
            "- 2026-04-02 docs/01-requirements/a.md:§1 言い回し\n")
        issues = root / "docs/issues"; issues.mkdir(parents=True)
        (issues / "007-bug-x.md").write_text(
            "---\nid: 007-bug-x\ntype: bug\nseverity: 高\nfound: 2026-01-20\n"
            "closes_when: カウンタが成功ログインでリセットされ FR-auth-02-3 が green\n"
            "related: FR-auth-02\nsummary: x\n---\n# 007\n")
        (issues / "index.md").write_text("# 課題 一覧\n")   # index は母集団に入れない

        outputs, reverify, histories, errors, staleness = desired_outputs(root)
        assert len(reverify) == 1 and reverify[0].status == "再検証候補"
        assert histories[0].documents == ("docs/01-requirements/a.md",)
        assert histories[0].ids == ("FR-x-01", "MODULE-x")
        assert histories[0].recovery == "記録済み"
        assert recovery_status("# legacy\n", "-") == "旧形式(判定対象外)"
        assert recovery_status("# critical\n", "true") == "警告: critical復旧記録なし"
        # **`<>` はセル全体一致**。SQL の不等号を逐語で引いた復旧記録を空欄と誤認しない
        head = ("# x\n### ロールバック・復旧記録\n"
                "| 理由ID | 不可逆点 | 条件 | 手順 | 復元元 | 確認日 | 結果 |\n"
                "|---|---|---|---|---|---|---|\n")
        sql = head + ("| R-01 | スキーマ移行 | 24時間以内 | "
                      "`CHECK (delivery_state <> 'delivered')` を戻す | バックアップ | "
                      "2026-08-20 | `sqlite3 board.db .schema` → 一致 |\n")
        assert recovery_status(sql, "true") == "記録済み", recovery_status(sql, "true")
        tmpl = head + ("| R-01 | <なし(理由)> | <> | <> | <バックアップ> | <YYYY-MM-DD> | "
                       "`<コマンド>` → <結果> |\n")
        assert recovery_status(tmpl, "true") == "警告: critical復旧記録が未記入"
        # 雛形のうち埋め込みの欄だけが未記入でも見逃さない(部分一致を残した理由)
        half = head + ("| R-01 | スキーマ移行 | 24時間以内 | 手順あり | バックアップ | "
                       "2026-08-20 | `<コマンド>` → <結果> |\n")
        assert recovery_status(half, "true") == "警告: critical復旧記録が未記入"
        assert errors == 0
        ids = [row.ident for row in staleness]
        assert ids == ["P-003", "P-004", "007-bug-x"], ids
        assert staleness[0].condition == "外部監査が始まったとき または利用者が1000人を超えたとき"
        assert staleness[1].note.startswith("判定不能:")      # 解消条件が空
        assert staleness[2].kind == "issue" and staleness[2].recorded == "2026-01-20"
        pendings = collect_pendings(root)
        leftovers, leftover_oldest = collect_residual(root)
        assert (len(pendings), len(leftovers), leftover_oldest) == (2, 2, "2026-01-15")

        # --- 残務の掃除(生成器の外側。落ちるのは重複と実在しない対象の2つだけ) ---
        assert leftover_key("- 2026-01-15 docs/02-design/system.md:§3 表に穴") == \
               leftover_key("- 2026-03-01 docs/02-design/system.md:§3  表に穴。"), "鍵が日付に依存している"
        assert sweep_candidates(root, leftovers) == [], "実在する2行が落ちた"
        gone = "- 2026-01-15 docs/02-design/nonexistent.md:§1 参照が切れている"
        cands = sweep_candidates(root, [gone])
        assert len(cands) == 1 and "実在しない" in cands[0][2], cands
        real = "docs/01-requirements/a.md"      # fixture に実在する(重複判定だけを見たい)
        # **古いというだけでは落ちない** ★(2026-08-25 の裁定で 90日の恒久受容を廃止した)
        ancient = f"- 2020-01-01 {real}:§9 何年も誰も動かしていない"
        assert sweep_candidates(root, [ancient]) == [], "古さで落ちている(90日の規則が残っている)"
        # **多いというだけでも落ちない**(上限は無い。多い分はローテーションが引き取る)
        many = [f"- 2026-04-01 {real}:§{n} 穴{n}" for n in range(RESIDUAL_ROTATE_AT * 2)]
        assert sweep_candidates(root, many) == [], "行数で落ちている(上限が残っている)"
        # --- path の取り出し。**節の区切りは `:` だけではない** ---
        # バッククォート付きの `` `path`:節 `` を先に `:` で切ると ``a.md` `` という偽のパスが
        # 残り、**実在する文書が「もう無い」として掃除の候補になる**。2026-08-22 の実測では
        # 「不在」47 件のうち**本当に消えた文書は 1 件も無く**、18 行が消える側へ回っていた。
        for form in (f"`{real}`:§1", f"`{real}`(注記)", f"`{real}`「節」", f"`{real}`・同",
                     f"`{real}`(26,282", f"{real}(要件カバレッジ)/"):
            line = f"- 2026-01-15 {form} 実在するのに不在と判定されてはならない"
            assert sweep_candidates(root, [line]) == [], \
                f"実在する文書を不在と判定した: {form}"
        # 集合を指す書き方は1本のパスに解決できない。**「不在」と結論しない**(消さない側へ倒す)
        for form in (f"`{real[:-4]}*.md`:§1", "`docs/01-requirements/f-{a,b}.md`:§1"):
            line = f"- 2026-01-15 {form} 集合を指す行を不在と結論してはならない"
            assert sweep_candidates(root, [line]) == [], \
                f"集合を指す行を不在と判定した: {form}"
        # 本当に消えた文書は、バッククォート付きでも候補になる(濾しすぎていないこと)
        goneq = "- 2026-01-15 `docs/02-design/nonexistent.md`:§1 参照が切れている"
        cands = sweep_candidates(root, [goneq])
        assert len(cands) == 1 and "実在しない" in cands[0][2], cands
        dup = [f"- 2026-01-15 {real}:§1 同じこと", f"- 2026-02-01 {real}:§1 同じこと。"]
        cands = sweep_candidates(root, dup)
        assert len(cands) == 1 and cands[0][0] == 1 and "重複" in cands[0][2], cands
        # 記録日は**行頭のもの**ただ1つ。一文の中の日付は鍵にしない(最古の表示が狂う)
        quoted = f"- 2026-01-15 {real}:§9 穴 2026-05-01 の裁定が反映されていない"
        assert leftover_recorded(quoted) == "2026-01-15", "本文の日付を鍵に採っている"
        # **完全に同一の行**が2本。候補は2本目だけで、削除も2本目だけでなければならない
        # (文字列一致で消すと両方消える = 無記録の消去。独立レビューが見つけた欠陥)。
        same = f"- 2026-01-15 {real}:§1 まったく同じ行"
        cands = sweep_candidates(root, [same, same])
        assert [c[0] for c in cands] == [1], f"完全同一行の候補が誤り: {cands}"
        before = (root / RESIDUAL_IN).read_text()
        (root / RESIDUAL_IN).write_text(before.replace("## 残務(文書整合ほか)",
                                                      f"## 残務(文書整合ほか)\n{same}\n{same}"))
        hist = root / "sweep-record-1.md"   # 履歴の母集団を汚さない(下の決定性検査のため)
        sweep_residual(root, "2026-01-16", apply=True, record=hist)
        left_after, _ = collect_residual(root)
        assert sum(1 for l in left_after if l == same) == 1, \
            f"完全同一行が両方消えた(または残りすぎた): {left_after}"
        (root / RESIDUAL_IN).write_text(before)
        # --sweep を付けなければ 1 バイトも書き換えない
        sweep_residual(root, "2026-09-01", apply=False)
        assert (root / RESIDUAL_IN).read_text() == before, "候補列挙だけのはずが書き換えた"
        # **記録が先、削除が後**。履歴に落とした行が載っていること
        (root / RESIDUAL_IN).write_text(before.replace(
            "- 2026-01-15 docs/02-design/a.md:§2 表の穴", gone))
        hist2 = root / "sweep-record-2.md"
        sweep_residual(root, "2026-09-01", apply=True, record=hist2)
        assert hist2.is_file() and "残務から落とした行" in hist2.read_text(), "履歴へ記録されていない"
        assert "P-003" in (root / PENDINGS_IN).read_text(), "棚上げのファイルを触った"
        left2, _ = collect_residual(root)
        assert len(left2) == 1, f"実在しない対象の行が落ちていない: {left2}"
        (root / RESIDUAL_IN).write_text(before)

        # **コメントで包んだ日付行が在っても、記録した行だけが消える** ★
        # (2026-08-25 の独立検査 H-1: 読む側と消す側でコメントの扱いが違い、番号がずれて
        #  履歴に書いたのとは別の行が消えていた。この設計が禁じる無記録の消去である。)
        (root / RESIDUAL_IN).write_text(
            "# 残務\n\n## 残務(文書整合ほか)\n\n"
            "<!-- しまってある行\n- 2026-01-01 " + real + ":§0 コメントの中\n-->\n"
            f"- 2026-02-01 {real}:§1 生きている行A\n"
            "- 2026-02-02 docs/02-design/nonexistent.md:§2 対象が消えた行\n"
            f"- 2026-02-03 {real}:§3 生きている行B\n")
        hist3 = root / "sweep-record-3.md"
        sweep_residual(root, "2026-08-25", apply=True, record=hist3)
        rest = (root / RESIDUAL_IN).read_text()
        assert "生きている行A" in rest and "生きている行B" in rest, f"生きている行が消えた: {rest}"
        assert "nonexistent" not in rest, f"記録した行が消えていない: {rest}"
        assert "コメントの中" in rest, "コメントの中の行まで消した"

        # --- ローテーション(1行も落とさない。issues-pendings.md §2.1 (2)) ---
        head_note = "<!-- 書式: - <YYYY-MM-DD> <path:節> <一文> -->\n# 残務\n\n## 残務(文書整合ほか)\n\n"
        def put(n: int) -> None:
            (root / RESIDUAL_IN).write_text(
                head_note + "".join(f"- 2026-04-01 {real}:§{i} 穴{i}\n" for i in range(n)))
        put(RESIDUAL_ROTATE_AT - 1)
        total, dest = rotate_residual(root)
        assert (total, dest) == (RESIDUAL_ROTATE_AT - 1, None), f"49行でローテーションした: {dest}"
        put(RESIDUAL_ROTATE_AT)
        total, dest = rotate_residual(root)
        assert dest is not None and dest.name == "residual-001.md", f"押し出し先が誤り: {dest}"
        assert len(dest.read_text().splitlines()) == len(head_note.splitlines()) + total, \
            "押し出した側で行が落ちた"
        # 新しいほうは**見出しと注記を引き継ぎ**、残務は空である(書き手が見る形は変わらない)
        fresh = (root / RESIDUAL_IN).read_text()
        assert fresh.startswith("<!-- 書式:") and "## 残務(文書整合ほか)" in fresh, fresh
        assert collect_residual(root)[0] == [], "ローテーションした先の残務が空でない"
        # **まとめて書いて 50 を超えても、そのままローテーションする**(50 は厳密ではない)
        put(RESIDUAL_ROTATE_AT + 7)
        total, dest = rotate_residual(root)
        assert (total, dest.name) == (RESIDUAL_ROTATE_AT + 7, "residual-002.md"), (total, dest)
        assert collect_residual(root)[0] == [], "超過分が残った"
        # 押し出されたファイルは**読まない** — 現行ファイルだけが母集団である
        put(2)
        leftovers_now, _ = collect_residual(root)
        assert len(leftovers_now) == 2, f"押し出したファイルまで読んでいる: {len(leftovers_now)}"
        # **コメントの中の `## 残務` で頭を切らない** — 切ると `<!--` を閉じないまま
        # 新しいファイルへ入り、以後の残務行がコメントに沈む(独立検査 L-1)。
        (root / RESIDUAL_IN).write_text(
            "<!-- 書式の例:\n## 残務(文書整合ほか)\n-->\n# 残務\n\n## 残務(文書整合ほか)\n\n"
            + "".join(f"- 2026-04-01 {real}:§{i} 穴{i}\n" for i in range(RESIDUAL_ROTATE_AT)))
        _, dest = rotate_residual(root)
        fresh = (root / RESIDUAL_IN).read_text()
        assert fresh.count("<!--") == fresh.count("-->"), f"コメントが閉じていない: {fresh!r}"
        assert fresh.rstrip().endswith("なし"), fresh
        assert collect_residual(root)[0] == [], "コメント内の見出しで切って残務が残った"
        # **閉じていない `<!--` と、コメントの中の `<!--` で破れない** ★
        # (独立検査 M-1: 自前の数え上げが破れ、「押し出した」と表示しながら1行も片付かず、
        #  打つたびに押し出しの写しだけが増えていた。)
        for broken_head in ("<!-- 書式のメモ(閉じ忘れ)\n",
                            "<!-- 注記: コメントの中で <!-- を引用している -->\n"):
            (root / RESIDUAL_IN).write_text(
                broken_head + "# 残務\n\n## 残務(文書整合ほか)\n\n"
                + "".join(f"- 2026-04-01 {real}:§{i} 穴{i}\n" for i in range(RESIDUAL_ROTATE_AT)))
            before_n = len(collect_residual(root)[0])
            _, dest = rotate_residual(root)
            assert dest is not None, f"押し出さなかった: {broken_head!r}"
            assert collect_residual(root)[0] == [], \
                f"「押し出した」と言いながら片付いていない: {broken_head!r}"
            assert len(dest.read_text().splitlines()) >= before_n, "押し出した側で行が落ちた"
        (root / RESIDUAL_IN).write_text(before)
        for stale_file in root.glob("docs/residual-*.md"):
            stale_file.unlink()
        report = health(reverify, histories, errors, staleness)
        assert "再検証候補: 1" in report
        assert "鮮度確認の候補(棚上げ): 2(最古 2026-02-01)" in report
        assert "鮮度確認の候補(課題票): 1(最古 2026-01-20)" in report
        assert "残務: 2 行(最古 2026-01-15)" in (outputs[root / REVERIFY_OUT])
        for path, content in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True); path.write_text(content)
        outputs2, *_ = desired_outputs(root)
        assert all(path.read_text() == content for path, content in outputs2.items())

        # **main() の経路をそのまま通す。** 上の assert は health() を直接呼ぶので、
        # main 側の呼び出し側だけ引数が足りない、という壊れ方を捕まえられなかった(実測)。
        previous = Path.cwd()
        quiet = contextlib.redirect_stdout(io.StringIO())   # selftest の出力は最後の1行だけ
        try:
            os.chdir(root)
            with quiet:
                assert main(["doc-health.py"]) == 0
                assert main(["doc-health.py", "--check"]) == 0      # 直前に書いたので差分なし
                assert main(["doc-health.py", "--health"]) == 0
                (root / "docs/issues/008-bug-y.md").write_text(
                    "---\nid: 008-bug-y\ntype: bug\nfound: 2026-05-05\ncloses_when: y\n---\n# 008\n")
                assert main(["doc-health.py", "--check"]) == 1      # 増えた分が差分に出る
                # --- 採番の払い出し(2026-09-05。並走の衝突と再発行を塞ぐ) ---
                # fixture には 008-bug-y.md が在る → 次は 009。連続で呼べば単調に増える
                assert main(["doc-health.py", "--next-issue-id"]) == 0
                assert next_id(root, "issue") == "010", next_id(root, "issue")
                # 実物を消しても控え(ids.json)が再発行を防ぐ
                (root / "docs/issues/008-bug-y.md").unlink()
                assert next_id(root, "issue") == "011"
                # 棚上げ: fixture の P-004 と、履歴・02 に残る参照(ここでは無し)を見る → 次は 005
                got = next_id(root, "pending")
                assert got == "005", got
                # 履歴に P-020 の帰着行が残っていれば、それを跨ぐ
                (root / "docs/histories/2026-06-01-p.md").write_text(
                    "---\nid: p\n---\n帰着: P-020 を解消した\n")
                assert next_id(root, "pending") == "021"
                # オプションは単独でしか打てない
                assert main(["doc-health.py", "--next-issue-id", "--check"]) == 2
                # --- 控えの破損は黙って数え直さず、失敗する(2026-09-05 の独立確認) ---
                ids = root / IDS_STATE
                good = ids.read_text()
                for broken in ("{broken", '["list"]', '{"issue": "abc"}',
                               '{"issue": true}', '{"issue": false}',
                               '{"issue": -1}', '{"issue": 1000}'):
                    ids.write_text(broken)
                    try:
                        next_id(root, "issue")
                        raise AssertionError(f"壊れた控え {broken!r} で失敗しなかった")
                    except SystemExit as e:
                        assert "壊れている" in str(e), e
                ids.write_text(good)
                # --- 999 の天井: 控えを進める前に止まる ---
                ids.write_text('{"issue": 999, "pending": 4}')
                try:
                    next_id(root, "issue")
                    raise AssertionError("999 の次で失敗しなかった")
                except SystemExit as e:
                    assert "999" in str(e), e
                assert '"issue": 999' in ids.read_text(), "失敗したのに控えが進んだ"
                ids.write_text(good)
                # --- 押し出し中の追記の引き継ぎ(単体) ---
                snap = "# h\n\n## 残務\n\n- a\n- b\n"
                assert _carry_new_lines(snap, snap) == []
                assert _carry_new_lines(snap, snap + "- c\n") == ["- c"]
                assert _carry_new_lines("- a\n- b\n", "- a\n- x\n- b\n") == ["- x"]
                # --- 追記は錠の下の1経路に集約する(2026-09-12 の検査 A2-6) ---
                res = root / RESIDUAL_IN
                res.write_text("# 残務\n\n## 残務(文書整合ほか)\n\nなし\n")
                assert main(["doc-health.py",
                             "--append-residual=- 2026-09-12 docs/a.md:§1 表の穴"]) == 0
                got = res.read_text()
                assert "- 2026-09-12 docs/a.md:§1 表の穴" in got, got
                assert "なし" not in got, "空の印が残った"
                # 同じ鍵は何も書かない — 日付が違っても(鍵は path:節 と一文である)
                assert main(["doc-health.py",
                             "--append-residual=- 2026-09-20 docs/a.md:§1 表の穴。"]) == 0
                assert len(collect_residual(root)[0]) == 1, collect_residual(root)[0]
                # 形の違う行は受け取らない / 他のオプションと混ぜない
                try:
                    append_residual(root, "表の穴")
                    raise AssertionError("形の違う行を受け取った")
                except SystemExit as e:
                    assert "形が違う" in str(e), e
                assert main(["doc-health.py",
                             "--append-residual=- 2026-09-12 docs/b.md:§1 x",
                             "--check"]) == 2
                # --- 解消した行を落とす(削除も同じ錠を通る。2026-09-13 の検査 A2-6) ---
                res.write_text("# h\n\n## 残務\n\n- 2026-09-12 docs/a.md:§1 穴\n"
                               "- 2026-09-12 docs/b.md:§2 別の穴\n")
                hist = root / "docs/histories/resolve.md"
                what, left = resolve_residual(root, "2026-09-12 docs/a.md:§1 穴",
                                              "直した", hist)
                assert (what, left) == ("削除", 1), (what, left)
                assert "判定: 直した" in hist.read_text(encoding="utf-8")
                assert "docs/a.md" not in res.read_text(encoding="utf-8")
                assert "docs/b.md" in res.read_text(encoding="utf-8")
                assert resolve_residual(root, "2026-09-12 docs/zzz.md:§9 無い",
                                        "直した", hist)[0] == "不在"
                try:                              # 理由の無い削除は受け取らない
                    resolve_residual(root, "2026-09-12 docs/b.md:§2 別の穴", " ", hist)
                    raise AssertionError("理由の無い削除を受け取った")
                except SystemExit as e:
                    assert "--verdict" in str(e), e
                assert main(["doc-health.py",            # 記録先の無い削除は 2
                             "--resolve-residual=- 2026-09-12 docs/b.md:§2 別の穴",
                             "--verdict=直した"]) == 2
                res.write_text(before)
        finally:
            os.chdir(previous)
    print("OK doc-health: upstream-moved/history-reverse-index/critical-recovery/"
          "staleness-worklist/legacy/deterministic/leftover-sweep/rotate/next-id/"
          "residual-resolve")
    return 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv[1:]:
        return selftest()
    if any(arg in ("-h", "--help") for arg in argv[1:]):
        print(__doc__); return 0
    args = list(argv[1:])
    as_of = record = append = resolve = verdict = ""
    for arg in list(args):
        if arg.startswith("--as-of="):
            as_of = arg.split("=", 1)[1]; args.remove(arg)
        elif arg.startswith("--record="):
            record = arg.split("=", 1)[1]; args.remove(arg)
        elif arg.startswith("--append-residual="):
            append = arg.split("=", 1)[1]; args.remove(arg)
        elif arg.startswith("--resolve-residual="):
            resolve = arg.split("=", 1)[1]; args.remove(arg)
        elif arg.startswith("--verdict="):
            verdict = arg.split("=", 1)[1]; args.remove(arg)
    flags = set(args)
    if (flags - {"--check", "--health", "--sweep", "--rotate",
                  "--next-issue-id", "--next-pending-id"} or len(flags) != len(args)):
        print(__doc__); return 2
    for solo in ("--next-issue-id", "--next-pending-id"):
        if solo in flags and (flags != {solo} or as_of or record):
            print(f"エラー: {solo} は単独で打つ(他のオプションや --as-of / --record と混ぜない)。", file=sys.stderr)
            return 2
    if "--next-issue-id" in flags:
        print(next_id(Path.cwd(), "issue")); return 0
    if "--next-pending-id" in flags:
        print(next_id(Path.cwd(), "pending")); return 0
    if "--rotate" in flags and (flags != {"--rotate"} or as_of or record or append):
        # **他のオプションと混ぜられない。** 混ぜられると、先に見る --rotate が return したところで
        # --sweep や --check が黙って落ちる(引数の検証だけは通るので、呼び手からは
        # 「要求どおり打って 0 が返った」ようにしか見えない)。
        print("エラー: --rotate は単独で打つ(他のオプションや --as-of / --record / --append-residual と混ぜない)。"
              "ローテーションは掃除でも生成でもない別の操作である"
              "(issues-pendings.md §2.1)", file=sys.stderr)
        return 2
    if resolve and (flags or as_of or append):
        # 追記と同じ理由。**`--record=` だけは要る**(記録が先、削除が後)。
        print("エラー: --resolve-residual は --record= とだけ組む"
              "(他のオプションや --as-of / --append-residual と混ぜない)。"
              "落とした行の記録先が要る(issues-pendings.md §2.1)", file=sys.stderr)
        return 2
    if resolve:
        if not record:
            print("エラー: --resolve-residual には --record=<履歴ファイル> が要る"
                  "(記録が先、削除が後である)", file=sys.stderr)
            return 2
        what, left = resolve_residual(Path.cwd(), resolve, verdict, Path(record))
        print(f"{what}: 残り {left} 行")
        return 0 if what == "削除" else 1
    if verdict:
        print("エラー: --verdict は --resolve-residual と組んでだけ打つ", file=sys.stderr)
        return 2
    if append and (flags or as_of or record):
        # 上と同じ理由。追記も掃除でも生成でもローテーションでもない別の操作である。
        print("エラー: --append-residual は単独で打つ"
              "(他のオプションや --as-of / --record と混ぜない)。"
              "追記を済ませてから、必要なら --rotate を打つ"
              "(issues-pendings.md §2.1)", file=sys.stderr)
        return 2
    if as_of:
        from datetime import date
        try:                                     # 不正な日付を黙って「失効なし」にしない
            date.fromisoformat(as_of)
        except ValueError:
            print(f"エラー: --as-of の日付が不正: {as_of}(YYYY-MM-DD)", file=sys.stderr); return 2
    if "--sweep" in flags and not as_of:
        print("エラー: --sweep には --as-of=YYYY-MM-DD が要る"
              "(生成器は今日の日付を持たない。履歴に書く実行日は外から渡す)", file=sys.stderr)
        return 2
    if "--sweep" in flags and not record:
        print("エラー: --sweep には --record=<履歴ファイル> が要る。"
              "落とした行は**原本を書き換える前に**そこへ追記される — "
              "reverification.md は毎回生成し直されるので記録先にならない"
              "(issues-pendings.md §2.1)", file=sys.stderr)
        return 2
    root = find_root(Path.cwd())
    if (root / "docs").is_dir():
        # **入口が4つ(生成 / 掃き出し / 追記 / ローテーション)在るので、関所は手前に1つ置く。**
        # 入口ごとに違う扱いにすると、方針ではなく偶然になる(2026-08-25 の独立検査 L-1)。
        gap = residual_ledger_gap(root)
        if gap:
            print("エラー: " + gap, file=sys.stderr)
            return 2
    if append:
        # **追記も退避と同じ錠の下で行う** ★ — 錠を取らない追記は、複写から書戻しまでの
        # あいだに消える(2026-09-12 の検査 A2-6。issues-pendings.md §2.1 (1))。
        verdict, total = append_residual(root, append)
        if verdict == "重複":
            print(f"残務 {total} 行 / 同じ鍵が既に在るので何も書かなかった"
                  "(issues-pendings.md §2.1 (1))")
            return 0
        print(f"残務 {total} 行 / 追記: {append.strip()}")
        if total >= RESIDUAL_ROTATE_AT:
            print(f"→ {RESIDUAL_ROTATE_AT} 行以上。続けて `--rotate` を打つ"
                  "(issues-pendings.md §2.1 (2))")
        return 0
    if "--rotate" in flags:
        # **ローテーションは掃除でも生成でもない。** 1行も落とさないので --record も基準日も要らず、
        # 残務へ書いたフローが自分で打つ(issues-pendings.md §2.1 (2))。
        total, dest = rotate_residual(root)
        if dest is None:
            print(f"残務 {total} 行 / ローテーションなし({RESIDUAL_ROTATE_AT} 行未満)")
        else:
            print(f"残務 {total} 行 / {dest.relative_to(root)} へ押し出し、"
                  f"{RESIDUAL_IN} を作り直した")
            print("→ 生成物(docs/reverification.md)の残務の件数が古くなった。"
                  "作り直すのは `/verify-docs` である(issues-pendings.md §2.1)")
        return 0
    if as_of:
        # **掃除は生成物と無関係の経路である。** --as-of が付いたら候補(または削除結果)を
        # 出してそこで終える。生成物には触れない — 「候補を見るだけ」のつもりの実行が
        # reverification.md を書き換えるのは、コマンドの約束に反する。
        total, cands = sweep_residual(root, as_of, apply="--sweep" in flags,
                                      record=(root / record) if record else None)
        verb = "落とした" if "--sweep" in flags else "候補"
        print(f"残務 {total} 行 / 掃除の{verb}: {len(cands)} 行(実行日 {as_of})")
        for _, line, why in cands:
            print(f"  - {line.strip()}\n      理由: {why}")
        if cands and "--sweep" in flags:
            print(f"→ 落とした行は {record} に追記済み。**生成物を作り直すこと**: "
                  f"python3 .claude/scripts/doc-health.py")
        return 0
    outputs, reverify, histories, parse_errors, staleness = desired_outputs(root)
    if "--health" in flags:
        print(health(reverify, histories, parse_errors, staleness)); return 0
    changed: list[str] = []
    for path, content in outputs.items():
        old = path.read_text(encoding="utf-8") if path.is_file() else None
        if old == content:
            print(f"変更なし: {path.relative_to(root)}")
            continue
        changed.append(path.relative_to(root).as_posix())
        if "--check" not in flags:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            print(f"更新: {path.relative_to(root)}")
        else:
            print(f"差分あり: {path.relative_to(root)}")
    print(health(reverify, histories, parse_errors, staleness))
    if "--check" in flags and changed:
        print("→ 生成物が古い: " + ", ".join(changed)); return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
