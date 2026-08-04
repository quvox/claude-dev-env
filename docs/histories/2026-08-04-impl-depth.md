---
id: 2026-08-04-impl-depth
date: 2026-08-04
task: task-impl-depth
origin_layer: 01
issue: docs/issues/004-modify-03-impl-lacks-reimplementation-depth.md
summary: 03-impl と契約を「ドキュメントだけから再実装・再試験できる」深度まで掘り下げた(コードは1行も変更していない)
---

# 2026-08-04 03-impl と契約を再実装可能な深度まで掘り下げる

## 変更理由

`docs/issues/004`(03-impl が現状の説明としては正しいが、ドキュメントだけから再実装・再試験できる
深度に達していない)と `docs/issues/008`(契約の深度と測定不能な判定語)を同時に解消するため。
起点層は **01**(境界値・異常系の受入基準が無いこと自体が要件レベルの欠落)。

**コードから一意に読み取れる事実だけを書く**という制約(委任 `D0-scope-07`)の下で行い、
**システムの振る舞いは変えていない**(`git diff -- . ':!docs'` は空)。

## 変更内容の要約

- **01 に境界値・異常系の受入基準を17行追加**(FR-env-06 +5 / FR-orch-03 +4 / FR-orch-04 +3 /
  FR-orch-05 +3 / FR-env-09 +2)。測定不能語(`軽微` / `意味のあるまとまり`)を実装の条件へ置換。
- **契約3件を 02/03 の両側で型・必須性・既定値・異常時の値まで降ろした**。設定キーの実値表、
  プロンプトの構成9要素とフィールド表、環境変数の判定規則(厳密一致の比較対象)、字句規則。
- **relations 21本**に「呼び出され方の受理/拒否」「副作用の順序と回復点」「一貫性境界」
  「並行性と排他」「外部依存が失敗したときの挙動」を追記。`issue 009` (b) の10件を実シグネチャへ訂正。
- **00 に決定2件を新設**(`D0-scope-07` = 深度の停止条件と起票の閾値、`D0-orch-18` = 介入の発火条件)。
- 掘り下げの過程で見つけた**実装の欠陥・要件との不一致は全件 issue へ**(下記「副産物」)。
- 人間の裁定に従い **00 の決定3件を実装に合わせた**(`D0-orch-15` / `D0-sec-10` / `D0-auth-03`)。

## 更新したドキュメント

| ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|
| docs/00-requests/decisions/scope.md | 1.0.0 → 1.1.0 | `D0-scope-07` を新設(深度の停止条件・「持たない」ものの書き方・**起票の閾値と観測点の定義**) |
| docs/00-requests/decisions/orch.md | 1.0.0 → 1.2.0 | `D0-orch-18` を新設(介入の発火条件7行 + 射程)/ `D0-orch-15` の「スキーマ強制」を撤回 |
| docs/00-requests/decisions/sec.md | 1.0.0 → 1.1.0 | `D0-sec-10` に「`--vm` は KVM 必須・無ければ終了コード 1」を追記 |
| docs/00-requests/decisions/auth.md | 1.0.0 → 1.2.0 | `D0-auth-03` の「コンテナローカルへコピー / symlink 不採用」を撤回し実装の形(プロジェクトディレクトリ配下 + symlink)と**残るリスク2点**を明記。`D0-auth-02` のガードレールも同期 |
| docs/01-requirements/functional.md | 1.0.0 → 1.3.1 | 受入基準17行追加 / `FR-orch-06` #3 のスキーマ強制を実装へ / `FR-env-03` #2・#7 の認証の置き場所 / `FR-env-08` #5 に `--vm-fresh` |
| docs/01-requirements/non-functional.md | 1.0.1 → 1.2.0 | `NFR-perf-03` の測定可能化 + 第2文(文脈の絞り方)を設計へ降ろした |
| docs/01-requirements/usecases.md | 1.0.0 → 1.1.0 | `UC-04` 代替フロー A1 の「判断が軽微」を `D0-orch-18` の発火条件で書き直した |
| docs/02-design/architecture.md | 1.0.0 → 1.2.0 | 認証の置き場所(データモデル表・`DSN-auth-01`・`DSN-arch-02`)を実装へ |
| docs/02-design/contracts/cli-container.md | 1.0.0 → 1.2.0 | 環境変数10件の型・判定規則、マウント13件の付与条件、`--kvm`/`--vm` のエラーケース分離 |
| docs/02-design/contracts/cli-orchestrator.md | 1.0.0 → 1.1.0 | 設定9件の型・既定・不正値の扱い + **字句規則**(引用符・行末コメント・入れ子) |
| docs/02-design/contracts/orchestrator-prompt.md | 1.0.0 → 1.2.0 | プロンプト構成9要素・結果/レビュー/制御ファイルのフィールド表・エラーケース17行 + `DSN-prompt-03` |
| docs/03-impl/contracts/cli-container.md | 1.0.0 → 1.2.0 | 起動列の実値(`path:line` 付き)・厳密一致の判定・再試行20回の条件 |
| docs/03-impl/contracts/cli-orchestrator.md | 1.0.0 → 1.1.0 | 設定キーの実値表(適用条件と満たさないときの結果)+ 字句解釈の実測結果 |
| docs/03-impl/contracts/orchestrator-prompt.md | 1.0.0 → 1.1.0 | 結果 JSON の走査規則・打ち切り回数・秘密情報の除去を実値で |
| docs/03-impl/index.md | 1.1.0 → 1.5.0 | 層の状態(乖離・起票済み issue)・02 との差分4件・**01 との差異**節を新設 |
| docs/03-impl/infra/local/ghcr.md | 1.0.0 → 1.1.0 | 取得失敗の切り分け表(症状 → 原因 → 対処)と部分取得の帰結 |
| docs/03-impl/relations/(21本) | 版なし(層の代表は index) | 入力検証・境界値 / 副作用の順序と回復点 / 一貫性境界 / 並行性と排他 / 外部依存の失敗 / `issue 009` (b) の訂正 |
| docs/03-impl/tests/cli-forward.md ほか5件 | 各 MINOR | 追加した受入基準の行(状態は「未検証(テスト未実装)」)と `tests/strategy.md` のカバレッジ現状値 180 |
| docs/02-design/logging.md | 変更なし | 深度は足りていた。実装が満たしていない差分は `issue 013` / `014` へ |

## 実装したもの

| 対象 | 内容 | コミット |
|---|---|---|
| (なし) | **このタスクはコードを1行も変更していない**(DoD 1項目目)。`git diff -- . ':!docs'` が空であることを実測 | — |

## 機能間連携仕様書の変化

| 種別 | ID | 内容 |
|---|---|---|
| 追加 | (なし) | 機能表に追加した行は無い(`propose-features.py` の FT2 = 0 件) |
| 変更 | MODULE-cli-forward / -unforward / -start / -stop / -reset / -logout / -pull | 引数の受理/拒否、副作用の順序と回復点、並行性(**排他機構が無い事実**)、外部依存の失敗 |
| 変更 | MODULE-orchestrator-worktree / -state-io / -controller / -state-intervention | `taskID` の未検証、原子性の境界(1ファイル1書き込み)、`planMu`/`mergeMu`、壊れた `open.json` の帰結 |
| 変更 | MODULE-orchestrator-slack / -claude-exec / -pull | タイムアウト・再試行・バックオフの有無、API レベルの失敗を検出しないこと |
| 変更 | MODULE-orchestrator-session / -worker / -mode / -review / -term / -handoff / -streamlog / -trigger | `issue 009` (b) の実シグネチャ、`D0-orch-18` の発火条件7行、記述誤りの訂正 |
| 削除 | (なし) | — |

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 新規 issue(実装の欠陥) | docs/issues/010 / 011 / 012 / 013 / 020 / 021 / 022 / 023 / 024 / 025 / 026 / 028 / 029 | ポート選択の競合 / taskID 未検証 / `reviewer_vendor` 無効 / Slack の API 失敗を検出しない / CLI に排他が無い / store にロックが無い / `merge_strategy` 未検証 / SSH ブリッジポート未検証 / `stop` が他プロジェクトの compose を消す / `logout`・`reset` が消えていないのに成功と表示 / 状態保存の失敗を握りつぶす / 名前の一意性が `NFR-scale-01` 未達 / `logout` が確認なしで全プロジェクトを落とす |
| 新規 issue(**重大度 高**) | docs/issues/036 | **`start` の失敗時の後片付けが同名の稼働中コンテナを作業中の tmux ごと削除する(データ破壊)。次タスクで優先修正** |
| 新規 issue(ドキュメント) | docs/issues/014 / 017 / 019 / 030 / 031 / 032 / 033 / 038 / 041 / 042 / 043 | 追記型ログの必須フィールド / 測定不能語の残存 / 実在しないテスト識別子 / index の完全性の主張 / 監査レンズのモデル未定 / 範囲外 relations の乖離18件 / 題材の pytest が常に失敗 / **範囲内 relations の乖離27件** / ブロック対象ドメイン未定義 / `AC-02` の A0 不整合 / NFR の測定欠落 |
| 気づき | docs/feedbacks/013 / 014 / 015 / 016 | 裁定は起点層から降ろす / 自分で記録した事実を適用し忘れる(`set -e`)/ 範囲の最小化は次の検証で再浮上する / 「追跡済み」は「裁定済み」ではない |
| 解消した issue | docs/issues/008 / 016 / 018 / 034 / 035 / 037 / 039 / 040(削除) | 契約の深度と判定語 / forward の成功表示(受入基準を精密化)/ `--vm` の中止が 02 に無い / レビューのスキーマ強制 / `NFR-perf-03` 第2文 / pull の部分成功(② は `set -e` により誤検知)/ 00 が 01 の精密化に追随していない / 認証の置き場所 |
| 残した issue | docs/issues/004 / 009 | **004**: 観点1〜5と観点7は解消。残件は永続データモデルの記述・モデル/effort ポリシー・観点6(テストデータ)。**009**: (a) の規約(`/kit-improve` 案件)と引数表3件 |
| キット改善 | .claude/improvements/KIT-restore-shell-make-after-kit-update.md(適用済み) | キット更新で巻き戻った shell/make 抽出を再適用し、**本流へ渡すパッチを書き出した** |

## ★2026-08-04 追記: フェーズ4 の完了時に人間から直接得た裁定

**この節は memo.md が削除されても残る恒久記録である。** これまでの実行が「呼び出し元の申告」として
扱ってきた回答と違い、以下は**人間が本セッションで直接回答したもの**である
(`task-impl-depth` の決定シート論点5 が求めていた本人確認)。提示に先立って、各論点の
**上流・同層・下流のドキュメントとコードを再照合した**(前の実行の記録は根拠にしていない)。

| # | 論点 | 回答 |
|---|---|---|
| 1 | 00層の意味を変える3件の承認: `D0-orch-15`(レビュー結果の**スキーマ強制を撤回**)/ `D0-sec-10`(`--vm` / `--vm-fresh` は `/dev/kvm` 必須、無ければ終了コード 1)/ `D0-auth-03`(認証はホストの**プロジェクトディレクトリ配下へコピー + symlink 参照**) | **承認**。3件とも 00 → 01 → 02 → コードまで整合していることを再確認した(`orchestrator/review.go:66`,`:115`,`:182` / `claude-dev:703`,`:709`,`:858`〜`:861` / `claude-dev:749`〜`:766` と `scripts/entrypoint-claude.sh:199`,`:212`) |
| 1b | 上記に伴い、`D0-auth-03` が自認する残リスク2件(**認証情報がホストのプロジェクト配下に平文で存在する** / **`~/.claude.json` がファイル単位 symlink でアトミック書き込みに壊されうる**)の受容記録が**どこにも無かった**(原則8 の宛先が空) | **`docs/pendings.md` P-004 として受容を明文化**(なぜ今 OK か・どうなったら解消が必要かを含む) |
| 2 | `docs/issues/044`(`terminology.md` 1.1.0 の「資源逼迫」の閾値定義に承認の記録が無い) | **案A′ = 承認 + 微修正**(00 からは環境変数名を落とし「既定値。上書き手段は 03-impl」とする)。**下降(`FR-env-08` #4 と 02 の5箇所、`issue 017` からの除去、合格証の発行)は次タスクで実施** — closure 外の SSOT を変更指示なしで書き換えることは 044 が問題にした逸脱そのものになるため。severity は 高 → **中** |
| 3 | 削除ゲート (b) が `docs/03-impl/features.md` を「version がない」で落としていた | **`/kit-improve` で `close-task.py` の例外リストに `features.md` / `feature-graph.md` を追加**(規範 `.claude/directions/features.md:125`,`:134`〜`:135`,`:206` は「版・合格証を持たない」と明記済みで、**追随していないのは実装だけ**)。検討メモ `.claude/improvements/KIT-close-task-versionless-docs.md` |
| 4 | 残る「中」の指摘の束ね方 | **次タスクを2本に分ける**。① **仕様の測定可能性** = `issue 043` + `017` + `041`(**案D**)+ `042` + `044` の下降(要件層の判断を含むので決定シートが必要)/ ② **relations をコードへ全面追随** = `issue 038` + `032` + 契約(機械照合中心で無人で回せる) |

**この再照合で新たに確定した事実**(いずれも該当 issue へ追記済み):

- **`issue 044` の前実行の推奨 C は成立しない。** `.claude/directions/00-requests.md:52` が用語集について
  「定義が揺れる語を残すな」と定め、現行 1.1.0 は既に「既定・環境変数で上書き可」と書いており、
  なにより **C の受け皿が 02 に存在しない**(`02-design/logging.md:88` の第3列はログの内容欄で
  定義の置き場ではない)。→ `docs/feedbacks/017` に一般化した教訓を記録。
- **`issue 041` の A/B/C は前提がずれていた。** 実装のブロックリストは
  `scripts/init-firewall-claude.sh:37`「ここにブロックしたいドメインを追加してください」+ 既定20件
  (paste系9 / webhook系3 / トンネル系4 + 本番の雛形はコメントアウト)という
  **利用者が編集する前提のテンプレート**である。論点は集合の妥当性ではなく
  「01 が『設定で与えられる集合』と書いていない」こと。→ **案D** を追記。
- **`issue 042` は起票時より強い指摘である。** `claude-dev:695` の `USE_VNC=1` は**既定**で、
  `:846`〜`:848` が `-p <6080番台>:6080` を必ず付ける。`AC-02` の期待結果は既定構成で反例が出る
  (不合格条件は「意図せず」なので破れていない)。案A で振る舞いを変えずに解消できる。
- **`issue 038` の残件は実在する。** 例: `MODULE-orchestrator-term.md:48`,`:61` は今も
  `selectMenu` の引数を「`options` = 文字列の並び」、`rawKeyMode` / `ttyRestoreSane` / `sttyRun` を
  「エラーを返す」と書くが、`orchestrator/term.go:96`,`:34`,`:44`,`:48` は
  `items []menuItem` / `(func(), bool)` / 戻り値なし / `bool` である。一方**「高」5件の解消は本物**
  (`MODULE-orchestrator-controller.md:174` の `errSuspended` 吸収、
  `MODULE-orchestrator-review.md:34`〜`:38` の「`severity` の値域を検証しない」)。
- **issue の削除ステップは 10:23 の `/task-close` で完了していた。** その後の `/doc-check` 3実行が
  「削除ステップは未了」と書き続けていたのは、前の実行の文をそのまま引き継いだ陳腐化である
  → `.claude/improvements/KIT-stale-carry-forward-of-remaining-work.md` に起票。

## ★2026-08-04 追記: フェーズ4 再開時に実測した機械検査(DoD の裏付け)

| # | 検査 | 結果 |
|---|---|---|
| 1 | `build-callgraphs.py --check` | 最新(再生成しても差分なし) |
| 2 | `cluster-features.py --check` | 最新 |
| 3 | `callgraph-check.py` | **重大度「高」0 件**(中3 / 低17 / 参考20) |
| 4 | `check-relations.py` | 合格(82 ファイル / 82 ID) |
| 5 | `check-contracts.py` | 合格(02-design 5件 / 03-impl 5件。REST なし) |
| 6 | `relations-coverage.py` | 終了コード 1。未記載 30 件は**全件が `scan-entrypoints.py` の Go `switch` 誤検出**(設定キー9件 / TUI キー入力 / JSON 型識別子 / `case "rebase"`)。実在する入口の漏れはゼロ |
| 7 | `build-index.py --check` | 差分なし |
| — | `git diff --stat -- . ':!docs'` | **空**(コードは1行も変更していない) |
| — | `close-task.py --check` | (a) 反映済み 39/39 / (b) 影響範囲 52 件のうち 51 件 OK・`features.md` のみ不合格(→ 論点3)/ (d) `check-relations` 合格 |
