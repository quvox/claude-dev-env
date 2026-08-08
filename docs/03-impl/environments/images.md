---
id: images
version: 1.0.0
updated: 2026-08-03
source:
  - docs/02-design/environments.md
summary: 配布イメージ(claude-cli / claude-vnc)のステージ構成・ビルド引数・キャッシュの効かせ方
keywords: [イメージ, Dockerfile, ビルド]
verified:
  at: 2026-08-08
  version: 1.0.0
  against:
    - doc: docs/02-design/environments.md
      version: 1.3.0
---

<!-- 2026-08-04 /doc-check ssot task-impl-depth(新しい実行): **合格証を再発行した(1.0.0)。**
     直前に削除した理由(source の docs/02-design/environments.md が未検証)は解消した。
     本文には問題を見つけていない。★本実行は独立レンズが1つも走っていない。 -->

# コンテナイメージのビルドの実装仕様

## 何をどう制御しているか

配布するイメージは1つの Dockerfile(`.devcontainer/Dockerfile.claude`)から作る。ステージは4つで、
**共通の重い層を `base` に集め、ブラウザ確認資産を `vnc-base` に積み、配布する2つの終端ステージで
エージェント CLI だけを最後に載せる**(`DSN-dist-01`)。

```mermaid
graph LR
  OB[orch-builder<br/>golang:1.24-alpine] --> BASE
  BASE[base<br/>ubuntu:24.04<br/>開発ツール一式] --> VNC[vnc-base<br/>VNC/Chrome/日本語入力]
  BASE --> CLI[claude-cli<br/>= 配布イメージ・ブラウザ確認なし]
  VNC --> VNCF[claude-vnc<br/>= 配布イメージ・ブラウザ確認あり]
```

- `orch-builder`(`.devcontainer/Dockerfile.claude:16`)で orchestrator をビルドし、成果物を
  後段のステージへコピーする。
- `base`(`:23`)が `ubuntu:24.04` の上に開発ツール(Go・Python・各種 CLI)を積む。
  **`ENV container=docker`(`:307`)はここで焼き込む**ので、`vnc-base` も終端ステージも継承する
  (`D0-env-06`)。
- `vnc-base`(`:318`)が `FROM base` で VNC・Chrome・日本語入力を積む。
- 終端ステージ `claude-cli`(`:506`)と `claude-vnc`(`:534`)が、それぞれ `FROM base` /
  `FROM vnc-base` で**最後にエージェント CLI だけを入れる**(`:514`/`:517`、`:542`/`:545`)。
  この2つが配布物である。

エージェント CLI の導入を終端に置くのは、更新のたびに失効するレイヤーを CLI のバイナリ層だけに
限定するためである。`vnc-base` は `base` に連なるため、`base` の途中を失効させると VNC の高コスト層
まで巻き込んで再ビルド・再取得になる(`DSN-dist-01` / `NFR-perf-01`)。

## 関係するファイル

| ファイル | 役割 |
|---|---|
| `.devcontainer/Dockerfile.claude` | 配布イメージ2つ(と中間ステージ2つ)の定義 |
| `.devcontainer/Dockerfile.docker-proxy` | docker-proxy イメージの定義 |
| `.devcontainer/tmux.conf` | コンテナ内の tmux 設定(イメージへ同梱し、起動時に読み取り専用でマウントする) |
| `Makefile` | ビルドの入口(`MODULE-makefile-build*`) |
| `.github/workflows/ghcr-images.yml` | CI からのビルドと公開。構成値は `infra/local/ghcr.md` が正 |
| `scripts/entrypoint-claude.sh` | イメージの ENTRYPOINT(実装仕様は `MODULE-entrypoint-claude`) |
| `scripts/init-firewall-claude.sh` | `/usr/local/bin/init-firewall.sh` として同梱(`MODULE-firewall-init`) |
| `scripts/dood-portsync.sh` / `scripts/wait-limit-reset.sh` / `scripts/save_prompt.sh` / `scripts/sendslackmsg.sh` | コンテナ内で使う資産として同梱(それぞれ機能間連携仕様書を持つ) |

## 使い方(実際のコマンド)

| やりたいこと | コマンド | 備考 |
|---|---|---|
| 全イメージをビルド | `make build` | `claude` + `claude-vnc` + `docker-proxy` |
| 個別ビルド | `make build-claude` / `make build-claude-vnc` / `make build-docker-proxy` | `claude-vnc` は `base` に続けてビルドする |
| キャッシュ無しで作り直す | `make upgrade` | 全イメージ |
| エージェント CLI だけ更新 | `make update-claude` | キャッシュを使い終端レイヤーだけを作り直す |
| 配布イメージを取得 | `claude-dev pull` | GHCR から取得して以降の判定名へ付け替える |

## 依存サービスと起動順

```mermaid
graph LR
  OB[orch-builder] --> BASE[base]
  BASE --> VNC[vnc-base]
  BASE --> CLI[claude-cli]
  VNC --> VNCF[claude-vnc]
```

| サービス | 起動条件 | ヘルスチェック |
|---|---|---|
| ビルド | `make build` 実行時。ネットワーク到達性が必要(パッケージ・CLI の取得) | ビルドの終了コード |
| 取得 | `claude-dev pull` 実行時。GHCR への到達性が必要 | 取得の終了コード |

## 環境変数(ビルド引数)

| 変数 | 用途 | 既定値 | 必須 | 定義箇所 |
|---|---|---|---|---|
| `USERNAME` | コンテナ内ユーザー名 | `devuser` | 任意 | `.devcontainer/Dockerfile.claude:29` |
| `USER_UID` / `USER_GID` | ビルド時のユーザー ID(起動時に entrypoint がホストへ追従させる) | `1500` / `1500` | 任意 | `:30`〜`:31` |
| `IMAGE_VERSION` | イメージのラベルに入れる版(タイムスタンプ) | `local` | 任意 | `:38`〜`:39` |
| `GO_VERSION` | 同梱する Go | `1.26.1` | 任意 | `:140` |
| `PYTHON_VERSION` | 同梱する Python | `3.13` | 任意 | `:152` |
| `CLAUDE_VERSION` | 同梱する Claude Code。**CI が具体バージョンへ解決して渡す** | `latest` | 実質必須(CI から) | `:509` / `:537` |
| `CODEX_VERSION` | 同梱する Codex CLI。**CI が具体バージョンへ解決して渡す** | `latest` | 実質必須(CI から) | `:510` / `:538` |
| `container`(ENV) | コンテナ内であることのマーカー | `docker` | 必須 | `:307` |

## 落とし穴

| 事象 | 原因 | 回避方法 |
|---|---|---|
| 同梱エージェント CLI が更新されない | `CLAUDE_VERSION=latest` / `CODEX_VERSION=latest` のまま渡すと**文字列が変わらずキャッシュキーとして機能せず**、導入層が永久にヒットして中身だけ凍結する(2026-07 に実際に発生) | CI の prepare ジョブで具体バージョンへ解決してから build-arg で渡す(`infra/local/ghcr.md`) |
| 取得が毎回フルダウンロードになる | 時刻由来の値をレイヤーチェーンに入れると、内容が変わらない日も全層が失効する | レイヤーチェーンに入れてよいのは**内容由来**の値だけ(`DSN-dist-01`)。時刻はラベルに置く |
| VNC 層まで再ビルドされる | エージェント CLI の導入を `base` の途中に置くと、`FROM base` の `vnc-base` まで失効が波及する | 導入は終端ステージの最終レイヤーにのみ置く |
| ローカルビルドと配布イメージで版が違う | ローカルは `latest` の既定のまま解決されるため、ビルドした時点の版が焼かれる | チームで揃えるときは `claude-dev pull` を使う |
