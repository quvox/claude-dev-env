---
id: 020-static-callgraph-is-blind-to-interface-dispatch
date: 2026-08-05
context: task-relations-code-sync のフェーズ3〜4(callgraph-check.py の指摘を1件ずつ裁定した過程)
summary: 静的コールグラフはインターフェース越しの呼び出しを見られない — 実装済みの機能に出る CG3「低(実装前)」は実装漏れではなく、CG4 の確度「候補」は `exec.Cmd.Run()` のような同名衝突である。どちらもツールの限界であって仕様の欠陥ではない
---

# 020 静的コールグラフはインターフェース越しの呼び出しを見られない

`callgraph-check.py` の指摘を額面どおり読むと**実装漏れがあるように見える**が、
実際には Go のインターフェース経由の呼び出しと同名メソッドの衝突で、いずれも
**コードは正しく、ドキュメントも正しい**というケースが2種類ある。
どちらも「指摘が出ていること自体は正常」なので、次回は**この2型を先に思い出してから**
コードを読むと早い。

## 型1: CG3「低(実装前)」 — インターフェース越しの呼び出しは辺が出ない

`MODULE-orchestrator-controller` の `callees` に `MODULE-orchestrator-slack` を足したところ、
`callgraph-check.py` が「宣言した連携が callgraph に無い(実装前)」と出した。**実装は存在する**。

```go
// orchestrator/worker.go:77
type Notifier interface{ Notify(text string) }
// orchestrator/controller.go:323 ほか6箇所
c.Notifier.Notify(...)          // ← 実体は slack.go:31 SlackNotifier.Notify
```

呼び出し側が見ているのは**インターフェースの型**なので、静的解析は実体へ辺を張れない。
`ClaudeRunner`(`worker.go:48`〜`:51`)⇄ `ExecClaude.RunPrompt`(`worker.go:350`)も同型で、
`worker → claude-exec` と `review → claude-exec` の2辺が同じ理由で出なかった。

**「実装前」というラベルに引きずられないこと。** ツールは「変更指示で宣言されたが辺が無い」
辺をそう呼ぶだけで、実装の有無は判定していない。

**対処**: 呼び出し位置を `path:line` で本文の「連携先と連携内容」に書く。
`check-relations.py` は `callees` に ID があるのに本文に対応する `### 節` が無いと WARN を出すので、
**その WARN を消す作業がそのまま根拠を書く作業になる**。

## 型2: CG4 の確度「候補」 — `Run` という名前は衝突しすぎる

`claude-exec` / `mode` / `session` / `term` → `controller` / `session` の**7辺**が候補として出た。
全件が `exec.Cmd.Run()` の呼び出しで、`Controller.Run` / `SessionManager.Run` と名前が衝突しただけ。

```go
// orchestrator/term.go:54
cmd := exec.Command("stty", args...); return cmd.Run() == nil
// orchestrator/session.go:119
return exec.CommandContext(ctx, "tmux", args...).Run()
```

`Run` / `Close` / `Get` のような標準ライブラリの短い動詞は候補辺を量産する。
**候補辺は「取りこぼすよりは出す」設計**(`docs/03-impl/feature-graph.md:27`)なので、
出ること自体は正常であり、`callees` に載せてはならない。

**対処**: 棄却してよいが、**棄却の理由をどこかに残す**(でないと次の実行が同じ調査をやり直す)。
今回は `/task-close` の histories に「7辺は `exec.Cmd.Run()` の同名衝突として棄却」と書いた。

## 見分け方(先に確かめる順)

1. 指摘された呼び出し元のシンボルを開き、**呼び出しの受け手が interface 型か**を見る
   → interface なら型1。実装は在る。
2. 呼び出しているメソッド名が `Run` / `Close` などの**汎用動詞**か
   → 標準ライブラリの同名メソッドを呼んでいないか見る。呼んでいれば型2。
3. どちらでもなければ、初めて**実装漏れ / 過剰主張**を疑う。

## なぜ間違えやすいか

`callgraph-check.py` の出力は「コードにある / 無い」と断定的に読めるが、
実際は **Tier とツールの解決能力の範囲での主張**である。ヘッダの
「未解決の呼び出しを持つシンボル: N 件 — この範囲では『経路が無い』と断定しない」は
まさにこの限界の宣言で、**先にここを読むと指摘の重みが変わる**。
限界そのものは `.claude/directions/callgraphs.md` §5 と `relations.md` §6 が持つ。

## 関連

- `docs/03-impl/relations/MODULE-orchestrator-controller.md`(連携先と連携内容 → MODULE-orchestrator-slack)
- `docs/03-impl/feature-graph.md`(候補辺の定義)
- [[016-tracking-is-not-adjudication]]
