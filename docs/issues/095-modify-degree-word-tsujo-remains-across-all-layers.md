---
id: 095-modify-degree-word-tsujo-remains-across-all-layers
type: modify
origin_layer: 02
severity: 低
found: 2026-08-08
found_in: /doc-check task-layer-placement(独立レビュー(サブエージェント)の C 指摘を裁定し、check-changeset.py --ssot で全件を数えて確定)
related: docs/02-design/contracts/cli-container.md, docs/02-design/contracts/orchestrator-prompt.md, docs/02-design/system.md, docs/00-requests/decisions/scope.md, docs/03-impl/relations/
pattern: CLAUDE.md §8 が禁じる程度語「通常」が仕様ドキュメントに残る
pattern_survey: "python3 .claude/scripts/check-changeset.py --ssot docs の CS8。**task-layer-placement の SSOT 反映後(2026-08-08)に数え直して 24 箇所**(00: 1 / 01: 0 / 02: 4 / 03: 19)。起票時点(反映前)は 34 箇所(00: 4 / 01: 2 / 02: 5 / 03: 23)だった"
summary: 程度語「通常」が 24 箇所に残る。CS8 は全件を検出しているが、母集団を誰が減らすかの担い手が決まっていない
---

# 095 程度語「通常」が 24 箇所に残る

## 事象

CLAUDE.md §8 は「**程度語も曖昧語である**」として「ほぼ」「長めに」「十分に」などを禁じており、
`check-changeset.py --ssot` の `CS8` はこれを検出する。2026-08-08 の `task-layer-placement` の
SSOT 反映後に数え直した時点で「通常」は **24 箇所**ある(起票時点は 34 箇所)。
「通常」は「何と比べて通常なのか」を伴わないため、読み手ごとに指す集合が変わる
(例: `CTR-cli-container:131`「本体コンテナの削除・`fwd-*` の片付け・遊休判定は**通常どおり**行う」は、
どの節の定めに従うのかがこの行から決まらない)。

**CS8 は全件を検出できている。** 欠けているのは検査ではなく、母集団を誰がいつ減らすかの担い手である
(`docs/issues/031` は `environments.md` の「未定」1 件、`docs/issues/056` は変更相対語という**別の型**を
追跡しており、程度語「通常」を追跡する issue はこれまで無かった)。

## 同型の全件(24 箇所。**2026-08-08 の SSOT 反映後に数え直した値**)

```bash
python3 .claude/scripts/check-changeset.py --ssot docs 2>&1 | grep '曖昧語「通常」'
```

| 層 | 件数 | 箇所 |
|---|---|---|
| 00 | 1 | `docs/00-requests/decisions/scope.md:131` |
| 01 | 0 | (なし) |
| 02 | 4 | `docs/02-design/contracts/cli-container.md:121`・`:131` / `docs/02-design/contracts/orchestrator-prompt.md:134`・`:135` |
| 03 | 19 | `MODULE-cli-logout.md:93`・`:215` / `MODULE-cli-start.md:120`・`:321` / `MODULE-cli-stop.md:79`・`:185`・`:226` / `MODULE-cli-unforward.md:49` / `MODULE-docker-proxy-serve.md:152` / `MODULE-orchestrator-claude-exec.md:89`・`:101` / `MODULE-orchestrator-main.md:42` / `MODULE-orchestrator-slack.md:76` / `MODULE-orchestrator-state-io.md:42` / `MODULE-orchestrator-state.md:84` / `MODULE-orchestrator-streamlog.md:57` / `MODULE-orchestrator-worker.md:145` / `MODULE-orchestrator-worktree.md:46`・`:78`(いずれも `docs/03-impl/relations/` 配下) |

**起票時点(反映前)は 34 箇所で、`task-layer-placement`(2026-08-07〜08)が 10 箇所を同じ下降の中で
消した**: `acceptances.md:55` / `decisions/sec.md:153`・`:156` / `usecases.md:114`・`:198` /
`system.md:456`(→「`CTR-docker-api` が拒否条件と定めない要求の透過」)/ `MODULE-cli-logout.md:231` /
`docs/03-impl/tests/e2e.md` の 3 箇所。**この 10 箇所は下の「どう直すか」の書き替え方の実例である。**

## なぜ今すぐ全件を直さないか

`.claude/directions/layer-fit.md` §3 が「全部を『高』にすると 1 回の検証で終わらない量になり、
結果として誰も直さない」と定めるとおり、24 箇所は 1 タスクの範囲を超える。
**03 の 23 箇所は `/task-close` の relations 再生成で書き直される可能性がある**ため、
02 以上を先に片づけるのが安い。起点層を 02 としたのはそのためである。

## どう直すか

- 「通常」を、**その行が指している定めへの指し先**に置き換える。文言の言い換え(「一般に」など)では
  同じ欠陥が残る。
- 例: `CTR-cli-container:131`「通常どおり行う」→「**本節の他の行が定めるとおりに行う**(compose 資源の
  削除だけを行わない)」/ `orchestrator-prompt.md:134`「通常の失敗」→「`needs_human` を持たない失敗と
  同じ経路」/ `system.md:456`「通常操作の透過」→「`CTR-docker-api` が拒否条件と定めない要求の透過」。
- 進捗は `CS8` の件数で測れる(検査が既に全件を見ているので、専用の確認手順は要らない)。

## 経緯

- 2026-08-08 起票。`/doc-check task-layer-placement` の独立レビュー(`lens: subagent`)が
  02 の 5 箇所を検出。裁定にあたり `CS8` で全件を数えたところ 34 箇所あり、**同型を全件列挙する**
  規則(`.claude/directions/issues-pendings.md` §3.1)に従って本 issue にまとめた。
- 2026-08-08 `/doc-check ssot task-layer-placement`(反映後)。**母集団を数え直して 34 → 24 箇所に
  訂正した。** 起票時の表は反映前の値で、issue 自身が「反映後に再実行すると減る」と書いていたが、
  実測値に置き換えないと `CS8` の件数を進捗の指標として使えない(本 issue 自身が
  「進捗は `CS8` の件数で測れる」と定めている)。**箇所の一覧も現在の行番号へ置き換えた。**
