---
id: 106-bug-two-auxiliary-host-asset-steps-halt-start-under-set-e
type: bug
severity: 中
origin_layer: 03
found: 2026-08-19
found_in: task-stop-cleanup-and-project-env のフェーズ4 で同型の全件走査を行って検出
related: NFR-avail-03, FR-env-02-6, FR-env-04-6, MODULE-cli-start, docs/03-impl/tests/cli-start.md
closes_when: 読み取れないファイルを含む `~/.local/bin/` と、読み取れない `~/.ssh/config` のそれぞれで `claude-dev start` を実行し、取り込めなかったことを表示したうえでコンテナの起動まで到達することを、Linux 版・macOS 版の両方で確認できること
pattern: set-e-unguarded-auxiliary-step-halts-start
pattern_survey: "`claude-dev` の `start)` 分岐(1417〜1799 行)にある代入・リダイレクト・ファイル操作を全件走査した。**握られていない補助処理はこの2つだけ**である: `cp -a \"${HOME}/.local/bin/.\" …`(:1538)と `sed -E … \"${HOME}/.ssh/config\" > \"$_ssh_config_tmp\"`(:1624。`mktemp` も同様)。同型だった他の4件(`.gitignore` の追記・新規作成・新規作成後の追記、`jq` によるホスト設定の取り込み、読めない env ファイル)は 2026-08-19 に同タスクの中で修正済み。`echo` によるメッセージ出力は端末への書き込みなので対象外とした。`mkdir -p \"${PROJECT_DIR}/.claude\" \"${PROJECT_DIR}/.codex\"`(:1504)は補助機能ではなく `FR-env-03` が要求する主機能の一部なので、この pattern には含めない"
summary: ~/.local/bin のコピーと ~/.ssh/config の加工が set -e の下で握られておらず、読めないと start が起動まで到達しない
---

# 106 ホスト資産を取り込む2つの補助処理が `set -e` で `start` を止める

## 事象

`claude-dev start` は、ホスト側の任意の資産をコンテナへ引き継ぐ補助処理をいくつか持つ。
そのうち **2つが失敗を握っておらず、`set -e` の下でその場でスクリプトが終わる**。

| 箇所 | 処理 | 失敗する条件 |
|---|---|---|
| `claude-dev:1537`-`:1538` / `claude-dev-mac` の同一箇所 | `~/.local/bin/` を `.claude/host-local-bin/` へ `cp -a` する | ディレクトリ内に読み取れないファイルが1つでもある |
| `claude-dev:1623`-`:1624` / 同上 | `~/.ssh/config` から `IdentityFile` 等の行を `sed` で除いた一時コピーを作る | `~/.ssh/config` が読めない、`/tmp` に `mktemp` できない |

どちらも**コンテナの起動そのものには要らない**補助であり、`NFR-avail-03`
(補助機能の失敗が主機能を止めないこと。目標値「補助機能の失敗時も主機能の成功率 100%」)
に反する。SSH については `FR-env-04-6`(agent ソケットの残骸を除去できない場合も起動を止めない)、
ホスト設定については `FR-env-02-6`(ホストの設定ファイルが無ければマウントせずに続行する)が
同じ方向を課している。

再現手順(`~/.local/bin` の側):

1. `chmod 000 ~/.local/bin/<何かのファイル>` を作る。
2. 任意のディレクトリで `claude-dev start --no-vnc` を実行する。
   → `cp: cannot open …: 許可がありません` で終わり、コンテナは起動しない。

## 影響

**ホスト側の環境がひとつ壊れているだけで、隔離コンテナがまったく起動しなくなる。**
利用者から見ると `claude-dev start` が使えず、原因(`~/.local/bin` の1ファイル)が
表示されたエラーからしか分からない。**失敗は表示されるので静かではない** — severity は「中」。

## 原因の見当

**推測ではなく確定**: `claude-dev` / `claude-dev-mac` は冒頭で `set -e` を有効にしており、
単純コマンドの失敗がそのままスクリプトの終了になる。上の2箇所には `|| true` も `if` も無い。

**同型の欠陥が同じ日に4件見つかっており、これはその残りである**
(`.gitignore` の追記・新規作成・新規作成後の追記、`jq` によるホスト設定の取り込み、
読めない env ファイル — いずれも `task-stop-cleanup-and-project-env` の中で修正した)。
**この2件だけを残したのは、どちらも本タスクが触っていない以前から在る経路だからである**
(`.claude/directions/issues-pendings.md` §1 の行1 は「現タスクの範囲で直すべきか」を問い、
範囲外のものは記録に回す)。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| 補助処理の失敗で起動を止めてよいか | 止まる(握っていない) | `NFR-avail-03` が「補助機能の失敗が主機能を止めない」を目標値 100% で課す | **要件が正。実装を直す** |

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | 2箇所を `if ! …; then <表示>; fi` の形にし、取り込めなかったことを表示して続行する(同日に直した4件と同じ倒し方) | `claude-dev` / `claude-dev-mac` の各2箇所 + `MODULE-cli-start` の異常系と既知の制限 |
| B | `start)` 分岐の先頭で `set +e` にし、要所だけ明示的に判定する | 影響範囲が広く、止まるべき失敗(コンテナ作成)まで握ってしまう |

推奨は **A**。**両 OS に同じ形で入れること**(`D0-scope-03`)。

## 経緯

- 2026-08-19 `task-stop-cleanup-and-project-env` のフェーズ4 で、同じ型の欠陥が3回続けて
  独立レビューに検出されたため、`start)` 分岐を全件走査して残りを洗い出した。
  **同タスクが触った経路の4件は同タスクの中で修正し、以前から在るこの2件を記録に回した。**
