---
target: docs/03-impl/index.md
change: replace
sections:
  - "## この層の状態"
  - "## 01(要件)との差異(未解消のもの)"
deletes: []
reason: issue 019 / 032 / 038 を解消したので「コードとの乖離として未解決のもの」から外す。あわせて MODULE-docker-proxy-serve の既知の制限が issue 005 を参照するようになるため起票済みの件数を 15 → 16 に直す
reflected: 2026-08-05
---

<!-- 変更指示。反映後の最終形を書く。version / verified は持たない。
     ・`機能間連携仕様書の本数` / `網羅しているモジュール` / `check-relations.py 最終結果` /
       `relations-coverage.py 最終結果` の各行は現行のまま(本タスクは本数を変えない)。
       check-relations.py の再実行結果は /task-close が実測値で更新する。
     ・`issue 009` (a) の 17 件は本タスクの範囲外(決定シート論点2 = 案A)。
     ・2026-08-05 /doc-check(task) の自動修正: 「`045` は…**本タスク**が修正して解消した」の
       「本タスク」を実タスク名 `task-fix-destructive-scope` へ置き換えた。SSOT に「本タスク」を
       残すと参照先が存在しない(削除済みタスク)ため。docs/issues/056 と同じ性質の残留である。 -->

## この層の状態

| 項目 | 値 |
|---|---|
| 機能間連携仕様書の本数 | 83 |
| 網羅しているモジュール | MOD-cli-common, MOD-cli-setup, MOD-cli-start, MOD-cli-stop, MOD-cli-attach, MOD-cli-code, MOD-cli-list, MOD-cli-login, MOD-cli-login-codex, MOD-cli-logout, MOD-cli-forward, MOD-cli-unforward, MOD-cli-ports, MOD-cli-ssh-keys, MOD-cli-firewall, MOD-cli-orchestrate, MOD-cli-pull, MOD-cli-upgrade, MOD-cli-reset, MOD-makefile, MOD-entrypoint, MOD-firewall, MOD-docker-proxy, MOD-portsync, MOD-vm-mode, MOD-orchestrator, MOD-hooks, MOD-container-tools, MOD-sample-project(29モジュール) |
| `check-relations.py` 最終結果 | 合格(2026-08-04 に再実行。83 ファイル / 83 ID。対称性・参照実在・impl パス・必須項目・機能表との 1:1 すべて問題なし) |
| コードとの乖離として未解決のもの | **機能の欠落は 1 件**: macOS のコントローラ生存判定が無い(`docs/issues/003-future-macos-orchestrator-scope.md`)。**本文の叙述レベルの食い違いとして残るのは `issue 009` (a) の 17 件だけ**である(本文で `ctx` 等の定型引数を省略してよいかの規約が未決。`/kit-improve` 案件であり、規約が決まるまで直さない)。**`issue 019`(`tests/orchestrator.md` の実在しないテスト識別子)/ `issue 032`(影響範囲外だった orchestrator 7本の叙述)/ `issue 038`(掘り下げ対象 21 本のうち変更指示の `sections` に入っていなかった節)は解消した**(コードを正として全件を突き合わせ、`## 処理の流れ` / `## 呼び出され方` / `## 連携先と連携内容` / `## 戻り値・副作用` / `## 異常系` / `## 既知の制限` と frontmatter の `callers` / `callees` / `tests` を実装の事実へ揃えた。経緯は `docs/histories/`)。集計の維持そのものは `docs/issues/030` で追跡する |
| 実装の欠陥として起票済み(コードは未修正) | **18件**。数え方は「`03-impl` のいずれかの `## 既知の制限` から参照されている `type: modify` / `type: bug` の issue」のうち、**本システムが未修正のもの**とし、`type: future` の `003` は除く: `docs/issues/001`(orchestrator の7シンボルが製品コードから呼ばれない。**`MODULE-orchestrator-worktree` の `HasCommits` と `MODULE-orchestrator-mode` の `ResolveArgsOne` も同じ性質として同 issue から追跡する**)/ `002`(`.claude-dev.yaml` が全面上書きされる)/ `005`(docker-proxy が解釈できないボディを検査せず中継する)/ `010`(forward のホストポート選択の競合)/ `011`(taskID を検証しないパス結合)/ `012`(`reviewer_vendor` が無効)/ `013`(Slack の API レベルの失敗を検出しない)/ `015`(列挙外の `needs_human.reason` が黙って捨てられる)/ `021`(`.orchestrator/` ストアにロックが無い)/ `022`(`merge_strategy` の列挙を検証しない)/ `023`(`CLAUDE_DEV_SSH_BRIDGE_PORT` を無検証で採る)/ `026`(コントローラが状態保存の失敗を握りつぶす)/ `028`(名前の一意性が `NFR-scale-01` を満たさない)/ `047`(`reset` が `claude-dev-vm-*` ボリュームを消さない)/ `052`(`logout` が削除対象0件の経路でラベル無しコンテナの警告を出さない)/ `053`(`logout` が列挙できない共有ボリュームを「空」と判定する)/ **`057`(壊れた `intervention/open.json` で判断待ちキューが黙って失われる)/ `058`(未知の `severity` が品質ゲートを通過する)**。**後の2件は `docs/issues/038` から切り出したもので、038 自身は記述の乖離の issue だったため従来この集計に入っていなかった**(`task-relations-code-sync` で 038 を閉じるにあたり、コードの欠陥だけを別 issue として残した)。**`036`(`start` の後片付けが同名の稼働中コンテナを削除する)は `task-fix-start-cleanup` で、`020`(排他機構が無い)/ `024`(`stop` が別プロジェクトの compose 資源を巻き込む)/ `025`(削除失敗を握って成功と表示する)/ `029`(`logout` が確認なしで全プロジェクトのコンテナを落とす)/ `045`(遊休判定が古いイメージのコンテナを数え落とす)は `task-fix-destructive-scope` で修正して解消した**ため、この数から外れている(`024` だけは `MODULE-cli-stop` の「既知の制限」から**移行期の残り**として今も参照されているが、根本は解消済みなので未修正には数えない)。**`014`(追記型ログが必須フィールドを満たさない)/ `046`(`list` / `make status` / `make clean` が `--filter ancestor` でコンテナを数え落とす)/ `051`(CLI の出力に生の Docker ID が混じる)/ `054`(SSOT が削除済み issue のパスを参照し続ける。そもそも実装の欠陥ではなく記録の運用の問題)は、どの「既知の制限」からも参照されていない**ため上の数に含めない(いずれもコードは未修正である。集計の対象は「既知の制限」から参照されているものに限る、という数え方の定義による)。**`045` は `MODULE-cli-stop` の「既知の制限」に書くと約束していたが、`task-fix-destructive-scope` が修正して解消したため書かない**(約束は果たされた形で閉じた)。集計の維持そのものは `docs/issues/030` で追跡する |
| `relations-coverage.py` 最終結果 | 未記載 30 件を検出するが、**全件が `scan-entrypoints.py` の Go `switch` 誤検出**(設定キー `max_workers` 等・TUI のキー入力 `p`/`d`/`i`・JSON の型識別子・git のサブコマンド文字列)であり、実在する入口ではない。コードとの一致は `callgraph-check.py` と `check-relations.py` が担保する |

## 01(要件)との差異(未解消のもの)

**すべて人間が裁定済み**(実装の修正は別タスク)。「要件との差異が無い」わけではないので、
ここに明記する。

| 要件 | 実装 | 裁定と追跡 |
|---|---|---|
| `NFR-scale-01`「コンテナ名・compose プロジェクト名がプロジェクト間で衝突しない(衝突 0 件)」 | コンテナ名・compose プロジェクト名・中継コンテナ名をディレクトリ名だけから導くため、別パスの同名ディレクトリが同一セッション扱いになる | **設計が正**(2026-08-04)。コード修正は別タスク。`docs/issues/028` |
| `AC-03` / `FR-env-07` 受入基準8「危険な操作は拒否される」 | docker-proxy は解釈できないボディを検査せず中継する | `D0-sec-05`(Docker API 検査の厳密さの委任)の範囲内で「中」と裁定。`docs/issues/005` |
| `FR-orch-05` 受入基準7「読めない状態ファイルの既存内容を破壊しない」 | 壊れた `intervention/open.json` は空キューとして扱われ、判断待ちキュー全体が黙って失われる | 事実を `MODULE-orchestrator-state-intervention` の異常系に明記済み。コード修正は別タスク。`docs/issues/057-bug-broken-open-json-silently-drops-the-intervention-queue.md` |
| `NFR-ops-01`(運用の可観測性) | 追記型ログ3本が `02-design/logging.md` の必須フィールドを満たさない(上の「02 との差分」と同一事象) | 正がどちらかは**要確認**。`docs/issues/014` |
| `FR-orch-06` 受入基準3(品質ゲートは重大な指摘があれば差し戻す) | レビュー結果の `severity` の値域を検証しないため、綴り違い・別語彙の重大な指摘が「重大でない」扱いでゲートを通過する | 事実を `MODULE-orchestrator-review` の処理の流れに明記済み。**正がどちらかは要確認**(実装の誤りか、契約の不足か)。`docs/issues/058-bug-unknown-severity-passes-the-review-gate.md` |
