## 2026-07-03（新規作成）
- 新規作成。VM モード（QEMU+virtiofs）の実装仕様。Dockerfile へ virtiofsd・cloud-image-utils 追加、Ubuntu cloud image の遅延 provision（cloud-init seed）、vm-up.sh（virtiofsd＋QEMU 常駐＋dockerd 同期待ち）、claude-dev の start --vm、vm ヘルパー、VM_DEV.md 生成、DOCKER_HOST/hostfwd 配線を規定。
- 実装仕様内および設計(08)との整合性確認（独立エージェント）で検出した点を是正:
  - VM_MEM は単位付き（例 4096M）を規定し -m と memory-backend-memfd size で同一表記（無単位だと起動失敗）。
  - vm-up 失敗時は DOCKER_HOST を設定せず proxy 既定を維持（docker 全面不通を回避）。成功時のみ DOCKER_HOST env スニペット出力＋VM_DEV.md 生成。
  - QEMU は -daemonize＋シリアル/QMP をログ/socket へ（vm-up.sh が返る）。ログ位置・初回判定（overlay qcow2 の有無）・ゲストアクセス主経路(ssh 2222)を明記。
  - `--vm` 時は 31_entrypoint.md の「CLAUDE.md へ KVM セクション追記」を抑止し VM_DEV.md へ集約（CLAUDE.md 不可侵）。
  - 発見導線3系統（バナー/orchestrator 前置=60 側/--append-system-prompt=claude-dev）を明記し関連文書に 60 を追加。proxy 併存（DOCKER_HOST 一時上書き）を明記。
- 実装状況: 設計確定・未実装（次フェーズ）。

## 2026-07-03（実装）
- VM モードを実装: Dockerfile.claude（apt に virtiofsd/cloud-image-utils、scripts COPY）、scripts/vm-up.sh（初回 cloud-init provision＋virtiofsd＋QEMU 常駐＋dockerd 同期待ち）、scripts/vm（status/shell/restart/down/logs）、scripts/VM_DEV.md.tmpl、entrypoint（VM 起動・DOCKER_HOST env スニペット・VM_DEV.md 生成・バナー・--vm 時の CLAUDE.md KVM 追記抑止）、claude-dev（start --vm＝--kvm 含意・/dev/kvm 無しで中止・CLAUDE_DEV_VM/ボリューム/VM_PORTS 付与、code で --append-system-prompt 注入）。
- 静的検証: 全スクリプト bash -n 緑。base イメージ上で virtiofsd/cloud-image-utils の導入可能性を確認。
- 【ビルド検証で発見・修正】virtiofsd は PATH に無く /usr/libexec/virtiofsd に入るため、vm-up.sh を絶対パス解決（command -v || /usr/libexec/virtiofsd）に修正。qemu-system-x86_64/cloud-localds/qemu-img は PATH 上。
- 未検証: 実機 VM ブート E2E（cloud-init/QEMU/virtiofs/docker-in-VM、要 /dev/kvm ホスト）。
- 未実装（次段階）: 発見導線2（orchestrator プロンプト前置＝60 側 Go 改修）。

## 2026-07-03（実機 E2E 検証・cloud-init 修正）
- KVM ホストで実機 E2E を実施し全項目合格（docs/reviews/2026-07-03_vm-mode-e2e.md）: provision→QEMU→virtiofs 同一パス共有→ゲスト dockerd 到達→bind mount ライブ反映、自動化（vm-up 自力で dockerd 検知）。
- 実機で発見・修正: ゲスト dockerd の tcp 待受設定を `-H fd:// -H tcp://0.0.0.0:2375`＋`systemctl restart docker` に是正（enable --now は再起動しない／unix 明示は docker.socket と競合／127.0.0.1 は hostfwd が届かない）。80 §3/§8・08 §3.2 を実態へ更新、実装状況を「実機 E2E 検証済み」に。

## 2026-07-03（orchestrator の VM 対応）
- orchestrator を VM モードで透過利用できるよう配線: `claude-dev orchestrate` が起動前に `/etc/claude-dev/vm.env` を source し、ゲスト DOCKER_HOST を orchestrator（および claudeChildEnv 経由で worker）へ引き継ぐ（非対話起動は rc を読まないため）。VM 未起動時は proxy にフォールバック。
- 発見導線2 を実装: `state.go` の `VMModePreamble()`（CLAUDE_DEV_VM=1 で定型ポインタを返す）を mode.go(WallbounceArgs/ResolveArgs)・worker.go(BuildPrompt)・review.go(buildReviewPrompt) の先頭に LoadProjectPolicy と並べて前置。worker/reviewer/壁打ち/介入が「docker はゲスト・bind は /workspace 配下・詳細 VM_DEV.md」を認識。CLAUDE.md 非侵襲。
- 80/60/10_cli/08 を更新。単体テスト（VMModePreamble の off/on とプロンプト前置）追加・緑。DOCKER_HOST 継承をシェルで確認。実機の orchestrator×VM 通し E2E は要イメージ再ビルドで次段階。

## 2026-07-03（実運用修正: 権限/再provision/uid制約/ポート自動転送）
- entrypoint: `su $USERNAME` で走る vm-up.sh の前に、root 所有のマウント点/実行時ディレクトリ（`$USER_HOME/.claude-dev-vm`・`/run/vm`）を `install -d -o $USERNAME` で先に用意（未対応だと mkdir が Permission denied で VM 起動失敗）。
- `--vm-fresh`（claude-dev）/`vm rebuild`（vm）を追加。`VM_FRESH=1` で走行中 VM 停止＋overlay/seed 破棄→再 provision。`--vm-fresh` は起動時にゲスト用ボリュームも破棄。
- start --vm の待ち時間を延長（VM は 420s、通常 30s）＋進捗表示＋タイムアウト時の案内（無言 attach 失敗を回避）。所要時間メッセージを表示。
- 既知の uid 制約を明記（80 §5・08）: virtiofsd は uid1000 で動くため、ゲスト内コンテナが bind mount を別 uid へ chown する処理（mysql/grafana 等）は `operation not permitted`。root 化は逆に生成物が管理不能になる両刃のため、bind mount にコンテナ管理データを置くスタックは非対応（named volume 化で回避）。root-virtiofsd 案は撤回。
- **ポート自動転送を実装**: `scripts/vm-portsync.sh`（新規）がゲスト docker の公開ポートを検出し QMP `hostfwd_add n0 tcp:127.0.0.1:P-:P` で claude 側 localhost へ同期。vm-up.sh がゲスト dockerd 準備完了後に `--loop`（既定5秒間隔・多重起動防止）で常駐起動。一発同期は `vm portsync`。`/run/vm/portsync.forwarded`（`<qemu_pid>:<port>`）で重複防止・VM 再起動で自然リセット。`VM_PORTS` 手動指定なしで公開ポートが自動到達。Dockerfile に COPY 追加、VM_DEV.md.tmpl のポート節を自動転送前提に更新。
- 実機検証: 一発同期で新規ポート即到達、常駐ループが後付けコンテナのポートを数秒で自動フォワード（いずれも稼働中コンテナへ hot-copy して確認）。恒久反映は要 `make build`。

## 2026-07-04（既定 RAM 8G 化・スワップ確保）
- 原因特定: 実機 VM モード（別プロジェクト）が異常に遅い件を調査。ゲスト load avg 178・Swap 0・空き 350MB・kswapd0 43%・PSI memory full avg300 55%・QEMU が host CPU 150% 常時消費。TCP(2222/2375)は接続可だが ssh 認証/docker API が応答しない＝メモリ枯渇＋スワップ無しによるページ回収スラッシングでユーザーランドが CPU 枯渇。仮想化オーバーヘッドではない。
- `scripts/vm-up.sh`: 既定 `VM_MEM` を 4096M→8192M に変更。`VM_SWAP`（既定 2G・0/空で無効）を追加し、cloud-init user-data の runcmd にスワップファイル作成（生成時に MB 確定→`fallocate`／失敗時 `dd` フォールバック→`mkswap`→`swapon`→fstab 追記・冪等）を注入。§3 のマウント直後に配置。
- `claude-dev`: `start --vm` の env 受け渡しループに `VM_SWAP` を追加（`VM_PORTS VM_MEM VM_SMP VM_DISK VM_SWAP`）。上書き可能に。
- 80 §3（スワップ手順）・§4（既定値 VM_MEM=8192M / VM_SWAP=2G）・§4 のメモリ単位一致の例・実装状況、08 §3.3・§4 正本ポインタを更新。
- 静的検証: `bash -n` 緑（vm-up.sh / claude-dev）。user-data 生成をVM_SWAP=2G/2048M/0 でシミュレートし YAML インデント・dd count・無効時の空行が正しいことを確認。既定値変更・スワップは**要 provision 反映**（稼働中ゲストは `vm rebuild`／`--vm-fresh`、または既存ゲストへ手動 swapon）。

## 2026-07-04（vm-healthd: ゲスト資源逼迫の検知・警告）
- §7.2 を新設。`scripts/vm-healthd.sh`（新規・常駐）が QEMU プロセスの CPU（`/proc/<pid>/stat` の utime+stime を `VM_HEALTH_INTERVAL` 窓で2点サンプル、上限は `/proc/<pid>/cmdline` の `-smp` から解決）を評価し、上限比が `VM_HEALTH_CPU_PCT`（既定60%）以上を `VM_HEALTH_SUSTAIN`（既定12回≒3分）継続で WARN。ゲストには一切問い合わせない。
- 警告: WARN 中は tmux `@vm_health` を set（OK 復帰で unset）＋遷移時 `display-message` フラッシュ（`VM_HEALTH_COOLDOWN` 既定600秒で抑制）。health ファイル `${CHOME}/.claude-dev-vm/health`（STATE/CPU/CEIL/TS/MSG）を毎周回書き、`vm status`・orchestrator dashboard が読む。
- `vm-up.sh`: `start_healthd()` を追加し dockerd 準備後に portsync と併せ常駐起動（pgrep で多重起動防止）。`scripts/vm`: `status` に health 表示を追加。`tmux.conf`: status-right に `@vm_health` を条件表示。`Dockerfile.claude`: vm-healthd.sh を COPY＋chmod。
- カバーするコード・実装状況・関連文書（60/30/40）を更新。
- 検証: `bash -n` 緑。稼働中 VM（別プロジェクト）の実 QEMU に対しワンショット実行し、-smp からの上限解決（200%）・CPU 算出・WARN/OK 分岐・health ファイル生成を確認。**要イメージ再ビルドで全 VM に反映**（tmux.conf は RO マウントのため再 start で反映）。
