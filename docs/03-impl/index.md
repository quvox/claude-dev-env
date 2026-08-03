---
id: index
version: 1.1.0
updated: 2026-08-03
source:
  - docs/02-design/system.md
  - docs/02-design/relations.md
summary: 03-impl 層の目次。機能間連携仕様書群の代表として層全体の版と合格証を持つ
keywords: [目次]
verified:
  at: 2026-08-03
  version: 1.1.0
  against:
    - doc: docs/02-design/system.md
      version: 2.0.0
    - doc: docs/02-design/relations.md
      version: 1.0.0
---

# 03-impl 目次

## この層の状態

| 項目 | 値 |
|---|---|
| 機能間連携仕様書の本数 | 82 |
| 網羅しているモジュール | MOD-cli-common, MOD-cli-setup, MOD-cli-start, MOD-cli-stop, MOD-cli-attach, MOD-cli-code, MOD-cli-list, MOD-cli-login, MOD-cli-login-codex, MOD-cli-logout, MOD-cli-forward, MOD-cli-unforward, MOD-cli-ports, MOD-cli-ssh-keys, MOD-cli-firewall, MOD-cli-orchestrate, MOD-cli-pull, MOD-cli-upgrade, MOD-cli-reset, MOD-makefile, MOD-entrypoint, MOD-firewall, MOD-docker-proxy, MOD-portsync, MOD-vm-mode, MOD-orchestrator, MOD-hooks, MOD-container-tools, MOD-sample-project(29モジュール) |
| `check-relations.py` 最終結果 | 合格(2026-08-03。82 ファイル / 82 ID。対称性・参照実在・impl パス・必須項目・機能表との 1:1 すべて問題なし) |
| コードとの乖離として未解決のもの | 1件: macOS のコントローラ生存判定が無い(`docs/issues/003-future-macos-orchestrator-scope.md`) |
| `relations-coverage.py` 最終結果 | 未記載 30 件を検出するが、**全件が `scan-entrypoints.py` の Go `switch` 誤検出**(設定キー `max_workers` 等・TUI のキー入力 `p`/`d`/`i`・JSON の型識別子・git のサブコマンド文字列)であり、実在する入口ではない。コードとの一致は `callgraph-check.py` と `check-relations.py` が担保する |

## 02 との差分(未解消のもの)

| 種別 | 対象 | 内容 | 対処 |
|---|---|---|---|
| PLAN なし / MODULE あり | MODULE-orchestrator-* の内部関数18本、MODULE-sample-project-mathkit | 設計側は同一モジュール内部で完結する private helper を書かない取り決めのため、意図的な差分である | 対処不要(`02-design/relations.md` の網羅範囲に明記) |
| 契約の差異 | CTR-cli-orchestrator | macOS 版にコントローラの生存判定が無く、設計の期待(OS によらず同じ観測可能な結果)を満たしていない | `docs/issues/003-future-macos-orchestrator-scope.md` で追跡 |

上記2件を除いて差分なし。

## 目次

<!-- BEGIN GENERATED: build-index.py -->

| ファイル | version | 更新 | 概要 |
|---|---|---|---|
| [features](features.md) | - | 2026-08-02 | claude-dev 開発環境の機能一覧と入口。CLI サブコマンド・Makefile ターゲット・常駐スクリプト・Go バイナリの入口を列挙する |
| [images](environments/images.md) | 1.0.0 | 2026-08-03 | 配布イメージ(claude-cli / claude-vnc)のステージ構成・ビルド引数・キャッシュの効かせ方 |
| [local-docker-resources](infra/local/docker-resources.md) | 1.0.0 | 2026-08-03 | ホスト上に作られる Docker リソース(ネットワーク・ボリューム・コンテナ)の一覧と命名規則 |
| [local-ghcr](infra/local/ghcr.md) | 1.0.0 | 2026-08-03 | 配布イメージの公開先 GHCR の構成(リポジトリ・タグ・マルチアーキ・認証の置き場所) |

件数: 4

<!-- END GENERATED -->

## 機能間連携仕様書

`docs/03-impl/relations/index.md` を参照(こちらも生成物)。**82機能** の境界は
`docs/03-impl/features.md`(人間が合意した機能表)が定義する。

## コールグラフ

`docs/03-impl/callgraphs/index.md` を参照。**ツールだけが書く場所**であり、機能間連携仕様書では
ない(`.claude/directions/callgraphs.md`)。版も合格証も持たない純粋な導出物で、鮮度は
`python3 .claude/scripts/build-callgraphs.py --check` で検査する。

| 項目 | 値 |
|---|---|
| 最終検査 `--check` | 最新(2026-08-03。go 219シンボル/399辺 / shell 130/168 / make 19/22 / python 5/0 / typescript 0 / infra 0。エントリポイント 72) |
| `callgraph-check.py` の未解決指摘 | 指摘 40 件・**重大度「高」ゼロ**(中3 = CG3 entrypoint のプロセス跨ぎ連携 / 低17 = CG2 到達不能候補 / 参考20 = CG4 取りこぼし候補)。中3件は絶対パス起動のため shell 抽出器が辺を解決できないもので、根拠は `relations/MODULE-entrypoint-claude.md` の本文にある |
| 抽出器が無い領域 | Dockerfile と GitHub Actions。この2つはモジュールにせず `environments/images.md` と `infra/local/ghcr.md` が記述を持つ(`DSN-mod-05`) |
