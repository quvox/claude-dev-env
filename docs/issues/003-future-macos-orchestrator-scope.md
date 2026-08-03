---
id: 003-future-macos-orchestrator-scope
type: future
severity: 中
found: 2026-07-31
found_in: 2026-07-31 の独立監査(cli-mac の orchestrate 実装と 02-design の契約の突き合わせ)
related: MODULE-cli-orchestrate, CTR-cli-orchestrator, FR-orch-02, FR-env-10
summary: macOS 版 orchestrate が生存判定・attach/resume を実装しておらず契約と食い違ったままになっている
---

# 003 macOS 版 `orchestrate` に生存判定・attach/resume が無い

## 事象

`claude-dev-mac` の `orchestrate` は、Linux 版(`claude-dev`)と実装が異なる。

| 観点 | Linux 版 | macOS 版 |
|---|---|---|
| 未起動時 | `CLAUDE_DEV_NO_ATTACH=1 start` で自動起動する | 「`claude-dev start` を先に実行」と表示して `exit 1` |
| コントローラの生存判定 | `pgrep -f "claude-orchestrator --workspace"` で判定し attach / resume を分ける | **判定しない**。毎回新規に起動する |
| セッション | `orch-<project>-main` を `new-session -d` で作る | 既存の `main` に `new-window` を足して attach する |
| VM env の読み込み | `/etc/claude-dev/vm.env` を source する | しない(VM モード非対応) |

## 影響

契約 `CTR-cli-orchestrator` が定める「生存判定による attach / resume 分岐」が macOS では成立せず、
実行中の run に再接続したいときも新しいウィンドウで `claude-orchestrator` がもう1つ起動しうる。
FR-orch-02 が定めるコントローラ常駐の前提が macOS では満たされない。
運用は `claude-dev attach` で `main` セッションへ入り直すことでしのいでいる。

要件 FR-env-10(macOS 対応)は VM / KVM のみを非対応と宣言しており、オーケストレーターの扱いには
触れていないため、**要件と実装の間にギャップが残っている**。

## 原因の見当

macOS 対応を「Linux 版との差分を最小に保つ」方針で進めた際、`orchestrate` の常駐まわりが
移植対象から外れたと考えられる(**推測**)。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| macOS での attach / resume | 実装していない | `CTR-cli-orchestrator` は生存判定による分岐を定め、FR-env-10 は VM/KVM のみを非対応としている | **要件・設計が正**。ただし対応時期は人間判断で先送り済み |

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | macOS 版に Linux 版と同じ生存判定・専用セッション・resume を移植する | `MODULE-cli-orchestrate`(`claude-dev-mac` 側)・`CTR-cli-orchestrator` の検証 |
| B | FR-env-10 に「オーケストレーターの常駐は macOS 非対応」と明記して要件側を実装に合わせる | `01-requirements/functional.md`・`02-design/contracts/` |

## 経緯

- 2026-07-31 独立監査で検出。**人間判断: 「macOS のオーケストレーター対応は後日あらためて開発する。それまで現状のまま放置する」**。旧 `docs/tasks/macos-orchestrator-scope.md` として管理していた。
- 2026-08-02 task-docs-restructure の決定シート(論点2 = A)により、旧形式タスクを issue へ降格して本ファイルにした。
