---
target: docs/03-impl/index.md
change: replace
sections:
  - "## この層の状態"
  - "## 01(要件)との差異(未解消のもの)"
deletes: []
reason: docs/issues/036 を本タスクで解消する。層の代表である index.md が 036 を「実装の欠陥として起票済み(コードは未修正)」と「01(要件)との差異」の両方に挙げているため、解消後の姿へ更新する
---

<!-- 変更指示。記法の正は .claude/directions/change-set.md
     ・「この層の状態」: 起票済みの件数を 17 → 16 にし、036 を一覧から外す。
       あわせて「本タスクで解消して削除予定の 034 は除く」という記述を実態(034 は
       task-impl-depth の /task-close で削除済み)へ直す
     ・「01(要件)との差異」: FR-env-01 / NFR-scale-01(同名コンテナの扱い)の行を削除する。
       NFR-scale-01 の命名の一意性の行(issue 028)は**残る**(別事象・別タスク)
     ・他の行・他の節(「02 との差分」など)は変更しない -->

## この層の状態

| 項目 | 値 |
|---|---|
| 機能間連携仕様書の本数 | 82 |
| 網羅しているモジュール | MOD-cli-common, MOD-cli-setup, MOD-cli-start, MOD-cli-stop, MOD-cli-attach, MOD-cli-code, MOD-cli-list, MOD-cli-login, MOD-cli-login-codex, MOD-cli-logout, MOD-cli-forward, MOD-cli-unforward, MOD-cli-ports, MOD-cli-ssh-keys, MOD-cli-firewall, MOD-cli-orchestrate, MOD-cli-pull, MOD-cli-upgrade, MOD-cli-reset, MOD-makefile, MOD-entrypoint, MOD-firewall, MOD-docker-proxy, MOD-portsync, MOD-vm-mode, MOD-orchestrator, MOD-hooks, MOD-container-tools, MOD-sample-project(29モジュール) |
| `check-relations.py` 最終結果 | 合格(2026-08-04 に再実行。82 ファイル / 82 ID。対称性・参照実在・impl パス・必須項目・機能表との 1:1 すべて問題なし) |
| コードとの乖離として未解決のもの | **機能の欠落は 1 件**: macOS のコントローラ生存判定が無い(`docs/issues/003-future-macos-orchestrator-scope.md`)。**本文の叙述レベルの食い違いは、解消したものと残るものを分けて数える。** 解消済み: issue 009 (b) の10件、`MODULE-orchestrator-worker`(セッション ID の採番元・`--resume` 失敗時のフォールバック)/ `MODULE-orchestrator-slack`(`NopNotifier` を返すという記述)/ `MODULE-orchestrator-handoff`(壊れた制御ファイルの扱い)の3件、`MODULE-orchestrator-state-intervention`(同じ壊れた制御ファイルの扱い)/ `MODULE-orchestrator-streamlog`(戻り値と「追記」)/ `MODULE-orchestrator-term`(`selectMenu` の戻り値)の3件 — いずれも**実装に合わせて訂正した**。**未解決として残るもの**: `issue 009` (a) の17件(本文で `ctx` 等の定型引数を省略してよいかの規約が未決。`/kit-improve` 案件)/ `issue 019` の**残 1 件**(`TestReadyTasks_Basic`。`tests/orchestrator.md:57`・`:110` の2箇所。他の7件は 2026-08-04 に実名へ置換済みで、コードとの機械照合で残存 0 を確認した)/ `issue 032` の18件(この層のうち影響範囲外だった7本の叙述。高2件は上記のとおり解消済み)/ **`issue 038` の残 27 件(同 issue の表 #7〜#32。`task-impl-depth` が掘り下げた影響範囲内の21本のうち、`## 処理の流れ` / `## 連携先と連携内容` / `## 戻り値・副作用` と frontmatter の `callers` / `callees` — いずれも変更指示の `sections` に入っていなかった節。重大度は中20件・低7件で、**「高」5件(表 #1〜#5)は 2026-08-04 の再裁定=案B により `task-impl-depth` で解消済み**。#6 は `issue 037` の再裁定で解消)**。集計の維持そのものは `docs/issues/030` で追跡する |
| 実装の欠陥として起票済み(コードは未修正) | **16件**。数え方は「`03-impl` のいずれかの `## 既知の制限` から参照されている `type: modify` / `type: bug` の issue」とし、`type: future` の `003` は除く: `docs/issues/001`(orchestrator の7シンボルが製品コードから呼ばれない)/ `002`(`.claude-dev.yaml` が全面上書きされる)/ `010`(forward のホストポート選択の競合)/ `011`(taskID を検証しないパス結合)/ `012`(`reviewer_vendor` が無効)/ `013`(Slack の API レベルの失敗を検出しない)/ `015`(列挙外の `needs_human.reason` が黙って捨てられる)/ `020`(CLI に排他機構が無い)/ `021`(`.orchestrator/` ストアにロックが無い)/ `022`(`merge_strategy` の列挙を検証しない)/ `023`(`CLAUDE_DEV_SSH_BRIDGE_PORT` を無検証で採る)/ `024`(`stop` が別プロジェクトの compose 資源を巻き込みうる)/ `025`(`logout` / `reset` が削除失敗を握って成功と表示する)/ `026`(コントローラが状態保存の失敗を握りつぶす)/ `028`(名前の一意性が `NFR-scale-01` を満たさない)/ `029`(`logout` が確認なしで全プロジェクトのコンテナを落とす)。**`036`(`start` の後片付けが同名の稼働中コンテナを削除する = データの破壊)は `task-fix-start-cleanup` で修正して解消した**ため、この数から外れている。**`014`(追記型ログが必須フィールドを満たさない)と `045`(`stop` の遊休判定が古いイメージの稼働コンテナを数え落として共有 docker-proxy を消す。`FR-env-01` 受入基準9 違反)はどの「既知の制限」からも参照されていない**ため上の数に含めない(`045` は `MODULE-cli-stop` の「既知の制限」へ書くのが正しく、それは `MODULE-cli-stop` を影響範囲に含む次のタスクで行う)。集計の維持そのものは `docs/issues/030` で追跡する |
| `relations-coverage.py` 最終結果 | 未記載 30 件を検出するが、**全件が `scan-entrypoints.py` の Go `switch` 誤検出**(設定キー `max_workers` 等・TUI のキー入力 `p`/`d`/`i`・JSON の型識別子・git のサブコマンド文字列)であり、実在する入口ではない。コードとの一致は `callgraph-check.py` と `check-relations.py` が担保する |

## 01(要件)との差異(未解消のもの)

**すべて人間が裁定済み**(実装の修正は別タスク)。「要件との差異が無い」わけではないので、
ここに明記する。

| 要件 | 実装 | 裁定と追跡 |
|---|---|---|
| `NFR-scale-01`「コンテナ名・compose プロジェクト名がプロジェクト間で衝突しない(衝突 0 件)」 | コンテナ名・compose プロジェクト名・中継コンテナ名をディレクトリ名だけから導くため、別パスの同名ディレクトリが同一セッション扱いになる | **設計が正**(2026-08-04)。コード修正は別タスク。`docs/issues/028` |
| `AC-03` / `FR-env-07` 受入基準8「危険な操作は拒否される」 | docker-proxy は解釈できないボディを検査せず中継する | `D0-sec-05`(Docker API 検査の厳密さの委任)の範囲内で「中」と裁定。`docs/issues/005` |
| `FR-orch-05` 受入基準7「読めない状態ファイルの既存内容を破壊しない」 | 壊れた `intervention/open.json` は空キューとして扱われ、判断待ちキュー全体が黙って失われる | 事実を `MODULE-orchestrator-state-intervention` の異常系に明記済み。コード修正は別タスク。`docs/issues/038` #3 |
| `NFR-ops-01`(運用の可観測性) | 追記型ログ3本が `02-design/logging.md` の必須フィールドを満たさない(上の「02 との差分」と同一事象) | 正がどちらかは**要確認**。`docs/issues/014` |
