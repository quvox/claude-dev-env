---
slug: codex-sandbox-disabled-in-container
layer: task
title: Codex サンドボックス無効化の既定設定を entrypoint に実装する（D-27 ⑥）
date: 2026-07-31
source:
  - docs/03-impl/entrypoint.md
history: docs/histories/2026-07-31-codex-sandbox-disabled-in-container.md
---

# タスク:Codex サンドボックス無効化の既定設定を entrypoint に実装する（D-27 ⑥）

## 目的

`scripts/entrypoint-claude.sh` に、codex の `config.toml` が不在のときだけ
`sandbox_mode = "danger-full-access"` / `approval_policy = "never"` を生成する処理を追加する。
D-27 ⑥ の文書反映（00→01→02→03）は完了済みでコードだけが未反映のため、その差分を埋める。

## 前提（ゲート状況の記録）

`/implement` の Phase A ゲートは「対象 03-impl と source チェーンが全て verified」を要求するが、
着手時点で `docs/03-impl/entrypoint.md` は **check B（03-impl⇄コード）不合格で合格証なし**だった。

- 上流は全て verified: `00-requests/*`(request 1.1 / decisions 1.6 / glossary 1.2 / acceptance 1.2)、
  `01-requirements/core.md` 1.8.0、`02-design/system.md` 1.8.0。
- entrypoint.md の剥落理由は「文書が誤っている」ではなく「**コードが未了**」であり、
  それが本作業の対象そのもの。
- よってゲートの趣旨（未検証の仕様から実装しない）は満たされていると判断し、停止せず着手した。
  根拠は `docs/knowledge/docs-ahead-of-code-deadlocks-doc-check.md`、および人間が是認済みの
  同種判断（`docs/feedback/log.md` [5]・[7]）。完了後に `/doc-check entrypoint` で循環を閉じる。

## タスク

- [ ] 1. `scripts/entrypoint-claude.sh` に codex `config.toml` の既定生成を追加する
      （`settings.json` 生成ブロックの直後。`$LOCAL_CODEX/config.toml` 不在時のみ 2 行を書き、
      所有権を `$USERNAME` へ。存在時は内容を読まず一切変更しない）
      _要件: core/12-4, 12-5, 12-6_ _Boundary: scripts/entrypoint-claude.sh のみ_ _Depends: なし_
- [ ] 2. 実機確認（既定生成・既存不変）を行う
      （`config.toml` 不在のコンテナで生成されること／利用者が書き換えた `config.toml` が
      再起動後も不変であることを、実コンテナで観測する）
      _要件: core/12-5, 12-6_ _Boundary: 検証のみ（コード変更なし）_ _Depends: 1_

## Definition of Done

以下がすべて満たされたときに完了とする。**ビルドが通っただけでは完了ではない。**

- [ ] 上記タスクの全チェックが完了している
- [ ] lint: `go vet ./...`（各 Go モジュール）がエラーなしで通る。Bash には自動 lint が無いため
      `bash -n scripts/entrypoint-claude.sh` を代替の静的検査として実施する
- [ ] 単体・結合テスト: `cd docker-proxy && go test ./...` と
      `cd orchestrator && go test -mod=vendor ./...` が全パスする
- [ ] 今回対象の受け入れ基準（core/12-4・12-5・12-6）に対応する検証が存在し、パスする
      （シェル系は自動テストなし＝実機確認。03-impl/entrypoint.md のテスト対応表の 2 行に対応）
- [ ] 影響する E2E シナリオ（E2E-6）の確認状況を記録する。E2E-6 はデバイス認証のブラウザ操作を
      伴い原理的に無人自動化できないため、実施可否を明記する
- [ ] 対象モジュールの 03-impl（entrypoint.md）が実装結果と一致するよう更新されている
      （テスト対応表含む）
- [ ] history エントリ `2026-07-31-codex-sandbox-disabled-in-container.md` の affected に、
      今回更新した全ドキュメントの version 遷移が記録されている
- [ ] この作業中に発生した 質問/修正/委任判断 がすべて `docs/feedback/log.md` に記録されている

## 進捗メモ

- 2026-07-31 作業開始。`/doc-check full` が指摘1（高）として検出した「文書は D-27 ⑥ を記述
  しているがコードに実装が無い」を埋める作業。`grep -n "sandbox_mode\|approval_policy\|config.toml"
  scripts/entrypoint-claude.sh` は 2026-07-31 時点でコメント 1 行（L169）のみで、生成処理は不在。
- 実装位置は `scripts/entrypoint-claude.sh` の `settings.json` 生成ブロック（L237-241）直後。
  文書（entrypoint.md 手順10）が「同じ考え方で codex 側も既定設定を置く」と書いている位置に対応。
- ゲート判断（上記「前提」）はフィードバックログへ 3 回目の再発として記録する。
