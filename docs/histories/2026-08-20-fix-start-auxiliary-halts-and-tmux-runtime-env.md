---
id: 2026-08-20-fix-start-auxiliary-halts-and-tmux-runtime-env
date: 2026-08-20
record: docs/build-records/fix-start-auxiliary-halts-and-tmux-runtime-env.md
critical: true
origin_layer: 01
issue: docs/issues/106-bug-two-auxiliary-host-asset-steps-halt-start-under-set-e.md, docs/issues/108-bug-tmux-session-recreated-by-cli-misses-entrypoint-runtime-env.md
summary: 読めないホスト資産で start が止まらないようにし、CLI が作り直す tmux の窓へ entrypoint の実行時の値を届ける
---

# 2026-08-20 `start` の補助処理と、作り直した tmux の窓を直す

## 変更理由

### R-01 ホスト資産を取り込む2つの補助処理が `set -e` で `start` を止めていた(issue 106)

- 起点層・根拠: `NFR-avail-03`(補助機能の失敗が主機能を止めないこと。目標値 100%)。
  01 には「存在しない」場合の条項(`FR-env-02-6`)しか無く、**「存在するのに読めない」場合の
  観測される振る舞いが書かれていなかった**ので、起点は 01 である。
- 変更が必要になった条件: 2026-08-19 の `task-stop-cleanup-and-project-env` が同型を4件直した際、
  以前から在る2箇所(`~/.local/bin` の `cp -a` / `~/.ssh/config` の `mktemp` + `sed`)を
  範囲外として issue に回していた。ホスト側のファイル1つの権限で隔離コンテナが起動しない。

### R-02 ホスト CLI が作り直す tmux の窓に entrypoint の実行時の値が届かなかった(issue 108)

- 起点層・根拠: `FR-env-07-13` / `FR-env-14-11` が「起動経路を問わない」と定めているのに、
  `CTR-cli-container` が到達の義務の受け側を **entrypoint と名指していた**ため、
  ホスト CLI が `docker exec` で tmux サーバを作り直す経路を覆っていなかった(02 起点)。
- 変更が必要になった条件: 稼働中コンテナで tmux サーバが失われると経路2 に入り、
  VM モードの `DOCKER_HOST` と macOS の `SSH_AUTH_SOCK` が窓に届かない
  (`docker exec` はコンテナ作成時の env しか引き継がない)。

## 変更内容の要約

- **R-01**: `~/.local/bin` の `cp -a` を `if !` で握り、`~/.ssh/config` の `mktemp` + `sed` を
  `if` の条件に並べて両方を握った。後者は**加工前の config を代替として渡さない**
  (`IdentityAgent` が残るとコンテナ内で agent が不通になり、除去の理由が消えるため)。
  観測される振る舞いを `FR-env-02-7` / `FR-env-04-9` として 01 へ書いた。
- **R-02**: 契約の義務の主語を「コンテナ内でプロセスの木を新しく起こす側」へ広げ、
  **実行時に決まる環境変数の受け渡し `/etc/claude-dev/runtime.env` を新設**した。
  entrypoint が値を採用した地点で1行ずつ追記し、ホスト CLI の再接続経路が木を起こす直前に読む。

## 更新したドキュメント

| 理由ID | ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|---|
| R-01 | docs/01-requirements/functional.md | 1.21.0 → 1.22.0 | `FR-env-02-7`(読めないホスト資産は取り込まずに表示して続行)と `FR-env-04-9`(SSH クライアント設定の加工済みコピーを作れないとき加工前を渡さない)を新設。どちらも `[DS-02]` の開示行つき |
| R-01・R-02 | docs/02-design/contracts/cli-container.md | 1.15.0 → 1.16.0 | 到達義務の主語を「木を新しく起こす側」へ拡張 / `実行時に決まる環境変数の受け渡し(/etc/claude-dev/runtime.env)` 節を新設 / マウント表とエラーケース表に3行追加 / 削除済み `docs/issues/046` への参照を履歴へ付け替え |
| R-01・R-02 | docs/03-impl/contracts/cli-container.md | 1.11.0 → 1.12.0 | 受け渡しファイルの実装上の事実を1行、ホスト資産の取り込みの握りを1行追加。`~/.ssh/config` の加工行と `DOCKER_HOST` / `SSH_AUTH_SOCK` の行を更新。frontmatter `impl:` に受け側 `scripts/entrypoint-claude.sh::main` を追加 |
| R-01・R-02 | docs/03-impl/relations/MODULE-cli-start.md | (版なし。updated 2026-08-19 → 2026-08-20) | 手順7・11・13 を更新、異常系に3行追加、副作用の順序の 9・11 を更新、既知の制限から issue 106 の行を削除、判断3・4 を更新し `[DS-05]` `[DS-02]` を2行追加。**あわせて残務(2026-08-19)の程度語3箇所を落とした** |
| R-02 | docs/03-impl/relations/MODULE-entrypoint-claude.md | (版なし。updated 2026-08-19 → 2026-08-20) | 手順0(受け渡し先の初期化)を新設、手順5・15 に記録を追記、永続化に `runtime.env` を追加、`[DS-05]` を1行追加 |
| R-01・R-02 | docs/03-impl/tests/cli-start.md | 1.5.1 → 1.6.0 | `FR-env-02-7` / `FR-env-04-9` / `FR-env-07-13` / `FR-env-14-11`(作り直し経路の側)の対応行と未検証行を追加、`[DS-01]` を1行追加 |
| R-02 | docs/03-impl/tests/entrypoint.md | 1.3.0 → 1.3.1 | `FR-env-07-13` / `FR-env-14-11` の対応行に「初回起動の経路の側」であることを明記 |
| R-01・R-02 | docs/03-impl/tests/e2e.md | 1.13.0 → 1.14.0 | E2E-01 に手順9-8・9-9(作り直した窓と、受け渡しファイルが無い構成)と手順11(読めないホスト資産2種)を追加、`[DS-01]` を3行追加 |
| R-01・R-02 | docs/03-impl/index.md | 1.31.0 → 1.32.0 | 「02 との差分」の最後の1件(issue 108)を解消済みにし、実装欠陥の起票数を 5件 → 4件へ |

## 実装したもの

| 理由ID | 対象 | 内容 | コミット |
|---|---|---|---|
| R-01 | MODULE-cli-start | `claude-dev:1553` / `claude-dev-mac:1628` の `cp -a` を `if !` で握る。`claude-dev:1648`-`:1658` / `claude-dev-mac:1739`-`:1749` の `mktemp` + `sed` を `if` の条件に並べて握り、失敗時は加工前を渡さず作りかけを消す | (下記の commit) |
| R-02 | MODULE-entrypoint-claude | `scripts/entrypoint-claude.sh:25`-`:33` に `RUNTIME_ENV_FILE` の初期化と `record_runtime_env` を新設。`:131`(`SSH_AUTH_SOCK`)と `:516`(VM の `DOCKER_HOST`)で採用した値を記録 | (同上) |
| R-02 | MODULE-cli-start | `claude-dev:1474`-`:1476` / `claude-dev-mac:1551`-`:1553` の再接続経路を `sh -c '[ -f … ] && . …; exec tmux new-session -d -s main'` へ | (同上) |

## 実施した移行

| 理由ID | 対象 | 手順(実行したコマンド / スクリプト) | 実行日 | 結果・確認方法 |
|---|---|---|---|---|
| — | なし | なし | — | データ移行・スキーマ変更を伴わない |

### ロールバック・復旧記録

| 理由ID | 不可逆点 | 切り戻し可能な条件・期限 | 切り戻し手順 / forward-fix のみの理由と復旧手順 | 復元元 | 確認日 | 復旧確認コマンド・結果 |
|---|---|---|---|---|---|---|
| R-01 | なし(削除も外部送信も行わない。既存の失敗経路を握るだけで、成功経路の振る舞いは変えていない) | 期限なし。次のコミットでいつでも戻せる | `git revert` のみ。外部副作用が無いので復旧手順を別に要さない | 不要(状態を持たない) | 2026-08-20 | `bash -n claude-dev && bash -n claude-dev-mac` → 構文エラーなし。読めない資産での続行を隔離ハーネスで確認 |
| R-02 | なし(コンテナ内に `0644` の1ファイルを作るだけで、コンテナの削除とともに消える。**秘密は書かない** — 載るのはソケットのパスと Docker API の URL で、いずれも `docker inspect` で既に見える種類の値) | 期限なし | `git revert` のみ。稼働中のコンテナに残る `runtime.env` は次回起動時に entrypoint が空へ戻す | 不要 | 2026-08-20 | `record_runtime_env` の往復(有/無の両方)を隔離ハーネスで確認。ファイルが無い構成でも木が立つことを確認 |

## 機能間連携仕様書の変化

| 種別 | ID | 内容 |
|---|---|---|
| 変更 | MODULE-cli-start | 手順7 が `/etc/claude-dev/runtime.env` を読むようになった(新しい機能は作っていない。`callees` に増減なし) |
| 変更 | MODULE-entrypoint-claude | 手順0 を新設し `runtime.env` を書くようになった(`callees` に増減なし) |

**新しい機能を1本も作っていない**(受け渡しは既存2機能の内部に閉じ、共有基盤へ上げる条件を
満たさない)。`PLAN-*` と `MODULE-*` は 61 対 61 のままである。

## 検討した代替案

| 論点 | 採用した案 | 棄却した代替案 | 棄却の理由 / 崩れる条件 |
|---|---|---|---|
| 作り直した窓へ実行時の値を届ける手段(issue 108 の案 A / B / C) | **C の拡張**: entrypoint が採用した値を `/etc/claude-dev/runtime.env` へ記録し、外から木を起こす側が読む | **A**: CLI が `docker exec -e` で `DOCKER_HOST` / `SSH_AUTH_SOCK` を組み立てて渡す | entrypoint は **VM の起動に成功したときだけ** `DOCKER_HOST` を上書きし、`SSH_AUTH_SOCK` も socat がソケットを作れたときだけ export する。CLI 側は成否を知らないので、**A では失敗時に嘘の値を配る**(中継先が正しい場面でゲスト VM を指す)。崩れる条件: entrypoint が実行時に値を決めるのをやめたとき |
| 同上 | 同上 | **B**: 経路2 をやめ、コンテナ内の1本のスクリプトへ委ねて entrypoint と同じ形で起こす | entrypoint の環境は既にプロセスごと失われているので、**値の出どころを別に用意する必要が残る**(結局 C と同じものが要る)。経路を1本にする利点だけでは、失われた環境を取り戻せない |
| 既存の `/etc/claude-dev/vm.env` に相乗りさせるか | 別ファイル(`runtime.env`)を新設 | `vm.env` に `SSH_AUTH_SOCK` も足して1本にする | `vm.env` は**対話シェルの rc から source される**もので、読む相手も載る値の範囲も違う。混ぜると「対話シェル用」と「外から読む用」の2つの契約が1ファイルに同居する |
| 読めない `~/.ssh/config` の扱い | 何も渡さずに続行する | 加工前の config をそのまま渡す | `IdentityAgent` が残るとコンテナ内で `SSH_AUTH_SOCK` を上書きして agent を不通にする。**除去している理由が、そのまま代替として渡してはならない理由である**(`D0-sec-02`) |
| 読めない `~/.local/bin` の扱い | 読めたぶんだけ取り込んで続行する | 1つでも読めなければ何も取り込まない | `cp -a` は1件の失敗で全体を止めないので、実装として自然なのは「読めたぶんが残る」形である。全か無かにすると、正常なスクリプトまで届かなくなる |

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 解消した issue | docs/issues/106-bug-two-auxiliary-host-asset-steps-halt-start-under-set-e.md(削除) | `pattern: set-e-unguarded-auxiliary-step-halts-start` の残り2件を直した。同型は 0 件になった |
| 解消した issue | docs/issues/108-bug-tmux-session-recreated-by-cli-misses-entrypoint-runtime-env.md(削除) | 契約の義務の主語を広げ、受け渡しファイルで両経路が同じ値を使うようにした |
| 残務(直した) | docs/pendings.md | `MODULE-cli-start.md` の程度語3箇所(「数分」「即座に」×2)を落とした(2026-08-19 の残務) |
| 残務(直した) | docs/pendings.md | 削除済み `docs/issues/046` を指す参照のうち、closure 内の1件(`02-design/contracts/cli-container.md`)を履歴へ付け替えた |
| 残務(持ち越す) | docs/pendings.md | `03-impl/contracts/cli-container.md` のコード引用の行番号ずれ。**本タスクで実測したところ参照は 129 トークン**(ファイル名つき 43 / 裸の `:NNN` 86)で、裸の側は直前の名前つき参照に係るため1件ずつ実コードに当て直すしかない。本タスクが触った行の引用は現在値へ取り直したが、残りをこの closure で全部直すと差分の大半が無関係な機械的入れ替えになる(CLAUDE.md §3 の健全性signal)。次に同ファイルを触るタスクへ持ち越す |
| 残務(持ち越す) | docs/pendings.md | `03-impl/contracts/cli-container.md` の `impl:` の担当範囲。**受け側 `scripts/entrypoint-claude.sh::main` は本タスクで足した**が、残務が問うている `stop` / `logout` / `reset` まで含む範囲の決め方は本 closure の外である |
| 残務(持ち越す) | docs/pendings.md | `03-impl/relations/` の「実装上の判断」の書式が2つある件。全 56 本の一括移行であり、1モジュールの closure で扱う対象ではない |
| 残務(持ち越す) | docs/pendings.md | 01 層に終了コード 130 の記述が無い件。**上げるかどうかは要件側の判断**であり、本タスクは終了コードを1つも変えていない |
