---
id: 014-modify-append-logs-lack-required-fields
type: modify
severity: 中
found: 2026-08-03
found_in: task-impl-depth のドライラン パス2(コード精読。issue 004 の観点5「ログ・可観測性」)
related: MODULE-orchestrator-state-intervention, MODULE-orchestrator-controller, docs/02-design/logging.md
summary: 追記型ログ3本が 02-design/logging.md の必須フィールド(event / task_id / attempt)を満たしておらず、行の形式もファイルごとに違う
---

# 014 追記型ログが必須フィールドを満たしていない

## 事象

`docs/02-design/logging.md`「必須フィールド」は、追記型ログ(JSON Lines)に
**`ts` / `event` / `task_id` / `attempt` / `detail`** を求めている。実装の3本を突き合わせると
次のとおり食い違う。

| ファイル | 行の型 | `ts` | `event` | `task_id` | `attempt` | `detail` |
|---|---|---|---|---|---|---|
| `audit.jsonl` | `AuditEntry`(`state.go:217`) | あり | あり | あり(**run 単位のイベントでは空文字**) | **無い**(`dispatch` だけ `detail.attempt` に入る) | あり(任意) |
| `assumptions.jsonl` | `Assumption`(`state.go:185`) | あり | **無い** | あり | **無い** | 無い(`description` / `rationale`) |
| `interventions.jsonl` | `Intervention`(`state.go:194`) | あり | **無い** | あり | **無い** | 無い(`trigger_reason` / `question` / `answer`) |

再現手順:

1. orchestrator を1 run 実行する。
2. `.orchestrator/audit.jsonl` / `assumptions.jsonl` / `interventions.jsonl` を開く。
3. どの行にも `attempt` が無く、後者2本には `event` が無いことを確認する。

なお**秘密情報の混入は確認されなかった**: トークンは子プロセスの環境から除去され
(`claudebin.go::claudeChildEnv`)、Slack のエラーログにもトークンは出ない。worker の生出力は
`workers/<taskID>.log` にのみ残り、追記型ログには要約だけが入る。

## 影響

- **`attempt` が無いため、何回目の試行で何が起きたかを追記型ログだけから復元できない。**
  `NFR-ops-01`(実行の経過を後から追える)の根拠が弱い。
- 3本のスキーマが揃っていないので、**1つの読み取り側で横断的に処理できない**。
- `logging.md` を仕様として信じて解析ツールを書くと動かない(`03-impl` が
  「ドキュメントだけから再実装・再試験できる」という目的に反する)。

severity を「中」とした根拠: 実行の正しさには影響せず、`dispatch` イベントには
`detail.attempt` があるため主要な追跡は可能。ただし設計が定めた必須フィールドを満たしていない
状態が明文化されないまま残っている。

## 原因の見当

推測: `logging.md` は3系統のログを整理した時点で「追記型ログ」を1つの理想形として定義したが、
実装側は用途ごとに別の構造体(`AuditEntry` / `Assumption` / `Intervention`)を先に持っており、
両者を突き合わせる機会が無かった。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| 追記型ログの共通フィールド | 3本でバラバラ。`attempt` はどこにも無い | `logging.md`「必須フィールド」で5項目を要求 | **要確認**(実装を揃えるのか、設計を実態へ寄せて `attempt` の要求を `detail` 経由に緩めるのか) |

**この判断は要件・設計の意味を変えるため、勝手に決めない。**

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | 3本に `event` と `attempt` を持たせて `logging.md` に揃える | `orchestrator/state.go` の3構造体と全呼び出し箇所、`MODULE-orchestrator-state-intervention`、`tests/orchestrator.md` |
| B | `logging.md` を実態に合わせ、「共通は `ts` / `task_id`、それ以外はファイルごと」と定義し直す | `02-design/logging.md` と `03-impl` の該当記述 |
| C | 監査ログ(`audit.jsonl`)だけを必須フィールドの対象と定義し、他2本は派生ログとして別枠にする | B と同規模 |

推奨は **A**(設計が求める可観測性を実装が満たす方向)。ただし追記型ログの読み手は現状 human と
`history/` の保全だけなので、**B / C を選ぶ判断もありうる**。

## 経緯

- 2026-08-03 起票。`task-impl-depth` のフェーズ2で 02 の `logging.md` と 03 の実態を
  突き合わせて発見(決定シート論点3 の合意「03 に現状を書き、02 との差は issue 起票」に従う)。
  **本タスクではコードも 02 も変更しない。**

## 裁定の記録(2026-08-04)

**人間の裁定: 先送り(次タスクへ)。案A(実装を設計に合わせる)を推奨として添えた。**
`task-impl-depth` の質問キュー #2「`issue 014` の正はどちらか」に対する回答である。

- 本タスク(`task-impl-depth`)では**コードも 02 も変更しない**。03 に実態を書き、
  `03-impl/index.md`「02 との差分」に「**正がどちらかは要確認**」として残す。
- したがってこの差分は「人間が判定済み(判定の内容は『この タスクでは決めず次タスクへ送る』)」
  であり、未裁定のまま放置されているものではない。
- 記録先をこの issue にした理由: 判断の経緯がタスクの `memo.md` にしか無いと、
  `/task-close` が memo.md を削除した時点で「誰がいつ先送りを決めたか」が失われる。

★2026-08-04 `/doc-check task-impl-depth` が「人間の裁定が memo.md にしか無い」ことを検出して追記した。
