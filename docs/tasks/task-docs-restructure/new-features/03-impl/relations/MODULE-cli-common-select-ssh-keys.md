---
target: docs/03-impl/relations/MODULE-cli-common-select-ssh-keys.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-cli-common-select-ssh-keys
module: MOD-cli-common
kind: function-call
sync: sync
impl: claude-dev::select_ssh_keys_interactive, claude-dev-mac::select_ssh_keys_interactive
callers: MODULE-cli-ssh-keys-select, MODULE-cli-start
callees: MODULE-cli-common-write-project-ssh-keys
contracts: なし
design: DSN-mod-01, DSN-mod-02
requirements: FR-env-04
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: 利用可能な SSH 鍵を列挙し対話選択させて保存する
---

# MODULE-cli-common-select-ssh-keys SSH 鍵の対話選択

## 目的

コンテナへ見せる SSH 鍵を**プロジェクト単位で明示選択**させる(FR-env-04)。鍵の推測や
グローバル設定へのフォールバックを行わないという安全側の設計を、この対話 UI が担保している。

## 処理の流れ

1. `discover_ssh_keys`(同一モジュールの私有ヘルパ。畳み込み済み)で `~/.ssh/id_*`
   (`.pub` を除く)を列挙する。
2. 0 件なら「⚠️ ~/.ssh に鍵ファイル(id_*)が見つかりません。SSH 転送なしで続行します。」を出し、
   空の `ssh_keys:` を書き出して戻る。
3. 1 件以上あれば番号付きで一覧表示し、「番号をカンマ/空白区切り, a=全部, n=なし」で入力を促す。
4. 入力を解釈する: `a`/`A`/`all`/`ALL` → 全件、`n`/`N`/`none`/`NONE`/空 → 0 件、
   それ以外 → カンマを空白に変換して数値トークンだけを採用し、範囲内(1〜件数)のものを選ぶ。
5. `MODULE-cli-common-write-project-ssh-keys` を呼び、カレントディレクトリの
   `.claude-dev.yaml` へ選択結果を書き出す。
6. 「✅ SSH 鍵の選択を保存しました: <file>(<n> 件)」を表示し、`SSH_KEY_LIST` に選択結果を入れる。

## 呼び出され方

- 契機: `claude-dev ssh-keys` / `claude-dev ssh-keys select` の実行、または `start` が
  `.claude-dev.yaml` 不在を検出したとき(TTY のみ)。
- 前提条件: 標準入力が対話可能であること(非 TTY では呼び出し元が空設定の作成へ分岐する)。
- 引数: なし。書き出し先は常に `$(pwd)/.claude-dev.yaml`。

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| (なし) | - | - | 入力は `~/.ssh/id_*` と標準入力 |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

### MODULE-cli-common-write-project-ssh-keys

- 何のために呼ぶか: 選択結果をプロジェクト設定として永続化するため。
- 何を渡すか: 書き出し先パス(`$(pwd)/.claude-dev.yaml`)と、選択された鍵パスの並び(0 件可)。
- 何を受け取るか: 戻り値なし(ファイルが作られる)。
- **失敗したときどうなるか**: リダイレクト失敗は `set -e` によりスクリプト全体が非0で終了する。
  中途半端な `.claude-dev.yaml` が残る可能性があるが、次回実行時に上書きされる。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 常に 0。シェル変数 `SSH_KEY_LIST` に選択した鍵パスの配列を設定する |
| 永続化 | カレントプロジェクト直下の `.claude-dev.yaml`(`ssh_keys:` セクション) |
| 発火するイベント | なし |
| ログ | 標準出力へ鍵一覧・選択結果("✅ SSH 鍵の選択を保存しました") |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| `~/.ssh` に鍵が無い | 警告を出し、空の `ssh_keys:` を書いて 0 で戻る(停止しない) | SSH 転送なしで起動が続く |
| 数値でない入力・範囲外の番号 | そのトークンを黙って読み飛ばす | 選択件数が想定より少なくなる |
| `read` が EOF(非 TTY で直接呼ばれた場合) | 空入力として扱い 0 件選択になる | SSH 転送なしになる |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 選択 UI とファイル書き出しを分離し、書き出し側を独立機能にした(`ensure_project_config` も書き出しだけを使うため) | D0-scope-02 |
| 2 | 鍵の内容(パスフレーズ有無・種別)は見ない。列挙はファイル名パターン `id_*` のみ | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| `~/.ssh/id_*` という命名の鍵しか列挙しない | 別名の鍵は一覧に出ず、`.claude-dev.yaml` を手で書く必要がある | なし |
