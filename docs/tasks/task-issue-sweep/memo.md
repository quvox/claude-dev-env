---
id: task-issue-sweep
phase: 反映
lane: critical
origin_layer: 00
external_behavior: true
irreversible_data: true
security_payment_privacy: false
public_contract_breaking: false
shared_resource_format: false
unresolved_impact: false
rollback_defined: true
issue: docs/issues/023-bug-ssh-bridge-port-accepts-unvalidated-host-env.md, docs/issues/047-bug-reset-leaves-vm-volumes-behind.md, docs/issues/051-bug-cli-output-leaks-raw-docker-ids.md, docs/issues/056-modify-ssot-retains-change-relative-wording.md, docs/issues/087-modify-container-path-has-no-log-when-owner-label-injection-fails.md, docs/issues/088-bug-stop-does-not-report-a-failed-compose-default-network-removal.md, docs/issues/101-bug-reset-omits-the-unmanaged-container-warning-when-deletion-fails.md, docs/issues/054-modify-ssot-references-deleted-issue-paths.md, docs/issues/074-modify-fr-env-01-9-has-three-owning-rows-in-test-tables.md, docs/issues/077-modify-unverified-enumeration-target-column-keeps-the-pre-clause-id-notation.md, docs/issues/078-modify-two-frontmatter-scalars-start-with-a-backtick-and-break-yaml-parsing.md, docs/issues/084-modify-test-documents-have-no-test-design-decision-section.md, docs/issues/095-modify-degree-word-tsujo-remains-across-all-layers.md, docs/issues/009-modify-relations-prose-signatures-drift-from-code.md, docs/issues/030-modify-03-impl-index-understates-code-doc-divergences.md, docs/issues/004-modify-03-impl-lacks-reimplementation-depth.md, docs/issues/006-modify-e2e-procedures-lack-reproducibility.md, docs/issues/031-modify-audit-lens-model-is-undecided-so-the-weakest-runs.md, docs/issues/048-modify-design-claims-shared-base-functions-never-call-each-other.md, docs/issues/065-modify-lens-substitution-policy-has-no-normative-home.md, docs/issues/066-modify-six-more-nfr-targets-do-not-measure-the-whole-requirement.md, docs/issues/071-modify-terminology-lacks-inclusion-exclusion-examples.md, docs/issues/072-modify-five-design-points-are-not-derivable-from-the-documents.md, docs/issues/080-modify-destructive-commands-appear-in-no-use-case.md
date: 2026-08-11
updated: 2026-08-12
source:
  - docs/00-requests/decisions/auth.md
  - docs/00-requests/decisions/env.md
  - docs/00-requests/decisions/scope.md
  - docs/00-requests/decisions/sec.md
  - docs/01-requirements/functional.md
  - docs/02-design/contracts/cli-container.md
  - docs/02-design/environments.md
  - docs/02-design/logging.md
  - docs/02-design/relations.md
  - docs/02-design/system.md
  - docs/03-impl/contracts/cli-container.md
  - docs/03-impl/contracts/docker-api.md
  - docs/03-impl/index.md
  - docs/03-impl/relations/MODULE-cli-common-destructive.md
  - docs/03-impl/relations/MODULE-cli-common-ensure-infrastructure.md
  - docs/03-impl/relations/MODULE-cli-login-codex.md
  - docs/03-impl/relations/MODULE-cli-login.md
  - docs/03-impl/relations/MODULE-cli-logout.md
  - docs/03-impl/relations/MODULE-cli-reset.md
  - docs/03-impl/relations/MODULE-cli-start.md
  - docs/03-impl/relations/MODULE-cli-stop.md
  - docs/03-impl/relations/MODULE-cli-unforward.md
  - docs/03-impl/relations/MODULE-docker-proxy-serve.md
  - docs/03-impl/tests/cli-attach.md
  - docs/03-impl/tests/cli-code.md
  - docs/03-impl/tests/cli-common.md
  - docs/03-impl/tests/cli-firewall.md
  - docs/03-impl/tests/cli-forward.md
  - docs/03-impl/tests/cli-list.md
  - docs/03-impl/tests/cli-login-codex.md
  - docs/03-impl/tests/cli-login.md
  - docs/03-impl/tests/cli-logout.md
  - docs/03-impl/tests/cli-ports.md
  - docs/03-impl/tests/cli-pull.md
  - docs/03-impl/tests/cli-reset.md
  - docs/03-impl/tests/cli-setup.md
  - docs/03-impl/tests/cli-ssh-keys.md
  - docs/03-impl/tests/cli-start.md
  - docs/03-impl/tests/cli-stop.md
  - docs/03-impl/tests/cli-unforward.md
  - docs/03-impl/tests/cli-upgrade.md
  - docs/03-impl/tests/container-tools.md
  - docs/03-impl/tests/docker-proxy.md
  - docs/03-impl/tests/e2e.md
  - docs/03-impl/tests/entrypoint.md
  - docs/03-impl/tests/firewall.md
  - docs/03-impl/tests/images.md
  - docs/03-impl/tests/makefile.md
  - docs/03-impl/tests/portsync.md
  - docs/03-impl/tests/strategy.md
  - docs/03-impl/tests/vm-mode.md
summary: 36 件の issue を原則8のゲートで一括棚卸しし、コード7件と文書整合9件を直し、空振り2件を閉じ、6件を pendings 残務へ降格する
---

# task-issue-sweep issue の一括棚卸し

> 解決済みの経緯: `memo-1.md` = フェーズ1〜2 の調査メモ(31 行。実測した母集団とコードの位置)

## 目的

`docs/issues/` の 36 件を一度に棚卸しする。実体のあるコードの欠陥7件と、機械で母集団を数えられる
文書整合6件を直し、実体が消えた2件を閉じ、原則8のゲート行4に当たる6件を `docs/pendings.md` の
残務へ1行で降格して閉じる。残す 11 件(設計判断が要る8件 + キット凍結中の3件)は範囲外として
明示する。

## やること・やらないこと

| 種別 | 内容 |
|---|---|
| やること | **(A) コードの欠陥7件**: 023(`CLAUDE_DEV_SSH_BRIDGE_PORT` の無検証)/ 047(`reset` が `claude-dev-vm-*` を残す)/ 051(生の Docker ID が利用者向け出力に漏れる)/ 056(出力文言が変更相対)/ 087(所有者ラベル注入失敗がコンテナ経路でログに出ない)/ 088(`stop` が compose 既定ネットワーク削除の失敗を報告しない)/ 101(`reset` が削除失敗時にラベル無しコンテナを表示しない) |
| やること | **(B) 文書整合6件**(母集団は下の調査メモで凍結): 054(参照切れ 16 箇所)/ 074(`FR-env-01-9` の重複行)/ 077(旧表記 19 ファイル 188 箇所)/ 078(frontmatter の YAML 解析失敗。SSOT 外)/ 084(「テスト設計の判断」欠落 19 ファイル)/ 095(程度語「通常」1 箇所) |
| やること | **(C) 実体が消えた2件を閉じる**: 009 / 030(`MODULE-orchestrator-*` は 0 本) |
| やること | **(D) pendings 残務へ降格して閉じる6件**: 004 / 006 / 066 / 071 / 072 / 080(論点2 の回答=案A により、当初9件から 031 / 048 / 065 が外れた) |
| やること | **(E) 論点2 で解消へ回した3件**: 031(environments.md から issue 参照を外す)/ 048(relations.md の追跡の1文を削除)/ 065(独立レビューの代替の可否を environments.md に1行足す) |
| やらないこと(このタスクの範囲外) | **設計判断が要る8件**: 002 / 005 / 010 / 028 / 046 / 055 / 092 / 097。いずれも 01 か 02 の判断を伴い、1回の降下に収まらない |
| やらないこと(このタスクの範囲外) | **キットの3件**: 076 / 079 / 081。CLAUDE.md §3 により製品 DoD 未達の間はキットが凍結されている |
| やらないこと(このタスクの範囲外) | 実機 E2E-01 手順8 の未実施分(`docs/pendings.md` の既存の残務行が追跡する) |

## 影響範囲(closure)

| 層 | SSOT のパス | 変更指示のパス | 変更の種類 |
|---|---|---|---|
| 00 | docs/00-requests/decisions/scope.md | new-features/00-requests/decisions/scope.md | replace |
| 00 | docs/00-requests/decisions/auth.md | new-features/00-requests/decisions/auth.md | replace |
| 00 | docs/00-requests/decisions/env.md | new-features/00-requests/decisions/env.md | replace |
| 00 | docs/00-requests/decisions/sec.md | new-features/00-requests/decisions/sec.md | replace |
| 00 | docs/00-requests/request.md | - | 変更なし(理由: 目的・対象ユーザー・やらないことは動かない) |
| 00 | docs/00-requests/acceptances.md | - | 変更なし(理由: AC-01〜03・06 の合否条件は動かない。AC-03 が参照する issue 005 は範囲外で残る) |
| 00 | docs/00-requests/terminology.md | - | 変更なし(理由: 071 は降格であり用語集を書き換えない) |
| 01 | docs/01-requirements/functional.md | new-features/01-requirements/functional.md | replace |
| 01 | docs/01-requirements/non-functional.md | - | 変更なし(理由: 066 は降格であり NFR の目標値・測定方法を書き換えない) |
| 01 | docs/01-requirements/usecases.md | - | 変更なし(理由: 080 は降格であり UC のフローを書き換えない) |
| 01 | docs/01-requirements/system.md | - | 変更なし(理由: 技術前提は動かない) |
| 01 | docs/01-requirements/decisions/split.md | - | 変更なし(理由: 分割可否の値も理由文も動かない) |
| 02 | docs/02-design/logging.md | new-features/02-design/logging.md | replace |
| 02 | docs/02-design/contracts/cli-container.md | new-features/02-design/contracts/cli-container.md | replace |
| 02 | docs/02-design/environments.md | new-features/02-design/environments.md | replace |
| 02 | docs/02-design/relations.md | new-features/02-design/relations.md | replace |
| 02 | docs/02-design/system.md | new-features/02-design/system.md | replace |
| 02 | docs/02-design/architecture.md | - | 変更なし(理由: 全体構成もデータモデルも動かない) |
| 02 | docs/02-design/contracts/docker-api.md | - | 変更なし(理由: 087 はログの欠落であり、02 の判定表もエラーケースも既に正しい。直すのは 03 側である) |
| 03 | docs/03-impl/contracts/docker-api.md | new-features/03-impl/contracts/docker-api.md | replace |
| 03 | docs/03-impl/relations/MODULE-cli-common-destructive.md | new-features/03-impl/relations/MODULE-cli-common-destructive.md | replace |
| 02 | docs/02-design/contracts/entrypoint-firewall.md | - | 変更なし(理由: ファイアウォールの契約に触れない) |
| 03 | docs/03-impl/contracts/cli-container.md | new-features/03-impl/contracts/cli-container.md | replace |
| 03 | docs/03-impl/relations/MODULE-cli-reset.md | new-features/03-impl/relations/MODULE-cli-reset.md | replace |
| 03 | docs/03-impl/relations/MODULE-cli-stop.md | new-features/03-impl/relations/MODULE-cli-stop.md | replace |
| 03 | docs/03-impl/relations/MODULE-cli-logout.md | new-features/03-impl/relations/MODULE-cli-logout.md | replace |
| 03 | docs/03-impl/relations/MODULE-cli-start.md | new-features/03-impl/relations/MODULE-cli-start.md | replace |
| 03 | docs/03-impl/relations/MODULE-cli-login.md | new-features/03-impl/relations/MODULE-cli-login.md | replace |
| 03 | docs/03-impl/relations/MODULE-cli-login-codex.md | new-features/03-impl/relations/MODULE-cli-login-codex.md | replace |
| 03 | docs/03-impl/relations/MODULE-cli-unforward.md | new-features/03-impl/relations/MODULE-cli-unforward.md | replace |
| 03 | docs/03-impl/relations/MODULE-cli-common-ensure-infrastructure.md | new-features/03-impl/relations/MODULE-cli-common-ensure-infrastructure.md | replace |
| 03 | docs/03-impl/relations/MODULE-docker-proxy-serve.md | new-features/03-impl/relations/MODULE-docker-proxy-serve.md | replace |
| 03 | docs/03-impl/tests/strategy.md | new-features/03-impl/tests/strategy.md | replace |
| 03 | docs/03-impl/tests/e2e.md | new-features/03-impl/tests/e2e.md | replace |
| 03 | docs/03-impl/tests/cli-attach.md | new-features/03-impl/tests/cli-attach.md | replace |
| 03 | docs/03-impl/tests/cli-code.md | new-features/03-impl/tests/cli-code.md | replace |
| 03 | docs/03-impl/tests/cli-common.md | new-features/03-impl/tests/cli-common.md | replace |
| 03 | docs/03-impl/tests/cli-firewall.md | new-features/03-impl/tests/cli-firewall.md | replace |
| 03 | docs/03-impl/tests/cli-forward.md | new-features/03-impl/tests/cli-forward.md | replace |
| 03 | docs/03-impl/tests/cli-list.md | new-features/03-impl/tests/cli-list.md | replace |
| 03 | docs/03-impl/tests/cli-login.md | new-features/03-impl/tests/cli-login.md | replace |
| 03 | docs/03-impl/tests/cli-login-codex.md | new-features/03-impl/tests/cli-login-codex.md | replace |
| 03 | docs/03-impl/tests/cli-logout.md | new-features/03-impl/tests/cli-logout.md | replace |
| 03 | docs/03-impl/tests/cli-ports.md | new-features/03-impl/tests/cli-ports.md | replace |
| 03 | docs/03-impl/tests/cli-pull.md | new-features/03-impl/tests/cli-pull.md | replace |
| 03 | docs/03-impl/tests/cli-reset.md | new-features/03-impl/tests/cli-reset.md | replace |
| 03 | docs/03-impl/tests/cli-setup.md | new-features/03-impl/tests/cli-setup.md | replace |
| 03 | docs/03-impl/tests/cli-ssh-keys.md | new-features/03-impl/tests/cli-ssh-keys.md | replace |
| 03 | docs/03-impl/tests/cli-start.md | new-features/03-impl/tests/cli-start.md | replace |
| 03 | docs/03-impl/tests/cli-stop.md | new-features/03-impl/tests/cli-stop.md | replace |
| 03 | docs/03-impl/tests/cli-unforward.md | new-features/03-impl/tests/cli-unforward.md | replace |
| 03 | docs/03-impl/tests/cli-upgrade.md | new-features/03-impl/tests/cli-upgrade.md | replace |
| 03 | docs/03-impl/tests/container-tools.md | new-features/03-impl/tests/container-tools.md | replace |
| 03 | docs/03-impl/tests/docker-proxy.md | new-features/03-impl/tests/docker-proxy.md | replace |
| 03 | docs/03-impl/tests/entrypoint.md | new-features/03-impl/tests/entrypoint.md | replace |
| 03 | docs/03-impl/tests/firewall.md | new-features/03-impl/tests/firewall.md | replace |
| 03 | docs/03-impl/tests/images.md | new-features/03-impl/tests/images.md | replace |
| 03 | docs/03-impl/tests/makefile.md | new-features/03-impl/tests/makefile.md | replace |
| 03 | docs/03-impl/tests/portsync.md | new-features/03-impl/tests/portsync.md | replace |
| 03 | docs/03-impl/tests/vm-mode.md | new-features/03-impl/tests/vm-mode.md | replace |
| 03 | docs/03-impl/index.md | new-features/03-impl/index.md | replace |
| 03 | docs/03-impl/features.md | - | 変更なし(理由: 機能の増減が無い。097 は範囲外) |
| 03 | docs/03-impl/infra/local/docker-resources.md | - | 変更なし(理由: 資源の命名規則は動かない。`claude-dev-vm-` は既出) |
| 03 | docs/03-impl/environments/images.md | - | 変更なし(理由: イメージのビルド構成に触れない) |

**SSOT ではないが書き換えるもの**(closure 表の対象外。`/task-close` §5〜§7 が扱う):
`docs/pendings.md`(降格9件 + 陳腐化した既存行の削除)/ `docs/feedbacks/018-mv-atomicity-is-about-the-path-not-the-contents.md`(078)/
`docs/issues/`(削除 24 件 + 残る issue の本文からの参照の付け替え)/ コード
(`claude-dev` / `claude-dev-mac` / `docker-proxy/main.go`)。

## 読む範囲(読了記録)

- 全文読了: 2026-08-11
  - docs/00-requests/acceptances.md@1.4.1
  - docs/00-requests/decisions/auth.md@1.3.0
  - docs/00-requests/decisions/dist.md@1.2.0
  - docs/00-requests/decisions/env.md@1.5.0
  - docs/00-requests/decisions/scope.md@1.2.0
  - docs/00-requests/decisions/sec.md@1.3.0
  - docs/00-requests/request.md@1.4.0
  - docs/00-requests/terminology.md@1.5.0
  - docs/01-requirements/decisions/split.md@1.3.0
  - docs/01-requirements/functional.md@1.15.0
  - docs/01-requirements/non-functional.md@1.7.0
  - docs/01-requirements/system.md@1.2.1
  - docs/01-requirements/usecases.md@1.5.0
  - docs/02-design/architecture.md@1.5.0
  - docs/02-design/contracts/cli-container.md@1.10.0
  - docs/02-design/contracts/docker-api.md@1.1.0
  - docs/02-design/contracts/entrypoint-firewall.md@1.0.1
  - docs/02-design/environments.md@1.4.0
  - docs/02-design/logging.md@1.7.0
  - docs/02-design/relations.md@1.10.0
  - docs/02-design/system.md@2.11.0

## 決定シート(回答済み)

> 回答済み: `docs/tasks/task-issue-sweep/sheet.md`(転記済み)

- チャット回答(2026-08-11)「すべて推奨どおり」 — 対象: 一括(概念1・概念2 / 論点1・論点2・論点3)— 反映先: 下の表の各行

| # | 論点 | 回答 | 反映先 |
|---|---|---|---|
| 概念1 | 「issue を片付ける」の外延(解消 / 空振り / 降格 の3区別。範囲外の 11 件は含まない) | 推奨を承認(チャット一括回答) | 未反映(タスクの進め方の語彙であり仕様ドキュメントに着地しない。除外範囲 = 00〜03 の全層。記録は `docs/histories/` の本タスクのエントリと `docs/pendings.md` 残務9行) |
| 概念2 | 文書整合6件の母集団を 2026-08-11 の実測値で凍結する | 推奨を承認(チャット一括回答) | 未反映(母集団は本 memo.md の調査メモ 12〜15 が持ち、仕様ドキュメントに着地しない。除外範囲 = 00〜03 の全層) |
| 論点1 | issue 004 の降格が `D0-scope-07` の「閉じずに残る」と食い違う → **案A(00 を書き換えて残務へ移す)** | 推奨を承認(チャット一括回答) | `D0-scope-07` / `new-features/00-requests/decisions/scope.md` |
| 論点2 | 031 / 048 / 065 は降格ではなく**解消**する → **案A** | 推奨を承認(チャット一括回答) | `new-features/02-design/environments.md`(031 / 065)/ `new-features/02-design/relations.md`(048) |
| 論点3 | `reset` の削除対象を `claude-dev-vm-*` へ広げる → **案A(広げる)** | 推奨を承認(チャット一括回答) | `new-features/02-design/logging.md`「破壊的操作の削除対象の確認」/ `new-features/03-impl/relations/MODULE-cli-reset.md` |

## 未決点

| # | 未決点 | 帰着 | 検出元 |
|---|---|---|---|
| 1 | 023 の不正値を「中止」と「縮退」のどちらにするか | ドキュメント記載(`FR-env-04-8` = 縮退。`CTR-cli-container`「値の検証で起動を止めることはしない」と `FR-env-04-5` の先例に従う) | ドライラン パス1 |
| 2 | 056 の新しい文言 | ドキュメント記載(`FR-env-03-17` = 「管理ラベルが付く前に起動した可能性がある」。5層すべてで同じ文言に揃えた) | ドライラン パス1 |
| 3 | `docker network create` の標準出力を捨ててよいか | 委任決定(DS-03。`MODULE-cli-common-ensure-infrastructure` に開示行を書いた) | ドライラン パス1 |
| 4 | 047 の VM ボリュームをどう列挙するか | 委任決定(DS-05 の内部構造。`reset` の既存の `claude-dev-chrome-*` の列挙と同じ形にする。実装は フェーズ3) | ドライラン パス2 |
| 5 | `environments.md` の frontmatter 直後の HTML コメントに残る `docs/issues/031` | ドキュメント記載できない(**変更指示は最初の見出しより前の本文を `sections` にも `deletes` にも載せられない**)。`/task-close` の反映時に手で消す(既存の残務と同じ扱い) | ドライラン パス1 |
| 6 | `03-impl/index.md` の 009 / 030 を名指す記述 | ドキュメント記載できない(この節は生成物ではなく `/task-close` §3-4 が手で保守する)。反映時に実測値へ書き直す | ドライラン パス1 |

## 調査メモ

(memo-1.md に移動)

## 質問キュー(未提示)

| # | 論点 | 何が止まるか | 推奨する回答(暫定) |
|---|---|---|---|
| - | なし(フェーズ1のシートに3件を載せた) | - | - |

## タスクリスト

<!-- フェーズ3で /implement が埋める -->

- [ ] 1. **051**: `docker network create` の標準出力も捨てる(4箇所) _要件:_ NFR-ops-05 _Boundary:_ `claude-dev:353,761` / `claude-dev-mac:418,828` _Depends:_ -
- [ ] 2. **088**: compose 既定ネットワークの削除失敗を `_spawned_failed` へ積む _要件:_ FR-env-01-24 _Boundary:_ `claude-dev:1728` / `claude-dev-mac:1737` _Depends:_ - (P)
- [ ] 3. **101**: `reset` の失敗経路で `exit 1` の前にラベル無しコンテナの表示を出す _要件:_ FR-env-03-17 _Boundary:_ `claude-dev:2264` 前後 / macOS 同型 _Depends:_ - (P)
- [ ] 4. **056**: 出力文言を「管理ラベルが付く前に起動した可能性があります」へ揃える _要件:_ FR-env-03-17 _Boundary:_ `claude-dev:1013` ほか / macOS 同型 _Depends:_ - (P)
- [ ] 5. **047**: `reset` の `_rc_volumes` に `claude-dev-vm-*` を足す _要件:_ FR-env-03-14 _Boundary:_ `claude-dev:2059`〜`:2064` / macOS 同型 _Depends:_ 3
- [ ] 6. **023**: `ensure_ssh_bridge` でホスト環境変数の値を 1〜65535 の整数として検証する _要件:_ FR-env-04-8 _Boundary:_ `claude-dev-mac:274` _Depends:_ -
- [ ] 7. **087**: docker-proxy のコンテナ作成経路に `NO-OWNER-LABEL` のログを1行足す _要件:_ FR-env-07-12 _Boundary:_ `docker-proxy/main.go:707` 前後 _Depends:_ -
- [ ] 8. `cd docker-proxy && go vet ./... && go test ./...` が green
- [ ] 9. `diff <(grep -n spawned claude-dev) <(grep -n spawned claude-dev-mac)` 相当で両 OS の同型を確認する

## Definition of Done

<!-- 2026-08-12 のフェーズ3で実測した。HEAD = 99b7b607556ce509e30586acbe66d22ea113117b -->

| # | 項目 | 実行したコマンド | 最終行(逐語) | 判定 |
|---|---|---|---|---|
| 1 | lint | `cd docker-proxy && go vet ./...` | (出力なし。終了コード 0) | ✅ |
| 2 | 単体・結合テスト | `cd docker-proxy && go test ./...` | `ok  	github.com/quvox/claude-dev-env/docker-proxy	0.047s` | ✅ |
| 3 | 受入基準のテストが全て存在し通る | — | — | **対象外**(シェル実装は `SR-32` / `DSN-test-01` により自動テストランナーを持たない。`docker-proxy` の条項は全て `実装済み`。新設した `FR-env-04-8` は `未検証(テスト未実装)` で、これは PASS を塞がない分類である) |
| 4 | 影響する E2E シナリオ | 隔離ハーネス(下の「実機確認の実施状況」) | — | **一部実施**(下表) |
| 5 | コールグラフ再生成 + `callgraph-check.py --to-be` | `CG_OUT=$(python3 .claude/scripts/resolve-callgraph-out.py task-issue-sweep) && python3 .claude/scripts/build-callgraphs.py --out "$CG_OUT"` / `python3 .claude/scripts/callgraph-check.py --to-be task-issue-sweep` | 重大度「高」 **0 件**(シンボル 200 / 辺 88 は変更前と同数) | ✅ |
| 6 | `check-relations.py` | `python3 .claude/scripts/check-relations.py` | `合格: 対称性・参照実在・impl パス・必須項目・機能表との 1:1すべて問題なし。` | ✅ |
| 7 | `check-changeset.py` | `python3 .claude/scripts/check-changeset.py docs/tasks/task-issue-sweep/new-features` | `合格: 不変条件の違反なし` | ✅ |
| 8 | `new-features/` を SSOT へ反映 | — | — | `/task-close` で実施 |
| 9 | `/doc-check` が影響範囲を PASS | 2026-08-11 に PASS(独立レビュー Codex) | — | ✅(C-1 の編集は**実装結果の事実の記録**であり振る舞い・契約・設計を変えていないので PATCH 相当。判定は維持) |
| 10 | `docs/histories/` に記録 | — | — | `/task-close` で実施 |
| 11 | 範囲外の問題を issues / pendings へ記録 | — | — | `/task-close` §5 で残務6件+3件を書く |

### 実機確認の実施状況(E2E)

| 対象 | 確認したこと | 手段 | 結果 |
|---|---|---|---|
| issue 051 | `docker network create` が標準出力へ ID を出さない | 実 Docker(使い捨てネットワーク) | ✅ 修正前 64 文字 → 修正後 0 文字 |
| issue 088 | compose 既定ネットワークの削除失敗が `_spawned_failed` に積まれる | 実 Docker(接続中コンテナで削除を失敗させる) | ✅ 使用中 = failed / 空き = deleted |
| issue 101 | 削除に失敗した実行でもラベル無しコンテナが表示される | 隔離ハーネス(結果ブロックを合成配列で実行) | ✅ 3ケース(失敗+有 / 成功+有 / 失敗+無)とも期待どおり |
| issue 047 | `claude-dev-vm-*` の列挙が実在するボリュームを引く | 実 Docker(`docker volume ls --filter`) | ✅ 実在の2本を引き、無関係な名前は引かない |
| issue 023 | 受理できない値を採用しない | 検証ロジックを切り出して5入力で実行 | ✅ `0` / `70000` / `abc` / 23桁の数字 を拒否、`8022` を受理 |
| issue 087 | 未付与の理由がコンテナ経路でもログに出る | `go test`(新設2本) | ✅ `TestValidateContainerCreate_LogsReasonWhenNotLabelled` / `..._NoReasonLogWhenLabelled` |
| **E2E-01 手順8 の全体** | — | — | **未実施**。`logout` / `reset` を実機で流すとこのホストの稼働中セッション(本セッション自身を含む)と認証・イメージが失われる。**前タスクで人間が承認済みの扱い**(`docs/pendings.md` の既存の残務行)と同じ |
| **E2E-01 手順8-15 の VM 部分 / 手順8-20** | — | — | **未実施**。前者は `/dev/kvm`、後者は macOS 実行機が要る |
| **E2E-03 手順5・6** | — | — | **未実施**(実 Docker でコンテナ内から `docker run` する必要がある)。087 の分は単体テストで代替した |

## 進捗メモ

- 2026-08-12 **フェーズ3 完了**。コード7件を実装(コミット `359e1d4` / `99b7b60`)。`go vet` / `go test` green(単体テスト2本を新設して 39 → 41 本)。`callgraph-check.py --to-be` の重大度「高」0 件、シンボル数・辺の数は変更前と同数(関数の増減なし)。C-1 で変更指示を実装結果へ揃えた: `MODULE-docker-proxy-serve` の `tests:` と `tests/docker-proxy.md` の識別子に新設2本を足し、実装で決めたことを **`[DS-01]` / `[DS-02]` / `[DS-03]` / `[DS-05]` の開示行7本**として4つの relations へ降ろした。**C-2 の決定シート: 追加なし**(問う基準を満たす論点は生じていない)。
- 2026-08-11 **/doc-check(task) 判定: PASS**(反復 1/2)。独立レビュー: **Codex**(`gpt-5.6-sol` / high。指摘7件)。変更指示 51 本のハッシュ `sha256:b7c1ee6b2d27`。closure の版は読了記録のとおり(00〜02 の 21 ファイル)。修正の区分: **PATCH** = system.md の条項数 140→141 / strategy.md の件数表現 / scope.md の issue パス除去 / docker-proxy-serve の reason の行番号 / e2e 手順20 の位置。**MINOR** = テスト文書 19 本の「テスト設計の判断」を `[DS-01]` の開示から「判断なし: <理由>」へ書き直し(帰属の誤りを Codex が指摘)/ `docs/03-impl/index.md`「この層の状態」の変更指示を新設(009・030 の名指しを外し、起票済み欠陥を 9→5 件へ)。
- 2026-08-11 フェーズ2: **03 完了**(relations 10本 + tests 28本 + contracts 2本 = 40本)。`check-changeset.py` **合格(違反なし)**。closure をさらに2件広げた: `docs/03-impl/contracts/docker-api.md`(087)と `docs/03-impl/relations/MODULE-cli-common-destructive.md`(051 の参照)。**issue 077 の母集団を実測で訂正した**(調査メモ25): 機械変換できるのは 127 箇所で、残り 61 箇所は範囲表記を含む散文参照なので対象外とし `pendings.md` の残務へ回す。
- 2026-08-11 フェーズ2: **00 完了**(decisions/scope.md・auth.md・env.md・sec.md の4本)/ **01 完了**(functional.md 1本)/ **02 完了**(logging.md・contracts/cli-container.md・environments.md・relations.md・**system.md** の5本)。**closure を1件広げた**: `FR-env-04-8` を新設したことで CS13 が 02 の要件カバレッジ表に行を要求するため、`docs/02-design/system.md` を「変更なし」から `replace` へ移した(原則3 の適用。同じ降下の中で直した)。次は 03 層。
- 2026-08-11 フェーズ1。36 件の issue を機械で裏取りして仕分け、人間が「混合スイープ」の範囲を承認した。00〜02 を全文読了(21 ファイル)。closure を 48 ファイルで確定し、`sheet.md` に概念2件・論点3件を載せた。次は回答を待って `/task-doc` へ。

## 申し送り事項

- **範囲外として残す 11 件**: 002 / 005 / 010 / 028 / 046 / 055 / 092 / 097(設計判断が要る)と 076 / 079 / 081(キット凍結中)。本タスクの完了後も `docs/issues/` に残る。
- **CS20(issue の `origin_layer` 欠落)は本タスクで 29 件 → 5 件になるが 0 にはならない**。残る5件は範囲外の issue のものなので、それらを扱うタスクが埋める。
- **`/task-close` の反映時に手で行うことが3つある**(いずれも変更指示で表現できない):
  (a) `docs/02-design/environments.md` の frontmatter 直後の HTML コメントに残る `docs/issues/031` の参照を消す(最初の見出しより前の本文は `sections` にも `deletes` にも載せられない)。
  (b) `docs/03-impl/index.md`「この層の状態」の `docs/issues/009` / `030` を名指す2行を実測値へ書き直す(§3-4 が手で保守する節)。
  (c) `docs/pendings.md` P-003 の「独立監査に必要な設定は確定している」を実態(未記入でキットの既定が効く)へ直す(issue 031 の残りの片側。pendings は SSOT ではない)。
- **issue 077 のうち 61 箇所は本タスクの対象外**: `e2e.md`(43)と `cli-logout.md`(8)ほかの散文中の参照で、`FR-env-01` 受入基準 14〜27 のような**範囲表記**を含み条項ID へ機械変換できない。`/task-close` で `pendings.md` の残務へ1行残す。
