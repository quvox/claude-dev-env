---
id: 2026-08-20-verify-impl-citation-and-runtime-env-facts
date: 2026-08-20
record: なし(taskless — flow: verify-impl)
critical: false
origin_layer: 03
issue: docs/issues/109-bug-make-status-treats-a-failed-docker-query-as-zero-sessions.md
summary: F3 実装整合フローが、受け渡しファイルの存在条件と 03 層のコード引用をコードで決着させ、make status の契約違反を起票した
---

<!-- taskless の履歴。F3(/verify-impl all)の自動修正が残したもの。 -->

# 2026-08-20 実装整合フローの自動修正(引用と受け渡しファイルの事実)

## 変更理由

### R-01 受け渡しファイルの存在条件が 02・03・E2E の3箇所で偽だった

- 起点層・根拠: CLAUDE.md 原則2(事実の食い違いはコードを正として直す)。
  `scripts/entrypoint-claude.sh:27` の `: > "$RUNTIME_ENV_FILE"` は**条件節の外**にあり、
  `/etc/claude-dev/runtime.env` は常に作られる(空・0644)。
- 変更が必要になった条件: 独立レビュー(lens: claude)が、02 の契約・03 の契約・E2E 手順9-9 の
  3箇所が「このファイルは存在しないことがある」と書いていることを検出した。

### R-02 コード引用の行番号が `2217c84` の実装で動いたまま残っていた

- 起点層・根拠: 同 原則2。`docs/pendings.md:168` が持ち越している「コード引用の行番号のずれ」の、
  今回の verify の射程に入る分である。
- 変更が必要になった条件: F3 が 03 層の `path:line` 引用 132 件を実コードに当て、
  ずれと、`sort -u` のように実装に存在しない機構の記述を見つけた。

## 変更内容の要約

- 受け渡しファイルの存在条件を「常に在る。空のことがある」へ直した(02 の契約・03 の契約・E2E 手順)。
- 03 層のコード引用のずれを実コードで取り直した(`MODULE-cli-start` 4件、`03-impl/contracts/cli-container.md`
  の `CLAUDE_DEV_VM` 1件、`features.md` 3件、`03-impl/index.md` と `docs/issues/097` の `help|*)` 各1件)。
- `MODULE-makefile-status` の `sort -u` を実装の `awk` へ、異常系の1行を実際の出力へ直した。
- `MODULE-makefile-status` / `MODULE-makefile-clean` の `tests:` を `03-impl/tests/makefile.md` と揃えた。
- 削除済み issue を指す参照3件を、経緯の履歴を指す形へ替えた。

## 更新したドキュメント

| 理由ID | ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|---|
| R-01 | docs/02-design/contracts/cli-container.md | 1.16.0 → 1.17.0 | 受け渡しファイルの「無いとき」の行を「中身が空のとき」へ替え、ファイル自体は常に作られることを書いた |
| R-01 | docs/03-impl/contracts/cli-container.md | 1.12.0 → 1.13.0 | 同じ行と、`SSH_AUTH_SOCK` の記録条件(`[ -S ]` であって中継ポート方式に限らない)を実装へ揃えた |
| R-01 | docs/03-impl/tests/e2e.md | 1.14.0 → 1.15.0 | 手順9-9 の前提を「無い構成」から「中身が空の構成」へ替えた |
| R-02 | docs/03-impl/relations/MODULE-cli-start.md | なし(relations 層は版を持たない) | `path:line` 4件を実コードで取り直した |
| R-02 | docs/03-impl/relations/MODULE-makefile-status.md | 同 | `sort -u` → `awk`、異常系の1行、`tests:` |
| R-02 | docs/03-impl/relations/MODULE-makefile-clean.md | 同 | `tests:`、削除済み issue への参照 |
| R-02 | docs/03-impl/relations/MODULE-cli-list.md | 同 | 削除済み issue への参照2件 |
| R-02 | docs/03-impl/features.md | 同 | 到達しない関数の判断3件の `path:line` |
| R-02 | docs/03-impl/index.md | 1.33.0 → 1.34.0 | `help|*)` の引用、`check-relations.py` の再実行の主体、層の合格証を 1.34.0 で書き直した |
| R-02 | docs/03-impl/callgraphs/index.md, shell.md | なし(ツール生成) | `build-callgraphs.py` の再生成(`record_runtime_env` の1シンボル・1辺が入った) |

## 実装したもの

| 理由ID | 対象 | 内容 | コミット |
|---|---|---|---|
| (なし) | - | 製品コードは1バイトも変えていない(F3 は製品コードを書かない) | - |

## 実施した移行

なし

### ロールバック・復旧記録

適用外(critical: false。製品コードに触れず、変更はすべて Markdown である)

## 機能間連携仕様書の変化

| 種別 | ID | 内容 |
|---|---|---|
| (増減なし) | - | 機能 61 / 機械が出した辺 88 は再生成の前後で同数 |

## 検討した代替案

| 論点 | 採用した案 | 棄却した代替案 | 棄却の理由 / 崩れる条件 |
|---|---|---|---|
| CG3 の3件と CG4 の「参考」12件の再提起を止めるか | `docs/pendings.md` の既存1行に確認済み/棄却の根拠を書き足すだけにした | `docs/03-impl/features.md` に雛形が持つ「棄却した候補辺・確認済みの境界辺」節を新設する | CLAUDE.md §3 が「検証は文書を増やしてはならない。置換か削除で直す」と定める。同じキーの残務が既に在るので、そこを直す形にした。節の新設は次に features.md を closure に持つ `/build` の仕事である |
| `make status` の契約違反をどこへ出すか | `docs/issues/109` として起票した | 残務1行 | 02 の契約に対して振る舞いが誤っており、利用者が「稼働中のセッションが無い」と読み違える。原則8 のゲートの行1(仕様に対する bug)に当たる |

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 新規 issue | docs/issues/109-bug-make-status-treats-a-failed-docker-query-as-zero-sessions.md | `make status` が問い合わせの失敗を0件として表示する |
| 棚上げ | docs/pendings.md 残務 | 構築記録 `fix-session-list-undercount` の `BR-05` 根拠と closure の欠落2件 |
| 棚上げ | docs/pendings.md 残務 | `claude-dev list` / `make status` に固定名 `claude-dev-docker-proxy` の除外が無い(偶然で成立している) |
| 解消した issue | (なし) | - |
