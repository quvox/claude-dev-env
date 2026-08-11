---
target: docs/03-impl/relations/MODULE-cli-login.md
change: replace
version_bump: patch
reason: 'issue 054(解消して削除された issue のパスが根拠として残る)。`docs/issues/020` は 2026-08-04 の `task-fix-destructive-scope` が解消して削除済みで、参照先が実在しない(CS11)。経緯を持つ `docs/histories/2026-08-04-fix-destructive-scope.md` へ 3 箇所を付け替える。**排他の記述・異常系・実装上の判断は1文字も変えない**'
id: MODULE-cli-login
module: MOD-cli-login
kind: tool
sync: sync
impl: claude-dev::main#login, claude-dev-mac::main#login
callers: なし
callees: MODULE-cli-common-ensure-infrastructure, MODULE-cli-common-lock, MODULE-cli-common-require-setup
contracts: CTR-cli-container
design: DSN-mod-01, DSN-mod-02, DSN-auth-01, DSN-env-02
requirements: FR-env-03
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-11
summary: Claude の OAuth ログインをコンテナ内で実行し共有ボリュームへ保存する
---

# MODULE-cli-login Claude 認証の取得

## 目的

ホストのクレデンシャルをコンテナへ渡す経路を作らずに Claude の認証を得る(FR-env-03)。
認証は使い捨ての一時コンテナ内で取得し、共有ボリューム `claude-dev-auth` にだけ残す
(DSN-auth-01)。

## 処理の流れ

1. `MODULE-cli-common-require-setup` でイメージをそろえる。
2. `MODULE-cli-common-ensure-infrastructure` でネットワークと共有ボリュームを用意する。
3. `MODULE-cli-common-lock` で**共有資源単位**のロック(キー `shared`、操作名 `login`)を取る。
   取得できなければ**共有ボリュームに一切書かずに**非0で終わる(`FR-env-01` 受入基準16)。
   `logout` / `reset` / 他の `login` と重なるのを防ぐ(`docs/histories/2026-08-04-fix-destructive-scope.md`)。
   **ロックは手順7 が終わるまで保持する**(対話認証の間ずっと保持する)。
4. `docker run --rm -it --entrypoint bash` で一時コンテナを起動し、`claude-dev-auth` を
   `~/.claude-shared` へマウントする(`TERM` / `LANG` も渡す)。
5. コンテナ内 root が `settings.json` 未存在時に
   `{"permissions":{"defaultMode":"bypassPermissions"},"model":"sonnet"}` を生成して `chown` する
   (この設定は共有しない)。
6. `su` でコンテナユーザへ切り替え、共有ボリュームの `.credentials.json` / `.claude.json` を
   `~/.claude/` へコピーし、`~/.claude.json` をリンクする。`claude` を対話起動する
   (利用者がブラウザで OAuth を完了させる)。
7. 終了後、`~/.claude/` の認証を `~/.claude-shared/` へ書き戻す。
8. ロックを解放する(`trap` により異常終了時も解放される)。

## 呼び出され方

- 契機: 利用者が `claude-dev login` を実行したとき。
- 前提条件: 端末が対話可能(`-it`)であること。
- 引数: なし。

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| (なし) | - | - | - |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

### MODULE-cli-common-lock

- 何のために呼ぶか: 共有ボリュームへ認証を**書く**唯一の経路であり、`logout` / `reset` が同時に
  走ると書いた直後に消える、または `start` の認証コピーが空を読む(`docs/histories/2026-08-04-fix-destructive-scope.md`)。
- 何を渡すか: キー `shared` と操作名 `login`。 / 何を受け取るか: 終了ステータス。
- **失敗したときどうなるか**: **共有ボリュームに一切書かずに**非0で終わる。保持している操作名と
  再実行の方法を表示する。
- **注記**: 対話認証を含むため保持時間が長い(利用者がブラウザで認証を終えるまで)。その間
  `start` の認証コピー区間と `logout` / `reset` は取得できず、理由を表示して非0で終わる。

### MODULE-cli-common-require-setup

- 何のために呼ぶか: ログイン用の一時コンテナに使うイメージを保証するため。
- 何を渡すか: なし。 / 何を受け取るか: なし。
- **失敗したときどうなるか**: `set -e` で非0終了し、ログインは始まらない。ロックはまだ取っていない。

### MODULE-cli-common-ensure-infrastructure

- 何のために呼ぶか: 共有ボリューム(認証)とネットワークを用意するため。
- 何を渡すか: なし。 / 何を受け取るか: なし。
- **失敗したときどうなるか**: 握りつぶされ、`docker run` のボリューム自動作成で吸収される。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | `claude` の対話終了後 0。**ロックを取得できない場合は 1**(共有ボリュームに一切書かない) |
| 永続化 | 共有ボリューム `claude-dev-auth` 直下の `.credentials.json` / `.claude.json`。**ロックのシンボリックリンク `${HOME}/.claude-dev/locks/shared.lock` を作成・削除する** |
| 発火するイベント | なし |
| ログ | 標準出力へ手順案内。`claude` の対話出力はそのまま端末に出る。ロックの取得失敗と残骸の引き継ぎは stderr |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| **共有資源単位のロックを取得できない** | 保持している操作名と PID、再実行の方法を stderr へ出し、**共有ボリュームに一切書かずに** `exit 1` | `logout` / `reset` / 他の `login` と重なって**書いた直後に消える**ことを防ぐ(`docs/histories/2026-08-04-fix-destructive-scope.md`) |
| **ロックが存在しないプロセスに保持されたまま残っている** | 引き継いだ旨を stderr へ出して処理を続行する | 永久に取得できない状態にならない |
| OAuth を完了せず終了 | 書き戻す認証が無く、共有ボリュームは変化しない。**ロックは `trap` が解放する** | 次回の `start` は未ログイン状態で起動する |
| 非 TTY で実行 | `docker run -it` が「the input device is not a TTY」で失敗し非0終了する。**ロックは `trap` が解放する** | ログインできない |
| 対話の途中で `INT` / `TERM` を受けた | `trap` がロックを解放して終了コード 130 で終わる | 共有ボリュームは対話前の状態のまま |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | ロックの取得を `require_setup` と `ensure_infrastructure` の**後**に置く。どちらも冪等な共有資源の準備で、ロックの保護対象ではないため(契約の「排他(ロックキー)」) | D0-env-09 |
| 2 | ロックを**対話認証の全区間で保持する**。認証の書き込みは対話の終了後(手順7)なので、対話の前後で取り直すと窓が開く。長時間の保持は `D0-env-08` 項6 の「待たない」設計の帰結として受け入れる(他の操作は理由を表示して非0で終わり、固まらない) | D0-env-09 |
| 3 | Linux 版・macOS 版の**両方に同じ形で**入れる(同じサブコマンドの成否・出力を OS で変えないため) | D0-scope-03 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| **対話認証の全区間でロックを保持するため、保持時間が利用者の操作に依存する** | その間 `start` の認証コピー区間・`logout` / `reset` / `login-codex` は取得できず、理由を表示して非0で終わる | なし(閾値の外: 認証を書いている最中に消す/読むほうが害が大きい。**待たない**設計なので他の操作は固まらない。`MODULE-cli-login` 判断2) |
| **`require_setup` と `ensure_infrastructure` はロックの外で走る** | ロックが取れなくてもイメージ・ネットワーク・空のボリュームは作られていることがある | なし(閾値の外: どちらも冪等に作られる共有資源で、作られるのは中身の無い器だけである。契約「排他(ロックキー)」が保護対象外と明示) |
| **ロックはホスト CLI のプロセス間でしか有効でない** | 利用者が直接コンテナを立てて認証を書く経路は防げない | なし(契約「ロックが守れない範囲」が明示) |
