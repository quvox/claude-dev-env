---
id: MODULE-cli-login-gemini
updated: 2026-11-23
module: MOD-cli-login-gemini
kind: tool
sync: sync
impl: claude-dev::main#login-gemini, claude-dev-mac::main#login-gemini
callers: なし
callees: MODULE-cli-common-ensure-infrastructure, MODULE-cli-common-lock, MODULE-cli-common-require-setup
contracts: CTR-cli-container
design: DSN-mod-01, DSN-mod-02, DSN-auth-01, DSN-env-02
requirements: FR-env-03, FR-env-12
tests: なし(未実装。Google への実ログインが要り無人では回せないため、E2E-07 の実機確認手順で代替する)
summary: agy の Google 認証を一時コンテナで実行し、認証トークンを共有ボリュームの gemini/ へ置く
---

# MODULE-cli-login-gemini agy(Google Antigravity CLI)の認証の取得

## 目的

同梱の agy を使えるようにするための Google の認証を、Claude・Codex と同じ「一時コンテナで取得して
共有ボリュームへ置く」方式で得る(FR-env-03-25・FR-env-12。`D0-dist-07` 項3〜4)。
agy の認証トークンは専用ボリュームを作らず `claude-dev-auth` の `gemini/` サブディレクトリへ
相乗りさせる(DSN-auth-01)。共有するのは `antigravity-cli/antigravity-oauth-token` の1本だけである。

## 処理の流れ

1. `MODULE-cli-common-require-setup` → `MODULE-cli-common-ensure-infrastructure`。
2. `MODULE-cli-common-lock` で**共有資源単位**のロック(キー `shared`、操作名 `login-gemini`)を取る。
   取得できなければ**共有ボリュームに一切書かずに**非0で終わる(`FR-env-01-16`)。
   **ロックは手順7 が終わるまで保持する**(対話認証の間ずっと保持する)。
3. `login` / `login-codex` と同型の一時コンテナ(`--rm -it --entrypoint bash`、`claude-dev-auth` を
   `~/.claude-shared` へ)を起動する。**環境変数 `SSH_CONNECTION` を渡す** — agy は SSH 越しの環境を
   検出すると「URL を別の端末のブラウザで開き、表示されたコードを貼り付ける」方式になる
   (コンテナ内にはブラウザもホストへ戻る経路も無いので、常にこの方式へ寄せる)。
4. root が `~/.claude-shared/gemini/antigravity-cli/` を `mkdir -p` し、**`chown -R` で所有権を
   コンテナユーザへ戻す**(entrypoint の同期ループが root で書き戻すため共有側が root 所有になりうる)。
5. コンテナ内の `~/.gemini` を空で作り直す(**既存の認証を引き継がない** — 判断1)。
6. `su` でユーザへ切り替え、`agy` を対話起動する。利用者は Google の認証を選び、URL をブラウザで開き、
   表示されたコードを端末へ貼り付け、ログインできたら agy を終了する
   (Linux 版は「ブラウザ(手元の PC)」と案内、mac 版はローカルブラウザ前提の文言)。
7. 終了後、`~/.gemini/antigravity-cli/antigravity-oauth-token` があれば共有ボリュームの
   `gemini/antigravity-cli/` へコピーして `chmod 600` する。無ければ「共有ボリュームは変更していない」と表示する。
8. ロックを解放する(`trap` により異常終了時も解放される)。

## 呼び出され方

- 契機: 利用者が `claude-dev login-gemini` を実行したとき。
- 前提条件: 端末が対話可能であること。
- 引数: なし。

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| (なし) | - | - | - |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

### MODULE-cli-common-lock

- 何のために呼ぶか: 共有ボリュームの `gemini/` へ認証を書く経路であり、`logout` / `reset` が同時に
  走ると書いた直後に消える、または `start` の認証コピーが空を読む。
  `login` / `login-codex` と同じキーを使うので、複数のログインが同時に走ることも防ぐ。
- 何を渡すか: キー `shared` と操作名 `login-gemini`。 / 何を受け取るか: 終了ステータス。
- **失敗したときどうなるか**: **共有ボリュームに一切書かずに**非0で終わる。保持している操作名と
  再実行の方法を表示する。

### MODULE-cli-common-require-setup

- 何のために呼ぶか: ログイン用の一時コンテナに使うイメージを保証するため。
- 何を渡すか: なし。 / 何を受け取るか: なし。
- **失敗したときどうなるか**: `set -e` で非0終了し、認証は始まらない。ロックはまだ取っていない。

### MODULE-cli-common-ensure-infrastructure

- 何のために呼ぶか: 共有ボリューム(認証)とネットワークを用意するため。
- 何を渡すか: なし。 / 何を受け取るか: なし。
- **失敗したときどうなるか**: 握りつぶされ、`docker run` のボリューム自動作成で吸収される。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | agy の対話終了後 0。**ロックを取得できない場合は 1**(共有ボリュームに一切書かない) |
| 永続化 | 共有ボリューム `claude-dev-auth` の `gemini/antigravity-cli/antigravity-oauth-token`(`chmod 600`)。所有権をコンテナユーザへ戻す `chown -R` も行う。**ロックのシンボリックリンク `${HOME}/.claude-dev/locks/shared.lock` を作成・削除する** |
| 発火するイベント | なし |
| ログ | 標準出力へ手順案内。agy が認証 URL を端末に出す。**トークンの中身は表示しない**。ロックの取得失敗と残骸の引き継ぎは stderr |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| **共有資源単位のロックを取得できない** | 保持している操作名と PID、再実行の方法を stderr へ出し、**共有ボリュームに一切書かずに** `exit 1` | `logout` / `reset` / `login` / `login-codex` と重なって書いた直後に消えることを防ぐ |
| **ロックが存在しないプロセスに保持されたまま残っている** | 引き継いだ旨を stderr へ出して処理を続行する | 永久に取得できない状態にならない |
| 認証を完了せず終了 | トークンが無いので共有側へ書かず、その旨を表示する。**共有中の既存のトークン(あれば)はそのまま残る**。ロックは `trap` が解放する | 既存のログインのまま、または未ログインのまま |
| 共有側 `gemini/` が root 所有のまま | 手順4の `chown -R` で修復してから進む | なし |
| 非 TTY で実行 | `docker run -it` が失敗し非0終了する。**ロックは `trap` が解放する** | 認証できない(`FR-env-03-13`) |
| 対話の途中で `INT` / `TERM` を受けた | `trap` がロックを解放して終了コード 130 で終わる | 共有ボリュームは対話前の状態のまま |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | **既存の認証を引き継がず、毎回認証の画面から始める**(`login-codex` は引き継いでから始めるが、agy はログイン済みだと認証の画面を出さないため、引き継ぐと別アカウントへ切り替えられない)。途中でやめれば共有中のトークンは変わらない | DS-01(2026-11-23。見直す条件: 引き継いでほしいと言われたとき) |
| 2 | ロックの取得を `require_setup` と `ensure_infrastructure` の**後**に置く(どちらも冪等な共有資源の準備で、ロックの保護対象ではない) | D0-env-09 |
| 3 | `login` / `login-codex` と**同じキー `shared`** を使う(3つの認証は同じボリュームに同居する。`D0-auth-01`) | D0-env-09 / D0-auth-01 |
| 4 | `SSH_CONNECTION` を固定値で渡し、URL とコードの貼り付けの方式へ寄せる(コンテナからホストのブラウザへ戻るコールバックの経路が無いため) | DS-01 |
| 5 | Linux 版・macOS 版の**両方に同じ形で**入れる(案内の1行の文言だけが違う) | D0-scope-03 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| **対話認証の全区間でロックを保持するため、保持時間が利用者の操作に依存する** | その間 `start` の認証コピー区間・`logout` / `reset` / `login` / `login-codex` は取得できず、理由を表示して非0で終わる | なし(閾値の外: **待たない**設計なので他の操作は固まらない) |
| **agy の認証の画面の操作(Google の認証を選ぶ・終了する)は利用者に任せている** | 案内の文言どおりに操作しないとトークンができず、共有ボリュームは変わらない | なし(閾値の外: 認証の対話は agy のものである) |
| **実ログインの経路は無人で検証できない** | 自動テストを持たない | なし(E2E-07 の実機確認手順で確かめる) |
