---
id: 2026-08-11-relations-sync-to-code
date: 2026-08-11
task: なし(タスク無しでの `/relations all --apply`。CLAUDE.md 原則1 の既存例外)
origin_layer: 03
issue: docs/issues/096-modify-fourteen-shared-helpers-with-fanin-2-or-more-are-absent-from-the-feature-table.md
summary: コードと 03-impl の一致を復元するため feature-graph.md を再生成し、未到達2件の判断を機能表に記録した
---

# 2026-08-11 コードと 03-impl の同期(`/relations all --apply`)

## 変更理由

`/retrofit` の前提検査で `cluster-features.py --check` が「古い」を返した。
`docs/03-impl/feature-graph.md` が生成物でありながら再生成結果と一致せず、
**実在しないファイル `docs/03-impl/callgraphs/resources.md` を指す1行**を持っていた
(原則2 の事実の食い違い)。進行中タスクは無く、人間が明示的に同期を要求したため、
`/relations` §0 のケース2(タスク無し + 人間の明示要求)で `--apply` を実行した。

## 変更内容の要約

- `feature-graph.md` を再生成した。差分は上記1行の削除のみで、機能・辺・共有関数の数は変わらない
  (機能 56 / 辺 76(確定 76 / 候補 0)/ 共有関数 28 / 未到達 8)。
- `callgraph-check.py` の CG3「中」3件(`MODULE-entrypoint-claude` の callees 3本)を裁定した。
  **宣言が正**で、shell 抽出器が絶対パス起動を解決できないだけであることをコードで確認した。
- `feature-graph.md` の「未到達」8件のうち、判断が記録されていなかった
  `_destructive_done` / `_release_all_locks`(OS別で4件)を Tier 3 抽出の取りこぼしと判定し、
  機能表の「到達しない関数についての判断」に記録した。
- `propose-features.py` の共通基盤候補28件(14シンボル)が機能表のどの表にも無いことを検出し、
  `docs/issues/096` を起票した。**境界そのものは変更していない**。
- **独立レビュー(Codex)が指摘10件を返し、うち7件をコードで裏取りして 03-impl を修正した**
  (終了コード 130 の記載漏れ4件、事実の誤り3件)。残る3件のうち2件は誤検知、1件は
  `docs/issues/097` として起票した。
- **コードは1行も変更していない**(`/relations` はコードを変更しない)。

## 更新したドキュメント

| ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|
| docs/03-impl/feature-graph.md | (生成物。版を持たない) | 再生成。実在しない `callgraphs/resources.md` を指す1行が消えた(資源結合0件のため生成器が出力しない) |
| docs/03-impl/features.md | (版を持たない。代表は 03-impl/index.md) | 「到達しない関数についての判断」に2行追加(`_destructive_done` / `_release_all_locks`)。機能一覧・統合・昇格の各表は変更なし |
| docs/03-impl/index.md | 1.19.1 → 1.20.0 | relations を反映したときの MINOR 上げ(`/relations` §6-5)。`check-relations.py` と `callgraph-check.py` の最終実行日を 2026-08-11 に更新し、CG3「中」3件の実在確認箇所と未到達4件の記録先を追記。`relations-coverage.py` の「未記載 0 件」が機械の拾える入口に限った主張であることを `docs/issues/097` とともに明記 |
| docs/03-impl/relations/MODULE-cli-logout.md | (版を持たない) | 戻り値欄の 130 の条件を修正。ロック取得より前に張られる `trap`(`claude-dev:452`)により、削除中に限らず列挙・確認プロンプトの区間でも 130 になる |
| docs/03-impl/relations/MODULE-cli-reset.md | (版を持たない) | 同上 |
| docs/03-impl/relations/MODULE-cli-start.md | (版を持たない) | 戻り値欄に 130 を追加。entrypoint の副作用が「`start` を実行すると必ず起きる」を「コンテナを新規に作る経路でだけ起きる」へ修正(稼働中は `claude-dev:1216` で `exit 0` し `docker run` に到達しない)。判断11 の macOS 早期拒否について「副作用は何も起きておらず」を修正(`ensure_project_config` が拒否より前に走る。`claude-dev-mac:1236`-`:1250`) |
| docs/03-impl/relations/MODULE-cli-stop.md | (版を持たない) | 戻り値欄に 130 を追加。手順8 の「先に消えているものへの `docker rm -f` は失敗するが握って続行する」を「二重削除は起きない」へ修正(列挙が削除より後なので消えたものは結果に現れない。`claude-dev:1620`-`:1639`) |
| docs/pendings.md | (版を持たない) | 残務に1行追加。01 層に終了コード 130 の記述が `FR-env-03-23` 以外に無い |

## 実装したもの

| 対象 | 内容 | コミット |
|---|---|---|
| なし | このスキルはコードを変更しない | - |

## 実施した移行

なし

## 機能間連携仕様書の変化

| 種別 | ID | 内容 |
|---|---|---|
| 変更 | MODULE-cli-logout | 戻り値の 130 の条件(`callees` は変更なし) |
| 変更 | MODULE-cli-reset | 同上 |
| 変更 | MODULE-cli-start | 戻り値に 130 / entrypoint 副作用の条件 / macOS 早期拒否の副作用(`callees` は変更なし) |
| 変更 | MODULE-cli-stop | 戻り値に 130 / 手順8 の二重削除の記述(`callees` は変更なし) |
| 変化なし | 他52本 | 内容・frontmatter とも変更なし。本数は 56 のまま(`check-relations.py` 合格・56ファイル / 56 ID) |

## 検討した代替案

| 論点 | 採用した案 | 棄却した代替案 | 棄却の理由 / 崩れる条件 |
|---|---|---|---|
| ファンイン2以上の共有関数14件を昇格させるか | **この実行では判断しない**(`docs/issues/096` へ起票し、人間の合意に委ねる) | この実行で案A(破壊的操作を1機能に統合して昇格 + 4件を個別昇格)を実施する | モジュール境界の変更は `delegation.md` §2 の DS-05「対象外」で AI が決めてよい範囲の外である。加えて昇格は 02-design/relations.md に `PLAN-*` の追加を要するが、`--apply` のケース2 は 02 層への書き込みを許さない(許すのは `--bootstrap` の分割定義節のみ)。**崩れる条件**: 人間が案 A を選んだとき — そのときは `/task-new 096` でタスク化する |
| 未到達の `_destructive_done` / `_release_all_locks` を到達不能コードとして扱うか | 取りこぼしと判定し、削除しないと記録した | 到達不能候補として扱う | `destructive_skipped` が `logout` 本体(`claude-dev:1042`)から呼ばれ、その1行形式の関数定義(`claude-dev:653`)の本体を Tier 3 抽出器が走査しないために辺が立たないことを確認した。`_release_all_locks` は `trap` 文字列(`claude-dev:451-452`)経由で、静的抽出では原理的に見えない |

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 新規 issue | docs/issues/096-modify-fourteen-shared-helpers-with-fanin-2-or-more-are-absent-from-the-feature-table.md | ファンイン2以上の共有関数14件が機能表に記録されていない。破壊的操作のプロトコルは `MODULE-cli-logout` と `MODULE-cli-reset` に記述が重複している(実測4項目) |
| 新規 issue | docs/issues/097-modify-cli-help-dispatch-branch-is-absent-from-the-feature-table.md | CLI の `help\|*)` 分岐(`claude-dev:2183` / `claude-dev-mac:2207`)が機能表に無い。shell 抽出器が入口として拾わないため FT2 も 0 件を報告する |
| 棚上げ | docs/pendings.md 残務(2026-08-11) | 01 層に終了コード 130 の記述が `FR-env-03-23` 以外に無い。利用者から見える値なので 01 へ上げるかは要件側の判断 |
