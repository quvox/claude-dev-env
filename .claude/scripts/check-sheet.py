#!/usr/bin/env python3
"""決定シート(`docs/sheets/<slug>.md`)の機械の検査。**SSOT を書き始めてよいか。**

規範: .claude/directions/build-record.md §3 / 書式: .claude/templates/sheet.md
手順: .claude/skills/build/SKILL.md §1(このスクリプトを呼ぶ)

**fail-closed。** 「概念の明確化」が誰にも確認されないまま書き始めると、**曖昧な語のまま
03 まで降りる**(それが `KIT-concept-clarification-sheet` の症状だった)。

**ただし人間の記入コストは1行(または発言1つ)である。** 合格経路は3つ:
(1) シートの「一括回答」節に1行、(2) 全ブロックの個別記入、(3) **チャット回答の構築記録への
転記** — `docs/build-records/<slug>.md` の「決定シート(回答済み)」節に、人間の発言の
**逐語引用+日付**つき転記行が全空欄ブロック分(または「一括」の1行)あること。
経路 (3) の転記行は AI が書くが、**引用の捏造は証拠の偽造である** — 機械が検証できるのは
形式まで(人間の関与のディスク上の証拠は、逐語引用+日付が担う)。誰も確認していないシートは
3経路とも空なので、今までどおり落ちる。
一括承認(シート・チャットとも)のときは、**全ブロック**を SH5 / SH6 の対象にする
(承認が及ぶ範囲だから、雛形の例示が残っていてはならない)。規範は
`.claude/directions/delegation.md` §1 と `.claude/directions/build-record.md` §3。

**第4の経路は「そもそも問いが無い」である。** 「概念の明確化」が
`### <n>. 曖昧さなし — …` の**1件だけ**で、「論点」も「委任にしてよいか確認したい項目」も
0件のとき、そのシートは**開示であって問いではない**ので SH4 を免除する(記録して
シートを削除し、そのまま進んでよい)。**論点が1件でも在れば、シートは全体として
再び問いに戻る。** 免除しても SH5 / SH6 は当てる(雛形のまま出すことは許さない)。

**シートは表ではなくブロックである**(`KIT-decision-sheet-is-a-wide-table`)。
1論点 = `### <n>. <種別> —「<語>」` の見出し + `- **項目名**: 値` の並び + `**★あなたの記入**:`。
**この検査器は見出しと項目名だけを見る**ので、項目を1つ増やしても壊れない。

**SH10 は「問うてはならないことを問っていないか」の唯一の機械の検査である。** エラー処理・テスト・
ログ・設定(DS-01〜DS-04)の論点は、上流が沈黙していても問わず、要求と受け入れシナリオ・受け入れ基準から導いて決める
(`.claude/directions/delegation.md` §2.1)。抜け道は2つだけで、どちらも外部の実体を名指す:
`委任外の根拠`(DS-ID + 上流の ID)か、`発端` + 構築記録の `origin: human-report`。

**SH11 は「人間が読める形で問うているか」の唯一の機械の検査である。** シートを読むのは人間なので、
`AC-07` `原則5` のような**このキットの中でしか通じない記号を裸で出さない**(初出に丸括弧で中身を
書く。規範は `.claude/directions/delegation.md` §1.1 の規則1)。

**SH12 は「キット内部の言い回しを人間に向けて使っていないか」を見る。** `delegation.md` §1.1 の
規則2 は「関門2」「原則5」「問う基準」「標準委任」のような**この規範を読んだ AI にしか通じない語**を (LA3-ok)
禁じているが、SH11 は記号しか見ないのでこれらは素通りしていた。
**禁じる語の正は `.claude/directions/glossary.md`** であり、このスクリプトは列挙を持たない
(持つと正が2つになる — 原則10)。規範用語集の「人」欄に ★ が付いた語と、
「使ってはならない表記」欄の語が対象である。**規範用語集が無い環境では SH12 だけを「未検査」と報告する。**
**規範が許す逃げ道は2つある** — 「普通の言葉に開く」と「その場で1行定義する」。
SH12 は後者も合格にする(`語(説明)` と `説明(語)` の両方の書き方)。
**これを見ない実装は、規範どおりに書いたシートを落とし、通る道を「その語を消す」だけにしていた。**

**実装している検査IDの正はこのファイルの CHECKS だけである。**
一覧は `--list` で出る。**規範側に「SH1〜SHn」のような範囲を書かないこと**
(`KIT-check-id-list-owned-by-tool`)。

SH6 の照合相手は `.claude/templates/sheet.md` の例示ブロックである。**正は雛形1箇所のまま**にし、
スクリプトは値を持たない(原則10)。雛形が無い環境では SH6 だけを「未検査」と報告する。

**シートが無く、構築記録も名指していない**場合は「問いの無いタスク」とみなし、
**未検査**として報告して終了コード0で通す(合格ではない)。

使い方:
    python3 .claude/scripts/check-sheet.py <slug>
    python3 .claude/scripts/check-sheet.py docs/sheets/<slug>.md
    python3 .claude/scripts/check-sheet.py --list      # 実装している検査IDの一覧
    python3 .claude/scripts/check-sheet.py --selftest  # 壊した事例で検知できることを示す

終了コード: 0=合格(または未検査) 1=不合格 2=使い方・前提エラー
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

SECTION = "概念の明確化"
BULK_SECTION = "一括回答"
ANSWER_LABEL = "★あなたの記入"
PLACEHOLDER = re.compile(r"<[^<>]{0,40}>")
CODE_SPAN = re.compile(r"`[^`\n]*`")
TEMPLATE = ".claude/templates/sheet.md"
GLOSSARY = ".claude/directions/glossary.md"

ITEM_RE = re.compile(r"^###\s+(.+?)\s*$")
FIELD_RE = re.compile(r"^\s*[-*]\s+\*\*(.+?)\*\*\s*[:：]\s*(.*)$")
ANSWER_RE = re.compile(r"^\s*\*\*" + re.escape(ANSWER_LABEL) + r"\*\*\s*[:：]?\s*(.*)$")

# **実装している検査IDの唯一の正。** `--list` もレポートの見出しもここから作る。
CHECKS: dict[str, str] = {
    "SH1": "構築記録がシートを名指しているのに実体が無い(消された)",
    "SH2": f"「{SECTION}」の節、またはその論点ブロックが無い",
    "SH3": "論点が0件(曖昧さが無い場合も1件書く)",
    "SH4": f"「{BULK_SECTION}」も個別の「{ANSWER_LABEL}」も空で、構築記録にチャット回答の"
           "転記(逐語引用+日付)も無い(誰も確認していない)。"
           "**「曖昧さなし」1件のみ・論点0件・委任0件のシートは免除**(開示であって問いではない)",
    "SH5": "雛形の差し込み記号(`<…>`)が残ったまま記入されている",
    "SH6": "差し込み記号を消しただけで、骨が雛形の例示ブロックのままのものがある",
    "SH10": "エラー処理・テスト・ログ・設定(DS-01〜DS-04)の論点が、根拠なしに載っている"
            "(上流が沈黙しているなら導いて決める — delegation.md §2.1)",
    "SH11": "人間が読む欄に、中身の説明が無い内部識別子が出ている"
            "(`AC-07` ではなく `AC-07(注文が確定したときに確認メールを送ること)` — "
            "delegation.md §1.1)",
    "SH12": "人間が読む欄に、キット内部でしか通じない言い回しが出ている"
            "(禁じる語の正は directions/glossary.md — delegation.md §1.1 の規則2)",
}

# SH4 第3経路: 構築記録「決定シート(回答済み)」のチャット転記行。
# 「チャット回答」の語 + 日付(YYYY-MM-DD)+ 逐語引用(「…」)がそろって1件と数える。
CHAT_ROW = re.compile(r"チャット回答.*?(\d{4}-\d{2}-\d{2}).*?「(.+?)」")

# SH6: 何項目一致したら「骨が同じ」とみなすか。雛形の1ブロックは6項目ある。
GHOST_HIT = 3

# ---- SH10: 標準委任の4領域(エラー処理・テスト・ログ・設定 = DS-01〜DS-04)
#
# **実測(2026-08-11、2プロジェクト): シートの論点はこの4領域で埋まり、細かすぎて人間が裁定できず、
# 毎回「推奨どおり」で返ってきた。** 往復は買うものが無く、AI は「問うのは無料」と学ぶ。
# 規範は既に「実現方法は問わない」と書いていたが、判断ベースの禁止は破られる —
# **数えられる検査にしないと守られない**(このキットが繰り返し実測してきた型)。
#
# 見るのは**論点の主題だけ**(見出しと「明確にしたいこと」「選択肢」)。根拠や戻し方の本文まで
# 見ると「テストで気づく」のような無関係な語で誤検知し、全ブロックに定型文を書かせることになる。
TOPIC_SECTION = "論点"
DELEGATION_SECTION = "委任にしてよいか確認したい項目"
DISCLOSURE_KIND = "曖昧さなし"      # 概念の明確化の「問いが無い」ときの固定の種別語
SUBJECT_FIELDS = ("明確にしたいこと", "選択肢")
DELEGATED_AREA = re.compile(
    r"エラー|例外|失敗|リトライ|再試行|タイムアウト|ログ|ロギング|監視|可観測|"
    r"テスト|モック|スタブ|フィクスチャ|設定値|コンフィグ|既定値|デフォルト値|環境変数")
GROUNDS_FIELD = "委任外の根拠"      # DS-nn の対象外に当たる、という主張(上流の ID つき)
ORIGIN_FIELD = "発端"               # 人間が動かして問題提起した、という主張
DS_REF = re.compile(r"DS-\d\d")
UPSTREAM_REF = re.compile(r"(AC|FR|CTR|D0|D1|P)-[0-9A-Za-z._-]+|docs/[\w./-]+\.md|要確認")
HUMAN_REPORT = "human-report"


# ---- SH11: 人間が読む欄の、説明の無い内部識別子(規範は delegation.md §1.1)
#
# **シートは人間が読むものである。** `AC-07` `FR-env-03` `DS-02` `P-003` は、このキットと
# このプロジェクトの中でしか通じない記号なので、裸で出すと**答える側が調べる羽目になる** —
# 調べないなら、判断は勘になる(2026-08-18 の人間の指摘)。
#
# **見るのは「丸括弧の説明が続いているか」だけである。** 説明が理解できるものかは機械には
# 見えないので、そこは規範の側に置く。**数えられるところだけを検査にする** —
# 判断ベースの禁止は破られる、というのがこのキットが繰り返し実測してきた型である。
#
# 見ないものが3つある。どれも「人間に向けた主張ではない」ためで、誤検知を出す側に倒すと
# 全ブロックに定型文を書かせる結果になる(SH10 の主題欄と同じ判断):
#   - **行内コード(`…`)の中** — コマンド例と path。`--upstream MODULE-a` は引数であって主張ではない
#   - **差し込み記号(`<…>`)の中** — 雛形の例示
#   - **「★あなたの記入」** — 人間が自分のために書いたものを AI が採点することはない
#     (fields に入らないので、そもそも走査対象外)
#
# **初出だけを見る。** 同じ識別子を1ブロックで何度も書くたびに説明を繰り返させると、
# 読みにくくなって規範の目的に反する。
# **`原則n` もここに入れる。** delegation.md §1.1 は規則2 の例として「原則5」を名指しており、
# 丸括弧で1行定義するのは規則2 が認める開き方そのものである(`原則4(上流に無いものは作らない)`)。
# `原則として` のような日常語には当たらない — 数字を必須にしてあるため。
INTERNAL_ID = re.compile(
    r"(?<![0-9A-Za-z_-])(?:AC|FR|NFR|CTR|DS|D0|D1|UC|TS|PLAN|MODULE|P)-[0-9A-Za-z][0-9A-Za-z._-]*"
    r"|原則\d+")
# `^` を付けないこと。**`match(text, pos)` は pos に錨を打つが `^` は文字列の先頭にしか当たらない**
# ので、付けると並びを一度も飛ばせなくなる(2026-08-18、自己検査 (v) が実際に落ちた)。
ID_CHAIN_SEP = re.compile(r"\s*[、,/／・]\s*")
GLOSS_OPEN = ("(", "（")


def glossed(text: str, pos: int) -> bool:
    """識別子の直後に丸括弧の説明が続いているか。

    **識別子が並んでいるときは、並びの後ろに1つで足りる** — `AC-02・AC-04(いずれも…)` は
    合格である。1つずつ括弧を強いると、かえって読めない行になる。
    """
    while True:
        sep = ID_CHAIN_SEP.match(text, pos)
        if not sep:
            break
        nxt = INTERNAL_ID.match(text, sep.end())
        if not nxt:
            break
        pos = nxt.end()
    return text[pos:].lstrip().startswith(GLOSS_OPEN)


def check_unglossed(items: list[tuple[str, dict]]) -> list[tuple[str, str]]:
    """SH11。ブロック内で初出の内部識別子に、丸括弧の説明が続いていなければ落とす。"""
    bad: list[str] = []
    for name, it in items:
        seen: set[str] = set()
        miss: list[str] = []
        for value in it["fields"].values():
            body = PLACEHOLDER.sub("", CODE_SPAN.sub("", value))
            for m in INTERNAL_ID.finditer(body):
                if m.group(0) in seen:
                    continue
                seen.add(m.group(0))
                if not glossed(body, m.end()):
                    miss.append(m.group(0))
        if miss:
            bad.append(f"{name}: {', '.join(miss)}")
    if not bad:
        return []
    return [("SH11", "該当 " + " / ".join(bad) + "。"
                     "**このシートを読むのは人間である** — 記号の初出に丸括弧で中身を書くこと"
                     "(`AC-07(注文が確定したときに確認メールを送ること)`)。"
                     "並んでいるときは並びの後ろに1つでよい。"
                     "規範は .claude/directions/delegation.md §1.1")]


# ---- SH12: 人間が読む欄の、キット内部の言い回し(規範は delegation.md §1.1 の規則2)
#
# **禁じる語の列挙をここに書かない。** 正は `.claude/directions/glossary.md` の表であり、
# このスクリプトはそれを読むだけである(原則10 — 正を2つにすると必ずずれる)。
#
# 規範用語集の表は6欄で、1列目=日本語 / 5列目=使ってはならない表記 / 6列目=人。
# 対象になるのは **6列目に ★ が付いた行の1列目** と、**5列目の語**である。
# `/` で区切ると複数語になる。**丸括弧を含む項目は使わない** — 「影響範囲(単独で書かない)」の
# ような条件つきの禁止は機械には判定できないので、括弧が「対象外」の印になっている
# (この約束は規範用語集 §1 に書いてある)。
# **雛形の指示文は人間への問いではない。** SH11 が使う PLACEHOLDER は 40 文字までで入れ子も
# 見ないので、`<回答の写し先を名指す — docs/…/<slug>.md …>` のような長い指示文が残る。
# SH12 は行ごとに「最初の `<` から最後の `>` まで」を落とす(雛形の指示文は1行1つの形で書く)。
# **行内コードを先に落としてから当てる** — `<details>` のような要素名はコード span の中に在る。
INSTRUCTION = re.compile(r"<.*>")
GLOSSARY_ROW_CELLS = 6
GLOSSARY_HUMAN_BAN = "★"
GLOSSARY_NONE = "—"
TERM_SEP = re.compile(r"\s*/\s*")
HAS_PAREN = re.compile(r"[(（]")


def jargon_terms(glossary_text: str) -> list[str]:
    """規範用語集から「人間に向けて書いてはならない語」を集める。長い順に返す。

    長い順にするのは、`条件1` と `条件` のように片方が他方を含むとき、
    **報告に出る語を具体的な側にする**ため。
    **同じ長さの語は文字列の順で並べる** ★ — 集合をそのまま `key=len` で並べると、
    同長の語の順が**プロセスごとに変わる**(文字列の hash が実行ごとに変わるため)。
    SH12 の判定は語の順を見るので、固定しないと**同じ入力で合否が揺れる**。
    """
    terms: set[str] = set()

    def add(cell: str) -> None:
        for raw in TERM_SEP.split(cell):
            term = raw.strip().strip("`*").strip()
            if not term or term == GLOSSARY_NONE or HAS_PAREN.search(term):
                continue
            terms.add(term)

    for line in glossary_text.replace("\r", "").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != GLOSSARY_ROW_CELLS or not cells[0] or cells[0] == "日本語":
            continue
        if set(cells[0]) <= set("-: "):          # 区切り行
            continue
        add(cells[4])
        if GLOSSARY_HUMAN_BAN in cells[5]:
            add(cells[0])
    return sorted(terms, key=lambda s: (-len(s), s))


PAREN_PAIRS = {"(": ")", "（": "）"}


def in_place_definition(body: str, term: str, terms: list[str]) -> tuple[int, int] | None:
    """その語の**初出**が「その場で1行定義する」形なら、その語の範囲を返す(でなければ None)。

    規範(`delegation.md` §1.1 の規則2)が許す逃げ道は2つ — 普通の言葉に開くか、
    **その場で1行定義する**。後者の書き方は2つあり、どちらも合格にする:

      (a) `語(説明)` — SH11 の `glossed()` と同じ形。
      (b) `説明(語)` — 先に普通の言葉で書き、括弧でキットの語を添える形。
          **括弧の前に普通の言葉が在ること**を要求する(裸の `(語)` は開いたことにならない)。
          **その普通の言葉が別のキット語で終わっていたら定義と見ない** —
          `標準委任(問う基準)` は、どちらの語も人間には開かれていない。

    **開き括弧と閉じ括弧は種類を対応させる** — `(` は `)` で、`（` は `）` で閉じたときだけ
    定義と見る。混ぜた `語(説明）` を通すと、括弧の壊れた行が定義を名乗れる。
    **初出だけを見る**(SH11 と同じ理由 — 同じ語に何度も定義を強いると、かえって読めなくなる)。
    **定義は同じ行の中で閉じていること**を要求する(規範の言い方が「その場で1行定義する」である)。
    形の検査なので**中身の無い定義も通る** — SH11 が既に抱えている限界と同じで、そこを見るのは人間。
    **SH11 と違い、語の並び(`語A・語B(いずれも…)`)は定義と見ない** — SH11 が見る識別子と違って、
    キット語の並びに1つの説明を当てても、どの語がどれを指すかが人間に伝わらないからである。
    返すのは**語そのものの範囲**である(呼ぶ側が、定義できた長い語の中に在るだけの短い語を
    落とすのに使う)。**説明の側は見逃さない** — そこに別のキット語が在れば、
    その語は自分の初出として別に判定される。
    """
    pos = body.find(term)
    if pos < 0:
        return None
    end = pos + len(term)
    line_end = body.find("\n", end)
    if line_end < 0:
        line_end = len(body)
    tail = body[end:line_end]
    # **強調の記号は跨ぐ** — 決定シートの欄はどれも `**…**` で書かれるので、
    # `**語**(説明)` がいちばん出やすい形である(SH11 の `glossed()` は跨がない)。
    lead = len(tail) - len(tail.lstrip(" \t*"))
    opener = tail[lead:lead + 1]
    if opener in PAREN_PAIRS:                                  # (a) 語(説明)
        return (pos, end) if PAREN_PAIRS[opener] in tail[lead + 1:] else None
    line_start = body.rfind("\n", 0, pos) + 1
    lead_text = body[line_start:pos]
    open_at = max(lead_text.rfind(c) for c in PAREN_PAIRS)     # (b) 説明(語)
    if open_at < 0:
        return None
    opener = lead_text[open_at]
    if PAREN_PAIRS[opener] in lead_text[open_at:]:
        return None                                            # その括弧は語の前で閉じている
    head = lead_text[:open_at].strip().rstrip("*").strip()
    if PAREN_PAIRS[opener] not in tail or not head:
        return None                                            # 同じ行で閉じない / 括弧の前が空
    if any(head.endswith(other) for other in terms):
        return None                                            # 括弧の前も禁じられた語である
    return (pos, end)


def check_jargon(items: list[tuple[str, dict]], terms: list[str]) -> list[tuple[str, str]]:
    """SH12。人間が読む欄にキット内部の言い回しが出ていたら落とす。

    見ないものは SH11 と同じ(行内コード・差し込み記号・「★あなたの記入」)。
    **見出しは見る** — 題にキット語を置くのがいちばん目に付く形だからである。
    **その場で1行定義してある語は落とさない**(`in_place_definition`。規範が許す2つ目の逃げ道)。
    """
    bad: list[str] = []
    for name, it in items:
        hits: list[str] = []
        decided: set[str] = set()          # 初出で判定済みの語(項目ごと)
        bodies = [it["title"], *it["fields"].values()]
        for value in bodies:
            body = "\n".join(INSTRUCTION.sub("", ln)
                             for ln in CODE_SPAN.sub("", value).splitlines())
            # **語ごとに、元の本文に対して独立に判定する** ★ — 判定の途中で本文を書き換えると、
            # 同じ長さの語のどちらを先に見たかで結果が変わる。
            defined: list[tuple[int, int]] = []
            found: list[tuple[str, int]] = []
            for term in terms:             # 長い順・同長は文字列順(jargon_terms が保証)
                if term in decided:
                    continue
                pos = body.find(term)
                if pos < 0:
                    continue
                decided.add(term)
                span = in_place_definition(body, term, terms)
                if span is None:
                    found.append((term, pos))
                else:
                    defined.append(span)
            for term, pos in found:
                # `条件1(説明)` の中の `条件` は、裸の使用として数えない —
                # **定義できた長い語の中に在るだけ**だからである。
                if any(s <= pos and pos + len(term) <= e for s, e in defined):
                    continue
                hits.append(term)
        if hits:
            bad.append(f"{name}: {', '.join(hits)}")
    if not bad:
        return []
    return [("SH12", "該当 " + " / ".join(bad) + "。"
                     "**この語はこの規範を読んだ AI にしか通じない** — "
                     "普通の言葉に開くか、**その場で1行定義する**こと"
                     "(`語(その場の説明)` でも `その場の説明(語)` でもよい。"
                     "括弧は種類を合わせ、同じ行の中で閉じること)。"
                     "禁じる語の正は .claude/directions/glossary.md、"
                     "規範は .claude/directions/delegation.md §1.1 の規則2")]


def memo_origin(memo_text: str) -> str:
    """構築記録 frontmatter の `origin:`。無ければ derived(正は delegation.md §5)。"""
    if memo_text.startswith("---"):
        parts = memo_text.split("---", 2)
        if len(parts) > 2:
            m = re.search(r"^origin:\s*(\S+)\s*$", parts[1], re.M)
            if m:
                return m.group(1).strip('`"\'')
    return "derived"


def filled(value: str) -> bool:
    """人間/AI が実際に書いたか(雛形の差し込み記号だけの行は「書いていない」)。"""
    return bool(PLACEHOLDER.sub("", value).strip())


def check_delegated(items: list[tuple[str, dict]], origin: str) -> list[tuple[str, str]]:
    """SH10。4領域に触れる論点は、抜け道2つのどちらかを示していなければ落とす。

    抜け道は**書いた事実**で判定する(内容の妥当性は機械には見えない) — が、どちらも
    上流の ID か人間の問題提起という**外部の実体**を名指す形なので、書けば監査できる。
    """
    bad: list[str] = []
    for label, it in items:
        subject = label + " " + " ".join(it["fields"].get(k, "") for k in SUBJECT_FIELDS)
        if not DELEGATED_AREA.search(subject):
            continue
        g = it["fields"].get(GROUNDS_FIELD, "")
        if filled(g) and DS_REF.search(g) and UPSTREAM_REF.search(g):
            continue
        o = it["fields"].get(ORIGIN_FIELD, "")
        if filled(o) and origin == HUMAN_REPORT:
            continue
        why = []
        if filled(g):
            why.append(f"「{GROUNDS_FIELD}」に DS-nn と上流の ID(AC-… / FR-… / CTR-… / パス)が要る")
        if filled(o) and origin != HUMAN_REPORT:
            why.append(f"「{ORIGIN_FIELD}」はあるが構築記録が origin: {origin}"
                       f"(人間が動かして問題提起したタスクだけ {HUMAN_REPORT})")
        bad.append(label + (f"({' / '.join(why)})" if why else ""))
    if not bad:
        return []
    return [("SH10", f"該当 {len(bad)} 件: {', '.join(bad)}。"
                     "この4領域は上流が沈黙していても問わない — 要求と受け入れシナリオ・受け入れ基準から導いて決め、"
                     "外から見えるものは 01 の受け入れ基準に [DS-nn] つきで書き足す"
                     "(.claude/directions/delegation.md §2.1)。"
                     f"どうしても問うなら `- **{GROUNDS_FIELD}**: DS-nn 対象外① — 根拠: AC-nn` か、"
                     f"`- **{ORIGIN_FIELD}**: <issue / 逐語引用>` + 構築記録の `origin: {HUMAN_REPORT}`。"
                     "既に答えをもらっているなら、それを decisions へ落としてこの論点は外すこと")]


def norm(s: str) -> str:
    """`<…>` を落とし空白を畳んだ値。人間が実際の語を書けば必ず変わる。"""
    return re.sub(r"\s+", "", PLACEHOLDER.sub("", s))


def same_skeleton(a: dict, b: dict) -> bool:
    """項目名ごとに値の骨を比べ、GHOST_HIT 個以上一致したら「雛形のまま」とみなす。"""
    hits = 0
    for k, v in b["fields"].items():
        nb = norm(v)
        if nb and norm(a["fields"].get(k, "")) == nb:
            hits += 1
    return hits >= GHOST_HIT


def find_root(start: Path) -> Path:
    cur = start.resolve()
    for cand in [cur, *cur.parents]:
        if (cand / "CLAUDE.md").is_file() and (cand / ".claude").is_dir():
            return cand
    return cur


def items_of_section(text: str, section: str = SECTION) -> tuple[bool, list[dict]]:
    """(節が在ったか, 論点ブロックの一覧)。

    ブロック = `### 見出し` + `- **項目名**: 値`(継続行は前の項目に足す)+ `**★あなたの記入**:`。
    記入は欄の行と、それ以降・次の見出しまでの本文を合わせたもの。
    """
    inside = found = False
    items: list[dict] = []
    cur: dict | None = None
    last: str | None = None

    for line in text.replace("\r", "").splitlines():
        if line.startswith("## "):
            inside = section in line          # 別の `##` が来たら節はそこで終わる
            found = found or inside
            cur, last = None, None
            continue
        if not inside:
            continue

        m = ITEM_RE.match(line)
        if m:
            cur = {"title": m.group(1), "fields": {}, "answer": [], "has_slot": False}
            items.append(cur)
            last = None
            continue
        if cur is None:
            continue

        a = ANSWER_RE.match(line)
        if a:
            cur["has_slot"] = True
            if a.group(1).strip():
                cur["answer"].append(a.group(1).strip())
            last = None
            continue
        if cur["has_slot"]:
            if line.strip() and not line.lstrip().startswith("<!--"):
                cur["answer"].append(line.strip())
            continue

        f = FIELD_RE.match(line)
        if f:
            last = f.group(1).strip()
            cur["fields"][last] = f.group(2).strip()
        elif last and line.strip() and not line.lstrip().startswith("<!--"):
            cur["fields"][last] += " " + line.strip()   # 継続行

    return found, items


def bulk_answer(text: str) -> tuple[bool, str]:
    """(「一括回答」節が在ったか, 記入された内容)。

    節に `###` ブロックは無いので `items_of_section` では拾えない。**欄が無いこと**と
    **欄が空であること**を区別できるように、節の有無も返す(古いシートには節が無い)。
    """
    inside = found = slot = False
    parts: list[str] = []
    for line in text.replace("\r", "").splitlines():
        if line.startswith("## "):
            if inside:
                break
            inside = BULK_SECTION in line
            found = found or inside
            continue
        if not inside or line.lstrip().startswith("<!--"):
            continue
        m = ANSWER_RE.match(line)
        if m:
            slot = True
            if m.group(1).strip():
                parts.append(m.group(1).strip())
            continue
        if slot and line.strip():
            parts.append(line.strip())
    return found, " ".join(parts).strip()


def chat_transcript(memo_text: str) -> tuple[int, bool]:
    """構築記録「決定シート(回答済み)」のチャット転記行。(件数, 一括か)。

    行の条件は CHAT_ROW(語・日付・逐語引用の3点セット)。どれか欠けた行は数えない —
    引用と日付が「人間がそう言った」のディスク上の証拠だから(build-record.md §3)。
    「一括」を含む行は全ブロックに及ぶ(シートの「一括回答」と同じ意味論)。
    """
    inside = False
    n, bulk = 0, False
    for line in memo_text.replace("\r", "").splitlines():
        if line.startswith("## "):
            inside = ("決定シート" in line) and ("回答済み" in line)
            continue
        if not inside or line.lstrip().startswith("<!--"):
            continue
        m = CHAT_ROW.search(line)
        if m and m.group(2).strip():
            n += 1
            if "一括" in line:
                bulk = True
    return n, bulk


# 決定シートを何周したか。**上限ではなく兆候の可視化である**(K-9)。中断したタスクは
# 決定シートを 13 回まで回した(実測 2026-08-07)。1 タスクの想定は「着手時に 1 回 +
# 出口で最大 1 回」なので、4 周目から警告する。**判定は落とさない**(警告のみ)。
SHEET_ROUND_WARN = 3


def sheet_rounds(memo_text: str) -> int:
    """「決定シート(回答済み)」の転記行に現れる**日付の種類数** = 人間に問うた回数。

    同じ日にまとめて答えた分は 1 周と数える(1 往復だから)。日付を持たない行は
    数えない —— `chat_transcript` と同じ理由で、日付が「いつ問うたか」の唯一の証拠である。
    """
    inside, dates = False, set()
    for line in memo_text.replace("\r", "").splitlines():
        if line.startswith("## "):
            inside = ("決定シート" in line) and ("回答済み" in line)
            continue
        if not inside or line.lstrip().startswith("<!--"):
            continue
        dates.update(re.findall(r'(20\d\d-\d\d-\d\d)', line))
    return len(dates)


def disclosure_only(text: str, items: list[dict]) -> bool:
    """人間の回答を要さないシートか(SH4 の第4経路。docstring 冒頭)。

    「概念の明確化」が `曖昧さなし` 1件だけで、「論点」も「委任にしてよいか確認したい項目」も
    0件のとき、そのシートは開示であって問いではない。**論点が1件でも在れば False**。
    """
    if len(items) != 1 or DISCLOSURE_KIND not in items[0]["title"]:
        return False
    return not items_of_section(text, TOPIC_SECTION)[1] \
        and not items_of_section(text, DELEGATION_SECTION)[1]


def evaluate(text: str, template_text: str | None,
             memo_text: str = "",
             glossary_text: str | None = None) -> tuple[list[tuple[str, str]], list[str], int]:
    """(不合格, 未検査の注記, 論点の件数)。ファイル入出力を持たないので単体で試せる。

    `memo_text` は構築記録の本文。SH4 の第3経路(チャット回答の転記行)の材料。
    空文字列なら第3経路は単に不成立(旧来の2経路だけで判定)。
    `glossary_text` は `.claude/directions/glossary.md` の本文。None なら SH12 は未検査。
    """
    failures: list[tuple[str, str]] = []
    notes: list[str] = []
    found, items = items_of_section(text)

    if not found:
        failures.append(("SH2", f"「## {SECTION}」の節が無い"))
        return failures, notes, 0
    if not items:
        failures.append(("SH3", "`### ` で始まる論点ブロックが1つも無い"))
        return failures, notes, 0

    def label(i: int, it: dict) -> str:
        return f"{i}「{it['title']}」"

    # **一括回答が埋まっていれば1行で承認とみなす。** 空欄のブロックは AI推奨の採用である
    # (雛形が「未回答時の既定: AI推奨のとおりにする」と約束している)。
    bulk_found, bulk = bulk_answer(text)
    if not bulk_found:
        notes.append(f"「## {BULK_SECTION}」の節が無い(このキットの一括回答より前のシート)。"
                     "全ブロックに個別の記入が要る")

    blank = [label(i, it) for i, it in enumerate(items, 1) if not it["answer"]]

    # 第3経路: チャット回答の構築記録への転記(逐語引用+日付)。「一括」1行は全ブロックに及び、
    # 個別転記なら空欄ブロックの数だけ要る(どのブロック分かの照合は転記規範側 — 機械は数まで)。
    chat_n, chat_bulk = chat_transcript(memo_text)
    chat_ok = chat_bulk or bool(chat_n and blank and chat_n >= len(blank))

    # 第4経路: 問いが1件も無いシートは開示である(免除しても SH5 / SH6 は当てる)。
    disclosure = disclosure_only(text, items)
    if disclosure:
        notes.append(f"SH4  免除  「{DISCLOSURE_KIND}」1件のみ・論点0件・委任0件 = "
                     "開示であって問いではない(delegation.md §1)。人間の回答は要らない")

    if blank and not bulk and not chat_ok and not disclosure:
        missing = [it for it in items if not it["has_slot"]]
        why = f"(うち {len(missing)} 件は「{ANSWER_LABEL}」の欄自体が無い)" if missing else ""
        hint = (f"。チャット転記は {chat_n} 件で空欄 {len(blank)} 件に足りない" if chat_n else "")
        failures.append(("SH4", f"「{BULK_SECTION}」が空で、かつ空の論点がある: "
                                f"{', '.join(blank)}{why}{hint}。"
                                f"「{BULK_SECTION}」に `すべて推奨どおり` と書けば全件承認になる"
                                "(チャットでの回答でも可 — 逐語引用+日付つきで構築記録に転記)"))
    elif bulk:
        notes.append(f"{BULK_SECTION}: 「{bulk}」— 空欄のブロックは AI推奨の採用として扱う")
    elif blank and chat_ok:
        notes.append(f"チャット回答の転記 {chat_n} 件(構築記録 決定シート(回答済み)"
                     f"{'、一括' if chat_bulk else ''})を合格証拠として扱う")

    # 一括承認(シート・チャットとも)は全ブロックに及ぶので、
    # **答えの有無にかかわらず**雛形の残りを見る。
    covered = [(i, it) for i, it in enumerate(items, 1)
               if it["answer"] or bulk or chat_ok or disclosure]

    # **行内コード(`…`)の中は差し込み記号として数えない。**HTML/XML の要素名やジェネリクスを
    # 論点として扱えなくなるため(実測 2026-08-10: `<details>` / `<summary>` の開閉を論点にした
    # シートが、記入済みなのに SH5 で落ちた)。雛形の差し込みはコード span に入っていない。
    ghost = [label(i, it) for i, it in covered
             if any(PLACEHOLDER.search(CODE_SPAN.sub("", v)) for v in it["fields"].values())]
    if ghost:
        failures.append(("SH5", f"該当: {', '.join(ghost)}"
                                "(雛形の例示ブロックにそのまま答えている。"
                                "実際の論点で書き直すこと)"))

    # SH10: 4領域の論点。**概念の明確化と論点の両方**を見る(どちらの節にも現れる)。
    origin = memo_origin(memo_text)
    concepts = [(label(i, it), it) for i, it in enumerate(items, 1)]
    topics = [(f"論点{i}「{it['title']}」", it)
              for i, it in enumerate(items_of_section(text, TOPIC_SECTION)[1], 1)]
    failures += check_delegated(concepts + topics, origin)

    # SH11: 説明の無い内部識別子。**人間が読む節はすべて**見る(委任の節も人間が答える)。
    delegations = [(f"委任{i}「{it['title']}」", it)
                   for i, it in enumerate(items_of_section(text, DELEGATION_SECTION)[1], 1)]
    human_read = concepts + topics + delegations
    failures += check_unglossed(human_read)

    # SH12: キット内部の言い回し。禁じる語の正は規範用語集であって、このスクリプトではない。
    if glossary_text is None:
        notes.append(f"SH12 未検査  規範用語集が無い({GLOSSARY})。**未検査は合格ではない** — "
                     "キット内部の言い回しが人間に渡っていても見つけられない")
    else:
        failures += check_jargon(human_read, jargon_terms(glossary_text))

    if template_text is None:
        notes.append(f"SH6  未検査  雛形が無い({TEMPLATE})。**未検査は合格ではない** — "
                     "例示ブロックをそのまま埋めたものを見つけられない")
    else:
        _, examples = items_of_section(template_text)
        copied = [label(i, it) for i, it in covered
                  if label(i, it) not in ghost
                  and any(same_skeleton(it, ex) for ex in examples)]
        if copied:
            failures.append(("SH6", f"該当: {', '.join(copied)}"
                                    f"(骨が {TEMPLATE} の例示ブロックと同じ。"
                                    "実際の論点で書き直すこと)"))

    return failures, notes, len(items)


def main(argv: list[str]) -> int:
    if any(a in ("-h", "--help") for a in argv[1:]):
        print(__doc__)   # 明示要求は 0。使い方エラーの 2 と区別する(tools-readme §2)
        return 0
    args = argv[1:]
    if args and args[0] == "--list":
        for cid, desc in CHECKS.items():
            print(f"{cid}  {desc}")
        return 0
    if args and args[0] == "--selftest":
        return selftest()
    if len(args) != 1 or args[0].startswith("-"):
        print(__doc__)
        return 2

    root = find_root(Path.cwd())
    arg = args[0]
    if arg.endswith(".md"):
        sheet = (root / arg) if not Path(arg).is_absolute() else Path(arg)
    else:
        sheet = root / "docs" / "sheets" / f"{arg}.md"

    print(f"## 決定シートの検査: {sheet.relative_to(root) if sheet.is_relative_to(root) else sheet}")

    # 転記の証拠は構築記録(同じ slug)。質問シートに記録は無い(memo_text 空で判定)
    record = root / "docs" / "build-records" / f"{sheet.stem}.md"
    memo_text = record.read_text(encoding="utf-8") if record.is_file() else ""

    if not sheet.is_file():
        if f"sheets/{sheet.name}" in memo_text:
            print(f"  NG  SH1  {CHECKS['SH1']}"
                  "。シートを復元するか、転記済みなら構築記録の名指しを「転記済み」に直すこと")
            return 1
        # fail-closed(inspection-14): シートが無い状態を合格にできるのは、構築記録に
        # 「問いなし」の宣言か転記の証拠(逐語引用+日付の行)があるときだけ。
        n, _bulk = chat_transcript(memo_text)
        if "問いなし" in memo_text or "転記済み" in memo_text or n:
            print("  OK  シートは転記済みか問いなし(構築記録に証拠あり)")
            return 0
        if not memo_text:
            print("エラー: シートも構築記録も無い(検査対象が無い)", file=sys.stderr)
            return 2
        print("  NG  SH1  シートが無く、構築記録に「問いなし」の宣言も転記の証拠も無い"
              "(未回答のままシートだけ消された疑い — fail-closed)")
        return 1

    template = root / TEMPLATE
    glossary = root / GLOSSARY
    failures, notes, n = evaluate(
        sheet.read_text(encoding="utf-8"),
        template.read_text(encoding="utf-8") if template.is_file() else None,
        memo_text,
        glossary.read_text(encoding="utf-8") if glossary.is_file() else None,
    )

    if failures:
        for cid, detail in failures:
            print(f"  NG  {cid}  {CHECKS[cid]} — {detail}")
        for note in notes:
            print(f"  --  {note}")
        print(f"\n→ SSOT を書き始めてはならない。人間に返すこと"
              f"(「## {BULK_SECTION}」に1行書けば全件承認になる — チャットでの回答でもよく、"
              "その場合は発言を逐語引用+日付つきで構築記録に転記する、と添えること)。"
              f"**「{ANSWER_LABEL}」を AI が埋めてはならず、転記の引用を捏造してはならない**"
              "(.claude/directions/build-record.md §3)。")
        return 1

    for note in notes:
        print(f"  --  {note}")
    rounds = sheet_rounds(memo_text)
    if rounds > SHEET_ROUND_WARN:
        print(f"  警告  決定シートを {rounds} 回まわしている(目安 {SHEET_ROUND_WARN} 回)。"
              "問いが尽きないのはタスクが大きすぎる兆候である —— **02-design の分割定義を"
              "見直すこと**(`.claude/directions/core.md` §4)。判定は落とさない")
    print(f"  OK  論点 {n} 件が確認済み(雛形の例示ブロックの残りなし)")
    return 0


# ---------------------------------------------------------------- 自己検査


def selftest() -> int:
    """壊した事例で各検査が実際に落ちることを示す(`/kit-improve` §6-3)。

    **雛形は実物を読む。** 検査の相手は `.claude/templates/sheet.md` なので、
    雛形を書き換えたのに検査が追随していない、を自己検査で捕まえられるようにする。
    """
    root = find_root(Path(__file__).resolve().parent)
    tpl_path = root / TEMPLATE
    if not tpl_path.is_file():
        print(f"エラー: 雛形が無い: {tpl_path}")
        return 2
    tpl = tpl_path.read_text(encoding="utf-8")
    # **規範用語集も実物を読む。** 禁じる語を書き換えたのに検査が追随していない、を捕まえる。
    # 同時に「実物の規範用語集が実物の雛形を誤検知しない」ことも (d) が示すことになる。
    gls_path = root / GLOSSARY
    if not gls_path.is_file():
        print(f"エラー: 規範用語集が無い: {gls_path}")
        return 2
    gls = gls_path.read_text(encoding="utf-8")

    def answered(sheet: str, *answers: str) -> str:
        """`**★あなたの記入**:` を順に埋める。"""
        out, i = [], 0
        for line in sheet.splitlines():
            m = ANSWER_RE.match(line)
            if m and i < len(answers):
                out.append(f"**{ANSWER_LABEL}**: {answers[i]}")
                i += 1
            else:
                out.append(line)
        return "\n".join(out)

    def real(sheet: str) -> str:
        """例示の骨を実際の論点で置き換える(雛形のままではない状態を作る)。

        **置き換え先は SH11 を満たす書き方にする**(識別子の初出に丸括弧の説明)。
        雛形を書き換えたのにここが追随していなければ、置換が空振りして (d) が落ちる —
        それがこの自己検査に雛形の実物を読ませている理由である。
        """
        return (sheet
                .replace("### 1. 語の外延 —「<語>」", "### 1. 語の外延 —「実行中のセッション」")
                .replace("- **場所**: `<path>:<line>` / "
                         "AC-02(<その受け入れシナリオが求めていることを一言で>)・AC-04(<同>)",
                         "- **場所**: `docs/00-requests/request.md:12` / "
                         "AC-02(起動中のコンテナ数を課金の対象として数えること)")
                .replace("- **明確にしたいこと**: 何を1件と数えるか。含む例2件と含まない例1件",
                         "- **明確にしたいこと**: 停止中のコンテナを数に入れるか")
                .replace("- **AI推奨**: 含む = <例>・<例> / 含まない = <例>。理由: <>。崩れる条件: <>",
                         "- **AI推奨**: 含む = 起動中。含まない = 削除済み。理由: 課金対象。崩れる条件: 再開機能")
                .replace("- **波及**: この数え方に依存する動作が <n> 箇所"
                         "(<どの機能の話かを普通の言葉で>)",
                         "- **波及**: この数え方に依存する動作が 2 箇所(課金の集計と、一覧の件数表示)")
                .replace("### 2. 範囲の境界 —「<箇所>」", "### 2. 範囲の境界 —「ダッシュボード」")
                .replace("- **場所**: `<path>:<line>`", "- **場所**: `docs/02-design/system.md:88`")
                .replace("- **明確にしたいこと**: 今回やるのはどれか。やらないものを名指し",
                         "- **明確にしたいこと**: 今回は一覧だけか、詳細も含むか")
                .replace("- **AI推奨**: 今回は <A: 何をするか> だけにする。"
                         "<B: 何をするか> は「やらないこと」へ回す。\n  理由: <>。崩れる条件: <>",
                         "- **AI推奨**: 今回は一覧の表示だけにする。詳細画面は「やらないこと」へ回す。"
                         "理由: 粒度。崩れる条件: 詳細が要件に入るとき")
                .replace("- **未回答時の既定**: AI推奨のとおりにする(<B> は「やらないこと」へ回す)",
                         "- **未回答時の既定**: AI推奨のとおりにする(詳細画面は「やらないこと」へ回す)")
                .replace("- **波及**: <この選択で変わる動作を、数と普通の言葉で>",
                         "- **波及**: 画面の表示項目が 1 箇所(ダッシュボードの一覧)")
                .replace("- **間違えたときの戻し方**: <いつ気づくか / 何を直せば戻るか>",
                         "- **間違えたときの戻し方**: 集計値の初回レビューで気づく。数え方を1箇所直せば戻る"))

    results: list[tuple[str, bool, str]] = []

    def check(name: str, cond: bool, note: str = "") -> None:
        results.append((name, cond, note))

    def ids(text: str) -> set[str]:
        f, _, _ = evaluate(text, tpl, "", gls)
        return {cid for cid, _ in f}

    # **最初の記入欄は「一括回答」である。** 以降の引数が論点ブロックに対応する。
    NO_BULK = ""

    # (a) 雛形そのまま(誰も記入していない)→ SH4
    check("(a) 未記入は SH4 で落ちる", "SH4" in ids(tpl), str(ids(tpl)))

    # (b) 雛形の例示に記入だけした → SH5(差し込み記号が残っている)
    filled_tpl = answered(tpl, NO_BULK, "既定", "既定")
    check("(b) 例示のまま答えたら SH5", "SH5" in ids(filled_tpl), str(ids(filled_tpl)))

    # (c) 差し込み記号を消しただけ(骨は雛形のまま)→ SH6
    ghostly = answered(PLACEHOLDER.sub("", tpl), NO_BULK, "既定", "既定")
    check("(c) 骨が雛形のままなら SH6", "SH6" in ids(ghostly), str(ids(ghostly)))

    # (d) 実際の論点で書き直し、記入済み → 合格
    ok = answered(real(tpl), NO_BULK, "既定", "一覧のみでよい")
    check("(d) 実際の論点なら合格", not ids(ok), str(ids(ok)))

    # (p) **一括回答1行だけで合格になる**(この改善の中心。人間の記入コストは1行)
    bulk_only = answered(real(tpl), "すべて推奨どおり")
    check("(p) 一括回答だけで合格", not ids(bulk_only), str(ids(bulk_only)))
    check("(p) 一括回答を読み取れている", bulk_answer(bulk_only) == (True, "すべて推奨どおり"),
          str(bulk_answer(bulk_only)))

    # (q) 一括承認は全ブロックに及ぶので、雛形の残りは答えの有無にかかわらず落とす
    bulk_ghost = answered(tpl, "すべて推奨どおり")
    check("(q) 一括承認でも雛形のままなら SH5", "SH5" in ids(bulk_ghost), str(ids(bulk_ghost)))

    # (r) 一括回答の節が無い古いシートは、今までどおり全ブロック記入が要る
    legacy = real(tpl).replace(f"## {BULK_SECTION}", "## 旧・記入方法")
    check("(r) 節が無ければ従来どおり SH4", "SH4" in ids(answered(legacy, NO_BULK, "", "")),
          str(ids(answered(legacy, NO_BULK, "", ""))))
    check("(r) 節が無いことを未検査として注記する",
          any(BULK_SECTION in n
              for n in evaluate(answered(legacy, NO_BULK, "既定", "既定"), tpl, "", gls)[1]),
          str(evaluate(answered(legacy, NO_BULK, "既定", "既定"), tpl, "", gls)[1]))

    # (s) チャット転記(SH4 の第3経路)。一括の1行で合格になり、件数不足・形式不備は落ちる
    def ids_m(text: str, memo: str) -> set[str]:
        f, _, _ = evaluate(text, tpl, memo, gls)
        return {cid for cid, _ in f}

    unanswered = real(tpl)
    chat_bulk_memo = ("## 決定シート(回答済み)\n"
                      "- チャット回答(2026-08-08)「すべて推奨どおり」 — 一括\n")
    check("(s) チャット一括転記で合格", not ids_m(unanswered, chat_bulk_memo),
          str(ids_m(unanswered, chat_bulk_memo)))
    per_block = ("## 決定シート(回答済み)\n"
                 "- チャット回答(2026-08-08)「1は含む扱いで」 — 論点 1\n")
    check("(s) 個別転記が足りなければ SH4", "SH4" in ids_m(unanswered, per_block),
          str(ids_m(unanswered, per_block)))
    per_all = per_block + "- チャット回答(2026-08-08)「2は一覧のみ」 — 論点 2\n"
    check("(s) 全ブロック分の個別転記で合格", not ids_m(unanswered, per_all),
          str(ids_m(unanswered, per_all)))
    no_date = "## 決定シート(回答済み)\n- チャット回答「すべて推奨どおり」 — 一括\n"
    check("(s) 日付の無い転記行は数えない", "SH4" in ids_m(unanswered, no_date),
          str(ids_m(unanswered, no_date)))
    other_section = chat_bulk_memo.replace("決定シート(回答済み)", "調査メモ")
    check("(s) 節の外の転記行は数えない", "SH4" in ids_m(unanswered, other_section),
          str(ids_m(unanswered, other_section)))
    check("(s) チャット一括でも雛形のままなら SH5", "SH5" in ids_m(tpl, chat_bulk_memo),
          str(ids_m(tpl, chat_bulk_memo)))

    # (u) **問いが1件も無いシートは、回答なしで合格する**(SH4 の第4経路。人間の往復を1回減らす)
    def disclosure_sheet(sheet: str) -> str:
        """概念「曖昧さなし」1件だけ・論点0件・委任0件のシートを組み立てる。"""
        out, drop = [], False
        for line in sheet.splitlines():
            if line.startswith("## "):
                drop = False
            elif line.startswith("### "):
                drop = not line.startswith("### 1. ")
            if not drop:
                out.append(line)
        return ("\n".join(out)
                .replace("### 1. 語の外延 —「実行中のセッション」",
                         f"### 1. {DISCLOSURE_KIND} —「00/01 の語を1つも増やさない」"))

    disc = disclosure_sheet(real(tpl))
    check("(u) 曖昧さなし1件のみなら回答なしで合格", not ids(disc), str(ids(disc)))
    check("(u) 免除したことを注記する",
          any("免除" in n for n in evaluate(disc, tpl)[1]), str(evaluate(disc, tpl)[1]))
    with_topic = disc.replace(
        f"## {TOPIC_SECTION}(概念以外。従来の決定シート)",
        f"## {TOPIC_SECTION}(概念以外。従来の決定シート)\n\n### 論点 1. 取り直しの周期\n\n"
        "- **選択肢**: 1分 / 5分\n- **AI推奨**: 1分。理由: 既存の画面と揃う。"
        "下流の代償: 無し。崩れる条件: 負荷\n\n**★あなたの記入**:\n")
    check("(u) 論点が1件でも在れば SH4 に戻る", "SH4" in ids(with_topic), str(ids(with_topic)))
    check("(u) 免除は「曖昧さなし」の語で判定している",
          not disclosure_only(disc.replace(DISCLOSURE_KIND, "語の外延"),
                              items_of_section(disc.replace(DISCLOSURE_KIND, "語の外延"))[1]))

    # (e) 記入欄そのものを消した → SH4(欄が無いことを名指しする)
    noslot = "\n".join(l for l in real(tpl).splitlines() if not ANSWER_RE.match(l))
    f_noslot, _, _ = evaluate(noslot, tpl)
    check("(e) 記入欄が無ければ SH4", "SH4" in {c for c, _ in f_noslot})
    check("(e) 欄が無いことを名指しする",
          any("欄自体が無い" in d for c, d in f_noslot if c == "SH4"),
          str(f_noslot))

    # (f) 節ごと消した → SH2
    nosec = real(tpl).replace(f"## {SECTION}", "## 別の節")
    check("(f) 節が無ければ SH2", "SH2" in ids(nosec), str(ids(nosec)))

    # (g) 節はあるがブロックが0件 → SH3
    empty = f"# sheet\n\n## {SECTION}(空)\n\n本文だけ。\n\n## 次に問う候補\n"
    check("(g) 論点が0件なら SH3", "SH3" in ids(empty), str(ids(empty)))

    # (h) 雛形が無い環境では SH6 を「未検査」と報告する(黙って合格にしない)
    f_no_tpl, notes, _ = evaluate(ok, None, "", gls)
    check("(h) 雛形が無ければ SH6 は未検査", any("SH6" in n and "未検査" in n for n in notes), str(notes))
    check("(h) それでも他の検査は動く", not f_no_tpl, str(f_no_tpl))

    # (i) 次の `##` 節の内容を論点として数えない(「次に問う候補」を巻き込まない)
    _, items = items_of_section(ok)
    check("(i) 節の外を数えない", len(items) == 2, f"{len(items)} 件: {[i['title'] for i in items]}")

    # (j) 項目を1つ増やしても壊れない(検査は項目名を決め打ちしない)
    波及 = "- **波及**: この数え方に依存する動作が 2 箇所(課金の集計と、一覧の件数表示)"
    extended = ok.replace(波及, 波及 + "\n- **新しい項目**: 増やしても落ちない")
    check("(j) 項目を足しても合格のまま", not ids(extended), str(ids(extended)))

    # (v) SH11: 人間が読む欄の、説明の無い内部識別子(delegation.md §1.1)
    GLOSSED = "AC-02(起動中のコンテナ数を課金の対象として数えること)"
    bare = ok.replace(GLOSSED, "AC-02")
    check("(v) 説明の無い識別子は SH11", "SH11" in ids(bare), str(ids(bare)))
    check("(v) 説明があれば通る", "SH11" not in ids(ok), str(ids(ok)))
    chained = ok.replace(GLOSSED, "AC-02・AC-04(いずれも課金対象の数え方を決めている)")
    check("(v) 並びは後ろに1つでよい", "SH11" not in ids(chained), str(ids(chained)))
    twice = ok.replace("- **明確にしたいこと**: 停止中のコンテナを数に入れるか",
                       "- **明確にしたいこと**: AC-02 の数え方に停止中を入れるか")
    check("(v) 初出に説明があれば2回目は要らない", "SH11" not in ids(twice), str(ids(twice)))
    in_code = ok.replace("- **明確にしたいこと**: 停止中のコンテナを数に入れるか",
                         "- **明確にしたいこと**: `relations-query.py --upstream MODULE-a` を見る")
    check("(v) 行内コードの中は見ない", "SH11" not in ids(in_code), str(ids(in_code)))
    answer_only = answered(real(tpl), NO_BULK, "AC-02 のままでよい", "一覧のみでよい")
    check("(v) ★あなたの記入は見ない", "SH11" not in ids(answer_only), str(ids(answer_only)))
    topic_bare = with_topic.replace("- **選択肢**: 1分 / 5分",
                                    "- **選択肢**: 1分 / 5分(FR-env-03 に合わせる)")
    check("(v) 論点の節も見る", "SH11" in ids(topic_bare), str(ids(topic_bare)))

    # (w) SH12: キット内部の言い回し(delegation.md §1.1 の規則2)。禁じる語の正は規範用語集。
    TERMS = jargon_terms(gls)
    check("(w) 規範用語集から語を集められている",
          {"問う基準", "標準委任", "関門2", "窓", "朝のシート"} <= set(TERMS),  # LA3-ok
          f"{len(TERMS)} 語: {TERMS[:12]}")
    check("(w) 括弧つきの項目は対象外(条件つきの禁止は機械に判定できない)",
          not any("(" in x or "（" in x for x in TERMS), str([x for x in TERMS if "(" in x]))
    jargon = ok.replace("- **明確にしたいこと**: 停止中のコンテナを数に入れるか",
                        "- **明確にしたいこと**: これは問う基準を満たすか")
    check("(w) 内部の言い回しは SH12", "SH12" in ids(jargon), str(ids(jargon)))
    check("(w) 実物の雛形は実物の規範用語集で誤検知しない", "SH12" not in ids(ok), str(ids(ok)))
    banned = ok.replace("### 2. 範囲の境界 —「ダッシュボード」",
                        "### 2. 範囲の境界 —「関門2」")  # LA3-ok
    check("(w) 見出しも見る", "SH12" in ids(banned), str(ids(banned)))
    in_code_j = ok.replace("- **明確にしたいこと**: 停止中のコンテナを数に入れるか",
                           "- **明確にしたいこと**: `問う基準` の実装を見るか")
    check("(w) 行内コードの中は見ない", "SH12" not in ids(in_code_j), str(ids(in_code_j)))
    f_no_gls, notes_g, _ = evaluate(jargon, tpl, "", None)
    check("(w) 規範用語集が無ければ SH12 は未検査",
          any("SH12" in n and "未検査" in n for n in notes_g), str(notes_g))
    check("(w) 未検査のときは SH12 を出さない",
          "SH12" not in {c for c, _ in f_no_gls}, str(f_no_gls))

    # (w2) SH12: 規範が許すもう1つの逃げ道「その場で1行定義する」を落とさない(B-10)
    def jargon_line(text: str) -> str:
        return ok.replace("- **明確にしたいこと**: 停止中のコンテナを数に入れるか", text)

    check("(w2) 語の並びは決定的(同じ長さは文字列の順)",
          TERMS == sorted(TERMS, key=lambda s: (-len(s), s)), str(TERMS[:12]))
    gloss_after = jargon_line("- **明確にしたいこと**: これは問う基準"
                              "(人間に問うてよいかを決める2つの条件)を満たすか")
    check("(w2) 語(説明)の形は通る", "SH12" not in ids(gloss_after), str(ids(gloss_after)))
    gloss_before = jargon_line("- **明確にしたいこと**: これは人間に問うてよいかを決める2つの条件"
                               "(問う基準)を満たすか")
    check("(w2) 説明(語)の形も通る", "SH12" not in ids(gloss_before), str(ids(gloss_before)))
    bare_paren = jargon_line("- **明確にしたいこと**: (問う基準)を満たすか")
    check("(w2) 括弧の前に普通の言葉が無ければ通さない",
          "SH12" in ids(bare_paren), str(ids(bare_paren)))
    unclosed = jargon_line("- **明確にしたいこと**: これは問う基準(人間に問うてよいかを決める条件\n"
                           "  をここでは説明しない")
    check("(w2) 同じ行で閉じない括弧は定義として数えない",
          "SH12" in ids(unclosed), str(ids(unclosed)))
    first_bare = jargon_line("- **明確にしたいこと**: 問う基準を満たすか\n"
                             "- **なぜ**: 問う基準(人間に問うてよいかを決める2つの条件)が効くため")
    check("(w2) 初出が裸なら、あとで定義しても落とす",
          "SH12" in ids(first_bare), str(ids(first_bare)))
    mixed_a = jargon_line("- **明確にしたいこと**: これは問う基準"
                          "(人間に問うてよいかを決める2つの条件）を満たすか")
    check("(w2) 括弧の種類が食い違えば定義として数えない(語(説明）)",
          "SH12" in ids(mixed_a), str(ids(mixed_a)))
    mixed_b = jargon_line("- **明確にしたいこと**: これは人間に問うてよいかを決める2つの条件"
                          "（問う基準)を満たすか")
    check("(w2) 括弧の種類が食い違えば定義として数えない(説明（語))",
          "SH12" in ids(mixed_b), str(ids(mixed_b)))
    jargon_gloss = jargon_line("- **明確にしたいこと**: これは標準委任(問う基準)を満たすか")
    check("(w2) 括弧の前も禁止語なら、括弧の中の語を落とす",
          "SH12" in ids(jargon_gloss), str(ids(jargon_gloss)))
    bold_after = jargon_line("- **明確にしたいこと**: これは**問う基準**"
                             "(人間に問うてよいかを決める2つの条件)を満たすか")
    check("(w2) 太字の記号を挟んだ 語(説明) も通る",
          "SH12" not in ids(bold_after), str(ids(bold_after)))
    bold_before = jargon_line("- **明確にしたいこと**: これは**標準委任**(問う基準)を満たすか")
    check("(w2) 太字でも、括弧の前が禁止語なら中の語を落とす",
          "SH12" in ids(bold_before), str(ids(bold_before)))
    contained = jargon_line("- **明確にしたいこと**: これは関門2"  # LA3-ok
                            "(出荷してよいかを見る2つ目の判定)を満たすか")
    check("(w2) 定義できた長い語の中に在るだけの短い語は数えない",
          "SH12" not in ids(contained), str(ids(contained)))

    # (x) SH11 は `原則n` も見る(§1.1 の規則2 が名指しした形。丸括弧の定義で通る)
    prin = ok.replace("- **明確にしたいこと**: 停止中のコンテナを数に入れるか",
                      "- **明確にしたいこと**: 原則4 に照らしてどちらか")
    check("(x) 裸の 原則n は SH11", "SH11" in ids(prin), str(ids(prin)))
    prin_ok = ok.replace("- **明確にしたいこと**: 停止中のコンテナを数に入れるか",
                         "- **明確にしたいこと**: 原則4(上流に無いものは作らない)に照らしてどちらか")
    check("(x) 括弧で定義すれば通る", "SH11" not in ids(prin_ok), str(ids(prin_ok)))
    check("(x) 「原則として」には当たらない",
          "SH11" not in ids(ok.replace("- **明確にしたいこと**: 停止中のコンテナを数に入れるか",
                                       "- **明確にしたいこと**: 原則として含めるかどうか")),
          "日常語に誤検知した")

    # (k) 実ファイル経由でも同じ判定になる(evaluate だけでなく main の経路)
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "docs" / "sheets"
        t.mkdir(parents=True)
        (t / "task-x.md").write_text(tpl, encoding="utf-8")
        (Path(td) / "CLAUDE.md").write_text("# x\n", encoding="utf-8")
        (Path(td) / ".claude").mkdir()
        import subprocess
        r = subprocess.run([sys.executable, str(Path(__file__).resolve()),
                            "task-x"], cwd=td, capture_output=True, text=True)
        # ---- (t) SH10: 4領域(エラー処理・テスト・ログ・設定)の論点は根拠なしに問えない。
    #      **抜け道が本当に抜けられること**まで見る(抜けられない検査は、書き換えられて終わる)。
    def topic(title: str, extra: str = "") -> str:
        """「論点」節に1ブロックだけ持つ最小のシート(概念節は合格状態にしておく)。"""
        base = answered(real(tpl), "すべて推奨どおり")
        return base + (
            f"\n\n## 論点(追記)\n\n### 論点 9. {title}\n"
            "- **選択肢**: A / B\n"
            f"{extra}"
            "- **根拠(上流)**: `docs/01-requirements/functional.md §2`\n"
            "\n**★あなたの記入**:\n")

    def ids_o(text: str, memo: str) -> set[str]:
        f, _, _ = evaluate(text, tpl, memo)
        return {cid for cid, _ in f}

    DERIVED = "---\nid: task-x\norigin: derived\n---\n"
    REPORTED = "---\nid: task-x\norigin: human-report\n---\n"

    check("(t) エラー処理の論点は根拠なしなら SH10",
          "SH10" in ids_o(topic("リトライ回数をいくつにするか"), DERIVED),
          str(ids_o(topic("リトライ回数をいくつにするか"), DERIVED)))
    check("(t) テスト・ログ・設定も同じ検査",
          all("SH10" in ids_o(topic(t), DERIVED) for t in
              ("テストをどこまで自動化するか", "ログの水準をどうするか", "既定値をいくつにするか")))
    check("(t) 4領域に触れない論点は SH10 を出さない",
          "SH10" not in ids_o(topic("公開APIの命名を変えるか"), DERIVED),
          str(ids_o(topic("公開APIの命名を変えるか"), DERIVED)))
    check("(t) 委任外の根拠(DS-ID + 上流の ID)があれば通る",
          "SH10" not in ids_o(topic("失敗時に利用者へ何を見せるか",
                                    "- **委任外の根拠**: DS-02 対象外① — 根拠: AC-07 が別の表示を要求\n"),
                              DERIVED))
    check("(t) DS-ID だけ / 上流の ID だけでは通らない",
          "SH10" in ids_o(topic("失敗時の通知をどうするか",
                                "- **委任外の根拠**: DS-02 の対象外だと思う\n"), DERIVED)
          and "SH10" in ids_o(topic("失敗時の通知をどうするか",
                                    "- **委任外の根拠**: AC-07 に関係する\n"), DERIVED))
    check("(t) 人間の問題提起由来なら 発端 で通る",
          "SH10" not in ids_o(topic("エラー文言をどう変えるか",
                                    "- **発端**: docs/issues/012-modify-error-wording.md\n"),
                              REPORTED))
    check("(t) 発端があっても origin: derived なら通らない",
          "SH10" in ids_o(topic("エラー文言をどう変えるか",
                                "- **発端**: docs/issues/012-modify-error-wording.md\n"),
                          DERIVED))
    check("(t) origin: human-report でも 発端 の記載が無ければ通らない",
          "SH10" in ids_o(topic("エラー文言をどう変えるか"), REPORTED))
    check("(t) 差し込み記号のままの抜け道は「書いていない」と見る",
          "SH10" in ids_o(topic("リトライ回数をいくつにするか",
                                "- **委任外の根拠**: <DS-nn 対象外 — 根拠: AC-nn>\n"), DERIVED))
    check("(t) origin 未記入は derived と同じ扱い",
          "SH10" in ids_o(topic("タイムアウト値をいくつにするか"), "---\nid: task-x\n---\n"))
    check("(t) 概念の明確化の節でも同じ検査が働く",
          "SH10" in ids_o(answered(real(tpl).replace(
              "### 1. 語の外延 —「実行中のセッション」",
              "### 1. 失敗時に観測される振る舞い —「タイムアウト」"), "すべて推奨どおり"), DERIVED))

    check("(k) 未記入のシートを非0で拒む", r.returncode == 1, r.stdout + r.stderr)

    for name, okc, _ in results:
        print(f"  {'PASS' if okc else 'FAIL'}  {name}")
    ng = [(n, note) for n, c, note in results if not c]
    if ng:
        print(f"\n{len(ng)} 件 FAIL", file=sys.stderr)
        for n, note in ng:
            print(f"--- {n}\n{note}", file=sys.stderr)
        return 1
    print(f"\n全 {len(results)} 項目 PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
