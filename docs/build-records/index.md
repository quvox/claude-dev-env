# 構築記録 一覧

<!-- このファイルは build-index.py が生成する。手書きしない。 -->

<!-- BEGIN GENERATED: build-index.py -->

| slug | 状態 | critical | 更新 | 概要 |
|---|---|---|---|---|
| cleanup-retired-changeset-kit-records | verified | false | 2026-08-20T05:43:36+00:00 | 規約刷新で廃止された変更指示系スクリプト・規範に紐づくキットパッチ・残務・issue を後始末する |
| delete-issue-102-per-human-adjudication | verified | false | 2026-08-20T05:43:36+00:00 | 人間の裁定により issue 102 を削除し、102 を参照している索引・03 層の集計・残務行を整合させる |
| delete-issue-110-per-human-adjudication | awaiting-verify | false | 2026-08-20T14:22:00+09:00 | 人間の裁定により issue 110 を削除し(closes_when は未充足)、110 を参照している 03 層の集計文と生成索引を整合させる |
| document-codex-sandbox-preconditions | verified | true | 2026-08-20T05:43:36+00:00 | コンテナで codex を起こす側が前提にしてよい環境を実測して 02 に明文化し、bwrap の非ゼロを故障と読む誤りを断つ |
| fix-fr-env-07-13-owner-and-codex-sandbox-defaults | awaiting-verify | true | 2026-08-20T15:40:00+09:00 | F2 の独立レビューが挙げた「高」2件(FR-env-07-13 の担当根拠と契約の正面衝突、codex サンドボックス既定と 02 の記述の不一致)を 02-design 側で直す修繕 |
| fix-make-status-hides-docker-query-failure | verified | false | 2026-08-20T05:43:36+00:00 | make status が docker への問い合わせの失敗を0件と同一視する欠陥を直し、claude-dev list と同じ警告行を出す |
| fix-session-list-undercount | verified | true | 2026-08-20T05:43:36+00:00 | list / make status / make clean の Claude コンテナ列挙を、イメージ由来から「管理ラベル ∪ イメージ ∪ 固定接頭辞」へ改める |
| fix-start-auxiliary-halts-and-tmux-runtime-env | verified | true | 2026-08-20T05:43:36+00:00 | start の補助処理2つを握って起動を止めないようにし、CLI が作り直す tmux の窓へ entrypoint の実行時の値を届ける |

件数: 8

<!-- END GENERATED: build-index.py -->
