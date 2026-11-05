#!/usr/bin/env python3
"""保護ブランチで作業させない — 判定と、作業ブランチへの移動を1本にまとめたもの。

**規範の正は `.claude/directions/flows.md` §7.1 である。** ここはその実装であって、
規則を持たない。**食い違ったら向こうが正しい。**

なぜスクリプトにするか(2026-08-23 の裁定):
**この判定は11のファイルに散文で書かれていた。** 書き足すたびに同じ文が増え、
**判定の中身を1つ直すたびに全部を1つずつ直すことになる** — 実測で2度起きた:

- 既定ブランチの名前を比べる前に `origin/` を取り除く1手の抜け(その全部を直した)
- 同じ名前の枝が既に在るときの2分岐(C-12。7か所を直した)

**規範の側は「どのスキルが判定するか」を名前で列挙していた。** 列挙は現実に追いつかず、
既存プロジェクトへの導入経路(`/relations --apply` と `/retrofit`)が判定を1つも
持たないまま、書き込んではいけない枝の上で文書を大量に生成していた(A-22)。
**列挙をやめて「判断を含む文字を書くスキルはすべて」にし、判定の中身はこの1本が持つ。**

使い方:

    python3 .claude/scripts/guard-branch.py --slug <slug>   # work/<今日>-<slug>
    python3 .claude/scripts/guard-branch.py --verify        # work/<今日>-verify
    python3 .claude/scripts/guard-branch.py --name <名前>   # 名前をそのまま使う(艦隊の work/<mid>)
    python3 .claude/scripts/guard-branch.py --selftest

終了コード:

    0  作業ブランチに居る(元から居た / 作って移った / 移って基点を追いつかせた)
    1  **止まって報告する** — こちらの知らない事情が在る
    2  **使い方の誤り** — 呼び手を直せば済む(枝名が不正、移る先が保護ブランチ、など)

**`1` を握りつぶさない。** ここで止まるのは、別の作業ツリーがその枝を使っている、
前の周の書きかけが衝突した、中断したマージが残っている、といったときである。
**`git branch -D` を打って先へ進んではならない** — それは書きかけを消す。
"""
import argparse
import datetime
import os
import re
import subprocess
import sys
import tempfile

# 名前で保護される3つ。4つ目は「そのリポジトリの既定ブランチ」で、名前は何であってもよい。
NAMED_PROTECTED = ("main", "master", "develop")
REMOTE_PREFIX = re.compile(r'^[^/]+/')
# **作業ブランチの名前は `work/…` である**(`flows.md` §7.1)。移る先をこの形に縛るのは、
# **`--name` に保護ブランチの名前を渡せてしまう**からである — 縛らないと、保護ブランチで
# 作業させないための道具が、頼まれれば保護ブランチを消して作り直し、その上で「OK」と言う。
WORK_PREFIX = "work/"
# **枝名の可否を自前の正規表現で決めない** ★ — 実測で両方向に外れた:
# `ユーザ認証` を撥ね(**このキットは日本語のファイル名を積極的に支えている** —
# `check-ssot.py` が「ASCII 限定にすると日本語ファイル名の文書を数え落とす」と書いている。
# 構築記録は `docs/build-records/<slug>.md` なので、日本語の slug は認められた形である)、
# `x.lock` や `x..y` を通した(git が撥ねるので、**直せる誤字が「人間を呼んで止まる」に化けた**)。
# **git 自身に聞く** — `git check-ref-format --branch` と二度とずれない。
# git の助言をそのまま報告に載せない。**読んだ相手に `-D` の文字列を渡すことになる。**
ADVICE = re.compile(r'^\s*If you are sure.*$', re.M)


# git の出力を英語に固定する。**文面を読むためではなく**、`-D` を勧める助言行を確実に
# 落とすためである(利用者のロケール次第で文言が変わると、落とし損ねる)。
ENV = dict(os.environ, LC_ALL="C", LANG="C")


def git(*args, cwd=None, env=None):
    """git を1回走らせて (終了コード, 出力) を返す。**例外にしない** — 判定に使う。"""
    r = subprocess.run(("git",) + args, cwd=cwd, capture_output=True, text=True,
                       env=env or ENV)
    return r.returncode, ADVICE.sub("", r.stdout + r.stderr).strip()


def valid_branch_name(name, cwd=None):
    """git がその名前を枝名として受け取るか。**判断は git に任せる。**"""
    return git("check-ref-format", "--branch", name, cwd=cwd)[0] == 0


def current_branch(cwd=None):
    """いま立っている枝の名前。detached なら空文字。読めなければ None。

    **`git rev-parse --abbrev-ref HEAD` を使わない** ★ — あれは**コミットが1本も無い枝**
    (`git init` の直後)で `fatal` を吐く。`/setup` は `git init` してコミットしないと
    自分で書いており、**グリーンフィールドの最初の `/build` はまさにその状態で来る** —
    そこで判定不能にすると、規範が定めた引き渡しのちょうど一点で入口が死ぬ。
    `git branch --show-current` はその状態でも枝の名前を返し、detached では空を返す。
    """
    code, out = git("branch", "--show-current", cwd=cwd)
    return out if code == 0 else None


def default_branches(cwd=None):
    """既定ブランチとして扱う名前の集合と、それがこのリポジトリの事実に基づくか。

    **最初に当たった1つで打ち切らない** ★ — リモートは名前順に出るので、`origin` より前に
    並ぶリモート(`archive` / `backup` / フォーク元)が在ると、**そちらの既定枝が答えになり
    主に使う共有先(ふつうは `origin`)の既定枝が丸ごと外れる**。保護は**緩めるより広げるほうが安全**なので全部足す。

    **取れた名前が実在するかまで確かめる** — `git symbolic-ref` は**指す先が消えていても
    終了コード 0 で名前を返す**(サーバ側で既定枝を改名した後の古いクローンがこれである)。

    **`init.defaultBranch` は最後に置き、しかも「特定できた」とは数えない** ★ —
    あれは `git init` のときに読まれる設定であって、そのリポジトリが実際に使っている枝名の
    記録ではない。git は全利用者にこれを設定せよと助言するので、**入っている機械のほうが
    普通である** — 数えてしまうと、「守れていない」という唯一の合図が黙って消える。
    """
    names, known = set(), False
    code, remotes = git("remote", cwd=cwd)
    for r in ([x for x in remotes.splitlines() if x.strip()] if code == 0 else []):
        code, out = git("symbolic-ref", "--short", f"refs/remotes/{r}/HEAD", cwd=cwd)
        if code != 0 or not out:
            continue
        # `origin/trunk` のようなリモート追跡の名前が返る。**比べる前に接頭辞を落とす** —
        # 現在の枝は `trunk` なので、落とさずに比べると**必ず一致せず、守ろうとした
        # 4つ目の枝をそのまま見逃す**(`flows.md` §7.1)。
        name = REMOTE_PREFIX.sub("", out)
        if git("rev-parse", "--verify", "--quiet",
               f"refs/remotes/{r}/{name}", cwd=cwd)[0] == 0:
            names.add(name)
            known = True
    # **保存場所によらず「特定できた」とは数えない** ★(2026-09-15。inspection-28 C-8)—
    # このリポジトリ自身の設定(`--local`)であっても、あれは `git init` のときに読まれる値で
    # あって、**いま実際に使っている枝名の記録ではない**(init の後に改名しても残る)。
    # 数えると「守れていない」という唯一の合図が黙って消える。
    # **値そのものは保護の側へ足す**(保護は緩めるより広げるほうが安全である)。
    code, out = git("config", "--get", "init.defaultBranch", cwd=cwd)
    if code == 0 and out:
        names.add(out)
    return names, known


def protected_names(cwd=None):
    """保護される枝の名前と、既定ブランチをこのリポジトリの事実から特定できたか。"""
    extra, known = default_branches(cwd=cwd)
    return set(NAMED_PROTECTED) | extra, known


def branch_exists(name, cwd=None):
    return git("rev-parse", "--verify", "--quiet", "refs/heads/" + name, cwd=cwd)[0] == 0


def unfinished(cwd=None):
    """中断した操作か未解決の衝突が残っているか。残っていれば理由の文字列。

    **これを入口で見ないと、止めた意味が次の呼び出しで消える** ★ — 追いつかせるマージが
    衝突して止まったあと、木は作業ブランチの上に在るので、**次のフローの入口は
    「作業ブランチに居る」と言って `0` を返す。** 単独運用の1周は F3 → F2 → F4 を直列に
    回すので、2本目が**衝突の印が入ったファイルを仕様として読み始める。**
    """
    code, out = git("rev-parse", "--git-dir", cwd=cwd)
    if code == 0:
        gd = out if os.path.isabs(out) else os.path.join(cwd or ".", out)
        for f, why in (("MERGE_HEAD", "マージ"), ("CHERRY_PICK_HEAD", "cherry-pick"),
                       ("REVERT_HEAD", "revert"), ("rebase-merge", "rebase"),
                       ("rebase-apply", "rebase")):
            if os.path.exists(os.path.join(gd, f)):
                return f"中断した{why}が残っている"
    code, out = git("ls-files", "--unmerged", cwd=cwd)
    if code == 0 and out:
        return "未解決の衝突が残っている"
    return None


def guard(target, cwd=None, out=print):
    """判定して、必要なら作業ブランチへ移る。終了コードを返す。"""
    if git("rev-parse", "--is-inside-work-tree", cwd=cwd)[1] != "true":
        out("NG  作業ツリーの中に居ない(git リポジトリでない、または bare である)")
        return 1
    if not target.startswith(WORK_PREFIX):
        out(f"NG  移る先が `{WORK_PREFIX}…` ではない: {target}"
            f" — 作業ブランチの名前は `{WORK_PREFIX}<YYYY-MM-DD>-<slug>` である(呼び手の誤り)")
        return 2
    if not valid_branch_name(target, cwd=cwd):
        # **使い方の誤りを `1` に化けさせない** — `1` は人間を呼んで止める合図であり、
        # 直せる誤字で無人の周を止めることになる。**単独運用と艦隊運用で挙動を変えない**
        # ので、`--slug` から組んだ名前も `--name` で渡された名前も、ここで同じ判定を通る。
        out(f"NG  git が枝名として受け取らない: {target}(呼び手の誤り)")
        return 2

    current = current_branch(cwd=cwd)
    if current is None:
        out("NG  いまのブランチを読めない")
        return 1
    if current == "":
        out("NG  どのブランチにも居ない(detached HEAD)— 人間が場所を決めること")
        return 1

    why = unfinished(cwd=cwd)
    if why:
        out(f"NG  {why} — 止まる。**始末してから呼び直すこと**")
        out("    衝突の印が入ったファイルを仕様として読み始めてはならない")
        return 1

    protected, known = protected_names(cwd=cwd)
    if target in protected:
        out(f"NG  移る先が保護ブランチである: {target}(呼び手の誤り)")
        return 2
    if not known:
        # **黙って緩まない。** 名前3つだけで判定していることを言う。
        out("--  既定ブランチを特定できないので、名前3つ"
            f"({' / '.join(NAMED_PROTECTED)})だけで判定する")

    if current not in protected:
        # **「作業ブランチ」と言わない** — この語は `work/…` に予約されている(用語集)。
        out(f"OK  保護ブランチではない: {current}")
        return 0

    if not branch_exists(target, cwd=cwd):
        code, msg = git("switch", "-c", target, cwd=cwd)
        if code != 0:
            out(f"NG  作業ブランチを作れない: {msg}")
            return 1
        out(f"OK  {current} から {target} を作って移った")
        return 0

    # **同じ名前の枝が既に在る。比べる相手は HEAD である**(いま立っている保護ブランチ)。
    # 保護ブランチは最大4つ在りうるので名前を選ぶと、判定した相手と `git branch -d` が
    # 見る相手(あれは HEAD を見る)がずれる。HEAD なら必ず解決するので 128 も出ない。
    # **枝を `refs/heads/` で名指す** ★ — 裸の名前だと、同名のタグが在るときに git は
    # **タグを先に解決する**ので、判定が枝ではなくタグを見る。
    code, msg = git("merge-base", "--is-ancestor", "refs/heads/" + target, "HEAD", cwd=cwd)
    if code == 0:
        # 取り込み済み = 前の周は終わっている。削除して作り直す。
        code, msg = git("branch", "-d", target, cwd=cwd)
        if code != 0:
            out(f"NG  取り込み済みのはずの {target} を消せない — 止まる: {msg}")
            out("    **`-D` を打たないこと。** 別の作業ツリーが使っているなどの事情が在る")
            return 1
        code, msg = git("switch", "-c", target, cwd=cwd)
        if code != 0:
            out(f"NG  {target} を作り直せない: {msg}")
            return 1
        out(f"OK  取り込み済みの {target} を消して、{current} から作り直した")
        return 0
    if code != 1:
        # 128 など。**「取り込み前」ではなく誤りである。**
        out(f"NG  取り込み済みかを判定できない(終了コード {code}): {msg}")
        return 1

    # 取り込み前 = 中断からの再開。**消してはならない** — 前の周の書きかけが在る。
    code, msg = git("switch", target, cwd=cwd)
    if code != 0:
        out(f"NG  {target} へ移れない — 止まる: {msg}")
        out("    前の周の書きかけが在る枝である。未コミットの変更を人間が始末すること")
        return 1
    # **「取り込まれていない」ことと「基点が新しい」ことは別の質問である。**
    # `--is-ancestor` が答えるのは前者だけなので、ここで保護ブランチを取り込む。
    code, msg = git("merge", "--no-ff", "-m",
                    f"基点を追いつかせる({current} を取り込む)", current, cwd=cwd)
    if code != 0:
        # **木を元に戻してから止まる** ★ — 衝突を残したまま戻ると、次のフローの入口が
        # 「作業ブランチに居る」と言って通してしまう(上の `unfinished` と二重に守る)。
        # **戻せたかを確かめてから「戻した」と言う** ★ — 戻せていないのに戻したと言うと、
        # 木は作業ブランチの上に残り、中断の印も消えているので、**次の呼び出しが `0` を返す。**
        back = git("merge", "--abort", cwd=cwd)[0] == 0
        back = back and git("switch", current, cwd=cwd)[0] == 0
        where = "木は元に戻した" if back else f"**木を元に戻せなかった。いま {target} の上に居る**"
        out(f"NG  {current} を取り込めない — 止まる({where}): {msg}")
        out("    前の周の書きかけと保護ブランチが同じ場所を触っている。人間が始末すること")
        return 1
    out(f"OK  中断していた {target} へ戻り、{current} を取り込んで基点を追いつかせた")
    return 0


def selftest():
    """一時リポジトリで、規範が書いている経路を実際に走らせる。

    **覆えていないものは「覆えている」と言わない** — 下の「守れない」の事例がそれである。
    """
    ok, ran = True, 0

    def check(label, got, want):
        # **件数は数える。書かない**(このキットが `CS21` で禁じる「件数の主張」である)。
        nonlocal ok, ran
        ran += 1
        if got == want:
            print(f"  PASS  {label}")
        else:
            print(f"  NG    {label}(期待 {want!r} / 実際 {got!r})", file=sys.stderr)
            ok = False

    # **利用者の設定から隔離する** ★ — `git config --unset` はリポジトリ設定しか消せないので、
    # 隔離しないと `init.defaultBranch = trunk` を持つ機械で自己検査が落ちる(実測)。
    # **自己検査が人によって赤くなると、誰も走らせなくなる。**
    global ENV
    ENV = dict(os.environ, LC_ALL="C", LANG="C",
               GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull)

    def repo(td, branch="main"):
        git("init", "-q", "-b", branch, td)
        git("config", "user.email", "t@example.invalid", cwd=td)
        git("config", "user.name", "t", cwd=td)

    def commit(td, name="spec.md", text="v1\n", msg="c"):
        with open(os.path.join(td, name), "w", encoding="utf-8") as f:
            f.write(text)
        git("add", "-A", cwd=td)
        git("commit", "-qm", msg, cwd=td)

    quiet = lambda *a, **k: None
    W = "work/x"

    with tempfile.TemporaryDirectory() as td:
        repo(td)
        # **コミットが1本も無いリポジトリ**(`/setup` の直後。グリーンフィールドの入口)
        check("コミットが無くても枝を切れる", guard(W, cwd=td, out=quiet), 0)
        check("切った先に居る", current_branch(cwd=td), W)

    with tempfile.TemporaryDirectory() as td:
        repo(td); commit(td)
        check("保護ブランチなら作って移る", guard(W, cwd=td, out=quiet), 0)
        check("既に作業ブランチなら何もしない", guard(W, cwd=td, out=quiet), 0)

    with tempfile.TemporaryDirectory() as td:
        repo(td); commit(td)
        git("switch", "-q", "-c", W, cwd=td); commit(td, "a.md", "a\n", "w")
        git("switch", "-q", "main", cwd=td)
        git("merge", "-q", "--no-ff", "-m", "m", W, cwd=td)
        commit(td, "spec.md", "v2\n", "later")
        check("取り込み済みは作り直す", guard(W, cwd=td, out=quiet), 0)
        check("作り直した枝は最新の基点",
              open(os.path.join(td, "spec.md"), encoding="utf-8").read().strip(), "v2")

    with tempfile.TemporaryDirectory() as td:
        repo(td); commit(td)
        git("switch", "-q", "-c", W, cwd=td); commit(td, "wip.md", "書きかけ\n", "wip")
        git("switch", "-q", "main", cwd=td); commit(td, "spec.md", "v2\n", "later")
        check("取り込み前は移って追いつかせる", guard(W, cwd=td, out=quiet), 0)
        check("基点が追いついている",
              open(os.path.join(td, "spec.md"), encoding="utf-8").read().strip(), "v2")
        check("書きかけが残っている", os.path.isfile(os.path.join(td, "wip.md")), True)

    with tempfile.TemporaryDirectory() as td:
        repo(td); commit(td)
        git("switch", "-q", "-c", W, cwd=td); commit(td, "spec.md", "枝の側\n", "b")
        git("switch", "-q", "main", cwd=td); commit(td, "spec.md", "本流の側\n", "m")
        check("衝突したら止まる", guard(W, cwd=td, out=quiet), 1)
        # **止めた意味が次の呼び出しで消えないこと。** ここが本体である。
        check("衝突を残さず元へ戻す", current_branch(cwd=td), "main")
        check("2度目も通さない", guard(W, cwd=td, out=quiet), 1)

    with tempfile.TemporaryDirectory() as td:
        repo(td); commit(td)
        git("switch", "-q", "-c", W, cwd=td); commit(td, "spec.md", "枝\n", "b")
        git("switch", "-q", "main", cwd=td); commit(td, "spec.md", "本\n", "m")
        git("merge", "--no-ff", "-m", "x", W, cwd=td)      # 手で衝突を作って放置する
        check("中断したマージが残っていれば止まる", guard(W, cwd=td, out=quiet), 1)

    with tempfile.TemporaryDirectory() as td:
        # **同名のタグが在っても、枝を見る**(git はタグを先に解決する)
        repo(td); commit(td)
        git("switch", "-q", "-c", W, cwd=td); commit(td, "a.md", "a\n", "w")
        git("switch", "-q", "main", cwd=td)
        git("merge", "-q", "--no-ff", "-m", "m", W, cwd=td)
        git("tag", W, "HEAD~1", cwd=td)                    # 枝より古いところを指すタグ
        check("同名のタグに騙されない", guard(W, cwd=td, out=quiet), 0)

    with tempfile.TemporaryDirectory() as td:
        # クローンで `origin/HEAD` が張られる = 現実に起きる形
        src = os.path.join(td, "src"); os.makedirs(src)
        repo(src, branch="trunk"); commit(src)
        dst = os.path.join(td, "dst")
        git("clone", "-q", src, dst)
        git("config", "user.email", "t@example.invalid", cwd=dst)
        git("config", "user.name", "t", cwd=dst)
        check("既定ブランチが trunk のクローンを守る", guard(W, cwd=dst, out=quiet), 0)
        check("trunk から移った", current_branch(cwd=dst), W)

    with tempfile.TemporaryDirectory() as td:
        # **`origin` より前に並ぶリモートに、`origin` の既定枝を上書きさせない** ★
        # リモートは名前順に出るので、最初に当たった1つで打ち切ると `archive` が勝つ。
        up = os.path.join(td, "up"); os.makedirs(up)
        repo(up, branch="trunk"); commit(up)
        mir = os.path.join(td, "mirror"); os.makedirs(mir)
        repo(mir, branch="master"); commit(mir)
        dst = os.path.join(td, "dst")
        git("clone", "-q", up, dst)
        git("config", "user.email", "t@example.invalid", cwd=dst)
        git("config", "user.name", "t", cwd=dst)
        git("remote", "add", "archive", mir, cwd=dst)
        git("fetch", "-q", "archive", cwd=dst)
        git("remote", "set-head", "archive", "-a", cwd=dst)
        names, _ = protected_names(cwd=dst)
        check("前に並ぶリモートに上書きされない", "trunk" in names, True)
        check("前に並ぶリモートの既定枝も足す", "master" in names, True)
        check("trunk を守って移る", guard(W, cwd=dst, out=quiet), 0)

    with tempfile.TemporaryDirectory() as td:
        # **覆えていないことを、覆えているふりで隠さない** ★
        # リモートも `init.defaultBranch` も無い `trunk` は、名前3つに当たらないので守れない。
        # 規範(`flows.md` §7.1)が「それ以上は推測しない」と決めている範囲である。
        repo(td, branch="trunk"); commit(td)
        check("リモートも設定も無い trunk は守れない(既知の穴)",
              guard(W, cwd=td, out=quiet), 0)
        check("その場合そのまま trunk に居る", current_branch(cwd=td), "trunk")
        check("特定できないことは黙らない", protected_names(cwd=td)[1], False)

    with tempfile.TemporaryDirectory() as td:
        # **利用者全体の設定だけでは「特定できた」と数えない**(黙って緩まない)
        gc = os.path.join(td, "gitconfig")
        with open(gc, "w", encoding="utf-8") as f:
            f.write("[init]\n\tdefaultBranch = trunk\n")
        repo(td, branch="trunk"); commit(td)
        saved = ENV
        try:
            ENV = dict(saved, GIT_CONFIG_GLOBAL=gc)
            check("利用者全体の設定は「特定できた」に数えない",
                  protected_names(cwd=td)[1], False)
            check("値そのものは保護に使う", "trunk" in protected_names(cwd=td)[0], True)
        finally:
            ENV = saved

    with tempfile.TemporaryDirectory() as td:
        # **枝名の可否は git に聞く** — 日本語の slug は通し、git が撥ねる形は 2 で返す
        repo(td); commit(td)
        check("日本語の slug を撥ねない", guard("work/2026-01-01-ユーザ認証", cwd=td, out=quiet), 0)
    for bad in ("work/x.lock", "work/x..y", "work/a b", "work/", "work/.hidden"):
        with tempfile.TemporaryDirectory() as td:
            repo(td); commit(td)
            check(f"git が撥ねる名前は 2 で返す({bad})", guard(bad, cwd=td, out=quiet), 2)
            check(f"そのとき枝を作らない({bad})",
                  [b for b in git("branch", "--list", cwd=td)[1].split()
                   if b.startswith(WORK_PREFIX)], [])

    with tempfile.TemporaryDirectory() as td:
        repo(td); commit(td)
        check("移る先が保護ブランチなら撥ねる", guard("develop", cwd=td, out=quiet), 2)
        check("work/ で始まらない名前も撥ねる", guard("feature-1", cwd=td, out=quiet), 2)
        check("撥ねたとき枝は作らない", branch_exists("develop", cwd=td), False)

    with tempfile.TemporaryDirectory() as td:
        repo(td); commit(td)
        git("checkout", "-q", git("rev-parse", "HEAD", cwd=td)[1], cwd=td)
        check("detached HEAD では止まる", guard(W, cwd=td, out=quiet), 1)

    with tempfile.TemporaryDirectory() as td:
        check("git リポジトリでなければ止まる", guard(W, cwd=td, out=quiet), 1)

    print(f"全 {ran} 項目 PASS" if ok else f"NG あり({ran} 項目走らせた)",
          file=sys.stdout if ok else sys.stderr)
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(add_help=True, description=__doc__.splitlines()[0])
    ap.add_argument("--slug", help="work/<今日>-<slug> を使う")
    ap.add_argument("--verify", action="store_true", help="work/<今日>-verify を使う")
    ap.add_argument("--name", help="この名前をそのまま使う(艦隊の work/<mid>)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    chosen = [x for x in (a.slug, a.verify or None, a.name) if x]
    if len(chosen) != 1:
        print("エラー: --slug / --verify / --name のどれか1つを渡すこと", file=sys.stderr)
        return 2
    if a.name:
        target = a.name
    else:
        slug = "verify" if a.verify else a.slug
        target = f"work/{datetime.date.today().isoformat()}-{slug}"
    return guard(target)


if __name__ == "__main__":
    raise SystemExit(main())
