---
id: cli-mac
layer: impl
title: cli-mac 実装説明書
version: 1.0.0
updated: 2026-07-18
verified:
  at: 2026-07-18
  version: 1.0.0
  against:
    - doc: docs/02-design/system.md
      version: 1.0
summary: >
  macOS 版ホスト CLI `claude-dev-mac`（単一 bash）。cli との差分のみを持つ——SSH agent を
  専用 agent＋socat TCP ブリッジ（127.0.0.1）で転送・ポート直結（SSH トンネルなし）・VM/KVM 非対応・
  arm64 ネイティブ。共通挙動は cli.md を正本とする。
keywords: [CLI, claude-dev-mac, macOS, SSHブリッジ, socat, ポート直結, arm64, VM非対応]
depends_on: [cli]
source:
  - docs/02-design/system.md
---

# 実装説明書:cli-mac

## 概要

`claude-dev-mac` は Linux 版 `cli`（`claude-dev`）の macOS（Docker Desktop）適応版で、単一の
bash スクリプトである。サブコマンド体系・定数・大半のヘルパーは `cli` と同一実装であり、本書は
**macOS 固有の差分のみ**を記述する。共通挙動は [cli.md](./cli.md) を正本とする。差分は 4 点＋
プラットフォーム——(1) SSH agent 転送を専用 agent＋socat TCP ブリッジで行う、(2) Docker ソケット
を検出する、(3) VM/KVM を早期拒否する、(4) ポートフォワードを直結案内する、(5) arm64 ネイティブで
ビルド/実行する。対応要件は core/10（[全体設計](../02-design/system.md) の cli-mac 行）。コンテナ内
資産（firewall・docker-proxy・tmux.conf・entrypoint）は Linux 版と共有し、CLI だけを分岐させる。

## ファイル構成

| パス | 役割 |
|---|---|
| `claude-dev-mac`（リポジトリ直下） | macOS 版ホスト CLI（単一 bash スクリプト） |
| `${HOME}/.claude-dev/agents/`（実行時生成） | プロジェクト専用 agent/ブリッジ置き場（`<name>.sock`/`.pid`/`.bridge.pid`/`.bridge.port`、`chmod 700`） |
| `<PROJECT_DIR>/.claude-dev.yaml`（実行時生成） | プロジェクト単位の使用 SSH 鍵設定（cli と共通スキーマ） |

## モジュール別実装詳細

### SSH agent 転送（方式D:専用 agent＋socat TCP ブリッジ）

- **責務:** core/10 受け入れ基準2「SSH agent を TCP ブリッジで転送」。cli の `$SSH_AUTH_SOCK`
  直 bind mount（魔法ソケット方式）は macOS では使えない（Docker Desktop の Unix ソケットは
  コンテナへ直マウントできず、利用者の鍵がある agent を転送しない）ため置き換える。秘密鍵ファイルは
  コンテナに渡らず、agent プロトコルのみを 127.0.0.1 経由で転送する。
- **公開インターフェース（主要ヘルパー）:**

```
dev_agent_path <name> sock|pid|bpid|bport -> path         # プロジェクトごとのファイルパスを返す
resolve_ssh_keys_for_start <project_dir>                  # <project_dir>/.claude-dev.yaml の ssh_keys のみ解決
ensure_dedicated_agent <name> -> 0|1                      # 専用 agent 起動/再利用し鍵を ssh-add
find_free_local_port -> port                              # 9700〜9799 の空き 127.0.0.1 ポート
ensure_ssh_bridge <name> -> port(stdout) | 非0            # socat TCP ブリッジ起動、使用ポートを返す
stop_ssh_bridge <name>                                    # ブリッジ socat 停止（専用 agent は残す）
```

- **処理の要点:**
  - agent/ブリッジは**プロジェクト（=`NAME`=ディレクトリ名）ごと**に隔離する。`DEV_AGENT_DIR`
    （`${HOME}/.claude-dev/agents/`、`chmod 700`）に `<name>.sock`/`<name>.pid`/
    `<name>.bridge.pid`/`<name>.bridge.port` を持つ。
  - 鍵解決は **`<PROJECT_DIR>/.claude-dev.yaml` の `ssh_keys:` のみ**（`_parse_ssh_keys_yaml`
    の簡易パース、`~`→`$HOME` 展開）。グローバル config へのフォールバック・自動生成・対話選択は
    しない。無ければ 0 件＝SSH 転送なし。鍵解決方針・`ssh_keys` スキーマ・`ssh-keys` サブコマンドは
    cli と共通（cli.md 正本）。
  - `ensure_dedicated_agent`:`ssh-add -l` の終了コードが 2（接続不可）または sock 非存在なら
    `ssh-agent -a <sock>` で（再）起動。登録済み鍵は指紋（`ssh-keygen -lf`）突き合わせで
    スキップし、未登録分をパスフレーズなし一括（`SSH_ASKPASS=/bin/false`）→残りを対話追加。
    存在しない鍵は警告してスキップ。
  - `ensure_ssh_bridge`:`socat` 不在なら `brew install socat` を案内して非0で戻る（SSH 転送
    スキップ）。既存ブリッジが `kill -0` で生存ならその port を再利用。無ければ `.env` の
    `CLAUDE_DEV_SSH_BRIDGE_PORT` があればそれ、無ければ `find_free_local_port` で確保し、
    `socat TCP-LISTEN:<port>,bind=127.0.0.1,fork,reuseaddr UNIX-CONNECT:<name>.sock` を
    `nohup ... &` で起動、port を返す。
  - **`start` の SSH 部分:** `resolve_ssh_keys_for_start` で鍵解決 →実在鍵が 1 つ以上あれば
    `ensure_dedicated_agent "$NAME"` →成功後 `ensure_ssh_bridge "$NAME"` で port 取得。
    port が得られたときのみ `docker run` に `-e CLAUDE_DEV_SSH_BRIDGE_PORT=<port>` を付与
    （コンテナ内で `/tmp/ssh-agent.sock` を立て `SSH_AUTH_SOCK` に設定するのは entrypoint 側）。
    `~/.ssh/known_hosts` は存在時 RO マウント、`~/.ssh/config` は `IdentityFile`/
    `IdentitiesOnly`/**`IdentityAgent`** 行を sed 除去した**一時コピー**を RO マウント
    （ホスト config は不変。`IdentityAgent` 除去は cli と共通）。
  - **`stop`:** コンテナ削除後 `stop_ssh_bridge "$NAME"`（そのプロジェクトのブリッジのみ停止・
    専用 agent は鍵保持のため残す）と `stop_proxy_if_idle` を呼ぶ。
- **実装上の判断:** ブリッジポート帯は 9700〜9799（forward の 8100〜・noVNC の 6080〜 と非重複）。
  旧・単一 agent/ブリッジ（`LEGACY_*`:`ssh-agent.sock` 等）は生成しなくなったが `ssh-keys reset`
  が残骸を掃除する（後方互換）。

### Docker ソケット検出（`detect_docker_sock` / `ensure_docker_proxy_container`)

- **責務:** cli では固定の `/var/run/docker.sock` を前提とするが、Docker Desktop は配置が異なる
  ため検出する。
- **処理の要点:** `detect_docker_sock` は `/var/run/docker.sock` →`$HOME/.docker/run/docker.sock`
  の順で最初に存在する Unix ソケットを返す（無ければ空文字）。`ensure_docker_proxy_container` は
  検出結果が非空のときのみ動作し、`-v "${sock}:/var/run/docker.sock:ro"` でマウントして
  docker-proxy を `claude-dev-net` 上に `--restart unless-stopped` で起動。`start` は
  `if [ -n "$(detect_docker_sock)" ]` で判定し、非空なら `DOCKER_HOST=tcp://<proxy>:2375` を付与。

### VM/KVM の早期拒否

- **責務:** core/10 受け入れ基準2「VM/KVM 非対応」。macOS/Docker Desktop に `/dev/kvm` は無く、
  ネスト仮想化も不可のため。
- **処理の要点:** `start` のフラグ解析で `--kvm`/`--vm`/`--vm-fresh` を検出したら理由を表示して
  `exit 1`。この判定は `require_setup`（イメージ自動ビルド）**より前**に行い無駄なビルドを避ける。
  cli にある `KVM_OPTS`・`VM_OPTS`・VM 用長時間待機（tmux 待ちは常に 30 秒上限）は**存在しない**。
  `code` は VM 判定（`CLAUDE_DEV_VM` printenv・`--append-system-prompt` 注入）を行わず常に
  `tmux new-window -t main "claude"`。`orchestrate` は `vm.env` 読み込みを挟まない（それ以外は
  cli と同一）。

### ポートフォワード直結（`forward` / `help`)

- **責務:** core/10 受け入れ基準2「ポートは直結（SSH トンネル不要）」。macOS はローカルで
  Docker Desktop が公開ポートを直接見せるため。
- **処理の要点:** socat プロキシコンテナ生成（`fwd-<name>-<port>`、`-p <hport>:<cport>`、
  `IMG_CLAUDE` を `--entrypoint socat`）は cli と同じ。案内文のみ「ブラウザで
  `http://localhost:<host-port>`」に変更し、`help` の Web アクセス節も直結案内にする
  （`--kvm`/`--vm` の記載なし。ただし「VM/KVM は非対応」の注記は残す）。

### プラットフォーム（arm64 ネイティブ）

- **責務:** core/10 受け入れ基準3「Apple Silicon で arm64 ネイティブ動作」。
- **処理の要点:** `DOCKER_DEFAULT_PLATFORM` は**固定しない**（利用者が明示した場合のみ尊重）。
  共有 `Dockerfile.claude` がアーキ別に対応済み（arm64=Playwright Chromium／amd64=Google Chrome、
  gcloud はアーキ名写像、共通ランチャー `claude-dev-chrome`）のため、Apple Silicon（arm64）でも
  Intel Mac（amd64）でもエミュレーションなしでビルドできる。詳細は devcontainer に属す。

### install（symlink）

- `make install` は OS を判定し、macOS では `sudo ln -sf` で `/usr/local/bin/claude-dev` を
  `claude-dev-mac` への symlink にする（判定・実行は makefile モジュール）。本スクリプトの
  パス解決は `readlink -f "$0"`（失敗時 `realpath "$0"`）→`dirname` で `BASE_DIR` を得るため、
  symlink 経由でも repo 実体パスへ解決し repo 内資産（Dockerfile・tmux.conf・CLAUDE.md 等）を
  参照できる。利用者コマンド名はどの OS でも `claude-dev`。core/10 受け入れ基準1に対応。

## データアクセス

| データ | 操作 | 実施モジュール | 備考 |
|---|---|---|---|
| `<PROJECT_DIR>/.claude-dev.yaml`（`ssh_keys`） | 読み（解決）・書き（選択保存/reset） | cli-mac（cli と共通スキーマ） | プロジェクト単位。cli.md 正本 |
| `${HOME}/.claude-dev/agents/<name>.*` | agent/ブリッジの sock/pid/port 管理 | cli-mac | macOS 固有。`chmod 700` |
| Docker リソース（net/volume/image/コンテナ） | cli と同一 | cli-mac | 命名は `claude-dev-` 接頭辞（cli.md 正本） |

## API実装詳細

外部公開 API なし（ホスト CLI。UI はコマンド体系＝[全体設計 UI設計](../02-design/system.md) の
cli-commands 画面）。コンテナ→docker-proxy の HTTP 契約は docker-proxy モジュールが持つ。

## 設定・環境変数

| 名前 | 用途 | デフォルト | 必須 |
|---|---|---|---|
| `CLAUDE_DEV_SSH_BRIDGE_PORT` | ブリッジ TCP ポートの明示指定。`start` が port として `docker run` に注入（コンテナ内 entrypoint が参照） | 未指定時 `find_free_local_port` | 任意 |
| `CLAUDE_DEV_ALLOW_WORKSPACE_BINDS` | docker-proxy の `/workspace` bind 許可 | 1 | 任意 |
| `DOCKER_DEFAULT_PLATFORM` | ビルド/実行アーキ。cli-mac は固定しない | 未設定（ネイティブ） | 任意 |
| `DOCKER_CLI_HINTS` | docker CLI ヒント抑制 | false | 任意 |
| `CLAUDE_DEV_REGISTRY`/`CLAUDE_DEV_IMAGE_TAG` | `pull` の GHCR 参照（cli 共通） | `ghcr.io/quvox`／`latest` | 任意 |

その他の共通環境変数は cli.md を参照。

## エラーハンドリング実装

| 異常系 | 実装箇所 | 実際の振る舞い | 対応する要件 |
|---|---|---|---|
| 必須コマンド不足（docker/jq/**socat**） | `check_host_deps`（`start` 冒頭） | 不足分を列挙し導入案内（docker=Docker Desktop URL、他=`brew install <cmd>`）して `exit 1` | core/10（socat は macOS 差分） |
| `socat` 不在（SSH ブリッジ） | `ensure_ssh_bridge` | `brew install socat` を案内し非0で戻る。SSH 転送なしで start 継続 | core/10 受け入れ基準2 |
| `--kvm`/`--vm`/`--vm-fresh` 指定 | `start` フラグ解析 | 非対応理由を表示し `exit 1`（ビルド前） | core/10 受け入れ基準2 |
| SSH 鍵未選択 | `start` SSH 部 | 日本語案内（`ssh-keys` 選択 or `.claude-dev.yaml` 作成）を出し転送なしで継続 | core/10（停止しない方針は cli 共通） |
| Docker ソケット不在 | `detect_docker_sock` 空 | docker-proxy を起動せず `DOCKER_HOST` 未付与で継続 | core/7 周辺 |

方針（前提不足は停止せず日本語案内・人間向け表示は日本語）は cli と共通。

## テスト

本モジュールは bash スクリプトで自動テストを持たない（[全体設計 テスト戦略](../02-design/system.md)
「シェル系は自動テストなし＝実機確認」）。検証は macOS 実機での実操作による。

| テスト(ファイル::ケース名) | レベル | 検証内容 | 対応する受け入れ基準/契約 |
|---|---|---|---|
| （自動テストなし・macOS 実機確認） | 単体 | `make install` で `/usr/local/bin/claude-dev`→`claude-dev-mac` symlink | core/10-基準1 |
| （自動テストなし・macOS 実機確認） | 単体 | 鍵選択後 `start` で 127.0.0.1 ブリッジ確立・agent 転送到達／`forward` 後 `http://localhost:<port>` 直結／`--vm` 早期拒否 | core/10-基準2 |
| （自動テストなし・macOS 実機確認） | 単体 | Apple Silicon で arm64 ネイティブ起動（エミュレーションなし） | core/10-基準3 |

実行方法:macOS 実機で `claude-dev`（=`claude-dev-mac`）を直接操作して確認する。core/10 の
全受け入れ基準は上記のとおり **未検証(自動テストなし)** ＝実機確認扱い。

## 既知の制限・技術的負債

- top-level `reset` はコンテナ・ボリューム・イメージを削除するが、プロジェクト専用 agent/ブリッジ
  （`${HOME}/.claude-dev/agents/`）は掃除しない。掃除は `ssh-keys reset`（当該プロジェクトのみ）が担う。
- 自動テストがなく、回帰検出は実機操作に依存する（シェル系共通の方針）。
- `image_version` はラベル `io.github.quvox.claude-dev.version` を参照する（コード内コメントの
  `org.opencontainers.image.version` は表記のみで実挙動は前者。cli と共通）。

## 運用メモ

- 導入前提:macOS + Docker Desktop、`docker`/`jq`/`socat`（`brew install socat`）。SSH agent 転送に
  host socat が必須。
- SSH 鍵はプロジェクト単位で `.claude-dev.yaml` に選択（`claude-dev ssh-keys`）。露出は選択鍵のみ・
  稼働中のみ・127.0.0.1 限定。
- コンテナ内資産・共通挙動の詳細は [cli.md](./cli.md)、entrypoint 側のブリッジ受け（
  `CLAUDE_DEV_SSH_BRIDGE_PORT` 分岐）は entrypoint モジュールを参照。
