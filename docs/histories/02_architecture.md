# 変更履歴: 02_architecture.md

> 対応文書: `docs/02_architecture.md`（旧 `docs/architecture.md`）

## 2026-06-08
- `docs/architecture.md` → `docs/02_architecture.md` にリネーム（番号付け整理）。
- 冒頭に「この文書の役割」を追記し、実装仕様（`docs/impl/`）への参照を追加。
- 内部相互リンク `security.md` → `03_security.md` に更新。
- 完全性確認に伴う実装整合修正: Docker イメージのビルド構成を実装に一致させた。ステージ名を実装どおり `base` / `vnc` に修正（旧記載の `--target claude-dev-claude` 等はイメージ名でありステージ名ではない）。`make build-claude` は `base` のみ、`make build-claude-vnc` が `base`→`vnc`、両方は `make build`、と明記。
- 共通仕様に「ハードウェア仮想化 (KVM/QEMU)」を追記。ホストに `/dev/kvm` がある場合のみ `/dev/kvm`・`/dev/vhost-net`・`/dev/net/tun` をデバイス渡しし、コンテナ内で VM を起動できること（無ければスキップ）を記載。
- KVM デバイス渡しを `claude-dev start --kvm` のオプトインに変更したのに合わせ、記述を「既定では渡さず `--kvm` 指定時のみ渡す」に更新。

## 2026-07-01
- 開発ツールの言語一覧に pyenv を追記（Python3 venv/pyenv）。

## 2026-07-04（proxy の /workspace 配下 bind 許可を反映）
- Docker Socket Proxy のセキュリティ説明を更新。ホストバインドは原則拒否だが、呼び出し元の /workspace 配下は実ホストパスへ書き換えて許可する（既定有効・CLAUDE_DEV_ALLOW_WORKSPACE_BINDS で切替）旨と §5 への参照を追記（正本 03_security.md §5 / impl 50）。ASCII 図の `-v /:/host` 拒否例は /workspace 外のため引き続き正。

## 2026-07-04（DooD ポート転送 dood-portsync 追加）
- DooD のポートアクセス設計を追記。DooD ではコンテナ公開ポートがホスト 0.0.0.0:PORT に出て claude コンテナの 127.0.0.1 に届かない問題を、常駐 dood-portsync（socat で 127.0.0.1:PORT→GW:PORT 転送。VM モードの vm-portsync 相当）で解消する旨と、ホスト可視・隔離が要るなら VM モードという整理を記載。
