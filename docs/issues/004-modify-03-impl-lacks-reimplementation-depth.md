---
id: 004-modify-03-impl-lacks-reimplementation-depth
type: modify
severity: 中
found: 2026-08-03
found_in: task-docs-restructure の /doc-check(Claude 自身の実装ドライラン パス1。独立レンズの指摘ではない)
related: MODULE-cli-start, MODULE-cli-forward, MODULE-orchestrator-controller, MODULE-orchestrator-state-io, CTR-cli-container, CTR-cli-orchestrator, CTR-orchestrator-prompt
summary: 03-impl が「現状の説明」としては正しいが、ドキュメントだけから再実装・再試験できる深度に達していない領域が約20件ある
---

# 004 03-impl に「ドキュメントだけから再実装・再試験できる」深度が無い領域がある

## 事象

`task-docs-restructure` の `/doc-check` で実装ドライラン パス1(ドキュメントだけを読み、
「決めないと実装を進められない点」を洗い出す)を行ったところ、**記述の深度が足りない**領域が
次の観点に集中していることが分かった。

<!-- 出所の訂正(2026-08-03): この issue は当初「独立レンズ(Codex readiness 3本)が高14件を含む
     29件を報告した」と書いていたが、それは事実ではない。実際に走った Codex readiness 2本の指摘は
     反映手順に関する11件で、下記の深度不足は含まれていない。下記は Claude 自身がドキュメントを
     読んで洗い出したものである。件数「約20件」も概算であり、レンズが数えた値ではない。 -->

| 観点 | 代表例 | 該当 |
|---|---|---|
| 入力検証と境界値 | `claude-dev forward <cport>` の `<cport>` が「整数」としか定義されず、0・負数・65536 以上・空・非数値・先頭ゼロの受理/拒否とメッセージが無い。`taskID` の許容文字・長さ・パストラバーサルも同様 | `MODULE-cli-forward` / `MODULE-cli-unforward` / `MODULE-orchestrator-worktree` |
| 永続化とトランザクション境界 | `start` の「認証コピー → 設定抽出 → hook コピー → `.gitignore` 追記 → Docker 資源作成」で、途中失敗時にどこまで残すか・再実行がどこから安全に回復するかの一貫性境界が無い。orchestrator も plan/state・git merge・複数の JSONL 追記を横断する境界と復旧順序が未定義 | `MODULE-cli-start` / `MODULE-orchestrator-state-io` / `MODULE-orchestrator-controller` |
| 並行性と順序 | 同時 `start` / `forward` / `reset` / `logout` の排他単位と許容結果が未定義。`forward` は競合時のリトライが無い。orchestrator は worker 完了・TUI 操作・tick・シグナルが同時に来たときの排他と重複イベントの冪等性が未記載 | `MODULE-cli-*` / `MODULE-orchestrator-controller` |
| 外部依存の失敗時の挙動 | Docker / GHCR / Slack / Claude CLI の失敗が「非0で停止」「握りつぶす」までで、認証失敗・タグ不存在・レート制限・通信断・部分取得の区別、タイムアウト・再試行回数・バックオフが無い | `infra/local/ghcr.md` / `MODULE-orchestrator-slack` / `MODULE-orchestrator-claude-exec` |
| ログ・可観測性 | 出力先が機能ごとに断片的で、レベル・時刻・run/task 識別子といった必須フィールドと、秘密値のマスキング方針が定義されていない | 03-impl 全般 |
| テストデータの準備と後始末 | 多くの機能が「自動テストランナーが無く実機確認で代替」とするだけで、実機確認の確認項目・初期状態・作成資源・失敗注入・cleanup の責任者・残存確認が無い | `03-impl/tests/` 全般 |
| 契約の型 | `CTR-orchestrator-prompt` の「必要な文脈」「構造化された結果」がフィールド単位で定義されておらず、必須性・型・列挙値・欠落時の判定を導出できない | `contracts/orchestrator-prompt.md` |

## なぜ本タスクで直さないか

`task-docs-restructure` は**ドキュメント体系の移設**であり、「やらないこと」に
**コードの変更**と**仕様そのものの変更(振る舞い・受け入れ基準の意味を変えない)**を掲げている。
上記を埋めるには、実装を読んで現在の振る舞いを新たに文書化する作業(観点によっては
「決まっていないことを決める」作業)が必要で、移設の範囲を超える。

また、この指摘は「**ドキュメントだけを読んで製品全体を再実装できるか**」という基準で出ている。
本タスクのフェーズ3は実装ではなく SSOT への反映であり、反映の実行可能性は別途担保されている
(memo のタスクリスト7 の手順)。したがって本タスクの完了はブロックしない。

## 影響

- 現状の把握には支障がない(03-impl はコードの合わせ鏡として `check-relations.py` /
  `callgraph-check.py` / `relations-coverage.py` に合格している)。
- 効いてくるのは**この領域を変更するタスクが立ったとき**である。境界値・異常系・並行性が
  書かれていないと、`/implement` が未決点ゼロの入場条件を満たせず、その時点で調査が発生する。

## どうしたいか

領域ごとに小さなタスクへ分割して埋める。優先度は次の順を推奨する。

1. **並行性と永続化の境界**(`MODULE-cli-start` / `MODULE-orchestrator-state-io`)— 事故が起きたときの
   影響が最も大きく、実測しないと分からない事実を含む。
2. **入力検証と境界値**(`MODULE-cli-forward` / `MODULE-orchestrator-worktree`)— コードを読めば
   一意に決まるので安価。パストラバーサルはセキュリティに直結する。
3. **外部依存の失敗時の挙動**と**ログ・可観測性** — 運用に効く。
4. **契約の型**(`CTR-orchestrator-prompt`)。

`03-impl/tests/` の「実機確認の手順化」は `docs/pendings.md` の QA レーン(P-003)と同時に扱うのが
効率的である。

## 関連

- `docs/pendings.md` P-003(QA レーンの各設定が未定)
- 検出経緯は `task-docs-restructure` の memo.md「独立レンズの実際の結果」および
  「/doc-check(task モード)2026-08-03 — 追加の未決点と裁定」
