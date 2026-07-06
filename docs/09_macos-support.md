---
summary: macOS（Docker Desktop）上で Claude Code 安全開発環境を動かすための設計文書。Linux 版 claude-dev の OS 依存箇所を洗い出し、macOS 版 CLI（claude-dev-mac）での解決方針（SSH agent はプロジェクト（ディレクトリ）ごとの専用 agent＋socat TCP ブリッジで転送＝鍵はプロジェクト設定 .claude-dev.yaml の ssh_keys のみ（グローバルへのフォールバックなし。鍵解決・ssh-keys サブコマンドは両 OS 共通）・Docker ソケット検出・VM/KVM 非対応・ポート直結・Apple Silicon の arm64 ネイティブ対応＝Playwright Chromium／gcloud アーキ写像・install は sudo symlink）を定める。
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

### 1. SSH agent の転送（最重要。方式 D: claude-dev 専用 agent＋TCP ブリッジ。プロジェクト単位で鍵を隔離）

**Linux 版**: claude-dev がプロジェクト専用 ssh-agent（`~/.claude-dev/agents/<name>.sock`）を起動して解決した鍵だけを登録し、その **Unix ドメインソケットをコンテナへ直接 bind mount** して `SSH_AUTH_SOCK` に割り当てる（ホストの環境 agent を丸ごと転送するわけではない。詳細は [impl/10_cli.md](impl/10_cli.md)）。macOS で問題になるのはこの「Unix ドメインソケットを bind mount する」手段の方である。

**macOS の問題**:
- (a) macOS の Unix ドメインソケットは Docker Desktop の Linux VM 内コンテナへ bind mount しても機能しない（ソケットは VirtioFS のファイル共有境界を越えられない）。
- (b) Docker Desktop の魔法ソケット `/run/host-services/ssh-auth.sock` が転送するのは **Docker Desktop が握る既定 agent** に限られ、利用者が別 agent（例: Strongbox）や既定 agent 外に鍵を持つと**空 agent** になる。
- (c) その魔法ソケットは `root:root 0660` で、非 root のコンテナユーザー（`dev` 等）からは `Permission denied` で使えない。

**解決（方式 D）**: どのホスト agent 構成にも依存せず、claude-dev が**自前の ssh-agent を鍵ファイルから構築**し、127.0.0.1 の TCP ブリッジ経由でコンテナへ転送する。これにより **全 Mac で同一挙動・同一鍵**になり、Strongbox 等「その機の agent が何か」に一切依存しない（(b) 解決）。専用ソケットはユーザー所有で作るため (c) も解決。VM 境界は TCP で越える（(a) 解決）。

- **鍵の選択（プロジェクトのローカル設定のみ）**: 転送する鍵は**そのプロジェクト直下の `<PROJECT_DIR>/.claude-dev.yaml` の `ssh_keys` だけ**を見る。グローバル `~/.config/claude-dev.yaml` へのフォールバックや自動生成、`start` 時の対話選択は**行わない**。`.claude-dev.yaml` が無い/`ssh_keys` が空なら SSH 転送なしで起動する。
  - **選択の作成/変更**: `claude-dev ssh-keys` を実行すると `~/.ssh/id_*`（`.pub` 除く）を列挙して**対話選択**させ、選んだパスを**カレントプロジェクトの `.claude-dev.yaml`** に書き込む（手書きでも同形式で設定可）。
  - **選択のリセット**: `claude-dev ssh-keys reset` でカレントプロジェクトの `.claude-dev.yaml` から `ssh_keys` を除去し（ssh_keys だけのファイルは削除、他の記述があれば残す）、**このプロジェクト（`container_name`）の専用 agent とブリッジ socat を停止**して `<name>.sock`/`<name>.pid`/`<name>.bridge.pid`/`<name>.bridge.port` を削除する（旧・単一 agent/ブリッジの残骸も掃除）。次回 `start` で再選択（または `.claude-dev.yaml` を作成）。
- **専用 agent（プロジェクトごと）**: ホストにプロジェクト専用 ssh-agent（ソケット `~/.claude-dev/agents/<name>.sock`、`<name>` = ディレクトリ名）を起動し、そのプロジェクトで解決した鍵だけを `ssh-add`（既登録鍵は指紋照合でスキップ＝パスフレーズ再入力なし）。利用者の個人 agent（Strongbox 等）とは完全に独立で、**別プロジェクトの鍵は見えない**。
- **TCP ブリッジ（プロジェクトごと）**: ホストで `socat TCP-LISTEN:<port>,bind=127.0.0.1,fork,reuseaddr` ↔ `UNIX-CONNECT:~/.claude-dev/agents/<name>.sock` を常駐させ、コンテナ側 entrypoint が `socat UNIX-LISTEN:/tmp/ssh-agent.sock,fork,mode=600`（ユーザー所有・0600）↔ `TCP:host.docker.internal:<port>` を張って `SSH_AUTH_SOCK=/tmp/ssh-agent.sock` を各シェルに設定する。CLI は `docker run` に `-e CLAUDE_DEV_SSH_BRIDGE_PORT=<port>` を渡す。（listen を 127.0.0.1 に限定するのは socat の `bind=` オプション。`TCP-LISTEN:` の第1引数はポート番号のみ。）
- **ポート（プロジェクトごと）**: `.env` の `CLAUDE_DEV_SSH_BRIDGE_PORT` があればそれを使い、無ければ空き 127.0.0.1 ポートを確保して `~/.claude-dev/agents/<name>.bridge.port` に記録・再利用する（**プロジェクトごとに 1 つ**。稼働中の別プロジェクトのブリッジがポートを占有するため衝突しない）。
- **前提**: ホストに `socat`（`brew install socat`）。`host.docker.internal` は Docker Desktop が提供（要到達確認済み）。
- **露出範囲と寿命**: ブリッジは **127.0.0.1 のみ**に listen し、**そのプロジェクトのコンテナが稼働している間だけ**起動する（`stop` でそのプロジェクトのブリッジを停止。専用 agent は鍵を保持したまま常駐＝TCP 露出なし。例外として `ssh-keys reset` 時のみそのプロジェクトの専用 agent も停止する）。露出するのは**そのプロジェクトで選択した鍵だけ**（個人 agent 全体でも、他プロジェクトの鍵でもない）。
- **魔法ソケット方式は使用しない**（`/run/host-services/ssh-auth.sock` のマウントは廃止）。Linux 版の `$SSH_AUTH_SOCK` 直 bind mount も macOS 版には存在しない。
- `~/.ssh/known_hosts` / `~/.ssh/config`（`IdentityFile`/`IdentitiesOnly`/**`IdentityAgent`** 行を除去した一時コピー）の RO マウントは従来どおり。`IdentityAgent` を除去するのは、ホスト固有の agent パス（例 Strongbox の `~/.strongbox/agent.sock`）がコンテナ内で `SSH_AUTH_SOCK`（ブリッジ）を上書きし agent を不通にするため。ホストの `~/.ssh/config` 実体は変更しない（sed 出力は別の一時ファイル）。

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
| `scripts/entrypoint-claude.sh` | **ブラウザ起動を `claude-dev-chrome` 経由に変更**（§5）、および **SSH ブリッジ分岐を追加**（§1）: `CLAUDE_DEV_SSH_BRIDGE_PORT` が渡された場合、コンテナ側 `socat` で `/tmp/ssh-agent.sock`↔`host.docker.internal:<port>` を張り `SSH_AUTH_SOCK` を設定する（未設定なら従来どおり `/tmp/ssh-agent.sock` の存在で判定）。UID/GID 追従・認証共有・MCP 設定・VNC 起動等の他ロジックは OS 非依存で不変 |
| `scripts/init-firewall-claude.sh` | 不変。コンテナ内の iptables 設定。`--cap-add NET_ADMIN`/`NET_RAW` は Docker Desktop でも有効 |
| `docker-proxy/`（Go） | 不変。`/workspace` bind の実ホストパスへの書き換えは Docker API から取得したマウント元をそのまま使うため、ホストパスが macOS の `/Users/...` でも問題なく機能する |
| `scripts/tmux.conf` | 不変。OS 非依存 |

## macOS 前提条件

- macOS（Apple Silicon / Intel いずれも Docker Desktop が動作すること）
- Docker Desktop（Docker Engine + CLI 同梱）
- `jq`（`claude-dev` の `start` がホストの `~/.claude/settings.json` から hooks/env を抽出するのに使用。`brew install jq`）
- `socat`（SSH agent の TCP ブリッジに使用。`brew install socat`。§1。SSH 鍵を使わないなら不要）
- Claude Pro / Max プラン（OAuth 認証）
- SSH 鍵を使う場合: 秘密鍵ファイルが `~/.ssh/` にあること。使う鍵はプロジェクト直下の `.claude-dev.yaml` の `ssh_keys` で指定する（`claude-dev ssh-keys` で対話選択→そのファイルに保存、または手書き。§1）。ホストの個人 agent（Strongbox 等）には依存しない

## 関連文書

- 実装仕様: [docs/impl/11_cli-mac.md](impl/11_cli-mac.md)（`claude-dev-mac` と 1:1）
- Linux 版 CLI 実装仕様: [docs/impl/10_cli.md](impl/10_cli.md)
- アーキテクチャ全体: [docs/02_architecture.md](02_architecture.md)
- VM モード（Linux 専用）: [docs/08_vm-mode.md](08_vm-mode.md)
