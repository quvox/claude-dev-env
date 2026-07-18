---
title: QEMU user-mode 越しにゲスト dockerd へ到達させる配線の勘所
summary: systemctl enable --now は既起動 daemon を再起動しない。docker.socket の fd 競合は -H fd:// で回避。hostfwd（SLIRP）で届かせるにはゲスト daemon を 0.0.0.0 待受にし、露出はコンテナ 127.0.0.1 hostfwd に限定する
---

## 状況

VM モード（QEMU+virtiofs）で、claude コンテナからゲスト VM 内の dockerd を
`DOCKER_HOST=tcp://127.0.0.1:2375` 経由で透過利用する構成を実機検証した。cloud-init で dockerd の
tcp 待受を設定したが到達できず、原因切り分けで複数の配線ミスが判明した。

## 判断（修正した配線）

- **`systemctl enable --now` は既に起動済みの dockerd を再起動しない**ため override（待受設定）が
  反映されない → `systemctl restart docker` にする。
- unix を明示 `--host=unix://…` すると **`docker.socket` の fd と競合**する → `-H fd://`
  （socket 活性化の unix を維持したまま競合回避）。
- tcp を `127.0.0.1` にすると **QEMU user-mode（SLIRP）の hostfwd が届かない**（hostfwd は
  ゲストの SLIRP IP 宛に転送される）→ ゲスト daemon を **`-H tcp://0.0.0.0:2375`** で待受にする。
  外部露出は「claude コンテナの 127.0.0.1 への hostfwd 経由のみ」に限定され、ネットワークには非公開。
- claude コンテナは `--device /dev/kvm` のみ（非 privileged）。virtiofs で `/workspace` を同一パス共有し
  bind mount がライブ反映する。cloud image はキャッシュし冪等（dockerd 到達時は no-op）。

## 一般化した教訓（今後どう活かすか）

- **`enable --now` は「未起動なら起動」であって「設定を反映して再起動」ではない**。override を効かせたい
  なら明示的に `restart` する。
- systemd socket activation 下の daemon は、待受を手で `--host=unix://` 指定すると socket の fd と
  二重化して競合する。**`-H fd://` を使い socket 活性化に委ねる**。
- **QEMU user-mode ネットワークでは、ゲストのサービスを `127.0.0.1` に縛ると hostfwd が届かない**。
  ゲスト側は `0.0.0.0` 待受にし、**露出の絞り込みはホスト側 hostfwd のバインド先（コンテナの
  127.0.0.1）で行う**。「ゲストで 0.0.0.0 待受」＝「ネットワーク公開」ではない点に注意。
