#!/usr/bin/env python3
"""仕様ドキュメントの一括検査(SSOT 全体の機械検査)。

SSOT 全体に、文書の構造に依存しない検査(CS 群)を当てる。数秒で終わるので
**1編集ごとに回せる**。呼び出し元は `/build` §1(母集団の凍結)と `/verify-docs` §1
(検査のたび)。**どの CS が何を見るかの正はこのファイルの names 表と各関数の docstring**
(--list で出る)。

旧 check-changeset.py の `--ssot` モードの後継である。変更指示(new-features/)の検査モードは
変更指示の全廃(ワークフロー再設計 2026-08-19)とともに retired — SSOT は /build が直接書き、
その整合はタスク内整合確認と verify 系フローの二重の網が見る。

使い方:
  python3 .claude/scripts/check-ssot.py [docs]
  python3 .claude/scripts/check-ssot.py --list        # 実装している検査の一覧
  python3 .claude/scripts/check-ssot.py --selftest    # 壊した事例で CS21 が落ちることを示す
  終了コード: 0 = 違反なし / 1 = 違反あり / 2 = 使い方・対象エラー

fail-closed: 存在しないパス・対象0件は「違反なし」ではなくエラー(終了コード2)。
「検査して問題なし」と「検査していない」を同じ表示にしない。
"""
import sys, re, json, pathlib, collections


def lst(v):
    return [] if not v or v.strip() == 'なし' else [x.strip() for x in v.split(',') if x.strip()]


# ------------------------------------------------------------------ 両モード共通の検査
#
# 旧2モード時代の共有部。いまは SSOT 一括だけが走る。

# **変更相対語**: 「いつ読んでも同じ意味」でない語。SSOT は今の姿だけを書くので、
# 「本変更」「次のタスクで」は書かれた瞬間から意味が固定されず、読む時点で嘘になる。
# **これは違反として数えない。候補として列挙するだけである** — 正当な用法が3種類あり、
# どれも機械では見分けられない: (a) コードが実際に出力する文面の逐語引用
# (直すとコード ⇄ 03-impl が壊れる = 原則2)、(b) 日付で固定された決定の改訂記録
# (「2026-08-04 に改めた」)、(c) 却下した案の記録(「(旧実装)」)。
# 語彙は実測で足りなかった分を含む(当初は「本変更」「〜へ改める」しか拾えず、
# その後の実行が「本タスク」「次のタスクで」「現行も」「旧実装」を追加で見つけた。計17箇所)。
CHANGE_RELATIVE = ("本変更", "本タスク", "従来は", "現行も", "旧実装", "次のタスク", "へ改める")

VAGUE = ("適切に", "正しく", "高速に", "柔軟に",
         "ほぼ", "長めに", "短めに", "短く", "十分に", "なるべく", "適度に", "通常")

# **「通常」だけは同じ文字列が2つの役目を持つ。**
#   (a) 程度の緩衝 —— 「通常は 3 回まで再試行する」「通常、失敗しない」。これは曖昧語である。
#   (b) 対比のための区分名 —— FIDO2 に対する「通常パスワード」、rollback に対する
#       「通常のエクスポート」、強制削除に対する「通常の削除」、「デプロイ(通常)」。
#       **書き換えると意味が落ちる**(何と対比しているのかが消える)。
# 固定文字列で拾うと (b) まで違反になる。実測: SSOT の 12 件が**全件 (b) かコードコメントの
# 逐語引用**で、1 件も書き換えられなかった(2026-08-11)。そこで **(a) の形だけを違反とする**。
# 「通常」の直後が助詞「は」・読点・句点・「であ」・行末のときだけ緩衝と見なす。
# 「の」「で」「に」「)」や名詞が続く形は区分名なので拾わない。
VAGUE_CONTEXT = {
    "通常": re.compile(r'通常(?=\s*(?:は|、|,|。|であ|$))'),
}
OPEN_POINT = ("実装の判断", "後で決める", "未定(")

# 本文中の参照。**拡張子を要求しない。** 実測では `docs/issues/054` の形(ID だけ、`.md` 無し)が
# 157箇所あり、`\.md` を要求する正規表現はその同型を1件も拾えなかった
# — それが `claude-dev-env` の `docs/issues/054` そのものである。
# **ASCII 限定にすると、日本語ファイル名の文書を数え落とす。** ファイル名に許される文字は
# OS が決めるので列挙しきれない。`\w` は Python3 では Unicode 対応なので、書記系を問わず
# 文字・数字・下線に当たる(Unicode 対応の書き方)。**散文中の `docs/…` の
# ような例示は `…` が `\w` でないため当たらない** —— 区切りを列挙する書き方だと誤検出になる。
# ここは CS11(参照実在)。ASCII 限定だと**日本語名への壊れたリンクを黙って通す**。
REF = re.compile(r'(?<![\w/])(docs/[\w.*/-]+)')
# 採番規則 `NNN-<slug>.md` を持つ記録先(`.claude/directions/issues-pendings.md` §1・§4)。
# **`docs/histories/` は日付命名なので含めない**(`\d{3}` に当たらず、含めても解決できない)。
NUMBERED_ID = re.compile(r'^(docs/issues|docs/feedbacks)/(\d{3})(?:-|$)')
# **Markdown のフェンスは2種類ある**(``` と ~~~)。片方しか見ないと、`~~~` で囲った
# 例示が本物の内容として読まれ、**参照実在(CS11)も件数の主張(CS21)も偽の違反を出す**
# — 検査が嘘をつく側の欠陥である。(印の種類ごとの対応づけまでするのは `cs25` だけである。
#  ここを使う4か所は開閉を交互に数えるので、種類を混ぜた入れ子では早く閉じうる —
#  それでも「見えたまま」より安全な倒れ方である。)
FENCE = re.compile(r'^\s*(```|~~~)')


def ref_exists(ref: str, repo) -> bool:
    """参照先が在るか。ID だけの参照(`docs/issues/054`)とグロブ(`MODULE-*.md`)を解決する。"""
    if '<' in ref or '>' in ref:
        return True                            # 雛形の差し込み記号。参照ではない
    m = NUMBERED_ID.match(ref)
    if m:
        return bool(list((repo / m.group(1)).glob(f"{m.group(2)}-*.md"))) \
            or (repo / ref).exists() or (repo / (ref + ".md")).exists()
    if '*' in ref:
        try:
            return bool(list(repo.glob(ref)))
        except (ValueError, OSError):
            return True                        # 解釈できないものを違反にはしない
    return (repo / ref).exists() or (repo / (ref + ".md")).exists()


# 規範が明示的に命じる「未定」の定型はどちらも未決点ではない(宣言された停止点):
# 「未定(いつ決めるか)」= 02(directions/02-design.md)/「未定(02設計で決める)」= 01
UNDECIDED_OK = ("未定(いつ決めるか)", "未定(02設計で決める)")


def visible_lines(body, base=0):
    """HTML コメントを除いた本文を、行番号を保って返す。

    コメントは仕様の文ではない(CS8 の規範は「仕様の文に残さない」)。雛形の
    案内コメントが `/setup` で SSOT に逐語コピーされると、曖昧語の禁止一覧そのものが
    曖昧語として検出されていた。

    **`base` は frontmatter の行数**(loader が `'base'` に入れる)。`body` は
    frontmatter を切り落とした後なので、これを足さないと**報告した行番号で開いても
    指摘した行が無い**(CLAUDE.md 原則11。`KIT-ssot-sweep-line-numbers-are-body-relative`)。
    """
    inc = False
    for n, line in enumerate(body.splitlines(), 1 + base):
        s = line
        if inc:
            if '-->' in s:
                s, inc = s.split('-->', 1)[1], False
            else:
                yield n, ""
                continue
        while '<!--' in s:
            pre, rest = s.split('<!--', 1)
            if '-->' in rest:
                s = pre + rest.split('-->', 1)[1]
            else:
                s, inc = pre, True
                break
        yield n, s


def md_headings(text):
    """本文の見出しテキスト一覧(コードフェンス内の `#` コメントは見出しではない)。"""
    out, fence = [], False
    for line in text.splitlines():
        if FENCE.match(line):
            fence = not fence
            continue
        if fence:
            continue
        m = re.match(r'\s{0,3}#{1,6}\s+(.+?)\s*$', line)
        if m:
            out.append(m.group(1).strip())
    return out


def cs8(docs):
    """曖昧語・未決点。**程度を表す語も曖昧語である**(`.claude/directions/core.md` §6)。"""
    out = []
    for k, d in docs.items():
        for n, line in visible_lines(d['body'], d.get('base', 0)):
            for w in VAGUE:
                pat = VAGUE_CONTEXT.get(w)
                hit = bool(pat.search(line)) if pat else (w in line)
                if hit: out.append(("CS8", k, f"{n}行: 曖昧語「{w}」"))
            for w in OPEN_POINT:
                if w in line and not any(x in line for x in UNDECIDED_OK):
                    out.append(("CS8", k, f"{n}行: 未決点が仕様に残っている「{w}」"))
    return out


def cs11(docs, repo):
    """参照実在。**frontmatter の `source:` と本文の `docs/…` が実在するか。**

    解消して削除した issue のパスが根拠として残り続ける、が実例である
    (claude-dev-env の `docs/issues/054`: 10 個の ID・20 以上のファイル)。
    人間が読むまで気づけない一方、機械なら一撃で全件出る型の欠陥。
    """
    out = []
    for k, d in docs.items():
        seen = set()
        for src in lst(d['fm'].get('source', '')):
            src = src.strip('`" ')
            if src.startswith('docs/') and src not in seen and not ref_exists(src, repo):
                seen.add(src)
                out.append(("CS11", k, f"frontmatter source が実在しない: {src}"))
        fence = False
        for n, line in visible_lines(d['body'], d.get('base', 0)):
            if FENCE.match(line):
                fence = not fence
                continue
            if fence:
                continue                       # コード例の中のパスは参照ではない
            for m in REF.finditer(line):
                ref = m.group(1).rstrip('.、。)')      # 文末の句読点は参照の一部ではない
                if ref in seen or ref_exists(ref, repo):
                    continue
                seen.add(ref)
                out.append(("CS11", k, f"{n}行: 参照先が実在しない: {ref}"))
    return out


# CS18: 01 に降りてきた下位層の語彙。**規範は `.claude/directions/01-requirements.md` の
# 「The line between 01 and 02/03」**(置き換えテスト・観測者テスト)であり、ここはその
# **露骨な場合だけ**を機械で拾う。要件が機構で書かれると、実現方法の一つ一つが「要件」になり、
# 全部が人間の合意を要る判断に化ける — それがこの検査の防ぎたい損失である。
# `system.md` は対象外(技術を名指すのがその節の目的。§「system.md」)。
CS18_TARGET = re.compile(r'01-requirements/(functional|usecases|non-functional)')
LOWER_ID = re.compile(r'\b(MODULE-[A-Za-z0-9_-]+|MOD-[A-Za-z0-9_-]+|PLAN-[A-Za-z0-9_-]+'
                      r'|CTR-[A-Za-z0-9_-]+)')
# 行内コードのうち、コードの識別子とパスだけを拾う。日本語の強調や ID は拾わない。
CODE_TOKEN = re.compile(r'`([^`\n]{1,80})`')
CODE_SHAPE = re.compile(r'(\w\(\)|::|->|\w+\.(py|ts|tsx|go|rs|java|rb|sql|ya?ml|json)\b'
                        r'|^(src|lib|app|internal|pkg|cmd)/)')


def cs18(docs):
    """01 の本文に下位層(02/03)の語彙が現れていないか。"""
    out = []
    for k, d in docs.items():
        if not CS18_TARGET.search(k):
            continue
        fence = False
        for n, line in visible_lines(d['body'], d.get('base', 0)):
            if FENCE.match(line):
                fence = not fence
                continue
            if fence:
                continue
            for m in LOWER_ID.finditer(line):
                out.append(("CS18", k, f"{n}行: 下位層の ID「{m.group(1)}」が要件に在る"
                                       "(機構は 02/03。01-requirements.md の置き換えテスト)"))
            for m in CODE_TOKEN.finditer(line):
                tok = m.group(1)
                if tok.startswith('docs/') or tok.startswith('.claude/'):
                    continue               # 規範・文書への参照は機構ではない
                if CODE_SHAPE.search(tok):
                    out.append(("CS18", k, f"{n}行: 実装の識別子「{tok}」が要件に在る"
                                           "(機構は 02/03。01-requirements.md の観測者テスト)"))
    return out


# CS19: 「なぜこうなっているのか」に答える節が、書かれるべき所で空でないか。
# **これは網羅の検査である。** 書かれた開示の形を見るのは検証フローの読取検査であって
# 機械検査ではなく、**そもそも何も書かなかった**場合はそれにも何にも当たらない。実装が在れば実現方法の判断は必ず在るので、
# 「判断なし」なら理由付きでそう書かせる — 沈黙と「判断が無かった」を区別できるようにする。
# 規範: .claude/directions/delegation.md §3 / 03-impl.md / 02-design.md
# **3つ目の値は見出しの深さ**(`##` なら 2)。**対象ごとに違う** — REST 契約の「設計判断」は
# `###` で(`.claude/templates/02-contract.md`)、REST でない契約は `##` である
# (同 `02-contract-nonrest.md`)ので、契約は両方を受ける。深さを固定にすると、
# **節が在るのに「節が無い」と言う**ことになる。
WHY_SECTIONS = [
    (re.compile(r'01-requirements/functional[^/]*\.md$'), "今回決めた既定(開示)", (2,)),
    (re.compile(r'03-impl/relations/MODULE-[^/]+\.md$'), "実装上の判断", (2,)),
    (re.compile(r'03-impl/tests/(?!index\.md$)[^/]+\.md$'), "テスト設計の判断", (2,)),
    (re.compile(r'02-design/architecture\.md$'), "設計判断", (2,)),
    (re.compile(r'02-design/system\.md$'), "分割の根拠", (2,)),
    (re.compile(r'02-design/contracts/(?:.*/)?(?!index\.md$)[^/]+\.md$'), "設計判断", (2, 3)),
    (re.compile(r'02-design/logging\.md$'), "設計判断", (2,)),
]
WHY_HEADING = re.compile(r'^(#{1,6})\s+(.+)$')
RELATIONS_INSTRUCTION = re.compile(r'03-impl/relations/MODULE-[^/]+\.md$')
NO_DECISION = re.compile(r'(判断なし|該当なし|なし)\s*[::((]')
PLACEHOLDER = re.compile(r'<[^<>\n]{0,60}>')
# 定型のラベルは中身ではない。**雛形が置く欄の名前はすべて並べる** ★ —
# 1つでも漏らすと、その欄が空でも「書いてある」と数えられる(2026-09-13: `影響する要件` の
# 1語で、`02-architecture.md` の空の設計判断が CS19 を通っていた)。
SKELETON = re.compile(r'\[[A-Za-z]{1,6}-?\d*\]|理由|見直す条件|却下した案|影響する要件|判断'
                      r'|[-—:：/|*`。、\s]')


def why_section(body: str, heading: str, base: int = 0,
                levels: tuple[int, ...] = (2,)) -> tuple[bool, bool]:
    """(節が在ったか, 中身が在ったか)。雛形の差し込み記号だけの状態は「無い」と数える。

    `levels` は見出しの深さの候補(`##` なら 2)。節は**同じ深さか、それより浅い見出し**で
    終わる。**それより深い見出しは、その節の中身として数える**(`### DSN-arch-01 …` は
    「設計判断」の中身である)。
    """
    inside = found = filled = False
    depth = 0
    for _n, line in visible_lines(body, base):
        s = line.strip()
        m = WHY_HEADING.match(s)
        if m:
            if inside:
                if len(m.group(1)) <= depth:
                    break
                # **深い見出しは器であって中身ではない** ★(2026-09-13)。
                # 数えると、雛形の `### DSN-log-01 <タイトル>` が在るだけで「書いてある」に
                # なり、**判断も理由も空のまま CS19 を通る。** 中身は、その下の行が持つ。
                continue
            else:
                if len(m.group(1)) in levels and heading in m.group(2):
                    inside, found, depth = True, True, len(m.group(1))
                continue
        if not inside or not s:
            continue
        if set(s) <= set("|- :"):
            continue                       # 表の区切り行
        marker = NO_DECISION.search(s)
        if marker:
            # **「判断なし」と書いただけでは通さない** ★(2026-09-12 の検査 A2-4)。
            # 印の後ろの理由から差し込み記号と定型のラベルを落として、なお中身が残るかを見る
            # (`- 判断なし:` / `- 判断なし: <理由>` / `- なし: <>` はどれも空である)。
            # 理由の無い「判断なし」は、CS19 が区別しようとしている沈黙そのものである。
            reason = SKELETON.sub("", PLACEHOLDER.sub("", s[marker.end():])).strip()
            if reason:
                return True, True          # 「判断なし: <理由>」は明示された答えである
            continue                       # 理由が空。この行は「書いてある」と数えない
        # **雛形の骨だけの行を「書いてある」と数えない。** 差し込み記号と定型のラベルを落として
        # なお中身が残るかで見る(`- [DS-<nn>] <決めたこと> — 理由: <> / 見直す条件: <>` は空である)。
        if SKELETON.sub("", PLACEHOLDER.sub("", s)).strip():
            filled = True
    return found, filled


def cs19(docs):
    """理由の網羅。「なぜこうなっているのか」に答える節が、書かれるべき所で空でないか。

    実装が在れば実現方法の判断は必ず在るので、「判断なし」なら理由付きでそう書かせる —
    沈黙と「判断が無かった」を区別できるようにする(規範: delegation.md §3 / 03-impl.md /
    02-design.md)。
    """
    out = []
    for k, d in docs.items():
        target = d['fm'].get('target', '') or k
        for pat, heading, levels in WHY_SECTIONS:
            if not pat.search(target):
                continue
            found, filled = why_section(d['body'], heading, d.get('base', 0), levels)
            if not found:
                marks = "」または「".join(f"{'#' * lv} {heading}" for lv in levels)
                out.append(("CS19", k, f"「{marks}」の節が無い"
                                       "(見出しは消さない。原則9)"))
            elif not filled:
                out.append(("CS19", k, f"「{heading}」が空。判断が無かったのなら"
                                       "「判断なし: <理由>」と書く — **沈黙と不在は区別できない**"
                                       "(理由を空にした「判断なし:」も、ここでは空と数える)"))
    return out


# CS24: `分割可否` の記載漏れ。**既定値を持たせない**(規範は
# `.claude/directions/01-requirements.md` の「分割可否」)。未記載を `不可分` とみなす既定は、
# 「決めなかった」と「不可分と決めた」を区別できなくする — 02 が正当に `部分` と書きたい場面で
# 完成判定が止まり、止まった側は原因を辿れない。決めるのは 01 を書く AI であり、
# 人間には問わない — 値はこの要件の行そのものが持つ(規範の「分割可否」の「どこで決まるか」)。
# **`SR-*` は対象外**(技術前提であって、部分的に満たされるという状態が無い)。
#
# **差し込み記号は値ではない** ★ — 雛形の `<不可分 | 段階可(理由)>` は選択肢の見本であって
# 決定ではない。`<…>` を落としてから値を探さないと、**雛形を写しただけの行が「決定済み」と
# 数えられる**(`cs25_substantive` と同じ強度である)。
# **値はちょうど1つである** — `不可分` と `段階可` が同じ行に残るのは選択肢の消し忘れであり、
# 決定ではない(規範の「値はちょうど2つ」)。
# **`段階可` は理由を持つ**(規範の「理由の無い `段階可` は重大度「高」の所見である」)。
# 空の文句は理由ではないので、**逃げ道の理由と同じ強度で見る**(`cs25_reason_ok` を共有する —
# 同じ判定を2つ持たない)。**`不可分` には理由を求めない** — 規範が課していない記入義務を
# 検査が作らない。
# **列の位置は決め打ちしない** ★ — 非機能要件の表で `分割可否` が何列目かは規範が決めて
# いないので、**見出し行から列を特定する**(CS25 が同じ事故で学んだことである)。
# 見出しが読めない表では、これまでどおり行全体を見る。
CS24_FUNC = re.compile(r'01-requirements/functional[^/]*\.md$')
CS24_NONFUNC = re.compile(r'01-requirements/non-functional\.md$')
CS24_FR = re.compile(r'^##\s+(FR-[A-Za-z0-9_-]+-\d+)')
CS24_NFR_ROW = re.compile(r'^\|\s*(NFR-[A-Za-z0-9-]+-\d+)\s*\|')
CS24_VALUE = re.compile(r'不可分|段階可')
CS24_FIELD = re.compile(r'分割可否\s*\**\s*[:：]')
CS24_OPEN = re.compile(r'段階可\s*[(（]')
CS24_REASON_LABEL = re.compile(r'\A\s*理由\s*[:：]\s*')
CS24_MSG = "(未記載は既定ではなく違反である — 規範は 01-requirements.md の `分割可否`)"
CS24_REASON_MSG = ("(理由の無い `段階可` は重大度「高」の所見である — 規範は "
                   "01-requirements.md の `分割可否`)")


def cs24_value(text):
    """その欄が述べている `分割可否`。**差し込み記号は値ではない。**

    返り値は (値, 理由)。値は `不可分` / `段階可` / `両方`(選択肢の消し忘れ)/ None(未記入)。
    理由は `段階可` のときだけ文字列で、丸括弧が無ければ空文字である。
    """
    s = PLACEHOLDER.sub("", text)
    # **値を探すのは、理由の外だけである** ★ — 理由の本文に「不可分」と書けるので
    # (「検索と編集は不可分ではなく独立して使える」)、欄の全体を走査すると
    # **正しい記入を「選択肢の消し忘れ」と読む。** 先に理由を切り離す。
    span = cs24_reason_span(s)
    outside = (s[:span[0]] + s[span[1]:]) if span else s
    kinds = {g.group(0) for g in CS24_VALUE.finditer(outside)}
    if span:
        kinds.add("段階可")
    if len(kinds) > 1:
        return "両方", None
    if not kinds:
        return None, None
    v = kinds.pop()
    if v == "不可分":
        return v, None
    if not span:
        return v, ""
    inner = s[span[0]:span[1]]
    inner = inner[inner.index("(") + 1 if "(" in inner[:8] else inner.index("（") + 1:-1]
    return v, CS24_REASON_LABEL.sub("", inner).strip()


def cs24_reason_span(text):
    """`段階可(…)` の丸括弧を**対応まで追って**切り出す。無ければ None。

    **最初の閉じ括弧で切らない** ★ — 理由の中に補足の括弧を書くことは禁じていないので、
    そこで切ると**残りが選択肢の側へ戻り**、理由に「不可分」と書いた正しい記入を
    「選択肢の消し忘れ」と読む(2026-09-13)。
    """
    m = CS24_OPEN.search(text)
    if not m:
        return None
    start = m.start()
    depth = 0
    for i in range(text.index("(", start) if "(" in text[start:m.end()] else
                   text.index("（", start), len(text)):
        if text[i] in "(（":
            depth += 1
        elif text[i] in ")）":
            depth -= 1
            if depth == 0:
                return start, i + 1
    return None                            # 閉じていない = 括弧を書きかけている


def cs24_bad(text):
    """`分割可否` の欄が抱える誤り。無ければ None。"""
    v, reason = cs24_value(text)
    if v is None:
        return f"の値が未記入である{CS24_MSG}"
    if v == "両方":
        return ("に `不可分` と `段階可` が両方在る"
                "(値はちょうど1つ — 選択肢を消し忘れた行は決定ではない)")
    if v == "段階可" and not cs24_reason_ok(reason):
        return f"の `段階可` に理由が無い{CS24_REASON_MSG}"
    return None


def cs24_reason_ok(text):
    """`段階可` の理由が中身を持つか。**空と、空の文句だけを弾く。**

    **`cs25_reason_ok` を使わない** ★ — あちらは最小文字数(`CS25_MIN_REASON`)を課すが、
    この検査に文字数の条件は無い(裁定 A-1: 理由の質を文字数で判定する仕組みは含めない)。
    妥当かどうかを読むのは `/verify-docs` である。
    """
    core = SKELETON.sub("", PLACEHOLDER.sub("", text)).strip()
    return bool(core) and not CS25_HOLLOW.match(core)


def cs24_is_field(line):
    """その行が `分割可否` の欄か。**題だけの言及は欄ではない。**"""
    if "分割可否" not in line:
        return False
    return bool(CS24_FIELD.search(line)) or cs24_value(line)[0] is not None


def cs24_cells(line):
    """表の行を欄に割る。行でなければ None。"""
    s = line.strip()
    return [c.strip() for c in s.strip("|").split("|")] if s.startswith("|") else None


def cs24(docs):
    """すべての要件が `分割可否` を述べているか。**既定値は無い。**"""
    out = []
    for k, d in docs.items():
        target = d['fm'].get('target', '') or k
        if CS24_FUNC.search(target):
            cur, at, seen = None, 0, False
            for n, line in visible_lines(d['body'], d.get('base', 0)):
                m = CS24_FR.match(line.strip())
                if m:
                    if cur and not seen:
                        out.append(("CS24", k, f"{at}行: 「{cur}」に 分割可否 が無い{CS24_MSG}"))
                    cur, at, seen = m.group(1), n, False
                elif cur and cs24_is_field(line):
                    seen = True
                    bad = cs24_bad(line)
                    if bad:
                        out.append(("CS24", k, f"{n}行: 「{cur}」の 分割可否 {bad}"))
            if cur and not seen:
                out.append(("CS24", k, f"{at}行: 「{cur}」に 分割可否 が無い{CS24_MSG}"))
        elif CS24_NONFUNC.search(target):
            col = None
            for n, line in visible_lines(d['body'], d.get('base', 0)):
                cells = cs24_cells(line)
                if cells is None:
                    continue
                m = CS24_NFR_ROW.match(line.strip())
                if not m:
                    for i, c in enumerate(cells):      # 見出し行から列を特定する
                        if "分割可否" in c:
                            col = i
                    continue
                cell = cells[col] if col is not None and col < len(cells) else line
                bad = cs24_bad(cell)
                if bad:
                    out.append(("CS24", k, f"{n}行: 「{m.group(1)}」の行の 分割可否 {bad}"))
    return out


# CS25: 受け入れ基準の `境界値` と `異常系` の欠落。規範は
# `.claude/directions/01-requirements.md` の「正常系だけを覆う受け入れ基準は未完成である」。
# **この穴だけは下流が捕まえられない** — 02 のカバレッジ表も 03 のテスト対応表も
# 「01 の条項に対して行が在るか」しか見ないので、**条項そのものが無い穴は全層を素通りする**
# (`.claude/directions/03-impl.md` が「実装後には作り直せないもの」に 01 の受け入れ基準を
# 挙げているのと同じ理由で、検出は最も早い時点に置く)。
# **正当な省略は在る**(外の誰にも区別できない結果しか持たないものは 01 に属さない — 同規範)。
# だから逃げ道を置くが、**骨抜きは数えない**: 差し込み記号と定型のラベルを落として中身が
# 残ること(CS19 と同じ強度)に加え、**「該当なし」だけの空の文句を名指しで弾く** —
# 逃げ道は必ず濫用されるので、CS19 より1段強くしてある。
CS25_KINDS = ("境界値", "異常系")
# **表は見出し行から特定する。** `種別` の欄が何列目かは規範が決めていない(決めているのは
# 「条項 ID は1列目」だけ — `01-requirements.md`)ので、**列の位置を決め打ちすると、並びの
# 違う文書で全要件が偽の違反になる**(実測: 1プロジェクトで 24 要件すべてが落ちた)。
# 見出し行に `種別` が在る表だけを受け入れ基準の表とみなすことで、**要件の中に在る別の表**
# (検討メモなど)を条項として数えてしまう経路も同時に閉じる。
CS25_HEAD = re.compile(r'^##\s')
CS25_SEP = re.compile(r'^[\s|:-]+$')
# **フェンスは ``` と ~~~ の2種類ある。** 共有の `FENCE` は前者しか見ないので、
# `~~~` で囲った例示の表が本物の条項として数えられた(実測)。**開いた印と同じ印でしか
# 閉じない** — 種類を混ぜて数えると、対応しない組み合わせで状態が反転する。
# (共有の `FENCE` を広げると CS11 と CS21 の見え方まで動くので、ここだけで持つ。
#  あちらにも同じ取り落としが在ることは、この変更の外の所見である。)
CS25_FENCE = re.compile(r'^\s*(```|~~~)')
# **見出しの深さが1段違うだけで、要件は1件も登録されない。** `CS24` も `CS25` も
# `^##\s+FR-` しか見ないので、`### FR-…` で書かれた文書は**両方が黙る** —
# 「対象が0件だった」と「全部合格した」が同じ表示になる(このファイル冒頭が掲げる
# 「対象0件は『違反なし』ではない」の、要件数の側である)。
# **要件が1件も無いこと自体は違反にしない**(書き始めの文書が在りうる)。
# **`FR-` の見出しが在るのに1件も登録できなかったときだけ**鳴らす。
CS25_ANY_FR = re.compile(r'^(#+)\s+(FR-[A-Za-z0-9_-]+-\d+)')
# **欄名は完全一致で当てない** ★ — 規範が決めているのは「条項 ID は1列目」だけであり、
# 欄の名前は決めていない。実測で `受け入れ基準` が `基準` に一致せず最後の欄(`備考`)を
# 基準と読み、そろった表が偽の違反になった。**列の位置を決め打ちしていた1周目の事故が、
# 名前の側で再現した**ので、こちらも部分一致にする。
CS25_KIND_COL = "種別"
CS25_CRIT_COL = "基準"
CS25_ID_COL = "条項"
# **`種別` の欄が在るだけでは受け入れ基準の表ではない。** 検討メモの表
# (`| 観点 | 種別 | 02 での扱い |`)がそれで条項として数えられた(実測)。
# **`種別` と、`基準` か `条項` のどちらかが揃っている表**だけを受け入れ基準の表とみなす。
# **中身の無い印は条項として数えない** — 空欄と差し込み記号だけを弾いても、
# `TBD` を2本足すのが検査を黙らせる最短手として残る(実測)。
CS25_EMPTY_CRIT = re.compile(r'^(TBD|未定|不明|保留|[?？~〜ー–—-]+)$', re.I)
# **欄の飾りを落としてから、種別の語と「完全に」比べる。** 部分一致にすると
# `| FR-x-2 | 境界値なし | |` が「境界値の条項が在る」と数えられ、**逃げ道より安く**
# 規範の「理由を書け」を回避できてしまう(実測)。
CS25_DECOR = re.compile(r'[*`\s]')
CS25_WAIVER = re.compile(r'(境界値|異常系)\s*なし\s*[((](.*?)[))]')
# 空の文句は**形で弾く**。**長さでは弾かない** ★ — 実測で両方向に外れた:
# 「外から区別できない」(9文字。正当な理由)が落ち、「あああああああああああ」(11文字。無意味)が
# 通った。**理由が本当に理由になっているかは、機械には判定できない** — それはこのキットが
# `delegation.md` §3 で既に「指針(検査を持てない)。読み手が差し戻す」に分類したものである。
# **機械が見るのは形だけ**: 打ち消しの決まり文句そのものでないこと、そして1〜2文字でないこと。
# 語の列挙は**語尾の助詞まで含めて**当てる(`該当なし` だけ弾いて `該当なしのため` を通すと、
# 逃げ道は1文字足せば抜ける)。
CS25_MIN_REASON = 4
CS25_HOLLOW = re.compile(
    r'^(該当|特に)?(なし|無し|無い|ありません|不要|省略|該当せず|未定|N/?A)'
    r'(のため|だから|である|です)?[。.]?$', re.I)


def cs25_cells(line):
    """表の行を欄に割る。行でなければ None。"""
    s = line.strip()
    if not s.startswith("|"):
        return None
    return [c.strip() for c in s.strip("|").split("|")]


def cs25_substantive(text):
    """欄に中身が在るか。

    **差し込み記号が1つでも残っていれば、書かれていないとみなす** ★ — 雛形の
    `WHEN <契機> the system SHALL <振る舞い>` は、落としてもなお `WHEN the system SHALL` が
    残るので、**雛形を写して埋めないままの行が「条項が在る」と数えられていた。**
    本物の条項が `<…>` を含むことは無い。
    """
    if PLACEHOLDER.search(text):
        return False
    core = SKELETON.sub("", text).strip()
    return bool(core) and not CS25_EMPTY_CRIT.match(core)


def cs25_reason_ok(text):
    """逃げ道の理由が中身を持つか。**空の文句は理由ではない。**"""
    core = SKELETON.sub("", PLACEHOLDER.sub("", text)).strip()
    return len(core) >= CS25_MIN_REASON and not CS25_HOLLOW.match(core)


def cs25_is_header(names):
    """受け入れ基準の表の見出し行か。**`種別` だけでは足りない**(検討メモの表が当たる)。"""
    if not any(CS25_KIND_COL in c for c in names):
        return False
    return any(CS25_CRIT_COL in c or CS25_ID_COL in c for c in names)


def cs25(docs):
    """すべての機能要件が `境界値` と `異常系` の条項を持つか。**正常系だけでは未完成である。**

    **非機能要件は対象外**である(条項に分けないので、種別の欄を持つ表が無い —
    規範の `01-requirements.md` がその旨を書いている)。
    """
    out = []
    for k, d in docs.items():
        target = d['fm'].get('target', '') or k
        if not CS24_FUNC.search(target):
            continue
        blocks, cur, cols, fence = [], None, None, None
        for n, line in visible_lines(d['body'], d.get('base', 0)):
            s = line.strip()
            # **フェンスの中は見ない。** 同じファイルの他の検査(CS11・CS21)と作法を揃える —
            # 例示の表を条項と数えたり、例示の `##` で要件を打ち切ったりするのを防ぐ。
            fm = CS25_FENCE.match(line)
            if fm:
                if fence is None:
                    fence = fm.group(1)           # 開いた印を覚える
                elif fence == fm.group(1):
                    fence = None                  # **同じ印でだけ閉じる**
                continue
            if fence:
                continue
            m = CS24_FR.match(s)
            if m:
                cur = {"id": m.group(1), "at": n, "kinds": set(), "waived": set()}
                blocks.append(cur)
                cols = None
                continue
            # **要件でない `##` 見出しは、要件の区切りである。** ここで閉じないと、
            # 「要求カバレッジ確認」など後続の表の行が直前の要件のものとして数えられる。
            if CS25_HEAD.match(s):
                cur, cols = None, None
                continue
            if cur is None:
                continue
            cells = cs25_cells(s)
            if cells is None:
                cols = None                       # 表が途切れた
            elif CS25_SEP.match(s):
                pass                              # 見出しと本体の区切り行
            elif cols is None and cs25_is_header([CS25_DECOR.sub("", c) for c in cells]):
                # **見出しを取り直すのは、表の外に居るときだけである** — 表の途中の行に
                # `種別` の語が出るたびに欄の対応を上書きすると、そこから先が読めなくなる。
                names = [CS25_DECOR.sub("", c) for c in cells]
                kind_at = next(i for i, c in enumerate(names) if CS25_KIND_COL in c)
                crit = [i for i, c in enumerate(names) if CS25_CRIT_COL in c and i != kind_at]
                cols = (kind_at, crit[0] if crit else len(cells) - 1)
            elif cols:
                kind_at, crit_at = cols
                if kind_at < len(cells):
                    kind = CS25_DECOR.sub("", cells[kind_at])
                    # **条項の中身が空なら、条項が在るとは数えない。** 空の行を2本足すのが
                    # この検査を黙らせる最短手になってはならない。
                    if kind in CS25_KINDS and crit_at < len(cells) \
                            and cs25_substantive(cells[crit_at]):
                        cur["kinds"].add(kind)
            # **逃げ道は表の外でだけ数える** ★ — 条項の本文に `境界値なし(…)` と書くと、
            # **条項そのものが免除の宣言に化けていた**(実測)。
            if cells is None:
                for w in CS25_WAIVER.finditer(s):
                    if cs25_reason_ok(w.group(2)):
                        cur["waived"].add(w.group(1))
        if not blocks:
            # 上の `CS25_ANY_FR` の説明を見ること。**沈黙と不在を区別する。**
            for n, line in visible_lines(d['body'], d.get('base', 0)):
                m = CS25_ANY_FR.match(line.strip())
                if m:
                    out.append(("CS25", k,
                                f"{n}行: 「{m.group(2)}」の見出しが `{m.group(1)}` の深さで"
                                "書かれているので、要件として1件も読めていない — "
                                "**`##` で書く**(`01-requirements.md`)。"
                                "`CS24`(分割可否)も同じ理由で黙っている"))
                    break
        if fence:
            # **この検査は「無いこと」を見るので、読み切れなかったときに黙ると
            # 「穴が無い」と区別が付かない。** 閉じないフェンスは、その先の要件を丸ごと
            # 検査から消すので、沈黙ではなく違反として出す。
            out.append(("CS25", k, "コードフェンス(```)が閉じていないので、"
                                   "この文書を読み切れなかった — 閉じるまで検査できない"))
        for b in blocks:
            for kind in CS25_KINDS:
                if kind in b["kinds"] or kind in b["waived"]:
                    continue
                out.append(("CS25", k,
                            f"{b['at']}行: 「{b['id']}」の受け入れ基準に {kind} の条項が無い"
                            f"(足すなら**末尾に新しい番号で**。既存の番号を振り直さない。"
                            f"正当に省くなら「{kind}なし(<外から観測できる違いが無い理由>)」を"
                            "この要件の中に書く — 空の文句は数えない。規範は "
                            "01-requirements.md の"
                            "「正常系だけを覆う受け入れ基準は未完成である」)"))
    return out


# CS26: 条項 ID の消失。規範は `.claude/directions/01-requirements.md` の
# 「**条項 ID は、一度割り当てたら決して動かない**」。**この規則にはこれまで検査が無く**、
# 番号を振り直した参照は解決してしまう(別の条項を指すだけ)ので、02 のカバレッジ表と
# 03 のテスト対応表の全行が別の条項についての主張に化けても、どの検査も鳴らなかった
# (inspection-23 A-3)。唯一の見張りだった独立レビューは、3ファイル以下の run では
# 免除される(`/verify-docs` §2)— 番号が動く典型はまさにその形の run である。
# **基準の版と比べる**: 最後の `verify-docs` の green の鮮度スタンプのコミット、無ければ
# `HEAD`。前者を既定にするのは、**免除された run が省いた独立の目を次の F2 が引き受ける
# 範囲**と同じものを見るためである(`HEAD` だけを基準にすると、番号を振り直したコミットは
# この検査を素通りする)。
# **git を引けない場所では判定しない** — この検査だけが git に依存するので、git の無い
# 環境とリポジトリの外では「判定不能」と印字し、違反を1件も出さない
# (`check-buildrecord.py` の `commit_ok` と同じ倒れ方)。**黙って OK を出さない**のは、
# このファイル冒頭の「『検査して問題なし』と『検査していない』を同じ表示にしない」である。
# **要件まるごとの移行は違反にしない**: 消えた条項の要件の見出しも一緒に消えているときは、
# 規範が「移行」と呼ぶ形である(同 `:97-99`)ので候補として列挙するだけにする —
# 参照の書き換えが同じクロージャに在るかは機械には判定できない。
# **見出しが残っているのに条項だけが消えた形**が違反である。
# 状態層の読み手は増やさない(原則10): 鮮度スタンプは `stamps.py` から読む。
# **条項は構造で読む**(課題311): 規範は条項 ID を `FR-<domain>-nn-#` とし、`#` の欄を
# 番地と呼ぶ(同 `:84`)ので、表の1列目には複合形(`| FR-auth-01-3 |`。雛形の形)も
# 局所番地(`| 6-2 |`。要件の見出しの下で番地だけを書く形)も在りうる。本文の全文から
# 複合形だけを拾うと、局所番地で書いた 01 では母集団が常に空になり、この検査は導入以来
# 一度も鳴らなかった(しかも本文中の参照「FR-payment-03 基準13」は条項として数えていた)。
# だから要件の見出し(`## FR-…-nn`)から、同じ深さ以上の次の見出しまでを要件の範囲とし、
# その中の**受け入れ基準の表**(見出し行の判定は CS25 と同じ `cs25_is_header`。検討メモの表を
# 条項と数えない)の行の1列目だけを条項として読む — 複合形はそのまま、数字で始まる番地は
# `見出しの ID-番地` に組み立てる。フェンスの扱いも CS25 と揃える(同じ印でだけ閉じる)。
CS26_LAYER = "01-requirements"
CS26_CLAUSE = re.compile(r'FR-[A-Za-z0-9_-]*\d+-\d+(?![\w-])')
CS26_REQ = re.compile(r'^(#+)\s+(FR-[A-Za-z0-9_-]*\d+)(?![\w-])')
CS26_HEAD = re.compile(r'^(#+)\s')
CS26_LOCAL = re.compile(r'^\d[^\s|]*$')      # 局所番地: 1 / 6-2 / 12(2)


def cs26_clauses(text):
    """01 の文書1本から ({条項 ID: その要件の ID}, 要件の ID の集合) を読む。

    基準の版にも現在の版にも同じものを当てる。**要件の見出しも同じ走査で集める** —
    条項だけフェンスを除き、見出しは生の全行から拾うと、例示の `## FR-…` が
    「見出しが残っている」と数えられ、要件まるごとの移行が違反に化ける。
    """
    out, reqs, req, depth, fence, in_tbl, prev = {}, set(), None, 0, None, False, None
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            prev = None
        fm = CS25_FENCE.match(line)
        if fm:
            if fence is None:
                fence = fm.group(1)
            elif fence == fm.group(1):
                fence = None
            continue
        if fence:
            continue
        h = CS26_HEAD.match(s)
        if h:
            m = CS26_REQ.match(s)
            if m:
                req, depth = m.group(2), len(m.group(1))
                reqs.add(req)
            elif req and len(h.group(1)) <= depth:
                req = None             # 同じ深さ以上の見出し = その要件の範囲の終わり
            in_tbl = False
            continue
        cells = cs25_cells(s)
        if cells is None:
            # **空行では表の種類を忘れない** — 実物の 01 には、受け入れ基準の表が空行で切れて
            # 見出し行なしに番地の続きから再開する形が在る(`| 18 | …`)。忘れるとその条項が
            # 基準の版からも現在の版からも黙って消え、消しても鳴らない。
            # **空行以外(段落・箇条書き)では忘れる** — その後の見出し行の無いパイプ行は
            # 受け入れ基準の表の続きとは言えず、数字を条項と取り違えると消失を隠す
            if s:
                in_tbl = False
            continue
        if CS25_SEP.match(s):
            # 区切り行の直前の行が表の見出し行である。ここで表の種類を決め直す
            in_tbl = bool(prev) and cs25_is_header([CS25_DECOR.sub("", c) for c in prev])
            continue
        prev = cells
        if not req or not in_tbl:
            continue
        cell = CS25_DECOR.sub("", cells[0])
        if cell.startswith(req + "-") and CS26_LOCAL.match(cell[len(req) + 1:]):
            out[cell] = req            # 複合形(番地は局所形と同じ字の並び。`FR-x-02-12(2)` も)
        elif CS26_CLAUSE.fullmatch(cell):
            out[cell] = req
        elif CS26_LOCAL.match(cell):
            out[f"{req}-{cell}"] = req
    return out, reqs


def _git(repo, *args):
    """git を1回叩いて標準出力を返す。**引けなければ None**(= 判定不能)。"""
    import subprocess
    try:
        r = subprocess.run(("git",) + args, cwd=repo, capture_output=True, text=True)
    except OSError:
        return None                    # git が無い
    return r.stdout if r.returncode == 0 else None


def cs26_base(repo):
    """比べる基準の版(コミット)。引けなければ None。"""
    rev = None
    here = str(pathlib.Path(__file__).resolve().parent)
    try:
        if here not in sys.path:
            sys.path.insert(0, here)
        import stamps                   # 状態の読み手は1つに保つ(原則10)
        e = stamps.green_entry(stamps.load_stamps(pathlib.Path(repo)), "verify-docs")
        if isinstance(e, dict):
            rev = str(e.get("commit") or "").strip() or None
    except Exception:
        # **状態が読めないことは判定不能ではない**(HEAD へ倒す)。
        # ここを狭い例外の列挙にすると、`stamps.py` 側の構文エラーや将来の別の失敗で
        # **この検査だけでなく一括検査の全体が落ちる**。読み手を増やした代償はここで払う。
        rev = None
    out = _git(repo, "rev-parse", "--verify", f"{rev or 'HEAD'}^{{commit}}")
    if out is None and rev:
        # 記録されたコミットが履歴から消えている(rebase・squash)。HEAD へ倒す
        out = _git(repo, "rev-parse", "--verify", "HEAD^{commit}")
    return out.strip() if out else None


def cs26(docs, docs_root, repo):
    """条項 ID が基準の版から消えていないか。**git を引けなければ判定しない。**

    戻り値は (所見, 判定不能の理由 or None, 移行と読める消失の一覧)。
    後ろの2つはどちらも**違反に数えない** — 印字だけである。
    """
    rev = cs26_base(repo)
    if rev is None:
        return [], "git を引けない — この検査だけが git に依存する", []
    listing = _git(repo, "ls-tree", "-r", "--name-only", rev, "--",
                   f"{docs_root.name}/{CS26_LAYER}")
    if listing is None:
        return [], f"基準の版 {rev[:12]} を引けない", []
    base_ids = {}
    for path in (x.strip() for x in listing.splitlines()):
        if not path.endswith(".md"):
            continue
        text = _git(repo, "show", f"{rev}:./{path}")
        if text is None:
            continue                   # その版で読めない1本は飛ばす
        base_ids.update(cs26_clauses(text)[0])
    now_ids, now_reqs = {}, set()
    for k, d in docs.items():
        if not k.startswith(CS26_LAYER + "/"):
            continue
        ids, reqs = cs26_clauses(d['raw'])
        now_ids.update(ids)
        now_reqs |= reqs
    if not base_ids:
        # **基準の版に条項が1件も無い** = 比べる相手が無い。「違反なし」ではない。
        # 現在の版にも無いなら、古い基準のせいではなく**条項の書き方を読めていない**疑いが先に立つ
        # (課題311 はこの2つを同じ文言で印字していたので、基準の版を新しくすれば直ると読めた)
        if not now_ids:
            return [], (f"基準の版 {rev[:12]} にも現在の版にも {CS26_LAYER} の条項が1件も"
                        "読めない — 要件の見出し `## FR-…-nn` の下の表の1列目に条項 ID を置いて"
                        "いるかを確かめる"), []
        return [], f"基準の版 {rev[:12]} に {CS26_LAYER} の条項が無い", []
    out, moved = [], []
    # **所見の鍵は実際の文書のパスである**(層名だけだと、`/build` §1 と `/verify-docs` §1 の
    # 「クロージャの中だけを見る」という振り分けがどちらも掛からない — 他の CS 検査と同じ形にする)。
    # 消えた条項はいまどの文書にも無いので、その要件を持っている文書を鍵にし、
    # 見つからなければ層の中の最初の文書へ倒す。
    def _where(cid):
        req = base_ids[cid]            # 番地にハイフンが入る(`6-2`)ので、ID を切って推さない
        for k, d in sorted(docs.items()):
            if k.startswith(CS26_LAYER + "/") and req in d['raw']:
                return k
        for k in sorted(docs):
            if k.startswith(CS26_LAYER + "/"):
                return k
        return CS26_LAYER
    for cid in sorted(set(base_ids) - set(now_ids)):
        if base_ids[cid] in now_reqs:
            out.append(("CS26", _where(cid),
                        f"条項 ID「{cid}」が基準の版({rev[:12]})から消えている — "
                        "その要件の見出しは残っているので、番号の振り直しか行ごとの削除である。"
                        "**退役は `種別` に `delete` と書いて行を残す**"
                        "(規範は 01-requirements.md の「条項 ID は不動である」)"))
        else:
            moved.append(cid)
    return out, None, moved


def cs27(repo):
    """採番の一意。**同じ番号が2つの別物に付いていないか**(2026-09-05。D-8)。

    課題票(`docs/issues/NNN-…`)と棚上げ(`docs/pendings.md` の `## P-nnn`)の連番は
    再利用しない約束だが、採番は長く手作業で、並走した2本が同じ番号を採る穴が在った。
    採番そのものは `doc-health.py --next-issue-id / --next-pending-id`(錠の下の払い出し)が
    塞ぐ。**この検査は、それでも起きたとき(手で採った・払い出しを迂回した)に黙って
    通さないための網である。** 参照はグロブで解決されるため、2つ在っても「在る」と
    判定される — 重複はここでしか捕まらない。
    """
    out = []
    issues = repo / "docs/issues"
    seen: dict[str, str] = {}
    for q in sorted(issues.glob("*.md")) if issues.is_dir() else []:
        m = re.match(r"(\d{3})-", q.name)
        if not m:
            continue
        n = m.group(1)
        if n in seen:
            out.append(("CS27", f"docs/issues/{q.name}",
                        f"課題票の番号 {n} が重複({seen[n]} と同じ番号)"))
        else:
            seen[n] = q.name
    pend = repo / "docs/pendings.md"
    if pend.is_file():
        nums: dict[str, int] = {}
        # **コメントの中の書式例(雛形の `## P-001 <一行タイトル>`)を実物と数えない** —
        # 行数を保ったままコメントの中身だけ潰す(doc-health.py の mask_comments と同じ考え方。
        # 2026-09-05 の独立確認: 雛形を残した正常な台帳が「P-001 が重複」になっていた)
        masked = re.sub(r"<!--.*?-->", lambda m: re.sub(r"[^\n]", " ", m.group(0)),
                        pend.read_text(encoding="utf-8"), flags=re.S)
        for i, line in enumerate(masked.splitlines(), 1):
            m = re.match(r"##\s+P-(\d{3})\b", line.strip())
            if m:
                n = m.group(1)
                if n in nums:
                    out.append(("CS27", "docs/pendings.md",
                                f"{i}行: 棚上げの番号 P-{n} が重複({nums[n]}行にも在る)"))
                else:
                    nums[n] = i
    return out


def cs12(repo):
    """同型の走査記録。**「1件見つけた」を「その同型を全件列挙した」に変える。**

    `docs/issues/*.md` に `pattern:` があれば `pattern_survey:`(何を走査して何件だったか)が要る。
    宣言だけして走査していない状態を許すと、同型の残りが次の検証で再浮上する
    (`claude-dev-env` の `043` → `066`。規範は `.claude/directions/issues-pendings.md`)。
    逆向きも見る: **severity 高 は pattern が必須**(issues-pendings.md §3.1。中・低には要求しない)。
    """
    # pattern -> 件数。解消 = ファイル削除(issues-pendings.md)なので、存在する issue は
    # すべて未処理 — `status:` のような frontmatter は規範に存在せず、見に行かない
    out, counts = [], collections.defaultdict(int)
    d = repo / "docs" / "issues"
    if not d.is_dir():
        return out, counts
    for p in sorted(d.glob("*.md")):
        if p.name == "index.md":
            continue
        t = p.read_text(errors="replace")
        if not t.startswith('---'):
            continue
        fm = t.split('---', 2)[1] if len(t.split('---', 2)) > 2 else ""
        g = dict(re.findall(r'^(\w+):[ \t]*(.*)$', fm, re.M))
        cls = g.get('pattern', '').strip()
        # 雛形の placeholder(`<同型のID。…>`)を剥がしていない宣言は、宣言が無いのと同じに
        # 数えると severity 高 の走査義務を素通りする(check-buildrecord の PLACEHOLDER 検出と
        # 同型 — inspection-17 M-12)。placeholder は severity を問わず誤りとして止める。
        if PLACEHOLDER.search(cls):
            out.append(("CS12", f"issues/{p.name}",
                        "pattern が雛形の placeholder のまま(`<…>` を剥がして同型の class 名を"
                        "書く。同型が無いなら `なし` と書く — 高 は class 名と走査記録が必須)"))
            continue
        if not cls or cls == 'なし':
            if g.get('severity', '').strip().strip('`"\'') == '高':
                out.append(("CS12", f"issues/{p.name}",
                            "severity 高 なのに pattern が無い(高 は同型の class 名と走査記録が"
                            "必須 — issues-pendings.md §3.1。走査の結果が自分1件でも、class 名と"
                            "件数を pattern / pattern_survey に書く。中・低には要求しない)"))
            continue
        counts[cls] += 1
        survey = g.get('pattern_survey', '').strip()
        if not survey or PLACEHOLDER.search(survey):
            out.append(("CS12", f"issues/{p.name}",
                        f"同型 `{cls}` を宣言しているのに pattern_survey が空か placeholder のまま"
                        "(何を走査して何件あったかが無い = 全件列挙していない)"))
    return out, counts

# CS20: issue の起点層。**「どの層の問題か」は起票の前に決める**(`.claude/directions/issues-pendings.md` §1)。
# 「03 で見つけた」は**発見場所**であって起点層ではない(それは `found_in:`)。取り違えると
# `/build` が起点層をそのまま引き継ぎ、**下流だけが直って要求は一度も変わらない** —
# 原則3 が防いでいる失敗が issue を経由して戻る。
# 語彙は履歴・issue と同じ4値(新しい語彙を作らない)。
ORIGIN_LAYERS = ("00", "01", "02", "03")


def cs20(repo):
    """issue に起点層が在り、語彙の中の値であること。"""
    out = []
    d = repo / "docs" / "issues"
    if not d.is_dir():
        return out
    for p in sorted(d.glob("*.md")):
        if p.name == "index.md":
            continue
        t = p.read_text(errors="replace")
        parts = t.split('---', 2)
        if not t.startswith('---') or len(parts) <= 2:
            # **frontmatter が無い/閉じていない issue を読み飛ばすと、origin_layer 欠落として
            # 検出されないまま CS20 が OK を出す**(そのまま `/build` に渡ると、起点層不明の
            # issue が症状の層だけを直すタスクになる — この検査が防ごうとしている型そのもの)。
            out.append(("CS20", f"issues/{p.name}",
                        "frontmatter が無い(または `---` が閉じていない)。"
                        "`.claude/templates/issue.md` から作ること"))
            continue
        g = dict(re.findall(r'^(\w+):[ \t]*(.*)$', parts[1], re.M))
        v = g.get('origin_layer', '').strip().strip('`"\'')
        if not v:
            out.append(("CS20", f"issues/{p.name}",
                        "origin_layer が無い(**直しが始まる層**。見つけた場所ではない — "
                        "`.claude/directions/issues-pendings.md` §1)"))
        elif v not in ORIGIN_LAYERS:
            # 雛形の `<00|01|02|03>` を埋め忘れた場合もここに落ちる(それが正しい)
            out.append(("CS20", f"issues/{p.name}",
                        f"origin_layer が語彙の外: {v}(00 / 01 / 02 / 03 のどれか1つ)"))
    return out


# CS21: 件数の主張。**「本文の数字」と「実体の数」を突き合わせる。**
# 実例(いずれも 2026-08-20 の実測。**3件すべて検証済み記録の付いた文書に残っていた** —
# 人間も独立レビューも数を数え直さないからである):
#   1. `02-design/system.md` の summary「7モジュール」に対し実体は8(同文書が「全 8 モジュール」と書く)
#   2. `01-requirements/functional.md` の「回収の契機は4つである」に対し `FR-delivery-04-3` が
#      「この3つの契機」と書く(同じ集合について数が二つある)
#   3. `01-requirements/usecases.md` の summary「UC-01〜UC-08」に対し実体は `UC-01`〜`UC-12`
#
# **開いた形を偽と呼ばない。** 「主要な3つは」「`SR-01〜`」のように全数を主張しない書き方は真である
# (F2 の実測: 00〜02 の summary 20 本のうち、閉じた形で件数を書く2本がどちらも偽で、開いた形の
# 4本は真)。ゆえに拾うのは**閉じた形だけ**である:
#   (a) `全` / `計` の付いた数え上げ(「全 8 モジュール」)
#   (b) 「この N つの…」(直前に挙げたものの全部を指す)
#   (c) 「<名詞>は N つ」(その名詞について全部を述べている)
#   (d) frontmatter の `summary`(文書それ自身の総量を述べる場所)
# **数え上げの対象は名詞だけでは決まらない。** 「予約する条件は2つ」と「`has_more` を立てる条件は
# 6つ」は同じ「条件」でも別の集合である(実測の誤検出2件がこの型)。そこで (c) は直前の修飾語まで
# 見て、修飾語が両方在って違うときは別の集合として扱う。
# **名詞は漢字・カタカナだけ**にする。ひらがなを含めると「モジュールに要件がある」を名詞として
# まとめ、同じ「モジュール」の主張どうしが突き合わせられない(実測)。
# **1 は数えない。**「1モジュールが持つ機能は…」のような分配の言い方が大量に偽の食い違いを作る。
CS21_NOUN = r'[ァ-ヶ一-龥々ー]{2,12}'
# 全数を主張しない語。**行にこれが在れば、その行の主張は開いている**と見る。
CS21_OPEN = ("主要", "代表", "など", "以上", "以下", "最大", "上限", "少なくとも", "例えば",
             "うち", "程度", "ごと", "あたり", "につき")
# 仮定・経過の言い方(「呼び出し元が5本になっても」「3つ目を持ったとき」)。今の数ではない。
CS21_HYPO = ("ても", "たとき", "なら", "場合", "増え", "超え", "目")
CS21_TOTAL = re.compile(rf'(?:全|計)\s*(?P<n>\d+)\s*(?P<noun>{CS21_NOUN})')
CS21_KONO = re.compile(rf'(?:この|その)\s*(?P<n>\d+)\s*[つ個件本]\s*の?\s*(?P<noun>{CS21_NOUN})')
CS21_HA = re.compile(rf'(?P<noun>{CS21_NOUN})\s*(?:は|が)\s*(?P<n>\d+)\s*[つ個件本]')
CS21_BARE = re.compile(rf'(?P<n>\d+)\s*(?P<noun>{CS21_NOUN})')      # summary の中だけで使う
CS21_CLAUSE = re.compile(r'[、。()「」|*`::  \t]')
# ID の範囲の主張(`UC-01〜UC-12` / `FR-ops-01〜04`)。**上限を書かない `SR-01〜` は当たらない**
# (開いた形だからである)。
CS21_RANGE = re.compile(r'(?P<fam>[A-Z][A-Za-z0-9]*(?:-[a-z][a-z0-9]*)*)-0*(?P<lo>\d{1,3})'
                        r'\s*[〜~～]\s*(?:(?P=fam)-)?0*(?P<hi>\d{1,3})(?!\d)')


def cs21_modifier(line: str, start: int) -> str:
    """名詞の直前の修飾語(節の区切りまで)。「予約する条件」と「立てる条件」を分けるために使う。"""
    return CS21_CLAUSE.split(line[max(0, start - 14):start])[-1]


def cs21_claims(line: str, summary: bool = False):
    """行から閉じた形の件数の主張を拾う。返すのは (名詞, 数, 修飾語) である。"""
    found = [(m, "") for pat in (CS21_KONO, CS21_TOTAL) for m in pat.finditer(line)]
    found += [(m, cs21_modifier(line, m.start('noun'))) for m in CS21_HA.finditer(line)]
    if summary:
        found += [(m, "") for m in CS21_BARE.finditer(line)]
    out = []
    for m, mod in found:
        n = int(m.group('n'))
        if n < 2:
            continue
        if any(h in line[m.end():m.end() + 6] for h in CS21_HYPO):
            continue
        out.append((m.group('noun'), n, mod))
    return out


def cs21(docs):
    """件数の主張。**同じ文書の中で、同じものの数が二つ在る**か。ID の範囲の主張が実体に合うか。

    「入っている数字が正しいか」は機械にしか数え直せない — 人間も独立レビューも、書いてある数を
    信じて読む。実例3件はすべて `verified` の付いた文書に残っていた(上のコメント)。
    """
    out = []
    for k, d in docs.items():
        summary = d['fm'].get('summary', '')
        by_noun = collections.defaultdict(list)
        if not any(w in summary for w in CS21_OPEN):
            for noun, n, mod in cs21_claims(summary, summary=True):
                by_noun[noun].append(("summary", n, mod))
        fence = False
        for ln, line in visible_lines(d['body'], d.get('base', 0)):
            if FENCE.match(line):
                fence = not fence
                continue
            if fence or any(w in line for w in CS21_OPEN):
                continue                       # コード例と開いた形は主張ではない
            for noun, n, mod in cs21_claims(line):
                by_noun[noun].append((f"{ln}行", n, mod))
        for noun, items in sorted(by_noun.items()):
            conflict = []
            for i, a in enumerate(items):
                for b in items[i + 1:]:
                    if a[1] == b[1] or (a[2] and b[2] and a[2] != b[2]):
                        continue               # 同じ数、または別の集合について述べている
                    conflict += [a, b]
            if not conflict:
                continue
            seen, uniq = set(), []
            for where, n, _mod in conflict:
                if (where, n) not in seen:
                    seen.add((where, n))
                    uniq.append(f"{where}:{n}")
            nums = "と".join(str(n) for n in sorted({n for _w, n, _m in conflict}))
            out.append(("CS21", k, f"「{noun}」の数が {nums} で食い違う({' / '.join(uniq)})"
                                   " — どちらかが偽である。実体を数え直して直す"))
        # ID の範囲の主張は summary だけを見る。**本文の `UC-03〜05` は「この3件」という
        # 指示であって全数の主張ではない**(実測: 本文まで見ると誤検出が11件出た)。
        for m in CS21_RANGE.finditer(summary):
            fam, lo, hi = m.group('fam'), int(m.group('lo')), int(m.group('hi'))
            if hi <= lo:
                continue
            outside = sorted({int(x.group(1)) for x in
                              re.finditer(re.escape(fam) + r'-0*(\d{1,3})(?!\d)', d['raw'])
                              if not (lo <= int(x.group(1)) <= hi)})
            if outside:
                out.append(("CS21", k, f"summary の「{fam}-{lo:02d}〜{hi:02d}」の外に同じ族の ID が"
                                       f"在る: {', '.join(f'{fam}-{i:02d}' for i in outside)}"
                                       " — summary が実体より狭い"))
    return out


# CS22: E2E 台本(E2E-nn)の置き場。**e2e 鮮度スタンプの失効判定は、02 のうち system.md と
# testing.md しか見ない**(stamps.py の DEPENDS — inspection-16 D3。02 全体を依存に取ると
# 無関係な 02 の修正で E2E suite 全件が失効するため絞った)。台本や言及が他の 02 ファイルへ
# 移ると、その変更が e2e を失効させなくなる(黙って網の外に出る)ので、02-design 内の
# E2E-nn は定義・言及ともこの2ファイルに限る(fail-closed: 言及ごと禁じる方が機械で守れる)。
CS22_ALLOWED = ("02-design/system.md", "02-design/testing.md")
CS22_ID = re.compile(r'\bE2E-\d+\b')


def cs22(docs):
    """02-design 内の E2E-nn は system.md / testing.md にだけ書ける(失効判定の網の内)。"""
    out = []
    for k, d in docs.items():
        if not k.startswith("02-design/") or k in CS22_ALLOWED:
            continue
        for n, line in enumerate(d['raw'].splitlines(), 1):
            if CS22_ID.search(line):
                out.append(("CS22", k, f"{n}行: E2E 台本の ID が固定の置き場の外に在る"
                                       "(定義も言及も system.md / testing.md へ — "
                                       "e2e の失効判定はその2ファイルしか見ない)"))
    return out


# CS23: `e2e_scripts_in` の宣言の裏取り。**`flow-config(.local).json` が
# `e2e_scripts_in: "testing"` と宣言すると、`docs/02-design/system.md` は e2e / qa の
# 失効判定から外れる**(stamps.py — inspection-20 V-4)。宣言は「E2E 台本を testing.md へ
# 切り出し済みである」という主張なので、**system.md に `E2E-nn` が残っていたらその主張は偽**
# であり、台本の在るファイルが黙って網の外へ出る。`stamps.py` 側は `testing.md` の存在までしか
# 見られない(そこが機械の限界だった)ので、中身を見るこの検査がその半分を埋める。
CS23_CONFIG = ".claude/scripts/flow-config.json"
CS23_LOCAL = ".claude/scripts/flow-config.local.json"


def cs23(docs, repo):
    """`e2e_scripts_in: "testing"` と宣言したなら、system.md に E2E-nn が残っていてはならない。"""
    declared = "system"
    for rel in (CS23_LOCAL, CS23_CONFIG):       # local が優先(stamps.py と同じ規則)
        try:
            data = json.loads((repo / rel).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        # **JSON オブジェクトでない設定は「無いもの」として次へ落ちる**(`stamps.py` の
        # `_cfg_json` と同じ倒し方)。`[]` も `null` も文字列も正規の JSON なので
        # ValueError では捕まらず、型を見ないと `.get` が落ちて検査全体が止まる。
        if not isinstance(data, dict):
            continue
        v = data.get("e2e_scripts_in")
        if isinstance(v, str) and v.strip() in ("system", "testing"):
            declared = v.strip()
            break
    # **`stamps.py` の倒し方を逐語で写す**: 切り出し先が無いあいだは宣言そのものを無視する
    # (`e2e_scripts_in()` の fail-closed。`flows.md` §2)。写さないと、正しく安全側へ
    # 倒れている構成をこの検査だけが違反にする。
    if declared != "testing" or "02-design/testing.md" not in docs:
        return []
    d = docs.get("02-design/system.md")
    if d is None:
        return []
    out = []
    for n, line in enumerate(d['raw'].splitlines(), 1):
        if CS22_ID.search(line):
            out.append(("CS23", "02-design/system.md",
                        f"{n}行: `e2e_scripts_in: \"testing\"` と宣言しているのに "
                        "E2E 台本の ID が system.md に残っている — 宣言が偽なら、"
                        "system.md の変更が e2e / qa を失効させなくなる"
                        "(testing.md へ移すか、宣言を戻すこと)"))
    return out


# 検査の一覧。**--list と報告の見出しはここだけを見る**(二重定義を作らない)。
# CS28: 02 の要件カバレッジ表の、**形で判定できる崩れ** ★(2026-09-15。inspection-28 A-15 / B-15)
#
# これまでこの表は「専用の機械検査は無い」と規範自身が明記しており(`02-design.md` の
# 「規則 / 検査主体」の表)、崩れは**次の文書検証まで誰にも見えなかった**。
# 同じ「行が在るか」を、構築の出口・文書検証・試験検証の3か所が人手で読み直してもいた。
#
# **ここで見るのは形だけである** — 中身がその条項を本当に満たすかは、人が読む側に残る:
#
#   (a) `充足` が空でなく、決められた語彙のどれかであること
#       FR/NFR は 完全 / 部分(P-nnn) / 適用外(理由) / -、SR は 満たす / 破れている(ID)。
#   (b) 1つの条項の**主担当行がちょうど1つ**であること(`-` 以外の値を持つ行が1つ)。
#   (c) 01 に在る条項が、この表に**行を1つ以上持つ**こと。
#
# **雛形のままの行は数えない** — `<…>` を含む ID は見本であって宣言ではない。
# **表が無い / 読めないときは何も言わない**(まだ書いていない段階で鳴らさない)。
CS28_ID = re.compile(r'^(FR-[A-Za-z0-9_-]+-\d+-\d+|NFR-[A-Za-z0-9_-]+-\d+|SR-\d+)$')
CS28_HEAD = re.compile(r'要件カバレッジ')
CS28_FR_OK = ("完全", "-")
CS28_SR_OK = ("満たす",)


def cs28_rows(doc: dict):
    """カバレッジ表の行を (条項ID, 充足) で返す。見出しから列を特定する。"""
    rows, in_tbl, cols = [], False, None
    for _n, line in visible_lines(doc['body'], doc.get('base', 0)):
        s = line.strip()
        if s.startswith("#"):
            in_tbl, cols = bool(CS28_HEAD.search(s)), None
            continue
        if not in_tbl or not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if cols is None:
            if any("充足" in c for c in cells):
                cols = {"id": 0, "fit": next(i for i, c in enumerate(cells) if "充足" in c)}
            continue
        if set("".join(cells)) <= set("-: "):      # 区切り行
            continue
        if cols["fit"] >= len(cells):
            continue
        rows.append((cells[0], cells[cols["fit"]]))
    return rows


def cs28(files: dict) -> list:
    out = []
    design = [k for k in files if k.endswith("02-design/system.md")]
    if not design:
        return out
    rows = cs28_rows(files[design[0]])
    # **行が0件でも、ここで戻らない** ★ — 表を丸ごと空にした状態こそ
    # 「01 の条項が1行も無い」が最も効くべき場面である(下の走査へ落とす)。
    seen: dict[str, int] = {}
    for cid, fit in rows:
        if "<" in cid or not CS28_ID.match(cid):
            continue                                   # 雛形の見本・表の外
        is_sr = cid.startswith("SR-")
        # **値は全体で一致させる** ★ — 開き括弧の前だけを見ると、`完全(余計)` や
        # `部分(理由)`(棚上げを指していない)がそのまま通る。
        # 括弧を取る値は、括弧の中身の**形**まで決める:
        #   部分(P-nnn) / 適用外(空でない理由) / 破れている(空でない課題票 ID)
        norm = fit.strip().replace("（", "(").replace("）", ")")
        if is_sr:
            good = (norm == "満たす"
                    or re.fullmatch(r'破れている\(\s*\S[^)]*\)', norm) is not None)
            vocab = "満たす / 破れている(課題票 ID)"
        else:
            good = (norm in ("完全", "-")
                    or re.fullmatch(r'部分\(\s*P-\d{3}\s*\)', norm) is not None
                    or re.fullmatch(r'適用外\(\s*\S[^)]*\)', norm) is not None)
            vocab = "完全 / 部分(P-nnn) / 適用外(理由) / -"
        if not fit:
            out.append(("CS28", design[0], f"{cid} の 充足 が空欄である"))
        elif not good:
            out.append(("CS28", design[0],
                        f"{cid} の 充足「{fit}」が語彙の外である({vocab})"))
        if norm != "-":
            seen[cid] = seen.get(cid, 0) + 1
    listed: dict[str, int] = {}
    for cid, _fit in rows:
        if "<" not in cid and CS28_ID.match(cid):
            listed[cid] = listed.get(cid, 0) + 1
    for cid in sorted(listed):
        n = seen.get(cid, 0)
        if n != 1:
            out.append(("CS28", design[0],
                        f"{cid} の主担当行が {n} 行ある(ちょうど1行であること — "
                        f"`-` 以外の 充足 を持つ行が主担当である)"))
    # `部分(P-nnn)` の参照先が棚上げに実在すること(形で判定できる「参照先の存在」)
    pend = [k for k in files if k.endswith("pendings.md")]
    if pend:
        # **コメントを外してから見る** ★ — 雛形の書式の見本(コメントの中の `## P-001 …`)を
        # 実物と数えると、指していない棚上げが実在扱いになる。
        d = files[pend[0]]
        body = "\n".join(l for _n, l in visible_lines(d["body"], d.get("base", 0)))
        for cid, fit in rows:
            if "<" in cid or not CS28_ID.match(cid):
                continue
            m = re.match(r'部分\s*[(（]\s*(P-\d+)\s*[)）]', fit.strip())
            if m and not re.search(rf'(?m)^#+\s*{re.escape(m.group(1))}\b', body):
                out.append(("CS28", design[0],
                            f"{cid} の 充足 が指す棚上げ {m.group(1)} が pendings.md に無い"))
    declared = {cid for cid, _ in rows if CS28_ID.match(cid) and "<" not in cid}
    for k, d in files.items():
        if "01-requirements/" not in k:
            continue
        text = "\n".join(l for _n, l in visible_lines(d['body'], d.get('base', 0)))
        for m in re.finditer(r'\b(FR-[A-Za-z0-9_-]+-\d+-\d+|NFR-[A-Za-z0-9_-]+-\d+|SR-\d+)\b', text):
            cid = m.group(1)
            if cid not in declared:
                out.append(("CS28", k, f"{cid} が 02 の要件カバレッジ表に1行も無い"))
                declared.add(cid)                      # 同じ ID を何度も言わない
    return out


CHECK_NAMES = {"CS8": "曖昧語・未決点", "CS11": "参照実在", "CS12": "同型の走査記録",
               "CS18": "要件に降りてきた機構", "CS19": "理由の網羅",
               "CS20": "issue の起点層", "CS21": "件数の主張",
               "CS22": "E2E 台本の置き場", "CS23": "e2e_scripts_in の宣言の裏取り",
               "CS24": "分割可否の記載", "CS25": "境界値と異常系の条項",
               "CS26": "条項 ID の消失", "CS27": "採番の一意",
               "CS28": "要件カバレッジ表の形"}


SSOT_LAYERS = ("00-requests", "01-requirements", "02-design", "03-impl")

# 機械の欄(手で保守する文書の中の、道具が丸ごと書く区画)。**中身は検査の対象外である** ★ —
# 手で編集してはならない場所なので、ここで違反を出しても直せる者が居ない
# (ツール生成領域を `load_ssot` が外しているのと同じ理由。違うのは粒度だけで、あちらは
# ファイル、こちらは区画である)。**正しさは `build-facts.py check` が見る**(差分ゼロ)。
# **行数は保つ** — 落とすと以後の違反の行番号が全部ずれる。
# **終端は2つの形を受ける** — 道具名つきと、道具名を持たない旧終端(`build-index.py` の
# docstring と雛形 `templates/03-index.md` が配っているのは後者である)。
_GENERATED_RE = re.compile(
    r"(?s)(<!--\s*BEGIN GENERATED:[^>]*-->)(.*?)(<!--\s*END GENERATED\s*(?::[^>]*)?\s*-->)")


def blank_generated(text):
    """機械の欄の中身を空行に置き換える(印と行数はそのまま残す)。"""
    return _GENERATED_RE.sub(
        lambda m: m.group(1) + "\n" * m.group(2).count("\n") + m.group(3), text)


def load_ssot(docs_root):
    """SSOT 本体を読む。**frontmatter が無くても捨てない** — CS8/CS11 は本文だけで走る。

    **ツール生成領域は除く**(`03-impl/callgraphs/` と `03-impl/feature-graph.md`)。
    どちらもツールの純粋な導出物で、曖昧語の概念が無く、**手で編集してはならない**ので、
    ここで違反を出しても直せる者が居ない。**正しさはどちらも `/verify-impl` が見る**が、
    見る道具は別である: `callgraphs/` は `build-callgraphs.py --check` と
    `callgraph-check.py`、`feature-graph.md` は `cluster-features.py`(再生成と FT1/FT2)。
    `build-index.py` と `doc-health.py` もこれらを外している
    (`doc-health.py` は同じ理由。索引 `index.md` も外す — 原則10 の「生成領域」はこの2つより
    広い。`build-index.py` が `callgraphs/` を外す一次理由は「専用の索引が在る」である)。
    **これが `/verify-docs` §0 の範囲と §1 の分担の宣言の実装側であり、`stamps.py` の
    `EXCLUDES` の根拠でもある** — 4つは同時に動かす。

    **機械の欄も同じ理由で外す**(2026-08-27)。ただし**外すのはファイルではなく区画**である
    — 手で保守する文書の中に在るので、ファイルごと外すと手書きの部分まで検査されなくなる。
    `blank_generated` が中身を空行に置き換え、**行数は保つ**(以後の違反の行番号を守るため)。
    """
    docs, files = {}, []
    for layer in SSOT_LAYERS:
        d = docs_root / layer
        if d.is_dir():
            files += sorted(p for p in d.rglob("*.md")
                            if "callgraphs" not in p.parts and p.name != "feature-graph.md")
    for p in files:
        rel = str(p.relative_to(docs_root))
        t = blank_generated(p.read_text(errors="replace"))
        fm, body = "", t
        if t.startswith('---'):
            parts = t.split('---', 2)
            if len(parts) >= 3:
                fm, body = parts[1], parts[2]
        docs[rel] = {'fm': dict(re.findall(r'^(\w+):[ \t]*(.*)$', fm, re.M)),
                     'body': body, 'raw': t, 'path': p, 'sections': [],
                     'base': fm.count('\n')}
    return docs, files


def main_ssot(root):
    """**仕様ドキュメントの一括検査。** SSOT 全体に、構造に依存しない検査だけを当てる。

    なぜ要るか: AI の読む検査は「その回の対象文書」しか見ない。**SSOT 全体を機械で
    走査する層が無いと、反復のたびに新しい欠陥が出る**(実測済み)。/build §1 がこれを回して
    母集団を凍結し、/verify-docs が検査のたびに回す。

    直す件数は人間が決める(既定は列挙のみ)。列挙を機械が保証し、切る判断は人間が持つ
    — `docs/feedbacks/015` の教訓は「切るな」ではなく「切ったことを人間が知った上で切れ」。
    """
    docs_root = pathlib.Path(root)
    if not docs_root.is_dir():
        print(f"エラー: 対象がディレクトリでない: {root}", file=sys.stderr); return 2
    repo = docs_root.parent
    docs, files = load_ssot(docs_root)
    if not docs:
        print(f"エラー: 対象が0件({root} に {'/'.join(SSOT_LAYERS)} が無い)。"
              f"渡すのは docs のパスである", file=sys.stderr)
        return 2

    # CS8 は 00-requests を対象外にする: 00 の本文は人間の言葉であり AI が直してはならないので、
    # 検査すると「違反を 0 にできない検査」= 恒久的に報告し続ける検査になる(実測済み)。
    # 検査は「違反を 0 にできること」を満たさねばならない。
    E = (cs8({k: v for k, v in docs.items() if not k.startswith("00-requests")})
         + cs11(docs, repo) + cs18(docs) + cs19(docs) + cs21(docs) + cs22(docs)
         + cs23(docs, repo) + cs24(docs) + cs25(docs) + cs28(docs))
    e12, counts = cs12(repo)
    E += e12 + cs20(repo) + cs27(repo)
    e26, cs26_undecided, cs26_moved = cs26(docs, docs_root, repo)
    E += e26

    by = collections.defaultdict(list)
    for code, where, msg in E: by[code].append((where, msg))
    names = CHECK_NAMES

    print(f"## 仕様ドキュメントの一括検査(SSOT 全体): {len(docs)} ファイル")
    print("   **これが母集団である。** /build は構築記録の調査メモに凍結してから着手すること")
    for code, label in names.items():
        v = by.get(code, [])
        if code == "CS26" and cs26_undecided:
            # **「検査していない」を「OK」と印字しない**(このファイル冒頭の fail-closed)
            print(f"  {code} {label}: 未検査 — 判定不能({cs26_undecided})")
            continue
        print(f"  {code} {label}: {'違反 %d 件' % len(v) if v else 'OK'}")
        for where, msg in v:          # **省略しない。** 母集団を数えるための出力である
            print(f"      - {where}: {msg}")
        if code == "CS26" and cs26_moved:
            print("      - 要件まるごとの移行と読める消失 "
                  f"{len(cs26_moved)} 件(**違反ではない**。参照の書き換えが同じ"
                  f"クロージャに在るかは読み手が見る): {' / '.join(cs26_moved)}")
    if counts:
        print("  同型の不具合ごとの件数(解消 = ファイル削除。存在する課題票は未処理):")
        for cls, total in sorted(counts.items()):
            print(f"      - {cls}: {total} 件")
    # **変更相対語は候補として出す。違反には数えない**(上の CHANGE_RELATIVE を参照)。
    cand = []
    for k, d in sorted(docs.items()):
        for n, line in visible_lines(d['body'], d.get('base', 0)):
            for w in CHANGE_RELATIVE:
                if w in line:
                    cand.append((k, n, w, line.strip()[:80]))
    if cand:
        print(f"\n### 変更相対語の候補 {len(cand)} 件(**違反ではない。人間か裁定の記録が除外する**)")
        print("   正当な用法: コードの出力文面の逐語引用 / 日付で固定された改訂記録 / 却下案の記録")
        for k, n, w, text in cand:
            print(f"      - {k}:{n}: 「{w}」 — {text}")
    print("合格: 違反なし" if not E else f"NG 違反 {len(E)} 件")
    return 1 if E else 0


def selftest() -> int:
    """CS21(件数の主張)を、**実測の3件と、実測の誤検出の型**で確かめる。

    検査ロジックの新設なので、**捕まえるべき例と捕まえてはならない例の両方**を持つ。
    3件はどれも `docs/` の実物(2026-08-20 に修正済み)から採った文である — 作った例で
    通しても、実物の書き方に当たるとは言えない。
    """
    import tempfile
    results = []

    def check(name, cond, note=""):
        results.append((name, cond, note))

    def run(rel_and_text) -> list:
        """一時的な SSOT を作って CS21 だけを走らせる。"""
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td) / "docs"
            for rel, text in rel_and_text.items():
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text, encoding="utf-8")
            docs, _files = load_ssot(root)
            return cs21(docs)

    def doc(summary: str, body: str) -> str:
        return f"---\nid: t\nversion: 1.0.0\nsummary: {summary}\n---\n\n{body}\n"

    # (cs27) 採番の一意 — 捕まえる例(重複)と捕まえてはならない例(歯抜けは正常)
    with tempfile.TemporaryDirectory() as td:
        repo = pathlib.Path(td)
        d = repo / "docs/issues"; d.mkdir(parents=True)
        (d / "010-BUG-a.md").write_text("x"); (d / "010-FEAT-b.md").write_text("x")
        (d / "012-BUG-c.md").write_text("x")   # 歯抜け(011 が無い)は違反ではない
        (repo / "docs/pendings.md").write_text("# 棚上げ事項\n\n## P-003 x\n\n## P-003 y\n\n## P-007 z\n")
        got = cs27(repo)
        check("(cs27) 課題票の重複番号を捕まえる", any("010" in m for _, _, m in got))
        check("(cs27) 棚上げの重複番号を捕まえる", any("P-003" in m for _, _, m in got))
        check("(cs27) 歯抜けと一意な番号は違反にしない",
              not any("012" in m or "P-007" in m for _, _, m in got) and len(got) == 2)
        # --- CS28(2026-09-15。inspection-28 A-15 / B-15)
        def _doc(body):
            return {"body": body, "base": 0, "fm": {}}
        tbl = ("## 要件カバレッジ確認\n\n"
               "| 受け入れ基準 ID | 割り当てモジュール | 充足 | 根拠 |\n|---|---|---|---|\n"
               "| FR-a-01-1 | MOD-a | 完全 | DSN-x-01 |\n"
               "| FR-a-01-2 | MOD-a |  | - |\n"
               "| FR-a-01-3 | MOD-a | ばっちり | - |\n"
               "| FR-a-01-4 | MOD-a | 完全 | - |\n"
               "| FR-a-01-4 | MOD-b | 完全 | - |\n"
               "| SR-01 | MOD-a | 満たす | - |\n")
        got = cs28({"02-design/system.md": _doc(tbl),
                    "01-requirements/functional.md": _doc("- FR-a-01-1\n- FR-a-09-1\n")})
        msgs = [m for _, _, m in got]
        check("(cs28) 充足の空欄を捕まえる", any("空欄" in m for m in msgs))
        check("(cs28) 語彙の外の値を捕まえる", any("語彙の外" in m for m in msgs))
        check("(cs28) 主担当が2行を捕まえる", any("主担当行が 2 行" in m for m in msgs))
        check("(cs28) 表に無い条項を捕まえる", any("FR-a-09-1" in m for m in msgs))
        check("(cs28) 正しい行は鳴らさない",
              not any("FR-a-01-1" in m or "SR-01" in m for m in msgs))
        check("(cs28) 雛形の見本を実物と数えない",
              cs28({"02-design/system.md": _doc(
                  "## 要件カバレッジ確認\n\n| 受け入れ基準 ID | 充足 |\n|---|---|\n"
                  "| FR-<domain>-01-1 | <完全> |\n")}) == [])
        check("(cs28) 表が無ければ何も言わない", cs28({"02-design/system.md": _doc("# 設計\n")}) == [])
        tbl2 = ("## 要件カバレッジ確認\n\n"
                "| 受け入れ基準 ID | 充足 |\n|---|---|\n"
                "| FR-a-01-1 | 部分() |\n| FR-a-01-2 | 適用外 |\n"
                "| FR-a-01-3 | 部分(P-009) |\n| SR-01 | 破れている() |\n")
        got2 = [m for _, _, m in cs28({"02-design/system.md": _doc(tbl2),
                                       "pendings.md": _doc("## P-003 x\n")})]
        check("(cs28) 部分の括弧が空なら捕まえる", any("FR-a-01-1" in m and "語彙の外" in m for m in got2))
        check("(cs28) 適用外に理由が無ければ捕まえる", any("FR-a-01-2" in m and "語彙の外" in m for m in got2))
        check("(cs28) 破れているに課題票が無ければ捕まえる", any("SR-01" in m and "語彙の外" in m for m in got2))
        # 全体一致(2026-09-15 の2巡目)— 前だけ見ると素通りした型
        got3 = [m for _, _, m in cs28({"02-design/system.md": _doc(
            "## 要件カバレッジ確認\n\n| ID | 充足 |\n|---|---|\n"
            "| FR-b-01-1 | 完全(余計) |\n| FR-b-01-2 | 部分(理由) |\n"
            "| FR-b-01-3 | 部分(P-1) |\n| SR-02 | 満たす(余計) |\n")})]
        for cid in ("FR-b-01-1", "FR-b-01-2", "FR-b-01-3", "SR-02"):
            check(f"(cs28) 語彙の全体一致: {cid}", any(cid in m and "語彙の外" in m for m in got3))
        # 表が空でも 01 の条項の走査は止めない(2026-09-15 の2巡目)
        check("(cs28) 表が空でも条項の欠落を言う",
              any("FR-c-01-1" in m for _, _, m in cs28({
                  "02-design/system.md": _doc("## 要件カバレッジ確認\n\n| ID | 充足 |\n|---|---|\n"),
                  "01-requirements/functional.md": _doc("- FR-c-01-1\n")})))
        # 棚上げの見本(コメントの中)を実物と数えない(2026-09-15 の2巡目)
        check("(cs28) 棚上げの見本を実物と数えない",
              any("P-001" in m for _, _, m in cs28({
                  "02-design/system.md": _doc("## 要件カバレッジ確認\n\n| ID | 充足 |\n|---|---|\n"
                                              "| FR-d-01-1 | 部分(P-001) |\n"),
                  "pendings.md": _doc("<!-- 書式:\n## P-001 <タイトル>\n-->\n")})))
        # 主担当0行(2026-09-15 の2巡目)
        check("(cs28) 主担当が0行でも捕まえる",
              any("0 行" in m for _, _, m in cs28({"02-design/system.md": _doc(
                  "## 要件カバレッジ確認\n\n| ID | 充足 |\n|---|---|\n| FR-e-01-1 | - |\n")})))
        check("(cs28) 指す棚上げが無ければ捕まえる", any("P-009" in m for m in got2))
        check("(cs28) 実在する棚上げなら鳴らさない",
              not any("P-003" in m for _, _, m in cs28({
                  "02-design/system.md": _doc("## 要件カバレッジ確認\n\n| ID | 充足 |\n|---|---|\n"
                                              "| FR-a-01-1 | 部分(P-003) |\n"),
                  "pendings.md": _doc("## P-003 x\n")})))
        # 雛形のコメントの中の書式例は実物ではない(独立確認 2026-09-05)
        (repo / "docs/pendings.md").write_text(
            "<!-- 書式:\n## P-001 <一行タイトル>\n- 決めた日: <YYYY-MM-DD>\n-->\n"
            "# 棚上げ事項\n\n## P-001 本物はこの1件だけ\n")
        for q in (repo / "docs/issues").glob("010-*.md"): q.unlink()
        check("(cs27) コメントの中の書式例を実物と数えない", cs27(repo) == [], str(cs27(repo)))

    # (a) summary の閉じた件数 ⇄ 本文の実体(02-design/system.md:10 の実例)
    a = run({"02-design/system.md": doc(
        "colabtmux のモジュール分割(7モジュール)・テスト戦略・E2Eシナリオ一覧",
        "**モジュールに要件が無いもの**: なし(全 8 モジュールに要件がある)。")})
    check("(a) summary「7モジュール」と本文「全 8 モジュール」の食い違いを捕まえる",
          len(a) == 1 and "モジュール" in a[0][2], str(a))

    # (b) 本文どうしの食い違い(01-requirements/functional.md の実例)
    b = run({"01-requirements/functional.md": doc(
        "colabtmux の機能要件",
        "  **回収の契機は4つである** — 明示的な回収の要求、掲示板を触る操作、\n"
        "| FR-delivery-04-3 | 正常系 | この3つの契機により、利用者が何も操作しなくても満たす |")})
    check("(b)「契機は4つ」と「この3つの契機」の食い違いを捕まえる",
          len(b) == 1 and "契機" in b[0][2], str(b))

    # (c) summary の ID 範囲 ⇄ 実体(01-requirements/usecases.md:9 の実例)
    c = run({"01-requirements/usecases.md": doc(
        "colabtmux のユースケース(UC-01〜UC-08)",
        "## UC-09 起動\n## UC-10 撤収\n## UC-11 監視\n## UC-12 知らせ\n")})
    check("(c) summary「UC-01〜UC-08」の外の UC を捕まえる",
          len(c) == 1 and "UC-12" in c[0][2], str(c))
    check("(c) 範囲が実体を覆っていれば黙る",
          not run({"01-requirements/usecases.md": doc(
              "ユースケース(11 件。UC-01〜UC-12 のうち UC-07 は欠番)",
              "## UC-01\n## UC-12\n")}), "")

    # (d) **開いた形を偽と呼ばない**(F2 の実測: 開いた形の4本はどれも真だった)
    check("(d) 開いた形「主要な3つは」は違反にしない",
          not run({"02-design/system.md": doc(
              "設計", "主要な3つは表に挙げる。全 8 モジュールに要件がある。")}), "")
    check("(d) 上限を書かない範囲「SR-01〜」は違反にしない",
          not run({"01-requirements/system.md": doc(
              "システム要件(SR-01〜)", "## SR-30\n## SR-35\n")}), "")

    # (e) **同じ名詞でも別の集合なら食い違いではない**(実測の誤検出2件がこの型)
    check("(e) 修飾語が違う「予約する条件は2つ」と「立てる条件は6つ」は違反にしない",
          not run({"03-impl/relations/MODULE-a.md": doc(
              "機能", "**予約する条件は2つあり**、どちらかで予約する。\n"
                      "**`has_more` を立てる条件は6つあり**、いずれかで `true` になる。")}), "")

    # (f) 分配の言い方(「1モジュールが持つ機能は…」)と仮定の言い方は今の数ではない
    check("(f)「1モジュール」の分配は違反にしない",
          not run({"02-design/system.md": doc(
              "設計", "**1モジュールが持つ機能は 15 本を上限とする**。全 8 モジュールに要件がある。")}), "")
    check("(f)「5本になっても」の仮定は違反にしない",
          not run({"03-impl/relations/MODULE-b.md": doc(
              "機能", "呼び出し元が6本になり、②の契機では3回呼ばれる。\n"
                      "呼び出し元が5本になっても分岐を1つも持たない。")}), "")

    # (g) コード例の中の数字は主張ではない
    check("(g) コードフェンスの中は見ない",
          not run({"02-design/system.md": doc(
              "設計", "全 8 モジュールに要件がある。\n```\n全 3 モジュールを起動する\n```\n")}), "")

    # (h) 本文の `UC-03〜05` は「この3件」の指示であって全数の主張ではない
    check("(h) 本文の ID 範囲は違反にしない",
          not run({"01-requirements/usecases.md": doc(
              "ユースケース", "| UC-03〜05 | 配信 |\n## UC-01\n## UC-12\n")}), "")

    # (i) CS22: E2E-nn は 02 の固定の置き場(system.md / testing.md)の外に書けない
    def run22(rel_and_text) -> list:
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td) / "docs"
            for rel, text in rel_and_text.items():
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text, encoding="utf-8")
            docs, _files = load_ssot(root)
            return cs22(docs)

    check("(i) CS22: architecture.md の E2E-nn は違反",
          bool(run22({"02-design/architecture.md": doc("設計", "E2E-03 を参照。")})), "")
    check("(i) CS22: system.md / testing.md の E2E-nn は違反にしない",
          not run22({"02-design/system.md": doc("設計", "## E2E-01\n手順。"),
                     "02-design/testing.md": doc("テスト", "## E2E-02\n手順。"),
                     "03-impl/tests/e2e.md": doc("試験", "E2E-01 は green。")}), "")

    # (j) CS23: e2e_scripts_in の宣言の裏取り(inspection-20 の裁定)
    def run23(declared, system_text, with_testing=True) -> list:
        with tempfile.TemporaryDirectory() as td:
            repo = pathlib.Path(td)
            cfg = repo / ".claude/scripts"
            cfg.mkdir(parents=True, exist_ok=True)
            body = {"e2e_scripts_in": declared} if declared else {}
            (cfg / "flow-config.json").write_text(json.dumps(body), encoding="utf-8")
            root = repo / "docs"
            tree = {"02-design/system.md": doc("設計", system_text)}
            if with_testing:
                tree["02-design/testing.md"] = doc("テスト", "## E2E-02\n手順。")
            for rel, text in tree.items():
                pth = root / rel
                pth.parent.mkdir(parents=True, exist_ok=True)
                pth.write_text(text, encoding="utf-8")
            docs, _files = load_ssot(root)
            return cs23(docs, repo)

    check("(j) CS23: testing 宣言なのに system.md に E2E-nn が残っていたら違反",
          bool(run23("testing", "## E2E-01\n手順。")), "")
    check("(j) CS23: testing 宣言で system.md に E2E-nn が無ければ違反にしない",
          not run23("testing", "モジュール分割の散文。"), "")
    check("(j) CS23: 宣言が system(既定)なら system.md の E2E-nn は違反にしない",
          not run23("system", "## E2E-01\n手順。")
          and not run23(None, "## E2E-01\n手順。"), "")
    check("(j) CS23: testing.md が無いときは宣言を無視する(stamps.py と同じ倒し方)",
          not run23("testing", "## E2E-01\n手順。", with_testing=False), "")

    # (k) CS23: JSON オブジェクトでない設定で落ちない(local を飛ばして本体へ落ちる)
    def run23_raw(local_raw, config_body, system_text) -> list:
        with tempfile.TemporaryDirectory() as td:
            repo = pathlib.Path(td)
            cfg = repo / ".claude/scripts"
            cfg.mkdir(parents=True, exist_ok=True)
            if local_raw is not None:
                (cfg / "flow-config.local.json").write_text(local_raw, encoding="utf-8")
            (cfg / "flow-config.json").write_text(json.dumps(config_body), encoding="utf-8")
            root = repo / "docs"
            for rel, text in {"02-design/system.md": doc("設計", system_text),
                              "02-design/testing.md": doc("テスト", "## E2E-02\n手順。")}.items():
                pth = root / rel
                pth.parent.mkdir(parents=True, exist_ok=True)
                pth.write_text(text, encoding="utf-8")
            docs, _files = load_ssot(root)
            return cs23(docs, repo)

    check("(k) CS23: local が JSON オブジェクトでなくても落ちず、本体へ落ちる",
          bool(run23_raw("[]", {"e2e_scripts_in": "testing"}, "## E2E-01\n手順。"))
          and bool(run23_raw("null", {"e2e_scripts_in": "testing"}, "## E2E-01\n手順。"))
          and bool(run23_raw('"testing"', {"e2e_scripts_in": "testing"}, "## E2E-01\n手順。"))
          and not run23_raw("[]", {"e2e_scripts_in": "system"}, "## E2E-01\n手順。"), "")
    check("(k) CS23: 壊れた JSON の local も同じく飛ばす",
          bool(run23_raw("{", {"e2e_scripts_in": "testing"}, "## E2E-01\n手順。")), "")

    # (l) CS19: 見出しの深さは対象ごとに違う(REST 契約の「設計判断」は `###`)
    def run19(rel_and_text) -> list:
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td) / "docs"
            for rel, text in rel_and_text.items():
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text, encoding="utf-8")
            docs, _files = load_ssot(root)
            return cs19(docs)

    check("(l) CS19: REST 契約の `### 設計判断` を「節が無い」と言わない",
          not run19({"02-design/contracts/order.md": doc(
              "契約", "## OpenAPI に書けないこと\n\n### 設計判断\n\n"
                      "#### DSN-order-01 期限\n\n- 判断: 期限は締切で切る\n")}), "")
    check("(l) CS19: 契約に「設計判断」が無ければ捕まえる",
          bool(run19({"02-design/contracts/order.md": doc(
              "契約", "## OpenAPI に書けないこと\n\n### 認可の考え方\n\n境界で切る。\n")})), "")
    check("(l) CS19: contracts/index.md は生成物なので見ない",
          not run19({"02-design/contracts/index.md": doc("索引", "## 一覧\n\n- なし\n")}), "")
    check("(l) CS19: logging.md の `## 設計判断` を見る",
          bool(run19({"02-design/logging.md": doc("ログ", "## ログレベル\n\n- INFO\n")}))
          and not run19({"02-design/logging.md": doc(
              "ログ", "## 設計判断\n\n### DSN-log-01 保存期間\n\n- 判断: 90日\n")}), "")
    check("(l) CS19: 雛形の骨だけ(深い見出し + 空の判断・理由)は「空」と数える",
          any("空" in msg for _c, _k, msg in run19({"02-design/logging.md": doc(
              "ログ", "## 設計判断\n\n### DSN-log-01 <タイトル>\n\n- 判断: <>\n- 理由: <>\n")})), "")
    check("(l) CS19: 隣の節を理由と読み違えない",
          any("設計判断" in msg for _c, _k, msg in run19({"02-design/contracts/order.md": doc(
              "契約", "### 設計判断\n\n### 認可の考え方\n\n境界で切る。\n")})), "")

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
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__); sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        sys.exit(selftest())
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        for code, label in CHECK_NAMES.items():
            print(f"{code}: {label}")
        sys.exit(0)
    sys.exit(main_ssot(sys.argv[1] if len(sys.argv) > 1 else "docs"))
