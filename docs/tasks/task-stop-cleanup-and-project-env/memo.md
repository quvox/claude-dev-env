---
id: task-stop-cleanup-and-project-env
phase: 反映
lane: critical
origin_layer: 00
external_behavior: true
irreversible_data: true
security_payment_privacy: true
public_contract_breaking: false
shared_resource_format: true
unresolved_impact: false
rollback_defined: false
issue: docs/issues/002-modify-claude-dev-yaml-is-overwritten-wholesale.md, docs/issues/092-modify-01-says-stop-halts-docker-proxy-while-the-code-deletes-it.md
origin: human-report
date: 2026-08-18
updated: 2026-08-19
source:
  - docs/00-requests/request.md
  - docs/00-requests/acceptances.md
  - docs/00-requests/terminology.md
  - docs/00-requests/decisions/env.md
  - docs/00-requests/decisions/sec.md
  - docs/01-requirements/functional.md
  - docs/01-requirements/usecases.md
  - docs/01-requirements/decisions/split.md
  - docs/02-design/architecture.md
  - docs/02-design/system.md
  - docs/02-design/relations.md
  - docs/02-design/logging.md
  - docs/02-design/contracts/cli-container.md
  - docs/02-design/contracts/docker-api.md
  - docs/03-impl/relations/MODULE-cli-stop.md
  - docs/03-impl/relations/MODULE-cli-reset.md
  - docs/03-impl/relations/MODULE-cli-start.md
  - docs/03-impl/relations/MODULE-cli-common-spawned-resources.md
  - docs/03-impl/relations/MODULE-cli-common-write-project-ssh-keys.md
  - docs/03-impl/relations/MODULE-cli-ssh-keys-reset.md
  - docs/03-impl/relations/MODULE-docker-proxy-serve.md
  - docs/03-impl/index.md
  - docs/03-impl/tests/cli-stop.md
  - docs/03-impl/tests/cli-start.md
  - docs/03-impl/tests/docker-proxy.md
  - docs/03-impl/tests/cli-reset.md
  - docs/03-impl/tests/e2e.md
summary: stop のセッション由来資源の片付けをボリュームまで広げるかを決め、あわせて .claude-dev.yaml で任意の環境変数をコンテナへ渡せるようにする
---

# task-stop-cleanup-and-project-env stop の片付け範囲とプロジェクト環境変数

> 解決済みの経緯: `memo-1.md`(帰着済みの未決点7件 / フェーズ1〜2 の調査メモ17件 / フェーズ1〜2 の進捗の詳細)

## 目的

人間からの2件の依頼を1回の降下で扱う。
**R-01**: `claude-dev stop` がそのセッションの中から作られた資源(コンテナ・ネットワーク・
マウント)を片付ける機能が「正しく動作していない」という指摘に対処する。
**R-02**: `.claude-dev.yaml` に書いた任意の環境変数を claude-dev のコンテナへ渡せるようにする。

## やること・やらないこと

| 種別 | 内容 |
|---|---|
| やること | **R-01-a**: `stop` が「存在しなかった compose 既定ネットワーク」を「削除できませんでした」として表示する欠陥を直す(実測で再現。下の調査メモ 3)。**R-01-b**: 名前付きボリュームを片付けの対象に加えるかを決め、決まったとおりに 00→03 とコードを降ろす(決定シート 概念1 / 論点1)。**R-02-a**: `.claude-dev.yaml` に **env ファイルのパス**を書けるようにし、`start` がその env ファイルを読んでコンテナへ環境変数として渡す。env ファイルは Git の追跡から外す(2026-08-19 の人間の回答。決定シート 論点2)。**R-02-b**: その前提として `docs/issues/002`(`.claude-dev.yaml` が全面上書きされ、`ssh-keys reset` が全リスト行を消す)を直す。**R-03**: `docs/issues/092`(docker-proxy を「停止しました」と表示するが実装は削除している)を同じ降下で直す(同日の回答。決定シート 論点3) |
| やらないこと(このタスクの範囲外) | **VM モードのゲスト内で作られた資源**(ホストの Docker に現れない。`D0-env-05` 項2 が対象外と明記)。**イメージの削除**(同項が「削除しない」と決めている)。**compose 一意化名のハッシュ衝突の検出**(`docs/pendings.md` P-005。解消条件は未到達 — 下の調査メモ 7)。**コンテナ名そのものの一意化**(`docs/issues/028`)。**`logout` の片付け範囲を広げること**(`D0-env-05` 項2 が明示的に除外) |

## 影響範囲(closure)

<!-- 03 の relations と tests は、決定シートの回答で R-01-b を採らない場合に一部が
     「変更なし」へ落ちる。確定は /task-doc(フェーズ2)で行う。 -->

| 層 | SSOT のパス | 変更指示のパス | 変更の種類 |
|---|---|---|---|
| 00 | docs/00-requests/request.md | new-features/00-requests/request.md | replace |
| 00 | docs/00-requests/acceptances.md | new-features/00-requests/acceptances.md | replace |
| 00 | docs/00-requests/terminology.md | new-features/00-requests/terminology.md | replace |
| 00 | docs/00-requests/decisions/env.md | new-features/00-requests/decisions/env.md | replace |
| 00 | docs/00-requests/decisions/sec.md | new-features/00-requests/decisions/sec.md | replace |
| 00 | docs/00-requests/decisions/auth.md | - | 変更なし(理由: 認証の保管・共有・破棄の方式は動かさない) |
| 00 | docs/00-requests/decisions/dist.md | - | 変更なし(理由: イメージの配布と同梱物に触れない) |
| 00 | docs/00-requests/decisions/scope.md | - | 変更なし(理由: 記述粒度と委任の範囲は動かさない) |
| 01 | docs/01-requirements/functional.md | new-features/01-requirements/functional.md | replace |
| 01 | docs/01-requirements/usecases.md | new-features/01-requirements/usecases.md | replace |
| 01 | docs/01-requirements/decisions/split.md | new-features/01-requirements/decisions/split.md | replace |
| 01 | docs/01-requirements/non-functional.md | - | 変更なし(理由: 性能・可用性・拡張性の目標値と測定方法は動かない。`NFR-sec-01` の4項目〈生ソケット・秘密鍵・焼き込み・confinement〉にも触れない) |
| 01 | docs/01-requirements/system.md | - | 変更なし(理由: 実行環境・依存・開発言語の技術前提は変わらない) |
| 02 | docs/02-design/architecture.md | new-features/02-design/architecture.md | replace |
| 02 | docs/02-design/system.md | new-features/02-design/system.md | replace |
| 02 | docs/02-design/relations.md | new-features/02-design/relations.md | replace |
| 02 | docs/02-design/logging.md | new-features/02-design/logging.md | replace |
| 02 | docs/02-design/contracts/cli-container.md | new-features/02-design/contracts/cli-container.md | replace |
| 02 | docs/02-design/contracts/docker-api.md | new-features/02-design/contracts/docker-api.md | replace |
| 02 | docs/02-design/environments.md | - | 変更なし(理由: lint・テスト・ビルド・整合検査のコマンド文字列は変わらない) |
| 02 | docs/02-design/contracts/entrypoint-firewall.md | - | 変更なし(理由: entrypoint とファイアウォールの取り決めに触れない) |
| 03 | docs/03-impl/relations/MODULE-cli-stop.md | new-features/03-impl/relations/MODULE-cli-stop.md | replace |
| 03 | docs/03-impl/relations/MODULE-cli-reset.md | new-features/03-impl/relations/MODULE-cli-reset.md | replace |
| 03 | docs/03-impl/relations/MODULE-cli-start.md | new-features/03-impl/relations/MODULE-cli-start.md | replace |
| 03 | docs/03-impl/relations/MODULE-cli-common-spawned-resources.md | new-features/03-impl/relations/MODULE-cli-common-spawned-resources.md | replace |
| 03 | docs/03-impl/relations/MODULE-cli-common-write-project-ssh-keys.md | new-features/03-impl/relations/MODULE-cli-common-write-project-ssh-keys.md | replace |
| 03 | docs/03-impl/relations/MODULE-cli-common-select-ssh-keys.md | - | 変更なし(理由: 呼び出す先の振る舞いが「全面上書き」から「節の差し替え」へ変わるだけで、この機能が渡すものも受け取るものも変わらない) |
| 03 | docs/03-impl/relations/MODULE-cli-ssh-keys-reset.md | new-features/03-impl/relations/MODULE-cli-ssh-keys-reset.md | replace |
| 03 | docs/03-impl/relations/MODULE-docker-proxy-serve.md | new-features/03-impl/relations/MODULE-docker-proxy-serve.md | replace |
| 03 | docs/03-impl/contracts/cli-container.md | - | 変更なし(理由: 行番号を含む実装の鏡であり、`/task-close` がコードから再生成して突き合わせる。実装前に書くと必ず上書きされる — `.claude/directions/03-impl.md`) |
| 03 | docs/03-impl/contracts/docker-api.md | - | 変更なし(理由: 同上) |
| 03 | docs/03-impl/features.md | - | 変更なし(理由: 機能を1本も増減させないため。プロジェクト環境ファイルの読み取りは `MOD-cli-start` の内部に閉じ、共有基盤の機能へ上げない — `DSN-env-05` / `PLAN-cli-start`) |
| 03 | docs/03-impl/tests/cli-stop.md | new-features/03-impl/tests/cli-stop.md | replace |
| 03 | docs/03-impl/tests/cli-start.md | new-features/03-impl/tests/cli-start.md | replace |
| 03 | docs/03-impl/tests/cli-common.md | - | 変更なし(理由: 条項が1つも増減しない。`docs/issues/002` の修正は既存条項 `FR-env-04` の振る舞いを変えない) |
| 03 | docs/03-impl/tests/cli-reset.md | new-features/03-impl/tests/cli-reset.md | replace |
| 03 | docs/03-impl/tests/cli-ssh-keys.md | - | 変更なし(理由: 同上) |
| 03 | docs/03-impl/tests/docker-proxy.md | new-features/03-impl/tests/docker-proxy.md | replace |
| 03 | docs/03-impl/tests/e2e.md | new-features/03-impl/tests/e2e.md | replace |
| 03 | docs/03-impl/index.md | -(§3-4 で版のみ更新) | 版のみ更新 |

**変更の起点層**: **00**。R-01-b は `D0-env-05` 項2 が「削除しない: 名前付きボリューム」と
決めた範囲そのものを動かす判断であり、用語集「セッション由来の資源」の定義(含まない例に
名前付きボリュームを名指ししている)も同時に動く。R-02 は `request.md`「やること」に無い
新しい能力(プロジェクト設定でコンテナへ環境変数を渡す)であり、`.claude-dev.yaml` の
所有と射程を決めているのも 00(`D0-sec-08` / `DSN-arch-02` の上流)である。
R-01-a(存在しないネットワークを「削除できませんでした」と表示する)だけは起点が 03 だが、
CLAUDE.md §4 の「起点をまたぐなら上位に合わせて同じ降下で直す」に従い本タスクへ含める。

**既存タスクとの関係**: なし(`docs/tasks/` は空だった)。

## 読む範囲(読了記録)

- 全文読了: 2026-08-18
  - docs/00-requests/acceptances.md@1.5.0
  - docs/00-requests/decisions/auth.md@1.3.1
  - docs/00-requests/decisions/dist.md@1.3.0
  - docs/00-requests/decisions/env.md@1.5.1
  - docs/00-requests/decisions/scope.md@1.2.1
  - docs/00-requests/decisions/sec.md@1.3.1
  - docs/00-requests/request.md@1.5.0
  - docs/00-requests/terminology.md@1.6.0
  - docs/01-requirements/decisions/split.md@1.4.0
  - docs/01-requirements/functional.md@1.17.0
  - docs/01-requirements/non-functional.md@1.8.0
  - docs/01-requirements/system.md@1.3.0
  - docs/01-requirements/usecases.md@1.6.0
  - docs/02-design/architecture.md@1.6.0
  - docs/02-design/contracts/cli-container.md@1.11.0
  - docs/02-design/contracts/docker-api.md@1.1.0
  - docs/02-design/contracts/entrypoint-firewall.md@1.0.1
  - docs/02-design/environments.md@1.5.0
  - docs/02-design/logging.md@1.8.0
  - docs/02-design/relations.md@1.10.1
  - docs/02-design/system.md@2.13.0

## 決定シート(回答済み)

> 回答済み: sheet.md(転記済み)。**回答待ちは0件。**
> (2026-08-19 の `/doc-check`(タスクモード・増分再実行)が確認。
>  前回残っていた論点4 の未降下は解消済みで、6件すべてが 00〜03 に降りている)

<!-- 2026-08-19 に人間がチャットで回答した。シートの「★あなたの記入」欄は空のままである
     (AI は書き込まない)。以下は発言の逐語引用+日付による転記であり、これが SH4 の合格証拠。 -->

| # | 論点 | 回答 | 反映先 |
|---|---|---|---|
| 概念1 | 「セッションが作った資源」にボリュームを含めるか | チャット回答(2026-08-19)「それ以外は推奨で良い」 — 推奨を承認(含める = そのセッションの中から作られた名前付きボリュームと匿名ボリューム / 含まない = ホスト側で直接作ったもの・外部ボリューム・本システムの共有ボリューム) | `docs/00-requests/terminology.md` の用語「セッション由来の資源」 / `docs/00-requests/decisions/env.md` の `D0-env-05` 項2 |
| 概念2 | プロジェクト設定で渡せる環境変数のうち、本システムが使う名前を上書きさせるか | チャット回答(2026-08-19)「それ以外は推奨で良い」 — 推奨を承認(`CLAUDE_DEV_` 接頭辞・`DOCKER_HOST`・`COMPOSE_PROJECT_NAME`・`SSH_AUTH_SOCK`・`NODE_OPTIONS`・`container` を予約とし、書かれていたらその1件だけ採用せず名前を挙げて警告し、起動は続ける) | `docs/02-design/contracts/cli-container.md`「渡す環境変数」 / `docs/01-requirements/functional.md`(新設 `FR-env-14`) |
| 論点1 | ボリュームを既定で消すか、明示指定のときだけ消すか | チャット回答(2026-08-19)「それ以外は推奨で良い」 — 推奨を承認(案 B = 既定では消さず `claude-dev stop --volumes` を明示したときだけ消す。既定では残っているボリュームの名前を表示する) | `docs/00-requests/decisions/env.md` の `D0-env-05` 項2 / `docs/01-requirements/functional.md` の `FR-env-01` 受入基準 |
| 論点2 | `.claude-dev.yaml` に秘密の値が書かれうることの扱い | **チャット回答(2026-08-19)「論点2だけ修正して。.claude-dev.yamlではenvファイルを指定するようにして、秘密情報はenvファイルに書くことにする（envはgitignore）。それ以外は推奨で良い」 — AI推奨(案 A)を採らず、人間の指定した形にする**: `.claude-dev.yaml` には**env ファイルのパスを書く**。環境変数の実体は env ファイルに書き、その env ファイルは Git の追跡から外す | `docs/00-requests/decisions/sec.md`(新設の決定) / `docs/02-design/contracts/cli-container.md`「渡す環境変数」と設定ファイルの書式 / `docs/01-requirements/functional.md`(新設 `FR-env-14`) |
| 論点4 | 名前を付けずに作られたマウント(匿名ボリューム)も片付けの対象に入れるか | **チャット回答(2026-08-19)「Bで」 — 案 B を採用**(匿名ボリュームも対象に含める。手段は、削除の明示があるときにコンテナの削除へ名前無しのボリュームも一緒に消す指定を添える) | `docs/00-requests/terminology.md` の用語「セッション由来の資源」 / `docs/00-requests/decisions/env.md` の `D0-env-05` 項2・`D0-env-08` 項8 / `docs/01-requirements/functional.md` の `FR-env-01-28`・`-29` / `docs/02-design/contracts/cli-container.md` の規則D と `DSN-env-04` / `docs/02-design/contracts/docker-api.md` / `docs/03-impl/relations/MODULE-cli-stop.md`・`MODULE-cli-reset.md`・`MODULE-docker-proxy-serve.md` / `docs/03-impl/tests/e2e.md` |
| 論点3 | `docs/issues/092`(「停止しました」と出すが実際は削除)を一緒に直すか | チャット回答(2026-08-19)「それ以外は推奨で良い」 — 推奨を承認(案 A = 本タスクで一緒に直す。2026-08-07 の裁定のうち「独立したタスクにする」の部分だけを変える) | `docs/00-requests/decisions/env.md` の `D0-env-05` 項2・`D0-env-08` 項2 / `docs/01-requirements/functional.md` の `FR-env-01-6`・`FR-env-01-9` / `docs/02-design/architecture.md`(新設 `DSN-*`) / `docs/03-impl/relations/MODULE-cli-stop.md` |

## 未決点

(memo-1.md に移動。**人間判断へ回した未決点は0件**で、7件すべて委任決定またはドキュメント記載で帰着している)

## 調査メモ

(memo-1.md に移動)

## 質問キュー(未提示)

| # | 論点 | 何が止まるか | 推奨する回答(暫定) |
|---|---|---|---|
| - | なし(見つけたものはすべて sheet.md に載せた) | - | - |

## タスクリスト

<!-- /implement が最終化する。依存順に並べた草案。 -->

- [x] 1. docker-proxy: ボリューム作成要求への所有者ラベルの注入(`volumeCreateRe` と経路の追加、既存の `injectOwnerLabels` を再利用)+ 単体テスト4本 _要件:_ FR-env-07-11 _Boundary:_ `docker-proxy/` _Depends:_ -
- [x] 2. 共有基盤: `spawned_resources` に種別 `volume` を足す _要件:_ FR-env-01-28 _Boundary:_ `claude-dev` / `claude-dev-mac` _Depends:_ -
- [x] 3. `stop`: 存在しなかった資源を失敗に数えない(compose 既定ネットワークの実在確認) _要件:_ FR-env-01-34 _Boundary:_ 同上 _Depends:_ -
- [x] 4. `stop`: `--volumes` の受理と、ボリュームの列挙・削除・残ったときの表示 _要件:_ FR-env-01-28〜31 _Boundary:_ 同上 _Depends:_ 1, 2
- [x] 5. `reset`: `--volumes` の受理と、確認の列挙・削除・残ったときの表示 _要件:_ FR-env-01-32・33 _Boundary:_ 同上 _Depends:_ 1, 2
- [x] 6. `stop` / `reset` / 00・01 の文言: docker-proxy を「停止しました」から削除したことが分かる言葉へ _要件:_ FR-env-01-6 _Boundary:_ 同上 _Depends:_ - (P)
- [x] 7. 設定ファイル: `write_project_ssh_keys` を節の差し替えへ、`ssh-keys reset` を節の除去へ(`docs/issues/002`) _要件:_ FR-env-04 _Boundary:_ 同上 _Depends:_ -
- [x] 8. `start`: `load_project_env_file`(読み取り・予約名・重複・封じ込め・`.gitignore` 追記)と `PROJECT_ENV_OPTS` の付与 _要件:_ FR-env-14 _Boundary:_ 同上 _Depends:_ 7
- [x] 9. macOS 版(`claude-dev-mac`)へ 2〜8 を同じ形で反映し、両 OS の差分が案内文だけであることを確認する _要件:_ FR-env-10-4 _Boundary:_ `claude-dev-mac` _Depends:_ 2, 3, 4, 5, 6, 7, 8

## Definition of Done

- [x] lint が通る: `cd docker-proxy && go vet ./...`
- [x] 単体・結合テストが通る: `cd docker-proxy && go test ./...`
- [x] 受入基準のテストが全て存在し通る(シェル実装は `未検証(テスト未実装)` が方針。`DSN-test-01` / `SR-32`)
- [x] 影響する E2E シナリオが通る: E2E-01 の新設部分手順(8-21 / 8-22 / 8-23)と E2E-03 のボリュームのラベル確認を隔離ハーネスで実機確認。**手順8 の全体と `reset` 側は専有ホストが要るため未実施**(P-006 と同じ制約。申し送り参照)
- [x] 探索的ブラウザQA: **適用外(UI 無し)** — 根拠 `docs/02-design/system.md`「UI設計」`DSN-ui-01`
- [x] `CG_OUT=$(python3 .claude/scripts/resolve-callgraph-out.py task-stop-cleanup-and-project-env) && python3 .claude/scripts/build-callgraphs.py --out "$CG_OUT"` で
  コールグラフを再生成し、`callgraph-check.py --to-be task-stop-cleanup-and-project-env` の重大度「高」が0
- [x] `check-relations.py` が合格
- [ ] `new-features/` の全変更指示を SSOT へ反映済み
- [ ] `/doc-check` が影響範囲を PASS
- [ ] `docs/histories/` に記録(R-01 / R-02 を `R-01` `R-02` の節に分ける)
- [x] 見つけた範囲外の問題を記録済み: `docs/issues/102`(colabtmux が bwrap の非ゼロを理由に codex を起こさない。人間の指摘)/ `docs/pendings.md` の残務2行(`/doc-check` が記録)

## 進捗メモ

- 2026-08-19 `/doc-check`(**ssot task-stop-cleanup-and-project-env**。フェーズ4 の反映後・**同日3回目の増分再実行**)
  判定: **PASS(ブロッキング0件)。ただし製品側に severity 中の実装欠陥2件を起票した**。
  レビュー: **あり(Codex `gpt-5.6-sol` / reasoning high)**。実行形態: 呼び出し元スキルから
  起動した新しい文脈のサブエージェント。**反復 1/2**(2周目は不要)。
  記録は `docs/histories/2026-08-19-doc-check-ssot-stop-cleanup-and-project-env-third-recheck.md`。
  **2回目の記録は `…-recheck-after-code-fix.md`**(この進捗メモには入っていない)。
  - **増分の根拠**: 直前の検証以降に動いたのはコミット `faa4b3d` だけで、その中身は
    `claude-dev` / `claude-dev-mac` の `.gitignore` まわり(`claude-dev:1549` の1ハンク。
    8行 → 17行 = **以降を一律 +9**)と `MODULE-cli-start.md`・`03-impl/index.md` である。
    A〜E をこの差分と下流(03-impl の closure 文書)に絞った。**00・01・02 は再検証していない**
    (版と `verified.version` が一致したまま有効。原則6)。
  - **新規 issue: `docs/issues/106`(重大度 中 / 起点層 03)** — `load_project_env_file` が
    `[ ! -f ]` しか見ず読み取りが握られていないので、**読めない env ファイルで `start` が止まる**
    (`claude-dev:165`・`:203` / `claude-dev-mac:164`・`:202`)。`NFR-avail-03` 違反。
  - **新規 issue: `docs/issues/107`(重大度 中 / 起点層 03)** — `_overlay=$(jq … 2>/dev/null)` が
    終了ステータスを握らないので、**壊れた `~/.claude/settings.json` で `start` が止まる**
    (`claude-dev:1521` / `claude-dev-mac:1596`)。`NFR-avail-03` は「ホスト設定の取り込み」を名指し。
    **どちらも同型の最小スクリプトで実測。`/task-close` へ進む前にコードを直すこと**
    (`106` は `[ ! -r ]` を足すか `done < "$norm"` を握る / `107` は `|| _overlay=""` を添える。
    どちらも Linux 版・macOS 版の両方。`D0-scope-03`)。
  - **自動修正**: コード引用 **40 トークン / 15 箇所**の取り直し(PATCH)+ `MODULE-cli-start` の
    **偽になっていた4箇所**の書き直しと副作用の順序表の整理(MINOR)。
    `03-impl/index.md` は **1.28.0 → 1.29.0**(起票済み欠陥 4件 → 6件)。
    **`MODULE-cli-start` の `:1670` は2回目が取り直さずに残していたもの**である。
  - **記録した残務1行**: `MODULE-cli-start` の程度語2箇所(「数分」「即座に」)。
  - **恒久受容として落とした残務: 0行**(`doc-health.py --as-of=2026-08-19 --sweep`。残務 38 行 / 上限 50)。
  - **鮮度(A2)**: `P-005` は**未発火**。**`P-006` の3つ目の発火条件は2回目の記録が発火と判定したまま、
    人間の裁定を得ていない**(専有ホストが無く E2E-01 手順8-15 / 8-16 / 手順10・12 を実行できない)。
    新しい issue にも残務にもしない(`issues-pendings.md` §8)。
  - **機械検査**: `check-changeset.py --ssot` = CS20 のみ違反9件(既存・2026-08-12 の残務が持つ)/
    `check-relations.py` 合格 / `check-contracts.py` 合格 / `build-callgraphs.py --check` 最新 /
    `cluster-features.py --check` 最新 / `callgraph-check.py` 重大度「高」**0**(中3・低9・参考12 は既存)/
    `check-lane.py` 合格(lane=critical)/ `check-sheet.py` は SH8 のみ(本タスク自身の反映で
    closure の版が上がったため。フェーズ2 の入場ゲートは通過済み)。
  - **決定シートへの追記: なし**(問う基準を満たす論点は無い。`106` / `107` は「直す」以外の選択が無い)。
  - **最弱点**: 2回目の再実行が `MODULE-cli-start` を書き直しながら同じ文書の `:1670` を取り直して
    いなかったこと。**取り直しの単位は「変わった文書」ではなく「ずれた区間より下の全引用」である。**

- 2026-08-19 `/doc-check`(**ssot task-stop-cleanup-and-project-env**。フェーズ4 の反映後)
  判定: **PASS(ブロッキング0件)。ただし製品側に severity 中の実装欠陥2件を起票した**。
  レビュー: **あり(Codex `gpt-5.6-sol` / reasoning high)**。実行形態: 呼び出し元スキルから
  起動した新しい文脈のサブエージェント。**反復 1/2**(2周目は不要)。
  **検証済み記録を 20 文書へ発行した**(`close-task.py` 条件 (b) は全件 OK になった)。
  - **新規 issue: `docs/issues/103`(重大度 中 / 起点層 03)** — `reset)` 分岐が `--volumes` を
    解析していない(`claude-dev:2281`-`:2283` / `claude-dev-mac:2323`-`:2325`)。解析ブロックは
    直前の `logout)` 分岐(`claude-dev:1110`-`:1118`)に置かれており、`case` は1分岐しか走らないので
    **`claude-dev reset --volumes` は名前付きボリュームを1件も削除しない**。`FR-env-01-32` が未実装。
    `MODULE-cli-reset` の手順1・引数表・「既知の制限」に事実を書いて 03 を実装の鏡へ戻した。
    **`/task-close` へ進む前にコードを直すこと**(`reset)` の引数解析を `logout)` と同じ形にし、
    `logout)` からは取り除く。`logout` の片付け範囲を広げないことは `D0-env-05` 項2 が定める)。
  - **新規 issue: `docs/issues/104`(重大度 中 / 起点層 03)** — `.gitignore` への追記
    (`claude-dev:1555` / `claude-dev-mac:1630`)が `set -e` の下の単純コマンドなので、
    書き込めない `.gitignore` では `start` がそこで終了し、`FR-env-14-4` の
    「外せなかったことを表示して起動を続ける」に入らない。`MODULE-cli-start` へ事実を書いた。
  - **自動修正 45 件**。区分: **MINOR 5 文書 / PATCH 5 文書**(版を持たない relations 6本を含む)。
    内訳は `docs/histories/2026-08-19-doc-check-ssot-stop-cleanup-and-project-env-recertification.md`。
    主なもの: `FR-env-01-25` と `-33` の正面衝突(用語拡大の但し書き落ち)/ 実装で腐った
    コード引用 **28 箇所**の取り直し / 02 の `SCR-01` に `--volumes` が無かったこと /
    予約名の照合規則が 02 に無く 03 が発明していたこと / `03-impl/index.md` の起票済み欠陥が
    「4件」と言いながら 002 を含む5件を列挙していたこと / `tests/cli-stop.md`・`cli-start.md` の
    連番の二重化 / `tests/docker-proxy.md` のテスト 39件→45件。
  - **記録した残務3行**: `FR-env-07-11`・`-12` が UC に無い / `system.md` の主担当が複数モジュールの
    行が8つある / `--volumes` が組み込みヘルプに出ない。
  - **恒久受容として落とした残務1行**(`doc-health.py --sweep`。上の履歴へ追記済み):
    2026-08-10 の `docs/03-impl/tests/*.md` の状態列の語彙(パスが実在しないため)。
  - **鮮度(A2)**: `部分(P-005)`(`FR-env-01-19` / `FR-env-07-5`)は**未発火**、`P-006` も**未発火**。
    `docs/issues/002` と `092` は本タスクの実装で解消済み(**削除は `/task-close` の裁定**)。
    残務「既に版管理の追跡下にある env ファイルを検出できない」は実装で解消済み(同上)。
  - **機械検査**: `check-changeset.py --ssot` = CS20 のみ違反9件(既存・残務が持つ)/
    `check-relations.py` 合格 / `check-contracts.py` 合格 / `build-callgraphs.py --check` 最新 /
    `cluster-features.py --check` 最新 / `callgraph-check.py` 重大度「高」**0**(指摘 24 件は既存)/
    `check-lane.py` 合格(lane=critical)/ `close-task.py --check` は (b) 全件 OK、残る不合格は
    (c) DoD 3件・(g) 履歴・(h) 残務の裁定 12 件で、いずれも `/task-close` の仕事。
  - **`check-sheet.py` の SH8(読了記録の版ずれ)は想定内**: 本タスク自身の反映で closure の版が
    上がったために出るもので、フェーズ2 の入場ゲートは既に通過済みである。
  - **決定シートへの追記: なし**(問う基準を満たす論点は無い。issue 103 は「直す」以外の選択が無い)。
  - **最弱点**: 実装前に書いた `path:line` が実装の瞬間に全部腐るのに、フェーズ3 も `/task-close` も
    取り直していなかったこと。28 箇所のうち1つでも人が信じれば誤った場所を読む。

- 2026-08-19 **フェーズ3(実装)完了**。`git rev-parse HEAD` = `ecbb2d33cb87b54fa5fd416e98e51da6d822f74d`
  (**コミットはしていない** — 変更は作業ツリー上にある。ホストの規約でコミットは人間の指示があるときだけ行う)。
  DoD の検証結果:

  | DoD 項目 | 実行したこと | 最後の出力行(逐語) | 判定 |
  |---|---|---|---|
  | lint | `cd docker-proxy && go vet ./...` | `(出力なし)` | OK(出力なし = 指摘なし) |
  | 単体・結合テスト | `cd docker-proxy && go test ./...` | `ok  	github.com/quvox/claude-dev-env/docker-proxy	(cached)` | OK |
  | 受入基準のテスト | `FR-env-07-11`・`-12` に単体テスト4本を追加(状態 `実装済み`)。`FR-env-01-28`〜`-34` と `FR-env-14` はシェル実装のため `未検証(テスト未実装)` のまま(`DSN-test-01` / `SR-32`) | — | OK(方針どおり) |
  | E2E | **E2E-01 の新設部分手順(8-21 / 8-22 / 8-23)と E2E-03 のボリュームのラベル確認を、隔離ハーネス(ラベルつき疑似セッション `vol-a` / `envrun`)で実機の Docker に対して流した。** `stop`(`--volumes` 無し=残る / 有り=名前付きも匿名も消える)/ 存在しない compose 既定ネットワークを「削除できなかった」と出さないこと / 環境変数が渡ること・値が漏れないこと・予約名が差し替わらないこと・追跡から外れること・別プロジェクトへ漏れないことを確認した。**E2E-01 手順8 の全体と `reset` 側(手順8-15-1・8-15-2)は未実施** — 他のセッション(`ct_matchsupport`)が稼働中で専有ホストが要るため(`docs/pendings.md` P-006 と同じ制約) | — | 部分的に実施(未実施分は下の申し送り) |
  | 探索的ブラウザQA | **適用外(UI 無し)** — 根拠: `docs/02-design/system.md`「UI設計」の `DSN-ui-01`「UI はホスト CLI に限り、Web GUI を持たない」。noVNC は利用者が開発中の Web アプリを見る窓であって本システムのアプリ UI ではない | — | 適用外 |
  | コールグラフ再生成 + `callgraph-check.py --to-be` | `resolve-callgraph-out.py` → `build-callgraphs.py --out` → `callgraph-check.py --to-be` | 重大度「高」= **0 件** | OK |
  | `check-relations.py` | 同左 | `合格: 対称性・参照実在・impl パス・必須項目・機能表との 1:1すべて問題なし。` | OK |
  | `check-changeset.py` | 変更指示 26 件 | `合格: 不変条件の違反なし(ただし未検査: CS5, CS6, CS7, CS10, CS21 — **未検査は合格ではない**)` | OK |
  | SSOT への反映 / `/doc-check` PASS / histories | — | — | `/task-close` で実施 |

- 2026-08-19 フェーズ3 で行使した委任(すべて変更指示に開示行あり):
  **[DS-05]** 節を取り除く処理を私的ヘルパ1つに切り出し機能へ昇格させない(`MODULE-cli-common-write-project-ssh-keys`)/
  **[DS-05]** 読み取りを3つの私的ヘルパへ分ける(`MODULE-cli-start`)/
  **[DS-02]** 追跡から外せたかを `git check-ignore -q` で確かめる(同)/
  **[DS-05]** 注入の呼び出し口を `labelCreateRequest(r, logger, kind)` の1本にする(`MODULE-docker-proxy-serve`)/
  **[DS-01]** ボリューム経路の試験をネットワーク経路と同じ4本の型に揃える・`kind` 引数そのものは試験しない(`tests/docker-proxy.md`)。


- 2026-08-19 `/doc-check`(task。**増分再実行 = 論点4 の回答が降りた後**)判定: **PASS**。
  レビュー: **あり(Codex `gpt-5.6-sol` / reasoning high)**。実行形態: 呼び出し元スキルから
  起動した新しい文脈のサブエージェント。**反復 1/2**(2周目は不要)。
  **変更指示ハッシュ**: 入場 `80b47961e0484f6c` → 修正後 `2f02f7457ef0be4c`(前回は `3508e06e3408d52e`)。
  **closure の版は前回から1本も動いていない**(`request@1.5.0` / `acceptances@1.5.0` /
  `terminology@1.6.0` / `env@1.5.1` / `sec@1.3.1` / `functional@1.17.0` / `usecases@1.6.0` /
  `split@1.4.0` / `architecture@1.6.0` / `system@2.13.0` / `relations@1.10.1` / `logging@1.8.0` /
  `contracts/cli-container@1.11.0` / `contracts/docker-api@1.1.0` / `03-impl/index@1.25.1` /
  `tests/cli-stop@1.7.0` / `tests/cli-start@1.4.0` / `tests/cli-reset@1.4.1` / `tests/e2e@1.10.0`)。
  **前回のブロッキング1件(論点4 が 00〜03 のどこにも降りていない)は解消**: 00(用語集 /
  `D0-env-05` 項2 / `D0-env-08` 項8)・01(`FR-env-01-28`・`-29`)・02(`CTR-cli-container` 規則D /
  `CTR-docker-api`)・03(`MODULE-cli-stop` 手順8-1 / `MODULE-cli-reset` 手順6 /
  `MODULE-docker-proxy-serve` 既知の制限 / `tests/e2e` 手順8-21-5)に降りていることを確認した。
  **自動修正 9 件**。修正の区分: **MINOR 8 件 / PATCH 1 件**。
  - MINOR(意味変更): `MODULE-cli-stop` の契機・引数表へ `--volumes`(「第2引数以降は黙って無視する」が
    手順8 と `[DS-05]` 開示行と矛盾していた)/ `MODULE-cli-reset` の手順1・契機・引数表へ `--volumes`
    (「`--yes` のみ。それ以外は無視する」と同じ矛盾)/ `tests/e2e` 手順8-21-5 を**2回の実行で
    それぞれ匿名ボリュームを作り直す**形へ(1回目で紐づくコンテナが消えると、後から `--volumes` を
    付けても匿名ボリュームは消せない — 手順として実現不能だった)/ `D0-env-05` 項2 の残存表示の
    対象を名前付きボリュームに限る(01 の `FR-env-01-29` が匿名を表示対象外にしているのに 00 は
    「ボリューム(名前の有無を問わない)が残っていることを示す」と書いていた)/ `D0-env-08` の
    用語再掲を「ボリューム。名前の有無を問わない」へ(用語集と食い違っていた)/ 用語集
    「セッション由来の資源」の定義文へ匿名ボリュームの経路(作成要求そのものが無く、
    docker-proxy を経由したコンテナ作成にともなって Docker が直接作る)/ `02-design/system.md` の
    `MOD-cli-stop`・`MOD-cli-reset` の責務へ「それらのコンテナが抱えていた名前無しのボリューム」/
    `MODULE-cli-stop` 手順8 の列挙失敗の扱いを 8-1・8-2 の2種別から 8-3 を含む3種別へ
  - PATCH(意味保存): `MODULE-cli-reset` 手順6 の削除コマンドの列挙にボリュームと `-v` を反映
  - **コード引用の再確認**(原則2): 前回取り直した 13 箇所を実コードに当て直し、
    `claude-dev:1717`/`:1722`/`:1727`/`:1748`/`:1758`/`:1801`/`:2095`/`:2100`/`:2163`/`:2169`/
    `:2173`/`:2174`/`:2192`/`:1501`・`claude-dev-mac:535`/`:1552` がすべて一致することを確認した
    (コードはこのタスク中1バイトも変わっていない)。
  - **バイト数**: 入場 582,193 → 修正後 584,268(**+2,075**)。増分の理由は (a) 引数表2本への
    `--volumes` の行、(b) e2e 手順8-21-5 を実現可能な手順へ書き直したこと、(c) 00 の2箇所の但し書き。
  - **relations のバイト上限**: 前回の裁定(7本すべて実装済みモジュールの全文 `replace` =
    `change-set.md` §1 例外2 により不適用)をそのまま引き継ぐ。今回触った `MODULE-cli-stop` と
    `MODULE-cli-reset` も同じ区分である。
  - **機械検査**: `check-changeset.py`(タスク)= 違反0(未検査 CS5/6/7/10/21)/
    `compose-changeset.py --preview` = **exit 0**(25 件すべて反映可能)/ `check-relations.py` 合格 /
    `check-contracts.py` 合格 / `callgraph-check.py` 重大度「高」**0**(指摘 24 件は中3・低8・参考12・
    その他でいずれも既存)/ `check-sheet.py` 合格 / `check-lane.py` 合格(lane=critical / 必要下限=critical)/
    `build-callgraphs.py --check`(SSOT)最新 / `cluster-features.py --check`(SSOT)最新。
    タスク側 staged callgraphs は未生成(実装前。DoD がフェーズ3 で生成すると定めている)。
  - **記録した issue / 残務: 0 件**。独立レビューの低指摘(`e2e.md` の「すぐに」)は既存の残務
    (2026-08-11)と同一キーなので1バイトも書いていない。
  - **鮮度(A2)**: closure が開く `部分(P-005)`(`FR-env-01-19` / `FR-env-07-5`)の解消条件
    「数百規模 / 衝突の観測」は**未発火**、申し送りの `P-006`(専有ホスト / macOS 機)も**未発火**。
    どちらも新しい issue にも残務にもしない(`issues-pendings.md` §8)。
  - **決定シートへの追記: なし**(回答が生んだ差分から新しい論点は生まれていない)。
  - **最弱点**: `--volumes` を軸にした変更でありながら、03 の公開インターフェース(契機・引数表)が
    そのフラグを受理しない記述のまま2本とも残っていたこと。今回直したが、
    **手順を先に書いてインターフェース表を後から直す**書き方は次も同じ穴を作りうる。

- 2026-08-19 **論点4 に回答を得て降ろした**。チャット回答「Bで」(逐語引用は決定シート(回答済み))。
  匿名ボリュームを片付けの射程へ入れ、**印に頼らず紐づくコンテナの削除へ `-v` を添える**形で
  00(用語集 / `D0-env-05` 項2 / `D0-env-08` 項8)・01(`FR-env-01-28`・`-29`)・
  02(`CTR-cli-container` 規則D と `DSN-env-04` / `CTR-docker-api`)・
  03(`MODULE-cli-stop` 手順8-1・`MODULE-cli-reset` 手順6・`MODULE-docker-proxy-serve` 既知の制限・
  `tests/e2e` 手順8-21-5)へ降ろした。**修正の区分: MINOR**(意味変更のため、前回の判定は無効)。
  行使した委任: **[DS-04]** 匿名ボリュームを表示の対象外にする(`FR-env-01-29`)/
  **[DS-05]** 匿名ボリュームを `docker rm -f -v` で消し、別の列挙を作らない(`MODULE-cli-stop`)。
  `check-changeset.py` 合格 / `compose-changeset.py --preview` exit 0(25 件すべて反映可能)。
- 2026-08-19 `/doc-check`(task) 判定: **不合格(残存 1 件)**。レビュー: **あり(Codex `gpt-5.6-sol` / reasoning high)**。
  実行形態: 呼び出し元スキルから起動した新しい文脈のサブエージェント。
  **変更指示ハッシュ**(`find … | sort | xargs sha256sum | sha256sum`): `3508e06e3408d52e`。
  **closure の版**(フェーズ1 の読了記録から動いていない): `request@1.5.0` / `acceptances@1.5.0` /
  `terminology@1.6.0` / `env@1.5.1` / `sec@1.3.1` / `functional@1.17.0` / `usecases@1.6.0` /
  `split@1.4.0` / `architecture@1.6.0` / `system@2.13.0` / `relations@1.10.1` / `logging@1.8.0` /
  `contracts/cli-container@1.11.0` / `contracts/docker-api@1.1.0` / `03-impl/index@1.25.1` /
  `tests/cli-stop@1.7.0` / `tests/cli-start@1.4.0` / `tests/cli-reset@1.4.1` / `tests/e2e@1.10.0`。
  **残るブロッキングは1件**: 決定シート「論点4」(匿名ボリュームが 00〜03 のどこにも降りていない)。
  **自動修正 21 件**(内訳は下記)。修正の区分: **MINOR 10 件 / PATCH 11 件**。
  - MINOR(意味変更): `MODULE-docker-proxy-serve` の「ボリューム作成要求には注入しない」を削除 /
    同 永続化欄へボリューム / `MODULE-cli-stop` の目的の例外からボリュームを外し既定の扱いを明記 /
    同 順序欄へボリューム / `MODULE-cli-reset` の「削除しない」を「明示したときだけ削除する」へ /
    同 並行性の順序欄へボリューム / `MODULE-cli-common-spawned-resources` の `[DS-05]` 開示行を3種別へ /
    `02-design/relations.md` の `PLAN-cli-stop`・`PLAN-docker-proxy-serve` の一覧要約へボリューム /
    `logging.md` の所有者ラベル付与の種別へボリューム / `contracts/cli-container.md` の `env_file` の値へ
    「1つだけ・既定のファイル名は無い」(00 が 02 へ委ねた「ファイル名の既定・複数指定の可否」の受け手が無かった)
  - PATCH(意味保存): 変更指示の構造修正4本(`architecture` / `contracts/cli-container` /
    `contracts/docker-api` / `relations` / `system` — **新規の子見出しを親本文経由で足していたため
    `compose-changeset.py` が exit 1 で落ちていた**。該当の子見出しを指示本文の冒頭へ出し、
    `sections` + `anchors` へ別立てにした)/ `split.md` の条項数 26→33・範囲 20〜27→20〜34 /
    `logging.md` の新設4行に落ちていた「対応要件」列 / `MODULE-cli-stop` の「8-3 の列挙」→「8-4」 /
    `tests/e2e.md` の部分手順 21〜23 を手順7 の下から**手順8 の末尾へ移動**(参照側はすべて「手順8-21」)/
    コード引用の行番号 13 箇所(下記)
  - **コード引用の取り直し**(原則2。実コードから取り直した): `MODULE-cli-stop` `:1639`→`:1748` /
    `:1620`-`:1625`→`:1722`-`:1727` / `:1615`・`:1692`→`:1717`・`:1801` / `mac:517`→`mac:535`、
    `MODULE-cli-reset` `:2045`-`:2055`→`:2163`-`:2173` / `:2056`→`:2174` / `:2157`→`:2192` / `:2051`→`:2169`、
    `MODULE-cli-common-spawned-resources` `:1697`・`:1707`→`:1748`・`:1758` / `:2035`・`:2040`→`:2095`・`:2100`、
    `MODULE-cli-start` `:1399`・`mac:1432`→`:1501`・`mac:1552` / `:1198`-`:1216`→`:1305`-`:1318` /
    `mac:1236`・`:1237`・`:1245`-`:1250`→`mac:1356`・`:1357`・`:1365`-`:1370` / `mac:517`→`mac:535`。
  - **バイト数**: 入場 574,857 → 修正後 575,785(**+928**)。増分の理由は (a) 構造修正で節を移動した
    ぶんの空行、(b) `env_file` の値の行に既定と複数指定の可否を書いたこと、(c) 表の欠けた列の補い。
    削除で直した箇所(注入しないの1行)もある。
  - **relations のバイト上限の適用可否(次の反復で再導出しないための記録)**: `new-features/03-impl/relations/*.md`
    の 4,000 バイト上限は **7本すべてに適用しない** — いずれも**実装済みモジュールの全文 `replace`**
    (`change-set.md` §1 例外2)である。**何も変えない `replace` の床**(= SSOT の現在のバイト数)は
    `MODULE-cli-stop` 45,382 / `-start` 45,169 / `-reset` 40,215 / `-docker-proxy-serve` 24,987 /
    `-common-spawned-resources` 8,921 / `-ssh-keys-reset` 4,628 / `-common-write-project-ssh-keys` 3,429。
    最後の1本だけ床が 4,000 を下回るが、例外2 は「実装済みモジュールの全文 replace」に無条件で掛かる。
    `tests/strategy.md` はこの変更指示に無いので、後段の検査は対象なし。
  - **機械検査**: `check-changeset.py`(タスク)= 違反0(未検査 CS5/6/7/10/21)/
    `compose-changeset.py --preview` = **exit 0**(修正前は exit 1)/ `check-relations.py` 合格 /
    `check-contracts.py` 合格 / `callgraph-check.py` 重大度「高」0(中3・低8・参考12 はいずれも既存)/
    `check-sheet.py` 合格 / `build-callgraphs.py --check`(SSOT)最新 / `cluster-features.py --check`(SSOT)最新。
    タスク側 staged callgraphs は未生成(実装前なので当然。DoD がフェーズ3 で生成すると定めている)。
  - **記録した残務2件**(`docs/pendings.md`): 既に追跡下にある env ファイルを検出できない /
    実装前 relations の `tests:` が未実在のテストを挙げる。
  - **既存の残務へ差し戻したもの**(重複キーなので1バイトも書いていない): コード引用の行番号のずれ
    (2026-08-11)/ E2E-01 手順8-3 の「すぐに」(2026-08-11)/ 破壊的操作の条項が UC に無い(issue 080 残件)/
    用語の含む例・含まない例が空(issue 071 残件)/ テスト状態列の語彙2つ(2026-08-18・2026-08-10)/
    `id: images` の重複(2026-08-10)。
  - **最弱点**: 人間が承認した「匿名ボリュームも含める」が 00〜03 のどこにも降りていないこと。

- 2026-08-19 フェーズ2 で行使した委任(開示先はすべて変更指示の中):
  **[DS-02]** 存在しなかった資源の判定を削除コマンドの終了コードではなく実在確認で行う(`MODULE-cli-stop`)/
  **[DS-02]** env ファイルが無くても起動を止めない(`FR-env-14-6`)/
  **[DS-03]** 採用しなかった行の表示に値を出さない(`MODULE-cli-start`)/
  **[DS-04]** `reset` にも `--volumes` の明示を求める(`FR-env-01-32`)/
  **[DS-04]** 受理する範囲をプロジェクトディレクトリの中に限る(`FR-env-14-9`)/
  **[DS-04]** 同じ名前が2回書かれたら後勝ち(`FR-env-14-10`)/
  **[DS-04]** 値を展開しない・口を env ファイル1つに絞る・パスは設定ファイルからの相対(`DSN-env-05` ほか)/
  **[DS-04]** env ファイルの1行は最初の `=` で割り引用符を取り除かない(`MODULE-cli-start`)/
  **[DS-04]** 予約名の判定は大文字小文字を区別する(同)/
  **[DS-04]** `--volumes` が無いとき `reset` はボリュームを列挙しない(`MODULE-cli-reset`)/
  **[DS-05]** `--volumes` を名前の検証より前に取り除く(`MODULE-cli-stop`)/
  **[DS-05]** 環境ファイルの読み取りを `start` に畳み込み共有基盤へ上げない(`MODULE-cli-start`)/
  **[DS-05]** パスの封じ込めは字句的に行う(同)/
  **[DS-05]** 設定ファイルの節の判定に YAML 解析器を持ち込まない(`MODULE-cli-common-write-project-ssh-keys`)/
  **[DS-05]** ボリューム作成の判定を独立した正規表現で持つ(`MODULE-docker-proxy-serve`)/
  **[DS-05]** compose 既定ネットワークの削除失敗を既存の配列へ積む(`MODULE-cli-stop`。継続)/
  **[DS-01]** テストの分け方4件(`tests/cli-stop` / `cli-reset` / `cli-start` / `e2e` / `docker-proxy` 側は `MODULE-docker-proxy-serve` の開示行)
- 2026-08-19 フェーズ2: **01 完了**。`functional.md`(`FR-env-01` に条項 28〜34 を追加、
  `FR-env-01-6`・`-9` の docker-proxy の語を実態へ、`FR-env-07-11`・`-12` にボリューム作成要求、
  `FR-env-14` 新設、要求カバレッジに `RQ-env-07`)/ `usecases.md`(`UC-01` に代替 A5・例外 E6、
  `AC ⇄ UC` に `AC-08`)/ `decisions/split.md`(件数 23→24)の3本。
  `check-changeset.py` は CS13 が 34 件残る(02 カバレッジ表と 03 テスト表が未着手のため。想定内)。
  行使した委任: **[DS-04]** `FR-env-01-32`(`reset` にも `--volumes` の明示を求める)/
  **[DS-02]** `FR-env-14-6`(env ファイルが無くても起動を止めない)/
  **[DS-04]** `FR-env-14-9`(受理する範囲をプロジェクトディレクトリの中に限る)/
  **[DS-04]** `FR-env-14-10`(同じ名前が2回書かれたら後勝ち)。次は 02。
## 申し送り事項

- **フェーズ3 の実機確認は専有ホストで行えていない。** 他のセッション(`ct_matchsupport`)が
  稼働中だったため、**E2E-01 手順8 の全体**と **`reset` 側の新設部分手順(8-15-1・8-15-2)**は
  未実施である。代わりにラベルつきの疑似セッションを立てた隔離ハーネスで、`stop` 側の
  新設部分手順(8-21・8-22)と環境変数の受け渡し(8-23)を実機の Docker に対して流した。
  `docs/pendings.md` P-006 が同じ制約を既に記録しており、**その残務の射程に本タスクの
  `reset --volumes` が加わる**(`/task-close` で裁定する)。
- **`docs/pendings.md` の 2026-08-19 の残務「既に版管理の追跡下にある env ファイルを検出できない」は、
  実装で解消した。** `git check-ignore -q` で確かめ、外れていなければ手順(`git rm --cached`)を
  表示する形にしたので、静かな失敗ではなくなった。**`/task-close` でこの残務行に裁定を与えること。**
- **変更はコミットしていない。** ホストの規約でコミットは人間の指示があるときだけ行うため、
  作業ツリー上に置いてある(`claude-dev` / `claude-dev-mac` / `docker-proxy/main.go` /
  `docker-proxy/labels_test.go` / `.devcontainer` は未変更)。
- **`claude-dev-docker-proxy` イメージを再ビルドした**(ボリューム作成要求へのラベル注入を
  実機で確かめるため)。**利用者のホストの既存イメージは新しいものに置き換わっている。**

- **`docs/issues/092`**(docker-proxy を 00・01 は「停止」と書き、実装は `docker rm -f` する。
  利用者向け出力も「停止しました」)は、2026-08-07 に人間が「案 A で確定。**コードに触るので
  本 issue は独立したタスクにする**」と裁定している。本タスクの closure は `stop` の出力と
  `MODULE-cli-stop` を既に含むので**同じ降下で直せる**。含めるかどうかは sheet.md 論点3 で問う。
- 本タスクの実測は**専有していないホスト**で行った(`opsvpn-*` の compose スタックがホスト側で
  稼働中)。`docs/pendings.md` P-006 が「専有できるホストが無い」ことを理由に E2E-01 手順8 の
  一部を未実施のまま受容しており、本タスクのフェーズ3 でも同じ制約に当たる見込みである。
