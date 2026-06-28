# 変更履歴: 02_architecture.md

> 対応文書: `docs/02_architecture.md`（旧 `docs/architecture.md`）

## 2026-06-08
- `docs/architecture.md` → `docs/02_architecture.md` にリネーム（番号付け整理）。
- 冒頭に「この文書の役割」を追記し、実装仕様（`docs/impl/`）への参照を追加。
- 内部相互リンク `security.md` → `03_security.md` に更新。
- 完全性確認に伴う実装整合修正: Docker イメージのビルド構成を実装に一致させた。ステージ名を実装どおり `base` / `vnc` に修正（旧記載の `--target claude-dev-claude` 等はイメージ名でありステージ名ではない）。`make build-claude` は `base` のみ、`make build-claude-vnc` が `base`→`vnc`、両方は `make build`、と明記。
- 共通仕様に「ハードウェア仮想化 (KVM/QEMU)」を追記。ホストに `/dev/kvm` がある場合のみ `/dev/kvm`・`/dev/vhost-net`・`/dev/net/tun` をデバイス渡しし、コンテナ内で VM を起動できること（無ければスキップ）を記載。
- KVM デバイス渡しを `claude-dev start --kvm` のオプトインに変更したのに合わせ、記述を「既定では渡さず `--kvm` 指定時のみ渡す」に更新。
