---
id: 2026-08-03-docs-restructure
date: 2026-08-03
task: task-docs-restructure
origin_layer: 00
issue: なし
summary: 旧3フェーズ体系で書かれた docs/ を 4層ドキュメント駆動開発の構造へ全面移設した(コードは1行も変更していない)
---

# 2026-08-03 ドキュメント体系の新構造への刷新

## 変更理由

`CLAUDE.md` と `.claude/directions/` `.claude/templates/` `.claude/skills/` を
**4層ドキュメント駆動開発**(00-requests / 01-requirements / 02-design / 03-impl、4フェーズ、
SSOT 不変則)へ書き換えたため、旧3フェーズ体系で書かれた `docs/` が規範と一致しなくなった。
起点層は 00(要求の見出し規定と ID 体系そのものが変わる)。

**システムの振る舞いは1バイトも変えていない。** 03-impl はコードから再導出した。

## 変更内容の要約

- 00〜03 の全層を新構造・新ID体系へ移設した。変更指示 **175 件**(add 145 / replace 4 / delete 26)を
  `/task-close` で1回だけ SSOT へ反映した。
- **03-impl をコードから再導出した**: 機能表 82 機能(人間が合意)、`callgraphs/`(ツール生成)、
  `feature-graph.md`(ツール生成)、`relations/MODULE-*.md` 82 本、`contracts/` 5 件、
  `tests/` 32 件、`environments/` 1 件、`infra/local/` 2 件。
- 02 のモジュール分割定義を 14 → **29 モジュール**へ変更した(CLI をサブコマンド単位に割り、
  `MOD-cli-common` を新設。`cli-mac` は解体して同名サブコマンドへ相乗り。`devcontainer` と
  `ghcr-workflow` はコールグラフに入口が無いため分割定義から外した)。
- 旧構造を撤去した: `_steering/`(3)/ `_templates/`(13)/ `knowledge/`(16)/ `feedback/`(1)/
  `WORKFLOW-GUIDE.md` / `RATIONALE.md` / `03-impl/<module>.md` 14 本。
- 新設した運用ファイル: `docs/issues/`(9件)/ `docs/pendings.md`(P-001〜P-003)/
  `docs/feedbacks/`(12件)。旧形式タスク4件は issue へ降格した。

### 本タスク中に投入したキット側の変更(本タスクの範囲外・`/kit-improve` で実施)

移設の前提が成立しなかったため、途中2回凍結して抽出器を用意した。

| ID | 内容 |
|---|---|
| `KIT-shell-make-extraction` | shell / Makefile の抽出器(Tier 3)を追加し、Go の `func main` もエントリポイント化した |
| `KIT-shell-comment-strip` | `${#arr[@]}` の `#` をコメント開始と誤認して関数範囲が暴走する不具合を修正 |
| `KIT-shell-heredoc-tracking` | ヒアドキュメント本文を通常のコードとして扱う不具合を修正 |

投入前は **本リポジトリの実エントリポイントが1件も機械に見えていなかった**
(bash 36 サブコマンド / `scripts/*.sh` 10 本 / Makefile 19 ターゲット / `func main` 2 件)。
投入後: shell 130 シンボル / 168 辺 / 51 入口、make 19 / 22 / 19、go 219 / 399 / 2。

## 旧ID → 新ID 対応表

### 決定台帳(旧 `00-requests/decisions.md` の `D-nn` → `00-requests/decisions/<category>.md` の `D0-*`)

| 旧 | 新 | 区分 | 旧 | 新 | 区分 |
|---|---|---|---|---|---|
| D-1 | D0-sec-06 | 決定 | D-15 | D0-orch-12 | 決定 |
| D-2 | D0-sec-07 | 決定 | D-16 | D0-orch-13 | 決定 |
| D-3 | D0-auth-03 | 決定 | D-17 | D0-orch-14 | 決定 |
| D-4 | D0-sec-08 | 決定 | D-18 | D0-orch-15 | 決定 |
| D-5 | D0-sec-09 | 決定 | D-19 | D0-scope-01 | 委任 |
| D-6 | D0-env-01 | 決定 | D-20 | D0-scope-06 | 委任 |
| D-7 | D0-env-02 | 決定 | D-21 | D0-orch-16 | 要確認 |
| D-8 | D0-sec-10 | 決定 | D-22 | D0-orch-17 | 要確認 |
| D-9 | D0-env-03 | 決定 | D-23 | D0-env-07 | 要確認 |
| D-10 | D0-env-04 | 決定 | D-24 | D0-env-05 | 決定 |
| D-11 | D0-dist-02 | 決定 | D-25 | D0-env-06 | 決定 |
| D-12 | D0-orch-09 | 決定 | D-26 | D0-dist-03 | 決定 |
| D-13 | D0-orch-10 | 決定 | D-27 | D0-dist-04 | 決定 |
| D-14 | D0-orch-11 | 決定 | — | — | — |

**新設(旧IDなし)**: `03-impl/relations/` が根拠として参照していた実装判断を委任として明文化した
20 件 — `D0-scope-02`〜`D0-scope-05` / `D0-auth-01` / `D0-auth-02` / `D0-sec-01`〜`D0-sec-05` /
`D0-dist-01` / `D0-orch-01`〜`D0-orch-08`。すべて区分「委任」。

### 要件

| 旧 | 新 |
|---|---|
| `01-requirements/core.md` 要件1〜12 | `FR-env-01` 〜 `FR-env-12`(番号は同順) |
| `01-requirements/orchestration.md` 要件12〜20 | `FR-orch-01` 〜 `FR-orch-09`(番号は同順) |
| core / orchestration の非機能要件の表 | `NFR-perf-01〜03` / `NFR-avail-01〜03` / `NFR-sec-01〜03` / `NFR-ops-01〜04` / `NFR-scale-01〜02`(6分類へ再編。法令は「対象外」) |
| 旧 `_steering/tech.md` の技術前提 | `SR-01`〜`SR-05`(必須制約)/ `SR-10`〜`SR-15` / `SR-20`〜`SR-24` / `SR-30`〜`SR-34` |

### その他

| 旧 | 新 |
|---|---|
| 受入シナリオ `AS-1` 〜 `AS-6` | `AC-01` 〜 `AC-06`(同順) |
| `UC-1` / `UC-2` / `UC-3` / `UC-6`(core) | `UC-01` / `UC-02` / `UC-03` / `UC-06` |
| `UC-4` / `UC-5`(orchestration) | `UC-04` / `UC-05` |
| `E2E-1` 〜 `E2E-6` | `E2E-01` 〜 `E2E-06`(同順) |
| 旧 `02-design/system.md` の無名5契約 | `CTR-cli-container` / `CTR-entrypoint-firewall` / `CTR-docker-api` / `CTR-cli-orchestrator` / `CTR-orchestrator-prompt` |
| モジュール分割定義 14 モジュール | 29 モジュール(上記のとおり) |
| 旧 `request.md` §5 やること 8 項目 | `RQ-env-01`〜`RQ-env-06` / `RQ-orch-01` / `RQ-dist-01` |

## 更新したドキュメント

反映で作成・置換・削除したものだけを層ごとに示す(新規はすべて `version: 1.0.0`)。

| ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|
| docs/00-requests/request.md | 1.1.0 → 1.2.0 | 旧 §1〜§8 を新見出し規定へ再配置し、要求へ `RQ-<category>-nn` を付与(意味は不変) |
| docs/00-requests/acceptances.md | 新規 1.0.0 | 旧 `acceptance.md` を改名し `AC-01`〜`AC-06` を付与。AC-03 に「この保証の限定」を追記 |
| docs/00-requests/terminology.md | 新規 1.0.0 | 旧 `glossary.md` を改名し「英語表記(識別子)」列を新設 |
| docs/00-requests/decisions/{auth,dist,env,orch,scope,sec}.md | 新規 1.0.0 ×6 | 旧 `decisions.md` の D-1〜27 をカテゴリ別に分割し、委任 20 件を新設 |
| docs/01-requirements/functional.md | 新規 1.0.0 | 旧 core / orchestration を統合し `FR-env-*` / `FR-orch-*` へ再採番。受け入れ基準を EARS 化 |
| docs/01-requirements/non-functional.md | 新規 1.0.0 | 6分類の非機能要件を既存記述から抽出 |
| docs/01-requirements/system.md | 新規 1.0.0 | 旧 `_steering/tech.md` の技術前提を `SR-*` として要件化 |
| docs/01-requirements/usecases.md | 新規 1.0.0 | `AC-*` を `UC-01`〜`UC-06` へ形式化(E2E の唯一の上流) |
| docs/02-design/architecture.md | 新規 1.0.0 | 旧 `system.md` から全体構成・データモデル・インフラ設計・アーキ級の設計判断を分離 |
| docs/02-design/system.md | 1.9.0 → 2.0.0 | H1 を「モジュール分割・テスト戦略・UI設計」へ改題。分割定義を 14 → 29 モジュールへ全面変更し、`SR-*` のカバレッジ表を新設 |
| docs/02-design/relations.md | 新規 1.0.0 | 設計が想定する連携 `PLAN-*` 63 件を新設 |
| docs/02-design/contracts/*.md(5) | 新規 1.0.0 ×5 | 旧 `system.md` の散文契約を独立ファイル化し `CTR-*` を付与 |
| docs/02-design/environments.md | 新規 1.0.0 | lint/テスト/**ドキュメント整合検査 7 コマンド**の厳密な文字列と Codex 実行設定 |
| docs/02-design/logging.md | 新規 1.0.0 | 3系統(端末出力・常駐プロセス・追記型ログ)のログ仕様 |
| docs/03-impl/index.md | 1.0.0 → 1.1.0 | 03-impl 層の代表。層の状態・02 との差分・コールグラフの実測値を記録 |
| docs/03-impl/features.md | 版を持たない | 82 機能の境界の定義(人間が合意) |
| docs/03-impl/relations/MODULE-*.md(82) | 版を持たない | コードから導出。層の代表 `index.md` がまとめて認証する |
| docs/03-impl/contracts/*.md(5) | 新規 1.0.0 ×5 | 02 と同一 ID。実装のバリデーション・既定値・拒否条件を定義箇所つきで記述 |
| docs/03-impl/tests/*.md(32) | 新規 1.0.0 ×32 | 旧 `e2e.md` を strategy / e2e / モジュール別 30 件へ分割。受入基準 163 件を重複なく配分 |
| docs/03-impl/environments/images.md | 新規 1.0.0 | イメージのステージ構成とビルド引数(旧 `devcontainer.md` の一部) |
| docs/03-impl/infra/local/{docker-resources,ghcr}.md | 新規 1.0.0 ×2 | Docker リソースの命名規則と GHCR 配布構成(旧 `ghcr-workflow.md` の一部) |
| docs/README.md / docs/ONBOARDING.md | 版を持たない | 新4層体系の索引と説明資料へ書き直し |
| (削除)docs/00-requests/{acceptance,glossary,decisions}.md | — | 新ファイルへ移設済み |
| (削除)docs/01-requirements/{core,orchestration}.md | — | `functional.md` / `non-functional.md` / `usecases.md` へ移設済み |
| (削除)docs/03-impl/<module>.md 14 本 | — | `relations/` `contracts/` `tests/` `environments/` `infra/` へ解体 |
| (削除)docs/_steering/ / docs/_templates/ / docs/knowledge/ / docs/feedback/ | — | それぞれ 01/02、`.claude/templates/`、02 の設計判断の理由欄、`docs/feedbacks/` へ吸収 |
| (削除)docs/WORKFLOW-GUIDE.md / docs/RATIONALE.md | — | CLAUDE.md §1〜3 との二重管理 |

## 実装したもの

**なし。本タスクはコードを1行も変更していない**(`git diff --stat -- . ':!docs'` が空であることで確認)。

## 機能間連携仕様書の変化

| 種別 | ID | 内容 |
|---|---|---|
| 追加 | MODULE-cli-*(20) | `claude-dev` / `claude-dev-mac` の 18 サブコマンド + `ssh-keys reset` の分岐 + `code` |
| 追加 | MODULE-cli-common-*(11) | 全サブコマンドがファンインする共有基盤関数(`container_name` / `is_running` 等) |
| 追加 | MODULE-makefile-*(19) | Makefile の各ターゲット |
| 追加 | MODULE-orchestrator-*(18) | 単一バイナリ内をファイル境界=責務境界で分割 |
| 追加 | MODULE-vm-mode-*(4) / MODULE-hooks-*(2) / MODULE-sample-project-*(2) | |
| 追加 | MODULE-entrypoint-claude / MODULE-firewall-init / MODULE-docker-proxy-serve / MODULE-portsync-dood / MODULE-container-tools-wait-limit-reset | |
| 削除 | (旧構造に機能単位の仕様書は存在しない) | 旧 `03-impl/<module>.md` 14 本はモジュール単位の散文だった |

**旧構造との差**: 旧 14 ファイルはモジュール単位の散文で、呼び出し関係・契約・要件との対応を
機械検査できなかった。新 82 本は `impl` / `callers` / `callees` / `contracts` / `design` /
`requirements` / `tests` をフロントマターに持ち、`check-relations.py` と `callgraph-check.py` が
コードとの一致を検査する。

### 反映後の機械検査(2026-08-03 実測)

| 検査 | 結果 |
|---|---|
| `build-callgraphs.py --check` | 最新 |
| `cluster-features.py --check` | 最新(機能 82 / 辺 121(確定 114 / 候補 7)/ 共有関数 1 / 未到達 15) |
| `callgraph-check.py` | 指摘 40 件・**重大度「高」ゼロ**(中3 / 低17 / 参考20) |
| `check-relations.py` | 合格(82 ファイル / 82 ID) |
| `check-contracts.py` | 合格(02: 5 件 / 03: 5 件。REST API なし) |
| `build-index.py --check` | 差分なし |
| `relations-coverage.py` | **終了コード 1**。未記載 30 件はすべて `scan-entrypoints.py` の Go `switch` 誤検出(設定キー `max_workers` 等・TUI のキー入力 `p`/`d`/`i`・JSON の型識別子・git のサブコマンド文字列)で、実在する入口ではない |

## 認証

`/doc-check ssot task-docs-restructure` を fresh-context サブエージェントで実行し **PASS**。
SSOT 00〜03 の **64 ドキュメント**に合格証を発行した(別エントリ
`2026-08-03-doc-check-ssot-certification-after-restructure.md` に詳細)。
独立レンズは **Codex 6 本**(docs 3 / readiness 1 / relations ⇄ コード 1 / 改訂後の再監査 1)を完走した。

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 新規 issue | docs/issues/001-modify-orchestrator-test-only-symbols.md | orchestrator の未到達7シンボル(テストからのみ参照) |
| 新規 issue | docs/issues/002-modify-claude-dev-yaml-is-overwritten-wholesale.md | `.claude-dev.yaml` が全面上書きされる |
| 新規 issue | docs/issues/003-future-macos-orchestrator-scope.md | macOS の `orchestrate` にコントローラの生存判定が無い(旧形式タスクの降格) |
| 新規 issue | docs/issues/004-modify-03-impl-lacks-reimplementation-depth.md | 03-impl の深度不足 約20件 |
| 新規 issue | docs/issues/005-modify-docker-proxy-relays-unparseable-bodies.md | 解釈できないボディを中継する(AC-03 の保証の穴) |
| 新規 issue | docs/issues/006-modify-e2e-procedures-lack-reproducibility.md | E2E 手順の再現性不足(旧形式タスクの降格) |
| 新規 issue | docs/issues/007-future-heterogeneous-vendor-reviewer.md | 異種ベンダーのレビュアー(旧形式タスクの降格) |
| 新規 issue | docs/issues/008-modify-spec-depth-contracts-and-wording.md | 契約と用語の深度(旧形式タスクの降格) |
| 新規 issue | docs/issues/009-modify-relations-prose-signatures-drift-from-code.md | relations 本文の関数シグネチャ約27件が実コードと不一致(省略記法の規約が無い) |
| 棚上げ | docs/pendings.md P-001 | E2E スクリプトをコールグラフの解析対象外に置く |
| 棚上げ | docs/pendings.md P-002 | PR での CI 自動実行を導入しない |
| 棚上げ | docs/pendings.md P-003 | QA レーンの各設定を未定のままにする(ブラウザ排他ロックを含む) |
| 気づき | docs/feedbacks/001〜011 | 旧 `feedback/log.md` 6 件と `knowledge/` 3 件の変換 + 本タスクで得た 2 件 |
| 気づき | docs/feedbacks/012 | バックグラウンドのサブエージェントと同じ作業ツリーで並行作業しない |
| 解消した issue | なし | 本タスクは issue 起点ではない(`issue: なし`) |

### キット側に残した欠落(`/kit-improve` 案件。`.claude/improvements/` は `/kit-improve` だけが書く)

| # | 内容 |
|---|---|
| 1 | **`scan-entrypoints.py` が Go の `case "X":` をすべて入口とみなす。** 本リポジトリで 30 件の誤検出を生み、`relations-coverage.py` が構造的に合格できない |
| 2 | **make 抽出器がレシピ行の `make <target>` を文脈なしで再帰 make とみなす**(`cgx/make_regex.py:107`)。`@echo "  make setup ..."` の案内文から実在しない辺が 13 本立つ |
| 3 | **Dockerfile と GitHub Actions の抽出器が無い。** この2つはモジュールにできず(`DSN-mod-05`)、機能表を手で書くことになる |
| 4 | **shell 抽出器が既定分岐(`help\|*)`)を入口にしない。** `Makefile::help` は入口になるのに CLI の `help` はならない非対称が残る |
| 5 | **`.claude/skills/codex-audit/audit-schema.json` が OpenAI の構造化出力要件を満たさない**(`findings.items.required` に `related` が無い)。`codex exec --output-schema` が `invalid_json_schema` で 400 を返す。本タスクではスクラッチパッドの修正版で回避した |
| 6 | **変更指示(change-set)にディレクトリを削除する記法が無い。** 本タスクでは `target` にディレクトリパスを書き、本文に対象ファイルを全列挙し停止条件を添える形で回避した |
| 7 | **`close-task.py` の反映ゲート(a)と `callgraphs/` の扱いが衝突する。** ゲートは `new-features/` 配下の全 `.md` に `target:` を要求するが、記法は「`callgraphs/` と `feature-graph.md` の変更指示は書かない」と定めている |
| 8 | **監査を起動するサブエージェントのツールが制限されていない。** 読み取り専用と指示しても書き換えうる(本タスクで実害が発生し `docs/feedbacks/012` に記録) |

## 完了時の人間の判断(決定シート4。2026-08-03)

タスクディレクトリの削除ゲート(`close-task.py`)が2点で拒否したため、人間に判断を仰いだ。**両方 A**。

| # | 論点 | 回答 |
|---|---|---|
| 1 | DoD の「`relations-coverage.py` が合格」を満たせない(未記載30件は全件が `scan-entrypoints.py` の Go `switch` 誤検出で、実在する入口の漏れはゼロ) | **DoD 項目を「誤検出30件を除いてゼロ」へ訂正**してチェックし、ツール側の修正は `/kit-improve`(上記「キット側に残した欠落」#1)へ回す |
| 2 | ゲート(b) が22件を「ファイルが存在しない」で落とす(memo の影響範囲と `source:` が移設前の旧 SSOT パスを指しており、それらは本タスクが `change: delete` で意図的に削除した) | **影響範囲と `source:` を反映後の新 SSOT パスへ更新**してゲートを再実行する。旧→新の対応は本エントリの対応表が保持する |

再実行後、(a) 反映済み 175/175 / (b) 合格証すべて有効 / (c) DoD 全16項目 / (d) `check-relations.py` 合格 —
**4条件すべて通過し、`docs/tasks/task-docs-restructure/` を削除した。**

### この2点が示したキットの限界(`/kit-improve` 案件。上記 #1 に加えて)

**`close-task.py` のゲート(b) は「このタスクが意図的に削除した SSOT」を表現できない。** 移設タスクでは
影響範囲の旧パスが必ず消えるため、閉じる直前に影響範囲を書き換える手作業が発生する。
ゲート側が「削除指示が反映済みの `target` は合格証を要求しない」と扱えるのが本来の姿である。
