---
id: task-remove-orchestrator
phase: 実装
origin_layer: 00
issue: なし
lane: critical
external_behavior: true
irreversible_data: true
security_payment_privacy: false
public_contract_breaking: true
shared_resource_format: true
unresolved_impact: false
rollback_defined: false
date: 2026-08-08
updated: 2026-08-10
source:
  - docs/00-requests/acceptances.md
  - docs/00-requests/decisions/dist.md
  - docs/00-requests/decisions/env.md
  - docs/00-requests/decisions/orch.md
  - docs/00-requests/decisions/sec.md
  - docs/00-requests/request.md
  - docs/00-requests/terminology.md
  - docs/01-requirements/decisions/split.md
  - docs/01-requirements/functional.md
  - docs/01-requirements/non-functional.md
  - docs/01-requirements/system.md
  - docs/01-requirements/usecases.md
  - docs/02-design/architecture.md
  - docs/02-design/contracts/cli-container.md
  - docs/02-design/contracts/cli-orchestrator.md
  - docs/02-design/contracts/orchestrator-prompt.md
  - docs/02-design/environments.md
  - docs/02-design/logging.md
  - docs/02-design/relations.md
  - docs/02-design/system.md
  - docs/03-impl/contracts/cli-orchestrator.md
  - docs/03-impl/contracts/orchestrator-prompt.md
  - docs/03-impl/environments/images.md
  - docs/03-impl/features.md
  - docs/03-impl/index.md
  - docs/03-impl/relations/MODULE-cli-common-container-name.md
  - docs/03-impl/relations/MODULE-cli-common-is-running.md
  - docs/03-impl/relations/MODULE-cli-common-require-setup.md
  - docs/03-impl/relations/MODULE-cli-common-resolve-container-user.md
  - docs/03-impl/relations/MODULE-cli-orchestrate.md
  - docs/03-impl/relations/MODULE-cli-start.md
  - docs/03-impl/relations/MODULE-docker-proxy-serve.md
  - docs/03-impl/relations/MODULE-hooks-save-prompt.md
  - docs/03-impl/relations/MODULE-hooks-send-slack-message.md
  - docs/03-impl/relations/MODULE-makefile-build-orchestrator.md
  - docs/03-impl/relations/MODULE-makefile-orch-sample-clean.md
  - docs/03-impl/relations/MODULE-makefile-orch-sample.md
  - docs/03-impl/relations/MODULE-orchestrator-claude-exec.md
  - docs/03-impl/relations/MODULE-orchestrator-config.md
  - docs/03-impl/relations/MODULE-orchestrator-controller.md
  - docs/03-impl/relations/MODULE-orchestrator-dashboard.md
  - docs/03-impl/relations/MODULE-orchestrator-handoff.md
  - docs/03-impl/relations/MODULE-orchestrator-main.md
  - docs/03-impl/relations/MODULE-orchestrator-mode.md
  - docs/03-impl/relations/MODULE-orchestrator-plan.md
  - docs/03-impl/relations/MODULE-orchestrator-review.md
  - docs/03-impl/relations/MODULE-orchestrator-session.md
  - docs/03-impl/relations/MODULE-orchestrator-slack.md
  - docs/03-impl/relations/MODULE-orchestrator-state-intervention.md
  - docs/03-impl/relations/MODULE-orchestrator-state-io.md
  - docs/03-impl/relations/MODULE-orchestrator-state.md
  - docs/03-impl/relations/MODULE-orchestrator-streamlog.md
  - docs/03-impl/relations/MODULE-orchestrator-term.md
  - docs/03-impl/relations/MODULE-orchestrator-trigger.md
  - docs/03-impl/relations/MODULE-orchestrator-worker.md
  - docs/03-impl/relations/MODULE-orchestrator-worktree.md
  - docs/03-impl/relations/MODULE-sample-project-mathkit.md
  - docs/03-impl/relations/MODULE-sample-project-scaffold.md
  - docs/03-impl/relations/MODULE-vm-mode-healthd.md
  - docs/03-impl/tests/cli-common.md
  - docs/03-impl/tests/cli-orchestrate.md
  - docs/03-impl/tests/e2e.md
  - docs/03-impl/tests/hooks.md
  - docs/03-impl/tests/images.md
  - docs/03-impl/tests/makefile.md
  - docs/03-impl/tests/orchestrator.md
  - docs/03-impl/tests/sample-project.md
  - docs/03-impl/tests/strategy.md
summary: orchestrator に関する記述・機能・実装を SSOT とコードから全て削除し、残りの辻褄を合わせる
---

# task-remove-orchestrator orchestrator の全面削除

> 解決済みの経緯: `memo-1.md`(フェーズ1 の決定シートの回答と転記の根拠) / `memo-2.md`(帰着済みの未決点4件とフェーズ2 の途中経過)

## 目的

AIオーケストレーター(`orchestrator/` の Go 実装、`claude-dev orchestrate`、自己検証題材、
それらを支える 00〜03 の全記述)を、**このプロジェクトに最初から存在しなかった形**へ戻す。
残る claude-dev(隔離コンテナ開発環境)だけで 00〜03 とコードの辻褄が合う状態にする。

## やること・やらないこと

| 種別 | 内容 |
|---|---|
| やること | 00〜03 の SSOT から orchestrator 由来の要求・要件・設計・契約・実装仕様を削除し、残る記述の参照・件数・カバレッジを合わせる。`orchestrator/` `examples/orch-sample/` `scripts/orch-sample.sh` とその周辺(Makefile・CLI・Dockerfile・.gitignore・README/INDEX)の実装を削除する。対象が消える `docs/issues/` を削除する |
| やらないこと(このタスクの範囲外) | **`docs/orch/`(2026-08-08 の抽出物)には触れない** — SSOT の外にあり、別プロジェクトへ分離するための素材として直前のコミットが意図して作ったもの。**`docs/histories/` と `docs/feedbacks/` には触れない** — 過去に何が起きたかの記録であり、現在の姿を述べる SSOT ではない。**docker-proxy / VM モード / Codex 同梱 / ブラウザ確認は一切変更しない** |

## 影響範囲(closure)

| 層 | SSOT のパス | 変更指示のパス | 変更の種類 |
|---|---|---|---|
| 00 | docs/00-requests/acceptances.md | new-features/00-requests/acceptances.md | replace |
| 00 | docs/00-requests/decisions/dist.md | new-features/00-requests/decisions/dist.md | replace |
| 00 | docs/00-requests/decisions/env.md | new-features/00-requests/decisions/env.md | replace |
| 00 | docs/00-requests/decisions/orch.md | new-features/00-requests/decisions/orch.md | delete |
| 00 | docs/00-requests/decisions/sec.md | new-features/00-requests/decisions/sec.md | replace |
| 00 | docs/00-requests/request.md | new-features/00-requests/request.md | replace |
| 00 | docs/00-requests/terminology.md | new-features/00-requests/terminology.md | replace |
| 01 | docs/01-requirements/decisions/split.md | new-features/01-requirements/decisions/split.md | replace |
| 01 | docs/01-requirements/functional.md | new-features/01-requirements/functional.md | replace |
| 01 | docs/01-requirements/non-functional.md | new-features/01-requirements/non-functional.md | replace |
| 01 | docs/01-requirements/system.md | new-features/01-requirements/system.md | replace |
| 01 | docs/01-requirements/usecases.md | new-features/01-requirements/usecases.md | replace |
| 02 | docs/02-design/architecture.md | new-features/02-design/architecture.md | replace |
| 02 | docs/02-design/contracts/cli-container.md | new-features/02-design/contracts/cli-container.md | replace |
| 02 | docs/02-design/contracts/cli-orchestrator.md | new-features/02-design/contracts/cli-orchestrator.md | delete |
| 02 | docs/02-design/contracts/orchestrator-prompt.md | new-features/02-design/contracts/orchestrator-prompt.md | delete |
| 02 | docs/02-design/environments.md | new-features/02-design/environments.md | replace |
| 02 | docs/02-design/logging.md | new-features/02-design/logging.md | replace |
| 02 | docs/02-design/relations.md | new-features/02-design/relations.md | replace |
| 02 | docs/02-design/system.md | new-features/02-design/system.md | replace |
| 03 | docs/03-impl/contracts/cli-orchestrator.md | new-features/03-impl/contracts/cli-orchestrator.md | delete |
| 03 | docs/03-impl/contracts/orchestrator-prompt.md | new-features/03-impl/contracts/orchestrator-prompt.md | delete |
| 03 | docs/03-impl/environments/images.md | new-features/03-impl/environments/images.md | replace |
| 03 | docs/03-impl/features.md | new-features/03-impl/features.md | replace |
| 03 | docs/03-impl/index.md | new-features/03-impl/index.md | replace |
| 03 | docs/03-impl/relations/MODULE-cli-common-container-name.md | new-features/03-impl/relations/MODULE-cli-common-container-name.md | replace |
| 03 | docs/03-impl/relations/MODULE-cli-common-is-running.md | new-features/03-impl/relations/MODULE-cli-common-is-running.md | replace |
| 03 | docs/03-impl/relations/MODULE-cli-common-require-setup.md | new-features/03-impl/relations/MODULE-cli-common-require-setup.md | replace |
| 03 | docs/03-impl/relations/MODULE-cli-common-resolve-container-user.md | new-features/03-impl/relations/MODULE-cli-common-resolve-container-user.md | replace |
| 03 | docs/03-impl/relations/MODULE-cli-orchestrate.md | new-features/03-impl/relations/MODULE-cli-orchestrate.md | delete |
| 03 | docs/03-impl/relations/MODULE-cli-start.md | new-features/03-impl/relations/MODULE-cli-start.md | replace |
| 03 | docs/03-impl/relations/MODULE-docker-proxy-serve.md | new-features/03-impl/relations/MODULE-docker-proxy-serve.md | replace |
| 03 | docs/03-impl/relations/MODULE-hooks-save-prompt.md | new-features/03-impl/relations/MODULE-hooks-save-prompt.md | delete |
| 03 | docs/03-impl/relations/MODULE-hooks-send-slack-message.md | new-features/03-impl/relations/MODULE-hooks-send-slack-message.md | delete |
| 03 | docs/03-impl/relations/MODULE-makefile-build-orchestrator.md | new-features/03-impl/relations/MODULE-makefile-build-orchestrator.md | delete |
| 03 | docs/03-impl/relations/MODULE-makefile-orch-sample-clean.md | new-features/03-impl/relations/MODULE-makefile-orch-sample-clean.md | delete |
| 03 | docs/03-impl/relations/MODULE-makefile-orch-sample.md | new-features/03-impl/relations/MODULE-makefile-orch-sample.md | delete |
| 03 | docs/03-impl/relations/MODULE-orchestrator-claude-exec.md | new-features/03-impl/relations/MODULE-orchestrator-claude-exec.md | delete |
| 03 | docs/03-impl/relations/MODULE-orchestrator-config.md | new-features/03-impl/relations/MODULE-orchestrator-config.md | delete |
| 03 | docs/03-impl/relations/MODULE-orchestrator-controller.md | new-features/03-impl/relations/MODULE-orchestrator-controller.md | delete |
| 03 | docs/03-impl/relations/MODULE-orchestrator-dashboard.md | new-features/03-impl/relations/MODULE-orchestrator-dashboard.md | delete |
| 03 | docs/03-impl/relations/MODULE-orchestrator-handoff.md | new-features/03-impl/relations/MODULE-orchestrator-handoff.md | delete |
| 03 | docs/03-impl/relations/MODULE-orchestrator-main.md | new-features/03-impl/relations/MODULE-orchestrator-main.md | delete |
| 03 | docs/03-impl/relations/MODULE-orchestrator-mode.md | new-features/03-impl/relations/MODULE-orchestrator-mode.md | delete |
| 03 | docs/03-impl/relations/MODULE-orchestrator-plan.md | new-features/03-impl/relations/MODULE-orchestrator-plan.md | delete |
| 03 | docs/03-impl/relations/MODULE-orchestrator-review.md | new-features/03-impl/relations/MODULE-orchestrator-review.md | delete |
| 03 | docs/03-impl/relations/MODULE-orchestrator-session.md | new-features/03-impl/relations/MODULE-orchestrator-session.md | delete |
| 03 | docs/03-impl/relations/MODULE-orchestrator-slack.md | new-features/03-impl/relations/MODULE-orchestrator-slack.md | delete |
| 03 | docs/03-impl/relations/MODULE-orchestrator-state-intervention.md | new-features/03-impl/relations/MODULE-orchestrator-state-intervention.md | delete |
| 03 | docs/03-impl/relations/MODULE-orchestrator-state-io.md | new-features/03-impl/relations/MODULE-orchestrator-state-io.md | delete |
| 03 | docs/03-impl/relations/MODULE-orchestrator-state.md | new-features/03-impl/relations/MODULE-orchestrator-state.md | delete |
| 03 | docs/03-impl/relations/MODULE-orchestrator-streamlog.md | new-features/03-impl/relations/MODULE-orchestrator-streamlog.md | delete |
| 03 | docs/03-impl/relations/MODULE-orchestrator-term.md | new-features/03-impl/relations/MODULE-orchestrator-term.md | delete |
| 03 | docs/03-impl/relations/MODULE-orchestrator-trigger.md | new-features/03-impl/relations/MODULE-orchestrator-trigger.md | delete |
| 03 | docs/03-impl/relations/MODULE-orchestrator-worker.md | new-features/03-impl/relations/MODULE-orchestrator-worker.md | delete |
| 03 | docs/03-impl/relations/MODULE-orchestrator-worktree.md | new-features/03-impl/relations/MODULE-orchestrator-worktree.md | delete |
| 03 | docs/03-impl/relations/MODULE-sample-project-mathkit.md | new-features/03-impl/relations/MODULE-sample-project-mathkit.md | delete |
| 03 | docs/03-impl/relations/MODULE-sample-project-scaffold.md | new-features/03-impl/relations/MODULE-sample-project-scaffold.md | delete |
| 03 | docs/03-impl/relations/MODULE-vm-mode-healthd.md | new-features/03-impl/relations/MODULE-vm-mode-healthd.md | replace |
| 03 | docs/03-impl/tests/cli-common.md | new-features/03-impl/tests/cli-common.md | replace |
| 03 | docs/03-impl/tests/cli-orchestrate.md | new-features/03-impl/tests/cli-orchestrate.md | delete |
| 03 | docs/03-impl/tests/e2e.md | new-features/03-impl/tests/e2e.md | replace |
| 03 | docs/03-impl/tests/hooks.md | new-features/03-impl/tests/hooks.md | delete |
| 03 | docs/03-impl/tests/images.md | new-features/03-impl/tests/images.md | replace |
| 03 | docs/03-impl/tests/makefile.md | new-features/03-impl/tests/makefile.md | replace |
| 03 | docs/03-impl/tests/orchestrator.md | new-features/03-impl/tests/orchestrator.md | delete |
| 03 | docs/03-impl/tests/sample-project.md | new-features/03-impl/tests/sample-project.md | delete |
| 03 | docs/03-impl/tests/strategy.md | new-features/03-impl/tests/strategy.md | replace |
| 00 | docs/00-requests/decisions/scope.md | - | 変更なし(理由: D0-scope-01〜07 はいずれも記述粒度と実装内部の委任で、orchestrator 固有の語を持たない) |
| 00 | docs/00-requests/decisions/auth.md | - | 変更なし(理由: 認証共有は Claude Code / Codex CLI の話で orchestrator を含まない) |
| 00 | docs/00-requests/decisions/index.md | - | 変更なし(build-index.py の生成物。反映後に再生成する) |
| 01 | docs/01-requirements/decisions/index.md | - | 変更なし(生成物) |
| 02 | docs/02-design/contracts/docker-api.md | - | 変更なし(理由: docker-proxy の検査規則に orchestrator は現れない) |
| 02 | docs/02-design/contracts/entrypoint-firewall.md | - | 変更なし(理由: ファイアウォールに orchestrator は現れない) |
| 02 | docs/02-design/contracts/index.md | - | 変更なし(生成物) |
| 03 | docs/03-impl/contracts/cli-container.md | - | 変更なし(理由: 実装側の契約に MOD-cli-orchestrate は現れない) |
| 03 | docs/03-impl/relations/index.md | - | 変更なし(生成物) |
| 03 | docs/03-impl/tests/index.md | - | 変更なし(生成物) |
| 03 | docs/03-impl/contracts/index.md | - | 変更なし(生成物) |
| 03 | docs/03-impl/feature-graph.md | - | 変更なし(cluster-features.py の生成物。反映後に再生成する) |
| 03 | docs/03-impl/callgraphs/ | - | 変更なし(build-callgraphs.py の生成物。ツールだけが書く) |
| 03 | docs/03-impl/infra/local/docker-resources.md | - | 変更なし(理由: Docker 資源の構成値に orchestrator は現れない) |
| 03 | docs/03-impl/infra/local/ghcr.md | - | 変更なし(理由: GHCR の配布構成に orchestrator は現れない) |

**closure の外だが同じタスクで触るもの**(SSOT ではないので上表に載せない):
実装(`orchestrator/` / `examples/orch-sample/` / `scripts/orch-sample.sh` /
`scripts/save_prompt.sh` / `scripts/sendslackmsg.sh` / `Makefile` / `claude-dev` /
`claude-dev-mac` / `.devcontainer/Dockerfile.claude` / `.gitignore` / `scripts/vm-healthd.sh` /
`README.md` / `INDEX.md`)、`docs/issues/` の該当ファイル、`docs/pendings.md`。

## 読む範囲(読了記録)

- 全文読了: 2026-08-08
  - docs/00-requests/acceptances.md@1.3.0
  - docs/00-requests/decisions/auth.md@1.3.0
  - docs/00-requests/decisions/dist.md@1.1.0
  - docs/00-requests/decisions/env.md@1.4.0
  - docs/00-requests/decisions/orch.md@1.4.0
  - docs/00-requests/decisions/scope.md@1.2.0
  - docs/00-requests/decisions/sec.md@1.2.0
  - docs/00-requests/request.md@1.3.0
  - docs/00-requests/terminology.md@1.4.0
  - docs/01-requirements/decisions/split.md@1.2.0
  - docs/01-requirements/functional.md@1.12.0
  - docs/01-requirements/non-functional.md@1.6.0
  - docs/01-requirements/system.md@1.1.0
  - docs/01-requirements/usecases.md@1.4.0
  - docs/02-design/architecture.md@1.4.0
  - docs/02-design/contracts/cli-container.md@1.7.0
  - docs/02-design/contracts/cli-orchestrator.md@1.2.0
  - docs/02-design/contracts/docker-api.md@1.1.0
  - docs/02-design/contracts/entrypoint-firewall.md@1.0.1
  - docs/02-design/contracts/orchestrator-prompt.md@1.3.0
  - docs/02-design/environments.md@1.3.0
  - docs/02-design/logging.md@1.4.1
  - docs/02-design/relations.md@1.7.0
  - docs/02-design/system.md@2.8.0

## 決定シート(回答済み)
> 回答済み: sheet.md(転記済み。**フェーズ2 の `/doc-check` が 論点5 を追記し、一括回答で settle して転記した**)

(memo-1.md に移動)

## 未決点

**未決点なし**(全4件は 2026-08-08 に帰着済み。内容は `memo-2.md` に移動)。帰着先はタスクリスト
14(実測値で書く 3 件)と 15(変更指示の記法で表せない HTML コメントの削除 1 件)。

## 調査メモ

| # | 調べたこと | 判明した事実 | 出どころ |
|---|---|---|---|
| 1 | 削除対象の機能の数 | 機能表 83 本のうち 27 本が対象。`MODULE-orchestrator-*` 19 本 + `MODULE-cli-orchestrate` + `MODULE-makefile-build-orchestrator` + `MODULE-makefile-orch-sample` + `MODULE-makefile-orch-sample-clean` + `MODULE-sample-project-scaffold` + `MODULE-sample-project-mathkit` + `MODULE-hooks-save-prompt` + `MODULE-hooks-send-slack-message` | `docs/03-impl/features.md:19`〜`:104` |
| 2 | 削除される受入基準の条項数 | `FR-orch-01`〜`09` = 69 条項(7+5+11+9+10+7+6+8+6)。加えて `FR-env-12-12`(対象外の行。`D0-orch-17` 未決に依存)1 条項。機能要件は 210 条項 → 140 条項になる | `docs/01-requirements/functional.md:353`〜`:527` / `docs/02-design/system.md:409` |
| 3 | 削除される非機能要件 | `NFR-perf-03` / `NFR-avail-01` / `NFR-sec-03` / `NFR-ops-04` の 4 件。13 件 → 9 件。`NFR-avail-03` は「通知」を補助機能の列挙から外す修正 | `docs/01-requirements/non-functional.md:41`,`:47`,`:49`,`:56`,`:64` |
| 4 | hooks が orchestrator の実装から呼ばれるか | 呼ばれない。orchestrator は自前の Go 実装(`orchestrator/slack.go`)で通知する。hooks はイメージに焼いてあるだけで、どのファイルからも登録されていない | `.devcontainer/Dockerfile.claude:274`〜`:275`,`:285` / `orchestrator/slack.go:14` / `claude-dev:1274` |
| 5 | hooks の要件上の根拠 | `MOD-hooks` の対応要件は `FR-orch-07` と `NFR-sec-03` / `NFR-avail-03` だけ。`FR-orch-07` を消すと要件の裏付けが 0 になる | `docs/02-design/system.md:63` / `docs/02-design/relations.md:74`〜`:75` |
| 6 | Go の外部依存 | 外部ライブラリ(bubbletea / lipgloss とその推移依存 17 本)を持つのは `orchestrator/` だけ。`docker-proxy/go.mod` は依存 0 本 | `orchestrator/go.mod:5`〜`:26` / `docker-proxy/go.mod` |
| 7 | `docs/orch/` の位置づけ | 直前のコミット `fce4552` が「別プロジェクトへ分離する前段」として SSOT から原文のまま抜き出した抽出物。`verified` を持たず SSOT ではない | `docs/orch/00.md:1`〜`:30` / `git show fce4552` |
| 8 | 走らせるべきテスト(DoD の種) | `cd docker-proxy && go test ./...`(orchestrator と orch-sample の test は対象ごと消える)。`go vet ./...` は `docker-proxy/` のみ。E2E は `E2E-01` / `E2E-02` / `E2E-03` / `E2E-06` が残り、`E2E-04` / `E2E-05` が消える | `docs/02-design/environments.md:52`〜`:63` / `docs/02-design/system.md:455`〜`:460` |
| 9 | 仕様ドキュメントの一括検査の母集団(着手時点) | 156 ファイル / NG 違反 134 件。内訳: CS8 曖昧語 36 / CS11 参照実在 19 / CS12 OK / CS18 OK / CS19 理由の網羅 26 / CS20 issue の起点層 53 | `python3 .claude/scripts/check-changeset.py --ssot docs`(2026-08-08 実行) |
| 10 | `orchestrator/main.go` の影響範囲 | 直接この実装を持つ機能 1 件、波及する呼び出し元 0 件、関係する要件 `FR-orch-01` / `FR-orch-02` / `FR-orch-05`、関係する契約 `CTR-cli-orchestrator` | `python3 .claude/scripts/relations-query.py --impact orchestrator/main.go` |
| 12 | 削除する `docs/issues/` の全件(21 件) | `001`(orchestrator のテスト専用シンボル)/ `003`(macOS の orchestrate)/ `007`(異種ベンダーのレビューアー)/ `011`(taskID の未検証)/ `012`(`reviewer_vendor` が無効)/ `013`(Slack の失敗を検出しない)/ `014`(追記型ログの必須フィールド)/ `015`(列挙外の `needs_human.reason`)/ `021`(`.orchestrator/` ストアにロックが無い)/ `022`(`merge_strategy` の未検証)/ `026`(状態保存の失敗を握る)/ `033`(orch-sample の pytest が失敗する)/ `057`(壊れた `open.json`)/ `058`(未知の `severity`)/ `059`(採点基準を覆うテストが無い)/ `061`(`dispatch` と `result` の要件の裏付け)/ `062`(`build-orchestrator` の程度語)/ `063`(ダッシュボードの WARN バナー)/ `064`(`DSN-prompt-03` の前置)/ `067`(hooks の Slack 失敗)/ `068`(介入トリガーの定義)。**21 件すべて `related` が orchestrator / hooks / 自己検証題材の ID だけで構成されており、対象の実装ごと消える**。残る issue は 61 - 21 = 40 件 | 各 issue の frontmatter `related` を全件確認(2026-08-08) |
| 13 | 削除する ID が SSOT のどこかに残っていないか | 節レベルで走査した結果、変更指示が覆っていない箇所は **2 件だけ**だった: `docs/03-impl/relations/MODULE-docker-proxy-serve.md:164`(`D0-orch-02` の引用)と `docs/01-requirements/functional.md:266`(`FR-env-08-4` の `docs/issues/063` 参照)。どちらも変更指示を追加して解消した | 自作の節レベル被覆スクリプト(2026-08-08) |
| 14 | 条項数の層またぎの一致 | 01 の 140 条項 = 02 のカバレッジ表 140 行 = 03 のテスト対応表 140 条項(集合として完全一致。差分 0)。03 のテスト対応表は `FR-env-01-9` が 3 行あるため 142 行、非機能 9 行と合わせて 151 行 | 突き合わせスクリプト(2026-08-08) |
| 11 | 実装側の削除箇所 | `claude-dev:1534`〜`:1610` と `:2290`(orchestrate サブコマンド)、`claude-dev-mac` の同等箇所、`Makefile:45`〜`:46`,`:61`,`:168`〜`:182`、`.devcontainer/Dockerfile.claude:12`〜`:21`,`:290`〜`:293`、`.gitignore:8`〜`:12`、`scripts/vm-healthd.sh:14`(コメント) | 各ファイルの該当行 |

## 質問キュー(未提示)

| # | 論点 | 何が止まるか | 推奨する回答(暫定) |
|---|---|---|---|
| - | なし | - | - |

## タスクリスト

- [x] 1. `orchestrator/` を削除する(Go モジュール一式・`vendor/`・`instructions/`) _要件:_ FR-orch-01〜09 の廃止 _Boundary:_ `orchestrator/` _Depends:_ -
- [x] 2. `examples/orch-sample/` / `workspace/orch-sample/` / `scripts/orch-sample.sh` を削除する _要件:_ FR-orch-09 の廃止 _Boundary:_ 左記 _Depends:_ - (P)
- [x] 3. `scripts/save_prompt.sh` / `scripts/sendslackmsg.sh` を削除する _要件:_ FR-orch-07 の廃止 _Boundary:_ 左記 _Depends:_ - (P)
- [x] 4. `Makefile` から `build-orchestrator` / `orch-sample` / `orch-sample-clean` の 3 ターゲットと `.PHONY` / `help` の行を削除する _要件:_ FR-orch-01 / FR-orch-09 の廃止 _Boundary:_ `Makefile` _Depends:_ 1,2
- [x] 5. `claude-dev` と `claude-dev-mac` から `orchestrate` サブコマンドの `case` 節と使い方の行を削除する _要件:_ FR-orch-01 / FR-orch-02 の廃止 _Boundary:_ `claude-dev` / `claude-dev-mac` _Depends:_ 1
- [x] 6. `.devcontainer/Dockerfile.claude` から `orch-builder` ステージ・`claude-orchestrator` のコピー・`instructions/` のコピー・hooks 2 本の `COPY` と `chmod` を削除する _要件:_ 同上 _Boundary:_ 左記 _Depends:_ 1,3
- [x] 7. `.gitignore` から `/orchestrator/orchestrator` と `/.orchestrator/` の行を削除する _Boundary:_ `.gitignore` _Depends:_ 1
- [x] 8. `.claude/scripts/callgraph-config.local.json` の `excludes` から `orchestrator/vendor/` と `.orchestrator/` を外す(02 の「コールグラフ抽出設定」に合わせる) _Boundary:_ 左記 _Depends:_ 1 — **着手時点でこのファイルが存在しなかった**(2026-08-10 のキット書き換えで失われた)。02 の設定に合わせて作り直し、`workspace/` / `tmp/` / `scripts/e2e6-codex.sh` の除外と `include_tooling: true` を書いた
- [x] 9. `scripts/vm-healthd.sh:14` のコメントから「orchestrator dashboard が読む」を外す _Boundary:_ 左記 _Depends:_ - (P)
- [x] 10. `README.md` と `INDEX.md` から orchestrator の記述を削除する _Boundary:_ 左記 _Depends:_ 1〜6 (P)
- [x] 11. 実行時の運用状態 `.orchestrator/` を削除する(gitignore 済みの生成物) _Boundary:_ `.orchestrator/` _Depends:_ 1
- [x] 12. `docs/issues/` から次の **21 件**を削除する(調査メモ 12 が根拠。ID を直接書くのは、**67 件の変更指示のうち 14 件しかこれらに言及しておらず、残り 7 件(`001` / `007` / `011` / `012` / `021` / `022` / `026`)はどの変更指示からも参照されないため** — 独立レビュー docs の指摘): `001` / `003` / `007` / `011` / `012` / `013` / `014` / `015` / `021` / `022` / `026` / `033` / `057` / `058` / `059` / `061` / `062` / `063` / `064` / `067` / `068`。あわせて `docs/pendings.md` の P-002 から「Go の2モジュール」の記述を直し、`python3 .claude/scripts/build-index.py` で `docs/issues/index.md` を再生成する _Boundary:_ `docs/issues/` / `docs/pendings.md` _Depends:_ 1〜11
- [x] 13. lint とテストを実行する(`cd docker-proxy && go vet ./... && go test ./...`) _Depends:_ 1〜11
- [ ] 15. `/task-close` の反映(`compose-changeset.py --apply`)では表せない箇所を、反映の手順として手で適用する _Depends:_ 14
  - a. `docs/01-requirements/functional.md` と `docs/01-requirements/non-functional.md` の frontmatter 直後の HTML コメント(削除される ID に触れる検証記録)を削除する。**見出しを持たないため `sections` にも `deletes` にも載せられない**
  - b. `docs/03-impl/features.md` の `## 統合した機能` / `## 昇格させた共通基盤機能` / `## 到達しない関数についての判断` と frontmatter の `keywords` を、`new-features/03-impl/features.md` の本文どおりに差し替える。**`compose-changeset.py` は features.md について `## 機能一覧` の差分表しか適用しない**(`docs/pendings.md` 残務)。差し替えないと `check-relations.py` の FT3 が `MODULE-sample-project-mathkit` で落ちる
  - c. `python3 .claude/scripts/build-index.py` で生成インデックス(`docs/03-impl/relations/index.md` ほか)を再生成する
- [x] 14. コールグラフと機能間関係グラフを再生成し、`callgraph-check.py` / `check-relations.py` / `check-contracts.py` / `relations-coverage.py` / `relations-query.py --health` を実行して、実測値で `new-features/03-impl/index.md` を書き、`new-features/03-impl/features.md` のファンイン値と `new-features/03-impl/environments/images.md` の行番号を更新する。**あわせて `new-features/03-impl/index.md` へ `## この層の状態` と `## コールグラフ` の 2 節を追記する**(フェーズ2 では実測値が確定しないため意図的に外してある) _Depends:_ 1〜13

## Definition of Done

<!-- 実測の表(コマンドの最終行を逐語で引用)は「進捗メモ」の 2026-08-10 フェーズ3 完了行にある。 -->

- [x] lint が通る: `cd docker-proxy && go vet ./...`
- [x] 単体・結合テストが通る: `cd docker-proxy && go test ./...`
- [x] build が通る: `make build`(`.devcontainer/Dockerfile.claude` から `orch-builder` ステージを外したため必須)
- [x] 受入基準のテストが全て存在し通る(**本タスクは要件を削除するだけで新設しないので、新しい受入基準は無い**。既存の対応表から削除対象の行が消えていることを確認する)
- [x] 影響する E2E シナリオ: **対象外**(削除したのは E2E-04 / E2E-05 そのもの。残る E2E-01〜03 / E2E-06 の手順は変更していない)。**E2E-01〜03 / E2E-06 は自動テストランナーを持たない実機確認**(`02-design/environments.md`)であり、本タスクは実行していない — 理由と再開条件は進捗メモに書いた
- [x] `CG_OUT=$(python3 .claude/scripts/resolve-callgraph-out.py task-remove-orchestrator) || exit 2` のあと
      `build-callgraphs.py --out "$CG_OUT"` でコールグラフを再生成し、
      `callgraph-check.py --to-be task-remove-orchestrator` の重大度「高」が0
- [x] `check-relations.py` が合格(合成ビューで実測)
- [x] `relations-query.py --health` の循環が0件(合成ビューで実測)
- [ ] `new-features/` の全変更指示を SSOT へ反映済み — `/task-close` で実施
- [ ] `/doc-check` が影響範囲を PASS — `/task-close` で実施
- [ ] `docs/histories/` に記録 — `/task-close` で実施
- [x] 見つけた範囲外の問題を `docs/issues/` / `docs/pendings.md` に記録済み(`docs/pendings.md`「残務(文書整合ほか)」に 9 行)
- [x] `docs/issues/` の該当 **21 件**が削除され、残りが **39 件**であること(タスクリスト 12)。**フェーズ1 の調査メモ 12 は「61 - 21 = 40」と書いていたが、母数 61 は `index.md` を含めた数え間違いで、実体は 60 件だった**(その後 `task-layer-placement` の完了で 5 件減り 1 件増えた分も含めて 2026-08-10 時点で 60 件)
- [ ] `docs/01-requirements/functional.md` / `non-functional.md` の冒頭 HTML コメントから、削除した ID への言及が消えていること(タスクリスト 15-a) — `/task-close` で実施
- [x] リポジトリ全体に orchestrator への参照が残っていないこと(`docs/` `.claude/` と git 履歴を除く)。**`docs/` に残るのは `/task-close` が反映する SSOT と、範囲外と決めた `docs/orch/` / `docs/histories/` / `docs/feedbacks/` / `docs/kit-report.md` / `docs/ONBOARDING.md` / 残る issue 6 件だけである**
