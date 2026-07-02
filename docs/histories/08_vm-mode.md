## 2026-07-03（新規作成）
- 新規作成。Docker を多用する開発向けに、claude コンテナ内で QEMU/KVM のゲスト VM を起動し、その中でネイティブ Docker を動かす「VM モード」の設計。
- 確定方式: (a) Ubuntu cloud image を初回起動時に遅延 provision（ボリュームキャッシュ）、(b) user-mode ネット + hostfwd、(c) DOCKER_HOST 転送TCP + virtiofs 同一パス(/workspace)共有（bind はその配下のみ・ライブ反映）。
- 起動主体は基盤（entrypoint、人間の --vm オプトイン起点）。agent は DOCKER_HOST と /workspace 同一パスで VM を意識せず docker を使える（透過）。最小限の理解は VM_DEV.md で付与。
- VM_DEV.md（/workspace）に VM 制御情報を集約し CLAUDE.md は不可侵。発見導線＝バナー／orchestrator プロンプト前置／--append-system-prompt の3系統。
- ssh-agent は既定 A（SSH/git は claude 側・ゲストに出さない）／B オプトイン（socat 転送。virtiofs は unix socket 転送不可）。
- セキュリティ: claude コンテナは privileged 化せず --kvm デバイスのみ。VM 境界に bind/privileged を隔離。SLIRP egress は既存 firewall 配下。
- 設計↔実装仕様の整合性確認（独立2エージェント×2パス）で検出した齟齬を是正（provision タイミング等を確定へ、dockerd unix socket・vm logs・/dev/kvm 無し中止を明記、vm-shell 表記統一）。
