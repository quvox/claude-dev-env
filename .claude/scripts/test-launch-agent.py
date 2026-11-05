#!/usr/bin/env python3
"""launch-agent.py の自己検査 — 実際にエージェントを起こさずに起動コマンドだけを見る。

走らせ方: python3 .claude/scripts/test-launch-agent.py
"""

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]

spec = importlib.util.spec_from_file_location(
    'launch_agent', ROOT / '.claude/scripts/launch-agent.py')
launch_agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launch_agent)

failures: list[str] = []

def _exits(module, role: str) -> bool:
    """その役名で止まる(SystemExit になる)なら True。"""
    try:
        module.build_command('codex', role, [])
    except SystemExit:
        return True
    return False




def check(label: str, condition: bool, detail: str = '') -> None:
    if condition:
        print(f'  OK  {label}')
    else:
        print(f'  NG  {label}{": " + detail if detail else ""}')
        failures.append(label)


def main() -> None:
    print('## launch-agent.py の自己検査')

    own = (ROOT / '.claude/roles/work.md').read_text(encoding='utf-8')

    # 1. claude にはファイルのパスをそのまま渡す(中身を読まない)
    cmd = launch_agent.build_command('claude', 'work', [])
    check('claude: --append-system-prompt-file でパスを渡す',
          '--append-system-prompt-file' in cmd
          and cmd[cmd.index('--append-system-prompt-file') + 1] == '.claude/roles/work.md',
          str(cmd))
    check('claude: 本文を引数に埋め込まない', not any(own[:40] in a for a in cmd))
    check('claude: --permission-mode auto が落ちていない',
          '--permission-mode' in cmd and cmd[cmd.index('--permission-mode') + 1] == 'auto')

    # 2. codex には同じファイルの中身を渡す(口が文字列しか受けないため)
    cmd = launch_agent.build_command('codex', 'work', [])
    injected = [a for a in cmd if a.startswith('developer_instructions=')]
    check('codex: developer_instructions を渡す', len(injected) == 1, str(cmd[:6]))
    codex_text = injected[0][len('developer_instructions='):] if injected else ''
    check('codex: 渡すのはパスではなく中身', codex_text == own)

    # 3. **起動時に何も組み立てない** — 渡るのは役のファイル1本の中身だけである
    check('役のファイル1本ぶんだけが渡る(連結しない)', codex_text == own)
    for role in ('orchestrator', 'discuss', 'review', 'survey', 'qa', 'triage'):
        t = [a for a in launch_agent.build_command('codex', role, [])
             if a.startswith('developer_instructions=')][0][len('developer_instructions='):]
        if t != (ROOT / f'.claude/roles/{role}.md').read_text(encoding='utf-8'):
            check(f'{role} も1本だけ', False)
            break
    else:
        check('どの役でも1本だけが渡る', True)

    # 役名はパスの形で回避できない
    for bad in ('./work', '../templates/AGENTS', '.claude/roles/work'):
        if not _exits(launch_agent, bad):
            check(f'パスの形 {bad} を弾く', False)
            break
    else:
        check('役名をパスの形で回避できない', True)

    # 5. 砂箱は役によらず danger-full-access の1つだけである(orchestration.md §1.1.1)
    check('codex: 砂箱は danger-full-access',
          '--sandbox' in cmd and cmd[cmd.index('--sandbox') + 1] == 'danger-full-access',
          str(cmd[:6]))
    check('codex: workspace-write 専用の network_access を足さない',
          not any('network_access' in a for a in cmd))
    qa = launch_agent.build_command('codex', 'qa', [])
    check('codex: @qa も同じ1つのモードで起きる',
          '--sandbox' in qa and qa[qa.index('--sandbox') + 1] == 'danger-full-access')
    check('codex: 役によって砂箱が分かれない',
          [a for a in cmd if not a.startswith('developer_instructions=')]
          == [a for a in qa if not a.startswith('developer_instructions=')])
    # **無人で走ること**が落ちない(承認で止まるウィンドウは止まったのと同じ)
    for label, c in [('work', cmd), ('@qa', qa)]:
        check(f'codex: {label} でも --ask-for-approval never が入る',
              '--ask-for-approval' in c and c[c.index('--ask-for-approval') + 1] == 'never')
    check('codex: 役の注入は残る',
          all(any(a.startswith('developer_instructions=') for a in c) for c in (cmd, qa)))
    # 古い値を渡してきた起動行は、黙って読み替えずに止まる(前提が静かに外れないように)
    for bad in ('workspace-write', 'none'):
        done = subprocess.run([sys.executable, str(ROOT / '.claude/scripts/launch-agent.py'),
                               'codex', 'work', '--sandbox', bad, '--print'],
                              capture_output=True, text=True)
        check(f'codex: --sandbox {bad} は止まる',
              done.returncode != 0 and 'danger-full-access' in done.stderr,
              done.stdout[:60] + done.stderr[:120])

    # 6. `--` の後ろはそのまま末尾へ
    cmd = launch_agent.build_command('claude', 'orchestrator',
                                     ['--model', 'opus', '--effort', 'high'])
    check('追加の引数が末尾に付く', cmd[-4:] == ['--model', 'opus', '--effort', 'high'])

    # 7. 在るはずの役がすべて引ける(ファイル名 = 役の名前。先頭 _ は役ではない)
    roles = sorted(p.stem for p in (ROOT / '.claude/roles').glob('*.md')
                   if not p.name.startswith('_'))
    check('役が1つ以上在る', bool(roles), str(roles))
    for role in roles:
        try:
            launch_agent.build_command('codex', role, [])
        except SystemExit as exc:
            check(f'役 {role} を引ける', False, str(exc))
            continue
    check('すべての役を引けた', True)

    # 8. 無い役・空の役は、黙って起こさずに止まる
    for bad, label in [('no-such-role', '無い役で止まる')]:
        try:
            launch_agent.build_command('codex', bad, [])
        except SystemExit:
            check(label, True)
        else:
            check(label, False, '止まらなかった')

    with tempfile.TemporaryDirectory() as tmp:
        empty = Path(tmp) / 'empty.md'
        empty.write_text('   \n', encoding='utf-8')
        original = launch_agent.ROLES
        try:
            launch_agent.ROLES = Path(tmp)
            try:
                launch_agent.build_command('codex', 'empty', [])
            except SystemExit:
                check('空の役で止まる', True)
            else:
                check('空の役で止まる', False, '止まらなかった')
        finally:
            launch_agent.ROLES = original

    print()
    if failures:
        print(f'NG {len(failures)} 件: ' + ', '.join(failures))
        sys.exit(1)
    print('すべて通りました')


if __name__ == '__main__':
    main()
