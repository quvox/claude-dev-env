---
id: 011-modify-taskid-is-not-validated-before-path-join
type: modify
severity: 中
found: 2026-08-03
found_in: task-impl-depth のドライラン パス2(コード精読。issue 004 の観点「入力検証と境界値」)
related: MODULE-orchestrator-worktree, MODULE-orchestrator-state-io, CTR-orchestrator-prompt, NFR-sec-01
summary: taskID を検証せずにパス結合しているため、`..` を含むタスクIDが運用状態ディレクトリの外を指しうる
---

# 011 taskID を検証せずにパスへ結合している

## 事象

`Store` はタスクIDをそのままパス要素として使う。

| 関数 | 組み立てるパス | 位置 |
|---|---|---|
| `WorktreeRel(taskID)` | `.orchestrator/worktrees/<taskID>` | `orchestrator/state.go:572` |
| `WorktreeAbs(taskID)` | `<workspace>/.orchestrator/worktrees/<taskID>` | `orchestrator/state.go:577` |
| `WorkerLogPath(taskID)` | `<workspace>/.orchestrator/workers/<taskID>.log` | `orchestrator/state.go:539` |

**taskID の許容文字・長さ・形式を検証する箇所がコード上に無い。** `filepath.Join` は結果を
`Clean` するので、`taskID` が `../../x` であれば `<workspace>/x` を指す。git worktree の作成先と
worker のログ出力先が運用状態ディレクトリの外へ出る。

taskID の供給元は `plan.json` の各タスクの `id` で、これは**ブレインストーミングモードの対話 Claude
(LLM)が生成した内容**である。人間が直接入力する経路ではないが、機械が検証していない値である点は
変わらない。

再現手順: `.orchestrator/plan.json` のタスク `id` に `../escaped` を書いて `orchestrate` を実行し、
`<workspace>/escaped` に worktree が作られることを確認する。

## 影響

- 想定外の場所に git worktree とログファイルが作られる。`/workspace` の外へは出ない
  (コンテナの隔離境界は破れない)が、利用者のリポジトリ内の任意のパスは指しうる。
- 既存ファイルを上書きしうる(`WorkerLogPath` は `os.OpenFile` の追記なので破壊は限定的だが、
  worktree の作成は空でないディレクトリでは失敗する)。
- severity を「中」とした根拠: 供給元が外部の攻撃者ではなく同一コンテナ内の LLM であり、
  隔離境界(コンテナ / ホスト間)は破れない。一方で `NFR-sec-01`(隔離と最小権限)の観点では
  「検証していない値をパスに使っている」こと自体が指摘に値する。

## 原因の見当

taskID を「機械が作る安全な値」とみなしたためと推測する(コードにその旨のコメントは無い)。
plan は LLM が生成するので、この前提は成り立っていない。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| taskID の形式 | 制約なし | `CTR-orchestrator-prompt` は plan の各タスクの `id` の型・値域を定めていない(issue 008 が指摘した契約の深度不足そのもの) | **契約の欠落**。実装が正なのではなく、**どちらも決めていない** |

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | `CTR-orchestrator-prompt` で taskID の形式を定義し(例: `[A-Za-z0-9_-]{1,64}`)、`Store` の各パス組み立ての手前で検証して不正なら失敗させる | 02/03 の契約各1、`orchestrator/state.go` に検証関数1つ、plan 読み込み時の検証1箇所 |
| B | パス結合の直前に `filepath.Base(taskID)` を通してディレクトリ成分を落とす | 3箇所。安全だが、衝突する taskID を黙って同一視する |
| C | 現状維持し、「taskID は検証していない」と 03 に明記する | ドキュメントのみ(本タスクで実施済み) |

推奨は **A**(契約の欠落を埋めるのが本筋で、issue 008 の対処と同じ方向)。
ただし**コードの変更を伴うため本タスクでは扱わない**。本タスクでは C として事実を記述した。

## 関連

- `docs/issues/004-modify-03-impl-lacks-reimplementation-depth.md` の観点「入力検証と境界値」
- `issue 008`(**2026-08-04 に解消して削除。経緯は `docs/histories/2026-08-04-impl-depth.md`**)(契約の深度)
