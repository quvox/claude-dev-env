---
id: 2026-08-05-doc-check-ssot-relations-code-sync-certification
date: 2026-08-05
task: task-relations-code-sync
origin_layer: 03
issue: docs/issues/038-modify-closure-relations-still-diverge-from-code.md
summary: /doc-check ssot の指摘を修正して合格証4件を発行した(反映の取りこぼし3件と、独立レンズが見つけた review.go 記述の乖離)
---

<!-- タスクごとに1ファイル。追記のみ(確定したエントリの文章は書き換えない)。
     タスク・進捗・TODO は書かない(それは memo.md の仕事だった)。 -->

# 2026-08-05 /doc-check ssot の指摘修正と合格証の発行(フェーズ4 §4)

## 変更理由

`/task-close task-relations-code-sync` のフェーズ4 §4 として `/doc-check ssot` を
新しい文脈(サブエージェント)で実行した。SSOT 反映(`464e2dc`)によって
**合格証が失効した文書が4件**あり、その再発行が目的である。

検証の過程で、**反映そのものの取りこぼし3件**と、
**独立レンズがコードと突き合わせて見つけた記述の乖離**が出たため、
合格証を出す前にすべて修正した。起点層はすべて **03**(記述の誤りであり、実装は正しい)。

## 変更内容の要約

- **反映の取りこぼし(3件)**。変更指示の `sections:` が `"## 呼び出され方"` と
  `"### MODULE-*"` を並べていたため、`### MODULE-*` の節が**呼び出され方の直下へ二重に挿入**され、
  本来の「連携先と連携内容」側の同じ節がそのまま残っていた
  (`MODULE-orchestrator-dashboard` の `### MODULE-orchestrator-session`、
  `MODULE-orchestrator-review` の `### MODULE-orchestrator-worker`。いずれも逐語で同一)。
  重複した側を削除した。
- **`callees` に足したのに節が無い(2件)**。`MODULE-orchestrator-worker` と
  `MODULE-orchestrator-review` は `callees` に `MODULE-orchestrator-claude-exec` を追加したが、
  「連携先と連携内容」に対応する節を持っていなかった
  (`.claude/directions/relations.md` §4「frontmatter に載っていて本節に無い callee は不完全な文書」)。
  コードで裏取りして節を書いた。
- **テスト表の集計の不整合(1件。独立レンズが重大度「高」で検出)**。
  `03-impl/tests/orchestrator.md`「未検証(テスト未実装)の全件」表は 47 行だが、
  状態セルが未検証である 47 行とは**集合が違っていた**(`CTR-cli-orchestrator` を落とし、
  状態が「実装済み」の `MODULE-orchestrator-main` を代わりに含んでいた)。
  行数が偶然一致していたため、これまでの検査をすり抜けていた。
  表の数える範囲を明記し、欠けていた行を足した。
- **`MODULE-orchestrator-review` の記述とコードの乖離(11 箇所)**。
  独立レンズに `orchestrator/review.go` 全 362 行を読ませたところ、
  エラー経路・カウンタの実体・引数の実値・行番号引用の誤りが連続して見つかった。
  すべてコードを正として直した(下表)。

## 更新したドキュメント

| ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|
| docs/02-design/contracts/orchestrator-prompt.md | 1.3.0(据え置き) | 本文は変えず**合格証を再発行**した(`against` を `system.md` 2.2.1 へ) |
| docs/03-impl/contracts/orchestrator-prompt.md | 1.1.0(据え置き) | 本文は変えず**合格証を再発行**した(`against` を 02 契約 1.2.0 → **1.3.0**)。忘れると `close-task.py` 条件b が落ちる箇所 |
| docs/03-impl/tests/orchestrator.md | 1.2.0 → **1.3.0** | 「全件」表の数える範囲を明記し `CTR-cli-orchestrator` の行を追加(47 行 + #38 の例外 = 48 行)。ファイル名だけだったテスト識別子2件を実在する関数名へ |
| docs/03-impl/index.md | 1.12.0 → **1.13.1** | 本文は変えず、**relations 層の代表として層の内容変更(下記3本)を版に反映**した(1.13.0 で認証したのち、最終監査の後に入れた行番号引用2件の訂正を PATCH として 1.13.1 に載せ替え、合格証も同版で出し直した) |
| docs/03-impl/relations/MODULE-orchestrator-review.md | (層として index.md が認証) | `error` が非 `nil` になるのは context キャンセルのときだけである事実、`formatErrs` がローカル変数であること、介入キューへ積むのは controller であること、再整形の不変性が保証されないこと、`{"findings":null}` がゲートを通過すること、レビュア起動引数の実際、行番号引用4件を訂正。`### MODULE-orchestrator-claude-exec` を追加 |
| docs/03-impl/relations/MODULE-orchestrator-worker.md | (同上) | `### MODULE-orchestrator-claude-exec` を追加。`PrepareWorktree` の戻り値が `error` だけで worktree のパスは `t.Worktree` への副作用で渡ることを明記 |
| docs/03-impl/relations/MODULE-orchestrator-dashboard.md | (同上) | 呼び出され方の直下に二重挿入されていた `### MODULE-orchestrator-session` を削除 |
| docs/issues/054-...md | — | `019`/`032`/`038` 削除後に残る参照を実測で更新(`decisions/orch.md:199` は**層 00**) |
| docs/issues/056-...md | — | 走査語彙に「旧実装」を追加(該当2箇所) |
| docs/issues/059-...md | — | **新規**。`FR-orch-06` 受入基準2 を覆うテストが実在しないのに「実装済み」である |

## 実装したもの

| 対象 | 内容 | コミット |
|---|---|---|
| — | **コードは1行も変えていない**(記述をコードへ合わせる作業のため) | — |

## 機能間連携仕様書の変化

| 種別 | ID | 内容 |
|---|---|---|
| 追加(節) | MODULE-orchestrator-worker | `### MODULE-orchestrator-claude-exec`(`ClaudeRunner` 越しの `RunPrompt` 呼び出し) |
| 追加(節) | MODULE-orchestrator-review | `### MODULE-orchestrator-claude-exec`(レビュア起動と再整形の2経路) |
| 削除(重複) | MODULE-orchestrator-dashboard | 呼び出され方の直下に重複していた `### MODULE-orchestrator-session` |
| 削除(重複) | MODULE-orchestrator-review | 呼び出され方の直下に重複していた `### MODULE-orchestrator-worker` |

`callers` / `callees` の集合そのものは変えていない(反映時のものを維持した)。

## 副産物

- **新しい issue**: `docs/issues/059`(`FR-orch-06` 受入基準2 に対応するテストが無い)。
- **既存 issue への追記**: `054`(削除予定 issue への参照の実測更新)/ `056`(語彙「旧実装」)。
- **独立レンズの記録**: Codex(`gpt-5.6-terra` / reasoning `max`)を5本走らせ、4本が成功した。
  **22 本の relations を一度に見る `relations` 監査は 900 秒でタイムアウトした**(終了コード 124)。
  これは 2026-08-05 のフェーズ2 と同じ失敗で、**対象を絞れば通る**ことも同じである。
- **気づき**: `MODULE-orchestrator-review` は独立レンズに**同じファイルを3回**読ませた各回で
  新しい乖離を出し続けた(6件 → 7件 → 収束)。1本の relations を「再実装可能な深度」で
  コードと突き合わせるには、**そのファイル1本だけを対象にした監査**が要る。
  22 本まとめた監査はタイムアウトするだけでなく、通っても深度が出ない。
