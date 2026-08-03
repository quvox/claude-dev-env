---
target: docs/03-impl/relations/MODULE-vm-mode-up.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-vm-mode-up
module: MOD-vm-mode
kind: tool
sync: sync
impl: scripts/vm-up.sh::main
callers: MODULE-entrypoint-claude
callees: なし
contracts: なし
design: DSN-mod-01, DSN-mod-03, DSN-arch-01
requirements: FR-env-08
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する。静的検証として `bash -n` は緑)
updated: 2026-08-02
summary: QEMU/KVM で VM を起動し provision して常駐ヘルパーを立ち上げる
---

# MODULE-vm-mode-up ゲスト VM の起動と provision

## 目的

DooD + docker-proxy 構成では privileged や広範な bind を伴う「Docker 中心開発」が成立しない。
claude コンテナ内で QEMU/KVM のゲスト VM を起動し、その中でネイティブ Docker を動かすことで
この制約を外す(FR-env-08)。claude コンテナ自身は privileged にせず隔離を保つ。

## 処理の流れ

1. パスを定義する: `VM_HOME=${HOME}/.claude-dev-vm`、`RUN_DIR=/run/vm`、
   `ubuntu-cloud.img`、`guest-overlay.qcow2`、`seed.iso`、SSH 鍵 `id_vm`、
   virtiofs ソケット `vfs.sock`、QMP `qmp.sock`、`qemu.pid`。
   `virtiofsd` は PATH に無いため `command -v virtiofsd || /usr/libexec/virtiofsd` で絶対解決する。
2. `VM_FRESH=1` なら走行中の QEMU を kill し virtiofsd を止め、overlay と seed を削除する
   (再 provision の強制。cloud image のキャッシュは残す)。そうでなく `dockerd_ready`
   (`docker -H tcp://127.0.0.1:2375 info`)が真なら、冪等に portsync / healthd を起こして終了する。
3. **前提チェック**: `/dev/kvm`(キャラクタデバイス)・`qemu-system-x86_64`・`virtiofsd` の存在。
   欠ければ FATAL を出して非0終了する(TCG へのフォールバックはしない)。
4. **初回 provision**(overlay 不在時): cloud image を未取得なら `curl` で取得
   (`.part` → rename)、`qemu-img create -f qcow2 -F qcow2 -b <cloud-img>` で backing overlay を
   作り(サイズ `VM_DISK`)、`ssh-keygen -t ed25519` で鍵を作り、cloud-init の user-data を生成して
   `cloud-localds` で seed ISO にする。
   user-data はユーザ `dev`(NOPASSWD sudo・`docker` グループ・生成公開鍵)を作り、`docker.io` を入れ、
   `/workspace` を `/etc/fstab` に `workspace /workspace virtiofs defaults,nofail 0 0` で追記して
   `mount -a` し、dockerd を systemd drop-in で `-H fd:// -H tcp://0.0.0.0:2375` に上書きして
   `daemon-reload` → `enable docker` → **`restart docker`** する(`enable --now` では既に起動している
   dockerd が再起動されず tcp が有効化されないため)。tcp を **0.0.0.0** で待ち受けるのは、
   QEMU user-mode の hostfwd がゲスト SLIRP IP 宛に転送するため 127.0.0.1 では届かないから。
5. **スワップ確保**(`VM_SWAP` が 0 でも空でもないとき): provision 生成時に `numfmt --from=iec` で
   MB へ確定して user-data に焼き込み(既定 2048MB へフォールバック)、runcmd で
   `fallocate`(失敗時 `dd`)→ `chmod 600` → `mkswap` → `swapon` → fstab 追記(冪等)を行う。
   RAM 超過時のページ回収スラッシングでゲストが stall するのを防ぐ。
6. **virtiofsd 起動**: 既存が無ければ
   `virtiofsd --socket-path=<vfs.sock> --shared-dir=/workspace --sandbox=none` を背後で起動し、
   ソケット生成を最大5秒ポーリングする。
7. **hostfwd 組み立て**: 既定は
   `hostfwd=tcp:127.0.0.1:2375-:2375,hostfwd=tcp:127.0.0.1:2222-:22`。`VM_PORTS`(カンマ区切り)が
   あれば各ポートを追加する。
8. **QEMU 起動**: `-enable-kvm -cpu host -m ${VM_MEM} -smp ${VM_SMP}`、overlay を `if=virtio`、
   共有メモリ `memory-backend-memfd,size=${VM_MEM},share=on` と `-numa node,memdev=mem`
   (virtiofs には共有メモリが必須)、vhost-user-fs(tag=`workspace`)、`-netdev user` に hostfwd、
   初回だけ seed ISO を `if=virtio,media=cdrom` で添付、`-display none`、シリアルをログへ、
   `-qmp unix:<qmp.sock>`、`-pidfile` と `-daemonize` で常駐化する。
   **`VM_MEM` は `-m` と `memory-backend-memfd,size` の双方で同一の単位付き表記を使う**
   (無単位だと解釈が食い違い `-numa` の RAM 不一致で起動に失敗する)。
9. **dockerd 準備待ち**: `dockerd_ready` を最大 `VM_WAIT_SECS`(既定180)回、1秒間隔で同期ポーリング
   する。準備できたら `start_portsync` / `start_healthd` を起こして 0 で終わり、
   タイムアウトなら非0で終わる。
10. `start_portsync` / `start_healthd` はそれぞれ `vm-portsync.sh --loop` / `vm-healthd.sh --loop`
    を `setsid …&` で起動する。多重起動は `pgrep -f` で防ぐ。

## 呼び出され方

- 契機: `MODULE-entrypoint-claude` が `CLAUDE_DEV_VM=1` のときに実行する。利用者が
  `MODULE-vm-mode-cli` の `vm restart` / `vm rebuild` から呼ぶこともある。
- 前提条件: `/dev/kvm` が `MODULE-cli-start` の `--kvm` / `--vm` で渡っていること。
- 引数: なし(すべて環境変数で制御する)。

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `VM_FRESH` | 環境変数 | 任意 | `1` で再 provision を強制する |
| `VM_MEM` / `VM_SMP` / `VM_DISK` / `VM_SWAP` | 環境変数 | 任意 | 既定 `8192M` / `2` / `20G` / `2G`。`VM_MEM` は単位付き必須 |
| `VM_PORTS` | 環境変数 | 任意 | 起動時に固定で hostfwd するポート(カンマ区切り) |
| `VM_WAIT_SECS` | 環境変数 | 任意 | dockerd 準備待ちのタイムアウト秒(既定180) |

- 認可: コンテナ内のユーザ。

## 連携先と連携内容

連携先なし(`qemu-system-x86_64` / `virtiofsd` / `curl` / `docker` の実行は外部コマンド呼び出し。
常駐ヘルパーの起動も `setsid` によるプロセス起動であり、機能間の辺には現れない)。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 0 = ゲスト dockerd 準備完了 / 非0 = 前提不足またはタイムアウト。**entrypoint はこの終了コードだけで成否を判定する** |
| 永続化 | **`${HOME}/.claude-dev-vm/`**(`ubuntu-cloud.img`・`guest-overlay.qcow2`・`seed.iso`・`id_vm`・`logs/`・`user-data`)と **`/run/vm/`**(`vfs.sock`・`qmp.sock`・`qemu.pid`)。前者は名前付きボリュームで永続化される |
| 発火するイベント | `vm-portsync.sh --loop` と `vm-healthd.sh --loop` の常駐起動 |
| ログ | `${HOME}/.claude-dev-vm/logs/vm-up.log`・`qemu-serial.log`・`virtiofsd.log` |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| `/dev/kvm` が無い | FATAL を出して非0終了する(TCG へフォールバックしない) | entrypoint は失敗バナーを出す。`MODULE-cli-start` は `--vm` 指定時に事前に `exit 1` する |
| `qemu-system-x86_64` / `virtiofsd` が無い | FATAL を出して非0終了する | 同上 |
| ゲスト dockerd がタイムアウト内に起動しない | FATAL を出して非0終了する | entrypoint は失敗バナーを出し、`DOCKER_HOST` を設定せず**既定の DooD 経路を維持する**(docker が全面不通になるのを避ける) |
| 既に dockerd が到達可能 | 何もせず portsync / healthd だけ起こして 0 で終わる(冪等) | なし |
| cloud image の取得に失敗 | provision が失敗して非0終了する | 起動できない |
| `VM_MEM` を無単位で指定 | `-m` と `memory-backend-memfd,size` の解釈が食い違い `-numa` の RAM 不一致で QEMU の起動に失敗する | 非0終了 |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 待ち受けの主体を本スクリプトに一本化する(entrypoint は終了コードだけを待つ) | D0-scope-04 |
| 2 | TCG(ソフトウェアエミュレーション)へフォールバックしない(遅すぎて実用にならないため、KVM が無ければ明示的に失敗させる) | D0-scope-04 |
| 3 | dockerd の tcp を `0.0.0.0` で待ち受ける(QEMU user-mode の hostfwd はゲスト SLIRP IP 宛に転送するため) | D0-scope-04 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| **virtiofsd が uid 1000 で動く** | ゲスト内コンテナが bind mount 先を別 uid へ `chown` する処理(mysql / grafana 等)が `operation not permitted` で失敗する。回避策はデータを名前付きボリューム化してゲスト VM 内に置くこと | なし |
| Docker API 2375 が非 TLS | 到達経路が hostfwd の `127.0.0.1` だけでネットワークに公開されないため実害は無い | なし |
| ネットワークが user-mode(SLIRP) | ゲストへ外部から直接到達できない(外向き通信のみ。firewall 適用下) | なし |
