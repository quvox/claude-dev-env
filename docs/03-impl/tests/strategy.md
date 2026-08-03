---
id: strategy
scope: 全体
version: 1.0.0
updated: 2026-08-03
source:
  - docs/02-design/system.md
  - docs/02-design/environments.md
summary: テストのレベル別実行方法・状態列の語彙・受入基準の配分規約
keywords: [テスト, 方針]
verified:
  at: 2026-08-03
  version: 1.0.0
  against:
    - doc: docs/02-design/system.md
      version: 2.0.0
    - doc: docs/02-design/environments.md
      version: 1.0.0
---

# テスト実装仕様 — 実行方法と共通の流儀

## レベル別の実行方法

| レベル | ツール | コマンド | 実行環境 | 所要時間の目安 |
|---|---|---|---|---|
| 単体(docker-proxy) | `go test` | `cd docker-proxy && go test ./...` | ホストまたはコンテナ内。外部接続なし | 数秒 |
| 単体(orchestrator) | `go test` | `cd orchestrator && go test -mod=vendor ./...` | 同上 | 十数秒 |
| 単体(自己検証題材) | `pytest` | `cd examples/orch-sample && pytest` | 同上 | 数秒 |
| lint | `go vet` | `go vet ./...`(各 Go モジュールのディレクトリで) | 同上 | 数秒 |
| 結合 | `go test` + 実機確認 | 上記2つの `go test` に含まれる。シェル側の契約は実機確認 | Go は単体と同じ。実機分はコンテナ起動を伴う | Go は単体に含まれる |
| E2E | 実機操作 + 自己検証題材 | 自動テストランナーは無い。`make orch-sample` で題材を配置し `claude-dev orchestrate` で実走する | 実際のホストとコンテナ。実 tmux・実エージェント | 手順による(E2E-04 は数十分) |

**Bash と Makefile には自動テストランナーを設けていない**(`SR-32` / `DSN-test-01`)。
動作確認は実機で行い、手順は `e2e.md` が持つ。静的検査として `bash -n` による構文確認だけは
実施できる。

## 絞り込んで実行する方法

| やりたいこと | コマンド |
|---|---|
| 1パッケージだけ | `cd docker-proxy && go test ./...`(単一パッケージ構成のため全体と同じ) |
| 1テストだけ(docker-proxy) | `cd docker-proxy && go test -run TestValidateContainerCreate_BlocksHostBind ./...` |
| 1テストだけ(orchestrator) | `cd orchestrator && go test -mod=vendor -run TestArchiveRun_MovesNotDeletes ./...` |
| 前方一致でまとめて | `cd orchestrator && go test -mod=vendor -run 'TestDash.*' ./...` |
| 題材の1テストだけ | `cd examples/orch-sample && pytest -k mathkit` |
| シェルの構文確認だけ | `bash -n claude-dev` / `bash -n scripts/entrypoint-claude.sh` |

## テストデータの準備と後始末

| レベル | 準備 | 後始末 | 冪等か |
|---|---|---|---|
| 単体(Go) | テスト内で組み立てる。ファイルを使うものは一時ディレクトリを作る | Go のテスト機構が一時ディレクトリを破棄する | 冪等 |
| 単体(Python) | テスト内で組み立てる | 不要 | 冪等 |
| 結合(Go) | 同上。外部サービスへ接続しない | 同上 | 冪等 |
| 結合・E2E(実機) | 専用のプロジェクトディレクトリを作って `claude-dev start` する。オーケストレーターは `make orch-sample` で使い捨ての作業コピーを配置する | `claude-dev stop` でコンテナと compose 生成物を片付ける。題材は `make orch-sample-clean` で初期化する | 配置は冪等(再初期化は明示指定が必要) |

**実機確認は既存の作業用プロジェクトで行わない。** 認証・ポート・compose の生成物が混ざるため、
必ず専用のディレクトリを作る。

## フィクスチャ・ヘルパの流儀

| 用途 | 使うもの | 場所 |
|---|---|---|
| Docker API のリクエストを組み立てる | テストローカルのヘルパー | `docker-proxy/main_test.go` |
| bind の書き換えを検証する | 同上 | `docker-proxy/binds_test.go` |
| 運用状態の往復(保存 → 読み込み)を検証する | 一時ディレクトリと状態構造体 | `orchestrator/state_test.go` |
| TUI の描画と入力を検証する | bubbletea のモデルへ直接メッセージを送る | `orchestrator/dashtui_test.go` |
| プロンプト生成を検証する | ポリシーとモードの構造体 | `orchestrator/policy_test.go` / `orchestrator/mode_test.go` |
| 自己検証題材 | 題材のテスト一式 | `examples/orch-sample/` |

新しいテストは、対象と同じディレクトリに `<対象>_test.go` として置き、既存のテーブル駆動の
書き方に合わせる。

## 命名と配置の規約

| 種別 | 配置 | 命名 |
|---|---|---|
| 単体(Go) | 対象と同じパッケージ | `<対象>_test.go` / `Test<対象>_<条件>` |
| 結合(Go) | 同上(実行環境が単体と同じため分けない) | 同上 |
| 単体(Python) | 題材の中 | `test_*.py` |
| E2E(手順) | 自動テストは無い。手順を文書として持つ | `docs/03-impl/tests/e2e.md` の `E2E-nn` |

## 状態列の語彙の定義

`build-index.py` が集計するため、対応表の状態列は次の3語だけを使う。

| 語 | この体系での意味 |
|---|---|
| `実装済み` | 自動テストが存在し、上記のコマンドで実行できる |
| `未検証(テスト未実装)` | 自動テストが無い。**実機確認の手順が定義されていてもここに入る**(手順は自動実行されないため) |
| `対象外(理由)` | 意図的にテストを持たない。理由を必ず併記する |

**受入基準の行は主担当モジュール1つにだけ置く。** 1つの要件が複数モジュールに割り当てられていても、
受入基準ごとに主担当を1つ決めて重複させない(重複させると集計が二重になり、進捗が読めなくなる)。

**モジュール分割定義に無い領域のテストは `images.md` が持つ。** イメージのビルドと GHCR 配布は
コールグラフに入口を持たずモジュールにしていない(`DSN-mod-05`)ため、そこに割り当てられる受入基準
(`FR-env-09` の CI 側・`FR-env-12` の同梱・`NFR-perf-01` / `NFR-perf-02`)の行き場が無くなる。
これを落とさないための1ファイルであり、`scope` にモジュール ID を持たない唯一のファイルである。

## 既知の不安定テスト

| テスト | 症状 | 頻度 | 対処状況 |
|---|---|---|---|
| なし | — | — | 現時点で不安定なテストは把握していない |

不安定なテストを黙って再実行で通してはならない。見つけたらこの表に記録し、`docs/issues/` を立てる。

## カバレッジの扱い

| 指標 | 目標 | 現状 | 測定コマンド |
|---|---|---|---|
| 行カバレッジ(Go) | **目標値なし**(01 の非機能要件にカバレッジの目標は無い) | 測定していない | `cd docker-proxy && go test -cover ./...` |
| 受入基準のカバレッジ | すべての受入基準が対応表に行を持つこと(状態は問わない) | 全 163 基準に行がある | `python3 .claude/scripts/build-index.py --check` で集計を再生成して確認する |

**カバレッジ率ではなく「受入基準に行があるか」を指標にする。** 自動テストを持てない領域が大きい
(Bash と Makefile)ため、行カバレッジは実態を表さない。
