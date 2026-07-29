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

### [4] 2026-07-29 種別: 質問
- 作業文脈: 「毎日 GHCR イメージを更新しているのにコンテナ内の claude が古い」という指摘の原因調査（起点 00、D-26 の追加）。日次ビルドで Claude Code 導入レイヤーが常に `CACHED` になり同梱版が 2.1.214 で凍結していた。修正方針を決めるにあたり、イメージに焼くバージョンの「正」がどこにも定義されていなかった。
- 内容: 「同梱する Claude Code は `stable` チャネルと `latest` チャネルのどちらを正とするか」を質問。判断が必要だったのは、`install.sh` の引数なし既定が `stable` である一方、観測時点で stable=2.1.212 / latest=2.1.220 / 現に焼かれている版=2.1.214 と食い違い、`stable` を採ると**現状よりダウングレードになる**ため。回答は「`latest` 固定＋障害時のみ手動ピン」。→ D-26 として決定台帳に追加し、01 の要件9 受け入れ基準・02 の設計判断4・03（devcontainer/ghcr-workflow/makefile/cli）へ下方伝播した。
- 根本原因: `00-requests/decisions.md` の D-11（イメージ配布）が「日次・タイムスタンプタグで push」までしか定めておらず、**同梱する外部 CLI のバージョン追随ポリシー（どのチャネル・どこまで自動追随・不良版時の切り戻し手段）が未定義**だった。加えて `request.md` §6 に「外部 CLI（`claude` 等）と各ツールは変化が速い」という前提がありながら、その「変化」をイメージ配布でどう取り込むかが要求として書かれていなかった。D-11 にバージョン追随ポリシーを含めておけば、実装時にチャネル選択で停止せずに済んだ。同種の穴は「外部から取得してイメージへ焼くもの」全般（Terraform は index から最新解決＝版が不定、Go/Python は ARG 固定）にも及ぶため、上流キットでは「イメージへ焼く外部依存ごとに版の追随方針を決める」問いを持つとよい。

### [5] 2026-07-29 種別: 質問
- 作業文脈: D-26 のコード反映（`/implement`。対象 03-impl は devcontainer/ghcr-workflow/makefile/cli）の Phase A ゲート判定。
- 内容: `/change` で文書だけ先に更新した状態で `/doc-check full` を回したため、対象 03-impl 4 件が check B（03-impl⇄コード）で不合格＝合格証を失っていた。一方 `/implement` のゲートは「対象 03-impl と source チェーンが全て verified」を要求するため、規約どおりなら停止し、停止するとコードが変わらず再合格もしない**循環**に入る。人間へ確認せず、「ゲートの趣旨（未検証の仕様から実装しない）は上流 00/01/02 が全 verified なら満たされ、剥落理由は本作業の対象そのものである」と判断して着手し、根拠をタスクドキュメントの「前提（ゲート状況の記録）」節に明記した（完了後に `/doc-check` で循環を閉じる前提）。教訓は `docs/knowledge/docs-ahead-of-code-deadlocks-doc-check.md` に記録。
- 根本原因: 00-requests 側の記述不足ではなく**上流キットのワークフロー規約の穴**。①CLAUDE.md/skills に「/change 後は /doc-check より先に /implement を通す」順序が明示されていない。②check B の不合格には「文書が誤り」と「コードが未了」の 2 種があるのに区別がなく、`/implement` のゲートは両者を同じ「未検証」として扱う。③文書だけ先行した未了作業を示す目印（タスクドキュメント）が /change 時点で作られないため、誰も未了と気づけない（今回 docs/tasks/ は空だった）。キット側で「仕様先行期間の扱い」を定義すればこの判断で迷わずに済む。
