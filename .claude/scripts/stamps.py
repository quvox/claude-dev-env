#!/usr/bin/env python3
"""鮮度スタンプ(`.claude/state/stamps.json`)の記録と、デプロイゲートの判定。

`.claude/state/stamps.json` は **git で共有する**(2026-08-22 の人間の指示)。記録の中身は
`{flow, scope, commit, at, verdict}` で、**どれも中身から決まる値であり、判定の手続きも
`git diff` と `git status` だけである** — つまり最初から「どこでも同じ答えが出る形」をしている。
git の外に置けば、**検証が通った状態からコードが変わっていないかを、その1か所でしか
確かめられない**。追跡すると record 毎にツリーが汚れるが、それは**1周につき1回の専用コミット**と
**明示のパスでの stage とコミット**(`git add -A` を使わない)で消える。`.claude/state/` はどのフローの
依存集合(DEPENDS)にも入っていないので、**このコミットがどの鮮度スタンプも失効させることはない**。
**記録の後にその作業のコミットを amend / rebase / squash してはならない** — 焼き込んだ commit が
履歴から消えると、下の判定は「判定不能」を返す。規範: `.claude/directions/flows.md` §2。

各 verify 系フロー(F2 `/verify-docs`・F3 `/verify-impl`・F4 `/verify-tests`)は完走時に
{flow, scope, commit, 時刻, 判定} を記録する。**デプロイ/リリースのデプロイゲートは
「verify 系の鮮度スタンプがすべて現在の状態に対して green」と機械的に定義する**(及第ライン —
規範: CLAUDE.md §4 / .claude/directions/flows.md §2)。

「現在の状態に対して green」の判定:
  **鮮度スタンプ以降に変わったファイル(未コミット・未追跡を含む)が
  その (flow, scope) の依存集合に掛からない**なら green。commit == HEAD でも早道は無い —
  同一 HEAD 上の未コミット変更を見逃す fail-open になるからである(inspection-16 H-2)。
  例外が2つ: **管理欄だけの変更と、機械の欄の中身だけの変更は失効を作らない**
  (`machine_owned_only` — 管理欄は frontmatter の
  `updated:` 行・`verified:` ブロック、そして**両側が正しい形の `version:` をちょうど1行
  持つときに限り**その `version:` 行)。F2 の証明書書込みが F3 を毎周失効
  させる構造を消すためである(inspection-16 D2)。**`version:` 行そのものを管理欄に入れたのは
  2026-08-25 の人間の裁定であり、D2 が PATCH までで引いていた線を引き直している。**
  **失効を決めるのは中身であって、版の札ではない** ★ — 本文と管理欄以外の frontmatter が
  動いていないなら、`version:` が MINOR / MAJOR へ繰り上がっていても失効させない
  (frontmatter は行に分けてから比べるので、**行の区切り方の違いは見ない**。本文はバイトで比べる)。
  「MINOR = 意味が動いた」は中身についての宣言であり、中身が動いていないならその宣言は偽で
  ある。事実と自己申告が食い違うときは事実を採る(CLAUDE.md 原則2)。中身が動いていれば版が
  据え置きでも失効するので、これは穴ではない(実測 2026-08-25: 証明書を打ち直すだけの run が
  本文無変更のまま MINOR を上げ、その1本だけで相手フローの鮮度スタンプが死んでいた)。
  **版の行が消えた・壊れた・重複した側では、版を本文と同じに扱って失効させる** —
  さもないと `version:` を消す変更が管理欄扱いになる(独立レビュー 2026-08-25 の所見1)。
  試験区分ごとのコードの置き場は `scope_roots` で宣言でき、宣言した試験区分はその置き場に
  掛からない変更では失効しない(**未宣言は広いほうへ倒す**: qa は `ui_roots`、それ以外は
  `code_roots` 全体 — 過大近似 = 安全側。inspection-21 V-9)。試験区分の中は当面 suite 丸ごと
  のままである(どの試験がどのパスを覆うかは機械で言えない)。
  もう1つの失効源は **宣言の変更**: コードの置き場(`code_roots`)を書く設定ファイルは
  **どのフローの依存集合にも入っていない**ので、動いても差分は失効を作らない。だから
  鮮度スタンプに記録時の宣言を焼き込み、現在の宣言と違えば失効にする —
  見る範囲を変えたら見直す(inspection-16 D8。焼き込み前の古い記録は比較せず、次の record で付く)。掛かるなら、そのパスを
  **その最後の変更以後に覆った green** が在るかを見る(部分再検証。`record --covers`)。
  1本でも覆えないパスが残れば「失効」であり、**見ていない範囲を green とは言わない**。
  **覆い切ったら基準点をその commit へ進めて部分を畳む**(`record` の covers 分岐)—
  併合が green = その commit に対する green なので主張は広がらず、畳まないと覆う義務の
  集合が単調に増え続け、互いの依存へ書く F2 と F3 が交互に回しても閉じなくなる。
  依存集合(`DEPENDS`)は**許可リスト**である: 宣言したものが動いたときだけ失効し、
  宣言していないものは何が動いても失効させない。コード側の置き場だけは
  プロジェクトごとに違うので flow-config(.local).json の `code_roots` が正であり、
  **未宣言ならデプロイゲートは red**(fail-closed)。qa 試験区分のコード依存だけは `ui_roots`
  (UI に関わるコードの置き場)が正で、**未宣言なら code_roots 全体へ倒す**(過大近似 =
  安全側。inspection-17 判断5 — バックエンドだけの変更で探索的ブラウザQAを失効させないための宣言)。
  同梱物(`externals/` 等)の正しさは失効判定ではなく**テスト**が担保する。
  **コードの置き場の中に在るが検証の入力ではないもの**は `code_excludes` で外せる
  (2026-08-22 の人間の指示。既定は空 = 今までどおり。**狭く誤ると穴になる**ので迷ったら書かない。
  どの置き場より真に狭い項目だけを受け付ける — 外のパスも、置き場の親も、置き場と等しいものも
  落とす(等しいものを通すと、その置き場ごと失効判定が死ぬ)。宣言は鮮度スタンプへ
  焼き込み、**欄を持たない古い記録も既定=空と読んで比べる**ので、後から足した宣言も取りこぼさない)。**宣言が無いせいで広い範囲で判定している試験区分は、
  `check` と `deps` がそう言う**(判定は変えない — 見えなければ、余分な失効を
  払い続けていることに誰も気づけない)。
  許可リストからの**除外**(`EXCLUDES`)は2件である。どちらも「見ないと宣言した場所は、
  動いても検証結果を古くしない」という同じ根拠に立つ: (1) F2 は 03-impl のうち
  **ツール生成領域(`callgraphs/` と `feature-graph.md`)の中身を検査しない**と分担で
  宣言しているので、そこが動いても F2 を失効させない(inspection-20 V-2)。
  (2) F2 は **残務(`docs/residual.md`)を検査の対象にしない** — そこは検証フローが
  所見を書き出す先であって、読み比べる対象ではない。数えていたころは、**F2 自身を含む
  どの検証フローも、残務に1行足しただけで F2 を失効させ**、同じ検証の周の中で F2 を
  もう1本払っていた(2026-08-26 の実測。`flows.md` §2)。
  E2E 台本を `testing.md` へ切り出したプロジェクトは `e2e_scripts_in: "testing"` を宣言でき、
  そのとき e2e / qa の依存から `system.md` が外れる(同 V-4。未宣言は安全側の `"system"`)。

**素の red は「最終 green の基準点」を消さない**(inspection-17 判断4)。latest とは別に
`last_green` を保持し、部分スタンプも red では捨てない。増分の範囲(「最終 green 以降の差分」)
と `check` の範囲印字は last_green を基準にする — red を記録した次の run が全数化しないため。
デプロイゲートは今までどおり latest を見る(red のまま出荷はできない)。red の解消は、その範囲を増分で
回してから**素の green** で閉じる(未変更部は last_green が保証している — --covers では
latest が red のまま残る)。

**critical: true の awaiting-verify 記録が在るあいだ、F2/F3 の green は `--lens <名前>` 必須**
(inspection-17 判断9)。CLAUDE.md §6 の「critical は独立レビュー必須」を記録の口で確かめる —
防げるのは忘れと依頼の不達であり、申告の嘘は防げない(それはレポートと朝の人間が見る)。

F4 は試験区分別に記録する(unit / integration / e2e / qa)。引数なしの `/verify-tests` は
全部実施なので全試験区分を一度に記録する。**デプロイゲートは flow-config.json の `f4_scopes`
に載る全試験区分の green を要求する**(UI の無いプロジェクトは local 設定で `qa` を外す —
それは「見ない」という決定なので、外すなら記録に残すこと。**受理する縮小はこの qa 外しだけ**:
それ以外の f4_scopes は無視して既定の全試験区分を要求する — fail-closed。inspection-16 H-5)。

**green の記録は、その依存(部分記録なら覆い)に未コミットの変更が無いときだけ通る。**
失効判定は未コミット・未追跡も見るので(`changed_since`)、汚れたまま記録した green は
書いた瞬間に失効している。**それを許すと「回したのにデプロイゲートが閉じない」だけが残る**ので、
`record` が拒む(red はいつでも記録できる — red は green の主張ではない)。

`record --full` は「全数(`all`)を回した」ことだけを別に記録する(**F2/F3 のみ** — F4 は
毎回が suite 丸ごと=全数であり、全数でしか回らない検査も無いので、印を持たない。
inspection-16 D1)。**これはデプロイゲートにも失効判定にも
1バイトも効かない** — 増分と全数を区別しないという設計は変えていない。記録する理由は、
**増分では回らない検査が在る**(用語の例が埋まっているかの点検・決定の見直す条件の発火 — 規範: flows.md §2.1)ので、
最後に全数が回った日が見えないと「一度も回さないまま green」に気づけないからである。

`check` は**複合のデプロイゲート**である(監査 inspection-14 #1)。鮮度スタンプだけでなく、
及第ラインを支える他の状態も読む — どれか1つでも欠けると red:
  (a) verify 系の全体の鮮度スタンプが現在の状態に対して green
  (b) `state: building` / `awaiting-verify` の構築記録がゼロ
      (building はまだ作業が終わっていないもの、awaiting-verify は作業は終わったが
       `promote` がまだ確認していないもの)
  (c) docs/sheets/ が空(未回答の人間への問いを抱えたままデプロイしない)
  (d) `type: bug` **かつ** `severity: 高` の課題票がゼロ(リリースの完了定義の3項目目の機械近似)
      **かつ である。** or にすると `severity: 中` の bug が1件でも在るだけで出荷できなくなり、
      「不具合ゼロではない」と明言している及第ラインを不具合ゼロへ戻してしまう
      (規範: flows.md §2。inspection-19 D-2 の裁定 2026-08-21)。
      `severity: 高` の定義は「`AC-nn` が実システムに対して落ちる」を含むので、
      完了定義の3項目目「受け入れシナリオを阻害する不具合」の近似としては and のほうが近い

`promote` は awaiting-verify の構築記録を verified へ遷移させる唯一の道である
(スキルは手で state を書き換えない): フローごとに「全体スタンプ以降、**その記録の commit
まで**に動いた依存」を出し、1本ずつ覆う green が在るときだけ遷移する。動いた依存がゼロなら
その記録はそのフローの判断を動かしていないので満たしている。**記録が鮮度スタンプの祖先なら
区間は空**(全体スタンプがその記録を含めて検証している — 通常経路はこちら)。

使い方:
    python3 .claude/scripts/stamps.py record <flow> <green|red> [--scope <s>]... \
                                             [--covers <path>]...   # 部分再検証
                                             [--full]               # 全数(all)を回した
                                             [--lens <名前>]        # 走った独立レビュー(critical 時の F2/F3 green に必須)
    python3 .claude/scripts/stamps.py check              # 複合のデプロイゲートの判定
    python3 .claude/scripts/stamps.py promote            # 検証が揃った記録を verified へ
    python3 .claude/scripts/stamps.py show               # 一覧(部分スタンプも出す)
    python3 .claude/scripts/stamps.py deps [<flow>[:<scope>]]   # 依存集合を印字
    python3 .claude/scripts/stamps.py release            # リリースを1件記録する(版は機械が決める)
    python3 .claude/scripts/stamps.py release --current  # いまの成果物の版を印字(組み立てが読む)
    python3 .claude/scripts/stamps.py --selftest

    <flow> は verify-docs / verify-impl / verify-tests。
    verify-tests は --scope 必須(全部実施したなら f4_scopes の全試験区分を並べる)。

終了コード: 0=green(record/show/promote は実行できれば0) 1=デプロイゲート red 2=使い方・解析エラー
"""

from __future__ import annotations

import contextlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import fcntl                      # 状態ファイルの排他(POSIX のみ。無ければ排他なしで動く)
except ImportError:                   # pragma: no cover
    fcntl = None

STATE = Path(".claude/state/stamps.json")
CONFIG = Path(".claude/scripts/flow-config.json")
LOCAL = Path(".claude/scripts/flow-config.local.json")
FLOWS = ("verify-docs", "verify-impl", "verify-tests")
DEFAULT_F4_SCOPES = ["unit", "integration", "e2e", "qa"]

# ---- 依存集合(許可リスト)★ -------------------------------------------------
# **宣言されたものが動いたときだけ失効する。宣言していないものは、何が動いても失効させない。**
# 除外リスト(「これ以外は全部対象」)を止めた理由は実測である: 検証の入力ではないファイルの
# 差分で全試験区分が失効し、無関係な再検証を強いた(人間の指示 2026-08-20 —
# 「なんどもいうが、externalsは無視しろ。。.gitignoreでredになるのはやめてくれ。
#   それで全部やり直しとかあり得ない。」)。**個別の除外規則は書かない** — ここに載らない
# ものの正しさは、失効判定ではなくテスト(ビルド・結合・E2E)が動かして確かめる。
# キット(`.claude/` と ルート直下の `CLAUDE.md` / `AGENTS.md`)はどのフローの依存でもないので、
# 許可リストにした時点で自動的に失効させない(旧 _BOOKKEEPING の個別除外は不要になった)。
#
# 粒度は **(flow, scope)**。キーは flow 名、または "flow:scope"(scope 付きが在ればそれが優先)。
# 文書側の依存はキットが持つ(どのプロジェクトでも同じ場所に在るため)。
# コード側は置き場がプロジェクトごとに違うので `<code>` トークンにし、
# flow-config(.local).json の `code_roots` が正である。**未宣言ならデプロイゲートは red**(fail-closed)。
CODE = "<code>"
UI = "<ui>"                # qa 用のコード依存。ui_roots が正、未宣言なら code_roots 全体(安全側)
DEPENDS: dict[str, tuple[str, ...]] = {
    # F2 は SSOT の内部整合 + 人間の入口 + 残務 + issue の索引。**コードには依存しない**。
    # ONBOARDING.md は載せない: 作り手がキットのどこにも居ない幽霊だった(inspection-16 D9)。
    "verify-docs": ("docs/00-requests/", "docs/01-requirements/", "docs/02-design/",
                    "docs/03-impl/", "docs/README.md",
                    "docs/pendings.md", "docs/residual.md", "docs/issues/index.md"),
    # F3 は コード ⇄ 03 ⇄ 02。比べる3辺そのものなので、ここが広いのは正当である。
    "verify-impl": (CODE, "docs/02-design/", "docs/03-impl/"),
    # F4 unit/integration は コード + テストコード(どちらも code_roots)だけに依存する。
    # 03 の試験表(docs/03-impl/tests/)は suite の結果を1バイトも変えない文書なので依存に
    # 数えない — 数えると「F4 が表の陳腐化を見つける → F3 が直す → コード不変のまま全 suite
    # 失効」という設計内ループになる(inspection-17 判断6。表の整合は F2 の網が見る)。
    "verify-tests:unit": (CODE,),
    "verify-tests:integration": (CODE,),
    # e2e は台本(02 の E2E-nn — 置き場は system.md、切り出し後は testing.md。固定の外に
    # 出た E2E-nn は check-ssot.py の CS22 が違反にする)・実行コマンド(environments)・
    # 受け入れシナリオに依存する。02 全体を取らないのは、無関係な 02 の修正で suite 全件が失効する
    # 増幅を消すため(inspection-16 D3)。03 側も同じ理由で `tests/` 全体ではなく e2e.md
    # 1本に絞る — `tests/<module>.md` の状態列を F3 が直すたびに最も高価な E2E suite が
    # コード不変のまま失効するのは、判断6 が unit/integration で消したループそのものである
    # (inspection-19 V-1)。
    "verify-tests:e2e": (CODE, "docs/03-impl/tests/e2e.md", "docs/02-design/system.md",
                         "docs/02-design/testing.md", "docs/02-design/environments.md",
                         "docs/00-requests/acceptances.md"),
    # qa のコード依存は ui_roots(UI に関わるコードの置き場)が正 — 未宣言なら code_roots
    # 全体(過大近似 = 安全側)。02 依存も D3 と同じ手で絞る: 「適用外(UI 無し)」の宣言も、
    # 実行環境と宛先 allowlist も environments.md に在る(02-design.md の
    # 「ブラウザQAの宛先 allowlist」が所有する)。system.md は E2E 台本のため(inspection-17 判断5 —
    # logging.md の散文修正で探索的ブラウザQAが失効する増幅を消す)。
    # docs/ux/(UX 文書)は qa だけの依存である(2026-08-28)。UX 文書は文書検証・実装整合
    # 検証の依存の外に居るので(directions/ux.md §0)、ここに足さないと、実画面と食い違う内容へ
    # 書き換えてもどの検査も鳴らずに出荷できてしまう。失効は周回末の @qa(qa 試験区分の run)が
    # 実画面との突き合わせで戻す。
    "verify-tests:qa": (UI, "docs/ux/", "docs/02-design/system.md",
                        "docs/02-design/environments.md",
                        "docs/00-requests/acceptances.md"),
    # 試験区分別の行が無い verify-tests(将来試験区分が増えたとき)の受け皿。
    "verify-tests": (CODE, "docs/03-impl/tests/"),
}

# 依存から差し引くもの(除外)。**許可リストの中に在るが、そのフローの検査対象ではない領域**。
# 個別の除外規則を書かないという方針(上)の唯一の例外であり、根拠は「見ないと宣言している
# 場所は、動いても検証結果を古くしない」— 分担の宣言そのものである。
EXCLUDES: dict[str, tuple[str, ...]] = {
    # F2 は 03-impl のうち **ツール生成領域の中身を検査しない**(分担の宣言:
    # `/verify-docs` §1 — そこは F3 の領分である)。依存に数えていたので、F3 がコードの
    # 変更を機械的に転記しただけの run でも F2 が失効し、毎周の覆い直しの run を払っていた
    # (inspection-20 V-2)。逆方向(F2 の管理欄の書込みが F3 を殺す)は machine_owned_only が
    # 既に塞いでいる。2026-08-20 の実測損失の原因は `tests/e2e.md`(AI が書く文書)であり、
    # この除外はそれを再導入しない。
    # F2 は **残務(`docs/residual.md`)を検査の対象にしない**。そこは 3チャネルの
    # 「キュー」の出口であり、F2 自身も他の検証フローも所見を1行足す。依存に数えていたので、
    # 残務へ1行書いた run が F2 を失効させ、同じ検証の周の中で F2 をもう1本払っていた
    # (2026-08-26 の実測)。**残務の行の中身は `doc-health.py` と `check-backlog.py` が見る**
    # ので、除外しても見る者が居なくなるわけではない。
    "verify-docs": ("docs/03-impl/callgraphs/", "docs/03-impl/feature-graph.md",
                    "docs/residual.md"),
}


def dep_excludes(root: Path, flow: str, scope: str | None) -> tuple[str, ...]:
    """この (flow, scope) の依存から差し引く接頭辞。

    2つの出どころが在る: **キットが決める分担の宣言**(`EXCLUDES`)と、
    **プロジェクトが宣言した「検証の入力ではないパス」**(`code_excludes`)。
    後者はコードに依存するフローにだけ効く — 文書側の依存はキットが持っており、
    プロジェクトが黙って外してよいものではない。"""
    out = list(EXCLUDES.get(dep_key(flow, scope), ()))
    rules = DEPENDS.get(dep_key(flow, scope), ())
    if CODE in rules or UI in rules:
        out.extend(code_excludes(root))
    return tuple(out)


def e2e_scripts_in(root: Path) -> str:
    """E2E 台本(`E2E-nn`)の置き場の宣言。`"system"`(既定)か `"testing"`。

    切り出しの済んだプロジェクトだけが `"testing"` を宣言でき、そのとき
    `docs/02-design/system.md` は e2e / qa の依存から外れ、代わりに `testing.md` が入る。
    モジュール分割定義の散文を直しただけの `/build` で最も高価な E2E suite 全件と
    探索的ブラウザQA が失効する過大近似を消すためである(inspection-20 V-4)。
    **未宣言・不正値はすべて `"system"` へ倒す**(過大近似 = 安全側)。
    **`docs/02-design/testing.md` が存在しないときも `"system"` へ倒す** — 切り出しの済んで
    いないプロジェクトが誤って宣言しても、台本の在る `system.md` が依存から静かに落ちない。
    """
    for rel in (LOCAL, CONFIG):        # local が優先(code_roots と同じ規則)
        data = _cfg_json(root, rel)
        if data is None:
            continue
        v = data.get("e2e_scripts_in")
        if isinstance(v, str) and v.strip() in ("system", "testing"):
            v = v.strip()
            if v == "testing" and not (root / "docs/02-design/testing.md").is_file():
                return "system"        # 誤宣言は安全側へ倒す(fail-closed)
            return v
    return "system"


def find_root(start: Path) -> Path:
    cur = start.resolve()
    for cand in (cur, *cur.parents):
        if (cand / "CLAUDE.md").is_file() and (cand / ".claude").is_dir():
            return cand
    return cur


_cfg_warned: set[str] = set()


def _cfg_json(root: Path, rel: Path) -> dict | None:
    """flow-config(.local).json を読む。**壊れた JSON を黙って無視しない**(inspection-17 低位)。

    縮退の方向はどの読み手も fail-closed(f4_scopes は既定の全試験区分、code_roots は未宣言
    = red、ui_roots は code_roots 全体)だが、壊れていること自体は必ず言う —
    「設定したつもりで入っていない」を沈黙のまま走らせない。警告は1ファイル1回。
    """
    path = root / rel
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        return None
    except ValueError:
        data = None
    if not isinstance(data, dict):
        key = str(rel)
        if key not in _cfg_warned:
            _cfg_warned.add(key)
            print(f"警告: {rel} が JSON オブジェクトとして読めない — 無いものとして扱う"
                  "(設定を直すこと)", file=sys.stderr)
        return None
    return data


def f4_scopes(root: Path) -> list[str]:
    for rel in (LOCAL, CONFIG):        # local が優先(上書き。和集合ではない — 外す設定だから)
        data = _cfg_json(root, rel)
        if data is None:
            continue
        v = data.get("f4_scopes")
        if not (isinstance(v, list) and v and all(isinstance(s, str) for s in v)):
            continue
        got = set(v)
        # 受理するのは既定の全部か qa を外した形だけ(規範が認める縮小は「UI 無しで qa を
        # 外す」のみ — flows.md §2)。それ以外は無視して既定の全試験区分を要求する(fail-closed)。
        if got == set(DEFAULT_F4_SCOPES) or got == set(DEFAULT_F4_SCOPES) - {"qa"}:
            return [x for x in DEFAULT_F4_SCOPES if x in got]
        print(f"警告: {rel} の f4_scopes {v} は受理できない(許されるのは既定の全部か "
              "qa を外した形だけ)。既定の全試験区分で判定する", file=sys.stderr)
        return list(DEFAULT_F4_SCOPES)
    return list(DEFAULT_F4_SCOPES)


def head(root: Path) -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                             capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def dirty(root: Path) -> list[str] | None:
    """未コミット・未追跡のパス。読めなければ None(=判定不能)。

    改名(`R  old -> new`)は**新しい側**を返す。古い側の名前で覆い判定をすると、
    もう存在しないパスを「動いた」と数えてしまう。
    """
    try:
        out = subprocess.run(["git", "status", "--porcelain"],
                             cwd=root, capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    paths = []
    for line in out.stdout.splitlines():
        if not line.strip():
            continue
        raw = line[3:].strip().strip('"')
        if " -> " in raw:
            raw = raw.split(" -> ", 1)[1].strip().strip('"')
        paths.append(raw)
    return paths


def changed_since(root: Path, commit: str) -> list[str] | None:
    """commit..HEAD で変わったパス + 未コミットの変更。読めなければ None(=判定不能)。"""
    try:
        diff = subprocess.run(["git", "diff", "--name-only", f"{commit}..HEAD"],
                              cwd=root, capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    pending = dirty(root)
    if pending is None:
        return None
    return [line.strip() for line in diff.stdout.splitlines() if line.strip()] + pending


def changed_between(root: Path, a: str, b: str) -> list[str] | None:
    """a..b で変わったパス(未コミットは見ない)。読めなければ None(=判定不能)。"""
    try:
        diff = subprocess.run(["git", "diff", "--name-only", f"{a}..{b}"],
                              cwd=root, capture_output=True, text=True, check=True)
        return [line.strip() for line in diff.stdout.splitlines() if line.strip()]
    except (OSError, subprocess.CalledProcessError):
        return None


# 版の行の正規形。**ASCII だけを受け付ける** ★ — `\s` は全角空白を、`\d` は全角数字を通す
# ので、`version:　1.2.3` や `version: １.２.３`(どちらも YAML として読めない)が「正しい形」に
# なり、そこへ書き換える変更が管理欄扱いされて古い green を延命させる(独立レビュー 2026-08-25
# の所見1・第2回)。区切りは ASCII 空白1個以上、数字は ASCII のみ、行末の空白だけ許す。
_CANONICAL_VERSION = re.compile(r"version:[ ]+[0-9]+\.[0-9]+\.[0-9]+[ ]*")


def _sound_version(text: str) -> bool:
    """frontmatter に **正しい形の `version:` がちょうど1行**在るか。

    版の繰り上げを失効の理由から外してよいのは、**両側がその形をしているときだけ**である。
    行の消滅・不正値・重複まで落とすと、`version: 1.2.3` を消す/`version: broken` にする
    変更が管理欄扱いになり、**壊れた版が古い green を延命させる**(独立レビュー 2026-08-25 の
    所見1)。そういう側では下の `_normalize_meta` が `version:` を**本文と同じに扱う**ので、
    値が動けばそのまま失効する — 安全側である。
    **正しい形は ASCII だけである**(`_CANONICAL_VERSION` の注記)。"""
    if not text.startswith("---"):
        return False
    parts = text.split("---", 2)
    if len(parts) < 3:
        return False
    lines = [ln for ln in parts[1].splitlines() if re.match(r"version:", ln)]
    return len(lines) == 1 and _CANONICAL_VERSION.fullmatch(lines[0]) is not None


def _normalize_meta(text: str, drop_version: bool) -> str:
    """frontmatter から管理欄(`updated:` 行・`verified:` ブロック、`drop_version` が真なら
    `version:` 行)を落とした全文を返す。frontmatter が無ければそのまま返す(本文は一切
    触らないので、本文中の `updated:` に見える行は管理欄扱いされない)。

    **`drop_version` は呼び手が両側を見て決める** — 失効を決めるのは中身であって版の札だが、
    その札が両側とも正しい形をしているときに限る(`_sound_version`)。"""
    if not text.startswith("---"):
        return text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return text
    out, in_verified = [], False
    for line in parts[1].splitlines():
        if in_verified:
            if line[:1] in (" ", "\t") or not line.strip():
                continue                  # verified ブロックの入れ子行
            in_verified = False
        if re.match(r"(?:updated|verified):", line):
            in_verified = line.startswith("verified:")
            continue
        if drop_version and re.match(r"version:", line):
            continue
        out.append(line)
    return "---" + "\n".join(out) + "---" + parts[2]


# 機械の欄(手で保守する文書の中の、道具が丸ごと書く区画)。**中身は比較から取り除く** ★ —
# 除外は**パス単位では書けない**(ファイルごと外すと、同じファイルの手書き部分の変更まで
# 失効しなくなる穴が開く)。だから管理欄と同じ形の**区画単位**の判定にする(2026-08-27)。
# 印の形の正は `.claude/directions/conventions.md` と `build-facts.py` の docstring である。
# **終端は2つの形を受ける** ★ — `<!-- END GENERATED: <道具名> -->` と、道具名を持たない
# 旧終端 `<!-- END GENERATED -->`(`build-index.py` が「旧終端も読める」と言っており、
# 雛形 `templates/03-index.md` が配っているのはその形である)。片方しか受けないと、
# **索引の中身が初めて動いた回にこの例外が効かない**(2026-08-27 の独立確認2周目)。
_GENERATED = re.compile(
    r"<!--\s*BEGIN GENERATED:[^>]*-->.*?<!--\s*END GENERATED\s*(?::[^>]*)?\s*-->",
    re.S)


def _strip_generated(text: str) -> str:
    """機械の欄の**中身**を落とす(印そのものは残す)。

    印を残すのは、**区画が増えた・消えた・id が変わった**ことは中身の変更だからである
    (道具の持ち場が動いたなら、それは見直す理由になる)。"""
    return _GENERATED.sub(lambda m: re.sub(r"-->.*?<!--", "-->\n<!--", m.group(0), flags=re.S),
                          text)


def machine_owned_only(root: Path, base: str, upto: str | None, path: str) -> bool:
    """path の base →(upto、None なら作業ツリー)の変更が、**機械が持つ領域だけ**か。

    機械が持つ領域は2つである:

    1. **管理欄** = frontmatter の `updated:` 行・`verified:` ブロック、そして
       **両側が正しい形の `version:` をちょうど1行持つときに限り** その `version:` 行。
    2. **機械の欄** = `<!-- BEGIN GENERATED: <道具名> ... -->` から
       `<!-- END GENERATED: ... -->` までの**中身**(2026-08-27。`build-facts.py`)。
       生成器が実装から書き写しただけの区画が動いても、**手書きの部分は動いていない**ので、
       読み比べる検査の結論は古くならない。**印そのものは比較に残す** — 区画が増減したり
       id が変わったりしたのは、道具の持ち場が動いたということである。
    **版の繰り上げは、それ自体では管理欄外の変更にならない** — 本文と残りの frontmatter が
    同一なら失効させない(2026-08-25。上の見出しの ★ に理由が在る)。**ただし版が消えた・
    壊れた・重複した側では版を本文と同じに扱う**ので、その変更は失効する(`_sound_version`)。
    md 以外・新規・削除・読めないときは False(意味のある変更として扱う — fail-closed)。
    inspection-16 D2(`version:` 行を管理欄に入れたのは 2026-08-25 の裁定。D2 は PATCH までで
    線を引いていた)。**旧名は `metadata_only` である**(機械の欄を足したときに改名した)。"""
    if not (path.endswith(".md") and path.startswith("docs/")):
        return False

    def blob(ref: str | None) -> str | None:
        if ref is None:
            f = root / path
            try:
                return f.read_text(encoding="utf-8", errors="replace") if f.is_file() else None
            except OSError:
                return None
        try:
            r = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=root,
                               capture_output=True, text=True)
            return r.stdout if r.returncode == 0 else None
        except OSError:
            return None

    a, b = blob(base), blob(upto)
    if a is None or b is None:
        return False
    drop = _sound_version(a) and _sound_version(b)
    return (_strip_generated(_normalize_meta(a, drop))
            == _strip_generated(_normalize_meta(b, drop)))


def code_roots(root: Path) -> list[str]:
    """製品コードとテストコードの置き場(接頭辞)。空 = 未宣言(デプロイゲートは red にする)。"""
    for rel in (LOCAL, CONFIG):        # local が優先(f4_scopes と同じ規則)
        data = _cfg_json(root, rel)
        if data is None:
            continue
        v = data.get("code_roots")
        if isinstance(v, list) and all(isinstance(s, str) for s in v):
            return [s for s in v if s]
    return []


def scope_roots(root: Path, scope: str | None) -> list[str]:
    """試験区分(`scope`)ごとのコードの置き場。空 = 未宣言(広いほうへ倒す)。

    `ui_roots` を qa 以外へ一般化したものである(inspection-21 V-9)。試験区分とコード領域の
    対応を宣言できると、無関係な試験区分が変更のたびに一律で失効することがなくなる。
    **未宣言は red ではなく広いほうへ倒す**(qa は `ui_roots`、それ以外は `code_roots` 全体
    — 過大近似 = 安全側)。狭く誤宣言したときだけ穴になるので、迷ったら宣言しない。
    試験区分の中は当面 suite 丸ごとのままである(どの試験がどのパスを覆うかは機械で言えない)。
    """
    if not scope:
        return []
    for rel in (LOCAL, CONFIG):        # local が優先(code_roots と同じ規則)
        data = _cfg_json(root, rel)
        if data is None:
            continue
        v = data.get("scope_roots")
        if isinstance(v, dict):
            w = v.get(scope)
            if isinstance(w, list) and all(isinstance(s, str) for s in w):
                return [s for s in w if s]
    return []


def ui_roots(root: Path) -> list[str]:
    """UI に関わるコードの置き場(qa 試験区分の失効判定用)。空 = 未宣言。
    **未宣言は red ではなく code_roots 全体へ倒す**(過大近似 = 安全側 —
    inspection-17 判断5。狭く誤宣言したときだけ穴になるので、既定は広いほう)。"""
    for rel in (LOCAL, CONFIG):        # local が優先(code_roots と同じ規則)
        data = _cfg_json(root, rel)
        if data is None:
            continue
        v = data.get("ui_roots")
        if isinstance(v, list) and all(isinstance(s, str) for s in v):
            return [s for s in v if s]
    return []


def all_declared_roots(root: Path) -> list[str]:
    """宣言されている置き場の**全部**(`code_roots` + すべての `scope_roots` の値 + `ui_roots`)。

    `code_excludes` の等号検査はここを見る。**`code_roots` とだけ比べるのでは足りない** —
    試験区分が実際に見るのは `scope_roots` → `ui_roots` → `code_roots` の順で解決した値であり
    (`resolved_roots`)、狭く宣言した値は `code_roots` より真に狭いので、それと等しい除外は
    等号検査をすり抜けて**その試験区分の失効判定を丸ごと殺す**(2026-08-22 の独立検査。実測:
    `scope_roots.unit = ["src/app/"]` と `code_excludes = ["src/app/"]` を並べると、
    unit はどのパスが動いても二度と失効しなくなった)。
    """
    out = list(code_roots(root))
    out.extend(ui_roots(root))
    for rel in (LOCAL, CONFIG):
        data = _cfg_json(root, rel)
        if data is None:
            continue
        v = data.get("scope_roots")
        if isinstance(v, dict):
            for w in v.values():
                if isinstance(w, list):
                    out.extend(x for x in w if isinstance(x, str) and x)
            break                       # local が在れば local だけを見る(解決規則と同じ)
    return out


def code_excludes(root: Path) -> list[str]:
    """コードの置き場の中に在るが、**検証の入力ではない**と宣言されたパス。空 = 宣言なし。

    2026-08-22 の人間の指示で足した。**コミットし忘れていた1本を後から入れただけで
    デプロイゲートが失効する**という実害があり、その1本はメモ・固定データ・同梱バイナリの
    ように、どの検証も読まないものだった。`code_roots` を狭めれば消せる場合もあるが、
    置き場の途中に混ざっているものは狭められない。

    **既定は空である**(宣言しなければ今までどおり = fail-closed のまま)。
    **狭く誤ると穴になる** — 検証が本当に読むファイルをここへ書くと、それを変えても失効せず、
    古い green のまま出荷できてしまう。`ui_roots` と同じ但し書きが掛かる: **迷ったら書かない。**

    **コードの置き場の下に無い項目は落とす。** `docs/` などをここへ書いて文書側の依存を
    黙って外せてしまうと、この宣言は「検証の入力ではない」ではなく「見ないことにする」の口になる。
    """
    roots = code_roots(root)
    if not roots:
        return []
    for rel in (LOCAL, CONFIG):        # local が優先(code_roots と同じ規則)
        data = _cfg_json(root, rel)
        if data is None:
            continue
        v = data.get("code_excludes")
        if isinstance(v, list) and all(isinstance(x, str) for x in v):
            # **どの置き場より真に狭いものだけを受け付ける。** 落とすのは3種類ある:
            # (1) 置き場の外 — 文書側の依存を黙って外す口になる。
            # (2) 置き場の親 — その置き場ごと無効にできる。
            # (3) **宣言されたどれかの置き場と等しいもの** — `code_roots` だけでなく、
            #     `scope_roots` の各値と `ui_roots` も含む(`all_declared_roots`)。
            #     等しいものを通すと、その置き場を見る側は**どのパスが動いても二度と失効しない**。
            #     入れ子の置き場も試験区分ごとの狭い宣言も、`code_roots` より真に狭いので、
            #     `code_roots` とだけ比べる等号検査はどちらもすり抜ける
            #     (2026-08-22 の独立検査。親 → 等号 → 入れ子 → 試験区分ごとの値、と4度指摘された)。
            # **置き場そのものを外したいなら、`code_excludes` ではなく `code_roots` から
            # その項目を消すのが正しい形である。**
            # 置き場が**ファイル**のときは、その下に在るものは存在しえないので容れ物に数えない
            # (`code_roots` は「ファイルでもディレクトリでもよい」— `flow-config.json`)。
            declared = {r.rstrip("/") for r in all_declared_roots(root)}
            def strictly_inside(x: str) -> bool:
                if x.rstrip("/") in declared:
                    return False        # (3) 宣言されたどれかの置き場そのもの(試験区分ごとの値も含む)
                return any(under(x, r) and not (root / r).is_file() for r in roots)
            return [x for x in v if x and strictly_inside(x)]
    return []


def widened(root: Path, flow: str, scope: str | None) -> str | None:
    """この (flow, scope) が、**宣言が無いせいで**実際より広い置き場で判定しているなら、その理由。

    **判定は1バイトも変えない。見えるようにするだけである。** 過大近似は安全側だが、代償は
    余分な失効であり、**宣言し忘れているプロジェクトはそれに気づく手がかりを持っていなかった** —
    出力は「失効 — 覆えていない依存 N 件」としか言わず、その N が実際の依存なのか宣言漏れの
    ぶんなのかを区別しない(2026-08-22 の実測: 1つのプロジェクトが、コードの置き場を1つ
    宣言しただけの状態で、Dockerfile 1本の変更により unit・integration・e2e・qa の
    4つの試験区分すべてを同時に失効させていた)。
    """
    rules = DEPENDS.get(dep_key(flow, scope), ())
    if not (CODE in rules or UI in rules):
        return None
    if not code_roots(root):
        return None                              # そもそも置き場が未宣言 = 別の案内が出ている
    if not scope:
        # **試験区分を持たないフロー(F3)は対象外である。** `scope_roots` は試験区分ごとの宣言なので
        # 宣言先が無く、言えば「消せない注記」を毎回出すことになる。F3 が広いのは設計であり
        # (比べる3辺そのもの — 上の DEPENDS の注)、宣言漏れではない(2026-08-22 の独立検査 B-2)。
        return None
    if scope_roots(root, scope):
        return None                              # 試験区分ごとに宣言済み = 倒れていない
    if UI in rules:
        if ui_roots(root):
            return None                          # ui_roots へ倒すのは設計どおりの絞り込み
        return "scope_roots も ui_roots も未宣言"
    return "scope_roots が未宣言"


def dep_key(flow: str, scope: str | None) -> str:
    k = f"{flow}:{scope}" if scope else flow
    return k if k in DEPENDS else flow


def resolved_roots(root: Path, flow: str, scope: str | None) -> list[str] | None:
    """この (flow, scope) が実際に見るコードの置き場(鮮度スタンプへ焼き込む値)。
    コード依存を持たないフローは None。"""
    rules = DEPENDS.get(dep_key(flow, scope), ())
    if UI in rules:
        return scope_roots(root, scope) or ui_roots(root) or code_roots(root)
    if CODE in rules:
        return scope_roots(root, scope) or code_roots(root)
    return None


def depends(root: Path, flow: str, scope: str | None) -> tuple[list[str], bool]:
    """(依存する接頭辞の一覧, コードの置き場が未宣言か)。"""
    rules = DEPENDS.get(dep_key(flow, scope), ())
    roots = code_roots(root)
    declared = scope_roots(root, scope)   # 試験区分ごとの宣言(未宣言なら空 → 下の既定へ倒す)
    code = declared or roots
    ui = declared or ui_roots(root) or roots   # 未宣言なら ui_roots、それも無ければ全体(安全側)
    undeclared = (CODE in rules and not code) or (UI in rules and not ui)
    out = []
    for r in rules:
        if r == CODE:
            out.extend(code)
        elif r == UI:
            out.extend(ui)
        else:
            out.append(r)
    # E2E 台本を testing.md へ切り出したと宣言したプロジェクトでは、e2e / qa の依存から
    # system.md を外し、testing.md を入れる(inspection-20 V-4)。宣言が無ければ何もしない。
    if dep_key(flow, scope) in ("verify-tests:e2e", "verify-tests:qa") \
            and e2e_scripts_in(root) == "testing":
        out = [x for x in out if x != "docs/02-design/system.md"]
        if "docs/02-design/testing.md" not in out:
            out.append("docs/02-design/testing.md")
    return out, undeclared


def under(path: str, prefix: str) -> bool:
    """path が prefix(ファイルでもディレクトリでもよい)の下に在るか。"""
    p = prefix.rstrip("/")
    return path == p or path.startswith(p + "/")


def depends_on(path: str, prefixes: list[str], excl: tuple[str, ...] = ()) -> bool:
    """このパスの変更が、その (flow, scope) の検証結果を失効させるか。
    除外(`EXCLUDES`)に当たるものは、許可リストの下に在っても失効させない。"""
    if any(under(path, e) for e in excl):
        return False
    return any(under(path, p) for p in prefixes)


RECORDS = Path("docs/build-records")


def record_states(root: Path) -> list[tuple[Path, str, str]]:
    """(path, state, commit)。frontmatter が読めないものは state を「不明」にする(fail-closed)。"""
    base = root / RECORDS
    if not base.is_dir():
        return []
    out = []
    for p in sorted(base.glob("*.md")):
        # **`._*`(macOS の AppleDouble)を落とす** ★ — `---` で始まらないので
        # 状態が `不明` になり、**デプロイゲートの「未 verified の構築記録」に入って
        # 閉じたままになる**(独立検査 2026-09-04 の実測)。`promote` でも verify でも
        # 解けない。シートの側(`pending_sheets`)と同じ型だが、**こちらは拒む側である。**
        if p.name == "index.md" or p.name.startswith("._"):
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        state = commit = ""
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) > 2:
                m = re.search(r"(?m)^state:\s*(\S+)", parts[1])
                state = m.group(1) if m else ""
                m = re.search(r"(?m)^commit:\s*(\S+)", parts[1])
                commit = m.group(1).strip("`\"'") if m else ""
        out.append((p, state or "不明", commit))
    return out


def pending_sheets(root: Path) -> list[str]:
    """未回答のシート。**AppleDouble(`._*`)は数えない。**

    macOS が非 HFS のボリューム(ネットワーク共有・exFAT・一部の VM 共有)へ書くとき、
    本体と同じ場所に `._<本体名>` という付随ファイルを作る。中身は資源フォークであって
    シートではないのに `*.md` に一致するため、**シートを1つ編集するたびに未回答が1件
    増えて見え、消してもシートを編集し直すと復活する**(実測 2026-09-01。デプロイの門が
    人間への問いを抱えていると誤って言い続ける)。名前で落とすのが唯一の見分け方である。
    """
    base = root / "docs/sheets"
    if not base.is_dir():
        return []
    return sorted(p.name for p in base.glob("*.md")
                  if p.is_file() and not p.name.startswith("._"))


def blocking_issues(root: Path) -> list[str]:
    """`type: bug` **かつ** `severity: 高` の課題票(リリースの完了定義の3項目目の機械近似)。

    **and である**(inspection-19 D-2 の裁定 2026-08-21)。正は `flows.md` §2 の
    「`type: bug` かつ `severity: 高` の課題票が0件」である。
    """
    base = root / "docs/issues"
    if not base.is_dir():
        return []
    out = []
    for p in sorted(base.glob("*.md")):
        if p.name == "index.md":
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        if re.search(r"(?m)^type:\s*[\"']?bug[\"']?\s*$", text) \
                and re.search(r"(?m)^severity:\s*[\"']?高", text):
            out.append(p.name)
    return out


def is_ancestor(root: Path, ancestor: str, descendant: str) -> bool | None:
    if ancestor == descendant:
        return True
    try:
        r = subprocess.run(["git", "merge-base", "--is-ancestor", ancestor, descendant],
                           cwd=root, capture_output=True)
        return r.returncode == 0
    except OSError:
        return None


def load_stamps(root: Path) -> dict:
    path = root / STATE
    if not path.is_file():
        return {"latest": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"latest": {}}
    if not (isinstance(data, dict) and isinstance(data.get("latest"), dict)):
        return {"latest": {}}
    # `partial` / `full` / `last_green` は後から足した鍵である。
    # **無い既存ファイルはそのまま読める**(移行不要 — `green_entry` が latest から補う)。
    for later in ("partial", "full", "last_green"):
        if not isinstance(data.get(later), dict):
            data.pop(later, None)
    return data


def green_entry(data: dict, k: str) -> dict | None:
    """増分の基準点 = 最後に green だった全体スタンプ。`last_green` が正で、無い旧ファイル
    では latest が green のときだけそれを使う(red が基準点を消していた旧挙動の互換読み)。"""
    e = data.get("last_green", {}).get(k)
    if e:
        return e
    e = data.get("latest", {}).get(k)
    return e if e and e.get("verdict") == "green" else None


def save_stamps(root: Path, data: dict) -> None:
    path = root / STATE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@contextlib.contextmanager
def state_lock(root: Path):
    """状態ファイルを排他する(読み→書きが1つの run のあいだ割り込まれない)。

    `record` も `promote` も read-modify-write なので、2本が重なると**後に書いた側が
    相手の鮮度スタンプを消す**。規範は verify 系を直列に流すと決めているが(orchestration.md §3.4)、
    それは文章での約束であり、破れたときに黙って壊れるのはここである。
    """
    path = root / STATE
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


def key(flow: str, scope: str | None) -> str:
    return f"{flow}:{scope}" if scope else flow


def _changed(root: Path, cache: dict, commit: str, upto: str | None) -> list[str] | None:
    """commit 以降に動いたパス。upto が在ればその commit まで(未コミットを見ない)。"""
    ck = (commit, upto)
    if ck not in cache:
        cache[ck] = changed_since(root, commit) if upto is None \
            else changed_between(root, commit, upto)
    return cache[ck]


def cover_winner(root: Path, parts: list[dict], path: str, cache: dict,
                 upto: str | None) -> dict | None:
    """path を覆う最後の部分スタンプ(`at` 昇順で後勝ち)。覆った後に動いた記録は数えない。"""
    winner = None
    for e in parts:
        if not any(under(path, c) for c in e.get("covers", ())):
            continue
        later = _changed(root, cache, str(e.get("commit", "")), upto)
        if later is None or (path in later
                             and not machine_owned_only(root, str(e.get("commit", "")), upto, path)):
            continue                      # その記録の後で動いた = 覆えていない
        winner = e
    return winner


def partials(data: dict, k: str) -> list[dict]:
    got = data.get("partial", {}).get(k, [])
    out = [e for e in got if isinstance(e, dict) and e.get("covers")]
    out.sort(key=lambda e: str(e.get("at", "")))
    return out


def uncommitted_in(root: Path, prefixes: list[str],
                   excl: tuple[str, ...] = ()) -> list[str] | None:
    """その範囲に在る未コミット・未追跡のパス(判定不能なら None)。"""
    pending = dirty(root)
    if pending is None:
        return None
    return sorted({p for p in pending if depends_on(p, prefixes, excl)})


CLOSURE_LINE = re.compile(r"^[-*]\s+`?([\w][\w./-]*)`?")
CLOSURE_PLACEHOLDER = re.compile(r"<[^<>\n]{0,60}>")


def closure_of(text: str) -> list[str]:
    """構築記録の `## 影響範囲(closure)` に並ぶ実パス。見出しの正は build-record.md。"""
    m = re.search(r"^##[^\n]*影響範囲[^\n]*$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    if not m:
        return []
    out = []
    for line in m.group(1).splitlines():
        hit = CLOSURE_LINE.match(line.strip())
        if hit and not CLOSURE_PLACEHOLDER.search(line):
            out.append(hit.group(1))
    return out


def critical_awaiting(root: Path, covers: list[str] | None = None) -> list[str]:
    """green の記録に独立レビューの実施(--lens)を要求する critical 記録の名前。

    条件は inspection-17 判断9(結線を文章だけに置かない)。**範囲は run に合わせる** ★
    (inspection-19 V-2 の裁定 2026-08-21): `--covers` を持つ run —— 範囲を絞って回した
    覆い直し —— では、**その覆いにクロージャが掛かる critical 記録だけ**が要求を起こす。
    リポジトリ全体で見ると、`/verify-docs` §2 が「3ファイル以下・critical 非含有なら
    独立レビューを起こすな」と指示した小型 run が record に拒まれ、**指示どおりに走ると
    記録できない**という閉じないループになる(そして実在しない独立レビュー名の申告を誘う)。
    覆いを持たない run(= 全体スタンプ)は依存集合まるごとを主張するので、従来どおり
    1件でも在れば要求する。
    """
    out = []
    for p, state, _ in record_states(root):
        if state != "awaiting-verify":
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        if not text.startswith("---"):
            continue
        parts = text.split("---", 2)
        if len(parts) <= 2 or not re.search(r"(?m)^critical:\s*true\b", parts[1]):
            continue
        if covers:
            cl = closure_of(text)
            # クロージャが読めない記録は安全側で要求する(fail-closed)
            if cl and not any(under(c, x) or under(x, c) for c in covers for x in cl):
                continue
        out.append(p.name)
    return out


def record(root: Path, flow: str, verdict: str, scopes: list[str],
           covers: list[str] | None = None, full: bool = False,
           lens: str | None = None) -> int:
    if flow not in FLOWS:
        print(f"エラー: 不明なフロー {flow}(verify-docs / verify-impl / verify-tests)",
              file=sys.stderr)
        return 2
    if verdict not in ("green", "red"):
        print("エラー: 判定は green か red", file=sys.stderr)
        return 2
    if flow == "verify-tests" and not scopes:
        print("エラー: verify-tests は --scope 必須(全部実施なら f4_scopes を全部並べる)",
              file=sys.stderr)
        return 2
    if flow != "verify-tests" and scopes:
        print(f"エラー: {flow} に試験区分は無い", file=sys.stderr)
        return 2
    sha = head(root)
    if sha is None:
        print("エラー: git の HEAD が読めない(鮮度スタンプは commit に紐づく)", file=sys.stderr)
        return 2
    covers = sorted(set(covers or []))
    if covers and full:
        print("エラー: --full と --covers は両立しない(全数を回したのなら覆いは要らない)",
              file=sys.stderr)
        return 2
    if full and flow == "verify-tests":
        print("エラー: F4 に全数の印は無い(毎回が suite 丸ごと=全数であり、全数でしか"
              "回らない検査も無い — flows.md §2.1)", file=sys.stderr)
        return 2
    # critical な仕事が検証待ちのとき、F2/F3 の green は独立レビューの実施を名乗って記録する
    # (CLAUDE.md §6 の必須を機械に接続する — inspection-17 判断9)。これが防ぐのは
    # 「忘れ・依頼の不達に気づかないまま完走」であって嘘ではない(申告ベース)。
    if verdict == "green" and flow in ("verify-docs", "verify-impl") and not lens:
        crit = critical_awaiting(root, covers)
        if crit:
            print(f"エラー: この run の範囲に掛かる critical: true の awaiting-verify 記録が在る"
                  f"({', '.join(crit)})— green の記録には独立レビューの実施が必須"
                  "(CLAUDE.md §6)。--lens <実際に走った独立レビューの名前> を添えて記録すること。"
                  "独立レビューが起こせない・返らない run は green を記録せず中断する"
                  "(/verify-docs §2)", file=sys.stderr)
            return 2
    for scope in (scopes or [None]):
        prefixes, undeclared = depends(root, flow, scope)
        excl = dep_excludes(root, flow, scope)
        if covers and undeclared:
            print("エラー: コードの置き場が未宣言なので部分記録はできない"
                  "(.claude/scripts/flow-config.local.json の code_roots)", file=sys.stderr)
            return 2
        for c in covers:                    # 覆っていない場所を「覆った」と書かせない
            if any(under(c, e) for e in excl):
                print(f"エラー: --covers {c} は {key(flow, scope)} の依存から除かれている領域である"
                      "(`stamps.py deps` で確かめること)", file=sys.stderr)
                return 2
            if not any(under(c, p) or under(p, c) for p in prefixes):
                print(f"エラー: --covers {c} は {key(flow, scope)} の依存集合の外である"
                      "(`stamps.py deps` で確かめること)", file=sys.stderr)
                return 2
        # **汚れたまま green を書かせない。** 未コミットはどの鮮度スタンプの commit よりも後なので
        # 構造的に覆えず、書いた瞬間に失効する(= 回したのにデプロイゲートが閉じない、だけが残る)。
        if verdict == "green":
            scope_of_claim = covers or prefixes
            pending = uncommitted_in(root, scope_of_claim, () if covers else excl)
            if pending is None:
                print("エラー: git の状態が読めないので green を記録できない", file=sys.stderr)
                return 2
            if pending:
                shown = pending[:8]
                more = f"(ほか {len(pending) - 8} 件)" if len(pending) > 8 else ""
                print(f"エラー: {key(flow, scope)} の"
                      f"{'覆い' if covers else '依存'}に未コミットの変更がある: "
                      f"{', '.join(shown)}{more}", file=sys.stderr)
                print("  先にコミットしてから記録すること"
                      "(未コミットのままの green は書いた瞬間に失効する)。"
                      "red はいつでも記録できる", file=sys.stderr)
                return 2
    data = load_stamps(root)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    merged: list[str] = []                  # 部分が覆い切って基準点を進めたもの
    for scope in (scopes or [None]):
        k = key(flow, scope)
        entry = {"flow": flow, "scope": scope, "commit": sha, "at": now, "verdict": verdict}
        if lens:
            entry["lens"] = lens
        br = resolved_roots(root, flow, scope)
        if br is not None:
            entry["code_roots"] = br        # 宣言を変えたら見直す(D8。qa は ui_roots の解決値)
            # **除外の宣言も焼き込む。** 焼かないと、後から code_excludes を広げた瞬間だけ
            # fail-open になる(いま失効しているパスが、宣言を変えた途端に失効しなくなり、
            # 誰も見ていない変更を古い green が覆っていることになる)。
            entry["code_excludes"] = sorted(code_excludes(root))
        if dep_key(flow, scope) in ("verify-tests:e2e", "verify-tests:qa"):
            entry["e2e_scripts_in"] = e2e_scripts_in(root)   # 同上(台本の置き場の宣言)
        if covers:                          # 部分再検証: 全体スタンプに併合して読む
            data.setdefault("partial", {}).setdefault(k, []).append({**entry, "covers": covers})
            # **覆い切ったら基準点を今の commit へ進めて、部分を畳む** ★
            # 併合の結果が green = 「基準点以降に動いた依存は1本残らず、その最後の変更以後に
            # 覆われている」であり、それは **今の commit に対する green そのもの**である。
            # 進めないと基準点は最後の「全部回した green」に据え置かれ、覆う義務のあるパスの
            # 集合が単調に増え続ける — 覆いは「そのパスの最後の書き手であること」を条件に
            # するので(cover_winner)、集合が育つほど、誰かが1本触るたびにどれかの覆いが
            # 死ぬ。F2 と F3 は互いの依存(docs/02-design/・docs/03-impl/)へ本文を書くため、
            # 交互に回すと義務が積み上がって閉じなくなる(2026-08-23 の実測: 7周まわって
            # デプロイゲートが閉じなかった)。
            # **主張は広がらない** — 畳む条件は「**この記録が green** であり、**かつ**
            # 今 stamp_state が green と言うこと」の2つだけで、併合で既に出ている判定を
            # 正規化しているにすぎない。基準点が無い(未実施)・latest が red・依存に
            # 未コミットが在る・宣言が記録時と違う、のいずれでも stamp_state は green を
            # 返さないので、畳みも起きない(fail-closed のまま)。
            # **畳むのは green の記録だけである** ★(独立レビュー 2026-08-25 の所見)。
            # `record` は `red --covers` を受理する(部分を回して red だった、の記録)。
            # そのとき stamp_state は **追記前の全体 green** を基準に判定するので、
            # 基準点以降の依存変更が0件なら green を返す。その green で畳むと red の entry が
            # latest と last_green へ入り、「素の red は最終 green の基準点を消さない」
            # (flows.md §2)を破って、以後 promote が red を green の基準として読む
            # (green_entry は verdict を見ない)。
            if verdict == "green":
                state, _, _ = stamp_state(root, data, flow, scope)
                if state == "green":
                    data["latest"][k] = dict(entry)
                    data.setdefault("last_green", {})[k] = dict(entry)
                    data.get("partial", {}).pop(k, None)
                    merged.append(key(flow, scope))
            else:
                # **部分を回して red だったなら、直近の判定(latest)は red である** ★
                # (独立レビュー 2026-08-25 の所見・第2回)。ここを動かさないでいると、
                # latest は以前の green のまま残り、基準点以降の依存変更が0件なら
                # `check` はそのフローを green と読んでデプロイゲートを開く —
                # **red だと分かっている範囲を抱えたまま出荷できる**。latest は「直近の判定」
                # であり、デプロイゲートはそれを見る(flows.md §2)。
                # **last_green と部分スタンプは消さない**(inspection-17 判断4 — 素の red と同じ)。
                data["latest"][k] = entry
        elif verdict == "green":            # 全部回した green = 部分の記録は用済み
            data["latest"][k] = entry
            data.setdefault("last_green", {})[k] = entry
            data.get("partial", {}).pop(k, None)
        else:                               # 素の red。**最終 green の基準点と部分の記録は
            data["latest"][k] = entry       # 消さない**(inspection-17 判断4 — 消すと次の
            #                                 増分が全数化する。red は判定であって忘却ではない)
        if full:                            # 全数を回した印。**デプロイゲートと失効判定には効かない**
            data.setdefault("full", {})[k] = {"commit": sha, "at": now, "verdict": verdict}
    save_stamps(root, data)
    what = f"部分({', '.join(covers)})" if covers else ("全数(all)" if full else "全体")
    for scope in (scopes or [None]):
        print(f"記録: {key(flow, scope)} = {verdict} @ {sha[:12]} ({now}) / {what}")
    for k in merged:
        print(f"  併合: {k} の部分が依存を覆い切ったので、基準点を {sha[:12]} へ進めて部分を畳んだ"
              "(次の増分はここからの差分だけになる)")
    return 0


def stamp_state(root: Path, data: dict, flow: str,
                scope: str | None = None) -> tuple[str, str, list[str]]:
    """(判定, 理由, 覆えていない依存パス)。判定は green / red / 失効 / 未実施 / 未宣言 / 判定不能。

    green は **「動いた依存パス1本ごとに、その最後の変更以後にそこを覆う green が在る」**
    ときにだけ成立する。覆う根拠の無いパスが1本でも残れば失効であり、**見ていない範囲を
    green と言うことはできない**。未コミットの変更は、どの鮮度スタンプの commit よりも後なので
    構造的に覆えない(= 汚れた作業ツリーが green を作ることはない)。
    """
    k = key(flow, scope)
    entry = data.get("latest", {}).get(k)
    prefixes, undeclared = depends(root, flow, scope)
    excl = dep_excludes(root, flow, scope)
    if undeclared:
        return "未宣言", "コードの置き場が宣言されていない", []
    if entry is None:
        return "未実施", "鮮度スタンプが無い", []
    if entry.get("verdict") != "green":
        # red はデプロイゲートを止めるが、増分の基準点(最終 green)は生きている(判断4)。
        # 「最終 green 以降に動いた依存で、まだ覆われていないもの」を出す — check が
        # 「増分で回すべき範囲」として印字するため(修繕は依存に載るので必ずここに現れる)。
        uncovered: list[str] = []
        g = green_entry(data, k)
        if g:
            base = str(g.get("commit", ""))
            changed = changed_since(root, base)
            if changed is not None:
                parts, cache = partials(data, k), {}
                for p in sorted({q for q in changed if depends_on(q, prefixes, excl)
                                 and not machine_owned_only(root, base, None, q)}):
                    win = cover_winner(root, parts, p, cache, None)
                    if win is None or win.get("verdict") != "green":
                        uncovered.append(p)
        return "red", f"{entry.get('at', '?')} の実行が red", uncovered
    if "code_roots" in entry and sorted(entry.get("code_roots") or []) \
            != sorted(resolved_roots(root, flow, scope) or []):
        return "失効", "コードの置き場(code_roots / ui_roots / scope_roots)の宣言が記録時と違う — " \
                     "見る範囲を変えたら見直す", []
    # **欄を持たない古い鮮度スタンプも比べる**(既定 = 空と読む)。飛ばすと、宣言を
    # 空 → 除外ありへ変えた瞬間だけ fail-open になり、その除外に当たる未検証の変更を
    # 古い green が覆っていることにできる(e2e_scripts_in と同型。2026-08-22 の独立検査 B-1)。
    # **コードに依存しないフローは対象外である** — そちらに焼き込む値がそもそも無い。
    if resolved_roots(root, flow, scope) is not None \
            and sorted(entry.get("code_excludes") or []) != sorted(code_excludes(root)):
        return "失効", "code_excludes(検証の入力ではないと宣言したパス)が記録時と違う — " \
                     "見る範囲を変えたら見直す", []
    # **欄を持たない古い鮮度スタンプも比べる**(既定値 "system" と読む)。飛ばすと、
    # 宣言を system → testing に変えた瞬間だけ fail-open になり、未検証の testing.md を
    # green と言えてしまう(設定ファイル自身はどのフローの依存でもない)。
    if dep_key(flow, scope) in ("verify-tests:e2e", "verify-tests:qa") \
            and entry.get("e2e_scripts_in", "system") != e2e_scripts_in(root):
        return "失効", "E2E 台本の置き場(e2e_scripts_in)の宣言が記録時と違う — " \
                     "見る範囲を変えたら見直す", []
    sha = head(root)
    if sha is None:
        return "判定不能", "git の HEAD が読めない", []
    # commit == HEAD の早道は作らない — 同一 HEAD 上の未コミット変更(changed_since が
    # 拾う)を見逃す fail-open になる(inspection-16 H-2)
    changed = changed_since(root, entry.get("commit", ""))
    if changed is None:
        return "判定不能", f"鮮度スタンプの commit {entry.get('commit', '?')[:12]} が履歴に無い", []
    pending = sorted({p for p in changed if depends_on(p, prefixes, excl)
                      and not machine_owned_only(root, str(entry.get("commit", "")), None, p)})
    if not pending:
        return "green", f"{entry.get('at', '?')}(以降の変更は依存の外だけ)", []
    parts, cache, uncovered = partials(data, k), {}, []
    for p in pending:
        win = cover_winner(root, parts, p, cache, None)
        if win is None or win.get("verdict") != "green":
            uncovered.append(p)
    if uncovered:
        return "失効", f"覆えていない依存 {len(uncovered)} 件", uncovered
    return "green", f"{entry.get('at', '?')} + 部分再検証で依存 {len(pending)} 件を併合", []


def needed(root: Path) -> list[tuple[str, str | None]]:
    return [("verify-docs", None), ("verify-impl", None)] \
        + [("verify-tests", s) for s in f4_scopes(root)]


def check(root: Path) -> int:
    data = load_stamps(root)
    latest = data["latest"]
    need = needed(root)
    ok = True
    print("## デプロイゲート(及第ライン — 複合判定)")
    scopes = f4_scopes(root)
    if set(scopes) != set(DEFAULT_F4_SCOPES):
        print(f"  注記: f4_scopes が既定から狭められている({', '.join(scopes)})。"
              "狭めた理由は docs/pendings.md の棚上げ(P-nnn)として残すこと")
    for flow, scope in need:
        state, why, uncovered = stamp_state(root, data, flow, scope)
        mark = "OK " if state == "green" else "NG "
        if state != "green":
            ok = False
        print(f"  {mark} {key(flow, scope)}: {state} — {why}")
        if state == "未宣言":
            print("      直し方: .claude/scripts/flow-config.local.json に "
                  '"code_roots": ["<コードの置き場>", ...] を書く'
                  "(宣言するまで red のまま — 見ていないものを green とは言わない)")
        if uncovered:                       # **回すべき最小の範囲**を名指しする
            shown = uncovered[:8]
            more = f"(ほか {len(uncovered) - 8} 件は表示を省いた)" if len(uncovered) > 8 else ""
            sc = f" --scope {scope}" if scope else ""
            if state == "red":
                # red の解消は素の green で閉じる: 未変更部は最終 green が保証していて、
                # 変更部(修繕を含む)がこの範囲である。--covers では latest が red のまま
                # デプロイゲートが開かない(inspection-17 判断4)
                print(f"      最終 green 以降に動いた依存(増分で回す範囲): "
                      f"{', '.join(shown)}{more}")
                print(f"      閉じ方: red の原因を直してからその範囲を /{flow}"
                      f"{f' {scope}' if scope else ''} の増分で回し、"
                      f"`record {flow} green{sc}`(素)で記録する")
            else:
                print(f"      回すべき最小の範囲: {', '.join(shown)}{more}")
                print(f"      閉じ方: その範囲だけ /{flow}"
                      f"{f' {scope}' if scope else ''} を回し、次で記録する:")
                print(f"        python3 .claude/scripts/stamps.py record {flow} green{sc} "
                      + " ".join(f"--covers {p}" for p in uncovered))
    wide = [(key(f, sc), w) for f, sc in need
            if (w := widened(root, f, sc)) is not None]
    if wide:
        print("  注記: 次の試験区分は**置き場の宣言が無いので、code_roots 全体で判定している**"
              "(過大近似 = 安全側)。")
        print("        そのぶん、その試験区分と関係のない変更でも失効する:")
        for k, why in wide:
            print(f"          {k} — {why}")
        print("        直し方: .claude/scripts/flow-config.local.json に")
        print('          "scope_roots": {"<試験区分>": ["<その試験区分に関わる置き場>", ...], ...}')
        print('          "ui_roots": ["<画面に関わる置き場>", ...]   # qa 試験区分だけに効く')
        print("        を書く。**判定は今までどおり fail-closed である** — "
              "宣言しないままでも安全側に倒れる。")
        print("        **狭く誤ると穴になる**(見るべき変更が素通りする)ので、迷ったら宣言しない。")
    if code_excludes(root):
        print("  注記: code_excludes が宣言されている(検証の入力ではないとしたパス): "
              + ", ".join(sorted(code_excludes(root))))
        print("        **ここに書いたパスは、変更しても何も失効させない。** "
              "検証が実際に読むものが混ざっていないか、宣言を変えるたびに確かめること")

    # **台帳ディレクトリの欠落を「0件」と読まない**(fail-closed — inspection-17 M-13)。
    # docs/ が在るのに /setup が作る台帳が無いのは破損であって、空と数えられたのではない
    # (check-backlog.py と同じ規則。docs/ 自体が無い bootstrap 前だけは対象外)。
    if (root / "docs").is_dir():
        missing_ledgers = [d for d in ("docs/build-records", "docs/sheets", "docs/issues")
                           if not (root / d).is_dir()]
        if missing_ledgers:
            ok = False
            print(f"  NG  台帳ディレクトリが無い: {', '.join(missing_ledgers)} — "
                  "/setup が作るもの。欠落を『0件』と読むわけにはいかない")
    building = [p.name for p, s, _ in record_states(root) if s == "building"]
    awaiting = [p.name for p, s, _ in record_states(root) if s not in ("verified",) and s != "building"]
    if building:
        ok = False
        print(f"  NG  building の構築記録: {', '.join(building)} — まだ作業が終わっていない記録が残っている"
              "(/build を出口まで進めるか、check-debt.py --demote で次の周の網へ戻す)")
    if awaiting:
        ok = False
        print(f"  NG  未 verified の構築記録: {', '.join(awaiting)} — "
              "検証が揃っているなら `stamps.py promote`、揃っていないなら verify 系を回す")
    sheets = pending_sheets(root)
    if sheets:
        ok = False
        print(f"  NG  未回答のシート: {', '.join(sheets)} — 人間への問いを抱えたままデプロイしない")
    bugs = blocking_issues(root)
    if bugs:
        ok = False
        print(f"  NG  type: bug かつ severity: 高 の課題票: {', '.join(bugs)}"
              "(リリースの完了定義の3項目目の機械近似)")
    print_full_note(root, data)
    if ok:
        print("green: すべての検証が現在の状態に対して有効。デプロイしてよい")
        return 0
    print("red: 上の NG を解消して green を作ってからデプロイする"
          "(決まった時刻を待つ義務はない — 手動起動でよい)")
    return 1


def print_full_note(root: Path, data: dict) -> None:
    """全数(`all`)の最終実行を注記で出す。**判定には1バイトも効かない**(計器である)。

    増分では回らない検査が在る(用語の例が埋まっているかの点検・決定の見直す条件の発火 — flows.md §2.1)ので、
    「一度も全数を回さないまま green」を人間に見えるようにするための1行である。
    """
    marks = data.get("full", {})
    now = datetime.now(timezone.utc)
    parts = []
    for flow, scope in needed(root):
        if flow == "verify-tests":       # F4 は毎回が全数なので印を持たない(inspection-16 D1)
            continue
        k = key(flow, scope)
        e = marks.get(k)
        if not e:
            parts.append(f"{k}: 一度も無い")
            continue
        ts = str(e.get("at", ""))
        try:
            age = (now - datetime.fromisoformat(ts)).days
            parts.append(f"{k}: {ts[:10]}({age}日前)")
        except ValueError:
            parts.append(f"{k}: {ts[:10]}")
    print("  注記: 全数(all)の最終実行 — " + " / ".join(parts))
    print("      (この行は判定に効かない。増分の green でデプロイゲートは閉じる — flows.md §2.1)")


def promote(root: Path) -> int:
    """awaiting-verify の記録を verified へ。**判定はその記録の時点で行う**。

    フローごとに「全体スタンプ(最終 green — red はこれを消さない。判断4)以降、
    その記録の commit までに動いた依存」を出し、1本ずつ
    「それを覆う green が在るか」を見る。動いた依存がゼロなら、その記録はそのフローの
    判断を1バイトも動かしていないので満たしている。`is_ancestor(記録, 鮮度スタンプ)` が真の
    ときは区間が空になるので、**従来の規則はこの規則の特殊形**である(退行しない)。
    """
    data = load_stamps(root)
    need = needed(root)
    moved = skipped = 0
    for path, state, commit in record_states(root):
        if state != "awaiting-verify":
            continue
        if not re.fullmatch(r"[0-9a-f]{7,40}", commit or ""):
            print(f"保留: {path.name} — commit が記録されていない({commit or '空'})")
            skipped += 1
            continue
        holds = []
        for flow, scope in need:
            k = key(flow, scope)
            # 基準は最終 green(latest が red でも消えない — 判断4)。その記録の区間が
            # 覆われているかだけを見る: 現在 red ならデプロイゲート(check)が別に止めるので、
            # ここで二重に止めない — 記録の検証済みは、後から出た red で嘘にならない
            entry = green_entry(data, k)
            prefixes, undeclared = depends(root, flow, scope)
            excl = dep_excludes(root, flow, scope)
            if undeclared:
                holds.append(f"{k}: コードの置き場が未宣言(code_roots)")
                continue
            if not entry:
                holds.append(f"{k} の green 鮮度スタンプが無い")
                continue
            if "code_roots" in entry \
                    and sorted(entry.get("code_roots") or []) \
                    != sorted(resolved_roots(root, flow, scope) or []):
                holds.append(f"{k}: code_roots / ui_roots / scope_roots の宣言が記録時と違う")
                continue
            if resolved_roots(root, flow, scope) is not None \
                    and sorted(entry.get("code_excludes") or []) != sorted(code_excludes(root)):
                holds.append(f"{k}: code_excludes の宣言が記録時と違う")
                continue
            if dep_key(flow, scope) in ("verify-tests:e2e", "verify-tests:qa") \
                    and entry.get("e2e_scripts_in", "system") != e2e_scripts_in(root):
                holds.append(f"{k}: e2e_scripts_in の宣言が記録時と違う")
                continue
            if is_ancestor(root, commit, str(entry.get("commit", ""))):
                continue          # 記録が鮮度スタンプの祖先 = 区間は空(flows.md §2。inspection-16 H-1)
            window = changed_between(root, str(entry.get("commit", "")), commit)
            if window is None:              # 比べられない = fail-closed で保留
                holds.append(f"{k}: 鮮度スタンプの commit "
                             f"{str(entry.get('commit', ''))[:12]} と記録の commit を比べられない")
                continue
            parts, cache = partials(data, k), {}
            base = str(entry.get("commit", ""))
            for p in sorted({q for q in window if depends_on(q, prefixes, excl)
                             and not machine_owned_only(root, base, commit, q)}):
                win = cover_winner(root, parts, p, cache, commit)
                if win is None or win.get("verdict") != "green":
                    holds.append(f"{k}: {p} を覆う green が無い")
                    break
        if holds:
            print(f"保留: {path.name} — {holds[0]}(ほか {len(holds) - 1} 件)"
                  if len(holds) > 1 else f"保留: {path.name} — {holds[0]}")
            skipped += 1
            continue
        text = path.read_text(encoding="utf-8")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        text = re.sub(r"(?m)^state:\s*awaiting-verify\s*$", "state: verified", text, count=1)
        text = re.sub(r"(?m)^updated:\s*.*$", f"updated: {now}", text, count=1)
        path.write_text(text, encoding="utf-8")
        print(f"遷移: {path.name} awaiting-verify → verified")
        moved += 1
    print(f"promote: 遷移 {moved} 件 / 保留 {skipped} 件")
    return 0


def show(root: Path) -> int:
    data = load_stamps(root)
    latest = data["latest"]
    if not latest:
        print("鮮度スタンプなし(verify 系フローがまだ一度も完走していない)")
        return 0
    for k in sorted(latest):
        e = latest[k]
        print(f"{k}: {e.get('verdict')} @ {str(e.get('commit', ''))[:12]} ({e.get('at')})")
        g = green_entry(data, k)
        if g and e.get("verdict") != "green":
            print(f"    最終green @ {str(g.get('commit', ''))[:12]} ({g.get('at')}) "
                  "— 増分の基準点(red はこれを消さない)")
        for pe in partials(data, k):
            print(f"    部分 {pe.get('verdict')} @ {str(pe.get('commit', ''))[:12]} "
                  f"({pe.get('at')}) 覆い: {', '.join(pe.get('covers', ()))}")
        fe = data.get("full", {}).get(k)
        if fe:
            print(f"    全数 {fe.get('verdict')} @ {str(fe.get('commit', ''))[:12]} "
                  f"({fe.get('at')})")
    return 0


def deps(root: Path, which: str | None) -> int:
    """依存集合を印字する。**規範はこの出力を指す**(同じものを2箇所に書かない)。"""
    for flow, scope in needed(root):
        k = key(flow, scope)
        if which and which not in (k, flow):
            continue
        prefixes, undeclared = depends(root, flow, scope)
        note = "  ← コードの置き場が未宣言(flow-config.local.json の code_roots)" \
            if undeclared else ""
        print(f"{k}: {', '.join(prefixes) if prefixes else '(なし)'}{note}")
        w = widened(root, flow, scope)
        if w:
            print(f"    ← {w}。code_roots 全体で判定している(過大近似 = 安全側)。"
                  "宣言すれば範囲が縮む")
        excl = dep_excludes(root, flow, scope)
        if excl:
            print(f"    ただし除外(動いても失効させない): {', '.join(excl)}")
    print("※ ここに載っていないパスは、何が動いても鮮度スタンプを失効させない(許可リスト)。")
    return 0



RELEASES = Path(".claude/state/releases.json")
FIRST_VERSION = "0.9.0"

# 構築記録の「外部挙動の変化」の宣言。**値まで読む** ★ — 語の存在だけを見ていた間、
# ここは誰にも読まれない1行だった。**判定はこの1箇所が持つ** — `check-buildrecord.py` は
# これを import して使う(同じ規則を二度実装しない)。
_DECL_VERSION = re.compile(r"\A\d+\.\d+\.\d+\Z")
# **接頭辞では見ない** ★ — `あり(後方互換XYZ)` や、説明の無い `あり(互換を壊す。)` を
# 通すと、非互換の変更が小さい桁で出ていく(独立検査 2026-09-04 の実測)。
# 括弧を閉じていること、区切りの後に**説明が1文字以上在ること**まで求める。
_DECL = (
    ("壊す", re.compile(r"\Aあり\s*[((]\s*互換を壊す[。.、,]\s*\S[^))]*[))]\s*\Z")),
    ("あり", re.compile(r"\Aあり\s*[((]\s*後方互換[。.、,]\s*\S[^))]*[))]\s*\Z")),
    ("なし", re.compile(r"\Aなし\s*[。.]?\s*\Z")),
)
_BEHAVIOUR_LINE = re.compile(r"(?m)^-\s*外部挙動の変化\s*[::]\s*(.+?)\s*$")
_CLAIMS_HEAD = re.compile(r"(?m)^#{2,}\s*主張\s*$")


def behaviour_change(text: str) -> str:
    """構築記録の宣言を3値に読む。**3つのどれでもなければ `不明`**(fail-closed)。

    **読むのは `## 主張` の節だけである** ★ — ファイル全体を見ると、背景や引用の中の
    同じ形の行を拾う(独立検査 2026-09-04 の実測: `## 背景` の1行で major が動いた)。
    **規則も入力も、入口(`check-buildrecord.py` BRC4)と出口(リリース)で同じにする。**
    「なしだが変更あり」のような言い回しは通さない — 通せば、その記録は構築フローの
    出口を抜けたのにリリースで止まる。
    """
    m = _CLAIMS_HEAD.search(text)
    if not m:
        return "不明"
    rest = text[m.end():]
    nxt = re.search(r"(?m)^#{2,}\s", rest)
    claims = rest[:nxt.start()] if nxt else rest
    hits = _BEHAVIOUR_LINE.findall(claims)
    if len(hits) != 1:
        # **2行在れば拒む** ★ — 先頭を採ると、`なし` と `あり(互換を壊す。…)` が並んだ記録が
        # revision で出ていく(独立検査 2026-09-04 の実測)。宣言は1つである。
        return "不明"
    for name, rx in _DECL:
        if rx.match(hits[0]):
            return name
    return "不明"


def load_releases(root: Path) -> list[dict] | None:
    """リリース台帳。**新しいものが先頭**。ファイルが無ければ空(まだ1度もリリースしていない)。
    **読めなければ None** ★ — 壊れた台帳を「未リリース」と読むと、次の release が
    履歴を捨てて最初から書き直す(fail-open。独立検査 2026-09-04 の実測)。
    """
    path = root / RELEASES
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    rel = data.get("releases") if isinstance(data, dict) else None
    if not isinstance(rel, list) or any(not isinstance(r, dict) for r in rel):
        return None
    return rel


def save_releases(root: Path, releases: list[dict]) -> None:
    path = root / RELEASES
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"releases": releases}, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def _is_ancestor(root: Path, a: str, b: str) -> bool | None:
    """a が b の祖先か。判定できなければ None。"""
    try:
        r = subprocess.run(["git", "merge-base", "--is-ancestor", a, b],
                           cwd=root, capture_output=True, text=True)
    except OSError:
        return None
    return r.returncode == 0 if r.returncode in (0, 1) else None


def next_version(prev: str, kinds: list[str]) -> tuple[str, str]:
    """前の版と、区間の宣言の集まりから、次の版とその理由を返す。**最大値を採る。**"""
    try:
        ma, mi, rv = (int(x) for x in prev.split("."))
    except ValueError:                 # pragma: no cover — 台帳が壊れている
        return prev, "前の版が読めない"
    if "壊す" in kinds:
        return f"{ma + 1}.0.0", "major: 互換を壊す変更が在る"
    if "あり" in kinds:
        return f"{ma}.{mi + 1}.0", "minor: 外部の振る舞いが増えた"
    return f"{ma}.{mi}.{rv + 1}", "revision: 外部の振る舞いは変わっていない"


def release(root: Path, show_current: bool = False) -> int:
    """リリースを1件記録する。**版は機械が決める** — 人間は桁を指定しない。

    拒む条件(どれも fail-closed):台帳が読めない / 版が3つ組でない / デプロイゲートが red /
    未コミットの変更が在る / 区間の構築記録に読めない宣言または `commit:` の欠けたものが在る。
    **同じ commit を二度リリースしたことにはしない**(状態が同じなら出来事も同じである)。
    """
    releases = load_releases(root)
    if releases is None:
        print(f"{RELEASES} が読めない — 手で直すまでリリースしない"
              "(壊れた台帳を未リリースと読むと履歴を捨てる)", file=sys.stderr)
        return 2
    if show_current:
        if not releases:
            print("まだ1度もリリースしていない", file=sys.stderr)
            return 1
        v = str(releases[0].get("version", ""))
        if not _DECL_VERSION.match(v):
            print(f"台帳の先頭の版が3つ組でない: {v!r}", file=sys.stderr)
            return 2
        print(v)
        return 0
    if releases and not _DECL_VERSION.match(str(releases[0].get("version", ""))):
        print(f"台帳の先頭の版が3つ組でない: {releases[0].get('version')!r} — 手で直す",
              file=sys.stderr)
        return 2
    if check(root) != 0:
        print("リリースしない: デプロイゲートが red である(上の理由を先に閉じる)", file=sys.stderr)
        return 1
    d = dirty(root)
    if d is None or d:
        print("リリースしない: 未コミットの変更が在る — 先にコミットする", file=sys.stderr)
        return 1
    sha = head(root)
    if not sha:
        print("リリースしない: HEAD が読めない", file=sys.stderr)
        return 2
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    if not releases:
        # **最初のリリースは桁を計算しない** ★ — 区間の始点が無く、過去の構築記録は
        # この仕組みが無かった頃の書式である。**遡って埋め直さない**(baseline.md §4.3)。
        save_releases(root, [{"version": FIRST_VERSION, "commit": sha, "at": now,
                              "reason": "最初のリリース(桁は計算していない)", "records": 0}])
        print(f"リリース {FIRST_VERSION} を記録した({sha})")
        return 0
    prev = releases[0]
    moved = changed_between(root, str(prev.get("commit", "")), sha)
    if moved is None:
        print("リリースしない: 台帳が指すコミットがこの複製に無い — "
              "**浅い複製(`--depth`)では起きる**。全部の履歴を持つ複製で打つか、台帳を確かめる",
              file=sys.stderr)
        return 2
    # **台帳そのものの commit は「出した」ではない** ★ — §9.1 の手順が HEAD を進めるので、
    # 素朴に「同じ commit なら何もしない」と書くと二度目以降は必ず素通りする
    # (独立検査 2026-09-04 の実測: 打ち直すたびに revision が動いた)。
    if not [m for m in moved if not m.startswith(".claude/state/")]:
        print(f"リリースしない: 前回({prev.get('version')})から、"
              "リリースの台帳の外は1バイトも動いていない")
        return 0
    kinds: list[str] = []
    bad: list[str] = []
    counted = 0
    for path, state, commit in record_states(root):
        rel_path = str(path.relative_to(root))
        if not commit or commit == "-":
            # **黙って飛ばさない** ★ — 区間に置けない記録は、互換を壊す宣言を持っていても
            # 数から消える(独立検査 2026-09-04 の実測)。名指して拒む。
            bad.append(f"{rel_path}: `commit:` が無い")
            continue
        older = _is_ancestor(root, commit, prev.get("commit", ""))
        here = _is_ancestor(root, commit, sha)
        if older is None or here is None:
            bad.append(f"{rel_path}: `commit:` を git が解決できない({commit})")
            continue
        if older:
            continue                   # 前回のリリースに含まれている
        if not here:
            # **黙って落とさない** ★ — この記録は HEAD の木に在るのに、その `commit:` が
            # HEAD から辿れない(cherry-pick、マージの revert、枝の作り直し)。
            # 区間に置けないものを数から消すと、互換を壊す宣言がそこで消える。
            bad.append(f"{rel_path}: `commit:` が HEAD から辿れない({commit})")
            continue
        counted += 1
        kind = behaviour_change(path.read_text(encoding="utf-8", errors="replace"))
        if kind == "不明":
            bad.append(f"{rel_path}: 外部挙動の変化が3つの値のどれでもない")
        else:
            kinds.append(kind)
    if bad:
        print("リリースしない: 区間に置けない構築記録が在る — 下の1件ずつを直す"
              "(宣言なら「なし / あり(後方互換。…)/ あり(互換を壊す。…)」のどれかに、"
              "`commit:` ならその記録が実際に入ったコミットに):", file=sys.stderr)
        for b in bad:
            print(f"  {b}", file=sys.stderr)
        return 2
    version, reason = next_version(str(prev.get("version", FIRST_VERSION)), kinds)
    save_releases(root, [{"version": version, "commit": sha, "at": now,
                          "reason": reason, "records": counted}] + releases)
    print(f"リリース {version} を記録した({sha}) — {reason} / 構築記録 {counted}件")
    return 0

def main(argv: list[str]) -> int:
    args = argv[1:]
    if "--selftest" in args:
        return selftest()
    if not args or any(a in ("-h", "--help") for a in args):
        print(__doc__)
        return 0 if args else 2
    root = find_root(Path.cwd())
    cmd, rest = args[0], args[1:]
    if cmd == "record":
        scopes: list[str] = []
        covers: list[str] = []
        pos: list[str] = []
        full = False
        lens: str | None = None
        i = 0
        while i < len(rest):
            if rest[i] == "--scope" and i + 1 < len(rest):
                scopes.append(rest[i + 1]); i += 2; continue
            if rest[i] == "--covers" and i + 1 < len(rest):
                covers.append(rest[i + 1]); i += 2; continue
            if rest[i] == "--lens" and i + 1 < len(rest):
                lens = rest[i + 1]; i += 2; continue
            if rest[i] == "--full":
                full = True; i += 1; continue
            pos.append(rest[i]); i += 1
        if len(pos) != 2:
            print("使い方: stamps.py record <flow> <green|red> [--scope <s>]... "
                  "[--covers <path>]... [--full] [--lens <名前>]", file=sys.stderr)
            return 2
        with state_lock(root):
            return record(root, pos[0], pos[1], scopes, covers, full, lens)
    if cmd == "check":
        return check(root)
    if cmd == "promote":
        with state_lock(root):
            return promote(root)
    if cmd == "show":
        return show(root)
    if cmd == "deps":
        return deps(root, rest[0] if rest else None)
    if cmd == "release":
        if rest and rest != ["--current"]:
            print("使い方: stamps.py release [--current]", file=sys.stderr)
            return 2
        if rest:                       # 版を読むだけ。状態を作らない(組み立てが叩く経路)
            return release(root, show_current=True)
        with state_lock(root):
            return release(root)
    print(__doc__)
    return 2


def selftest() -> int:
    import contextlib, io, os, tempfile
    previous = Path.cwd()
    quiet = contextlib.redirect_stdout(io.StringIO())
    silent = contextlib.redirect_stderr(io.StringIO())   # 異常系の使い方エラーも飲み込む
    with tempfile.TemporaryDirectory() as td, quiet, silent:
        root = Path(td)
        (root / ".claude/scripts").mkdir(parents=True)
        (root / "CLAUDE.md").write_text("x", encoding="utf-8")
        os.chdir(root)
        run = lambda *a: subprocess.run(a, cwd=root, capture_output=True, check=True)
        run("git", "init", "-q")
        run("git", "-c", "user.email=t@t", "-c", "user.name=t",
            "commit", "-q", "--allow-empty", "-m", "c1")

        def commit(msg: str) -> None:
            run("git", "add", "-A")
            run("git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", msg)

        local = root / ".claude/scripts/flow-config.local.json"
        # コードの置き場が未宣言なら F3/F4 は red(fail-closed。黙って穴にしない)
        assert main(["x", "record", "verify-impl", "green"]) == 0
        assert stamp_state(root, load_stamps(root), "verify-impl")[0] == "未宣言", \
            "code_roots 未宣言なのに判定が出た"
        local.write_text(json.dumps({"code_roots": ["src/"]}), encoding="utf-8")
        assert main(["x", "check"]) == 1, "未実施で green になった"
        assert main(["x", "record", "verify-docs", "green"]) == 0
        assert main(["x", "record", "verify-impl", "green"]) == 0
        assert main(["x", "record", "verify-tests", "green",
                     "--scope", "unit", "--scope", "integration",
                     "--scope", "e2e", "--scope", "qa"]) == 0
        assert main(["x", "check"]) == 0, "全 green で red になった"
        # red の記録はデプロイゲートを止める
        assert main(["x", "record", "verify-tests", "red", "--scope", "unit"]) == 0
        assert main(["x", "check"]) == 1, "red 混在で green になった"
        assert main(["x", "record", "verify-tests", "green", "--scope", "unit"]) == 0
        # 宣言していないパス(同梱物・設定・未追跡)は**何が動いても失効させない**
        (root / "externals").mkdir(); (root / "externals/bin").write_text("y", encoding="utf-8")
        (root / ".gitignore").write_text("tmp/\n", encoding="utf-8")
        commit("c1b")
        (root / "untracked.conf").write_text("z", encoding="utf-8")
        assert main(["x", "check"]) == 0, "宣言外のパスがデプロイゲートを止めた(許可リストが効いていない)"
        # 依存(宣言したコード)が動くと失効する
        (root / "src").mkdir(); (root / "src/a.py").write_text("x", encoding="utf-8")
        commit("c2")
        assert main(["x", "check"]) == 1, "コードが動いたのに green のまま"
        # ただし docs/ の外は verify-docs を失効させない
        assert stamp_state(root, load_stamps(root), "verify-docs")[0] == "green", \
            "コード変更が F2 を失効させた"
        # ここまでを一度覆い直してから、02 の散文だけを動かす
        assert main(["x", "record", "verify-docs", "green"]) == 0
        assert main(["x", "record", "verify-impl", "green"]) == 0
        assert main(["x", "record", "verify-tests", "green", "--scope", "unit",
                     "--scope", "integration", "--scope", "e2e", "--scope", "qa"]) == 0
        # 02 の散文は unit/integration を失効させない(本日の実害そのもの)
        (root / "docs/02-design").mkdir(parents=True)
        (root / "docs/02-design/architecture.md").write_text("a", encoding="utf-8")
        commit("c2b")
        assert stamp_state(root, load_stamps(root), "verify-tests", "unit")[0] == "green", \
            "02 の散文で unit が失効した"
        assert stamp_state(root, load_stamps(root), "verify-impl")[0] == "失効", \
            "02 が動いたのに F3 が失効しない"
        # 部分再検証: 覆った範囲だけが閉じ、覆えていない範囲は最小の一覧として残る
        st, _, uncovered = stamp_state(root, load_stamps(root), "verify-impl")
        assert uncovered == ["docs/02-design/architecture.md"], \
            f"失効の一覧が最小になっていない: {uncovered}"
        (root / "src/a.py").write_text("x2", encoding="utf-8")
        commit("c2c")
        st, _, uncovered = stamp_state(root, load_stamps(root), "verify-impl")
        assert uncovered == ["docs/02-design/architecture.md", "src/a.py"], uncovered
        assert main(["x", "record", "verify-impl", "green",
                     "--covers", "docs/02-design/architecture.md"]) == 0
        st, _, uncovered = stamp_state(root, load_stamps(root), "verify-impl")
        assert st == "失効" and uncovered == ["src/a.py"], \
            f"部分再検証で閉じた範囲が残っている: {uncovered}"
        assert main(["x", "record", "verify-impl", "green", "--covers", "src/"]) == 0
        assert stamp_state(root, load_stamps(root), "verify-impl")[0] == "green", \
            "全部の依存を覆ったのに green にならない"
        # 覆った後にもう一度動いたら、その覆いは効かない(要件3の要)
        (root / "src/a.py").write_text("x3", encoding="utf-8")
        commit("c2d")
        st, _, uncovered = stamp_state(root, load_stamps(root), "verify-impl")
        assert st == "失効" and uncovered == ["src/a.py"], \
            f"覆った後の変更が見逃された: {st} {uncovered}"
        assert main(["x", "record", "verify-impl", "green", "--covers", "src/"]) == 0
        # 依存の外を覆ったと書かせない
        assert main(["x", "record", "verify-impl", "green", "--covers", "externals/"]) == 2, \
            "依存集合の外の --covers が通った"
        # 記録類だけの変更は何も失効させない(verified の記録はデプロイゲートを止めない)
        assert main(["x", "record", "verify-docs", "green"]) == 0
        assert main(["x", "record", "verify-impl", "green"]) == 0
        assert main(["x", "record", "verify-tests", "green", "--scope", "unit",
                     "--scope", "integration", "--scope", "e2e", "--scope", "qa"]) == 0
        # 台帳ディレクトリの欠落は「0件」ではなく NG(fail-closed — inspection-17 M-13)
        assert main(["x", "check"]) == 1, "台帳ディレクトリが無いのにデプロイゲートが green になった"
        (root / "docs/build-records").mkdir(parents=True)
        (root / "docs/sheets").mkdir(parents=True)
        (root / "docs/issues").mkdir(parents=True)
        (root / "docs/build-records/r.md").write_text(
            "---\nslug: r\nstate: verified\nupdated: 2026-08-20T00:00:00+00:00\n---\n",
            encoding="utf-8")
        run("git", "add", "."); run("git", "-c", "user.email=t@t", "-c", "user.name=t",
                                    "commit", "-q", "-m", "c3")
        assert main(["x", "check"]) == 0, "記録類の変更がデプロイゲートを止めた"
        # building の記録は複合のデプロイゲートを止める
        (root / "docs/build-records/b.md").write_text(
            "---\nslug: b\nstate: building\n---\n", encoding="utf-8")
        assert main(["x", "check"]) == 1, "building 記録があるのに green になった"
        (root / "docs/build-records/b.md").unlink()
        # 未回答シート・bug issue も止める
        (root / "docs/sheets/s.md").write_text("x", encoding="utf-8")
        assert main(["x", "check"]) == 1, "未回答シートがあるのに green になった"
        (root / "docs/sheets/s.md").unlink()
        (root / "docs/issues/001-bug-x.md").write_text(
            "---\ntype: bug\nseverity: 高\n---\n", encoding="utf-8")
        assert main(["x", "check"]) == 1, "type: bug かつ severity: 高 の課題票があるのに green になった"
        (root / "docs/issues/001-bug-x.md").unlink()
        (root / "docs/issues/002-bug-q.md").write_text(
            '---\ntype: "bug"\nseverity: "高"\n---\n', encoding="utf-8")
        assert main(["x", "check"]) == 1, "引用符付きの bug + 高 を見逃した"
        (root / "docs/issues/002-bug-q.md").unlink()
        # --- inspection-19 D-2: **かつ** である。片方だけの課題票はデプロイゲートを止めない
        (root / "docs/issues/003-bug-mid.md").write_text(
            "---\ntype: bug\nseverity: 中\n---\n", encoding="utf-8")
        assert main(["x", "check"]) == 0, "severity: 中 の bug がデプロイゲートを止めた(D-2 は and)"
        (root / "docs/issues/003-bug-mid.md").unlink()
        (root / "docs/issues/004-task-high.md").write_text(
            "---\ntype: task\nseverity: 高\n---\n", encoding="utf-8")
        assert main(["x", "check"]) == 0, "bug でない severity: 高 がデプロイゲートを止めた(D-2 は and)"
        (root / "docs/issues/004-task-high.md").unlink()
        # promote: **依存を動かしていない記録**は、古い鮮度スタンプでも遷移してよい
        sha3 = head(root)               # c3 は記録類しか動かしていない
        (root / "docs/build-records/d.md").write_text(
            f"---\nslug: d\nstate: awaiting-verify\ncommit: {sha3}\n"
            "updated: 2026-08-20T00:00:00+00:00\n---\n", encoding="utf-8")
        # 依存(コード)を動かした記録は、それを覆う green が出るまで保留
        (root / "src/b.py").write_text("y", encoding="utf-8")
        commit("c4")
        sha4 = head(root)
        (root / "docs/build-records/a.md").write_text(
            f"---\nslug: a\nstate: awaiting-verify\ncommit: {sha4}\n"
            "updated: 2026-08-20T00:00:00+00:00\n---\n", encoding="utf-8")
        assert main(["x", "check"]) == 1, "awaiting-verify があるのに green になった"
        main(["x", "promote"])
        assert "awaiting-verify" in (root / "docs/build-records/a.md").read_text(), \
            "覆っていないコード変更を含む記録が promote された"
        assert "state: verified" in (root / "docs/build-records/d.md").read_text(), \
            "依存を動かしていない記録が、無関係な鮮度スタンプの古さで止められた"
        assert main(["x", "record", "verify-impl", "green", "--covers", "src/"]) == 0
        assert main(["x", "record", "verify-tests", "green", "--scope", "unit",
                     "--scope", "integration", "--scope", "e2e", "--scope", "qa",
                     "--covers", "src/"]) == 0
        assert main(["x", "promote"]) == 0
        assert "state: verified" in (root / "docs/build-records/a.md").read_text(), \
            "部分再検証で覆ったのに promote が遷移しなかった"
        assert main(["x", "check"]) == 0, "promote 後に green にならない"
        # 通常経路: 記録の commit より**後**の全体スタンプは区間ゼロでその記録を充足する
        # (記録が鮮度スタンプの祖先 — inspection-16 H-1。旧実装はここで永久保留だった)
        (root / "src/d.py").write_text("z", encoding="utf-8")
        commit("c6")
        (root / "docs/build-records/e.md").write_text(
            f"---\nslug: e\nstate: awaiting-verify\ncommit: {head(root)}\n"
            "updated: 2026-08-20T00:00:00+00:00\n---\n", encoding="utf-8")
        (root / "docs/02-design/architecture.md").write_text("a2", encoding="utf-8")
        commit("c7")                    # verify フロー自身の書込みに相当する後続 commit
        assert main(["x", "record", "verify-docs", "green"]) == 0
        assert main(["x", "record", "verify-impl", "green"]) == 0
        assert main(["x", "record", "verify-tests", "green", "--scope", "unit",
                     "--scope", "integration", "--scope", "e2e", "--scope", "qa"]) == 0
        assert main(["x", "promote"]) == 0
        assert "state: verified" in (root / "docs/build-records/e.md").read_text(), \
            "記録より後の全体スタンプが在るのに promote が遷移しない(通常経路の非収束)"
        # 管理欄(updated・verified ブロック・version 行)だけの変更は失効を作らない
        # (inspection-16 D2 + 2026-08-25 の裁定 — version 行そのものが管理欄に入った)
        arch = root / "docs/02-design/architecture.md"
        arch.write_text("---\nid: arch\nversion: 1.2.3\nupdated: 2026-08-20\n---\n本文\n",
                        encoding="utf-8")
        commit("c7b")
        assert main(["x", "record", "verify-docs", "green"]) == 0
        assert main(["x", "record", "verify-impl", "green"]) == 0
        arch.write_text("---\nid: arch\nversion: 1.2.4\nupdated: 2026-08-21\n"
                        "verified:\n  at: 2026-08-21\n  version: 1.2\n---\n本文\n",
                        encoding="utf-8")
        commit("c7c")
        assert stamp_state(root, load_stamps(root), "verify-impl")[0] == "green", \
            "管理欄(updated・verified・version 行)だけの変更が F3 を失効させた"
        assert stamp_state(root, load_stamps(root), "verify-docs")[0] == "green", \
            "管理欄だけの変更が F2 を失効させた"
        # 本文が同一なら、MINOR / MAJOR の繰り上げも失効を作らない(2026-08-25)。
        # 証明書を打ち直すだけの run が版だけ上げて相手フローを殺す構造を消すためである。
        arch.write_text("---\nid: arch\nversion: 1.3.0\nupdated: 2026-08-21\n---\n本文\n",
                        encoding="utf-8")
        commit("c7d")
        assert stamp_state(root, load_stamps(root), "verify-impl")[0] == "green", \
            "本文が同一なのに MINOR の版上げだけで F3 が失効した"
        arch.write_text("---\nid: arch\nversion: 2.0.0\nupdated: 2026-08-21\n---\n本文\n",
                        encoding="utf-8")
        commit("c7d2")
        assert stamp_state(root, load_stamps(root), "verify-docs")[0] == "green", \
            "本文が同一なのに MAJOR の版上げだけで F2 が失効した"
        # 版が据え置きでも本文が動けば失効する — 上の緩和が穴でないことの裏
        arch.write_text("---\nid: arch\nversion: 2.0.0\nupdated: 2026-08-21\n---\n本文2\n",
                        encoding="utf-8")
        commit("c7e")
        assert stamp_state(root, load_stamps(root), "verify-impl")[0] == "失効", \
            "本文の変更が失効を作らない"
        # 管理欄以外の frontmatter(source: など)が動いても失効する
        assert main(["x", "record", "verify-impl", "green"]) == 0
        arch.write_text("---\nid: arch\nversion: 2.0.0\nupdated: 2026-08-21\n"
                        "source:\n  - docs/01-requirements/functional.md\n---\n本文2\n",
                        encoding="utf-8")
        commit("c7e2")
        assert stamp_state(root, load_stamps(root), "verify-impl")[0] == "失効", \
            "管理欄以外の frontmatter の変更が失効を作らない"
        # 機械の欄(GENERATED 区画)の中身だけの変更は失効を作らない(2026-08-27)。
        # **除外はパス単位では書けない** — ファイルごと外すと手書き部分の変更まで
        # 失効しなくなるので、管理欄と同じ区画単位の判定にしてある。
        arch.write_text("---\nid: arch\nversion: 2.0.0\nupdated: 2026-08-21\n---\n本文2\n"
                        "<!-- BEGIN GENERATED: build-facts.py id=n -->\n31本\n"
                        "<!-- END GENERATED: build-facts.py -->\n", encoding="utf-8")
        commit("c7g")
        assert main(["x", "record", "verify-docs", "green"]) == 0
        assert main(["x", "record", "verify-impl", "green"]) == 0
        arch.write_text("---\nid: arch\nversion: 2.0.0\nupdated: 2026-08-21\n---\n本文2\n"
                        "<!-- BEGIN GENERATED: build-facts.py id=n -->\n33本\n"
                        "<!-- END GENERATED: build-facts.py -->\n", encoding="utf-8")
        commit("c7g2")
        assert stamp_state(root, load_stamps(root), "verify-docs")[0] == "green", \
            "機械の欄の中身だけの変更が F2 を失効させた"
        # 区画の外(手書き)が動けば、同じファイルでもそのまま失効する — 穴でないことの裏
        arch.write_text("---\nid: arch\nversion: 2.0.0\nupdated: 2026-08-21\n---\n本文3\n"
                        "<!-- BEGIN GENERATED: build-facts.py id=n -->\n33本\n"
                        "<!-- END GENERATED: build-facts.py -->\n", encoding="utf-8")
        commit("c7g3")
        assert stamp_state(root, load_stamps(root), "verify-docs")[0] == "失効", \
            "機械の欄を持つファイルの手書き部分の変更が失効を作らない(パス単位の除外の穴)"
        # 道具名を持たない**旧終端**(雛形 templates/03-index.md が配っている形)でも剥ぐ
        assert main(["x", "record", "verify-docs", "green"]) == 0
        arch.write_text("---\nid: arch\nversion: 2.0.0\nupdated: 2026-08-21\n---\n本文3\n"
                        "<!-- BEGIN GENERATED: build-index.py -->\n索引A\n"
                        "<!-- END GENERATED -->\n", encoding="utf-8")
        commit("c7h")
        assert main(["x", "record", "verify-docs", "green"]) == 0
        arch.write_text("---\nid: arch\nversion: 2.0.0\nupdated: 2026-08-21\n---\n本文3\n"
                        "<!-- BEGIN GENERATED: build-index.py -->\n索引B\n"
                        "<!-- END GENERATED -->\n", encoding="utf-8")
        commit("c7h2")
        assert stamp_state(root, load_stamps(root), "verify-docs")[0] == "green", \
            "道具名を持たない旧終端の機械の欄が剥がれていない(雛形が配っているのはこの形である)"
        arch.write_text("---\nid: arch\nversion: 2.0.0\nupdated: 2026-08-21\n---\n本文3\n"
                        "<!-- BEGIN GENERATED: build-facts.py id=n -->\n33本\n"
                        "<!-- END GENERATED: build-facts.py -->\n", encoding="utf-8")
        commit("c7h3")
        assert main(["x", "record", "verify-docs", "green"]) == 0
        # 区画そのものが消えたら、それは道具の持ち場が動いたということなので失効する
        assert main(["x", "record", "verify-docs", "green"]) == 0
        arch.write_text("---\nid: arch\nversion: 2.0.0\nupdated: 2026-08-21\n---\n本文3\n",
                        encoding="utf-8")
        commit("c7g4")
        assert stamp_state(root, load_stamps(root), "verify-docs")[0] == "失効", \
            "機械の欄そのものの消滅が失効を作らない"
        # 版の免除は「両側が正しい形の version をちょうど1行持つ」ときだけ(独立レビュー 所見1)。
        # 版を消す/壊す/重ねる変更は、版を本文と同じに扱うので失効する。
        arch.write_text("---\nid: arch\nversion: 3.0.0\nupdated: 2026-08-21\n---\n本文3\n",
                        encoding="utf-8")
        commit("c7f")
        assert main(["x", "record", "verify-docs", "green"]) == 0
        assert main(["x", "record", "verify-impl", "green"]) == 0
        arch.write_text("---\nid: arch\nupdated: 2026-08-21\n---\n本文3\n", encoding="utf-8")
        commit("c7f2")
        assert stamp_state(root, load_stamps(root), "verify-impl")[0] == "失効", \
            "version: 行の削除が失効を作らない(壊れた版が古い green を延命させる)"
        assert stamp_state(root, load_stamps(root), "verify-docs")[0] == "失効", \
            "version: 行の削除が F2 を失効させない"
        arch.write_text("---\nid: arch\nversion: 3.0.0\nupdated: 2026-08-21\n---\n本文3\n",
                        encoding="utf-8")
        commit("c7f3")
        assert main(["x", "record", "verify-impl", "green"]) == 0
        arch.write_text("---\nid: arch\nversion: broken\nupdated: 2026-08-21\n---\n本文3\n",
                        encoding="utf-8")
        commit("c7f4")
        assert stamp_state(root, load_stamps(root), "verify-impl")[0] == "失効", \
            "version: の不正値化が失効を作らない"
        arch.write_text("---\nid: arch\nversion: 3.0.0\nupdated: 2026-08-21\n---\n本文3\n",
                        encoding="utf-8")
        commit("c7f5")
        assert main(["x", "record", "verify-impl", "green"]) == 0
        arch.write_text("---\nid: arch\nversion: 3.0.0\nversion: 4.0.0\n"
                        "updated: 2026-08-21\n---\n本文3\n", encoding="utf-8")
        commit("c7f6")
        assert stamp_state(root, load_stamps(root), "verify-impl")[0] == "失効", \
            "version: の重複が失効を作らない"
        arch.write_text("---\nid: arch\nversion: 3.0.0\nupdated: 2026-08-21\n---\n本文3\n",
                        encoding="utf-8")
        commit("c7f7")
        assert main(["x", "record", "verify-impl", "green"]) == 0
        # 版の正規形は ASCII だけ(独立レビュー 2026-08-25 の所見1・第2回)。
        # 空白ゼロ・タブ・全角空白・全角数字は「正しい形」ではないので、そこへの書き換えは失効する。
        for i, bad in enumerate(("version:3.0.0", "version:\t3.0.0",
                                 "version:　3.0.0", "version: ３.０.０")):
            arch.write_text(f"---\nid: arch\n{bad}\nupdated: 2026-08-21\n---\n本文3\n",
                            encoding="utf-8")
            commit(f"c7g{i}")
            assert stamp_state(root, load_stamps(root), "verify-impl")[0] == "失効", \
                f"版の行を {bad!r} に変えても失効しない(ASCII 以外を正しい形として通した)"
            arch.write_text("---\nid: arch\nversion: 3.0.0\nupdated: 2026-08-21\n---\n本文3\n",
                            encoding="utf-8")
            commit(f"c7g{i}r")
            assert main(["x", "record", "verify-impl", "green"]) == 0
        # 行末の空白だけは正しい形のままである(退行を作らない)
        arch.write_text("---\nid: arch\nversion: 3.0.1 \nupdated: 2026-08-22\n---\n本文3\n",
                        encoding="utf-8")
        commit("c7h")
        assert stamp_state(root, load_stamps(root), "verify-impl")[0] == "green", \
            "行末の空白だけで失効した(PATCH の繰り上げは管理欄のままであるべき)"
        assert main(["x", "record", "verify-impl", "green"]) == 0
        assert main(["x", "record", "verify-docs", "green"]) == 0
        # e2e の 02 依存は system.md / testing.md / environments.md に絞られている(inspection-16 D3)
        assert stamp_state(root, load_stamps(root), "verify-tests", "e2e")[0] == "green", \
            "architecture.md の変更が e2e を失効させた(依存が 02 全体のまま)"
        assert stamp_state(root, load_stamps(root), "verify-tests", "qa")[0] == "green", \
            "architecture.md の変更が qa を失効させた(qa の 02 依存は system/environments に" \
            "絞られている — inspection-17 判断5)"
        (root / "docs/02-design/system.md").write_text("E2E-01 台本", encoding="utf-8")
        commit("c7f")
        assert stamp_state(root, load_stamps(root), "verify-tests", "e2e")[0] == "失効", \
            "system.md(台本の置き場)の変更が e2e を失効させない"
        assert stamp_state(root, load_stamps(root), "verify-tests", "qa")[0] == "失効", \
            "system.md(適用外の根拠の置き場)の変更が qa を失効させない"
        assert main(["x", "record", "verify-tests", "green", "--scope", "unit",
                     "--scope", "integration", "--scope", "e2e", "--scope", "qa"]) == 0
        (root / "docs/build-records/nc.md").write_text(
            "---\nslug: nc\nstate: awaiting-verify\ncommit: -\n---\n", encoding="utf-8")
        main(["x", "promote"])
        assert "awaiting-verify" in (root / "docs/build-records/nc.md").read_text(), \
            "commit 無しが promote された"
        (root / "docs/build-records/nc.md").unlink()
        # **依存に未コミットの変更が在るあいだ green は記録できない**(書いた瞬間の失効を作らない)
        (root / "src/c.py").write_text("dirty", encoding="utf-8")
        assert main(["x", "record", "verify-impl", "green"]) == 2, \
            "依存が汚れているのに green を記録できた"
        assert main(["x", "record", "verify-impl", "green", "--covers", "src/"]) == 2, \
            "覆いが汚れているのに部分 green を記録できた"
        assert main(["x", "record", "verify-impl", "red"]) == 0, "red が記録できない"
        # 依存の外(docs/ でも記録類)が汚れていても green は通る — 許可リストの帰結
        assert main(["x", "record", "verify-docs", "green"]) == 0, \
            "依存の外の汚れで F2 の green が止まった"
        commit("c5")
        assert main(["x", "record", "verify-impl", "green"]) == 0, "コミット後に記録できない"
        # 鮮度スタンプの commit == HEAD でも、未コミットの依存変更は green を残さない(inspection-16 H-2)
        (root / "src/c.py").write_text("dirty2", encoding="utf-8")
        assert stamp_state(root, load_stamps(root), "verify-impl")[0] == "失効", \
            "同一 HEAD の未コミット変更が見逃された"
        commit("c5b")
        assert main(["x", "record", "verify-impl", "green"]) == 0
        # 全数の印は別に持ち、**デプロイゲートにも失効判定にも効かない**
        assert main(["x", "record", "verify-docs", "green", "--full"]) == 0
        assert load_stamps(root)["full"]["verify-docs"]["commit"] == head(root), \
            "--full が全数の印を残さなかった"
        assert main(["x", "record", "verify-docs", "green", "--full",
                     "--covers", "docs/00-requests/"]) == 2, "--full と --covers が両立した"
        assert main(["x", "record", "verify-tests", "green", "--scope", "unit",
                     "--full"]) == 2, "F4 の --full が通った(F4 は全数の印を持たない)"
        assert main(["x", "record", "verify-tests", "green", "--scope", "unit",
                     "--scope", "integration", "--scope", "e2e", "--scope", "qa"]) == 0
        assert main(["x", "check"]) == 0, "全数の印がデプロイゲートの判定を変えた"
        # `partial` を持たない既存の stamps.json をそのまま読める(移行不要)
        old = {"latest": load_stamps(root)["latest"]}
        (root / STATE).write_text(json.dumps(old), encoding="utf-8")
        assert load_stamps(root)["latest"], "partial の無い既存ファイルが読めない"
        assert partials(load_stamps(root), "verify-impl") == [], "partial 既定が空でない"
        # code_roots の宣言変更は、焼き込んだ記録時の値との不一致で失効になる(inspection-16 D8)
        local.write_text(json.dumps({"code_roots": ["src/", "lib/"]}), encoding="utf-8")
        assert stamp_state(root, load_stamps(root), "verify-impl")[0] == "失効", \
            "code_roots の宣言変更が失効を作らない"
        local.write_text(json.dumps({"code_roots": ["src/"]}), encoding="utf-8")
        assert stamp_state(root, load_stamps(root), "verify-impl")[0] == "green", \
            "宣言を戻したのに green に戻らない"
        # f4_scopes の local 設定 — 受理する縮小は qa 外しだけ(それ以外は既定へ倒す fail-closed)
        local.write_text(json.dumps({"f4_scopes": ["unit", "integration", "e2e"],
                                     "code_roots": ["src/"]}), encoding="utf-8")
        assert f4_scopes(root) == ["unit", "integration", "e2e"], "qa 外しが効かない"
        local.write_text(json.dumps({"f4_scopes": ["unit"], "code_roots": ["src/"]}),
                         encoding="utf-8")
        assert f4_scopes(root) == DEFAULT_F4_SCOPES, "任意縮小の f4_scopes が素通りした"
        assert code_roots(root) == ["src/"], "local の code_roots が効かない"
        # --- inspection-17 判断4: 素の red は最終 green の基準点と部分記録を消さない
        (root / "src/e.py").write_text("v1", encoding="utf-8")
        commit("c8")
        assert main(["x", "record", "verify-impl", "green"]) == 0
        base_green = load_stamps(root)["last_green"]["verify-impl"]["commit"]
        # **覆い残しが在る部分記録は畳まれない**ので、部分スタンプが red を跨いで残る
        # (畳みの条件は「併合が green」— 下の 2026-08-25 の節がその表側を見る)
        (root / "src/e.py").write_text("v2", encoding="utf-8")
        (root / "src/f.py").write_text("v1", encoding="utf-8")
        commit("c9")
        assert main(["x", "record", "verify-impl", "green", "--covers", "src/e.py"]) == 0
        assert load_stamps(root)["last_green"]["verify-impl"]["commit"] == base_green, \
            "覆い残し(src/f.py)が在るのに基準点が進んだ"
        (root / "src/e.py").write_text("v3", encoding="utf-8")
        commit("c10")
        assert main(["x", "record", "verify-impl", "red"]) == 0
        data9 = load_stamps(root)
        assert data9["last_green"]["verify-impl"]["commit"] == base_green, \
            "red が最終 green の基準点を消した(判断4)"
        assert partials(data9, "verify-impl"), "red が部分スタンプを捨てた"
        st, _, unc = stamp_state(root, data9, "verify-impl")
        assert st == "red" and unc == ["src/e.py", "src/f.py"], \
            f"red でも最終 green 以降の増分範囲を出すはず: {st} {unc}"
        assert main(["x", "check"]) == 1, "red でデプロイゲートが開いた"
        assert main(["x", "record", "verify-impl", "green"]) == 0
        assert stamp_state(root, load_stamps(root), "verify-impl")[0] == "green", \
            "red の後の素の green で閉じない"
        # --- 2026-08-25: 部分が覆い切ったら基準点を進めて部分を畳む(相互失効が閉じない件)
        # 畳まないと「覆う義務のあるパス」の集合が単調に増え、互いの依存へ書く F2 と F3 を
        # 交互に回しても閉じなくなる(2026-08-23 の実測: 7周まわって green にならなかった)。
        base_before = load_stamps(root)["last_green"]["verify-impl"]["commit"]
        (root / "src/g.py").write_text("v1", encoding="utf-8")
        (root / "src/h.py").write_text("v1", encoding="utf-8")
        commit("c11")
        # 覆い残しが在るあいだは畳まない(fail-closed)
        assert main(["x", "record", "verify-impl", "green", "--covers", "src/g.py"]) == 0
        dataA = load_stamps(root)
        assert dataA["last_green"]["verify-impl"]["commit"] == base_before, \
            "覆い残しが在るのに基準点が進んだ"
        assert stamp_state(root, dataA, "verify-impl")[0] == "失効", \
            "覆い残し(src/h.py)が在るのに green になった"
        # 残りを覆った瞬間に併合が green になり、基準点が進んで部分が畳まれる
        assert main(["x", "record", "verify-impl", "green", "--covers", "src/h.py"]) == 0
        dataB = load_stamps(root)
        headB = head(root)
        assert dataB["last_green"]["verify-impl"]["commit"] == headB, \
            "覆い切ったのに最終 green の基準点が進まない"
        assert dataB["latest"]["verify-impl"]["commit"] == headB, \
            "覆い切ったのに latest が進まない"
        assert partials(dataB, "verify-impl") == [], "畳んだはずの部分スタンプが残っている"
        assert stamp_state(root, dataB, "verify-impl")[0] == "green", \
            "畳んだ後に green でなくなった"
        # **畳みは主張を広げない**: 畳んだ後にその依存が動けば、そのまま失効する
        (root / "src/g.py").write_text("v2", encoding="utf-8")
        commit("c12")
        st, _, unc = stamp_state(root, load_stamps(root), "verify-impl")
        assert st == "失効" and unc == ["src/g.py"], \
            f"畳んだ後の変更が失効を作らない(fail-open): {st} {unc}"
        assert main(["x", "record", "verify-impl", "green", "--covers", "src/g.py"]) == 0
        assert stamp_state(root, load_stamps(root), "verify-impl")[0] == "green", \
            "畳んだ基準点からの部分再検証で閉じない"
        # **`red --covers` は畳まない**(独立レビュー 2026-08-25 の所見)。追記前の全体 green を
        # 基準に判定するので併合は green になりうるが、そこで畳むと red の entry が
        # latest / last_green へ入り、「素の red は最終 green を消さない」を破る。
        base_red = load_stamps(root)["last_green"]["verify-impl"]["commit"]
        assert stamp_state(root, load_stamps(root), "verify-impl")[0] == "green", \
            "前提: ここは green のはず(基準点以降の依存変更が0件)"
        assert main(["x", "record", "verify-impl", "red", "--covers", "src/g.py"]) == 0
        dataR = load_stamps(root)
        assert dataR["last_green"]["verify-impl"]["commit"] == base_red, \
            "red の部分記録が最終 green の基準点を上書きした"
        assert dataR["last_green"]["verify-impl"]["verdict"] == "green", \
            "last_green に red の判定が入った"
        # **直近の判定は red へ進む** — 進めないと、基準点以降の依存変更が0件のとき
        # `check` が以前の green を読んでデプロイゲートを開く(red と分かっている範囲を
        # 抱えたまま出荷できる)
        assert dataR["latest"]["verify-impl"]["verdict"] == "red", \
            "red の部分記録が直近の判定(latest)に出ていない"
        assert stamp_state(root, dataR, "verify-impl")[0] == "red", \
            "red の部分記録の後に判定が green のまま"
        assert main(["x", "check"]) == 1, "red の部分記録を抱えたままデプロイゲートが開いた"
        assert partials(dataR, "verify-impl"), "red の部分記録が畳まれて消えた"
        assert [e for e in partials(dataR, "verify-impl") if e.get("verdict") == "red"], \
            "red の部分記録が残っていない"
        # **`--covers` の green では latest が red のまま閉じない**(flows.md §2)。
        # 閉じ直すのは素の green である
        assert main(["x", "record", "verify-impl", "green", "--covers", "src/g.py"]) == 0
        assert stamp_state(root, load_stamps(root), "verify-impl")[0] == "red", \
            "red を --covers の green で閉じてしまった"
        assert main(["x", "record", "verify-impl", "green"]) == 0   # 素の green で閉じ直す
        assert stamp_state(root, load_stamps(root), "verify-impl")[0] == "green", \
            "素の green で閉じ直せない"
        # 基準点が無いフローは、部分だけでは green にならない(畳みも起きない)
        fresh = {"latest": {k2: v for k2, v in load_stamps(root)["latest"].items()
                            if k2 != "verify-docs"},
                 "last_green": {k2: v for k2, v in load_stamps(root)
                                .get("last_green", {}).items() if k2 != "verify-docs"}}
        (root / STATE).write_text(json.dumps(fresh), encoding="utf-8")
        assert main(["x", "record", "verify-docs", "green",
                     "--covers", "docs/02-design/"]) == 0
        dataC = load_stamps(root)
        assert "verify-docs" not in dataC.get("last_green", {}), \
            "全体スタンプを1度も持たないフローが、部分だけで基準点を得た"
        assert stamp_state(root, dataC, "verify-docs")[0] == "未実施", \
            "全体スタンプの無いフローが部分だけで green になった"
        # --- inspection-17 判断6: 03 の試験表は unit/integration を失効させない
        # --- inspection-19 V-1: e2e の依存も tests/e2e.md 1本まで絞った(モジュールの表では失効しない)
        assert main(["x", "record", "verify-tests", "green", "--scope", "unit",
                     "--scope", "integration", "--scope", "e2e", "--scope", "qa"]) == 0
        (root / "docs/03-impl/tests").mkdir(parents=True)
        (root / "docs/03-impl/tests/mod.md").write_text("表", encoding="utf-8")
        commit("c11")
        assert stamp_state(root, load_stamps(root), "verify-tests", "unit")[0] == "green", \
            "試験表(docs/03-impl/tests/)の変更が unit を失効させた(判断6)"
        assert stamp_state(root, load_stamps(root), "verify-tests", "integration")[0] == "green", \
            "試験表の変更が integration を失効させた(判断6)"
        assert stamp_state(root, load_stamps(root), "verify-tests", "e2e")[0] == "green", \
            "モジュールの試験表の変更が e2e を失効させた(V-1 で依存から外したはず)"
        (root / "docs/03-impl/tests/e2e.md").write_text("台本", encoding="utf-8")
        commit("c11b")
        assert stamp_state(root, load_stamps(root), "verify-tests", "e2e")[0] == "失効", \
            "tests/e2e.md の変更が e2e を失効させない(e2e の依存に残っているはず)"
        assert main(["x", "record", "verify-tests", "green", "--scope", "e2e"]) == 0
        # --- inspection-17 判断5: qa のコード依存は ui_roots(未宣言なら code_roots 全体)
        (root / "src/api.py").write_text("b1", encoding="utf-8")
        commit("c12")
        assert stamp_state(root, load_stamps(root), "verify-tests", "qa")[0] == "失効", \
            "ui_roots 未宣言なのにコード変更で qa が失効しない(安全側の既定が壊れた)"
        local.write_text(json.dumps({"code_roots": ["src/"], "ui_roots": ["src/ui/"]}),
                         encoding="utf-8")
        assert main(["x", "record", "verify-tests", "green", "--scope", "qa"]) == 0
        (root / "src/api.py").write_text("b2", encoding="utf-8")
        commit("c13")
        assert stamp_state(root, load_stamps(root), "verify-tests", "qa")[0] == "green", \
            "ui_roots の外(バックエンド)の変更が qa を失効させた(判断5)"
        assert stamp_state(root, load_stamps(root), "verify-tests", "unit")[0] == "失効", \
            "コード変更が unit を失効させない"
        local.write_text(json.dumps({"code_roots": ["src/"]}), encoding="utf-8")
        assert stamp_state(root, load_stamps(root), "verify-tests", "qa")[0] == "失効", \
            "ui_roots の宣言変更が qa の失効を作らない(焼き込み — D8 と同型)"
        local.write_text(json.dumps({"code_roots": ["src/"], "ui_roots": ["src/ui/"]}),
                         encoding="utf-8")
        assert stamp_state(root, load_stamps(root), "verify-tests", "qa")[0] == "green", \
            "宣言を戻したのに qa が green に戻らない"
        (root / "src/ui").mkdir()
        (root / "src/ui/app.js").write_text("u1", encoding="utf-8")
        commit("c14")
        assert stamp_state(root, load_stamps(root), "verify-tests", "qa")[0] == "失効", \
            "ui_roots の中の変更が qa を失効させない"
        # --- inspection-21 V-9: 試験区分ごとのコードの置き場(scope_roots)。未宣言は広いほうへ倒す
        local.write_text(json.dumps({"code_roots": ["src/"], "ui_roots": ["src/ui/"],
                                     "scope_roots": {"unit": ["src/app/"]}}), encoding="utf-8")
        assert main(["x", "record", "verify-tests", "green", "--scope", "unit",
                     "--scope", "integration"]) == 0
        (root / "src/other.py").write_text("o1", encoding="utf-8")
        commit("c14a")
        assert stamp_state(root, load_stamps(root), "verify-tests", "unit")[0] == "green", \
            "scope_roots の外の変更が unit を失効させた(試験区分ごとの宣言が効いていない)"
        assert stamp_state(root, load_stamps(root), "verify-tests", "integration")[0] == "失効", \
            "宣言していない試験区分が code_roots 全体へ倒れていない(安全側の既定が壊れた)"
        (root / "src/app").mkdir()
        (root / "src/app/x.py").write_text("a1", encoding="utf-8")
        commit("c14b")
        assert stamp_state(root, load_stamps(root), "verify-tests", "unit")[0] == "失効", \
            "scope_roots の中の変更が unit を失効させない"
        local.write_text(json.dumps({"code_roots": ["src/"], "ui_roots": ["src/ui/"]}),
                         encoding="utf-8")
        assert stamp_state(root, load_stamps(root), "verify-tests", "unit")[0] == "失効", \
            "scope_roots の宣言を戻したのに失効しない(焼き込み — D8 と同型)"
        # --- 2026-08-22 の人間の指示(1): 広く倒れていることを check が言う(判定は変えない)
        local.write_text(json.dumps({"code_roots": ["src/"], "ui_roots": ["src/ui/"],
                                     "scope_roots": {"unit": ["src/app/"]}}), encoding="utf-8")
        assert widened(root, "verify-tests", "integration") == "scope_roots が未宣言", \
            "scope_roots 未宣言の試験区分が、広く倒れていると言われない"
        assert widened(root, "verify-tests", "unit") is None, \
            "宣言済みの試験区分まで『広く倒れている』と言っている"
        local.write_text(json.dumps({"code_roots": ["src/"]}), encoding="utf-8")
        assert widened(root, "verify-tests", "qa") == "scope_roots も ui_roots も未宣言", \
            "qa が ui_roots 未宣言のときに言われない"
        local.write_text(json.dumps({"code_roots": ["src/"], "ui_roots": ["src/ui/"]}),
                         encoding="utf-8")
        assert widened(root, "verify-tests", "qa") is None, \
            "ui_roots へ倒すのは設計どおりの絞り込みなのに、広いと言っている"
        assert widened(root, "verify-docs", None) is None, \
            "コードに依存しないフローについて言っている"
        assert widened(root, "verify-impl", None) is None, \
            "試験区分を持たないフロー(F3)に、宣言先の無い直し方を出している(消せない注記)"

        # --- 2026-08-22 の人間の指示(2): code_excludes — 検証の入力ではないと宣言したパス
        assert main(["x", "record", "verify-tests", "green", "--scope", "integration"]) == 0
        (root / "src/notes.md").write_text("n1", encoding="utf-8")
        commit("c14c")
        assert stamp_state(root, load_stamps(root), "verify-tests", "integration")[0] == "失効", \
            "宣言前なのに code_roots の中の変更が失効させない"
        local.write_text(json.dumps({"code_roots": ["src/"], "ui_roots": ["src/ui/"],
                                     "code_excludes": ["src/notes.md"]}), encoding="utf-8")
        assert main(["x", "record", "verify-tests", "green", "--scope", "integration"]) == 0
        (root / "src/notes.md").write_text("n2", encoding="utf-8")
        commit("c14d")
        assert stamp_state(root, load_stamps(root), "verify-tests", "integration")[0] == "green", \
            "code_excludes に書いたパスの変更が失効させている"
        (root / "src/real.py").write_text("r1", encoding="utf-8")
        commit("c14e")
        assert stamp_state(root, load_stamps(root), "verify-tests", "integration")[0] == "失効", \
            "code_excludes の外の変更まで失効させなくなった(穴)"
        # 宣言を変えたら焼き込みで失効する(code_roots と同型)
        assert main(["x", "record", "verify-tests", "green", "--scope", "integration"]) == 0
        local.write_text(json.dumps({"code_roots": ["src/"], "ui_roots": ["src/ui/"]}),
                         encoding="utf-8")
        assert stamp_state(root, load_stamps(root), "verify-tests", "integration")[0] == "失効", \
            "code_excludes の宣言を戻したのに失効しない(焼き込み漏れ = fail-open)"
        # コードの置き場の外は落とす(文書側の依存を黙って外せる口にしない)
        local.write_text(json.dumps({"code_roots": ["src/"],
                                     "code_excludes": ["docs/02-design/"]}), encoding="utf-8")
        assert code_excludes(root) == [], \
            "code_roots の外の code_excludes が生きている(見ないことにする口になっている)"
        # **置き場の親も落とす** — 通すと置き場ごと無効にできる(独立検査 B-2)
        local.write_text(json.dumps({"code_roots": ["src/app/"],
                                     "code_excludes": ["src/"]}), encoding="utf-8")
        assert code_excludes(root) == [], \
            "code_roots の親を code_excludes に書けている(置き場ごと無効にできる)"
        # **置き場と等しいものも落とす** — 親を弾いても等号が残れば結果は同じである
        for same in ("src/", "src"):
            local.write_text(json.dumps({"code_roots": ["src/"],
                                         "code_excludes": [same]}), encoding="utf-8")
            assert code_excludes(root) == [], \
                f"code_excludes に置き場そのもの({same})を書けている(失効判定が丸ごと死ぬ)"
        # 置き場より真に狭いものは通る(これが本来の用途である)
        local.write_text(json.dumps({"code_roots": ["src/"],
                                     "code_excludes": ["src/notes.md"]}), encoding="utf-8")
        assert code_excludes(root) == ["src/notes.md"], \
            "置き場より狭い code_excludes まで落としている"
        # **入れ子の置き場では、内側の置き場そのものも落とす**(外側より狭いので素通りしていた)
        (root / "src/app").mkdir(exist_ok=True)
        local.write_text(json.dumps({"code_roots": ["src/", "src/app/"],
                                     "code_excludes": ["src/app/", "src/app"]}), encoding="utf-8")
        assert code_excludes(root) == [], \
            "入れ子の置き場で、内側の置き場そのものを code_excludes に書けている"
        local.write_text(json.dumps({"code_roots": ["src/", "src/app/"],
                                     "code_excludes": ["src/app/notes/"]}), encoding="utf-8")
        assert code_excludes(root) == ["src/app/notes/"], \
            "入れ子の置き場で、正当な(より狭い)宣言まで落としている"
        # **試験区分ごとの宣言(scope_roots / ui_roots)と等しいものも落とす** — 通すとその試験区分が死ぬ
        local.write_text(json.dumps({"code_roots": ["src/"],
                                     "scope_roots": {"unit": ["src/app/"]},
                                     "code_excludes": ["src/app/"]}), encoding="utf-8")
        assert code_excludes(root) == [], \
            "scope_roots と等しい code_excludes が通っている(その試験区分が二度と失効しない)"
        local.write_text(json.dumps({"code_roots": ["src/"], "ui_roots": ["src/ui/"],
                                     "code_excludes": ["src/ui/"]}), encoding="utf-8")
        assert code_excludes(root) == [], \
            "ui_roots と等しい code_excludes が通っている(qa が二度と失効しない)"
        local.write_text(json.dumps({"code_roots": ["src/"],
                                     "scope_roots": {"unit": ["src/app/"]},
                                     "code_excludes": ["src/app/notes.md"]}), encoding="utf-8")
        assert code_excludes(root) == ["src/app/notes.md"], \
            "試験区分の置き場より狭い正当な宣言まで落としている"
        # **置き場がファイルなら、その「下」は存在しえないので受け付けない**
        (root / "Makefile").write_text("all:\n", encoding="utf-8")
        local.write_text(json.dumps({"code_roots": ["Makefile"],
                                     "code_excludes": ["Makefile/generated"]}), encoding="utf-8")
        assert code_excludes(root) == [], \
            "ファイルの置き場の『下』という在りえない宣言を受け付けている"
        # **欄を持たない古い鮮度スタンプでも、宣言を足したら失効する**(独立検査 B-1)
        local.write_text(json.dumps({"code_roots": ["src/"], "ui_roots": ["src/ui/"]}),
                         encoding="utf-8")
        assert main(["x", "record", "verify-tests", "green", "--scope", "integration"]) == 0
        st = load_stamps(root)
        st["latest"]["verify-tests:integration"].pop("code_excludes", None)   # 旧版の記録を模す
        (root / STATE).write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
        assert stamp_state(root, load_stamps(root), "verify-tests", "integration")[0] == "green", \
            "欄の無い記録が、宣言も空なのに失効している"
        local.write_text(json.dumps({"code_roots": ["src/"], "ui_roots": ["src/ui/"],
                                     "code_excludes": ["src/notes.md"]}), encoding="utf-8")
        assert stamp_state(root, load_stamps(root), "verify-tests", "integration")[0] == "失効", \
            "欄の無い古い記録が、code_excludes を足した後も green のまま(fail-open)"
        local.write_text(json.dumps({"code_roots": ["src/"], "ui_roots": ["src/ui/"]}),
                         encoding="utf-8")
        assert main(["x", "record", "verify-tests", "green", "--scope", "integration"]) == 0
        local.write_text(json.dumps({"code_roots": ["src/"], "ui_roots": ["src/ui/"]}),
                         encoding="utf-8")
        assert main(["x", "record", "verify-tests", "green", "--scope", "integration"]) == 0
        # --- inspection-17 判断9: critical の検証待ちが在る間、F2/F3 の green は --lens 必須
        (root / "docs/build-records/crit.md").write_text(
            f"---\nslug: crit\nstate: awaiting-verify\ncritical: true\ncommit: {head(root)}\n"
            "---\n\n## 影響範囲(closure)\n\n- docs/02-design/system.md\n- src/a.py\n",
            encoding="utf-8")
        commit("c15")
        assert main(["x", "record", "verify-docs", "green"]) == 2, \
            "critical 検証待ちが在るのに --lens 無しの green が通った(判断9)"
        # --- inspection-19 V-2: 覆いを持つ run は、その覆いに掛かる critical だけを見る
        assert main(["x", "record", "verify-docs", "green",
                     "--covers", "docs/issues/index.md"]) == 0, \
            "クロージャの外だけを覆う run に --lens を要求した(V-2)"
        assert main(["x", "record", "verify-docs", "green",
                     "--covers", "docs/02-design/system.md"]) == 2, \
            "クロージャに掛かる覆いなのに --lens を要求しなかった(V-2)"
        assert main(["x", "record", "verify-docs", "red"]) == 0, \
            "red にまで --lens を要求した(red は green の主張ではない)"
        assert main(["x", "record", "verify-docs", "green", "--lens", "@review(codex)"]) == 0, \
            "--lens 付きの green が通らない"
        assert main(["x", "record", "verify-tests", "green", "--scope", "unit"]) == 0, \
            "F4 の green に --lens を要求した(独立レビューは F2/F3 の機構)"
        (root / "docs/build-records/crit.md").unlink()
        commit("c16")
        assert main(["x", "record", "verify-impl", "green"]) == 0, \
            "critical が消えた後も --lens を要求した"
        # --- inspection-20 V-2: F2 は 03-impl のツール生成領域では失効しない(除外)
        assert main(["x", "record", "verify-docs", "green"]) == 0
        (root / "docs/03-impl/callgraphs").mkdir(parents=True)
        (root / "docs/03-impl/callgraphs/mod.md").write_text("生成", encoding="utf-8")
        (root / "docs/03-impl/feature-graph.md").write_text("生成", encoding="utf-8")
        commit("c17")
        assert stamp_state(root, load_stamps(root), "verify-docs")[0] == "green", \
            "ツール生成領域の再生成が F2 を失効させた(V-2 で依存から除いたはず)"
        assert stamp_state(root, load_stamps(root), "verify-impl")[0] == "失効", \
            "ツール生成領域の変更が F3 を失効させない(F3 の依存には残っているはず)"
        (root / "docs/03-impl/index.md").write_text("索引", encoding="utf-8")
        commit("c18")
        assert stamp_state(root, load_stamps(root), "verify-docs")[0] == "失効", \
            "03-impl の除外の外(index.md)の変更が F2 を失効させない"
        assert main(["x", "record", "verify-docs", "green",
                     "--covers", "docs/03-impl/callgraphs/"]) == 2, \
            "除外された領域を --covers で覆えてしまった"
        # 除外領域の**親**を覆いに指定した run。除外ガードは素通りする(親は除外の外)が、
        # そのぶん未コミット判定にも除外が効かない — **安全側の非対称であり、意図している**。
        # 「記録できない」で止まるだけで、見ていないものが green になる経路は作らない。
        (root / "docs/03-impl/callgraphs/mod.md").write_text("未コミットの再生成", encoding="utf-8")
        assert main(["x", "record", "verify-docs", "green",
                     "--covers", "docs/03-impl/"]) == 2, \
            "除外領域の親を覆いにすると、除外領域の未コミットが green を止めない(安全側が壊れた)"
        commit("c18a")
        assert main(["x", "record", "verify-docs", "green",
                     "--covers", "docs/03-impl/"]) == 0, \
            "コミットしたのに、除外領域の親を覆う部分記録が通らない"
        # --- inspection-20 V-4: e2e_scripts_in: testing で system.md が e2e/qa の依存から外れる
        assert main(["x", "record", "verify-docs", "green"]) == 0
        local.write_text(json.dumps({"code_roots": ["src/"], "ui_roots": ["src/ui/"],
                                     "e2e_scripts_in": "testing"}), encoding="utf-8")
        # 切り出し先が無いあいだは宣言を無視する(誤宣言の fail-closed)
        assert e2e_scripts_in(root) == "system", \
            "testing.md が無いのに e2e_scripts_in: testing を受理した(誤宣言の fail-open)"
        (root / "docs/02-design/testing.md").write_text("台本を切り出した", encoding="utf-8")
        commit("c18b")
        assert e2e_scripts_in(root) == "testing", "切り出し後も宣言が効かない"
        assert main(["x", "record", "verify-tests", "green", "--scope", "e2e",
                     "--scope", "qa"]) == 0
        (root / "docs/02-design/system.md").write_text("分割の散文を直した", encoding="utf-8")
        commit("c19")
        assert stamp_state(root, load_stamps(root), "verify-tests", "e2e")[0] == "green", \
            "台本を切り出した宣言があるのに system.md の変更が e2e を失効させた(V-4)"
        assert stamp_state(root, load_stamps(root), "verify-tests", "qa")[0] == "green", \
            "同上(qa)"
        (root / "docs/02-design/testing.md").write_text("台本を直した", encoding="utf-8")
        commit("c20")
        assert stamp_state(root, load_stamps(root), "verify-tests", "e2e")[0] == "失効", \
            "testing.md の変更が e2e を失効させない(切り出し後はここが台本である)"
        assert stamp_state(root, load_stamps(root), "verify-tests", "qa")[0] == "失効", \
            "testing.md の変更が qa を失効させない(切り出し後はここが台本である)"
        assert main(["x", "record", "verify-tests", "green", "--scope", "e2e",
                     "--scope", "qa"]) == 0
        local.write_text(json.dumps({"code_roots": ["src/"], "ui_roots": ["src/ui/"]}),
                         encoding="utf-8")
        assert stamp_state(root, load_stamps(root), "verify-tests", "e2e")[0] == "失効", \
            "e2e_scripts_in の宣言を戻したのに失効しない(焼き込み — D8 と同型)"
        # 欄を持たない古い鮮度スタンプも既定値 "system" と比べる(fail-open を作らない)
        assert main(["x", "record", "verify-tests", "green", "--scope", "e2e"]) == 0
        st = load_stamps(root)
        st["latest"]["verify-tests:e2e"].pop("e2e_scripts_in", None)
        save_stamps(root, st)
        assert stamp_state(root, load_stamps(root), "verify-tests", "e2e")[0] == "green", \
            "欄の無い古い鮮度スタンプが、宣言も既定のままなのに失効した"
        local.write_text(json.dumps({"code_roots": ["src/"], "ui_roots": ["src/ui/"],
                                     "e2e_scripts_in": "testing"}), encoding="utf-8")
        assert stamp_state(root, load_stamps(root), "verify-tests", "e2e")[0] == "失効", \
            "欄の無い古い鮮度スタンプが、宣言を testing に変えても失効しない(fail-open)"

        # --- リリース台帳(2026-09-04)— 版は機械が決める。人間は桁を指定しない
        def _commit_state(msg: str) -> None:
            run("git", "add", "-A")
            subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                            "commit", "-q", "--allow-empty", "-m", msg],
                           cwd=root, capture_output=True)

        def _all_green() -> None:
            assert main(["x", "record", "verify-docs", "green"]) == 0
            assert main(["x", "record", "verify-impl", "green"]) == 0
            assert main(["x", "record", "verify-tests", "green", "--scope", "unit",
                         "--scope", "integration", "--scope", "e2e", "--scope", "qa"]) == 0
            _commit_state("stamps")    # 鮮度スタンプの書込みは専用の1コミットで畳む(flows.md §2)

        def _rec(name: str, decl: str) -> None:
            (root / f"docs/build-records/{name}.md").write_text(
                f"---\nslug: {name}\nstate: verified\ncommit: {head(root)}\n"
                "updated: 2026-08-20T00:00:00+00:00\n---\n\n"
                f"## 主張\n\n- 外部挙動の変化: {decl}\n", encoding="utf-8")
            commit(f"rec-{name}")
            _all_green()

        for stale in (root / "docs/build-records").glob("*.md"):
            stale.unlink()
        commit("release-base")
        _all_green()
        assert main(["x", "check"]) == 0, "リリースの検査の前提(green)が作れない"
        assert main(["x", "release", "--current"]) == 1, "台帳が空なのに版を名乗った"
        assert main(["x", "release"]) == 0, "最初のリリースが記録できない"
        assert load_releases(root)[0]["version"] == FIRST_VERSION, \
            f"最初のリリースが {FIRST_VERSION} で始まらない"
        assert main(["x", "release", "--current"]) == 0, "記録した直後に版を名乗れない"
        # 台帳を書く前に打ち直しても重ならない(未コミットで拒む)
        assert main(["x", "release"]) == 1, "台帳が未コミットのままリリースを重ねた"
        _commit_state("release")
        # **台帳の commit だけでは版は動かない** ★ — §9.1 の手順が HEAD を進めるので、
        # ここで動くと打ち直すたびに版が増える(独立検査 2026-09-04)
        assert main(["x", "release"]) == 0, "台帳の外が動いていないのに拒んだ"
        assert len(load_releases(root)) == 1, "台帳の commit だけで版が動いた"
        # 構築記録が1件も無くても、台帳の外が動いていれば revision は動く(人間の裁定)
        (root / "src/n.py").write_text("n", encoding="utf-8"); commit("no-record")
        _all_green()
        assert main(["x", "release"]) == 0, "構築記録が無い区間でリリースできない"
        assert load_releases(root)[0]["version"] == "0.9.1", \
            "構築記録が無くても、出したなら revision は動く"
        _commit_state("release")
        _rec("v1", "なし")
        assert main(["x", "release"]) == 0
        _commit_state("release")
        assert load_releases(root)[0]["version"] == "0.9.2", \
            f"振る舞いが変わっていないのに revision が動かない: {load_releases(root)[0]}"
        _rec("v2", "あり(後方互換。画面を1つ足した)")
        assert main(["x", "release"]) == 0
        _commit_state("release")
        assert load_releases(root)[0]["version"] == "0.10.0", "後方互換の追加で minor が動かない"
        _rec("v3", "なし")
        _rec("v4", "あり(互換を壊す。引数を1つ必須にした)")
        assert main(["x", "release"]) == 0
        _commit_state("release")
        assert load_releases(root)[0]["version"] == "1.0.0", \
            "互換を壊す宣言が1件でも在れば major である(最大値を採る)"
        # 雛形のままの宣言は拒む(fail-closed)。**黙って revision にしない** ★
        _rec("v5", "<あり(何が変わるか1行)/ なし>")
        assert main(["x", "release"]) == 2, "雛形のままの宣言を拒まなかった"
        assert load_releases(root)[0]["version"] == "1.0.0", "拒んだのに台帳が動いた"
        (root / "docs/build-records/v5.md").unlink(); commit("drop-v5"); _all_green()
        # 未コミットの変更が在るあいだは記録しない(record の green と同じ理由)
        (root / "src/z.py").write_text("z", encoding="utf-8")
        assert main(["x", "release"]) == 1, "未コミットの変更が在るのにリリースを記録した"
        (root / "src/z.py").unlink()
        # `commit:` を持たない記録は**黙って飛ばさない**(区間に置けないものを数から消さない)
        (root / "docs/build-records/nc.md").write_text(
            "---\nslug: nc\nstate: verified\n---\n\n## 主張\n\n"
            "- 外部挙動の変化: あり(互換を壊す。x)\n", encoding="utf-8")
        commit("nc"); _all_green()
        assert main(["x", "release"]) == 2, "`commit:` の無い記録を黙って飛ばした"
        # git が解決できない `commit:` も同じく黙って落とさない(cherry-pick・revert の型)
        (root / "docs/build-records/nc.md").write_text(
            "---\nslug: nc\nstate: verified\ncommit: " + "0" * 40 + "\n---\n\n"
            "## 主張\n\n- 外部挙動の変化: あり(互換を壊す。x)\n", encoding="utf-8")
        commit("nc2"); _all_green()
        assert main(["x", "release"]) == 2, "解決できない `commit:` を黙って飛ばした"
        (root / "docs/build-records/nc.md").unlink(); commit("drop-nc"); _all_green()
        # 壊れた台帳は「未リリース」と読まない(履歴を捨てない)
        ledger = root / ".claude/state/releases.json"
        keep = ledger.read_text(encoding="utf-8")
        ledger.write_text("{壊れ", encoding="utf-8")
        assert main(["x", "release"]) == 2, "壊れた台帳を未リリースと読んで上書きした"
        assert main(["x", "release", "--current"]) == 2, "壊れた台帳から版を名乗った"
        ledger.write_text(json.dumps({"releases": [{"version": "1.2", "commit": "x"}]}),
                          encoding="utf-8")
        assert main(["x", "release"]) == 2, "3つ組でない版を受け入れた"
        assert main(["x", "release", "--current"]) == 2, "3つ組でない版を印字した"
        ledger.write_text(keep, encoding="utf-8")
        _commit_state("restore-ledger")
        os.chdir(previous)
    print("OK stamps: 複合のデプロイゲート/red混在/依存集合(許可リスト)/部分再検証の併合(覆い切ったら基準点を進めて畳む)/未宣言=red/"
          "未コミットでは green を書かせない/全数の印(判定に効かず F2/F3 のみ)/"
          "building/シート/issue/promote(記録の時点で判定・祖先なら区間ゼロ)/"
          "同一HEADの未コミット失効/f4_scopes(qa 外しのみ受理)/管理欄だけの変更は失効させない/"
          "機械の欄の中身だけの変更は失効させない(区画単位。旧終端も剥ぐ。外側が動けば失効する)/"
          "e2e の 02 依存の絞り込み/code_roots 焼き込み/旧ファイル互換/"
          "red は基準点を消さない(last_green)/試験表は unit・integration の依存外/"
          "qa の ui_roots と 02 絞り込み/試験区分ごとの scope_roots(未宣言は広いほうへ)/"
          "広く倒れていることの表示(判定は変えない)/code_excludes(焼き込み・置き場の外は落とす)/"
          "critical 時の --lens 必須(範囲は覆いに合わせる)/"
          "F2 はツール生成領域では失効しない(除外。覆いとの相互作用は安全側)/"
          "e2e_scripts_in による台本の置き場の宣言/"
          "リリース台帳(最初は 0.9.0・桁は宣言の最大値・雛形のままは拒む・未コミットは拒む)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
