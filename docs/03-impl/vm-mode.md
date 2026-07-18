---
id: vm-mode
layer: impl
title: vm-mode 実装説明書
version: 1.0.0
updated: 2026-07-18
verified:
  at: 2026-07-18
  version: 1.0.0
  against:
    - doc: docs/02-design/system.md
      version: 1.0
summary: >
  オプトインのゲスト VM モード。claude コンテナ内で QEMU/KVM のゲスト VM を起動し、
  virtiofs で /workspace を同一パス共有、ゲスト内ネイティブ dockerd を DOCKER_HOST 経由で
  使う。vm-up.sh（起動・provision）／vm（ヘルパー）／vm-portsync.sh（ポート同期）／
  vm-healthd.sh（資源監視）／VM_DEV.md.tmpl で構成する。
keywords: [VMモード, QEMU, KVM, virtiofs, cloud-init, DOCKER_HOST, hostfwd, VM_DEV]
depends_on: [cli]
source:
  - docs/02-design/system.md
---

# 実装説明書:vm-mode

## 概要

DooD＋docker-proxy 構成では proxy がホスト bind mount を原則拒否し（`/workspace` 配下のみ実ホストパスへ書換）、privileged や広範な bind を伴う「Docker 中心開発」が成立しにくい。vm-mode（要件 core/8）はこの制約を、claude コンテナ内で **QEMU/KVM のゲスト VM** を起動し、その中で**ネイティブ Docker（dockerd）**を動かすことで解決する。`/workspace` は **virtiofs でゲストへ同一パス共有**され bind mount がライブ反映付きで成立し、privileged 等も VM 境界内で使える。claude コンテナ自身は privileged 化せず隔離を保つ。ゲスト dockerd へは `DOCKER_HOST=tcp://127.0.0.1:2375`（QEMU user-mode hostfwd 経由）で接続する。上流: [全体設計](../02-design/system.md)（`vm-mode` 行・core/8）。

本モジュールは `scripts/` 配下のシェルスクリプト群と VM_DEV.md テンプレートのみを担う。`--vm` フラグ処理と `CLAUDE_DEV_VM=1` の受け渡し、entrypoint による vm-up 起動・`/etc/claude-dev/vm.env` 生成・VM_DEV.md 生成は依存モジュール（cli / entrypoint）側の実装だが、本モジュールが提供する成果物（vm-up.sh・VM_DEV.md.tmpl）を用いる連携点として記述する。

## ファイル構成

| パス | 役割 |
|---|---|
| scripts/vm-up.sh | ゲスト VM の起動本体。初回 provision（Ubuntu cloud image + cloud-init）→ virtiofsd 起動 → QEMU 常駐起動 → ゲスト dockerd 準備を同期ポーリング → ポート同期・資源監視の常駐起動 |
| scripts/vm | コンテナ内ヘルパー（`/usr/local/bin/vm`）。`status`/`shell`/`restart`/`down`/`rebuild`/`portsync`/`logs` |
| scripts/vm-portsync.sh | ゲスト公開ポートを QMP の `hostfwd_add` で `127.0.0.1` へ自動転送（一発/`--loop` 常駐） |
| scripts/vm-healthd.sh | QEMU の CPU 使用率から資源逼迫を検知し tmux バナー・health ファイルへ警告（一発/`--loop` 常駐） |
| scripts/VM_DEV.md.tmpl | エージェント向け VM 制御情報テンプレート。entrypoint が `@DOCKER_HOST@`/`@VM_PORTS@` を差し替え `/workspace/VM_DEV.md` を生成 |

いずれもイメージへ COPY され `/usr/local/bin` に実行権付きで置かれる（配置は devcontainer モジュール）。ゲスト qcow2・cloud image キャッシュ・ログ・鍵・health/env は `${HOME}/.claude-dev-vm`（＝名前付きボリューム）に永続化される。

## モジュール別実装詳細

### vm-up.sh(scripts/vm-up.sh)

- **責務:** ゲスト VM を初回 provision して起動し、ゲスト dockerd が到達可能になるまで同期待機する。冪等（既に dockerd 到達可能なら何もせず終了）。entrypoint がその終了コードで成否を判定する。
- **公開インターフェース:** 引数なしで実行。挙動は環境変数で制御（`VM_FRESH`/`VM_MEM`/`VM_SMP`/`VM_DISK`/`VM_SWAP`/`VM_PORTS`/`CLOUD_IMG_URL`/`VM_WAIT_SECS`）。終了コード: 0=dockerd 準備完了、非0=前提不足またはタイムアウト。
- **処理の要点:**
  - パス定義: `VM_HOME=${HOME}/.claude-dev-vm`、`RUN_DIR=/run/vm`、`CLOUD_IMG=ubuntu-cloud.img`、`GUEST_OVERLAY=guest-overlay.qcow2`、`SEED_ISO=seed.iso`、SSH 鍵 `id_vm`、virtiofs ソケット `vfs.sock`、QMP `qmp.sock`、`PIDFILE=qemu.pid`。
  - `virtiofsd` は PATH に無いため `command -v virtiofsd || /usr/libexec/virtiofsd` で絶対パス解決する。
  - **VM_FRESH=1**: 走行中 QEMU を kill・virtiofsd を停止し overlay/seed を削除（＝再 provision 強制。cloud image DL キャッシュは残す）。それ以外で `dockerd_ready`（`docker -H tcp://127.0.0.1:2375 info`）が真なら冪等に `start_portsync`/`start_healthd` して終了。
  - **前提チェック:** `/dev/kvm`（キャラクタデバイス）・`qemu-system-x86_64`・`virtiofsd` の存在。欠ければ FATAL で非0終了（TCG フォールバックはしない）。
  - **初回 provision（overlay 不在時, `FIRST_BOOT=1`）:** cloud image を未取得なら `curl` で DL（`.part`→rename）。`qemu-img create -f qcow2 -F qcow2 -b <cloud-img>` で backing overlay を作成（サイズ `VM_DISK`）。SSH 鍵を `ssh-keygen -t ed25519` で生成。cloud-init user-data を生成し `cloud-localds` で seed ISO 化。
  - **cloud-init user-data の内容:** ユーザ `dev`（NOPASSWD sudo・`docker` グループ・生成公開鍵）。`docker.io` を導入。`/workspace` を `/etc/fstab` に `workspace /workspace virtiofs defaults,nofail 0 0`（tag=`workspace`）で追記し `mount -a`。dockerd を systemd drop-in（`docker.service.d/override.conf`）で `ExecStart=… -H fd:// -H tcp://0.0.0.0:2375` に上書きし `daemon-reload`→`enable docker`→**`restart docker`**（`enable --now` では既起動 dockerd が再起動されず tcp が有効化されないため restart）。tcp は **0.0.0.0** 待受（QEMU user-mode hostfwd はゲスト SLIRP IP 宛に転送するため 127.0.0.1 では届かない）。
  - **スワップ確保（`VM_SWAP≠0`/非空時）:** provision 生成時に `numfmt --from=iec` でサイズを MB へ確定して user-data に焼き込む（既定 2048MB フォールバック）。runcmd で `fallocate`（失敗時 `dd`）→`chmod 600`→`mkswap`→`swapon`→fstab 追記（冪等）。RAM 超過時のページ回収スラッシングでゲストが stall するのを防ぐ目的。
  - **virtiofsd 起動:** 既存が無ければ `${VIRTIOFSD} --socket-path=<vfs.sock> --shared-dir=/workspace --sandbox=none` をバックグラウンド起動し、ソケット生成を最大 5 秒ポーリング。
  - **hostfwd 組み立て:** 既定 `hostfwd=tcp:127.0.0.1:2375-:2375,hostfwd=tcp:127.0.0.1:2222-:22`。`VM_PORTS`（カンマ区切り）があれば各ポートの hostfwd を追加。
  - **QEMU 起動:** `-enable-kvm -cpu host -m ${VM_MEM} -smp ${VM_SMP}`、overlay を `if=virtio`、共有メモリ `memory-backend-memfd,size=${VM_MEM},share=on` ＋ `-numa node,memdev=mem`（virtiofs は共有メモリ必須）、vhost-user-fs（tag=`workspace`）、`-netdev user` に hostfwd、初回のみ seed ISO を `if=virtio,media=cdrom` で添付、`-display none`、シリアルをログへ、`-qmp unix:<qmp.sock>`、`-pidfile`＋`-daemonize` で常駐化。`VM_MEM` は `-m` と `memory-backend-memfd,size` の双方で**同一の単位付き表記**を使う（無単位だと解釈が食い違い `-numa` の RAM 不一致で起動失敗）。
  - **dockerd 準備待ち:** `dockerd_ready` を最大 `VM_WAIT_SECS`（既定 180）回、1 秒間隔で同期ポーリング。準備完了で `start_portsync`/`start_healthd` して 0 終了、タイムアウトで非0終了。
  - **常駐起動ヘルパー:** `start_portsync`/`start_healthd` はそれぞれ `vm-portsync.sh --loop`/`vm-healthd.sh --loop` を `setsid …&` で起動。多重起動は `pgrep -f` で防止。
- **実装上の判断:** 待受主体を vm-up.sh に一本化（entrypoint は終了コードのみ待つ）。seed ISO は `media=cdrom` 指定で添付。

### vm(scripts/vm)

- **責務:** コンテナ内から VM を操作するヘルパー。設計上の `vm` サブコマンド一覧を実装する。
- **公開インターフェース:** `vm {status|shell|restart|down|rebuild|portsync|logs}`（引数省略時 `status`）。
- **処理の要点:**
  - `status`: QEMU プロセス生存（pidfile + `kill -0`）、`virtiofsd` 生存（pgrep）、ゲスト dockerd 到達性（`docker -H tcp://127.0.0.1:2375 info`）を表示。加えて health ファイルを読み `STATE`/`CPU`/`CEIL` と最終更新経過秒（`TS` から算出）を表示。health 不在時は `vm-healthd.sh --loop` の生存で「monitor starting/not running」を出し分ける。
  - `shell`: `ssh -p 2222 -i <id_vm>`（StrictHostKeyChecking=no 等）で `dev@127.0.0.1` に入る。`vm shell -- <cmd>` で単発実行。
  - `restart`: `vm down` 後 `vm-up.sh` を再実行。
  - `down`: QMP ソケットと `socat` があれば `system_powerdown` でグレースフル停止を最大 15 秒待ち、残れば `kill`。virtiofsd を `pkill`。
  - `rebuild`: `env VM_FRESH=1 vm-up.sh`（overlay/seed 破棄→再 provision、cloud image は残す）。
  - `portsync`: `vm-portsync.sh` を一発実行（即時同期）。
  - `logs`: `vm-up.log`/`qemu-serial.log`/`virtiofsd.log` の末尾を tail（既定 100 行、第2引数で行数指定）。
- **実装上の判断:** `down` は QMP 経由の powerdown を優先し、失敗・不在時のみシグナル kill にフォールバック。

### vm-portsync.sh(scripts/vm-portsync.sh)

- **責務:** ゲスト dockerd が公開したホストポートを、claude コンテナの `127.0.0.1:PORT` へ QEMU の hostfwd で自動転送する。
- **公開インターフェース:** `vm-portsync.sh`（一発同期）/ `vm-portsync.sh --loop`（常駐）。
- **処理の要点:**
  - `published_ports`: `docker -H tcp://127.0.0.1:2375 ps --format '{{.Ports}}'` から `0.0.0.0:PORT`/`[::]:PORT` のポート番号を抽出しユニーク化。
  - `sync_once`: QMP ソケットと pidfile が有効な各公開ポートについて、未追加なら QMP の `human-monitor-command` で HMP コマンド `hostfwd_add n0 tcp:127.0.0.1:PORT-:PORT` を実行。追加済みは `/run/vm/portsync.forwarded` に `<qemu_pid>:<port>` で記録し重複追加を回避。VM 再起動で pid が変わると自然にリセットされ張り直す。
  - `--loop`: `VM_PORTSYNC_INTERVAL`（既定 5 秒）間隔で `sync_once` を繰り返す。
- **実装上の判断:** `hostfwd_add` は HMP コマンドのため QMP から直接ではなく `human-monitor-command` でラップして送る。QMP 接続ごとに `qmp_capabilities` ネゴを行う。`set -u` のみ（`-e` は付けない＝一時的な docker/QMP 失敗でループを止めない）。

### vm-healthd.sh(scripts/vm-healthd.sh)

- **責務:** ゲスト RAM 逼迫（スラッシング）を、claude コンテナ側の **QEMU プロセス CPU 使用率のみ**から検知して警告する（スラッシング時はゲストの ssh/docker が応答しないためゲストへは問い合わせない）。
- **公開インターフェース:** `vm-healthd.sh`（一度評価して health を書き出力）/ `vm-healthd.sh --loop`（常駐）。
- **処理の要点:**
  - `evaluate_once`: pidfile から QEMU pid を得て（不在なら `STATE=OFF` を書き終了）、`/proc/<pid>/stat` の `utime+stime` を `VM_HEALTH_INTERVAL`（既定 15 秒）間隔で 2 点サンプルし、`getconf CLK_TCK` を用いて 1 コア基準 CPU% を算出。上限 `CEIL` は `/proc/<pid>/cmdline` から解決した `-smp N` × 100%。比率＝CPU%÷CEIL。
  - **判定:** 比率が `VM_HEALTH_CPU_PCT`（既定 60）以上を「hot」とし、連続 `VM_HEALTH_SUSTAIN`（既定 12 回≒3 分）で `WARN`。hot が途切れれば OK へ戻す。低め閾値＋長め窓で一過性ビルドを除外しつつスラッシングを捕捉する。
  - **health ファイル:** `${VM_HOME}/health` を毎周回アトミック上書き（`STATE`/`CPU`/`CEIL`/`TS`/`MSG`）。`vm status` と orchestrator ダッシュボードが読む。鮮度は `TS` で判定。
  - **tmux 連携:** WARN 中は `tmux set -g @vm_health "⚠ VM資源逼迫…"`、OK 復帰で `set -gu`（クリア）。OK→WARN 遷移または `VM_HEALTH_COOLDOWN`（既定 600 秒）経過時のみ `display-message` でフラッシュ。tmux サーバ未起動時（`has-session` 失敗）は各操作をスキップ。
- **実装上の判断:** サンプリング窓＝ループ周期を兼ねる（`sleep INTERVAL` を評価内に含む）。`set -u` のみ。

### VM_DEV.md.tmpl(scripts/VM_DEV.md.tmpl)

- **責務:** VM モード有効時にエージェント向け制御情報 `/workspace/VM_DEV.md` の元になるテンプレート。
- **処理の要点:** 冒頭に「claude-dev VM モードが自動生成・編集不要・必要なら gitignore」を明記。プレースホルダ `@DOCKER_HOST@`（ゲスト dockerd 向け先）と `@VM_PORTS@`（起動時固定公開ポート）を entrypoint が差し替える。記載内容: DOCKER_HOST の意味と proxy 経路への一時上書き方法、bind mount は `/workspace` 配下のみ（virtiofs 同一パス・ライブ反映）、ポート自動転送と `vm portsync`・`claude-dev forward` 併用、`vm` ヘルパー、ssh-agent 既定 A/オプトイン B、トラブルシュート（`vm status`/`vm logs`/`mount | grep virtiofs`）。
- **実装上の判断:** テンプレート本文への差し込みは entrypoint 側が担うため、本ファイルは静的テキスト＋プレースホルダのみ。

## データアクセス

| データ | 操作 | 実施モジュール | 備考 |
|---|---|---|---|
| `${HOME}/.claude-dev-vm/`（overlay/seed/cloud image/鍵/logs/health/user-data） | 生成・読取・削除 | vm-up.sh, vm | 名前付きボリュームで永続化。`rebuild`/`VM_FRESH` で overlay/seed のみ削除 |
| `/run/vm/`（vfs.sock/qmp.sock/qemu.pid/portsync.forwarded） | 生成・読取 | vm-up.sh, vm, vm-portsync.sh, vm-healthd.sh | ランタイム制御。QMP 経由で QEMU を操作 |
| `${VM_HOME}/health` | 書込（healthd）・読取（vm status, orchestrator） | vm-healthd.sh | アトミック上書き（tmp→rename） |

## API実装詳細

外部公開 API なし。ゲスト dockerd への到達は QEMU user-mode hostfwd（`127.0.0.1:2375`→ゲスト `0.0.0.0:2375`）経由で、SLIRP 内側のため実質 claude コンテナ内からのみ到達可能（非公開）。外向き通信は QEMU プロセス経由のため既存 egress firewall が適用される。

## 設定・環境変数

| 名前 | 用途 | デフォルト | 必須 |
|---|---|---|---|
| CLAUDE_DEV_VM | VM モード連携フラグ（cli の `--vm` が 1 を渡し entrypoint が判定） | （未設定） | ○（VM 有効化時） |
| DOCKER_HOST | ゲスト dockerd 向け先。成功時 entrypoint が `/etc/claude-dev/vm.env` に `tcp://127.0.0.1:2375` を書き rc から source | tcp://claude-dev-docker-proxy:2375（既定 DooD） | 否 |
| /dev/kvm | KVM 加速デバイス。vm-up.sh が存在を必須チェック（無ければ FATAL） | ホスト依存 | ○ |
| VM_MEM | ゲスト RAM（`-m` と memfd size 双方で使用・単位付き必須） | 8192M | 否 |
| VM_SMP | ゲスト vCPU 数（healthd の CEIL 算定にも使用） | 2 | 否 |
| VM_DISK | ゲスト overlay サイズ | 20G | 否 |
| VM_SWAP | ゲストスワップファイルサイズ（0/空で無効） | 2G | 否 |
| VM_PORTS | 起動時固定 hostfwd ポート（カンマ区切り） | （空） | 否 |
| CLOUD_IMG_URL | Ubuntu cloud image 取得元 | noble amd64 cloudimg | 否 |
| VM_WAIT_SECS | dockerd 準備待ちタイムアウト秒 | 180 | 否 |
| VM_FRESH | 1 で再 provision 強制（overlay/seed 削除、cloud image 残す） | （未設定） | 否 |
| VM_PORTSYNC_INTERVAL | portsync ループ間隔秒 | 5 | 否 |
| VM_HEALTH_INTERVAL / _CPU_PCT / _SUSTAIN / _COOLDOWN | 資源監視のサンプリング窓/閾値%/継続回数/フラッシュ抑制秒 | 15 / 60 / 12 / 600 | 否 |

## エラーハンドリング実装

| 異常系 | 実装箇所 | 実際の振る舞い | 対応する要件 |
|---|---|---|---|
| `/dev/kvm` 不在 | vm-up.sh 前提チェック | FATAL ログ＋非0終了（TCG フォールバックなし）。cli 側は `--vm` を警告して起動中止 | core/8 |
| qemu/virtiofsd 不在 | vm-up.sh 前提チェック | FATAL ログ＋非0終了 | core/8 |
| ゲスト dockerd がタイムアウト内に起動せず | vm-up.sh dockerd 準備待ち | FATAL ログ＋非0終了。entrypoint は失敗バナーを出し DOCKER_HOST を設定せず既定 DooD 経路を維持（docker 全面不通を回避） | core/8 |
| ゲスト RAM 逼迫（スラッシング） | vm-healthd.sh | QEMU CPU 継続高負荷で WARN。tmux バナー・health ファイル・フラッシュで警告。ゲストへは問い合わせない | core/8 |
| 一時的な docker/QMP 失敗 | vm-portsync.sh / vm-healthd.sh | `set -u` のみ（`-e` なし）でループ継続。次周回で再試行 | core/8 |

## テスト

自動テストは無い（シェル系＝実機確認、[02 テスト戦略]の方針: E2E はシェル系自動テストなし＝実機確認）。静的検証として全スクリプト `bash -n` 緑。以下は要件 core/8 の受け入れ観点を実機（`/dev/kvm` があるホスト）で確認する項目であり、自動テストとしては**未検証（自動テストなし）**。

| テスト(ファイル::ケース名) | レベル | 検証内容 | 対応する受け入れ基準/契約 |
|---|---|---|---|
| 実機確認::start --vm で docker がゲストを指す | 実機 | `DOCKER_HOST=tcp://127.0.0.1:2375`・`docker info` がゲスト daemon | core/8（VM 内ネイティブ Docker） 未検証(自動テストなし) |
| 実機確認::bind mount ライブ反映 | 実機 | `-v /workspace/…` の編集がゲスト内 docker コンテナに即反映 | core/8（virtiofs /workspace 同一パス共有） 未検証(自動テストなし) |
| 実機確認::VM_DEV.md 生成・CLAUDE.md 不変 | 実機 | `/workspace/VM_DEV.md` 生成、CLAUDE.md 非追記 | core/8 未検証(自動テストなし) |
| 実機確認::vm status / vm shell | 実機 | ステータス表示・ssh でゲスト到達 | core/8 未検証(自動テストなし) |
| 実機確認::ポート自動フォワード | 実機 | ゲスト公開ポートが数秒で `127.0.0.1:<port>` に到達（`vm portsync` 即時同期含む） | core/8 未検証(自動テストなし) |
| 実機確認::リセット | 実機 | `vm rebuild` は overlay/seed のみ削除（cloud image 残す）／`--vm-fresh` はボリュームごと破棄で完全再 provision | core/8 未検証(自動テストなし) |
| 実機確認::/dev/kvm 不在で中止 | 実機 | `--vm` が警告して起動中止 | core/8 未検証(自動テストなし) |

実行方法: 自動テストコマンドなし。静的検証は `bash -n scripts/vm-up.sh scripts/vm scripts/vm-portsync.sh scripts/vm-healthd.sh`。動作確認は KVM ホストで `claude-dev start --vm` 後に上表を手動確認。E2E は 03-impl/e2e.md のシナリオ一覧には現状 vm-mode 専用シナリオは無い（core E2E-1〜3 は DooD 経路が対象）。

## 既知の制限・技術的負債

- **virtiofsd の uid 問題:** virtiofsd は uid 1000 で動くため、ゲスト内コンテナが bind mount 先を別 uid へ `chown` する処理（mysql/grafana 等の DB ミドルウェア）は `operation not permitted` で失敗する。bind mount でコンテナ管理データを置くスタックは VM モードで完全動作しない。回避策はデータを名前付きボリューム化してゲスト VM 内に置くこと。
- **Docker API 2375 は非TLS**だが、到達経路が QEMU user-mode hostfwd の `127.0.0.1` のみでネットワーク非公開のため実害はない。
- ネットワークは user-mode（SLIRP）。ゲストは外部から直接到達不可（外向き通信のみ、firewall 適用下）。
- `VM_HEALTH_*` は環境変数上書きのみで、CLI からの明示受け渡しは設けていない（既定値運用）。

## 運用メモ

- ログは `${HOME}/.claude-dev-vm/logs/`（`vm-up.log`/`qemu-serial.log`/`virtiofsd.log`/`portsync.log`/`vm-healthd.log`）。`vm logs` は先頭 3 つを tail する。
- ゲストへ入るには `vm shell`（ssh 2222・注入した `id_vm` 鍵）。シリアルログは補助。
- 既定 DooD 経路との併存: VM モードでも proxy 経路は残る。VM を使わない docker 操作は当該コマンドで `DOCKER_HOST=tcp://claude-dev-docker-proxy:2375 docker …` と一時上書きして戻せる。
- ゲストを白紙化: 稼働中は `vm rebuild`（overlay/seed のみ、cloud image 残す）。完全リセットは `stop` 後 cli の `--vm-fresh`（ボリュームごと破棄＝cloud image も再取得）。
