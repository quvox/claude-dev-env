---
date: 2026-08-03
type: doc-check
task: task-docs-restructure
summary: 4層体系への移設後の SSOT を ssot モードで検証し、コードとの事実誤り9件を修正して 64 ドキュメントに合格証を発行した
---

# 2026-08-03 `/doc-check ssot task-docs-restructure` — 移設後 SSOT の認証

## 何をしたか

`task-docs-restructure` の `/task-close` が変更指示 175 件を SSOT へ反映した直後の状態に対して、
`/doc-check ssot task-docs-restructure` を fresh-context サブエージェントで実行した。
対象は **SSOT 00〜03 の全 64 版付きドキュメント**(移設直後のため、全件が未検証または失効)。

決定シート3 #2 の「改訂後の独立レンズ監査を `/task-close` 後の `ssot` モードで完走させる」を
この実行で履行した。

## 変更理由

検証指摘の修正。とくに**独立レンズ(Codex `relations` モード)がコードとの事実誤りを検出**し、
Claude が全件コードで裏取りして修正した。

## 独立レンズ

Codex CLI 0.146.0(`-c features.use_legacy_landlock=true` / `--sandbox read-only` / `--ephemeral`)を
**計6本**。初回5本(`docs` 00+01 / `docs` 02 / `docs` 03+E / `readiness` 03 / `relations` コード突合)、
改訂後の再監査1本。全実行で `git status --porcelain` は不変(mutation なし)。

**キット側の不具合を1件回避**: `.claude/skills/codex-audit/audit-schema.json` は OpenAI の構造化出力
要件(全 object の `required` が `properties` 全キーを含むこと)を満たさず `--output-schema` が
400 を返すため、スクラッチパッドに修正版を置いて実行した。**キット本体は変更していない**
(`/kit-improve` 案件。memo の申し送り5 と同一)。

## 更新したドキュメント

| ドキュメント | version | 具体的な変更 |
|---|---|---|
| `docs/03-impl/relations/MODULE-orchestrator-trigger.md` | (層代表) | `stuck_limit` が 0 以下のとき「即座に発火する」と書いていたが、実装は `StuckLimit > 0 &&` を条件にしており**発火しない**。実測どおりに反転させた |
| `docs/03-impl/relations/MODULE-orchestrator-state.md` | (層代表) | `state.json` / `plan.json` 不在時を「空の構造体とエラーを返す」としていたが、実装は `(nil, nil)`。`ArchiveRun(runID)` を実際の**引数なし** `ArchiveRun()` に訂正し、run ID の導出元(`State.RunID`、無ければ UTC 時刻)を明記 |
| `docs/03-impl/relations/MODULE-orchestrator-worker.md` | (層代表) | `Worker.Dispatch(ctx, task)` を実シグネチャ `(ctx, p *Plan, t *Task, feedback string)` へ訂正。**`assumptions.jsonl` を書くのは worker ではなく controller**(`controller.go:637`)である事実を3箇所へ反映 |
| `docs/03-impl/relations/MODULE-orchestrator-mode.md` | (層代表) | `WriteLaunchScript` の第2引数 `prof ModelProfile` の欠落を補い、**原子的に書かれるのは `.sys` / `.prompt` サイドカーだけで `<key>.sh` は `os.WriteFile`** である事実へ訂正。`BrainstormingArgs()` が model/effort を付けない事実を明記 |
| `docs/03-impl/relations/MODULE-orchestrator-plan.md` | (層代表) | `ReadyTasks(plan)` を `ReadyTasks(plan *Plan, limit int)` へ訂正し、`limit <= 0` が上限なしである境界動作を追記 |
| `docs/03-impl/index.md` | 1.0.0 → **1.1.0** | 上記5本の relations が意味を変えたため、層の代表として MINOR |
| `docs/01-requirements/non-functional.md` | 1.0.0 → 1.0.1 | `NFR-avail-01` / `NFR-sec-01` が旧ID `E2E-5` / `E2E-3` を参照していた。新ID `E2E-05` / `E2E-03` へ |
| `docs/00-requests/decisions/dist.md` | 1.0.0 → 1.0.1 | 同上(`E2E-6` → `E2E-06`) |
| `docs/03-impl/tests/orchestrator.md` | 1.0.0 → 1.0.1 | 同上(`E2E-4` / `E2E-5` → `E2E-04` / `E2E-05`) |
| `docs/00-requests/decisions/sec.md` | 1.0.0 → 1.0.1 | `D0-sec-02` のガードレールが「認証情報の実体をコンテナへ渡さない」とだけ書かれ、独立レンズが `D0-auth-03`(認証の共有ボリューム経由の持ち回り)との矛盾と読み違えた。**対象がホスト資産の受け渡しに限る**ことを明記(意味は不変) |
| relations 5本の `tests` | (層代表) | 実在しないテスト関数名 8 件を現行名へ(例: `TestReadyTasks_Basic` → `TestReadyTasks_DependencyResolution`) |
| SSOT 00〜03 の 64 ファイル | — | `verified` を発行(`request.md` 1.2.0 と `system.md` 2.0.0 の失効した合格証は差し替え) |

## 旧ID → 新ID 対応表(移設に伴う再採番)

`task-docs-restructure` の memo が確定させたもの。SSOT からタスクディレクトリが消える前にここへ転記する。

### 決定台帳(旧 `decisions.md` の `D-nn` → `decisions/<category>.md` の `D0-*`)

| 旧 | 新 | 旧 | 新 | 旧 | 新 |
|---|---|---|---|---|---|
| D-1 | D0-sec-06 | D-10 | D0-env-04 | D-19 | D0-scope-01 |
| D-2 | D0-sec-07 | D-11 | D0-dist-02 | D-20 | D0-scope-06 |
| D-3 | D0-auth-03 | D-12 | D0-orch-09 | D-21 | D0-orch-16 |
| D-4 | D0-sec-08 | D-13 | D0-orch-10 | D-22 | D0-orch-17 |
| D-5 | D0-sec-09 | D-14 | D0-orch-11 | D-23 | D0-env-07 |
| D-6 | D0-env-01 | D-15 | D0-orch-12 | D-24 | D0-env-05 |
| D-7 | D0-env-02 | D-16 | D0-orch-13 | D-25 | D0-env-06 |
| D-8 | D0-sec-10 | D-17 | D0-orch-14 | D-26 | D0-dist-03 |
| D-9 | D0-env-03 | D-18 | D0-orch-15 | D-27 | D0-dist-04 |

新設(旧IDなし。relations が根拠として参照していた実装判断を委任として明文化。計 20 件、すべて区分「委任」):
`D0-scope-02`〜`D0-scope-05` / `D0-auth-01` / `D0-auth-02` / `D0-sec-01`〜`D0-sec-05` /
`D0-dist-01` / `D0-orch-01`〜`D0-orch-08`。

### 要件・その他

| 旧 | 新 |
|---|---|
| core 要件1〜12 | `FR-env-01` 〜 `FR-env-12`(同順) |
| orchestration 要件12〜20 | `FR-orch-01` 〜 `FR-orch-09`(同順) |
| core / orchestration の非機能要件の表 | `NFR-perf-01`〜03 / `NFR-avail-01`〜03 / `NFR-sec-01`〜03 / `NFR-ops-01`〜04 / `NFR-scale-01`〜02(6分類へ再編。法令は「対象外」) |
| 旧 `_steering/tech.md` の技術前提 | `SR-01`〜`SR-05`(必須制約)/ `SR-10`〜`SR-15` / `SR-20`〜`SR-24` / `SR-30`〜`SR-34` |
| 受入シナリオ AS-1 〜 AS-6 | `AC-01` 〜 `AC-06`(同順) |
| UC-1 / 2 / 3 / 6(core)・UC-4 / 5(orchestration) | `UC-01` / `UC-02` / `UC-03` / `UC-06` / `UC-04` / `UC-05` |
| E2E-1 〜 E2E-6 | `E2E-01` 〜 `E2E-06`(同順) |
| 契約(旧 `system.md` の無名5節) | `CTR-cli-container` / `CTR-entrypoint-firewall` / `CTR-docker-api` / `CTR-cli-orchestrator` / `CTR-orchestrator-prompt` |
| モジュール分割定義 14 モジュール | 29 モジュール(cli をサブコマンド単位へ分割し `MOD-cli-common` を新設。`cli-mac` は解体して同名サブコマンドへ相乗り。`devcontainer` と `ghcr-workflow` は `DSN-mod-05` により分割定義から除外) |
| 要求(旧 `request.md` §5 やること 8項目) | `RQ-env-01`〜06 / `RQ-orch-01` / `RQ-dist-01` |

## 機械検査(最終)

| スクリプト | 結果 |
|---|---|
| `build-callgraphs.py --check` | 最新 |
| `cluster-features.py --check` | 最新 |
| `callgraph-check.py` | 指摘 40 件・**重大度「高」ゼロ**(中3 / 低17 / 参考20) |
| `check-contracts.py` | 合格(02: 5 / 03: 5) |
| `check-relations.py` | 合格(82 ファイル / 82 ID) |
| `build-index.py --check` | 差分なし |
| `git diff --stat -- . ':!docs'` | 空(**コードは1行も変更していない**) |

## 起票した issue

- `docs/issues/009-modify-relations-prose-signatures-drift-from-code.md`(中) —
  relations 本文の関数シグネチャが実コードと食い違うものが約 27 件残る。`ctx` の省略を許す規約が
  `.claude/directions/relations.md` に無いことが原因で、**規約の選択は人間の判断**として起票した。
