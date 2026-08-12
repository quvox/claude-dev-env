---
target: docs/03-impl/relations/MODULE-cli-login-codex.md
change: replace
version_bump: patch
reason: 'issue 054(解消して削除された issue のパスが根拠として残る)。`docs/issues/020` は 2026-08-04 の `task-fix-destructive-scope` が解消して削除済みで、参照先が実在しない(CS11)。経緯を持つ `docs/histories/2026-08-04-fix-destructive-scope.md` へ 3 箇所を付け替える。**排他の記述・異常系・実装上の判断は1文字も変えない**'
id: MODULE-cli-login-codex
module: MOD-cli-login-codex
kind: tool
sync: sync
impl: claude-dev::main#login-codex, claude-dev-mac::main#login-codex
callers: なし
callees: MODULE-cli-common-ensure-infrastructure, MODULE-cli-common-lock, MODULE-cli-common-require-setup
contracts: CTR-cli-container
design: DSN-mod-01, DSN-mod-02, DSN-auth-01, DSN-dist-02, DSN-env-02
requirements: FR-env-03, FR-env-12
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-11
summary: Codex のデバイス認証を実行し認証情報を共有ボリュームの codex/ へ置く
reflected: 2026-08-12
---

# MODULE-cli-login-codex Codex 認証の取得

## 目的

同梱の Codex CLI を使えるようにするための認証を、Claude と同じ「一時コンテナで取得して
共有ボリュームへ置く」方式で得る(FR-env-03・FR-env-12)。Codex 認証は専用ボリュームを
作らず `claude-dev-auth` の `codex/` サブディレクトリへ相乗りさせる(DSN-auth-01)。

## 処理の流れ

1. `MODULE-cli-common-require-setup` → `MODULE-cli-common-ensure-infrastructure`。
2. `MODULE-cli-common-lock` で**共有資源単位**のロック(キー `shared`、操作名 `login-codex`)を取る。
   取得できなければ**共有ボリュームに一切書かずに**非0で終わる(`FR-env-01` 受入基準16)。
   `logout` / `reset` / `login` と重なるのを防ぐ(`docs/histories/2026-08-04-fix-destructive-scope.md`)。
   **ロックは手順8 が終わるまで保持する**(デバイス認証の間ずっと保持する)。
3. `login` と同型の一時コンテナ(`--rm -it --entrypoint bash`、`claude-dev-auth` を
   `~/.claude-shared` へ)を起動する。
4. root が `~/.claude-shared/codex/` を `mkdir -p` し、**`chown -R` で所有権をコンテナユーザへ戻す**
   (entrypoint の同期ループが root で書き戻すため共有側が root 所有になりうる。戻さないと後続の
   ユーザー権限コピーが失敗する)。
5. コンテナ内の `~/.codex` を作り直す。
6. `su` でユーザへ切り替え、共有側に `codex/auth.json` があれば `~/.codex/` へコピーする(`chmod 600`)。
7. `codex login --device-auth` を対話起動する。表示された URL と認証コードを利用者がブラウザで開く
   (Linux 版は「手元の PC」と案内、mac 版はローカルブラウザ前提の文言)。
8. 終了後、`~/.codex/auth.json` を `~/.claude-shared/codex/` へ書き戻す(`chmod 600`)。
9. ロックを解放する(`trap` により異常終了時も解放される)。

## 呼び出され方

- 契機: 利用者が `claude-dev login-codex` を実行したとき。
- 前提条件: 端末が対話可能であること。
- 引数: なし。

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| (なし) | - | - | - |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

### MODULE-cli-common-lock

- 何のために呼ぶか: 共有ボリュームの `codex/` へ認証を書く経路であり、`logout` / `reset` が同時に
  走ると書いた直後に消える、または `start` の認証コピーが空を読む(`docs/histories/2026-08-04-fix-destructive-scope.md`)。
  `login` と同じキーを使うので、2つのログインが同時に走ることも防ぐ。
- 何を渡すか: キー `shared` と操作名 `login-codex`。 / 何を受け取るか: 終了ステータス。
- **失敗したときどうなるか**: **共有ボリュームに一切書かずに**非0で終わる。保持している操作名と
  再実行の方法を表示する。
- **注記**: デバイス認証を含むため保持時間が長い。その間 `start` の認証コピー区間と
  `logout` / `reset` / `login` は取得できず、理由を表示して非0で終わる。

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
| 戻り値 | `codex` の対話終了後 0。**ロックを取得できない場合は 1**(共有ボリュームに一切書かない) |
| 永続化 | 共有ボリューム `claude-dev-auth` の `codex/auth.json`(`chmod 600`)。所有権をコンテナユーザへ戻す `chown -R` も行う。**ロックのシンボリックリンク `${HOME}/.claude-dev/locks/shared.lock` を作成・削除する** |
| 発火するイベント | なし |
| ログ | 標準出力へ手順案内。`codex login --device-auth` の URL と認証コードが端末に出る。ロックの取得失敗と残骸の引き継ぎは stderr |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| **共有資源単位のロックを取得できない** | 保持している操作名と PID、再実行の方法を stderr へ出し、**共有ボリュームに一切書かずに** `exit 1` | `logout` / `reset` / `login` と重なって**書いた直後に消える**ことを防ぐ(`docs/histories/2026-08-04-fix-destructive-scope.md`) |
| **ロックが存在しないプロセスに保持されたまま残っている** | 引き継いだ旨を stderr へ出して処理を続行する | 永久に取得できない状態にならない |
| デバイス認証を完了せず終了 | 書き戻す `auth.json` が無く、共有ボリュームは変化しない。**ロックは `trap` が解放する** | 未ログインのまま。`start` は codex 認証をコピーせずに起動する |
| 共有側 `codex/` が root 所有のまま | 手順4の `chown -R` で修復してから進む | なし |
| 非 TTY で実行 | `docker run -it` が失敗し非0終了する。**ロックは `trap` が解放する** | 認証できない |
| 対話の途中で `INT` / `TERM` を受けた | `trap` がロックを解放して終了コード 130 で終わる | 共有ボリュームは対話前の状態のまま |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | ロックの取得を `require_setup` と `ensure_infrastructure` の**後**に置く。どちらも冪等な共有資源の準備で、ロックの保護対象ではないため(契約の「排他(ロックキー)」) | D0-env-09 |
| 2 | ロックを**デバイス認証の全区間で保持する**。認証の書き込みは対話の終了後(手順8)なので、対話の前後で取り直すと窓が開く | D0-env-09 |
| 3 | `login` と**同じキー `shared`** を使う(claude と codex の認証は同じボリュームに同居する。`D0-auth-01`)。キーを分けると、同居している資源に対する排他が成立しない | D0-env-09 / D0-auth-01 |
| 4 | Linux 版・macOS 版の**両方に同じ形で**入れる(同じサブコマンドの成否・出力を OS で変えないため) | D0-scope-03 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| **デバイス認証の全区間でロックを保持するため、保持時間が利用者の操作に依存する** | その間 `start` の認証コピー区間・`logout` / `reset` / `login` は取得できず、理由を表示して非0で終わる | なし(閾値の外: **待たない**設計なので他の操作は固まらない。判断2) |
| **`login` と同じキー `shared` を使うため、2つのログインを同時に実行できない** | `login` の実行中は `login-codex` が非0で終わる(逆も同じ) | なし(閾値の外: claude と codex の認証は同じボリュームに同居する(`D0-auth-01`)ので、キーを分けると排他が成立しない。判断3) |
| **`require_setup` と `ensure_infrastructure` はロックの外で走る** | ロックが取れなくてもイメージ・ネットワーク・空のボリュームは作られていることがある | なし(閾値の外: どちらも冪等に作られる共有資源である。契約「排他(ロックキー)」が保護対象外と明示) |
