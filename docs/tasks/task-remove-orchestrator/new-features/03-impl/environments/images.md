---
target: docs/03-impl/environments/images.md
change: replace
version_bump: minor
sections:
  - "## 何をどう制御しているか"
  - "## 関係するファイル"
  - "## 依存サービスと起動順"
  - "## 環境変数(ビルド引数)"
deletes: []
reason: 'オーケストレーターの全面削除にともなうイメージ構成の更新(決定シート 概念1・概念2)。(1) `## 何をどう制御しているか` のステージ図から `orch-builder`(`golang:1.24-alpine`)のノードと `base` への辺を削除し、「`orch-builder` で orchestrator をビルドし、成果物を後段のステージへコピーする」の箇条書きを削除する。**ステージは4つ(`orch-builder` / `base` / `vnc-base` / 終端2つの計5つ)から4つ(`base` / `vnc-base` / 終端2つ)になる** — `DSN-dist-01` が定める「重い共通層を `base` に集め、ブラウザ確認資産を `vnc-base` に積み、終端でエージェント CLI だけを載せる」という4ステージ構成そのものは変わらない。(2) `## 関係するファイル` の同梱スクリプトの行から `scripts/save_prompt.sh` と `scripts/sendslackmsg.sh` を外す(通知フックの削除)。(3) `## 依存サービスと起動順` の Mermaid から `orch-builder` のノードと辺を削除する。(4) **本文が引用している `.devcontainer/Dockerfile.claude` の行番号は、`orch-builder` ステージ(現行 `:12`〜`:21`)と orchestrator のコピー(現行 `:290`〜`:293`)を削除すると前後にずれる。フェーズ3 で実際に Dockerfile を編集したあと、`/implement` C-1 が本変更指示の行番号を実測へ更新する**(コードが正 — 原則2)。**実測の結果、`orch-builder` ステージ(旧 `:12`〜`:21`、区切りの空行を含めて 12 行)の削除で `.devcontainer/Dockerfile.claude` の行番号は一律 12 行ぶん繰り上がった**。行番号を引用しているのは `## 環境変数(ビルド引数)` の定義箇所の列 8 行だけなので、この節を `sections` に足して実測値へ書き換える(`USERNAME` `:29`→`:17` / `USER_UID` `USER_GID` `:30`〜`:31`→`:18`〜`:19` / `IMAGE_VERSION` `:38`〜`:39`→`:26`〜`:27` / `GO_VERSION` `:140`→`:128` / `PYTHON_VERSION` `:152`→`:140` / `CLAUDE_VERSION` `:509` `:537`→`:489` `:517` / `CODEX_VERSION` `:510` `:538`→`:490` `:518` / `container` `:307`→`:287`)。`## 落とし穴` は行番号を引用していないので触らない'
reflected: 2026-08-10
---

## 何をどう制御しているか

配布するイメージは1つの Dockerfile(`.devcontainer/Dockerfile.claude`)から作る。ステージは4つで、
**共通の重い層を `base` に集め、ブラウザ確認資産を `vnc-base` に積み、配布する2つの終端ステージで
エージェント CLI だけを最後に載せる**(`DSN-dist-01`)。

```mermaid
graph LR
  BASE[base<br/>ubuntu:24.04<br/>開発ツール一式] --> VNC[vnc-base<br/>VNC/Chrome/日本語入力]
  BASE --> CLI[claude-cli<br/>= 配布イメージ・ブラウザ確認なし]
  VNC --> VNCF[claude-vnc<br/>= 配布イメージ・ブラウザ確認あり]
```

- `base` が `ubuntu:24.04` の上に開発ツール(Go・Python・各種 CLI)を積む。
  **`ENV container=docker` はここで焼き込む**ので、`vnc-base` も終端ステージも継承する
  (`D0-env-06`)。
- `vnc-base` が `FROM base` で VNC・Chrome・日本語入力を積む。
- 終端ステージ `claude-cli` と `claude-vnc` が、それぞれ `FROM base` /
  `FROM vnc-base` で**最後にエージェント CLI だけを入れる**。
  この2つが配布物である。

エージェント CLI の導入を終端に置くのは、更新のたびに失効するレイヤーを CLI のバイナリ層だけに
限定するためである。`vnc-base` は `base` に連なるため、`base` の途中を失効させると VNC の高コスト層
まで巻き込んで再ビルド・再取得になる(`DSN-dist-01` / `NFR-perf-01`)。

## 関係するファイル

| ファイル | 役割 |
|---|---|
| `.devcontainer/Dockerfile.claude` | 配布イメージ2つ(と中間ステージ1つ)の定義 |
| `.devcontainer/Dockerfile.docker-proxy` | docker-proxy イメージの定義 |
| `.devcontainer/tmux.conf` | コンテナ内の tmux 設定(イメージへ同梱し、起動時に読み取り専用でマウントする) |
| `Makefile` | ビルドの入口(`MODULE-makefile-build*`) |
| `.github/workflows/ghcr-images.yml` | CI からのビルドと公開。構成値は `infra/local/ghcr.md` が正 |
| `scripts/entrypoint-claude.sh` | イメージの ENTRYPOINT(実装仕様は `MODULE-entrypoint-claude`) |
| `scripts/init-firewall-claude.sh` | `/usr/local/bin/init-firewall.sh` として同梱(`MODULE-firewall-init`) |
| `scripts/dood-portsync.sh` / `scripts/wait-limit-reset.sh` | コンテナ内で使う資産として同梱(それぞれ機能間連携仕様書を持つ) |

## 依存サービスと起動順

```mermaid
graph LR
  BASE[base] --> VNC[vnc-base]
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
| `USERNAME` | コンテナ内ユーザー名 | `devuser` | 任意 | `.devcontainer/Dockerfile.claude:17` |
| `USER_UID` / `USER_GID` | ビルド時のユーザー ID(起動時に entrypoint がホストへ追従させる) | `1500` / `1500` | 任意 | `:18`〜`:19` |
| `IMAGE_VERSION` | イメージのラベルに入れる版(タイムスタンプ) | `local` | 任意 | `:26`〜`:27` |
| `GO_VERSION` | 同梱する Go | `1.26.1` | 任意 | `:128` |
| `PYTHON_VERSION` | 同梱する Python | `3.13` | 任意 | `:140` |
| `CLAUDE_VERSION` | 同梱する Claude Code。**CI が具体バージョンへ解決して渡す** | `latest` | 実質必須(CI から) | `:489` / `:517` |
| `CODEX_VERSION` | 同梱する Codex CLI。**CI が具体バージョンへ解決して渡す** | `latest` | 実質必須(CI から) | `:490` / `:518` |
| `container`(ENV) | コンテナ内であることのマーカー | `docker` | 必須 | `:287` |
