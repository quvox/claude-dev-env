# 構築記録 一覧

<!-- このファイルは build-index.py が生成する。手書きしない。 -->

<!-- BEGIN GENERATED: build-index.py -->

| slug | 状態 | critical | 更新 | 概要 |
|---|---|---|---|---|
| bundle-chrome-devtools-mcp | verified | false | 2026-09-01T05:56:12+00:00 | chrome-devtools MCP を配布イメージへピン留めで同梱し、claude と codex の双方から実行時ダウンロードなしで使えるようにする |
| cleanup-retired-changeset-kit-records | verified | false | 2026-08-20T05:43:36+00:00 | 規約刷新で廃止された変更指示系スクリプト・規範に紐づくキットパッチ・残務・issue を後始末する |
| delete-issue-102-per-human-adjudication | verified | false | 2026-08-20T05:43:36+00:00 | 人間の裁定により issue 102 を削除し、102 を参照している索引・03 層の集計・残務行を整合させる |
| delete-issue-110-per-human-adjudication | verified | false | 2026-08-20T06:26:50+00:00 | 人間の裁定により issue 110 を削除し(closes_when は未充足)、110 を参照している 03 層の集計文と生成索引を整合させる |
| docs-ux-migrate | awaiting-verify | false | 2026-09-06T09:41:00+09:00 | 移行 2026-08-28-docs-ux を当て、02-design/system.md の UI設計節の中身を docs/ux/ へ引っ越す |
| document-codex-sandbox-preconditions | verified | true | 2026-08-20T05:43:36+00:00 | コンテナで codex を起こす側が前提にしてよい環境を実測して 02 に明文化し、bwrap の非ゼロを故障と読む誤りを断つ |
| facts-json-close | verified | false | 2026-09-11T11:52:08+00:00 | 事実の宣言 docs/facts.json を、宣言する事実0件として置き、移行 2026-08-27-facts-json を閉じる |
| fix-fr-env-07-13-owner-and-codex-sandbox-defaults | verified | true | 2026-08-20T07:01:50+00:00 | F2 の独立レビューが挙げた「高」2件(FR-env-07-13 の担当根拠と契約の正面衝突、codex サンドボックス既定と 02 の記述の不一致)を 02-design 側で直す修繕 |
| fix-make-status-hides-docker-query-failure | verified | false | 2026-08-20T05:43:36+00:00 | make status が docker への問い合わせの失敗を0件と同一視する欠陥を直し、claude-dev list と同じ警告行を出す |
| fix-session-list-undercount | verified | true | 2026-08-20T05:43:36+00:00 | list / make status / make clean の Claude コンテナ列挙を、イメージ由来から「管理ラベル ∪ イメージ ∪ 固定接頭辞」へ改める |
| fix-start-auxiliary-halts-and-tmux-runtime-env | verified | true | 2026-08-20T05:43:36+00:00 | start の補助処理2つを握って起動を止めないようにし、CLI が作り直す tmux の窓へ entrypoint の実行時の値を届ける |
| gitignore-recovery | verified | true | 2026-09-11T11:52:08+00:00 | .claude/ 配下が git に1件も追跡されていない状態を、許可リスト方式で直す(認証情報は除外を維持) |
| pyenv-nvm-in-claude-image | verified | false | 2026-09-01T05:56:12+00:00 | claude イメージの base ステージへ pyenv の3系統(3.11.11/3.13.14/3.14.7)と nvm v0.40.6(Node 22/24/26 系列の最新)を入れる |
| releases-decision | awaiting-verify | false | 2026-09-06T09:36:00+09:00 | リリース台帳 .claude/state/releases.json を新設するかを人間に問い、その答えのとおりに閉じる |
| repair-entrypoint-config-writes | verified | false | 2026-09-01T05:56:12+00:00 | 起動処理が /workspace 配下の設定を書くときの一時ファイルと chown を安全な形へ揃え、登録の有無の判定を値の真偽からキーの有無へ直す |

件数: 15

<!-- END GENERATED: build-index.py -->
