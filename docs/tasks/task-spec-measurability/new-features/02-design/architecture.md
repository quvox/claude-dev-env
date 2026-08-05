---
target: docs/02-design/architecture.md
change: replace
sections:
  - "## コンポーネントの責務"
deletes: []
reason: >
  NFR-sec-02 と NFR-ops-01 の削除(決定シート概念#2・#6)に伴い、責務表の「対応要件」列から
  両 ID を外す。container-tools は NFR-ops-01 が唯一の要件だったため、モジュール分割定義
  (system.md:64)が持つ FR-env-01 へ差し替える。責務そのものは変えない。
---

<!-- 変更は「対応要件」列の3行だけ: firewall(`NFR-sec-02` を外す)/
     hooks(`NFR-ops-01` を外す)/ container-tools(`NFR-ops-01` → `FR-env-01`)。
     VM モードの行の「資源逼迫」は用語集が閾値付きで定義した語なので書き替えない。 -->

## コンポーネントの責務

| コンポーネント | 責務 | 対応要件 |
|---|---|---|
| ホスト CLI | コンテナのライフサイクル・認証・ポート・SSH 鍵・オーケストレーター起動。OS 依存をここに閉じる | FR-env-01〜FR-env-12, FR-orch-02 |
| Makefile | ビルド・セットアップ・CLI の導入/除去・自己検証題材の配置 | FR-env-09, FR-env-10, FR-orch-09 |
| コンテナイメージ | 開発ツール・エージェント CLI・ブラウザ確認資産を同梱した実行基盤 | FR-env-09, FR-env-11, FR-env-12 |
| entrypoint | コンテナ起動時の初期化(UID/GID・認証・既定設定・ファイアウォール・VNC・tmux・同期ループ) | FR-env-02, FR-env-03, FR-env-05, FR-env-11, FR-env-12 |
| firewall | コンテナ内の外向き通信制御 | FR-env-05 |
| docker-proxy | Docker API の検査・書き換え・拒否。全コンテナで共有 | FR-env-07, NFR-sec-01 |
| portsync | 公開ポートの検出と転送(DooD / VM の両経路) | FR-env-06 |
| orchestrator | 2モードの制御ループ・worker 並列・介入・レビュー・TUI・通知・状態保全 | FR-orch-01〜FR-orch-08 |
| hooks | エージェントのイベントを受けてプロンプト保存と通知を行う | FR-orch-07 |
| container-tools | コンテナ内で利用者が使う補助資産(レート制限の待機など) | FR-env-01 |
| VM モード | ゲスト VM の起動・provision・ポート同期・資源逼迫の監視 | FR-env-08 |
| 自己検証題材 | オーケストレーターを実走させて振る舞いを確認するための題材 | FR-orch-09 |
