---
summary: VM モード（QEMU+KVM でゲスト VM を起動し virtiofs で /workspace を同一パス共有、ゲスト内 dockerd を DOCKER_HOST で使う）の実装仕様。Dockerfile への virtiofsd/cloud-image-utils 追加、Ubuntu cloud image の provision、起動スクリプト、claude-dev の --vm/vm、VM_DEV.md 生成の成果物仕様を定める。
keywords: [ VMモード, QEMU, virtiofs, cloud-init, DOCKER_HOST, hostfwd, VM_DEV ]
---

# 実装仕様: VM モード（QEMU + virtiofs）

> **この文書の役割**: [docs/08_vm-mode.md](../08_vm-mode.md) の設計を実装する成果物の仕様。CLI の正本は [10_cli.md](10_cli.md)、イメージビルドの正本は [40_devcontainer.md](40_devcontainer.md)、entrypoint は [31_entrypoint.md](31_entrypoint.md)、セキュリティは [../03_security.md](../03_security.md)。

## 要件（なぜ必要か）
DooD＋socket proxy 構成では proxy がホスト bind mount を全面拒否し、DooD のパス不一致もあって「bind mount を使う Docker 中心開発」ができない（08 §1）。VM モードは KVM のゲスト内でネイティブ Docker を動かし、virtiofs で `/workspace` を同一パス共有することで、**bind mount がライブ反映付きで成立**し、かつ claude コンテナを privileged 化せず隔離を保つ。設計・意図は 08 を参照。

## カバーするコード
```
.devcontainer/Dockerfile.claude   apt に virtiofsd・cloud-image-utils を追加（qemu 一式は既存）
claude-dev                        `start --vm`（--kvm 含意・VM 用ボリューム/ポート付与）、`vm` は原則コンテナ内ヘルパー
scripts/entrypoint-claude.sh      VM モード時に vm-up 起動→dockerd 準備待ち→(成功時のみ) DOCKER_HOST env スニペット出力＋VM_DEV.md 生成→バナー。CLAUDE.md は非追記（--vm 時は 31 の KVM 追記も抑止）
scripts/vm-up.sh (新規)           provision（初回）→ virtiofsd 起動 → QEMU 起動（常駐）→ ゲスト dockerd 準備を同期ポーリング → ポート自動同期(vm-portsync --loop)・資源監視(vm-healthd)を常駐起動
scripts/vm (新規)                 コンテナ内ヘルパー（status〔health 表示含む〕/shell/restart/down/rebuild/portsync/logs）
scripts/vm-portsync.sh (新規)     ゲスト公開ポートを 127.0.0.1 へ hostfwd 自動同期（一発/常駐）
scripts/vm-healthd.sh (新規)      QEMU CPU ヒューリスティックでゲスト資源逼迫を検知し tmux バナー/health ファイルへ警告（常駐。§7.2）
scripts/tmux.conf                 status-right に `@vm_health`（vm-healthd が set/clear する警告表示）を追加（正本 [30_scripts.md](30_scripts.md)）
orchestrator/dashboard.go         実行モードのダッシュボード描画時に health ファイルを読み警告バナー表示（正本 [60_orchestrator.md](60_orchestrator.md)）
scripts/VM_DEV.md.tmpl (新規)     VM_DEV.md 生成テンプレート（イメージ同梱）
（生成物）DOCKER_HOST env スニペット  entrypoint が dockerd 準備完了時のみ出力し system rc から source（後述 §5）
（生成物）/workspace/VM_DEV.md     エージェント向け VM 制御情報（--vm 時に生成）
```
`qemu-system-x86`/`qemu-utils`/`ovmf` は既存（[40](40_devcontainer.md)）。ゲスト qcow2・cloud image キャッシュは名前付きボリューム（後述）に置く。

## コンポーネント仕様

### 1. イメージ（Dockerfile.claude）
- apt に **`virtiofsd`**（vhost-user virtiofs デーモン）と **`cloud-image-utils`**（`cloud-localds` で cloud-init seed ISO を作る）を追加。`qemu-system-x86`/`qemu-utils` は既存。
- `scripts/vm-up.sh`・`scripts/vm`・`scripts/vm-portsync.sh`・`scripts/VM_DEV.md.tmpl` を `/usr/local/bin`（実行権付与）・`/usr/local/share/claude-dev/` に COPY。

### 2. CLI（claude-dev）
- **`start --vm`**: `USE_KVM=1` を含意（既存の `--device=/dev/kvm` 等付与ロジックを流用）。加えて:
  - 環境変数 `CLAUDE_DEV_VM=1` をコンテナへ渡す（entrypoint が判定）。
  - ゲスト qcow2・cloud image キャッシュ用の**名前付きボリューム `claude-dev-vm-${NAME}`**（プロジェクト名で一意）を `${CHOME}/.claude-dev-vm` にマウント（永続化・コンテナ作り直しで消えない）。
  - VM 用の hostfwd を設けるための設定（アプリポート）を環境変数 `VM_PORTS`（例 `8000,8080`）で受け、entrypoint/vm-up へ渡す（**起動時の既定 hostfwd は Docker API(2375)＋SSH(2222)**。アプリの公開ポートは §7.1 の port 同期が起動後に自動追加するため、`VM_PORTS` は「起動時から固定で開きたいポート」の明示指定用）。
  - `--vm` は `--kvm` を含意するが、`/dev/kvm` がホストに無い場合は警告し**起動を中止**（TCG では実用にならないため）。
  - **`--vm-fresh`**（`--vm` を含意）: コンテナ作成前にゲスト用ボリューム `claude-dev-vm-${NAME}` を `docker volume rm -f` で破棄し、新コンテナ初回ブートでゲストを再 provision する。ボリュームごと破棄するため **cloud image DL キャッシュも消え、次回ブートで再取得する（完全リセット）**。cloud image を残したまま作り直したい場合は稼働中コンテナ内の `vm rebuild`（overlay/seed のみ削除、§7）を使う。**稼働中コンテナには適用できない**（`start` は attach するだけ）ため、その場合は「`stop` してから `--vm-fresh`、または稼働中は `vm rebuild`」を案内する。
- **`vm` ヘルパー**は原則**コンテナ内**（`/usr/local/bin/vm`）。人間・エージェントの双方が利用可（08 §3.6）。ホスト側 `claude-dev` からの操作が必要なら `docker exec … vm …` で委譲（任意）。
- **対話 claude 起動時の VM_DEV.md 注入（発見導線3）**: VM モード時（`CLAUDE_DEV_VM=1`）に `claude-dev code` が対話 `claude` を起動する際、`--append-system-prompt` で「VM モード有効。制御情報は `/workspace/VM_DEV.md` を参照」の 1 行のみ注入する（CLAUDE.md は変更しない。08 §3.6）。
- **`orchestrate` の VM 対応**: `claude-dev orchestrate` は `claude-orchestrator`（非対話）を起動するため rc/vm.env を自動では読まない。起動コマンドの前に **`[ -f /etc/claude-dev/vm.env ] && . /etc/claude-dev/vm.env`** を挟み、ゲスト `DOCKER_HOST` を orchestrator（および `claudeChildEnv` 経由で worker）へ引き継ぐ。worker への VM モード周知は `--append-system-prompt` ではなく**発見導線2（orchestrator のプロンプト前置）**で行う（[60_orchestrator.md](60_orchestrator.md) §instruction 注入の `VMModePreamble`）。

### 3. ゲストイメージ provision（Ubuntu cloud image）
`scripts/vm-up.sh` が初回のみ実行（結果はボリュームにキャッシュ）:
1. Ubuntu cloud image（qcow2, 例 noble amd64）をキャッシュへダウンロード（未取得時）。
2. 書き込み用ゲストディスクを作成（cloud image を backing にした qcow2 overlay ＋ `qemu-img resize` で既定サイズへ）。
3. **cloud-init user-data** を `cloud-localds` で seed ISO 化。user-data は次を行う:
   - Docker を導入（Ubuntu リポジトリの `docker.io`）。
   - dockerd を systemd drop-in（`docker.service.d/override.conf`）で **`ExecStart=… -H fd:// -H tcp://0.0.0.0:2375`** に上書きし、`daemon-reload`＋**`systemctl restart docker`**（`enable --now` では既起動の dockerd が再起動されず tcp が有効化されない点に注意）。`-H fd://` で `docker.socket` 経由の unix ソケットを維持しつつ tcp を追加。**tcp は 0.0.0.0（ゲスト内）で待受**する必要がある（QEMU user-mode hostfwd はゲストの SLIRP IP 宛に転送するため、ゲスト `127.0.0.1` 待受では届かない）。露出は claude コンテナの `127.0.0.1` hostfwd 経由のみ。
   - **virtiofs を `/workspace` に自動マウント**（`/etc/fstab` に `workspace /workspace virtiofs defaults,nofail 0 0`。tag=`workspace`）。
   - **スワップを確保**（既定 `VM_SWAP=2G` のスワップファイル `/swapfile`）。`fallocate -l ${VM_SWAP} /swapfile`（失敗時は `dd` フォールバック）→ `chmod 600`→`mkswap`→`swapon`→`/etc/fstab` に `\/swapfile none swap sw 0 0` を追記（冪等: 既存行があれば追記しない）。Ubuntu cloud image は既定でスワップを持たないため、RAM 超過時のページ回収スラッシングで**ゲスト全体が stall する**のを防ぐ目的（08 §3.3）。`VM_SWAP=0`（または空）でスワップ作成を無効化できる。
   - `vm shell` 用に **SSH 公開鍵を注入**（起動時に生成した鍵。ssh は hostfwd 2222 経由が主経路）。シリアルコンソールは補助（`vm logs`／コンソール用）。
4. 初回ブートで cloud-init が上記を適用（provision 完了）。以降は provision 済みディスクを再利用。

### 4. VM 起動（scripts/vm-up.sh）
ログ出力先は `${CHOME}/.claude-dev-vm/logs/`（`vm-up.log`/`qemu-serial.log`/`cloud-init` は初回の serial に出る）。`vm logs`（§7）はここを参照する。**初回判定**は書き込み用 overlay qcow2（`${CHOME}/.claude-dev-vm/guest-overlay.qcow2`）の有無で行い、無ければ provision（§3）＋seed.iso 添付で起動、あれば通常起動。
**`VM_FRESH=1`（環境変数）**が渡された場合は、`dockerd_ready` チェックより前に、走行中 VM を停止（pidfile の QEMU を kill・virtiofsd を停止）し overlay/seed を削除してから続行する（＝再 provision を強制。cloud image DL キャッシュは残す）。`vm rebuild`（§7）がこの経路を使う。
1. **virtiofsd 起動**（バックグラウンド）: `${VIRTIOFSD} --socket-path=/run/vm/vfs.sock --shared-dir=/workspace --sandbox=none`（共有タグ `workspace`）。※Ubuntu の `virtiofsd` は **PATH に無く `/usr/libexec/virtiofsd`** に入るため、スクリプトは `command -v virtiofsd || /usr/libexec/virtiofsd` で絶対パス解決する。

   > **既知の制約（uid）**: virtiofsd は uid 1000（`$USERNAME`）で動くため、ゲスト内コンテナが bind mount 先を別 uid へ `chown` する処理（mysql/grafana 等の DB・ミドルウェアがデータディレクトリを自ユーザへ chown、docker が bind mount 元を作成して chown 等）は `operation not permitted` で失敗する。virtiofsd を root 化すれば chown は通るが、今度はコンテナが作るデータが container uid 所有となり uid 1000 から読取/削除できず（`make` 等の後片付け・build context 読取が失敗）、どちらも一長一短。Docker Desktop は共有層で「全ファイルをホストユーザ所有＋chown は no-op 成功」を実現しているが素の virtiofsd では再現できない。**bind mount でコンテナ管理データ（DB 等）を置くスタックは VM モードでは完全動作しない**。名前付きボリューム化（データをゲスト VM 内に置く）で回避できる。
2. **QEMU 起動**（KVM 加速・共有メモリ必須・**常駐**）:
   ```
   qemu-system-x86_64 -enable-kvm -cpu host -m ${VM_MEM} -smp ${VM_SMP} \
     -drive file=${GUEST_OVERLAY},if=virtio \
     -object memory-backend-memfd,id=mem,size=${VM_MEM},share=on -numa node,memdev=mem \
     -chardev socket,id=vfs,path=/run/vm/vfs.sock \
     -device vhost-user-fs-pci,chardev=vfs,tag=workspace \
     -netdev user,id=n0,hostfwd=tcp:127.0.0.1:2375-:2375,hostfwd=tcp:127.0.0.1:2222-:22[,<VM_PORTS ごとの hostfwd>] \
     -device virtio-net-pci,netdev=n0 \
     [-drive file=${SEED_ISO},if=virtio  ← 初回のみ] \
     -display none -serial file:${CHOME}/.claude-dev-vm/logs/qemu-serial.log \
     -qmp unix:/run/vm/qmp.sock,server,nowait -pidfile /run/vm/qemu.pid -daemonize
   ```
   - **メモリ単位の一致（重要）**: `VM_MEM` は**必ず単位付き**（例 `8192M`）と規定し、`-m ${VM_MEM}` と `memory-backend-memfd,size=${VM_MEM}` の**双方で同一表記**を使う（無単位だと `-m`=MiB／`size`=バイトで解釈が食い違い `-numa` の RAM 不一致で起動失敗する）。
   - **virtiofs は共有メモリが必須**のため `memory-backend-memfd,share=on` ＋ `-numa node,memdev=mem` を必ず付ける。
   - **常駐化**: `-daemonize`（＋シリアルをログへ、QMP を `/run/vm/qmp.sock` へ）で QEMU を常駐させ、`vm-up.sh` は返る。`vm down`/`vm restart` は QMP／プロセスシグナルで制御。`vm shell` の主経路は ssh(2222)、シリアルログは補助。
   - `hostfwd` で Docker API（2375）・SSH（2222）・アプリポート（`VM_PORTS`）を claude コンテナの `127.0.0.1` に露出。
3. **dockerd 準備待ち（同期）**: `vm-up.sh` が `docker -H tcp://127.0.0.1:2375 info` を一定回数**同期ポーリング**し、準備完了で成功終了／タイムアウトで非ゼロ終了。entrypoint（§5）は vm-up.sh の**終了コードを待つだけ**（待受主体は vm-up.sh に一本化）。

既定値（確定・環境変数で上書き可）: `VM_MEM=8192M`・`VM_SMP=2`・ゲストディスク `20G`・`VM_SWAP=2G`（§3 のスワップファイル。`0`/空で無効）。CLI からの上書きは環境変数で渡す（`config` ファイルは設けない）。`${CHOME}` はコンテナユーザーのホーム（[10_cli.md](10_cli.md)）。

### 5. entrypoint 連携（scripts/entrypoint-claude.sh）
`CLAUDE_DEV_VM=1` のとき、既存の VNC/Chrome 起動と同様に:
1. `vm-up.sh` を起動し、その**終了コードで dockerd 準備完了/失敗を判定**（§4.3。待受主体は vm-up.sh に一本化）。
2. **成功時のみ**:
   - `DOCKER_HOST=tcp://127.0.0.1:2375` を **env スニペット `/etc/claude-dev/vm.env` へ出力**し、system rc（`/etc/zsh/zshrc`・`/etc/bash.bashrc`）から `[ -f /etc/claude-dev/vm.env ] && . /etc/claude-dev/vm.env` で読ませる（対話/非対話シェルとも DOCKER_HOST がゲストを指す）。
   - `VM_DEV.md.tmpl` から **`/workspace/VM_DEV.md` を生成**（DOCKER_HOST 値・ポート・`vm` コマンド等を差し込む）。
   - **バナー**「VM モード有効。制御情報は VM_DEV.md」。
3. **失敗時**: バナーで失敗を通知し、**DOCKER_HOST は設定しない**（既定の DooD+proxy 経路を維持＝docker が全面不通にならない）。VM 無しで継続。
- **CLAUDE.md は一切追記しない**（08 §3.6）。さらに **`--vm` 時は [31_entrypoint.md](31_entrypoint.md) の「/dev/kvm 検出時に CLAUDE.md へ KVM セクションをマーカー追記」挙動を抑止**し、その KVM/VM 情報も `VM_DEV.md` 側へ集約する（31 側を本仕様に合わせて更新。「関連して更新する既存文書」節を参照）。

### 6. VM_DEV.md（生成物・エージェント向け）
`--vm` 時に `/workspace/VM_DEV.md` を生成。冒頭に「claude-dev VM モードが自動生成・編集不要・必要なら各自 gitignore」を明記。内容（08 §3.6）:
- `DOCKER_HOST` の値とゲスト daemon を指す旨、`docker`/`compose` はゲスト対象。
- **bind mount の source は `/workspace` 配下のみ**（virtiofs 共有範囲・同一パスで成立/ライブ反映）。
- ポート: ゲストのサービスが公開したポートは **自動で** claude 側 `127.0.0.1:<port>` に現れる（port 同期の常駐＝§7.1。即時反映は `vm portsync`）。外部公開は `claude-dev forward` 併用。
- `vm` ヘルパー（`status`/`shell`/`restart`/`down`/`rebuild`/`portsync`/`logs`）。
- ssh-agent: 既定 A（SSH/git は claude 側）／B オプトイン手順（08 §3.4）。
- トラブルシュート（dockerd 未準備時の確認、`mount | grep virtiofs`、ログ位置）。

**発見導線の実装（3系統・いずれも CLAUDE.md 非侵襲。08 §3.6）**:
1. **起動バナー** — entrypoint（§5 step4）。
2. **orchestrator のプロンプト前置** — worker/壁打ちプロンプト先頭に `VM_DEV.md` へのポインタを前置する。実装は **[60_orchestrator.md](60_orchestrator.md) 側**（既存の `ORCHESTRATOR.md` 前置と同じ仕組みを流用。VM モード時のみ前置）。本書は連携先として指す。
3. **`--append-system-prompt` 注入** — `claude-dev`（§2）が対話 claude 起動時に 1 行注入。

### 7. vm ヘルパー（scripts/vm）
コンテナ内 `/usr/local/bin/vm`。サブコマンド:
- `status`: qemu プロセス生存・`docker -H tcp://127.0.0.1:2375 info` 到達性・virtiofsd 生存に加え、**資源監視の現況（health ファイル §7.2: STATE / QEMU CPU% / 上限 / 最終更新経過）** を表示。
- `shell`: ゲストへ入る（主経路 `ssh -p 2222 …`＝注入した鍵を使用。補助としてシリアルログ/コンソール）。
- `restart`/`down`: QEMU/virtiofsd の再起動・停止。
- `rebuild`: `VM_FRESH=1 vm-up.sh` を実行し、VM 停止＋overlay/seed 削除＋再 provision（稼働中コンテナのゲスト白紙やり直し。**cloud image DL キャッシュは残す**）。CLI の `--vm-fresh`（§2）とはキャッシュ保全範囲が異なる（`--vm-fresh` はボリュームごと破棄＝キャッシュも消える）。
- `portsync`: `vm-portsync.sh` を一発実行し、現在ゲストが公開しているポートを 127.0.0.1 へ即時 hostfwd する。
- `logs`: vm-up / QEMU / cloud-init のログ表示。

### 7.1 ポート自動フォワード（scripts/vm-portsync.sh）
VM モードでは compose/docker が公開するポートはゲスト VM 側に出るため、claude コンテナ内のテスト等が叩く `127.0.0.1:PORT` には既定で繋がらない。これを解消するため、ゲスト dockerd 準備完了後に `vm-up.sh` が **`vm-portsync.sh --loop` を常駐起動**する（`start_portsync`。多重起動は `pgrep` で防止）。
- ループは一定間隔（既定 5 秒、`VM_PORTSYNC_INTERVAL`）で `docker -H tcp://127.0.0.1:2375 ps` の公開ポートを検出し、未フォワードのものを **QMP の `human-monitor-command` 経由で HMP コマンド `hostfwd_add n0 tcp:127.0.0.1:PORT-:PORT`** を実行して追加する（`hostfwd_add` は HMP コマンドのため QMP から直接ではなくラップして呼ぶ）。
- 追加済みは `/run/vm/portsync.forwarded`（`<qemu_pid>:<port>`）で記録し重複追加を避ける。VM 再起動で pid が変わると自然にリセットされ、新しい QEMU に対して張り直す。
- これにより `VM_PORTS` の手動指定なしに、公開したポートが自動的に claude コンテナの localhost へ現れる（`VM_PORTS` は起動時 hostfwd の明示指定として引き続き利用可能）。

### 7.2 ゲスト資源逼迫の監視・警告（scripts/vm-healthd.sh）
ゲスト RAM 逼迫でページ回収スラッシングが起きるとゲスト全体が stall し「異常に遅い」状態になる（08 §3.7）。これを気づかせるため、ゲスト dockerd 準備完了後に `vm-up.sh` が **`vm-healthd.sh` を常駐起動**する（`start_healthd`。多重起動は `pgrep` で防止）。**検知はコンテナ側の QEMU CPU のみに基づき、ゲストへは一切問い合わせない**（スラッシング時は ssh/docker が応答しないため。08 §3.7）。

- **サンプリング**: `PIDFILE`（`/run/vm/qemu.pid`）の QEMU の `utime+stime`（`/proc/<pid>/stat` 第14+15フィールド）を `VM_HEALTH_INTERVAL`（既定 15 秒）の間隔で2点サンプルし、`getconf CLK_TCK` を用いて **1コア基準の CPU%** を算出。上限は QEMU の `/proc/<pid>/cmdline` から解決した `-smp N`（＝`N*100%`）。比率 = CPU% ÷ 上限。
- **判定（低め閾値＋長め継続窓）**: 比率が `VM_HEALTH_CPU_PCT`（既定 60〔%〕）以上のサンプルを「hot」とし、**連続 `VM_HEALTH_SUSTAIN`（既定 12 回 ≒ 3 分）** で **WARN**。以後 hot が途切れたら OK へ戻す（level 追従）。今回の実機スラッシングは smp=2 で ~150%（コア平均 75%）だったため 60% 継続で捕捉でき、かつ一過性ビルドを 3 分窓で除外する狙い。
- **health ファイル**: 各周回で `${CHOME}/.claude-dev-vm/health` を上書き（`STATE=OK|WARN`・`CPU=<%>`・`CEIL=<%>`・`TS=<epoch>`・`MSG=…`）。`vm status`（§7）と orchestrator（§下）が読む。**鮮度**は `TS` で判定（読み手は「TS が古い＝監視停止」を非表示扱いにする）。
- **tmux バナー**: WARN の間 `tmux set -g @vm_health "⚠ VM資源逼迫…"`、OK 復帰で `tmux set -gu @vm_health`（クリア）。`tmux.conf` の status-right が `@vm_health` を表示（[30_scripts.md](30_scripts.md)）。OK→WARN 遷移時のみ `tmux display-message` でフラッシュ通知（`VM_HEALTH_COOLDOWN` 既定 600 秒で再フラッシュを抑制）。tmux サーバ未起動時（`tmux has-session` 失敗）はスキップ。
- **調整**: `VM_HEALTH_INTERVAL`/`VM_HEALTH_CPU_PCT`/`VM_HEALTH_SUSTAIN`/`VM_HEALTH_COOLDOWN` は環境変数で上書き可（CLI からの明示受け渡しは設けず、既定値で運用。必要なら稼働中コンテナ内で環境変数を与えて再起動）。ログは `logs/vm-healthd.log`。
- **orchestrator 連携**: 実行モードのダッシュボードが描画のたびに health ファイルを読み、`STATE=WARN` かつ `TS` が新しければ画面上部へ警告バナーを出す（controller ループは非改変・`dashboard.go` に限定。正本 [60_orchestrator.md](60_orchestrator.md)）。

### 8. ネットワーク・セキュリティ
- user-mode ネット（SLIRP）のため外向き通信は qemu プロセス（claude コンテナ内）経由＝**既存 egress firewall が適用**（08 §3.5）。
- Docker API（2375, 非TLS）: ゲスト内 dockerd は `0.0.0.0:2375` で待受するが、到達経路は **QEMU user-mode の hostfwd（claude コンテナの `127.0.0.1:2375` → ゲスト）だけ**。ゲストは SLIRP の内側で他ネットワークに接続されないため、実質 **claude コンテナ内からのみ到達**（ネットワーク非公開）。
- claude コンテナは privileged 化しない（付与は `--kvm` のデバイスのみ、[../03_security.md](../03_security.md)）。VM 内の bind/privileged は VM 境界に隔離。
- **proxy 経路との併存**: VM モードでも既定の DooD（socket proxy 経由のホスト daemon）経路は残る。VM を使わない Docker 操作をしたい場合は、当該コマンドで `DOCKER_HOST` を一時上書き（例 `DOCKER_HOST=tcp://claude-dev-docker-proxy:2375 docker …`）して proxy 経路に戻せる（08 §2/§4 の「併存可」の実装上の担保）。

## 関連して更新する既存文書
- [10_cli.md](10_cli.md): `start --vm`・`vm` ヘルパー。
- [40_devcontainer.md](40_devcontainer.md): apt に `virtiofsd`/`cloud-image-utils`、スクリプト COPY。
- [31_entrypoint.md](31_entrypoint.md): VM モード時の vm-up 起動・DOCKER_HOST env スニペット・VM_DEV.md 生成・バナー。**`--vm` 時は既存の「/dev/kvm 検出→CLAUDE.md へ KVM セクション追記」を抑止**（VM_DEV.md へ集約）。
- [60_orchestrator.md](60_orchestrator.md): VM モード時に worker/壁打ちプロンプト先頭へ `VM_DEV.md` ポインタを前置（発見導線2）。実行モードのダッシュボードが health ファイルを読み資源逼迫バナーを表示（§7.2）。
- [30_scripts.md](30_scripts.md): `scripts/vm-healthd.sh`（資源監視常駐）と `tmux.conf` の status-right `@vm_health`（vm-healthd が set/clear）。
- [40_devcontainer.md](40_devcontainer.md): `scripts/vm-healthd.sh` を `/usr/local/bin` へ COPY・実行権付与。
- [../03_security.md](../03_security.md): VM 境界による隔離・Docker API の localhost 限定露出・privileged 非付与。
- [../04_cli-reference.md](../04_cli-reference.md): 利用者向け `--vm`/`vm`。
- [../02_architecture.md](../02_architecture.md): VM モードの層構造（コンテナ→VM→Docker）。

## テスト方針（動作確認）
実 `/dev/kvm` があるホストで実施（08 の前提）:
- `claude-dev start --vm` 後、`docker info` がゲスト daemon を指すこと（`DOCKER_HOST`）。
- **bind mount ライブ反映**: `docker run --rm -v /workspace/t.txt:/t.txt busybox cat /t.txt` が claude 側編集を反映。
- `docker compose`（bind 使用）がゲストで動くこと。
- `/workspace/VM_DEV.md` が生成され CLAUDE.md が未変更であること。
- `vm status`/`vm shell` が機能すること。
- **ポート自動フォワード（§7.1）**: ゲストで公開ポートを持つコンテナを起動すると、数秒以内に claude 側 `127.0.0.1:<port>` へ到達できること（`vm portsync` の即時実行でも同様）。
- **リセット**: `vm rebuild` が overlay/seed のみ削除し cloud image を再取得せず再 provision すること／`start --vm-fresh` がボリュームごと破棄して完全再 provision すること。
- ホストに `/dev/kvm` が無い場合は `--vm` が警告して中止すること。

## 実装状況
**実装済み・実機 E2E 検証済み**（KVM ホストで確認。[docs/reviews/2026-07-03_vm-mode-e2e.md]）。
- 実装: `Dockerfile.claude`（apt に `virtiofsd`/`cloud-image-utils` 追加・scripts COPY）、`scripts/vm-up.sh`（provision〔Docker・virtiofs 自動マウント・スワップ `VM_SWAP` 確保〕＋virtiofsd＋QEMU 常駐〔既定 `VM_MEM=8192M`〕＋dockerd 同期待ち＋ポート自動同期・資源監視の常駐起動）、`scripts/vm`（status〔health 表示含む〕/shell/restart/down/rebuild/portsync/logs）、`scripts/vm-portsync.sh`（ゲスト公開ポートの hostfwd 自動同期）、`scripts/vm-healthd.sh`（QEMU CPU ヒューリスティックによる資源逼迫検知→tmux バナー/health ファイル警告。§7.2）、`scripts/VM_DEV.md.tmpl`、`scripts/entrypoint-claude.sh`（VM 起動・DOCKER_HOST env スニペット・VM_DEV.md 生成・バナー・`--vm` 時の CLAUDE.md KVM 追記抑止）、`claude-dev`（`start --vm`＝`--kvm` 含意・`/dev/kvm` 無しで中止・`CLAUDE_DEV_VM`/ボリューム/`VM_PORTS` 等付与・`--vm-fresh` でゲスト用ボリューム破棄→再 provision・起動待ち延長/所要時間表示、`code` で `--append-system-prompt` 注入）。
- 静的検証: 全スクリプト `bash -n` 緑。`virtiofsd` は `/usr/libexec/virtiofsd`（PATH 外。スクリプトで絶対パス解決）を確認。
- **実機 E2E（KVM ホスト）検証済み**: cloud-init provision→QEMU ブート→virtiofs で `/workspace` 同一パス共有→ゲスト dockerd 到達（`docker -H tcp://127.0.0.1:2375`）→**bind mount ライブ反映**（ホスト編集がゲスト docker コンテナに即反映）を確認。`vm status`/`vm shell` も動作。詳細は [docs/reviews/2026-07-03_vm-mode-e2e.md](../reviews/2026-07-03_vm-mode-e2e.md)。
- orchestrator 連携（本改訂で実装）: `claude-dev orchestrate` が `/etc/claude-dev/vm.env` を source してゲスト `DOCKER_HOST` を引き継ぎ（worker は `claudeChildEnv` で継承）、発見導線2（`VMModePreamble` によるプロンプト前置）を実装（[60_orchestrator.md](60_orchestrator.md)）。
