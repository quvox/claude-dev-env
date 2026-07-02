---
summary: 脅威モデルと多層防御（コンテナ隔離・Docker Socket Proxy・ファイアウォール・SSH agent転送）の設計意図を説明するセキュリティ設計文書。
keywords: [ セキュリティ, 脅威モデル, ファイアウォール, Docker Socket Proxy, コンテナ隔離, KVM, ブラックリスト ]
---

# セキュリティ設計

> **この文書の役割**: 本環境の脅威モデルと多層防御（コンテナ隔離・マウント制限・Docker Socket Proxy・ファイアウォール等）の設計意図を説明する設計文書。

## 脅威モデル

Claude Code を `--dangerously-skip-permissions` で実行すると、コマンド実行やファイル操作が無制限になる。想定される脅威:

| 脅威 | 説明 |
|------|------|
| ファイル窃取 | プロジェクト外のファイル（SSH 鍵、AWS 認証等）の読み取り |
| 認証情報窃取 | OAuth トークンの読み取り・外部送信 |
| データ外部送信 | ソースコードや秘密情報をペーストサイトや Webhook へ送信 |
| メタデータアクセス | クラウドインスタンスのメタデータから IAM 認証情報を取得 |
| リバースシェル | 外部への SSH 接続やトンネリングで永続的アクセスを確立 |
| メール送信 | SMTP 経由でデータを送信 |
| コンテナ脱獄 | Docker ソケット経由でホストを操作 |

## 防御層

### 1. Docker コンテナ隔離

Claude Code はコンテナ内で実行される。ホストのファイルシステムには直接アクセスできない。

**Claude コンテナにマウントされるもの:**
- プロジェクトディレクトリ → `/workspace`（読み書き）
- 認証情報ボリューム → `~/.claude-shared/`（読み書き、認証ファイルのみ。`~/.claude/` にコピーして使用）
- 共有シェル設定ボリューム → `~/.config-shared/`（読み書き、`.zshrc` をコンテナ間共有）
- CLAUDE.md、tmux.conf（読み取り専用）
- コマンド履歴ボリューム
- `~/.gitconfig`（読み取り専用、存在時のみ）
- `~/.ssh/known_hosts`、`~/.ssh/config`（読み取り専用、存在時のみ）
- SSH agent ソケット（読み取り専用、存在時のみ）

**マウントされないもの:**
- `~/.ssh/id_rsa`、`~/.ssh/id_ed25519` 等の秘密鍵ファイル
- `~/.aws/`（AWS 認証）
- `~/.config/`（各種設定）
- `.env`（環境変数ファイル）
- Docker ソケット

### 2. 認証情報の保護

認証情報は `claude-dev-auth` ボリュームに保存され、`~/.claude-shared/` にマウントされる。コンテナ起動時に認証ファイルのみが `~/.claude/`（`start` では `/workspace/.claude/` への symlink）にコピーされる。

```
claude-dev-auth ボリューム
    │
    ├── login 時: ~/.claude-shared/ にマウント
    │    └── 一時コンテナが起動時に ~/.claude/ へコピー → Claude Code が書込
    │         → /exit 時に ~/.claude-shared/ へ書き戻し
    │
    └── start 時: ~/.claude-shared/ にマウント (RW)
         ├── claude-dev CLI が認証ファイルを /workspace/.claude/ にコピー
         └── entrypoint が ~/.claude → /workspace/.claude を symlink 化、
              パーミッション調整、~/.claude.json への symlink 作成、
              30 秒ごとに変更を ~/.claude-shared/ に書き戻し
```

**制限事項:** Claude Code は認証情報（`~/.claude.json`, `~/.claude/`）を読み取れるため、完全な隔離はできない。ファイアウォールによる窃取先のブロックと組み合わせて防御する。

### 3. ブラックリスト方式ファイアウォール

iptables + ipset による送信トラフィック制御。

#### ブロック対象ドメイン

| カテゴリ | ドメイン |
|----------|---------|
| ペーストサイト | pastebin.com, paste.ee, hastebin.com, dpaste.org |
| ファイル共有 | transfer.sh, file.io, 0x0.st, ix.io, sprunge.us |
| Webhook テスト | webhook.site, requestbin.com, hookbin.com |
| トンネリング | ngrok.io, ngrok-free.app, localtunnel.me, serveo.net |

#### ブロック対象 IP/ポート

| 対象 | 理由 |
|------|------|
| `169.254.169.254` | AWS/GCP メタデータエンドポイント |
| `169.254.169.253` | Azure メタデータエンドポイント |
| TCP 25, 465, 587 | SMTP（メール送信によるデータ窃取） |
| TCP 22（外部向け） | リバースシェル防止（内部ネットワークは許可） |

#### デフォルトポリシー

デフォルトは **ACCEPT**（ブラックリスト方式）。Claude Code が npm, pip, apt, GitHub 等に自由にアクセスできる利便性を維持しつつ、既知の危険な宛先をブロックする。

### 4. ブラウザのコンテナ内統合

VNC ありコンテナ（`claude-dev-claude-vnc`）では、Google Chrome + TigerVNC がコンテナ内で直接動作する。

- Chrome はコンテナ内の Xvnc ディスプレイ上で動作し、Claude Code が chrome-devtools MCP サーバー経由で操作する
- noVNC ポートはコンテナごとに個別割り当て（6080〜）
- VNC なしコンテナ（`--no-vnc`）には Chrome / VNC がインストールされない
- Chrome プロファイルは `claude-dev-chrome-data` ボリュームに保存される

### 5. Docker Socket Proxy（Docker API の制限付き公開）

Claude Code がプロジェクト開発中に `docker` / `docker compose` コマンドを使えるよう、Docker API へのアクセスを提供する。ただし、生の Docker ソケット (`/var/run/docker.sock`) を直接マウントすると事実上のホスト root 権限を与えることになるため、**リクエストボディを検査するプロキシコンテナ**を経由させる。

#### 背景：生ソケットマウントのリスク

Docker ソケットへの無制限アクセスは以下を可能にする:

| 攻撃 | 手法 |
|------|------|
| コンテナ脱獄 | ホストの `/` をマウントした特権コンテナを起動 |
| 秘密情報の窃取 | `~/.ssh/`, `~/.aws/` 等をマウントしたコンテナを作成 |
| ファイアウォール迂回 | ファイアウォールのない新コンテナから外部にデータ送信 |
| 他コンテナの操作 | 他プロジェクトのコンテナを inspect / exec |

これらのリスクを排除するため、Claude コンテナには生の Docker ソケットをマウントせず、proxy 経由でのみ Docker API にアクセスさせる。

#### 設計

```
┌─ Claude コンテナ ────────────────────────────────┐
│  DOCKER_HOST=tcp://claude-dev-docker-proxy:2375  │
│  /var/run/docker.sock は存在しない               │
└──────┬───────────────────────────────────────────┘
       │ HTTP (claude-dev-net 内)
       ▼
┌─ Docker Socket Proxy コンテナ ───────────────────┐
│  claude-dev-docker-proxy                         │
│                                                  │
│  リクエストを受信 → ボディを検査 → 許可/拒否      │
│                                                  │
│  /var/run/docker.sock (RO) ← ホストからマウント   │
└──────────────────────────────────────────────────┘
```

Claude コンテナには Docker ソケットが存在しないため、proxy を迂回して Docker API にアクセスする手段はない。

#### API 許可/拒否ポリシー

proxy はリクエストのエンドポイントとボディを検査し、以下のポリシーで許可/拒否を判定する。

**コンテナ作成 (`POST /containers/create`) の検査項目:**

| 検査項目 | ルール | 理由 |
|----------|--------|------|
| `HostConfig.Binds` | **拒否**: ホストパスのバインドマウント | ホストファイルシステムへのアクセス防止 |
| `HostConfig.Privileged` | **拒否**: `true` | 特権コンテナによるホスト操作防止 |
| `HostConfig.PidMode` | **拒否**: `"host"` | ホストプロセス名前空間への侵入防止 |
| `HostConfig.NetworkMode` | **拒否**: `"host"` | ホストネットワーク名前空間への侵入防止 |
| `HostConfig.UsernsMode` | **拒否**: `"host"` | ホストユーザー名前空間への侵入防止 |
| `HostConfig.CapAdd` | **拒否**: 危険な capability（`SYS_ADMIN`, `SYS_PTRACE` 等） | 権限昇格防止 |
| `HostConfig.Devices` | **拒否**: デバイスマッピング | ホストデバイスへのアクセス防止 |
| `Volumes` (named volume) | **許可** | Docker 管理ボリュームは安全 |

**エンドポイント別の許可/拒否:**

| エンドポイント | 許可 | 用途 |
|---------------|------|------|
| `GET /containers/*` | Yes | `docker ps`, `docker logs`, `docker inspect` |
| `POST /containers/create` | 条件付き | 上記の検査を通過した場合のみ |
| `POST /containers/{id}/start,stop,restart,kill` | Yes | コンテナのライフサイクル管理 |
| `POST /containers/{id}/exec` | Yes | `docker exec` |
| `DELETE /containers/{id}` | Yes | `docker rm` |
| `GET /images/*` | Yes | イメージ一覧・詳細 |
| `POST /images/create` | Yes | `docker pull` |
| `POST /build` | Yes | `docker build` |
| `GET /networks/*` | Yes | ネットワーク一覧・詳細 |
| `GET /volumes/*` | Yes | ボリューム一覧・詳細 |
| `POST /volumes/create` | Yes | ボリューム作成 |
| `GET /version`, `GET /_ping`, `GET /info` | Yes | Docker 情報取得 |
| `GET /events` | Yes | イベントストリーム |

**明示的に拒否するエンドポイント（メソッド問わずパス前方一致で全面拒否）:**

| エンドポイント | 理由 |
|---------------|------|
| `/swarm/*` | Swarm 操作はホストクラスタに影響 |
| `/plugins/*` | プラグイン操作はホストに影響 |
| `/configs/*`, `/secrets/*` | Swarm の秘密情報操作 |

**exec 作成 (`POST /containers/{id}/exec`) の検査:** `Privileged: true` の exec は拒否する（通常の exec は許可）。

**接続ハイジャックが必要なエンドポイント（拒否ではなく中継）:** `POST /exec/{id}/start`、`POST /containers/{id}/attach`、`POST /exec/{id}/resize`、`POST /containers/{id}/resize` は HTTP コネクションのアップグレード（`Upgrade: tcp`）を伴うストリーミングのため、proxy が生 TCP で双方向中継する（`docker exec -it` / `docker attach` を機能させるため。**拒否はしない**）。

#### 攻撃耐性

| 攻撃 | 結果 | 理由 |
|------|------|------|
| ホストマウント付きコンテナ作成 | **拒否** | proxy が `Binds` を検査して拒否 |
| privileged コンテナ作成 | **拒否** | proxy が `Privileged` フラグを検査して拒否 |
| Docker ソケットに直接アクセス | **不可** | Claude コンテナにソケットがマウントされていない |
| proxy コンテナに `docker exec` | **可だが無害** | proxy 内にはソケットの読み取りアクセスのみ |
| Docker daemon の TCP ポートに接続 | **不可** | daemon はデフォルトで TCP リッスンしない |

#### 残存リスク

proxy 方式で防げないケース:

- **許可された操作範囲内での悪用**: `docker compose up` で正規のコンテナを起動する際、そのコンテナにファイアウォールが適用されず、データを外部送信するリスクがある。対策として、proxy が作成コンテナを `claude-dev-net` に強制接続する、またはファイアウォールルールを注入する方法が考えられる
- **カーネル脆弱性によるコンテナ脱獄**: Docker ソケットとは無関係の一般的な Docker リスクであり、proxy では防げない

#### ホスト Docker Engine への影響

proxy コンテナ方式は Docker Engine の設定を一切変更しない。

| 項目 | 影響 |
|------|------|
| `/etc/docker/daemon.json` | 変更なし |
| Docker Engine の再起動 | 不要 |
| proxy が停止/クラッシュした場合 | Claude コンテナの `docker` コマンドが失敗するのみ。ホストの Docker 操作には影響なし |
| 他のコンテナ/サービス | 影響なし（proxy を使うのは Claude コンテナだけ） |

### 6. SSH agent 転送（秘密鍵の隔離）

コンテナ内で `git push` 等の SSH 操作を可能にしつつ、秘密鍵ファイルはマウントしない。

- **SSH agent ソケット** (`SSH_AUTH_SOCK`) のみをコンテナに転送
- agent は「この鍵で署名して」というリクエストを中継するだけで、秘密鍵のバイト列を取り出す API はない
- コンテナ内で `cat ~/.ssh/*` や `ls ~/.ssh/` しても秘密鍵は存在しない
- `~/.ssh/known_hosts` と `~/.ssh/config` は読み取り専用でマウント（秘密情報を含まない）
- `claude-dev start` 時にホスト側で ssh-agent を自動起動し、鍵が未登録なら `ssh-add` を実行

### 7. 非 root 実行

Claude コンテナはビルド時にホストと同じ UID/GID でユーザーを作成する。entrypoint では `/workspace` の所有者と差異がある場合に UID/GID を合わせる。既存のシステムユーザー/グループと競合する場合は、競合エントリを退避してから変更する。

### 8. git による変更の可逆性

プロジェクトディレクトリはホスト上の git リポジトリそのもの。Claude Code が行った変更はすべて `git diff` で確認でき、`git checkout` で元に戻せる。

## KVM デバイスの扱いと特権の非対称性

Claude コンテナはハードウェア仮想化（KVM/QEMU）を利用できるが、これはデバイス渡しによる**限定的な特権付与**であり、セキュリティ上の含意を理解しておく必要がある。

- **デバイス渡しの条件**: 既定では KVM デバイスを渡さない（通常は Chrome 操作のみで十分）。`claude-dev start --kvm` を明示したとき**のみ**、ホストに存在する `/dev/kvm`・`/dev/vhost-net`・`/dev/net/tun` を `--device` でコンテナに渡す。privileged ではなく、個別デバイスのみを渡す。これにより、仮想化を使わない通常セッションではコンテナにデバイスが一切渡らず、攻撃面を最小化できる。
- **用途**: Claude コンテナ**内で直接** `qemu-system-x86` を実行して VM を起動する用途（CPU 仮想化・ゲストの高速ネットワーク・TUN/TAP）。
- **proxy との非対称性（重要）**: Docker Socket Proxy は `POST /containers/create` の `Devices` マッピングを**全面拒否**する。したがって Claude が proxy 経由で生成するコンテナには `/dev/kvm` 等を渡せない。KVM は「Claude コンテナ内で直接 QEMU を動かす」用途に限られ、「`--device` 付きの特権サイドカーコンテナを生やす」ことはできない。
- **リスク評価**: `/dev/kvm` への直接アクセス自体は KVM の ioctl に限定され、コンテナ脱獄に直結はしない。ただしデバイス渡し一般はコンテナ隔離をわずかに緩める。`/dev/net/tun` はネットワーク面の自由度を上げる。本環境は既定でデバイスを渡さず（`--kvm` オプトイン）、仮想化が必要なセッションに限って隔離を緩める設計としている。
- **VM モードのセキュリティ上の位置づけ（設計確定・未実装。正本 [docs/08_vm-mode.md](08_vm-mode.md) / [docs/impl/80_vm-mode.md](impl/80_vm-mode.md)）**: Docker を多用する開発向けに、`--vm` でゲスト VM（QEMU+virtiofs）を起動しその中でネイティブ Docker を動かす。**claude コンテナは privileged 化せず**（付与は `--kvm` のデバイスのみ）、bind mount・privileged 等の危険操作は**ハードウェア仮想化の VM 境界に封じ込め**られる（自律エージェントの Docker 作業を VM に隔離でき、暴走時はスナップショット/破棄で復旧可）。ゲストの Docker API は hostfwd で **claude コンテナの `127.0.0.1` にのみ**露出（非TLS・ネットワーク非公開）。ゲストの外向き通信は user-mode ネット（SLIRP）＝qemu プロセス経由のため**既存の egress firewall が引き続き適用**される。

## ブラックリストの限界と対策

ブラックリスト方式は利便性を優先した設計であり、すべてのデータ窃取を防げるわけではない。

### 防げないケース

- 未知のドメインへの送信
- DNS 経由のデータ窃取（DNS tunneling）
- 許可されたサービス（GitHub 等）を経由した間接的な送信

### 強化方法

#### 本番環境ドメインの追加

`scripts/init-firewall-claude.sh` の `BLACKLIST_DOMAINS` 配列に追加:

```bash
BLACKLIST_DOMAINS=(
    # 既存のリスト...

    # 本番環境
    "production-api.yourcompany.com"
    "prod-db.yourcompany.com"
)
```

#### ホワイトリスト方式への切替

最も安全な構成。必要なドメインのみ許可する:

```bash
# デフォルトポリシーを DROP に変更
iptables -P OUTPUT DROP

# 必要なドメインのみ許可
iptables -A OUTPUT -d <npm-registry-ip> -j ACCEPT
iptables -A OUTPUT -d <github-ip> -j ACCEPT
iptables -A OUTPUT -d <anthropic-api-ip> -j ACCEPT
```

ホワイトリスト方式では `npm install` や `git clone` が制限されるため、必要なドメインを事前に洗い出す必要がある。

