#!/usr/bin/env python3
"""人間を呼ぶ音。鳴らせるのは3つだけである。

    python3 .claude/scripts/notify-slack.py question <ウィンドウ名>  # <時刻> [<プロジェクト>] 質問があるので確認してください(ウィンドウ: <ウィンドウ名>)
    python3 .claude/scripts/notify-slack.py done        # <時刻> [<プロジェクト>] ミッションが完了しました
    python3 .claude/scripts/notify-slack.py --notice <文>   # colabtmux が呼ぶ(停止の検知)

**前の2つは自由な文面を受け取らない。** 「どの出来事で鳴らすか」を人間が覚えなくて済むことに
この仕組みの価値があり、AI が任意の文面を送れる口を1つ開ければ、その日のうちに元の洪水へ戻る。
**鳴らす主体は、自分がその出来事の当事者であるときに限られる** — `question` を叩けるのは
**人間に問いを出した作業エージェント本人**(2026-08-18 から。中央エージェントを経由しない。
orchestration.md §6)、**粒度判定役 `@triage`**(要望どうしの矛盾を人間に問うとき)、そして
**予算の計器の発火で配車を止めた中央エージェント**(2026-08-27。その1場面だけ)の3者である。
`done` は中央エージェントである。**取り次ぎで鳴らすことは、誰にも許されていない。**

[DS-05] `question` の引数は**ウィンドウ名1つだけ**を受け、`^[A-Za-z0-9._-]{1,32}$` に合わないものは
使い方の誤り(`2`)として送らない — 理由: 人間は「どのウィンドウへ行けばよいか」が分からなければ
全部のウィンドウを見に行くことになり、それは鳴っていないのと同じである。一方でここを自由文にすると
上の禁止が崩れるので、**入るのは宛先だけ**にする / 見直す条件: ウィンドウ名以外に人間の初動を変える
情報が現れたとき。**引数を省いた `question` は使い方の誤り(`2`)として送らない** —
ウィンドウ名の無い音は「どのウィンドウへ行けばよいか」を運ばず、鳴っていないのと同じである
(orchestration.md §6.1。「中央エージェントの代理鳴らし」— 中央が他のエージェントの代わりに
音を送ること — という例外は、いまも規範に存在しない。inspection-17 M-11)。
**中央エージェント自身が `question` を鳴らす場合が1つだけ在る** ★(2026-08-27。対策4):
**ミッションの予算の計器(`check-mission.py`)が発火して配車を止め、人間の裁定を待つとき**、
自分のウィンドウ名を添えて1回だけ打つ(orchestration.md §3.0 の6・§6.1)。
**代理ではない — 問うているのは中央エージェント自身である。** 監視は中央エージェントの
ウィンドウを見ないので(`exclude_windows`)、この音が無いと配車の停止は無音になる。
**この口の側は1バイトも変わっていない**: 受ける引数は今までどおり `question` と
ウィンドウ名1つだけであり、増えたのは規範の側の「鳴らしてよい役」だけである。

**3つ目 `--notice` は AI の口ではない。** colabtmux の監視が停止を検知したときに、
`colabtmux.conf` の `[notify] command` に書かれたこの行を**道具が**実行し、末尾に知らせの文を
足して渡す(文を組み立てるのは colabtmux であって AI ではないので、上の禁止は破れていない)。
AI がこの入口を叩くことは禁じる。
正: .claude/directions/orchestration.md §6.1

**文面は `<時刻> [<プロジェクト名>] <文>` である。** 1つの Slack チャンネルに複数のプロジェクトの
音が集まるので、送信元が文面に無ければ、受け手は呼ばれるたびに端末を全部見に行くことになる
(音の数と「何が起きているか」の1対1対応が壊れる。orchestration.md §6.1)。

[DS-04] プロジェクト名は `colabtmux.conf` の `[project] name`(= tmux のセッション名)を読み、
読めなければキットの置かれたディレクトリ名を使う — 理由: colabtmux 自身が `--project` 省略時に
決める順序と同じであり、**この音のために新しい設定も環境変数も1つも増やさない**(増やせば
「設定したつもりで入っていない」経路が1本増える) / 見直す条件: colabtmux が知らせ役へ
プロジェクト名を渡すようになったとき。

送信は fail-open である。Slack が落ちていても未設定でも、ミッションは止めない
(結果は1行で標準出力に出るので、中央エージェントはそれを台帳に書く)。

**ただし fail-open は「終了コード0を返す」ことではない。** 0 は「送った」の意なので、
**送っていないときは 0 を返さない** — 未設定・送信失敗・Slack が `ok:false` を返した、の
3つはどれも人間に1文字も届いていないので `3` を返す。2026-08-16 に実際に起きたのがこれで、
監視は停止を正しく検知して知らせ役を呼んだのに、環境に `SLACK_*` が無く誰も呼ばれず、
ログだけが「送った」と言った。**記録が嘘をつく通知は、通知が無いより悪い。**

**止まらないことは呼び出し側が担う。** colabtmux の監視は非ゼロを
`notice.failed`(`reason=exit_nonzero`)に記録してそのまま続け(`internal/monitor/notify.go`
の `Notify` は知らせ役の失敗を戻り値の error にしない)、中央エージェントは非ゼロを見ても
止まらず、送り直しもしない(orchestration.md §6.1)。fail-open は保たれたまま
**記録だけが真になる**。

[DS-02] 「送っていない」3経路を1つの終了コード `3` にまとめ、細分しない —
理由: 終了コードの読み手は2つしかなく、どちらも細分を消費できない(監視は非ゼロを
`exit_nonzero` の1値へ潰し、知らせ役の標準出力を捨てる。中央エージェントは標準出力の1行
`未送信:` / `送信失敗:` で原因を読む)。`2`(使い方の誤り)と混ぜないのは、直す相手が
呼び出し側のコードか運用者の環境かで違うからである。`3` はキット共通の約束(0/1/2)の外に
置いた専用値である(tools-readme.md §2)/ 見直す条件: 標準出力を読まずに終了コードだけで
分岐する呼び出しが増えたとき。
正: CLAUDE.md §9(通知の規則)
"""

import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

API = "https://slack.com/api/chat.postMessage"
TIMEOUT_SEC = 5

# キットの置き場所から見たプロジェクトのルート(このファイルは <root>/.claude/scripts/ に在る)。
# **cwd から探さない** — 知らせ役は colabtmux の監視(子プロセス)からも呼ばれるので、
# 呼び出し側の cwd に依存させない。
ROOT = pathlib.Path(__file__).resolve().parents[2]

MESSAGES = {
    "question": "質問があるので確認してください",
    "done": "ミッションが完了しました",
}

# ウィンドウ名に許す形(docstring [DS-05])。tmux のウィンドウ名 = colabtmux のエージェントID である。
WINDOW_RE = re.compile(r"[A-Za-z0-9._-]{1,32}")


def project_name() -> str:
    """送信元の名前(docstring の [DS-04])。設定が読めなければディレクトリ名。

    TOML の完全な解析はしない — 読むのは `[project]` の `name` 1つだけであり、そのために
    依存(tomllib は 3.11 以降)を足すと、古い python の環境で知らせ役ごと落ちる。
    """
    # 設定の置き場は2つありうる。`colabtmux` は自分の状態の置き場(`.colabtmux/`)の中に
    # 設定を作る版があり、そのときリポジトリ直下には1つも無い(実測 2026-09-01)。
    # **片方だけを見ると、設定が在るのに読めず、黙ってディレクトリ名へ落ちる。**
    # **読めた最初の1つで打ち切らない** ★ — 2つとも在って `[project] name` が直下にだけ
    # 書かれていると、打ち切る形は**名前を取れないまま終わる**(独立検査 2026-09-04 の実測)。
    # **打ち切るのは名前が取れたときである。**
    for cand in (ROOT / ".colabtmux/colabtmux.conf", ROOT / "colabtmux.conf"):
        try:
            text = cand.read_text(encoding="utf-8")
        except OSError:
            continue
        section = ""
        for raw in text.splitlines():
            line = raw.split("#", 1)[0].strip()  # 名前に `#` は入らない前提の割り切り
            if line.startswith("["):
                section = line
                continue
            key, sep, value = line.partition("=")
            if section == "[project]" and sep and key.strip() == "name":
                name = value.strip().strip("\"'")
                if name:
                    return name
    return ROOT.name


def main() -> int:
    if any(a in ("-h", "--help") for a in sys.argv[1:]):
        print(__doc__)   # 明示要求は 0。使い方エラーの 2 と区別する(tools-readme §2)
        return 0
    # colabtmux の監視が呼ぶ入口。文は道具が組み立てて末尾に足す(docstring 冒頭)。
    if len(sys.argv) == 3 and sys.argv[1] == "--notice":
        notice = sys.argv[2].strip()
        if not notice:
            print("usage: notify-slack.py --notice <文>", file=sys.stderr)
            return 2
        body = notice
    elif len(sys.argv) == 2 and sys.argv[1] == "done":
        body = MESSAGES["done"]
    elif len(sys.argv) == 2 and sys.argv[1] == "question":
        # ウィンドウ名の無い question は送らない(docstring [DS-05]。規範: orchestration.md §6.1)。
        print(
            "usage: notify-slack.py question <ウィンドウ名>(ウィンドウ名は必須 — 無い音は鳴っていないのと同じ)",
            file=sys.stderr,
        )
        return 2
    elif len(sys.argv) == 3 and sys.argv[1] == "question":
        # 宛先(どのウィンドウへ行けばよいか)だけを受ける。自由文の口は開けない(docstring [DS-05])。
        window = sys.argv[2].strip()
        if not WINDOW_RE.fullmatch(window):
            print(
                "usage: notify-slack.py question <ウィンドウ名>"
                "(ウィンドウ名は英数字と . _ - のみ、32バイト以内)",
                file=sys.stderr,
            )
            return 2
        body = f"{MESSAGES['question']}(ウィンドウ: {window})"
    else:
        print(
            "usage: notify-slack.py done | question <ウィンドウ名> | --notice <文>",
            file=sys.stderr,
        )
        return 2

    text = f"{time.strftime('%H:%M')} [{project_name()}] {body}"

    token = os.environ.get("SLACK_BOT_TOKEN", "")
    channel = os.environ.get("SLACK_CHANNEL", "")
    if not token or not channel:
        missing = " と ".join(
            n for n, v in (("SLACK_BOT_TOKEN", token), ("SLACK_CHANNEL", channel)) if not v
        )
        # 何も送っていない。0 は「送った」の意なので返さない(docstring の [DS-02])。
        print(f"未送信({missing} が無い): {text}")
        return 3

    req = urllib.request.Request(
        API,
        data=json.dumps({"channel": channel, "text": text}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as res:
            body = json.loads(res.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        # 届いていない。**監視はこの1行を捨てる**ので、非ゼロだけが記録に残る手段である。
        print(f"送信失敗({exc.__class__.__name__}): {text}")
        return 3

    if body.get("ok"):
        print(f"送信: {text}")
        return 0
    # Slack が受け取らなかった(チャンネル違い・権限・トークン失効)。届いていないので 0 は返さない。
    print(f"送信失敗({body.get('error', 'unknown')}): {text}")
    return 3


if __name__ == "__main__":
    sys.exit(main())
