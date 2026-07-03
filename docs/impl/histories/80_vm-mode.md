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
