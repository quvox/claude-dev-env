---
id: index
version: 1.8.0
updated: 2026-08-04
source:
  - docs/02-design/system.md
  - docs/02-design/relations.md
summary: 03-impl 層の目次。機能間連携仕様書群の代表として層全体の版と合格証を持つ
keywords: [目次]
verified:
  at: 2026-08-04
  version: 1.8.0
  against:
    - doc: docs/02-design/system.md
      version: 2.0.0
    - doc: docs/02-design/relations.md
      version: 1.0.0
---

<!-- 2026-08-04 /doc-check ssot task-impl-depth(新しい実行): **合格証を再発行した(1.5.0)。**
     この層を止めていた2つの理由はいずれも解消した。
     (1) docs/issues/038 — 影響範囲内の relations 21本の未解決の重大度「高」5件は、人間が
         **案B(高5件は task-impl-depth で直し、中低27件は別タスク)** で再裁定し、5件すべてが
         SSOT へ反映されている。本実行で5件すべてを**本文とコードの両方で照合して確認**した
         (controller.go:52 の Run(ctx) と :90〜:96 の errSuspended 吸収 / :70・:1080 の return err /
          state.go:396〜:402 の全エラーで空キュー / handoff.go:49〜:52 の poll<=0→500ms /
          review.go:22〜:31 の HasSevere 完全一致と :296〜:312 の未検証)。
         → issue 038 の**未解決分は中低27件だけ**なので、severity を 高 → 中 に是正した
         (2026-08-03 に issue 032 で行ったのと同じ是正)。
     (2) source の docs/02-design/system.md → docs/01-requirements/non-functional.md は
         1.2.0 で再認証済み(docs/issues/035 は解消)。本実行で 02 層まで再認証した。
     **残る既知の乖離は中低のみ**で、下の「コードとの乖離として未解決のもの」に列挙している
     (原則2 のとおり、どちらが正かは人間が裁定済み = 次タスクで記述をコードへ揃える)。
     ★本実行は**独立レンズが1つも走っていない**(Codex がアカウントの利用上限に達した)。
     合格証は Claude 単独の検証に基づく。2026-08-10 以降に /doc-check full を掛け直すこと。 -->

<!-- 2026-08-04 /doc-check ssot task-impl-depth(さらに新しい実行): **1.7.0 で再認証した。**
     直前の状態は version 1.6.0 / verified 1.5.0 で**合格証が失効していた**(1.5.0 → 1.6.0 の
     内容変更が histories にも memo の進捗メモにも記録されていない)。本実行で本文の主張を
     1項目ずつ機械照合し、**`issue 019` の残件数だけが古かった**ので訂正して再認証した
     (8件 → 残1件。他の7件は実名へ置換済みで、`docs/03-impl/` 全体を語境界付きで走査して残存0)。
     照合した内容: relations 82本 / モジュール29 / check-relations 合格(82/82)/
     callgraph-check 高0・中3・低17・参考20 / build-callgraphs --check 最新 /
     cluster-features --check 最新 / check-contracts 合格 / build-index --check 差分なし /
     受入基準カバレッジ 180=180・NFR 15/15(欠落0・余剰0・重複0)/ 02⇄03 は PLAN 63・MODULE 82 で
     PLAN のみ 0 件・MODULE のみ 19 件(orchestrator 内部18 + mathkit = 意図的除外と完全一致)/
     「実装の欠陥として起票済み 17件」の全 ID の実在と、`014` がどの `## 既知の制限` からも
     参照されていないこと。
     ★本実行も**独立レンズが1つも走っていない**(Codex は利用上限。復旧予定 2026-08-10)。 -->

# 03-impl 目次

## この層の状態

| 項目 | 値 |
|---|---|
| 機能間連携仕様書の本数 | 82 |
| 網羅しているモジュール | MOD-cli-common, MOD-cli-setup, MOD-cli-start, MOD-cli-stop, MOD-cli-attach, MOD-cli-code, MOD-cli-list, MOD-cli-login, MOD-cli-login-codex, MOD-cli-logout, MOD-cli-forward, MOD-cli-unforward, MOD-cli-ports, MOD-cli-ssh-keys, MOD-cli-firewall, MOD-cli-orchestrate, MOD-cli-pull, MOD-cli-upgrade, MOD-cli-reset, MOD-makefile, MOD-entrypoint, MOD-firewall, MOD-docker-proxy, MOD-portsync, MOD-vm-mode, MOD-orchestrator, MOD-hooks, MOD-container-tools, MOD-sample-project(29モジュール) |
| `check-relations.py` 最終結果 | 合格(2026-08-04 に再実行。82 ファイル / 82 ID。対称性・参照実在・impl パス・必須項目・機能表との 1:1 すべて問題なし) |
| コードとの乖離として未解決のもの | **機能の欠落は 1 件**: macOS のコントローラ生存判定が無い(`docs/issues/003-future-macos-orchestrator-scope.md`)。**本文の叙述レベルの食い違いは、解消したものと残るものを分けて数える。** 解消済み: issue 009 (b) の10件、`MODULE-orchestrator-worker`(セッション ID の採番元・`--resume` 失敗時のフォールバック)/ `MODULE-orchestrator-slack`(`NopNotifier` を返すという記述)/ `MODULE-orchestrator-handoff`(壊れた制御ファイルの扱い)の3件、`MODULE-orchestrator-state-intervention`(同じ壊れた制御ファイルの扱い)/ `MODULE-orchestrator-streamlog`(戻り値と「追記」)/ `MODULE-orchestrator-term`(`selectMenu` の戻り値)の3件 — いずれも**実装に合わせて訂正した**。**未解決として残るもの**: `issue 009` (a) の17件(本文で `ctx` 等の定型引数を省略してよいかの規約が未決。`/kit-improve` 案件)/ `issue 019` の**残 1 件**(`TestReadyTasks_Basic`。`tests/orchestrator.md:57`・`:110` の2箇所。他の7件は 2026-08-04 に実名へ置換済みで、コードとの機械照合で残存 0 を確認した)/ `issue 032` の18件(この層のうち影響範囲外だった7本の叙述。高2件は上記のとおり解消済み)/ **`issue 038` の残 27 件(同 issue の表 #7〜#32。`task-impl-depth` が掘り下げた影響範囲内の21本のうち、`## 処理の流れ` / `## 連携先と連携内容` / `## 戻り値・副作用` と frontmatter の `callers` / `callees` — いずれも変更指示の `sections` に入っていなかった節。重大度は中20件・低7件で、**「高」5件(表 #1〜#5)は 2026-08-04 の再裁定=案B により `task-impl-depth` で解消済み**。#6 は `issue 037` の再裁定で解消)**。集計の維持そのものは `docs/issues/030` で追跡する |
| 実装の欠陥として起票済み(コードは未修正) | **16件**。数え方は「`03-impl` のいずれかの `## 既知の制限` から参照されている `type: modify` / `type: bug` の issue」とし、`type: future` の `003` は除く: `docs/issues/001`(orchestrator の7シンボルが製品コードから呼ばれない)/ `002`(`.claude-dev.yaml` が全面上書きされる)/ `010`(forward のホストポート選択の競合)/ `011`(taskID を検証しないパス結合)/ `012`(`reviewer_vendor` が無効)/ `013`(Slack の API レベルの失敗を検出しない)/ `015`(列挙外の `needs_human.reason` が黙って捨てられる)/ `020`(CLI に排他機構が無い)/ `021`(`.orchestrator/` ストアにロックが無い)/ `022`(`merge_strategy` の列挙を検証しない)/ `023`(`CLAUDE_DEV_SSH_BRIDGE_PORT` を無検証で採る)/ `024`(`stop` が別プロジェクトの compose 資源を巻き込みうる)/ `025`(`logout` / `reset` が削除失敗を握って成功と表示する)/ `026`(コントローラが状態保存の失敗を握りつぶす)/ `028`(名前の一意性が `NFR-scale-01` を満たさない)/ `029`(`logout` が確認なしで全プロジェクトのコンテナを落とす)。**`036`(`start` の後片付けが同名の稼働中コンテナを削除する = データの破壊)は `task-fix-start-cleanup` で修正して解消した**ため、この数から外れている。**`014`(追記型ログが必須フィールドを満たさない)と `045`(`stop` の遊休判定が古いイメージの稼働コンテナを数え落として共有 docker-proxy を消す。`FR-env-01` 受入基準9 違反)はどの「既知の制限」からも参照されていない**ため上の数に含めない(`045` の本来の置き場は `MODULE-cli-stop` の「既知の制限」であり、`MODULE-cli-stop` を影響範囲に含む次のタスクで書く)。集計の維持そのものは `docs/issues/030` で追跡する |
| `relations-coverage.py` 最終結果 | 未記載 30 件を検出するが、**全件が `scan-entrypoints.py` の Go `switch` 誤検出**(設定キー `max_workers` 等・TUI のキー入力 `p`/`d`/`i`・JSON の型識別子・git のサブコマンド文字列)であり、実在する入口ではない。コードとの一致は `callgraph-check.py` と `check-relations.py` が担保する |

## 02 との差分(未解消のもの)

| 種別 | 対象 | 内容 | 対処 |
|---|---|---|---|
| PLAN なし / MODULE あり | MODULE-orchestrator-* の内部関数18本、MODULE-sample-project-mathkit | 設計側は同一モジュール内部で完結する private helper を書かない取り決めのため、意図的な差分である | 対処不要(`02-design/relations.md` の網羅範囲に明記) |
| 契約の差異 | CTR-cli-orchestrator | macOS 版にコントローラの生存判定が無く、設計の期待(OS によらず同じ観測可能な結果)を満たしていない | `docs/issues/003-future-macos-orchestrator-scope.md` で追跡 |
| ログ仕様の差異 | `02-design/logging.md`「必須フィールド」⇄ 追記型ログ3本 | 設計は `ts` / `event` / `task_id` / `attempt` / `detail` を必須とするが、実装は `attempt` を持たず(`dispatch` だけ `detail.attempt`)、`assumptions.jsonl` / `interventions.jsonl` は `event` も持たない | `docs/issues/014-modify-append-logs-lack-required-fields.md` で追跡(**正がどちらかは要確認**) |
| ログ仕様の差異 | `02-design/logging.md`「通知の送信失敗 → WARN」⇄ `MODULE-orchestrator-slack` | 実装が検出・記録するのは通信エラーだけで、4xx / 5xx / レート制限 / `ok:false` は無記録のまま捨てられる | `docs/issues/013-modify-slack-api-level-failures-are-undetected.md` で追跡(**設計が正**) |

02(設計)との差分は上記4件で、これ以外に差分は無い。

## 01(要件)との差異(未解消のもの)

**すべて人間が裁定済み**(実装の修正は別タスク)。「要件との差異が無い」わけではないので、
ここに明記する。

| 要件 | 実装 | 裁定と追跡 |
|---|---|---|
| `NFR-scale-01`「コンテナ名・compose プロジェクト名がプロジェクト間で衝突しない(衝突 0 件)」 | コンテナ名・compose プロジェクト名・中継コンテナ名をディレクトリ名だけから導くため、別パスの同名ディレクトリが同一セッション扱いになる | **設計が正**(2026-08-04)。コード修正は別タスク。`docs/issues/028` |
| `AC-03` / `FR-env-07` 受入基準8「危険な操作は拒否される」 | docker-proxy は解釈できないボディを検査せず中継する | `D0-sec-05`(Docker API 検査の厳密さの委任)の範囲内で「中」と裁定。`docs/issues/005` |
| `FR-orch-05` 受入基準7「読めない状態ファイルの既存内容を破壊しない」 | 壊れた `intervention/open.json` は空キューとして扱われ、判断待ちキュー全体が黙って失われる | 事実を `MODULE-orchestrator-state-intervention` の異常系に明記済み。コード修正は別タスク。`docs/issues/038` #3 |
| `NFR-ops-01`(運用の可観測性) | 追記型ログ3本が `02-design/logging.md` の必須フィールドを満たさない(上の「02 との差分」と同一事象) | 正がどちらかは**要確認**。`docs/issues/014` |

## 目次

<!-- BEGIN GENERATED: build-index.py -->

| ファイル | version | 更新 | 概要 |
|---|---|---|---|
| [features](features.md) | - | 2026-08-02 | claude-dev 開発環境の機能一覧と入口。CLI サブコマンド・Makefile ターゲット・常駐スクリプト・Go バイナリの入口を列挙する |
| [images](environments/images.md) | 1.0.0 | 2026-08-03 | 配布イメージ(claude-cli / claude-vnc)のステージ構成・ビルド引数・キャッシュの効かせ方 |
| [local-docker-resources](infra/local/docker-resources.md) | 1.1.0 | 2026-08-04 | ホスト上に作られる Docker リソース(ネットワーク・ボリューム・コンテナ)の一覧と命名規則 |
| [local-ghcr](infra/local/ghcr.md) | 1.1.0 | 2026-08-04 | 配布イメージの公開先 GHCR の構成(リポジトリ・タグ・マルチアーキ・認証の置き場所) |

件数: 4

<!-- END GENERATED -->

## 機能間連携仕様書

`docs/03-impl/relations/index.md` を参照(こちらも生成物)。**82機能** の境界は
`docs/03-impl/features.md`(人間が合意した機能表)が定義する。

## コールグラフ

`docs/03-impl/callgraphs/index.md` を参照。**ツールだけが書く場所**であり、機能間連携仕様書では
ない(`.claude/directions/callgraphs.md`)。版も合格証も持たない純粋な導出物で、鮮度は
`python3 .claude/scripts/build-callgraphs.py --check` で検査する。

| 項目 | 値 |
|---|---|
| 最終検査 `--check` | 最新(2026-08-04 に再実行。go 219シンボル/399辺 / shell 130/168 / make 19/22 / python 5/0 / typescript 0 / infra 0。エントリポイント 72) |
| `callgraph-check.py` の未解決指摘 | 指摘 40 件・**重大度「高」ゼロ**(2026-08-04 に再実行して同値)(中3 = CG3 entrypoint のプロセス跨ぎ連携 / 低17 = CG2 到達不能候補 / 参考20 = CG4 取りこぼし候補)。中3件は絶対パス起動のため shell 抽出器が辺を解決できないもので、根拠は `relations/MODULE-entrypoint-claude.md` の本文にある |
| 抽出器が無い領域 | Dockerfile と GitHub Actions。この2つはモジュールにせず `environments/images.md` と `infra/local/ghcr.md` が記述を持つ(`DSN-mod-05`) |
