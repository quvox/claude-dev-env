---
id: 009-modify-relations-prose-signatures-drift-from-code
type: modify
severity: 中
found: 2026-08-03
found_in: task-docs-restructure の /doc-check ssot(独立レンズ=Codex の B4 指摘を起点に、Claude が全 orchestrator relations へ機械的に横展開して発見)
related: MODULE-orchestrator-session, MODULE-orchestrator-worktree, MODULE-orchestrator-worker, MODULE-orchestrator-mode, MODULE-orchestrator-review, MODULE-orchestrator-slack, MODULE-orchestrator-term, MODULE-orchestrator-handoff, MODULE-orchestrator-claude-exec, MODULE-orchestrator-dashboard
summary: relations の「処理の流れ」本文が書く関数シグネチャが実コードと一致しない箇所が約27件あり、省略記法として許容するのか誤りとして直すのかの規約が無い
---

# 009 relations 本文の関数シグネチャが実コードと食い違う(規約が未定)

## 事象

`docs/03-impl/relations/MODULE-orchestrator-*.md` の「処理の流れ」節が本文で引用している関数
シグネチャを、`orchestrator/*.go` の実シグネチャと機械的に突き合わせたところ、**引数の個数が
一致しないものが約 27 件**あった(`cmd.Run()` など標準ライブラリの同名メソッドへの誤突合 3 件を
除いた数)。

再現手順:

1. `orchestrator/*.go`(`_test.go` を除く)から `func` 定義のシグネチャを収集する。
2. `docs/03-impl/relations/MODULE-orchestrator-*.md` の本文から バッククォートで囲まれた
   `Name(引数...)` 形式の記述を収集する。
3. 同名の関数について引数の個数を比較する。

内訳は**性質の異なる2種類**が混在している。

**(a) `ctx context.Context` を省略した記法**(大半):

| ドキュメントの記述 | 実シグネチャ |
|---|---|
| `Has(window)` / `SwitchTo(window)` / `Kill(window)` / `PaneDead(window)` | `(ctx context.Context, target string)` |
| `DetectSession()` / `SetupMainSession()` | `(ctx context.Context)` |
| `LaunchInteractive(window, script)` | `(ctx context.Context, target, scriptPath string)` |
| `PrepareWorktree(taskID)` | `(ctx context.Context, t *Task)` |
| `WorktreeRemove(taskID)` | `(ctx context.Context, repoDir, path string)` |
| `CleanOrchWorktrees()` | `(ctx context.Context, repoDir, worktreesDir string)` |
| `RunInteractive(ctx)` | `(ctx context.Context, args ...string)` |
| `WaitConsume(until)` | `(ctx context.Context, poll time.Duration, until func() bool)` |

**(b) 引数の顔ぶれ自体が違うもの**(省略では説明できない):

| ドキュメントの記述 | 実シグネチャ |
|---|---|
| `NewSessionManager(cname)` | `NewSessionManager()`(引数なし) |
| `Worker.BuildPrompt(task)` | `(p *Plan, t *Task, feedback string)` |
| `Reviewer.RunGate(ctx, task)` | `(ctx context.Context, p *Plan, t *Task)` |
| `Merge(taskID, strategy)` | `(ctx context.Context, repoDir, branch, strategy string)` |
| `ResolveArgs()` / `ResolveArgsOne()` / `IntervenePrompt()` | それぞれ `(ids []string)` / `(id string)` / `(id string)` |
| `NewSlackNotifier()` | `(cfg Config)` |
| `selectMenu(options, default)` | `(title string, items []menuItem, def int)` |
| `ExecClaude.RunPrompt(ctx, args, out)` | `(ctx context.Context, dir, model, prompt, logPath string, opts RunOpts)` |
| `EnsureAll()` | `(ctx context.Context, phase string, plan *Plan)` |
| `ExpectedWindows()` | `(phase string, plan *Plan)` |

## 影響

`03-impl` は「ドキュメントだけから再実装・再試験できる」ことを目的とする層なので、本文の
シグネチャを信じて呼び出し側を書くと合わない。とくに (b) は引数の**意味**が違う
(`NewSessionManager` にコンテナ名を渡せると読める、`Merge` にタスクIDを渡せると読める)ため、
読み手を誤らせる。

severity を「中」とした根拠: 機械検査が見ている面(frontmatter の `impl` / `callers` / `callees` /
`tests`、および「呼び出され方」の引数表)は正確で、`check-relations.py` と
`callgraph-check.py` は合格している。食い違うのは**本文の叙述**に限られる。

## 原因の見当

`.claude/directions/relations.md:112` は「処理の流れ」について
`No code snippets longer than a signature.` とだけ定めており、**本文で関数を引くときに完全な
シグネチャを書くのか、要点だけの省略記法でよいのかを定義していない**。テンプレート
`03-relation.md` が型・必須・制約を要求しているのは「呼び出され方」の引数表(=その機能の入口)
だけで、本文中の内部関数の引用は対象外である。

推測: 執筆時にコードの呼び出し箇所ではなく処理の意味を見て書いたため、`ctx` のような
定型引数が自然に落ち、(b) は初期の設計時の名残がそのまま残ったとみられる。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| (b) 引数の顔ぶれが違う 10 件 | 本文のシグネチャは実コードと一致しない | 02 は個々の内部関数のシグネチャを定めていない | **実装が正**(本文を直すべき) |
| (a) `ctx` の省略 17 件 | 本文は `ctx` を書かない | 規約が存在しない | **要確認**(省略を許す規約を明文化するか、完全一致を求めるか) |

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | (b) の 10 件だけ実コードに合わせて直し、(a) は「本文では `ctx` 等の定型引数を省略してよい」と `.claude/directions/relations.md` に明文化する | relations 7ファイル + directions 1ファイル。`/kit-improve` を併用 |
| B | 全 27 件を完全シグネチャへ揃え、本文でも省略しないと規約化する | relations 11ファイル + directions 1ファイル。記述が冗長になる |
| C | 本文のシグネチャ記述をやめ、関数名だけを引く(引数は「呼び出され方」の表に一本化する) | relations 11ファイル。読み手が本文だけで呼び出し方を掴めなくなる |

推奨は A(機械検査が見ている面は既に正確で、(b) だけが実害のある誤り)。ただし
**規約の選択は人間の判断**なので勝手に決めない。

## 経緯

- 2026-08-03 起票。`/doc-check ssot task-docs-restructure` の独立レンズ(Codex `relations` モード)が
  `MODULE-orchestrator-plan` / `-state` / `-mode` / `-worker` の 4 件を指摘し、Claude がコードで
  裏取りして修正した。その際に**同種の食い違いが他にも無いかを機械的に横展開**して本件を発見した。
  レンズが指摘した 4 件はこの実行で修正済みで、本 issue が扱うのは**残る約 27 件と規約の欠落**である。
- 2026-08-03 `task-impl-depth` の `/doc-check`(task モード)が、(b) と同種の食い違いが
  **「本文の散文」ではなく「`## 呼び出され方` の引数表」にも残っている**ことを発見した
  (独立レンズ Codex `readiness` の指摘を Claude がコードで裏取り)。同タスクの closure 内で
  訂正したものと、closure 外として残すものを分ける。

  | 箇所 | 記述 | 実コード | 扱い |
  |---|---|---|---|
  | `MODULE-orchestrator-session`「呼び出され方」 | 引数 `cname`(文字列・必須) | `NewSessionManager()` は**引数を取らない**(`orchestrator/session.go:50`。`COMPOSE_PROJECT_NAME` → ホスト名の順に読む) | **`task-impl-depth` で訂正した**(置換後の「処理の流れ」と正面から矛盾していたため) |
  | `MODULE-orchestrator-term`「戻り値・副作用」 | `selectMenu` は選択されたインデックス | `func selectMenu(...) string` — **項目の `Value`(文字列)**(`orchestrator/term.go:96`) | **`task-impl-depth` で訂正した**(同上) |
  | `MODULE-orchestrator-review`「呼び出され方」 | 引数は `task` と `ctx` の2つ | `RunGate(ctx context.Context, p *Plan, t *Task)` — **`p *Plan` が抜けている**(`orchestrator/review.go:179`) | **本 issue に残す**((b) と同種の引数漏れだが、置換後の節と矛盾はしていない) |
  | `MODULE-orchestrator-mode`「呼び出され方」 | 引数は `key` / `sys` / `prompt` | `WriteLaunchScript(key string, prof ModelProfile, sysPrompt, prompt string)` — **`prof ModelProfile` が抜けている**(`orchestrator/mode.go:116`) | **本 issue に残す**(同上) |
  | `MODULE-cli-logout`「処理の流れ」 | 「**稼働中**の Claude コンテナ…を `MODULE-cli-common-container-exists` で存在を確認してから消す」 | `docker ps -a --filter ancestor=…` なので**停止中も含む**。`container_exists` を通すのは docker-proxy だけ(`claude-dev:638`〜`:642`) | **本 issue に残す**(シグネチャではなく手順の記述誤りだが、同じ「本文が実装とずれる」類型) |

  したがって **`issue 009` は (a) の規約と、上表の「本issueに残す」3件を抱えて開いたままである**。
