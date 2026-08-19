---
id: 2026-08-19-fix-tmux-server-drops-reserved-env
date: 2026-08-19
task: task-fix-tmux-server-drops-reserved-env
lane: standard
origin_layer: 01
issue: docs/issues/107-bug-project-env-file-values-do-not-reach-tmux-windows.md
summary: tmux セッションを su -l で起こすのをやめ、コンテナへ渡した環境変数が tmux の窓の中の全プロセスから参照できるようにした
---

# 2026-08-19 tmux の窓へコンテナの環境が届かない欠陥を直す

## 変更理由

### R-01 tmux の窓の中から Docker が使えず、compose 資源が既定名へ落ちていた

`entrypoint` が tmux セッションを `su "$USERNAME" -s /bin/zsh -l -c "…"` で起こしていた。
**`su -l` はログイン用に環境を作り直すので、`docker run -e` で渡した変数もイメージの `ENV` で
付いた変数もまとめて捨てる。** tmux サーバの環境はその配下の全ウィンドウ・全プロセスが継承するため、
tmux の窓からは `DOCKER_HOST` / `COMPOSE_PROJECT_NAME` / `container` / `NODE_OPTIONS` /
`CLAUDE_DEV_*` が1つも見えなかった。結果として:

- 窓の中の `docker` が `unix:///var/run/docker.sock` を見に行って失敗する
  (`FR-env-07` の内容「コンテナ内から Docker を使える」/ `FR-env-07-1` を主経路で満たさない)
- 全プロジェクトが `/workspace` にマウントされるため、`COMPOSE_PROJECT_NAME` を失った窓では
  compose 既定名が `workspace` に落ち、**プロジェクト間で確実に衝突する**(`FR-env-07-5`)

`SSH_AUTH_SOCK` と `DISPLAY` だけが届いていたのは、`tmux` の `update-environment` の既定値8個に
その2つが含まれていたという**別の理由**による。本システムの主たる使い方は tmux の窓の中で
`claude` / `codex` を動かすこと(`FR-env-01-1` / `UC-01` 基本フロー4)なので、
主経路が満たされていない状態だった。

### R-02 env ファイルに書いた値も届かず、`AC-08` が実機に対して不合格だった

同じ `su -l` が、`.claude-dev.yaml` の `env_file:` で渡した組も落としていた。
`AC-08`(プロジェクトごとの環境変数がコンテナ内のツールに見える)の操作4 は
「**立ち上がった端末の中で**、書いた名前の環境変数を表示する」で、`claude-dev start` が
アタッチするのは tmux なので、その端末は tmux の窓である。不合格の条件として `AC-08` 自身が
「書いた値がコンテナの中で見えない」を挙げている。**2026-08-19 に実機で測り、不合格であることを
確認した**(`docs/issues/107`)。`docker exec` 経由では見えるため、確認の仕方によって合格に
見えるのが厄介だった。

### R-03 03 の記述4箇所とコード注釈5箇所が事実と違っていた

- `MODULE-cli-start` 実装上の判断3:「`-e` なら対話・非対話シェルと `docker exec` の全てで有効」
- `MODULE-entrypoint-claude` 手順5〜7: 初期化ファイルへの追記が「全シェルで有効にする」
- `03-impl/contracts/cli-container.md` の `SSH_AUTH_SOCK` 行: 同上
- `claude-dev` / `claude-dev-mac` / `scripts/entrypoint-claude.sh` のコード注釈

いずれも `su -l` を越えられないという事実を落としていた。**原則2 によりコードを正として直した。**

## 変更内容の要約

tmux セッションを起こす `su` から **`-l` を外した**。列挙して載せ直す形は採らない —
変数が増えるたびに列挙も増やす必要があり、増やし忘れが `AC-08` の不合格として現れた経路そのもの
だからである。あわせて 01 に条項を2つ新設し(`FR-env-07-13` / `FR-env-14-11`)、
02 の契約に到達の義務を書き、03 に機構と実測を書き、E2E-01 に手順9(7項目)を新設した。

## 更新したドキュメント

| ドキュメント | version 遷移 | 変更点(R-ID) |
|---|---|---|
| `docs/01-requirements/functional.md` | 1.19.1 → 1.20.0 | `FR-env-07-13`(R-01)と `FR-env-14-11`(R-02)を新設。両要件の内容に到達保証の1文。`FR-env-07` の分割可否を「他の12条項は不可分」へ |
| `docs/02-design/contracts/cli-container.md` | 1.13.0 → 1.14.0 | 「渡す環境変数」に到達の義務を追記。**初期化ファイルへの書き出しはこの義務を果たさない**ことを明記(R-01 / R-02)。対応要件に `FR-env-14` |
| `docs/02-design/system.md` | 2.15.0 → 2.16.0 | 要件カバレッジ表に2条項(主担当 `MOD-entrypoint`)。`MOD-entrypoint` の対応要件に `FR-env-14`。「分割の根拠」7件を読み直して継続(R-01 / R-02) |
| `docs/02-design/relations.md` | 1.11.1 → 1.11.2 | `PLAN-entrypoint-claude` の要件に `FR-env-14`(R-02) |
| `docs/01-requirements/decisions/split.md` | 1.5.0 → 1.5.1 | `D1-split-01` の「他の11条項」→「他の12条項」(R-01) |
| `docs/03-impl/contracts/cli-container.md` | 1.10.0 → 1.11.0 | `SSH_AUTH_SOCK` 行の誤りを訂正し、tmux サーバがコンテナの環境を引き継ぐ行を新設(R-01 / R-03) |
| `docs/03-impl/relations/MODULE-entrypoint-claude.md` | 層代表(下記) | 手順5・6・7・15・20 を書き直し。`[DS-05]` を**更新**、`[DS-02]` を**削除**(R-01 / R-02 / R-03) |
| `docs/03-impl/relations/MODULE-cli-start.md` | 層代表(下記) | 実装上の判断3 の誤った断定を事実へ(R-03) |
| `docs/03-impl/tests/entrypoint.md` | 1.2.1 → 1.3.0 | 2条項の対応行と未検証一覧の 24・25 行目(R-01 / R-02) |
| `docs/03-impl/tests/e2e.md` | 1.11.0 → 1.12.0 | E2E-01 に**手順9(7項目)**を新設。対応表のシナリオ欄。`[DS-01]` を1行(R-01 / R-02) |
| `docs/03-impl/index.md` | 1.29.1 → 1.30.0 | 層代表の版(relations 2本を代表)。「02 との差分」を更新 |

## 実装したもの

| 対象 | 内容(R-ID) |
|---|---|
| `scripts/entrypoint-claude.sh` | tmux セッションを起こす `su` から **`-l` を外した**(R-01 / R-02)。`SSH_AUTH_SOCK`(macOS 経路)と VM モードの `DOCKER_HOST` を entrypoint 自身の環境へも `export`(R-01)。コード注釈3箇所を事実へ(R-03) |
| `claude-dev` / `claude-dev-mac` | `COMPOSE_PROJECT_NAME` を `-e` で渡す箇所のコード注釈を事実へ(R-03) |

コミット: `44278fe`(実装・フェーズ3)。

## 実施した移行

**なし。** データもスキーマも触っていない。

### ロールバック・復旧記録

**適用外(`lane: standard`)。** 不可逆な点は無い — 環境変数の受け渡し経路だけを変えており、
破壊も移行も外部副作用も起こさない。戻すなら `scripts/entrypoint-claude.sh` の該当行に `-l` を
戻して `claude-dev start`(コンテナ再作成)するだけで、復元元は git である。

## 機能間連携仕様書の変化

**増減なし。** `PLAN-*` と `MODULE-*` は 61 対 61 のまま、機械が出した辺も 88 本で反映の前後に
増減が無い。変更は既存の `MODULE-entrypoint-claude` の内部に閉じており、新しい機能を1本も
作っていない。`propose-features.py` の FT1 / FT2 はどちらも 0 件。

## 検討した代替案

| 論点 | 採用した案 | 棄却した代替案 | 棄却の理由 / 崩れる条件 |
|---|---|---|---|
| 論点1: 01 に「起動経路によらず届く」を条項として書き足すか | **A: 書き足す** | B: 要件は今のまま、02 と 03 だけ直す | B だと**この保証を検証する行がどこにも生まれない**。今回の抜けが残っていたのは、まさに検証する行が無かったためである。崩れる条件: 本システムが tmux を使わなくなったとき |
| 論点2: env ファイルの値も届けるか、どの直し方にするか | **B: `su` から `-l` を外す** | A: 予約名 + 利用者の組を列挙して載せ直す / C: 予約名以外もすべて載せ直す | A と C は載せ直す名前を entrypoint が知る手段が要り、**変数が増えるたびに列挙も増やす必要がある**。増やし忘れが `AC-08` の不合格として現れた経路そのものである。崩れる条件: コンテナに渡る変数の中に tmux の窓へ渡してはならないものが現れたとき |
| `[DS-05]` 実現方法(フェーズ2 の初版) | (更新) `-l` を外す | `-l` を残して予約名を列挙して載せ直す | 初版はこれを採り、「`-l` を外すと `PATH` / `HOME` / 作業ディレクトリまで同時に変わる」を理由に `-l` を外す案を退けていた。**実機で両方を並べて測ると `PATH` も `HOME` も同一**で、この理由は事実として誤りだった(違うのは `PWD` だけで、コマンドが自分で `cd` する)。原則2 によりコードを正として更新した |
| `[DS-02]` エラー処理(フェーズ2 の初版) | (削除) | 載せ直しの非ゼロ終了で `set -e` が初期化を止めないよう握る | 列挙をやめたので握る対象そのものが消えた |
| `[DS-01]` 実機確認手順の置き場 | 手順8 の部分手順にせず、**手順9 として末尾に足す** | 手順8 の部分手順にする | 手順8 は破壊的操作を通しで確かめる一続きの手順で、セッション `aaa` を作って壊す前提を共有している。環境変数の到達確認はその前提を要さない。**末尾に足すので既存の手順番号が1つも動かない** |

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 知見 | `docs/feedbacks/031-a-narrower-fix-can-certify-itself-while-the-acceptance-criterion-still-fails.md` | 人間が「env ファイル機能と干渉しないか」と問うたことで `AC-08` の不合格が判明した。一般化: **上流がある集合を定義していることは、守備範囲をそこで切ってよい根拠にならない**(予約名の集合は「利用者に差し替えさせない名前」という別目的の集合だった)。**却下する理由は、退ける前に測る**(`-l` を外すと `PATH`/`HOME` が変わるという理由は1分の測定で覆った)。**検証の経路が本番の経路と違うと壊れたまま合格する**(`docker exec` では見えるが tmux の窓では見えなかった)。エラー処理・テスト・ログ・設定の4領域に該当する回答は無かったので `decisions/` へは書かない |
| 新規 issue | `docs/issues/108-bug-tmux-session-recreated-by-cli-misses-entrypoint-runtime-env.md` | ホスト CLI が作り直す tmux セッションは entrypoint が実行時に `export` した値(VM の `DOCKER_HOST` / macOS の `SSH_AUTH_SOCK`)を引き継がない。severity 中 / origin_layer 02。**人間の裁定で本タスクへは畳み込まない**(`AC` を落とさず、`/task-new 108-…` でいつでも起こせる) |
| 解消した issue | `docs/issues/107-...`(削除) | `closes_when`(env ファイルの組が tmux の窓で `printenv` で見え、E2E-01 手順9-6 が合格)を**実機で満たした** |
| 残務 +3 | `docs/pendings.md` | `.gitignore` が `.DS_Store` を無視していない / `claude-dev stop` のフラグを名前より前に書くとフラグが名前と解釈され、セッションが止まらないまま終了コード 0 になる(**仕様違反ではない**)/ 02 の SR 行19件が充足欄に `-` を書いている |
| 気づき | `docs/feedbacks/031-...` | 上記「知見」と同じファイル |

### closure に載る残務の裁定(`issues-pendings.md` §2.1)

<!-- 各行の先頭に、`docs/pendings.md` の残務行を一意に指す**照合キー**(その行の3番目のトークン)を
     そのまま置いている。close-task.py 条件 (h) はこの文字列で裁定の有無を判定する。 -->

照合キーの一覧(裁定は下表):
`**`docs/03-impl/relations/MODULE-cli-start.md`:程度語が2箇所ある**:` /
`**`docs/02-design/system.md`「要件カバレッジ確認」の主担当が複数モジュールの行がある**:` /
`docs/03-impl/contracts/cli-container.md` / `docs/03-impl/tests/e2e.md` /
`**issue` 006 の残件 / `**旧表記「受入基準` N」の残り 61 箇所 /
`**`docs/02-design/system.md`「要件カバレッジ確認」の` SR 行19件

| 残務(記録日) | 裁定 |
|---|---|
| `MODULE-cli-start.md` の程度語2箇所(`:32` / `:266`)(2026-08-19) | **持ち越す** — 本タスクが改訂したのは「実装上の判断」3 の1行だけで、指摘の2箇所はその節の外。数値を入れるか語を落とすかは、その節を実際に直すタスクの判断である |
| `02-design/system.md` カバレッジ表の主担当が複数の行(2026-08-19) | **持ち越す** — 本タスクが足した2行はどちらも主担当が1つ。指摘対象の8行は非機能要件で、主担当を1つに決めるのは非機能のカバレッジを見直す判断であり範囲外 |
| `03-impl/contracts/cli-container.md` の `impl:` が起動側だけを挙げている(2026-08-11) | **持ち越す** — 本タスクは「実装上の事実」表の2行を直しただけで frontmatter に触れていない。契約の担当範囲の書き方を決めるのは別の判断 |
| `tests/e2e.md` E2E-01 手順8-3 の「すぐに」(2026-08-11) | **持ち越す** — 手順8 は1箇所も触っていない |
| issue 006 の残件(E2E の実施手順に固定入力・観測点・合否判定・後始末が揃っていない)(2026-08-12) | **持ち越す** — 新設した手順9 はその4つを揃えているが、既存の手順1〜8 は揃っていない。全体を揃えるのは E2E を横断で触るタスクの仕事 |
| 旧表記「受入基準 N」の残り 61 箇所(2026-08-12) | **持ち越す** — 新設した手順9 は条項 ID で書いたが、既存の43箇所は範囲表記を含み、**範囲を条項 ID で書く規約が未定**である |
| `tests/e2e.md` E2E-01 手順7-3 の「すぐに」(2026-08-19) | **持ち越す** — 手順7 は1箇所も触っていない |
| `02-design/system.md`「モジュール分割定義」と 02 契約「対応要件」が `FR-env-14` を欠く(2026-08-19) | **直した** — `/doc-check ssot` が `system.md` の `MOD-entrypoint` 行、`contracts/cli-container.md` の対応要件、`relations.md` の `PLAN-entrypoint-claude` の3箇所へ `FR-env-14` を足した。残務行は削除した |

### 計測(`task-metrics.py report`)

`lane: standard` / 経過 11,718 秒 / 記録イベント: `start intake` ×2。
フェーズ1〜4 を1セッションで通し、**フェーズ3 まで進んだあと人間の裁定で範囲を広げてフェーズ1 へ戻り、
フェーズ2〜4 をやり直した**(`/doc-check` は task モード2回 + ssot モード1回、いずれも独立レビューは
Codex `gpt-5.6-sol` / effort high)。
</content>
