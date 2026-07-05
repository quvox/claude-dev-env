---
summary: Docker を多用する開発のために、claude コンテナ内で QEMU/KVM のゲスト VM を起動し、その中でネイティブ Docker を動かす「VM モード」の設計文書。virtiofs で /workspace を同一パス共有してライブ編集を保ち、ゲストの dockerd を DOCKER_HOST で claude 側エージェントから使う。bind mount・privileged 等を VM 境界に隔離して安全に許す。
keywords: [ VMモード, QEMU, KVM, virtiofs, Docker, 隔離, DOCKER_HOST ]
---

# VM モード（QEMU + virtiofs で Docker をネイティブに動かす）設計

> **この文書の役割**: Docker を多用するシステム（bind mount・compose・privileged 等）を、既存の DooD（socket proxy 経由でホスト daemon を叩く）構成の制約なしに開発するための「VM モード」を設計する。実装仕様は [docs/impl/80_vm-mode.md](impl/80_vm-mode.md)。セキュリティ上の位置づけは [docs/03_security.md](03_security.md)、既存の KVM デバイス受け渡しは同 §KVM を参照。

## 1. 背景と要件（なぜ必要か）

既定構成では claude コンテナは `DOCKER_HOST` → **Docker Socket Proxy** → ホスト daemon（DooD＝兄弟コンテナ）で Docker を使う。proxy はセキュリティのため **privileged・device・host network を拒否し、ホスト bind mount も原則拒否**する（例外として `/workspace` 配下の bind は proxy が実ホストパスへ書き換えて許可する＝[docs/03_security.md](03_security.md) §5）。このため **privileged や `/workspace` 外の bind を含む** Docker 中心のシステム開発は DooD 経路では成立しない（proxy が拒否・DooD のパス不一致）。

VM モードは、**ハードウェア仮想化（KVM）の境界の中でネイティブ Docker を動かす**ことでこれを解決する。VM 内では bind mount も privileged も compose も制限なく使え、その影響は VM に封じ込められるため、**claude コンテナを privileged 化せず**（＝既存の隔離・proxy・firewall を壊さず）に Docker 中心開発を可能にする。

要件:
- **R1 ネイティブ Docker**: ゲスト内で bind mount 等を含む通常の Docker/compose がそのまま動く。
- **R2 ライブ編集**: claude 側（エージェント）でコードを編集すると、ゲスト内 Docker の bind mount に**即反映**される。
- **R3 既存エージェント資産の流用**: orchestrator/worker などのエージェントは claude コンテナ側で動いたまま、`docker` コマンドでゲストの daemon を操作できる。
- **R4 隔離維持**: claude コンテナは privileged にしない。必要なのは `/dev/kvm` 等のデバイス渡し（既存 `--kvm`）のみ。VM は使い捨て・スナップショット可能な隔離サンドボックス。
- **R5 オプトイン**: 既定は従来の軽量コンテナ（移植性・密度）。VM モードは重い Docker 案件のときだけ有効化する。

## 2. 位置づけ（既存機能との関係）

| 機能 | 既存 | 本設計 |
|---|---|---|
| `--kvm` デバイス渡し | `/dev/kvm`・`/dev/net/tun` を claude コンテナへ渡す（[04](04_cli-reference.md)/[03](03_security.md)） | **前提として再利用**（VM モードは `--kvm` を含意） |
| computer-use GUI VM（[05](05_customization.md) §C） | `guest.qcow2` を `:99` に表示し MCP で操作する**手動 GUI** 用途 | 別用途（本設計は**ヘッドレスな Docker 実行環境**） |
| DooD + socket proxy | 既定の Docker 経路 | VM モード時は**ゲスト dockerd に切替**（proxy 経路は VM を使わない操作用に併存可） |

VM モードは既存の「素の QEMU が叩ける」状態を、**管理された起動・共有・接続・ライフサイクル**として作り込むもの。

## 3. アーキテクチャ

```
┌ claude コンテナ（非 privileged, --kvm でデバイスのみ付与）──────────────┐
│  エージェント / orchestrator / worker（従来どおりここで動く）              │
│    └ docker CLI  ──DOCKER_HOST=tcp://127.0.0.1:2375──┐                    │
│  /workspace（ホストからの bind。コードの正本）        │ hostfwd            │
│    └ virtiofsd（/workspace を共有）───────┐          │                    │
│  qemu-system-x86_64 -enable-kvm           │ vhost-user-fs              │
│    ├ virtio-net (user-mode, hostfwd)  ────┼── 127.0.0.1:2375→guest:2375 │
│    └ memory-backend-memfd (share=on)      │      + アプリ用ポート        │
│  ┌ ゲスト VM（Ubuntu, Docker 入り）────────▼───────────────────────────┐ │
│  │  virtiofs を /workspace に mount（**ホストと同一パス**）             │ │
│  │  dockerd（127.0.0.1:2375 で待受）                                   │ │
│  │    └ アプリのコンテナ: -v /workspace/app:/app が普通に効く＋ライブ   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.1 コード共有（R2 の要）＝ virtiofs 同一パス
- `virtiofsd` が claude コンテナの `/workspace` を共有し、ゲストは**同じ `/workspace` にマウント**する。
  - **既知の制約（uid）**: virtiofsd は uid 1000 で動くため、ゲスト内コンテナが bind mount 先を別 uid へ `chown` する処理（mysql/grafana 等がデータディレクトリを chown）は `operation not permitted` で失敗する。**bind mount でコンテナ管理データ（DB 等）を置くスタックは VM モードでは完全動作しない**（名前付きボリューム化で回避）。詳細と背景は [docs/impl/80_vm-mode.md](impl/80_vm-mode.md)。
- これにより、ゲスト内で `docker run -v /workspace/app:/app` としても、bind source `/workspace/app` は**ゲスト FS 上に存在**し（virtiofs 経由で claude/ホストの実体と同一）、**bind mount が成立しつつホスト側編集がライブ反映**される（DooD のパス不一致・proxy 制約の両方を回避）。
- compose の相対 bind も、`/workspace` 配下で実行すれば同様に成立。

### 3.2 ゲスト Docker への接続（R3）
- ゲストで `dockerd` を **`0.0.0.0:2375`（ゲスト内 TCP）＋ unix socket（`-H fd://`）** で待受（tcp を 0.0.0.0 にするのは、QEMU user-mode hostfwd がゲストの SLIRP IP 宛に転送し 127.0.0.1 では届かないため。露出は claude コンテナの hostfwd 経由のみ＝実質コンテナ内限定）。unix socket は `docker build --ssh` 等ゲスト内直操作用。
- QEMU user-mode ネットの **hostfwd** で claude コンテナの `127.0.0.1:2375` → ゲスト `:2375` に転送。
- claude 側は `DOCKER_HOST=tcp://127.0.0.1:2375` を設定 → 既存のエージェント/worker がそのままゲスト daemon を操作。
- **orchestrator（`claude-dev orchestrate`）**: 対話 TUI と違い**非対話コマンド**として起動されるため rc（vm.env）を自動では読まない。`claude-dev orchestrate` が起動前に `/etc/claude-dev/vm.env` を source して**ゲスト `DOCKER_HOST` を明示的に引き継ぐ**。worker（`claude -p`）は orchestrator の環境（`claudeChildEnv`）を継ぐため、worker の `docker` もゲストを指す。worktree は `/workspace/.orchestrator/worktrees/…`＝`/workspace` 配下なので virtiofs 共有され、worker の bind mount（同一パス）も成立する。
- アプリのサービスポートは **自動で** hostfwd され claude 側 `127.0.0.1:<port>` に露出する。常駐の port 同期（`vm-portsync.sh --loop`）がゲストの公開ポートを定期検出し QMP（`human-monitor-command` 経由の `hostfwd_add`）で張るため、`docker compose up` 等で公開すれば追加設定なしに `127.0.0.1:<port>` へ到達できる（`VM_PORTS` による起動時固定指定も併用可）。noVNC ブラウザからの確認はポートフォワード（既存 `claude-dev forward`）と組み合わせる。

### 3.3 ゲストイメージ（Ubuntu cloud image を provision）
- 公式 Ubuntu cloud image（qcow2）をベースに、**cloud-init（seed）または provision スクリプトで Docker と virtiofs 自動マウント・dockerd TCP 待受・スワップ確保を投入**して初回ビルド。
- **スワップを必ず確保する（既定 2G のスワップファイル）**。cloud image は既定でスワップを持たず、ゲスト RAM が埋まると（スワップ無しでは）カーネルのページ回収が空回りしてゲスト全体が stall する（＝「異常に遅い」の主因）。スワップがあれば RAM 超過が致命的スラッシングにならず緩やかに劣化する。RAM 既定は 8192M（既定値の正本は実装仕様 [docs/impl/80_vm-mode.md](impl/80_vm-mode.md) §4）。
- ビルド成果物（qcow2）は**名前付きボリュームにキャッシュ/永続化**（コンテナ作り直しで消えない）。
- Ubuntu の標準カーネルは `virtiofs`（`CONFIG_VIRTIO_FS`）対応のため追加カーネルビルドは不要。

### 3.4 ssh-agent の扱い
既定では host の ssh-agent が claude コンテナへ forward される（`SSH_AUTH_SOCK=/tmp/ssh-agent.sock`、秘密鍵はコンテナに入れない。[docs/03_security.md](03_security.md)）。VM モードではゲストは別マシンで、**virtiofs は unix ドメインソケットを転送できない**（ソケットは通常ファイルではなく、パス共有ではエンドポイントが繋がらない）ため、socket をそのまま共有しても agent は使えない。方針:

- **A（既定・推奨）: SSH/git は claude コンテナ側に残す**。ゲストは Docker 実行専用とし、`git push/pull` 等の SSH を要する操作は claude 側エージェント（既存 ssh-agent がそのまま有効）で行う。→ **ゲストに agent 不要**。
- **B（オプトイン）: ゲスト内でも agent が要る場合**（`docker build --ssh`、`vm shell` からの git 等）は、user-mode ネット経由で agent を転送する。claude 側 `socat TCP-LISTEN:<p>,fork UNIX-CONNECT:/tmp/ssh-agent.sock` ＋ QEMU `hostfwd` ＋ ゲスト側 `socat UNIX-LISTEN:$SSH_AUTH_SOCK,fork TCP:10.0.2.2:<p>`（`10.0.2.2`=SLIRP ゲートウェイ）。`vm shell` を ssh にするなら `ssh -A` でも可。露出は claude/ゲストの localhost 限定に絞り、必要に応じ `ssh-add -c`。信頼境界は「コンテナへ forward するのと同等」。

### 3.5 ネットワークと firewall
- user-mode ネット（SLIRP）の外向き通信は **qemu プロセス（claude コンテナ内）経由**で出るため、**claude コンテナの egress firewall（ブラックリスト iptables）が引き続き適用**される（VM だけが firewall を素通りすることはない）。
- ゲスト daemon/サービスは hostfwd で **claude コンテナの localhost にのみ**露出（ネットワークには晒さない）。

### 3.6 エージェント向け情報の提供（`VM_DEV.md`、CLAUDE.md は不可侵）
VM を扱うために agent（Claude/orchestrator/worker）が知るべき情報は、**専用ファイル `VM_DEV.md` に集約**する。**CLAUDE.md には一切追記しない**（各プロジェクトが独自に運用する CLAUDE.md を侵さないため。従来 entrypoint が環境情報を CLAUDE.md へ追記していたのとは方針を変える）。

- **生成（確定）**: `--vm` 起動時に基盤（entrypoint／VM 起動スクリプト）が **`/workspace/VM_DEV.md`** を生成する。ファイル冒頭に「claude-dev の VM モードが自動生成・編集不要」を明記した生成物として扱い、**`.gitignore` は基盤側で自動改変しない**（これ以上プロジェクトファイルに手を入れない方針。コミット除外は利用者判断）。
- **内容（VM を意識した制御に必要な全情報）**:
  - `DOCKER_HOST` の値（ゲスト daemon を指す）と、`docker`/`compose` はゲストに向く旨。
  - **bind mount の source は `/workspace` 配下のみ**（virtiofs 共有範囲。同一パスなので `-v /workspace/...:/...` が成立・ライブ反映）。
  - ポート: ゲストのサービスは claude 側 `127.0.0.1:<port>` で自動的に見える（port 同期の常駐が hostfwd を自動追加。即時反映は `vm portsync`）。外部公開は `claude-dev forward` を併用。
  - `vm` ヘルパー（`vm status`/`vm shell`/`vm restart`/`vm down`/`vm rebuild`/`vm portsync`/`vm logs`）。
  - ssh-agent: 既定 A（SSH/git は claude 側）／B オプトイン手順（§3.4）。
  - トラブルシュート（dockerd 未起動時の確認、virtiofs マウント確認、ログの場所）。
- **発見（CLAUDE.md 非侵襲の導線）**:
  1. 起動時に端末へバナー表示（「VM モード有効。制御情報は `VM_DEV.md`」）。
  2. **orchestrator は worker/ブレインストーミングプロンプト先頭に `VM_DEV.md` へのポインタを前置**（既存の `ORCHESTRATOR.md` 前置と同じ仕組み。CLAUDE.md には触れない）。
  3. `claude-dev` が対話 claude 起動時に `--append-system-prompt` で「VM モード: `VM_DEV.md` 参照」の 1 行を注入（任意・CLAUDE.md 非侵襲）。

### 3.7 ゲスト資源逼迫の警告（vm-healthd）
ゲスト RAM が不足すると（スワップがあっても）ページ回収でゲスト全体が stall し、「異常に遅い」状態になる（§3.3 のスワップはこれを緩和するが根絶はしない）。これを**利用者・エージェントに気づかせる**ため、claude コンテナ内で軽量な監視を常駐させる。

- **検知方式（コンテナ側のみ・ゲスト非依存）**: スラッシング時は ssh/docker API がゲストで応答しなくなる（＝警告を出したい瞬間ほどゲストへの問い合わせは機能しない）。そこで**ゲストには一切問い合わせず**、claude コンテナから常に読める **QEMU プロセスの CPU 使用率**だけを信号に使う。QEMU が `-smp` 由来の上限に対して高い比率を**継続的に**保つとき、資源逼迫（thrashing の疑い）と判定する。
- **誤検知の扱い**: この方式は「正当な重い処理」と「スラッシング」を CPU だけでは厳密に区別できない。一過性のビルド等を拾わないよう**低め閾値＋長め継続窓**で判定し、警告文言は「逼迫の可能性」とし `vm status` での確認を促す（断定しない）。閾値・窓は環境変数で調整可能（正本は [docs/impl/80_vm-mode.md](impl/80_vm-mode.md) §7.2）。
- **警告の出し先（2系統）**:
  1. **tmux バナー** — tmux のステータス行に常時表示（level 追従で set/clear）＋ WARN 遷移時にフラッシュ通知。人間が noVNC/端末で即認識できる。
  2. **orchestrator** — 実行モードのダッシュボード描画時に監視状態を読み、逼迫時は画面上部に警告バナーを出す。worker/ブレインストーミングが資源逼迫を認識できる。
- **CLAUDE.md 非侵襲**の方針は §3.6 と同じ（追記しない）。現況は `vm status` にも表示する。

## 4. ライフサイクル

- **有効化**: `claude-dev start --vm`（`--kvm` を含意）。VM モードを示すフラグ/環境変数を渡す。**ホストに `/dev/kvm` が無い場合は警告して起動を中止**（TCG エミュレーションでは Docker ビルドに実用にならないため）。
- **起動**: entrypoint もしくは専用スクリプトが、(1) キャッシュされたゲスト qcow2 が無ければ cloud image から provision、(2) virtiofsd 起動（`/workspace` 共有）、(3) QEMU 起動、(4) ゲスト dockerd の準備完了を待ち、(5) `DOCKER_HOST` を対話シェルへ設定し、ポート自動同期（`vm-portsync --loop`）と資源監視（`vm-healthd`）を常駐起動。
- **操作補助**: ゲストへ入るための補助（`vm shell`＝ssh/シリアル）と、状態確認・停止・ログ（`vm status`/`vm down`/`vm logs`）。
- **永続化**: ゲスト qcow2 とゲスト内の Docker データはボリュームで保持。`/workspace` は virtiofs 共有（ホスト実体）なのでコードは常にホスト側が正本。
- **リセット（白紙 provision やり直し）**: 2 経路。(a) `claude-dev start --vm --vm-fresh` … コンテナ作成前にゲスト用ボリューム（`claude-dev-vm-<name>`）を破棄し、新コンテナ初回ブートで再 provision（稼働中コンテナには使えず、`stop` 後に実行）。(b) `vm rebuild`（稼働中コンテナ内ヘルパー）… VM を停止し overlay/seed を削除して再 provision（コンテナは作り直さない）。**キャッシュの扱いが異なる**：(a) はボリュームごと破棄するため **cloud image DL キャッシュも消え再取得する**（完全リセット）。(b) は overlay/seed のみ削除し **cloud image キャッシュは残す**（再ダウンロード回避）。
- **既定との併存**: `--vm` 無しなら従来どおり DooD + proxy。VM モード時も、VM を使わない Docker 操作を proxy 経由で行う余地は残す（運用で使い分け）。

## 5. セキュリティ考慮
- **claude コンテナは privileged 化しない**。付与は `--kvm` のデバイス（`/dev/kvm`・`/dev/net/tun` 等）のみ（[03](03_security.md) の非対称性を踏襲）。
- VM 内で privileged コンテナ・bind mount・危険操作を行っても、**影響は VM 境界に封じ込め**られる。自律エージェントの Docker 作業を VM に隔離でき、暴走時は**スナップショット/破棄で復旧**できる。
- ゲスト daemon はコンテナ localhost にのみ露出。外向きは既存 firewall 配下。
- 残るリスク: デバイス渡し一般による隔離のわずかな緩み（既存 `--kvm` と同じ）。`/dev/kvm` 自体は ioctl 限定で脱獄に直結しない（[03](03_security.md)）。

## 6. 範囲外・未決事項
- **範囲外**: computer-use GUI VM（[05](05_customization.md) §C）との統合、Firecracker/microVM 方式（密度重視の別案。[会話履歴の検討参照]）、VM 主体への全面再設計（proxy 廃止）。
- **確定済み**:
  - `VM_DEV.md` は `/workspace/VM_DEV.md` に自動生成、`.gitignore` は非改変。
  - **provision は「初回起動時の遅延 provision＋ボリュームキャッシュ」方式**（ビルド時前倒しはしない。§3.3/§4 の通り）。
  - **アプリポートは自動フォワード**：常駐の `vm-portsync`（§3.3）がゲストの公開ポートを検出し、**同一番号で** hostfwd を自動追加する。`VM_PORTS` は起動時に固定で開くための明示指定として併用可。ホスト側ポート番号を別番号へ動的に自動割当することはしない（ゲストと同番号で mirror）。
  - **ゲスト既定値（RAM/CPU/ディスク）や具体パラメータの正本は実装仕様 [docs/impl/80_vm-mode.md](impl/80_vm-mode.md)**（例: RAM 8192M / SMP 2 / disk 20G / スワップ 2G。**環境変数で上書き可・config ファイルは設けない**。RAM は単位付き必須）。
- **未決**: ssh-agent 方式 B（ゲストへの agent 転送）の具体配線（socat/hostfwd ポート・自動化するか手動手順に留めるか）、virtiofs の小ファイル大量時の性能チューニング（cache mode 等）、orchestrator worktree（`.orchestrator/worktrees`）を VM 内 Docker とどう併用するか。

## 7. 関連ドキュメント
- [docs/03_security.md](03_security.md)：KVM デバイス受け渡しと特権の非対称性（本設計の前提）
- [docs/05_customization.md](05_customization.md) §C：既存の computer-use GUI VM（別用途）
- [docs/04_cli-reference.md](04_cli-reference.md)：`--kvm`・`forward`
- [docs/impl/80_vm-mode.md](impl/80_vm-mode.md)：本設計の実装仕様（正本）
