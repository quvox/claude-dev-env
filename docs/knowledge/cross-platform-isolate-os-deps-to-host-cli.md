---
title: クロスプラットフォーム対応は OS 依存をホスト CLI に閉じ、コンテナ内資産は共有する
summary: macOS 対応は OS 依存をホスト CLI だけに閉じ、Dockerfile/entrypoint 等コンテナ内資産は共有。非対応オプションは重いビルドの前に早期拒否。arch 差は共有 Dockerfile 内の分岐で吸収し、秘密鍵はマウントせず agent 転送に限定
---

## 状況

Linux 前提の `claude-dev` を macOS（Docker Desktop / Apple Silicon）でも動かすため、ホスト側 CLI の
macOS 版 `claude-dev-mac` を新設した。コンテナ内資産（Dockerfile / entrypoint / firewall /
docker-proxy / tmux.conf）をどこまで共有し、OS 差・CPU アーキ差をどこで吸収するかが論点だった。

## 判断

- **OS 依存はホスト CLI に閉じ、コンテナ内資産は Linux 版とそのまま共有**する。差分は意図した種類のみ
  （`diff` で確認）。利用者コマンド名はどの OS でも `claude-dev`（`make install` が OS 判定して配置）。
- **非対応オプション（VM/KVM）は重いイメージビルドの前に早期拒否**。`--vm`/`--kvm`/`--vm-fresh` を
  `require_setup`（重ビルド）より前で exit 1 にし、無駄なビルドをゼロ化。VM 用の 420 秒待機分岐等も
  macOS 版から完全除去。
- **CPU アーキ差は共有 Dockerfile 内の arch 別分岐で吸収**（amd64 は従来と同一で後方互換）:
  gcloud は URL のアーキ名を写像（`aarch64`/`arm64`→`arm`、写像しないと 404）、GUI ブラウザは
  amd64=Google Chrome／arm64=base 導入済み Playwright Chromium に分岐し、呼び出しは共通ランチャー
  `claude-dev-chrome`（ビルド時生成の薄い exec ラッパー、実行時に arch 判定や外部取得をしない）に統一。
- **秘密鍵は非マウントの不変条件を維持**。macOS はホストの Unix ソケットを直接マウントできないため、
  Docker Desktop の魔法ソケット `/run/host-services/ssh-auth.sock` を転送（agent プロトコルのみ、
  鍵ファイルは渡らない）。生 Docker ソケットも渡さず Docker Socket Proxy 経由（RO マウント）を維持。

## 一般化した教訓（今後どう活かすか）

- クロスプラットフォーム対応は **「差分をどの層に閉じるか」を最初に決める**。コンテナ内資産を共有し
  OS 依存をホスト CLI に閉じ込めると、二重メンテを避けられ後方互換も保てる。
- **サポート外オプションは、コストの高い処理（ビルド・長時間待機）に入る前に早期拒否**する。エラーでも
  ビルド時間をゼロにできる。
- 共有ファイル内の**アーキ別分岐は薄い共通ラッパーの裏に隠す**（呼び出し側は arch を意識しない）。
  URL にアーキ名を含む取得（gcloud 等）は写像漏れで 404 になりやすい定番の穴。
- OS が変わっても **「秘密鍵はマウントせず agent 転送のみ／生 docker.sock は proxy 経由」という
  セキュリティ不変条件は維持する**。実現手段（魔法ソケット等）だけを OS ごとに差し替える。
