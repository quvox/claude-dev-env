#!/usr/bin/env python3
"""役の規範を起動時に渡してエージェントを起こす — claude と codex の差を1か所に閉じ込める。

使い方:
    python3 .claude/scripts/launch-agent.py <kind> <role> [--sandbox danger-full-access] [-- <追加の引数>...]

  kind  claude | codex
  role  .claude/roles/<role>.md のファイル名(拡張子を除いたもの)

**なぜこの script が要るか。**
claude には `--append-system-prompt-file` があり、役の規範をファイルのまま渡せる。
codex に同じ口(`-c developer_instructions=...`)は在るが、**受け取るのは文字列である。**
`colabtmux.conf` の `command` は静的な配列なので、そこでファイルを読むことができない。
起動行に「このファイルを読め」と書く形にすると、**読み損なう経路が残る** —
claude 側には無い経路なので、そこだけ kind による差が生まれる。
この script がファイルを読んで中身を渡すことで、**両方の kind で「役は起動時に決まる」**
が成り立つ(`.claude/directions/orchestration.md` §1.1)。

**渡すのは役のファイル1本だけである。** 起動時に何かを組み立てたり繋いだりしない ★ —
**ファイルを見れば、そのエージェントが何を受け取るかが分かる**状態を保つためである。
役に共通することは `CLAUDE.md` §2 が持つ(`AGENTS.md` はそれへのリンクなので、claude も codex も同じものを読む)。

**claude にはパスをそのまま渡す。** codex の `-c developer_instructions=` は文字列しか受けないので、
**そのときだけファイルを読んで中身を渡す** — 読むのは1本で、繋ぎ合わせはしない。

**codex の砂箱のモードは1つだけである — `danger-full-access`** ★(2026-09-20 に改めた。
人間の指示)。役によらず、ホストによらず、この script が必ずこれを渡す。**選ぶ余地は無い**ので、
`--sandbox` に他の値を書いたら止まる(書き忘れても同じものが入る)。
`--ask-for-approval never` も落とさない — 承認で止まるウィンドウは、止まったウィンドウと
同じだからである。**この2つで1組**であり、片方だけでは無人にならない。
**これが何を外すのかと、その代わりに何が守るのかは `orchestration.md` §1.1.1 が持つ。**
"""

import argparse
import os
from pathlib import Path
import shlex
import sys


ROOT = Path(__file__).resolve().parents[2]
ROLES = ROOT / '.claude/roles'


def roles() -> list[str]:
    """在る役の名前。先頭が `_` のものは役ではない。"""
    return sorted(p.stem for p in ROLES.glob('*.md') if not p.name.startswith('_'))


def _read(path: Path) -> str:
    text = path.read_text(encoding='utf-8')
    if not text.strip():
        sys.exit(f'役の規範が空です: {path}')
    return text


def role_path(role: str) -> Path:
    """その役の規範のパス。**在る役の名前と完全に一致するときだけ通す。**"""
    # パスの形(`./x` `../templates/AGENTS`)で、役のディレクトリの外を読ませられないようにする。
    if role not in roles():
        sys.exit(f'そんな役はありません: {role}\n在るのは: {", ".join(roles())}')
    return ROLES / f'{role}.md'


def role_text(role: str) -> str:
    """その役へ渡す本文。**1本のファイルをそのまま読むだけである。**"""
    return _read(role_path(role))


# **追加の引数で上書きさせないもの。** ここを重ねて渡せると、役の本文が差し替わったり、
# 無人で走る保証(承認で止まらないこと)が外れたりする。起動の口を1本にした意味が消えるので拒む。
PROTECTED = {
    'claude': ('--append-system-prompt', '--append-system-prompt-file', '--permission-mode'),
    # codex は同じことを何通りにも書ける(`-c k=v` / `-cK=v` / `--config k=v` / `--config=k=v` /
    # 短縮の `-s` `-a`)。**前方一致だけでは素通りする**(2026-09-14 に実測で抜けられた)ので、
    # **形を正規化してから見る。**
    'codex': ('--sandbox', '-s', '--ask-for-approval', '-a'),
}

# `-c` / `--config` で渡されると困る設定のキー。
PROTECTED_CONFIG_KEYS = ('developer_instructions', 'sandbox_mode', 'approval_policy')


def check_extra(kind: str, extra: list[str]) -> None:
    """`--` の後ろに、この script が決めるものを重ねて渡させない。"""
    # **`--print` を `--` の後ろに置くと、表示のつもりで本当に起こしてしまう。**
    for own in ('--print', '--sandbox'):
        if own in extra:
            sys.exit(f'{own} は `--` より前に置いてください(後ろに置くと起動コマンドへ渡ります)')

    for i, arg in enumerate(extra):
        head = arg.split('=', 1)[0]
        if head in PROTECTED[kind] or arg in PROTECTED[kind]:
            sys.exit(f'`--` の後ろに {head} は渡せません: {arg}\n'
                     f'  砂箱のモードと、無人で走るための設定は、この script が決めます'
                     f'(codex の砂箱は danger-full-access の1つだけです)。')
        if kind != 'codex':
            continue
        # `-c k=v` / `-ck=v` / `--config k=v` / `--config=k=v` のどれでも中身を取り出す
        value = None
        if head in ('-c', '--config'):
            value = arg.split('=', 1)[1] if '=' in arg else (
                extra[i + 1] if i + 1 < len(extra) else '')
        elif arg.startswith('-c') and len(arg) > 2:
            value = arg[2:]
        if value is None:
            continue
        key = value.split('=', 1)[0].strip().strip('"\'')
        if key in PROTECTED_CONFIG_KEYS:
            sys.exit(f'`--` の後ろに設定 {key} は渡せません: {arg}\n'
                     f'  役の本文と、無人で走るための設定は、この script が決めます。')


# **codex の砂箱のモードはこれ1つである**(`orchestration.md` §1.1.1)。役でもホストでも分かれない。
SANDBOX = 'danger-full-access'


def build_command(kind: str, role: str, extra: list[str]) -> list[str]:
    check_extra(kind, extra)
    if kind == 'claude':
        # **ファイルのパスをそのまま渡す。** 中身を読む必要が無い。
        path = role_path(role)
        _read(path)   # 在否と、空でないことだけ確かめる
        command = ['claude', '--permission-mode', 'auto',
                   '--append-system-prompt-file', str(path.relative_to(ROOT))]
        return command + extra
    if kind == 'codex':
        # **2つで1組である**(orchestration.md §1.1.1)。`never` だけでは砂箱が書込みを拒み、
        # 砂箱のモードだけでは承認で止まる。どちらも落とさない。
        # `-c sandbox_workspace_write.network_access=true` は足さない ★ —
        # あれは workspace-write 専用の設定で、砂箱を使わないこのモードでは効かず、要りもしない。
        command = ['codex', '--ask-for-approval', 'never', '--sandbox', SANDBOX]
        # AGENTS.md は基本として読まれたまま、この中身が上に足される。
        command += ['-c', f'developer_instructions={role_text(role)}']
        return command + extra
    sys.exit(f'未対応の kind です: {kind}')


def main() -> None:
    parser = argparse.ArgumentParser(
        description='役の規範を起動時に渡してエージェントを起こす',
        epilog='`--` の後ろに書いたものは、そのまま起動コマンドの末尾へ足される'
               '(例: --model opus --effort high)',
    )
    parser.add_argument('kind', choices=['claude', 'codex'])
    parser.add_argument('role')
    parser.add_argument('--sandbox', default=None,
                        help=f'codex の砂箱のモード。**{SANDBOX} しか無い**ので、'
                             '書かなくても同じものが入る(書くなら同じ値だけ)。'
                             '役でもホストでも分かれない(orchestration.md §1.1.1)')
    parser.add_argument('--print', dest='print_only', action='store_true',
                        help='起こさずに、組み立てた起動コマンドを表示するだけにする')
    # `--` の後ろは argparse に解釈させない(`--model` 等がこの script の option に見えるため)。
    # **REMAINDER は使わない** — `--print` のような自分の option まで飲み込み、
    # 表示するだけのつもりが本当にエージェントを起こしてしまう(2026-09-14 に実際に踏んだ)。
    args, extra = parser.parse_known_args()
    if extra and extra[0] == '--':
        extra = extra[1:]
    # **claude では砂箱のモードを使わない。** 黙って無視すると、`@qa` を claude へ落とすときに
    # 「指定したのに効いていない」に気づけない(§1.4)。
    if args.kind == 'claude' and args.sandbox is not None:
        sys.exit('--sandbox は codex にだけ効きます(claude には砂箱のモードがありません)')
    # **古い起動行を黙って読み替えない** ★ — `workspace-write` や `none` を渡してくる呼出しは
    # 「砂箱が掛かっている」前提で書かれているので、そのまま通すとその前提が静かに外れる。
    if args.sandbox is not None and args.sandbox != SANDBOX:
        sys.exit(f'codex の砂箱のモードは {SANDBOX} だけです(渡されたのは {args.sandbox})\n'
                 f'  2026-09-20 に1つへ固定しました。理由と、外側で何が守るかは'
                 f' .claude/directions/orchestration.md §1.1.1 に在ります。')
    command = build_command(args.kind, args.role, extra)
    if args.print_only:
        # **そのまま貼って実行できる形で出す。** 役の本文は改行と引用符を含むので、
        # 素の空白つなぎでは行にならない。
        print(shlex.join(command))
        return
    os.chdir(ROOT)
    os.execvp(command[0], command)


if __name__ == '__main__':
    main()
