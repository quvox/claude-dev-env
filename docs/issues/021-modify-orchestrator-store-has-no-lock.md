---
id: 021-modify-orchestrator-store-has-no-lock
type: modify
severity: 中
found: 2026-08-03
found_in: task-impl-depth のフェーズ2(issue 004 の観点2・3。D0-scope-07 の起票の閾値に該当)
related: MODULE-orchestrator-state-io, MODULE-orchestrator-controller, FR-orch-05, FR-orch-02
summary: .orchestrator/ ストアにロックが無く、同一 workspace で2つ目のコントローラが起動すると plan.json が後勝ちで壊れる
---

# 021 orchestrator のストアにロックが無い

## 事象

`orchestrator/state.go` の永続化プリミティブは**ファイルロックを持たない**。
`writeAtomic` は一時ファイル → `os.Rename` で単一ファイルの置換を原子化するだけなので、
**別プロセスが同じ `plan.json` を書けば後勝ちで上書きされる**。ロック取得も PID ファイルも無い。

同一 workspace で2つ目のコントローラが起動する経路:

- **macOS**: `claude-dev orchestrate` に生存判定が無く、新しいウィンドウでもう1つ起動しうる
  (`docs/issues/003`)。
- **Linux**: CLI は `pgrep` 相当で生存判定するが、**コンテナの外や別セッションから
  `claude-orchestrator` を直接起動すれば検出されない**。orchestrator 自身は何も確認しない。

再現手順:

1. 同じ workspace に対して `claude-orchestrator` を2つ起動する(2つ目は CLI を経由しない)。
2. 双方が executing に入る状況を作る。
3. `.orchestrator/plan.json` のタスク状態が交互に上書きされ、完了済みタスクが `pending` に
   戻る・介入キューと plan が食い違うなどの不整合が起きることを確認する。

## 影響

`FR-orch-05`(中断・再開で完了済み作業をやり直さない)の前提が崩れる。
worker が並行して同じ worktree を触ることもありうる。**検出も警告も無いため利用者は気づけない。**

severity を「中」とした根拠: 通常経路(Linux + CLI)では生存判定が防ぐため発生条件が限られる。
一方で発生したときの被害は状態の破壊であり、`D0-scope-07` の起票の閾値 (a) に当たる。
`docs/issues/003` は macOS の二重起動を追跡しているが、**ストア側にロックが無いという事実は
どの issue も追跡していない**((b) を満たす)。

## 原因の見当

推測: 「コントローラは1つ」という前提を CLI 側の生存判定だけで担保し、ストア側では確認しない
構造になっている。`Store` は `NewStore` でディレクトリを作るだけで、占有の概念を持たない。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| ストアの占有 | ロックは無い(`MODULE-orchestrator-state-io` / `-controller` の「既知の制限」に事実として記述) | `FR-orch-02` は1セッション1コントローラを前提とするが、**二重起動を防ぐ責任がどこにあるか**を定めていない | **要確認**(ストア側でロックするか、CLI 側の生存判定だけを正とするか) |

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | `NewStore` で `.orchestrator/lock`(PID 入り)を排他作成し、既存かつプロセス生存なら起動を拒否する。異常終了で残った古いロックは PID 不在で無効化する | `orchestrator/state.go` / `main.go`、`MODULE-orchestrator-state-io`、`FR-orch-02` の受入基準 |
| B | 起動時に警告だけ出す(既存ロックがあれば「二重起動の可能性」を表示して続行) | 同上(受入基準の変更は不要) |
| C | 現状を仕様として確定させ、「二重起動の防止は CLI の責任」と 02 に明記する | ドキュメントのみ(`02-design/system.md` と `CTR-cli-orchestrator`) |

推奨は **A**(状態の破壊は回復が難しく、ロックの実装コストが小さい)。

## 経緯

- 2026-08-03 起票。`task-impl-depth` のフェーズ2で `MODULE-orchestrator-state-io` /
  `-controller` の並行性を書き下ろす際に確定。**本タスクではコードを変更しない。**
