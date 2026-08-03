---
target: docs/03-impl/relations/MODULE-orchestrator-mode.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-orchestrator-mode
module: MOD-orchestrator
kind: function-call
sync: sync
impl: orchestrator/mode.go::Mode.RunInteractive, orchestrator/mode.go::Mode.BrainstormingArgs, orchestrator/mode.go::Mode.ResolveArgs, orchestrator/mode.go::Mode.ResolveArgsOne, orchestrator/mode.go::Mode.IntervenePrompt, orchestrator/mode.go::Mode.WriteLaunchScript, orchestrator/mode.go::Mode.brainstormingInstr, orchestrator/mode.go::Mode.interveneInstr, orchestrator/mode.go::Mode.instructionPath, orchestrator/mode.go::readFileOr, orchestrator/mode.go::shellSingleQuote
callers: MODULE-orchestrator-controller, MODULE-orchestrator-session
callees: MODULE-orchestrator-claude-exec, MODULE-orchestrator-state, MODULE-orchestrator-state-intervention, MODULE-orchestrator-state-io, MODULE-orchestrator-term
contracts: CTR-orchestrator-prompt
design: DSN-mod-01, DSN-orch-01
requirements: FR-orch-01, FR-orch-04
tests: orchestrator/mode_test.go::TestWriteLaunchScript, orchestrator/mode_test.go::TestWriteLaunchScript_NoPromptOmitsPositional, orchestrator/mode_test.go::TestShellSingleQuote, orchestrator/policy_test.go::TestModeArgs_IncludesPolicy
updated: 2026-08-02
summary: 対話モードの起動引数・指示テンプレート・起動スクリプトを決める
---

# MODULE-orchestrator-mode 対話モードの起動と指示注入

## 目的

2モード(ブレインストーミング / 実行)のうち、人間と対話する側の claude をどう起動するかを
決める(FR-orch-01)。介入時の質問文の組み立て(FR-orch-04)もここが行う。契約
`CTR-orchestrator-prompt` のプロンプト注入部分の実装である。

## 処理の流れ

1. `instructionPath(name)` が指示テンプレート(`instructions/brainstorming.md` /
   `instructions/intervene.md`。イメージ同梱)の位置を解決し、`readFileOr` が読み込む。
   `brainstormingInstr` / `interveneInstr` がそれぞれの本文を返す。
2. `BrainstormingArgs()` がブレインストーミング用の `claude` 引数を組み立てる。
   `handoff_note.md` があれば先頭に前置し、消費後に削除する。
   `--append-system-prompt` で指示テンプレートを渡し、`--model` / `--effort` は
   `brainstormingProfile`(opus / high)を使う。
3. `ResolveArgs()` / `ResolveArgsOne()` が介入解決用の引数を組み立てる。
   `MODULE-orchestrator-state-intervention` の `ReadQuestion` で質問文を読み、
   `MODULE-orchestrator-state` の `LoadProjectPolicy`(`ORCHESTRATOR.md`)と `VMModePreamble` を
   プロンプト先頭へ前置する。
4. `IntervenePrompt()` が介入1件のプロンプト本文を返す。
5. `WriteLaunchScript(key, sys, prompt)` が `.orchestrator/sessions/<key>.sh` に launcher を生成する。
   中身は VM env の source、`claude` の PATH 解決(`MODULE-orchestrator-claude-exec` の
   `claudePath`)、`SLACK_BOT_TOKEN` の除去、workspace への `cd`、巨大なプロンプトを
   `.sys` / `.prompt` サイドカーから `$(cat)` で読む形。書き込みは
   `MODULE-orchestrator-state-io` の `writeAtomic` を通す。
6. `RunInteractive(ctx)` は tmux が無いときの前景フォールバック。子プロセスの終了までブロックし、
   戻ったら `MODULE-orchestrator-term` の `ttyRestoreSane` で端末を戻す。
7. `shellSingleQuote(s)` がシェル引数を安全にクォートする(`MODULE-orchestrator-session` も使う)。

## 呼び出され方

- 契機: controller がブレインストーミングを始めるとき、介入を解決するとき、
  session が対話 claude を起動するとき。
- 前提条件: 指示テンプレートがイメージに同梱されていること(`--instructions` で上書き可能)。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `key` | 文字列 | `WriteLaunchScript` で必須 | スクリプト名。`sessions/<key>.sh` |
| `sys` | 文字列 | 任意 | `--append-system-prompt` へ渡す内容 |
| `prompt` | 文字列 | 任意 | 位置引数のプロンプト。空なら位置引数を省く |

- 認可: プロセス内呼び出し。

## 連携先と連携内容

### MODULE-orchestrator-claude-exec

- 何のために呼ぶか: launch script と前景実行で使う `claude` の絶対パス(`claudePath`)と
  子プロセス環境(`claudeChildEnv`)を得るため。
- 何を渡すか: なし。 / 何を受け取るか: 実行ファイルのパスと環境変数の並び。
- **失敗したときどうなるか**: `claude` が見つからなければ起動時に「実行ファイルが無い」で失敗し、
  対話が始まらない。

### MODULE-orchestrator-state

- 何のために呼ぶか: `ORCHESTRATOR.md`(`LoadProjectPolicy`)と VM 前置文(`VMModePreamble`)を
  プロンプト先頭に置くため、および `Store.path` でスクリプトの置き場所を決めるため。
- 何を渡すか: workspace 相対のパス要素。 / 何を受け取るか: 前置文とパス。
- **失敗したときどうなるか**: `ORCHESTRATOR.md` が無ければ前置なしで続行する(正常系)。

### MODULE-orchestrator-state-intervention

- 何のために呼ぶか: 介入の質問文(`ReadQuestion`)を読むため。
- 何を渡すか: 介入 ID。 / 何を受け取るか: 質問の本文。
- **失敗したときどうなるか**: 空文字が返り、質問の無いプロンプトになる(人間には文脈が伝わらない)。

### MODULE-orchestrator-state-io

- 何のために呼ぶか: launch script を `writeAtomic` で書き出すため。
- 何を渡すか: パスとスクリプト本文。 / 何を受け取るか: エラー。
- **失敗したときどうなるか**: スクリプトが作られず、tmux でのウィンドウ起動が失敗する。

### MODULE-orchestrator-term

- 何のために呼ぶか: 前景フォールバックから戻ったときに端末をカノニカルモードへ戻すため。
- 何を渡すか: なし。 / 何を受け取るか: なし。
- **失敗したときどうなるか**: 端末が raw のまま残り、以降の行入力が読めなくなる。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | `claude` の引数配列、プロンプト文字列、生成した launch script のパス、エラー |
| 永続化 | `.orchestrator/sessions/<key>.sh` と、巨大プロンプト用の `.sys` / `.prompt` サイドカー。`handoff_note.md` は消費後に削除する |
| 発火するイベント | なし |
| ログ | なし |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 指示テンプレートが読めない | `readFileOr` が既定値(空)を返し、`--append-system-prompt` の内容が空になる | 対話は始まるが指示が効かない |
| プロンプトが極端に長い | `.sys` / `.prompt` サイドカーへ逃がし、スクリプト内で `$(cat)` して渡す | コマンドライン長の上限に当たらない |
| `handoff_note.md` の削除に失敗 | 次回のブレインストーミングにも前置されてしまう | 同じ差し戻し理由が二重に出る |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 指示は `--append-system-prompt` で渡し、テンプレートはイメージ同梱にする(プロジェクト側に置かない) | D0-orch-02 |
| 2 | model / effort は `models.go` のポリシー表から取る(設定では変えられない) | D0-orch-02 |
| 3 | launch script を介して起動する(VM env の source・PATH 補完・`SLACK_BOT_TOKEN` 除去を1か所にまとめるため) | D0-orch-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| `Mode.RunInteractive` の `cmd.Run()`(mode.go:51)が、静的解析では `Controller.Run` / `SessionManager.Run` への呼び出し候補として現れる | 実在しない候補辺が立つ。コードを読むと標準ライブラリの `*exec.Cmd.Run` であり、**棄却した** | なし |
