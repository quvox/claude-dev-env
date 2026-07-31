---
id: e2e
layer: impl
title: E2Eテスト実装説明書
version: 1.5.0
updated: 2026-07-31
summary: >
  02-design のE2Eシナリオ一覧(E2E-1〜6)に対応するE2E検証の実装説明。専用E2Eフレームワークは持たず、
  実機操作(claude-dev)とオーケストレーター自己検証(make orch-sample)で担保する。
keywords: [e2e, 実機確認, 自己検証, orch-sample, docker-proxy, orchestrate, codex認証共有, codexシェル実行]
depends_on: [cli, entrypoint, docker-proxy, portsync, orchestrator, sample-project]
source:
  - docs/02-design/system.md
---

# E2Eテスト実装説明書

## 概要

本システムのE2Eは、[全体設計のテスト戦略](../02-design/system.md)「E2Eシナリオ一覧」（E2E-1〜6）に従う。
Web アプリのような自動E2Eフレームワーク（Playwright 等）は導入していない。E2E は
**(a) ホスト CLI の実機操作**（コンテナ起動・フォワード・docker-proxy 挙動）と、**(b) オーケストレーターの
自己検証**（バンドル題材に対する `make orch-sample` の実走、[sample-project](sample-project.md)）で担保する。
したがって多くのシナリオは自動化されておらず**実機確認**である点を明記する。

## テスト環境・実行方法

| 項目 | 内容 |
|---|---|
| ツール | ホスト CLI `claude-dev`（実機操作）＋ `make orch-sample`（オーケストレーター自己検証題材の scaffold・実走） |
| 実行環境(構成) | Linux サーバ + Docker Engine 24+（macOS は Docker Desktop）。VNC あり/なしイメージ、docker-proxy 共有コンテナ |
| テストデータ方針 | 自己検証題材は `examples/orch-sample/`（正本）を `workspace/orch-sample/` へ scaffold（冪等・`--force` で再初期化）。実機確認は使い捨てのプロジェクトで行う |
| 実行コマンド | 実機: `claude-dev start` / `forward` / コンテナ内 `docker run` 等。自己検証: `make orch-sample`（題材を scaffold）→ `claude-dev orchestrate`（実走）、後始末は `make orch-sample-clean` |

## ファイル構成

| パス | 役割 |
|---|---|
| scripts/orch-sample.sh | 自己検証題材の scaffold（[sample-project](sample-project.md) が正本） |
| examples/orch-sample/ | オーケストレーター自己検証の題材（Python+pytest、seed/plan.json 等） |
| （専用E2Eテストコードなし） | CLI/コンテナ系は自動E2Eを持たず実機確認 |

## テスト対応表

| テスト(ファイル::ケース名) | 対応シナリオID | 対応ユースケース | 検証内容 |
|---|---|---|---|
| 実機確認(手動): `claude-dev start`（VNC/`--no-vnc`）→ claude 起動・再接続 | E2E-1 | UC-1 | /workspace マウント・認証・FW・tmux が整い Claude Code が動く。自動化なし＝**未検証(自動化なし・実機確認)** |
| 実機確認(手動): `claude-dev forward` → SSH トンネル → ブラウザ表示・`ports` 確認 | E2E-2 | UC-2 | 8100〜割当・クライアントから到達・start 時は非公開。自動化なし＝**未検証(自動化なし・実機確認)** |
| 実機確認(手動): コンテナ内 `docker run -v /:/host` 等 → 拒否／`/workspace` bind 許可／通常許可 | E2E-3 | UC-3 | docker-proxy の許可/拒否/書換（契約は [docker-proxy](docker-proxy.md) の結合テストが機械検証、E2E としては実機確認）＝**部分自動(結合テスト)＋実機確認** |
| 自己検証: `make orch-sample`（scaffold）→ `claude-dev orchestrate`（実走） | E2E-4 | UC-4 | ブレスト→plan→worker 並列→要判断タスク単位待機→回答復帰→完了。題材に対し実走で確認＝**半自動(自己検証題材で実走・観測)** |
| 実機確認(手動): 実行中に端末全終了 → `claude-dev orchestrate` 再実行 | E2E-5 | UC-5 | attach/resume・完了済み非再実行・plan/履歴保持。自動化なし＝**未検証(自動化なし・実機確認)** |
| 実機確認(手動): `claude-dev login-codex` → デバイス認証 → 別プロジェクトで `claude-dev start` → コンテナ内 `codex` にファイル読み書きを伴う作業を依頼 → 続けて landlock 疎通確認と読み取り専用での依頼 | E2E-6 | UC-6 | 共有ボリュームへ `codex/auth.json` が保存され、別プロジェクトのコンテナで再ログイン不要に `codex` が起動する。**依頼した作業で codex が起こすシェルコマンドが成功し（`bwrap` エラーで失敗しない）、`/workspace` のファイルを読み書きできる**。**landlock 疎通確認**として、entrypoint が置いた既定 `config.toml` があるコンテナで**フラグを付けずに** `codex sandbox -- /bin/true` が exit 0（＝config 経由で landlock が効いている。ここが要件 core/12-9 の本体）、同経路の `codex sandbox -- /bin/sh -c 'touch /tmp/x'` が失敗しファイルが生成されない。`--enable use_legacy_landlock` を明示した形でも exit 0 になる（フラグ経路の回帰確認）。さらに `codex exec -s read-only` を明示した依頼でファイル読み取りが成功する（要件 core/12-9）。トークン更新が 30 秒同期で共有ボリュームへ書き戻り次のコンテナへ引き継がれる。`config.toml`/セッション履歴はコンテナごとに独立。自動化なし＝**未検証(自動化なし・実機確認)** |

## 既知の制限・技術的負債

- CLI/コンテナ系（E2E-1,2,3,5,6）の**自動E2Eは未整備**で、実機確認に依存する。回帰検出は手動。
- E2E-6 はデバイス認証にブラウザ操作（クライアント PC 側）を伴うため、原理的に無人自動化できない。
  実施前にイメージの再ビルド（`make build`、または `make build-claude` と `make build-claude-vnc` の両方。
  codex 同梱層が新設されるため）が必要。
- E2E-6 の「シェル実行が成功する」観点は、**codex 自身の応答を合否根拠にしてはならない**。既定
  `sandbox_mode` ではコマンドが `exited 1` になってもモデルが成功したかのように応答する（出力の捏造）
  事象が観測されており、`codex doctor` も検知しない。さらに **`codex exec` プロセスの終了コードは
  内部のコマンドが全滅していても 0 になる**（2026-07-31 実測）。判定は codex の画面に出る `exec` 行の
  終了コードと、作業結果として `/workspace` に実際に残ったファイルで行う
  （[verify-automation-by-artifact-not-by-green-run](../knowledge/verify-automation-by-artifact-not-by-green-run.md)
  と同じ「成果物で確かめる」原則）。`codex sandbox` の疎通確認は例外的にプロセスの終了コードで判定してよい
  （モデルを介さず直接コマンドを実行するため）。
- E2E-6 の landlock 疎通確認は、`features.use_legacy_landlock` が deprecated（codex 0.146.0 時点で
  「will be removed soon」と警告）であることに対する回帰検知を兼ねる。`CODEX_VERSION` はビルド時に
  latest を解決してピン留めするため、**イメージを更新したら必ずこの確認を再実行する**。撤去されていた
  場合の退避は、codex にシェルを使わせない添付方式（対象ファイルの内容をプロンプトへ添付する）で
  読み取り専用の依頼を成立させることであり、その判断は 02-design 判断5 の却下案④に記録がある。
- E2E-4 は自己検証題材での実走・観測であり、合否を機械判定する厳密なアサーションは持たない（人間/助言的検証が確認する）。
- docker-proxy の契約は結合テスト（`docker-proxy/*_test.go`）で機械検証されるため、E2E-3 の中核ロジックはそちらでカバーされる。

## 運用メモ

- 自己検証は変更時に `make orch-sample` を実行して観測する（[tech steering](../_steering/tech.md)）。
- 実機E2Eは、リリース前・オーケストレーター/CLI 変更後に主要シナリオ（特に E2E-1/E2E-4）を手動で一巡することを推奨。
