---
slug: macos-orchestrator-scope
layer: task
title: macOS でオーケストレーターの常駐・復旧が成立しない件の要件上の扱いを決める
date: 2026-07-31
updated: 2026-07-31
phase: 決定
source:
  - docs/01-requirements/orchestration.md
  - docs/03-impl/cli-mac.md
history: []
---

# タスク:macOS のオーケストレーター対応範囲を決める

## 目的

`claude-dev-mac` の `orchestrate` が、要件 orchestration/13-2 が定める常駐・復旧を実装していない。
要件と実装のどちらを正にするかを決め、層をそろえる。

## 何が食い違っているか（2026-07-31 の独立監査で検出）

| | 内容 |
|---|---|
| 要件 orchestration/13-2 | 「コントローラを tmux セッション `orch-<project>-main` の `dashboard` ウィンドウで常駐させ、worker/ブレインストーミングを同セッションの独立ウィンドウとして管理しなければならない」（プラットフォーム条件なし） |
| 02-design 契約 | `cli(orchestrate)→orchestrator` は「生存判定による attach/resume 分岐」を定める |
| 要件 core/10（macOS） | 非対応と宣言しているのは **VM/KVM のみ**。オーケストレーターには触れていない |
| `claude-dev-mac` の実装 | 未起動なら `exit 1`（自動起動しない）／生存判定なし／resume なし／`orch-<project>-main` を作らず既存 `main` セッションに `tmux new-window` して attach |

つまり **macOS は現状 orchestration/13-2 を満たしていない**。`03-impl/cli-mac.md` には
（利用者判断「実装にあわせて」に基づき）実装どおりの記述と既知の制限を書いたが、要件側が未調整のため
`cli-mac.md` は合格証を出せない状態（C8: 未解決事項が残っている）。

## 選択肢（フェーズ1 の決定シートで確定する）

| 案 | 内容 | 影響 |
|---|---|---|
| A | 要件を実装に合わせる。core/10 に「macOS ではオーケストレーターの常駐・復旧を非対応とする」を追加し、orchestration/13 に WHERE 条件を入れる | 00（decisions）起点。01/02/03 へ下降。コード変更なし |
| B | 実装を要件に合わせる。`claude-dev-mac` に生存判定・専用セッション・resume を実装する | コード変更あり。macOS 実機での検証が必要（現状その環境が無い） |
| C | 当面ギャップとして明示保持し、`cli-mac.md` の合格証は出さないまま運用する | 何も変えないが、検証状態が恒久的に不合格のまま残る |

## 未決点

| # | 未決点 | 帰着 | 状態 |
|---|---|---|---|
| 1 | 上表の A / B / C のどれを採るか（macOS でオーケストレーターを正式サポートするのか） | 人間判断（フェーズ1 の決定シート） | 未closure |
| 2 | A を採る場合、macOS で `orchestrate` を実行したときの期待挙動（現状の簡易版を仕様として認めるのか、明示的に拒否するのか） | 同上 | 未closure |

## 質問キュー

なし（未決点はフェーズ1 の決定シートで一括提示する）

## Definition of Done

- [ ] 要件と実装のどちらを正にするかが決まり、00〜03 が一貫している
- [ ] `docs/03-impl/cli-mac.md` の「既知の制限」から未決の記述が消え、`/doc-check` で PASS する
- [ ] 本作業の 質問/修正/委任判断 が `docs/feedback/log.md` に記録されている

## 進捗メモ

- 2026-07-31: `/implement` の後始末中に独立監査が検出。`cli-mac.md` を実装に合わせて同期した時点で
  要件との齟齬が顕在化したため起票。未着手。**次は `/change` でフェーズ1 を回す。**
