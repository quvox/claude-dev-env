---
slug: fix-start-auxiliary-halts-and-tmux-runtime-env
state: building
critical: true
origin: derived
issue: docs/issues/106-bug-two-auxiliary-host-asset-steps-halt-start-under-set-e.md, docs/issues/108-bug-tmux-session-recreated-by-cli-misses-entrypoint-runtime-env.md
started: 2026-08-20T09:56:00+09:00
updated: 2026-08-20T09:56:00+09:00
commit: ->
summary: start の補助処理2つを握って起動を止めないようにし、CLI が作り直す tmux の窓へ entrypoint の実行時の値を届ける
---

# fix-start-auxiliary-halts-and-tmux-runtime-env — `start` の補助処理と作り直した tmux の窓を直す

## 目的・やらないこと

- 目的: issue 106(`~/.local/bin` のコピーと `~/.ssh/config` の加工が `set -e` で `start` を
  止める)と issue 108(ホスト CLI が作り直す tmux の窓に、entrypoint が実行時に export した
  `DOCKER_HOST` / `SSH_AUTH_SOCK` が届かない)を、`MODULE-cli-start` の同じ closure で直す。
- やらないこと: `start` 分岐の他の補助処理の再走査(issue 106 の `pattern_survey` が
  2026-08-19 に全件走査済みで、握られていないのはこの2つだけと確定している)。経路2 の
  `tmux new-session` に `-f ~/.tmux.conf` や `exec zsh -l` を足すこと(環境の到達とは別の話で、
  どちらの issue も求めていない)。`/tmp/claude-dev-ssh-config.XXXXXX` が消えない件
  (既知の制限として既に記録済み。本タスクの2件に含まれない)。

## 影響範囲(closure)

- docs/01-requirements/functional.md
- docs/02-design/contracts/cli-container.md
- docs/03-impl/contracts/cli-container.md
- docs/03-impl/relations/MODULE-cli-start.md
- docs/03-impl/relations/MODULE-entrypoint-claude.md
- docs/03-impl/tests/cli-start.md
- docs/03-impl/tests/entrypoint.md
- docs/03-impl/tests/e2e.md
- docs/03-impl/index.md
- claude-dev
- claude-dev-mac
- scripts/entrypoint-claude.sh

## 主張

- 触ったモジュールのテスト: **自動テストは存在しない**(`MODULE-cli-start` / `MODULE-entrypoint-claude`
  はどちらも `tests: なし(未実装)`。シェル実装のため自動テストランナーが無く、実機確認で代替する
  方針 — `DSN-test-01` / `SR-32`)。代わりに**実イメージで確認した**:
  `docker exec -u <user> <name> sh -c '[ -f /etc/claude-dev/runtime.env ] && . /etc/claude-dev/runtime.env; exec tmux new-session -d -s main'`
  → 受け渡しファイルが**空のとき**も `main` セッションが立ち、窓の中は
  `DOCKER_HOST=tcp://claude-dev-docker-proxy:2375` / `COMPOSE_PROJECT_NAME=cdx-rt-abc123`
  (コンテナ作成時の env がそのまま継がれている)。**VM モード相当の行を書いた状態**では同じ窓が
  `DOCKER_HOST=tcp://127.0.0.1:2375` / `SSH_AUTH_SOCK=/tmp/ssh-agent.sock` を返した。
  entrypoint が作る受け渡しファイルは `-rw-r--r-- 1 root root 0 Aug 20 10:15 /etc/claude-dev/runtime.env`。
  issue 106 側は `set -e` 下の同一ブロックを隔離ハーネスで実行し、読めないファイルを含む
  `~/.local/bin` と読めない `~/.ssh/config` のどちらでもブロックの先へ到達し、
  `SSH_OPTS=[]`(= 加工前の config を渡していない)で、失敗時の一時ファイルも残らない
  (`/tmp/claude-dev-ssh-config.*` が 51 → 51)ことを確認した。
- lint / build: green
  (`bash -n claude-dev && bash -n claude-dev-mac && bash -n scripts/entrypoint-claude.sh` → 構文エラーなし /
  `cd docker-proxy && go vet ./...` → 出力なし・終了 0 /
  `cd docker-proxy && go test ./...` → `ok  	github.com/quvox/claude-dev-env/docker-proxy	(cached)` /
  `make build-claude` → `✅ claude-dev-claude`)
- 外部挙動の変化: あり(読めないホスト資産があっても `start` が起動まで到達する / 作り直した
  tmux の窓で VM モードの `DOCKER_HOST` と macOS の `SSH_AUTH_SOCK` が初回起動と同じ値になる)
- 認証・決済・不可逆への接触: あり(critical: true)
- E2E・全件テスト・ブラウザQA: 実施していない(/verify-tests に委ねる — 収束契約)

## 基本要件の点検

| ID | 判定 | 理由 | 落とし先 |
|---|---|---|---|
| BR-01 | 非該当 | アカウント・権限・認証情報を作る/変える/消す機能に触れない。SSH agent の転送は既存の鍵集合をそのまま使うだけで、鍵の追加・削除・降格を行わない | - |
| BR-02 | 該当 | `~/.ssh/config` の加工に失敗した場合の扱いが「外部から受け取ったファイルを使うかどうか」の判断そのものである。**加工できなかった生の config を代わりに渡してはならない**(`IdentityFile` / `IdentityAgent` を残したまま渡すと `D0-sec-02` が除去した理由が消える) | `FR-env-04-9`(新設)+ `MODULE-cli-start` の異常系 |
| BR-03 | 非該当 | 利用者が値を決める識別子を新たに受け取らない。`/etc/claude-dev/runtime.env` に載るのは本システムが決めた固定名の変数だけで、利用者由来の名前は入らない | - |
| BR-04 | 該当 | `/etc/claude-dev/runtime.env` はプロセスの外(コンテナ内のファイル)を跨いで値を渡す新しい経路である。**誰が書き誰が読むか・何が載るか・載らないときどうなるか**を契約に書く | `CTR-cli-container`「実行時に決まる環境変数の受け渡し」(新設)+ `MODULE-entrypoint-claude` |
| BR-05 | 非該当 | 不可逆または影響の大きい操作を新たに行わない。書くのはコンテナ内の1ファイルで、コンテナの削除とともに消える | - |
| BR-06 | 非該当 | 推測されると困る値を生成しない。`runtime.env` に載るのはソケットのパスと Docker API の URL であり、いずれも秘密ではない | - |

## 決定シート(回答済み)

- 問いなし(開示のみ)

## 調査メモ

- issue 106 の対象2箇所: `claude-dev:1536`-`:1539`(`cp -a`)/ `claude-dev:1625`-`:1629`
  (`mktemp` + `sed`)。macOS 版は `claude-dev-mac:1611`-`:1614` / `:1716`-`:1720`。
- issue 108 の対象(経路2): `claude-dev:1464`-`:1467` / `claude-dev-mac:1541`-`:1544`。
- **entrypoint は VM 起動が成功したときだけ `DOCKER_HOST` を上書きする**
  (`scripts/entrypoint-claude.sh:487` の `if su "$USERNAME" -c '/usr/local/bin/vm-up.sh'; then`。
  失敗時は proxy 既定を維持する — 同 `:480` のコメント)。
- **macOS の `SSH_AUTH_SOCK` は socat がソケットを作れたときだけ export される**
  (`scripts/entrypoint-claude.sh:110` の `if [ -S "/tmp/ssh-agent.sock" ]; then`)。
- 既存の受け渡しファイル `/etc/claude-dev/vm.env` は `scripts/entrypoint-claude.sh:489` が
  書き、`:499` が両 rc から読ませている(VM モードの `DOCKER_HOST` だけを載せる)。
- 同型の先行修正の書き方: `git show 0b26b56`(`|| _overlay=""` + `⚠️ …(起動は続けます)`)。
- `check-backlog.py` / `check-debt.py` はいずれも合格(未クローズ issue 9 / 上限 30、残務 38 行 /
  上限 50、未検証の構築記録 2 / 上限 5)。

## 進捗メモ(再開点)

- 2026-08-20 09:56 構築記録を作成。closure 確定。決定シートは問いゼロ(問う基準の関門1・2を
  満たす論点なし)のため作らない。
- 2026-08-20 10:05 01 へ `FR-env-02-7`(読めないホスト資産)と `FR-env-04-9`(SSH クライアント
  設定の加工不可)を新設。どちらも `[DS-02]` の開示行つき。
- 2026-08-20 10:12 02 契約を更新: 環境変数の到達義務の主語を「コンテナ内でプロセスの木を
  新しく起こす側」へ広げ、`実行時に決まる環境変数の受け渡し(/etc/claude-dev/runtime.env)` 節を
  新設。マウント表とエラーケース表にも行を足した。
- 2026-08-20 10:20 [DS-05] issue 108 は対処案 A(CLI が `-e` で値を組み立てて渡す)ではなく
  **C(entrypoint が採用した値をコンテナ内の1ファイルへ記録し、外から起こす側が読む)を採る**
  — 理由: entrypoint は VM 起動が成功したときだけ `DOCKER_HOST` を上書きし
  (`scripts/entrypoint-claude.sh:487`)、`SSH_AUTH_SOCK` も socat がソケットを作れたときだけ
  export する(同 `:110`)。CLI 側は成否を知らないので、A では**失敗時に嘘の値を配る**。
  値の持ち主が記録する形なら、採用しなかったときは行が無く、既定がそのまま残る /
  見直す条件: entrypoint が実行時に値を決めるのをやめ、コンテナ作成時にすべて確定するように
  なったとき(そのときは受け渡しファイル自体が不要になる)
- 2026-08-20 10:24 [DS-02] 読めないホスト資産は「取り込まずに表示して続行」、`~/.ssh/config`
  は**加工前のものを代替として渡さない** — 理由: `NFR-avail-03` が補助機能の失敗で主機能を
  止めないことを求める一方、生の config を渡すと `IdentityAgent` が残って agent が不通になり、
  除去している理由が消える / 見直す条件: 除去対象がコンテナ内で無害になったとき。
  開示先は `FR-env-02-7` / `FR-env-04-9`(01)と `MODULE-cli-start` の異常系。
- 2026-08-20 10:30 実装完了(6箇所): `claude-dev` / `claude-dev-mac` の `cp -a` と
  `mktemp`+`sed` を握り、両者の再接続経路の `tmux new-session` を受け渡しファイル経由へ。
  `scripts/entrypoint-claude.sh` に `RUNTIME_ENV_FILE` の初期化と `record_runtime_env` を新設し、
  `SSH_AUTH_SOCK` と VM の `DOCKER_HOST` を採用した地点で記録するようにした。
- 2026-08-20 10:36 実挙動を確認: 読めないファイルを含む `~/.local/bin` と読めない
  `~/.ssh/config` のどちらでも `set -e` 下でブロックの先へ到達し、生の config は渡らず、
  失敗時の一時ファイルも残らない(51→51)。受け渡しファイルの往復も、有るとき/無いときの
  両方で意図どおり(値の上書き / 既定の維持)。
- 2026-08-20 10:50 03 を実装から取り直した(`MODULE-cli-start` の手順7・11・13 / 異常系3行 /
  副作用の順序 / 既知の制限から issue 106 の行を削除 / 判断3・4 を更新、`MODULE-entrypoint-claude`
  の手順0 新設、03 契約に受け渡しの実装事実2行)。テスト仕様(`tests/cli-start.md` /
  `tests/entrypoint.md` / `tests/e2e.md`)に条項の対応行と実機確認手順を足した。
- 2026-08-20 11:05 実イメージで確認(`make build-claude` → 経路2 のコマンドを実行)。
  受け渡しファイルが空でも窓は立ち、行が在るときは VM の値が窓へ届いた。
- 2026-08-20 11:10 残務の裁定: 程度語3箇所は**直した**(行を削除)。`03-impl/contracts/cli-container.md`
  の行番号ずれは**持ち越す**(実測 129 トークン。理由は履歴の副産物に記載)。`impl:` の担当範囲は
  受け側を足したうえで**持ち越す**。判断の書式の一括移行と 130 の 01 への引き上げも**持ち越す**。
  削除済み issue への参照は closure 内の1件(`046`)を**直した**。

## 申し送り

- **`03-impl/contracts/cli-container.md` のコード引用の行番号ずれは持ち越した**。本タスクが
  実測した規模は 129 トークン(ファイル名つき 43 / 裸の `:NNN` 86)で、`docs/pendings.md` の
  該当行へ書いた。**本タスク自身も `claude-dev` +26 行 / `claude-dev-mac` +26 行 /
  `scripts/entrypoint-claude.sh` +25 行のずれを新たに作っている**ので、次に同ファイルを触る
  タスクはその分も含めて取り直すこと。
- 実機確認は**この Linux ホストの非 VM 構成でしか行っていない**。`closes_when` が求める
  VM モードと macOS での確認は `/verify-tests`(E2E-01 手順9-8 / 手順11)に委ねる。
