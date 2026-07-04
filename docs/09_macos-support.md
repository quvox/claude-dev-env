---
summary: macOS（Docker Desktop）上で Claude Code 安全開発環境を動かすための設計文書。Linux 版 claude-dev の OS 依存箇所を洗い出し、macOS 版 CLI（claude-dev-mac）での解決方針（SSH agent 魔法ソケット・Docker ソケット検出・VM/KVM 非対応・ポート直結・Apple Silicon の arm64 ネイティブ対応＝Playwright Chromium／gcloud アーキ写像・install は sudo symlink）を定める。
keywords: [ macOS, Docker Desktop, claude-dev-mac, SSHエージェント, arm64, ポートフォワード, VM非対応 ]
---

# macOS 対応設計

> **この文書の役割**: Linux 向けに作られた `claude-dev` を、macOS（Docker Desktop）上でも動かすための設計を示す。macOS 版 CLI `claude-dev-mac` が Linux 版とどこで分岐するか、その理由と解決方針を定める。実装の詳細仕様は [docs/impl/11_cli-mac.md](impl/11_cli-mac.md) を参照。

## 要件（なぜ必要か）

Linux サーバ上で使う前提で作られた本環境を、開発者の手元の **macOS + Docker Desktop** でもそのまま使えるようにする。コンテナ内で動く部分（Ubuntu ベースの開発ツール・Chrome/VNC・ファイアウォール・Docker Socket Proxy）は OS に依存しないため再利用し、**ホスト側 CLI の OS 依存箇所だけ**を macOS 向けに置き換える。

## 設計原則

- **コンテナ内資産は共有**: `Dockerfile.claude` / `entrypoint-claude.sh` / `init-firewall-claude.sh` / `docker-proxy` / `tmux.conf` / `scripts/` はコンテナ内（Linux）で動くため両 OS で共有する。macOS 対応のための変更は **arm64 ネイティブ対応のアーキ別分岐**（`Dockerfile.claude` と `entrypoint-claude.sh` のみ。amd64 では従来と同一の後方互換。§5）に限り、その他は変更しない。
- **分岐はホスト側 CLI に閉じる**: OS 差分はホスト（macOS）で走る CLI スクリプトにのみ現れる。Linux 版 `claude-dev` は無変更のまま残し、macOS 版は独立した自己完結スクリプト `claude-dev-mac` として新設する。
- **利用体験は Linux 版と同一に保つ**: サブコマンド体系（`start` / `code` / `orchestrate` / `attach` / `stop` / `forward` / `list` …）と挙動は Linux 版に合わせる。macOS で成立しない機能（VM/KVM）だけを明確に拒否する。
- **インストール名は `claude-dev`**: `make install` は OS を判定し、macOS では `claude-dev-mac` を `/usr/local/bin/claude-dev` として配置する。利用者はどの OS でも `claude-dev` コマンドで操作する。
- **macOS の配置は `sudo ln -sf`（symlink）**: macOS では `/usr/local/bin` が root 所有のことが多いため、`make install` は `sudo ln -sf` でシンボリックリンクを張る（コピーはしない）。symlink 経由でも `readlink -f` が repo の実体パスへ解決するため、スクリプトは repo 内の資産（`.devcontainer/` 等）を通常どおり参照できる。Linux 版（`claude-dev`）は従来どおり（書込可能なら `ln -sf`、不可なら `sudo ln -sf` を案内）。

## Linux 依存箇所と macOS での解決

macOS 対応で解決すべき箇所は次の 5 点に集約される。うち §1〜§4 はホスト側 CLI（`claude-dev`）の OS 依存差分、§5 は CPU アーキテクチャ（共有イメージ側が中心。ホスト側はプラットフォーム非固定のみ）である。

### 1. SSH agent ソケットの転送（最重要）

**Linux 版**: ホストの `$SSH_AUTH_SOCK`（Unix ドメインソケット）をそのままコンテナへ bind mount し、コンテナ内 `SSH_AUTH_SOCK` に割り当てる。

**macOS の問題**: macOS の `$SSH_AUTH_SOCK`（launchd 由来）は **macOS ホスト上の** Unix ソケットであり、Docker Desktop の Linux VM 内で動くコンテナからは直接到達できない（ソケットは VirtioFS のファイル共有境界を越えられない）。

**解決**: Docker Desktop が Linux VM 内に用意する **魔法ソケット `/run/host-services/ssh-auth.sock`**（ホストの ssh-agent へブリッジされる）をコンテナへ bind mount する。マウント先はコンテナ内 `/tmp/ssh-agent.sock` に固定し、entrypoint 側の既存ロジック（`/tmp/ssh-agent.sock` を検出して各シェルの `SSH_AUTH_SOCK` に設定する処理）をそのまま活かす。

```
-v /run/host-services/ssh-auth.sock:/tmp/ssh-agent.sock -e SSH_AUTH_SOCK=/tmp/ssh-agent.sock
```

- 転送されるのは Docker Desktop が認識するホスト側 ssh-agent。CLI は起動前に `ensure_ssh_agent` でホスト agent に鍵を読み込む（Linux 版と同じ）。
- `/run/host-services/ssh-auth.sock` は macOS ホストのファイルシステムには見えない（VM 内にのみ存在する）。したがって CLI はこのパスの存在確認を macOS ホスト上で行わず、ホストに ssh-agent が有効（`$SSH_AUTH_SOCK` が設定済み）であることを条件にマウントを付与する。

### 2. Docker ソケットの検出

**Linux 版**: `/var/run/docker.sock` の存在（`[ -S ... ]`）で Docker の利用可否を判定し、Docker Socket Proxy へ RO マウントする。

**macOS の問題**: Docker Desktop の既定ソケットは `~/.docker/run/docker.sock`。「Allow the default Docker socket to be used」設定が有効な場合のみ `/var/run/docker.sock` が前者へのシンボリックリンクとして作られる。設定次第で `/var/run/docker.sock` が存在しないことがある。

**解決**: `/var/run/docker.sock` と `$HOME/.docker/run/docker.sock` の両方を候補として検出し（ヘルパー `detect_docker_sock` が最初に見つかったパスを標準出力に返す）、見つかったソケットを Proxy コンテナへ `-v <検出パス>:/var/run/docker.sock:ro` でマウントする。どちらも無ければ Proxy を起動せず（Docker API なしで継続）Linux 版と同じ挙動にする。

### 3. VM モード / KVM（macOS 非対応）

**Linux 版**: `--kvm` でホストの `/dev/kvm` 等をコンテナへ渡し、`--vm` でゲスト VM（QEMU+virtiofs）内のネイティブ Docker を使う。

**macOS の問題**: macOS には `/dev/kvm` が存在せず、Docker Desktop の Linux VM 内でのネスト仮想化も利用できない。VM/KVM モードは根本的に成立しない。

**解決**: macOS 版では `--kvm` / `--vm` / `--vm-fresh` を受け付けたら**理由を示して明確にエラー終了**する（`exit 1`）。KVM デバイス受け渡し・ゲスト VM 起動待ち（長時間待機）・VM 用ボリューム・`vm.env` 継承などの VM 関連ロジックは macOS 版 CLI から除去する。Docker を多用する開発は Docker Socket Proxy 経由（`/workspace` 配下 bind の書き換え許可。既定有効）で行う。

### 4. ポートフォワードの到達経路

**Linux 版**: リモートの Linux サーバで使う前提のため、フォワード確立後にクライアント PC から `ssh -O forward` で SSH トンネルを張る案内を表示する。

**macOS の問題**: macOS では利用者の手元マシン = Docker ホストであり、`docker run -p HPORT:CPORT` で公開したポートは **`localhost:HPORT`** に直接出る。SSH トンネルは不要。

**解決**: `forward` の出力・`help`・ドキュメントで、SSH トンネル手順の代わりに「ブラウザで `http://localhost:<host-port>` にアクセス」と案内する。noVNC URL も同様に手元ブラウザから直接開ける。フォワード自体の仕組み（socat プロキシコンテナ `fwd-<name>-<port>`）は Linux 版と共通。

### 5. CPU アーキテクチャ（Apple Silicon = ネイティブ arm64）

Apple Silicon の Docker Desktop は既定でコンテナを **arm64** で動かす。共有イメージ定義（`Dockerfile.claude`）には x86_64 を前提にした箇所が 2 つあり、arm64 ビルドで失敗する。**ネイティブ arm64 で動かす**ため、Dockerfile をアーキ別に対応させて解決する（エミュレーションは使わない）。

- **Google Cloud CLI**: `$(uname -m)` が arm64 コンテナ内で `aarch64` を返し、ダウンロード URL（arm64 版は `arm` 命名）が 404 になる。→ アーキ名を写像する（`aarch64`/`arm64` → `arm`、それ以外は `uname -m` のまま）。amd64 は不変で後方互換。
- **Google Chrome**: Linux 版は **arm64 バイナリが存在しない**（VNC イメージが `google-chrome-stable` を入れる）。→ アーキで分岐する:
  - **amd64**: 従来どおり Google Chrome 安定版を APT で導入（Linux サーバの挙動は不変）。
  - **arm64**: base イメージに導入済みの **Playwright Chromium**（arm64 対応・DevTools プロトコル対応）を GUI ブラウザに使う。
  - 呼び出し側（entrypoint の VNC 起動・openbox メニュー）はアーキを意識せず、共通ランチャー `/usr/local/bin/claude-dev-chrome` を叩く。ランチャーはビルド時に `google-chrome-stable` があればそれを、無ければ Playwright Chromium を起動するよう生成される。
- **その他の arch 依存**（Go/Rust/Terraform/AWS CLI/fnm/Claude Code/Docker CLI）は元々アーキ自動判定（`dpkg --print-architecture` / `uname -m` / インストーラ自動検出）で arm64 でも成立する。
- **プラットフォーム指定**: macOS 版 CLI / Makefile は `DOCKER_DEFAULT_PLATFORM` を固定しない。ホストのネイティブアーキ（Apple Silicon=arm64 / Intel Mac=amd64）でビルド/実行する。利用者が `DOCKER_DEFAULT_PLATFORM` を明示している場合のみそれを尊重する。
- **判定方法**: Dockerfile 内のアーキ分岐は `dpkg --print-architecture`（`amd64`/`arm64` を返す）で行い、BuildKit の有無に依存しない。

> この対応で `Dockerfile.claude`（VNC ステージの Chrome 導入・gcloud 導入）と `scripts/entrypoint-claude.sh`（ブラウザ起動）を変更する。いずれも **amd64 では従来と同一の成果物**になる後方互換の変更で、Linux サーバ運用に影響しない。正本は [docs/impl/40_devcontainer.md](impl/40_devcontainer.md) / [docs/impl/31_entrypoint.md](impl/31_entrypoint.md)。

## 共有資産の扱い

コンテナ内で動く資産は OS 非依存で両 OS で共有する。arm64 ネイティブ対応のため一部の共有資産にアーキ別分岐を入れるが、**amd64 では従来と同一の成果物**になる後方互換の変更で、Linux サーバ運用に影響しない。

| 資産 | 扱い |
|------|------|
| `.devcontainer/Dockerfile.claude` | **arch 別分岐を追加**（§5）: gcloud のアーキ名写像、VNC ステージのブラウザ（amd64=Chrome / arm64=Playwright Chromium）と共通ランチャー `claude-dev-chrome` 生成。`USER_UID`/`USER_GID`（macOS で 501/20）や GID 20 衝突解消は従来どおり |
| `scripts/entrypoint-claude.sh` | **ブラウザ起動を `claude-dev-chrome` 経由に変更**（§5）。UID/GID 追従・認証共有・MCP 設定・VNC 起動等の他ロジックは OS 非依存で不変。SSH ソケットは `/tmp/ssh-agent.sock` を見る既存ロジックを macOS 版もそのまま使う |
| `scripts/init-firewall-claude.sh` | 不変。コンテナ内の iptables 設定。`--cap-add NET_ADMIN`/`NET_RAW` は Docker Desktop でも有効 |
| `docker-proxy/`（Go） | 不変。`/workspace` bind の実ホストパスへの書き換えは Docker API から取得したマウント元をそのまま使うため、ホストパスが macOS の `/Users/...` でも問題なく機能する |
| `scripts/tmux.conf` | 不変。OS 非依存 |

## macOS 前提条件

- macOS（Apple Silicon / Intel いずれも Docker Desktop が動作すること）
- Docker Desktop（Docker Engine + CLI 同梱）
- `jq`（`claude-dev` の `start` がホストの `~/.claude/settings.json` から hooks/env を抽出するのに使用。`brew install jq`）
- Claude Pro / Max プラン（OAuth 認証）
- SSH 鍵を使う場合は Docker Desktop がホストの ssh-agent を認識していること（§1 の注意参照）

## 関連文書

- 実装仕様: [docs/impl/11_cli-mac.md](impl/11_cli-mac.md)（`claude-dev-mac` と 1:1）
- Linux 版 CLI 実装仕様: [docs/impl/10_cli.md](impl/10_cli.md)
- アーキテクチャ全体: [docs/02_architecture.md](02_architecture.md)
- VM モード（Linux 専用）: [docs/08_vm-mode.md](08_vm-mode.md)
