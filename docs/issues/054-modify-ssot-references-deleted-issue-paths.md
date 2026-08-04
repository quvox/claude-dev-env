---
id: 054-modify-ssot-references-deleted-issue-paths
type: modify
severity: 低
found: 2026-08-05
found_in: /doc-check ssot task-fix-destructive-scope(C10 参照の実在検査)
related: docs/00-requests/decisions/env.md, docs/02-design/contracts/cli-container.md, docs/03-impl/relations/MODULE-cli-stop.md, docs/03-impl/relations/MODULE-cli-reset.md, docs/03-impl/index.md, docs/issues/030
summary: 解消して削除された issue のファイルパス(docs/issues/NNN)が仕様ドキュメントの根拠として残り続けるため、10 個の ID・20 以上のファイルで参照先が実在しない
---

# 054 SSOT が削除済み issue のパスを参照し続ける

## 事象

`/task-close` は解消した issue を histories へ記録してから**ファイルを削除する**
(`.claude/directions/issues-pendings.md` の Lifecycle)。一方、仕様ドキュメントは
その issue を**根拠・経緯として `docs/issues/NNN` というパス表記で本文に埋め込んでいる**。
削除後もその表記は残るため、参照先が実在しないまま残る。

2026-08-05 時点の実測(00〜03 の全ファイルを走査):

| 実在しない issue ID | 参照しているファイル数 | 代表例 |
|---|---|---|
| `018` | 1 | `docs/00-requests/decisions/sec.md` |
| `020` | 8 | `decisions/env.md`, `02-design/contracts/cli-container.md`, `MODULE-cli-reset`, `MODULE-cli-login` ほか |
| `024` | 5 | `decisions/env.md`, `02/03 の contracts/cli-container.md`, `MODULE-cli-stop`, `MODULE-cli-start` |
| `025` | 1 | `decisions/env.md` |
| `034` | 2 | `decisions/orch.md`, `MODULE-orchestrator-review` |
| `035` | 3 | `01-requirements/non-functional.md`, `02-design/contracts/orchestrator-prompt.md`, `03-impl/index.md` |
| `037` | 1 | `03-impl/tests/cli-pull.md` |
| `039` | 3 | `decisions/orch.md`, `decisions/sec.md`, `01-requirements/functional.md` |
| `040` | 5 | `decisions/auth.md`, `01-requirements/functional.md`, `02-design/architecture.md` ほか |
| `045` | 3 | `02-design/contracts/cli-container.md`, `MODULE-cli-stop`, `03-impl/tests/e2e.md` |

**本タスク固有の問題ではない**(`018` / `034` / `035` / `037` / `039` / `040` は
本タスクより前のタスクが閉じた分である)。`020` / `024` / `025` / `045` が
2026-08-04 の `task-fix-destructive-scope` で新たに加わった。

とくに `docs/03-impl/index.md` は「`024` だけは `MODULE-cli-stop` の『既知の制限』から
**移行期の残り**として今も参照されている」と、**現役の参照であることを明示して**書いている。
その参照先は実在しない。

## 影響

読み手が「なぜこの決定になったのか」を追えない。ドキュメントの整合そのものは壊れておらず、
振る舞いにも影響しないので severity は「低」。ただし**根拠を辿れないこと自体が
本体系の価値(判断の追跡可能性)を削る**。

## 原因の見当

キット側のライフサイクル規則が、**issue ファイルの削除と、それを参照している SSOT の本文の
書き換えを結びつけていない**(推測ではなく `issues-pendings.md` の Lifecycle 節と
`/task-close` の手順から読める)。histories には記録が残るが、
**本文の表記は `docs/issues/NNN` というパスのままなので histories へは辿れない**。

## 正はどちらか

要件・設計・実装のいずれの問題でもなく、**記録の運用規則の問題**である。
どちらかが誤っているのではなく、規則に抜けがある。

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | `/task-close` が issue を削除する前に、その ID を参照している SSOT の表記を **histories のパスへ書き換える**(`docs/issues/024` → `docs/histories/2026-08-04-fix-destructive-scope.md`) | キット(`/task-close` と `issues-pendings.md`)+ 既存の10 ID 分の一括置換 |
| B | 解消した issue を**削除せず** `docs/issues/closed/` へ移す(パスは変わるので参照の書き換えは要る。ただし本文はそのまま残る) | キット + 既存分の移動と置換 |
| C | 参照表記を最初から ID だけ(「`issue 024`」)にし、パスを書かない規約にする。ID から辿る先は `docs/issues/index.md` と histories | キット(`.claude/directions/issues-pendings.md` の書式)+ 既存分の置換 |

**推奨は C**(削除の運用を変えずに済み、`index.md` と histories という既存の索引だけで
辿れるようになる)。**キット側の規則を変える案件でもあるため、`/kit-improve` と両輪で扱う。**

## 経緯

- 2026-08-05 `/doc-check ssot task-fix-destructive-scope` が参照の実在検査で検出した。
  本タスクの影響範囲の外にも同じ形の参照が広がっているため、
  **本タスクでは直さず起票のみ**とした(CLAUDE.md 原則8。範囲外の修正を混ぜない)。
