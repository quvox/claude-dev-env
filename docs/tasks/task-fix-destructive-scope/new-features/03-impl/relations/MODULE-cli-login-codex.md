---
target: docs/03-impl/relations/MODULE-cli-login-codex.md
change: replace
sections:
  - "## 処理の流れ"
  - "## 連携先と連携内容"
  - "## 実装上の判断"
deletes: []
reason: D0-env-08 項6 の排他の対象に login-codex を含める(共有ボリュームの codex/ へ認証を書く経路であり、logout / reset と重なると書いた直後に消える。docs/issues/020 の事象表)。FR-env-01 受入基準16
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
updated: 2026-08-04
summary: Codex のデバイス認証を実行し認証情報を共有ボリュームの codex/ へ置く
---

## 処理の流れ

1. `MODULE-cli-common-require-setup` → `MODULE-cli-common-ensure-infrastructure`。
2. `MODULE-cli-common-lock` で**共有資源単位**のロック(キー `shared`、操作名 `login-codex`)を取る。
   取得できなければ**共有ボリュームに一切書かずに**非0で終わる(`FR-env-01` 受入基準16)。
   `logout` / `reset` / `login` と重なるのを防ぐ(`docs/issues/020`)。
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

## 連携先と連携内容

### MODULE-cli-common-require-setup

- 何のために呼ぶか: ログイン用の一時コンテナに使うイメージを保証するため。
- 何を渡すか: なし。 / 何を受け取るか: なし。
- **失敗したときどうなるか**: `set -e` で非0終了し、認証は始まらない。ロックはまだ取っていない。

### MODULE-cli-common-ensure-infrastructure

- 何のために呼ぶか: 共有ボリューム(認証)とネットワークを用意するため。
- 何を渡すか: なし。 / 何を受け取るか: なし。
- **失敗したときどうなるか**: 握りつぶされ、`docker run` のボリューム自動作成で吸収される。

### MODULE-cli-common-lock

- 何のために呼ぶか: 共有ボリュームの `codex/` へ認証を書く経路であり、`logout` / `reset` が同時に
  走ると書いた直後に消える、または `start` の認証コピーが空を読む(`docs/issues/020`)。
  `login` と同じキーを使うので、2つのログインが同時に走ることも防ぐ。
- 何を渡すか: キー `shared` と操作名 `login-codex`。 / 何を受け取るか: 終了ステータス。
- **失敗したときどうなるか**: **共有ボリュームに一切書かずに**非0で終わる。保持している操作名と
  再実行の方法を表示する。
- **注記**: デバイス認証を含むため保持時間が長い。その間 `start` の認証コピー区間と
  `logout` / `reset` / `login` は取得できず、理由を表示して非0で終わる。

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | ロックの取得を `require_setup` と `ensure_infrastructure` の**後**に置く。どちらも冪等な共有資源の準備で、ロックの保護対象ではないため(契約の「排他(ロックキー)」) | D0-env-09 |
| 2 | ロックを**デバイス認証の全区間で保持する**。認証の書き込みは対話の終了後(手順8)なので、対話の前後で取り直すと窓が開く | D0-env-09 |
| 3 | `login` と**同じキー `shared`** を使う(claude と codex の認証は同じボリュームに同居する。`D0-auth-01`)。キーを分けると、同居している資源に対する排他が成立しない | D0-env-09 / D0-auth-01 |
| 4 | Linux 版・macOS 版の**両方に同じ形で**入れる(同じサブコマンドの成否・出力を OS で変えないため) | D0-scope-03 |
