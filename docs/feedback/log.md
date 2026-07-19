# フィードバックログ（上流キット向けテレメトリ）

質問／修正／委任判断の記録。詳細は CLAUDE.md「Feedback log」節を参照。

### [1] 2026-07-18 種別: 委任判断
- 作業文脈: 03-impl 各モジュールの逆生成（旧 docs/impl/*.md ＋実コードから再構成）。
- 内容: D-20（逆生成時の軽微な曖昧さの穴埋め＝コードを正とする）を各モジュールで行使。旧 docs と実コードが食い違う軽微点を、いずれもコード側に合わせて記述した。主な補正:
  - makefile: `install` は OS 分岐なく常に `sudo ln -sf`（旧「OS 分岐」記述を修正）。`.PHONY` に `env` 欠落を明記。
  - firewall: allowlist カスタマイズは環境変数でなく `BLACKLIST_DOMAINS` 配列の直接編集。`BLACKLIST_PORTS` 配列は不在。
  - devcontainer: orch-builder は `vendor/`＋`-mod=vendor`（旧「stdlib のみ・go.sum 不要」は誤り）。同梱スクリプトは旧記載より多い（wait-limit-reset・VM系・dood-portsync 等）。`GO_VERSION=1.26.1`。
  - cli: `orchestrate` は `mouse on`（旧 `mouse off`）。`code` は `CLAUDE_DEV_VM=1` 時に VM ポインタを注入。fallback セッション名は `orch-main`。`image_version` は `io.github.quvox.claude-dev.version` ラベル（コード内コメントが古い）。
  - cli-mac: top-level `reset` は専用 agent を掃除しない（`ssh-keys reset` のみ）。
  - vm-mode: `vm logs` は `virtiofsd.log` も対象。ポート検出は `[::]:PORT`（IPv6）も対象。
  - docker-proxy: 拒否=403／中継失敗=502。hijack 対象は exec start/attach・exec/container resize の4種。無効化トークンは `0/false/no/off`。
- 根本原因: なし（委任の行使）。

### [2] 2026-07-18 種別: 委任判断
- 作業文脈: 01-requirements/orchestration.md（要件20 自己検証）の再構成中に、実コード（Makefile の `orch-sample` ターゲット）との食い違いを発見。
- 内容: 旧要件・旧 impl 文書は「`make orch-sample` でオーケストレーターを実走させる」としていたが、実際の `make orch-sample` は `scripts/orch-sample.sh` による題材 scaffold までで、実走は別ステップ（`claude-dev orchestrate`）。D-20 の趣旨（コードを正）に沿い、要件20 を「scaffold と実走を分離」する形に補正し、02-design/system.md（E2E-4・テスト戦略）と 03-impl/e2e.md へ下方伝播させた。要件・振る舞いに触れる補正のため、下流に留めず 01 を起点に修正し、本ログにも記録して人間確認に付す。
- 根本原因: なし（委任の行使。ただし要件記述の不正確さに起因するため、上流の acceptance/要件の初期記述精度の論点として共有）。

### [3] 2026-07-19 種別: 質問
- 作業文脈: 03-impl（cli/cli-mac/entrypoint）で、複数プロジェクト同時起動時の docker compose 衝突（既定プロジェクト名 `workspace` の衝突）を修正中。ユーザーの「ネットワーク分離は要求事項」という指摘を受け、分離の対象範囲を確認した。
- 内容: 「ネットワーク分離」が (a) compose 層（各プロジェクトの `docker compose` が作るネットワーク/コンテナ名）なのか、(b) `claude-dev-net` 層（claude コンテナ↔共有 docker-proxy）まで含むのかを質問。回答は「compose 層の分離で十分」。→ `claude-dev-net` は現行要件5-2（単一共有）のまま維持し、要件変更なし。今回の `-e COMPOSE_PROJECT_NAME` 修正が該当要件を満たす。
- 根本原因: 00-requests/01-requirements に「複数プロジェクト同時起動時、各プロジェクトの docker compose リソース（ネットワーク名・コンテナ名）はプロジェクト間で衝突してはならない」という要件が明記されておらず、compose 層の分離が要件なのか実装詳細なのかが曖昧だった（要件5 はネットワーク隔離＝FW と claude-dev-net 共有のみを述べ、compose リソースの一意化には触れていない）。00-requests に当該要件を追記すれば、実装詳細か要件かの判断で迷わずに済んだ。
