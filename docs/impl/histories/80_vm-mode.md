## 2026-07-03（新規作成）
- 新規作成。VM モード（QEMU+virtiofs）の実装仕様。Dockerfile へ virtiofsd・cloud-image-utils 追加、Ubuntu cloud image の遅延 provision（cloud-init seed）、vm-up.sh（virtiofsd＋QEMU 常駐＋dockerd 同期待ち）、claude-dev の start --vm、vm ヘルパー、VM_DEV.md 生成、DOCKER_HOST/hostfwd 配線を規定。
- 実装仕様内および設計(08)との整合性確認（独立エージェント）で検出した点を是正:
  - VM_MEM は単位付き（例 4096M）を規定し -m と memory-backend-memfd size で同一表記（無単位だと起動失敗）。
  - vm-up 失敗時は DOCKER_HOST を設定せず proxy 既定を維持（docker 全面不通を回避）。成功時のみ DOCKER_HOST env スニペット出力＋VM_DEV.md 生成。
  - QEMU は -daemonize＋シリアル/QMP をログ/socket へ（vm-up.sh が返る）。ログ位置・初回判定（overlay qcow2 の有無）・ゲストアクセス主経路(ssh 2222)を明記。
  - `--vm` 時は 31_entrypoint.md の「CLAUDE.md へ KVM セクション追記」を抑止し VM_DEV.md へ集約（CLAUDE.md 不可侵）。
  - 発見導線3系統（バナー/orchestrator 前置=60 側/--append-system-prompt=claude-dev）を明記し関連文書に 60 を追加。proxy 併存（DOCKER_HOST 一時上書き）を明記。
- 実装状況: 設計確定・未実装（次フェーズ）。
