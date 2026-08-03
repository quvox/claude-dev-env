---
target: docs/03-impl/relations/MODULE-cli-common-container-name.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-cli-common-container-name
module: MOD-cli-common
kind: function-call
sync: sync
impl: claude-dev::container_name, claude-dev-mac::container_name
callers: MODULE-cli-attach, MODULE-cli-code, MODULE-cli-firewall, MODULE-cli-forward, MODULE-cli-orchestrate, MODULE-cli-ports, MODULE-cli-ssh-keys, MODULE-cli-ssh-keys-reset, MODULE-cli-start, MODULE-cli-stop, MODULE-cli-unforward
callees: なし
contracts: なし
design: DSN-mod-01, DSN-mod-02
requirements: FR-env-01
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: プロジェクト名からコンテナ名を導出する(命名規則の実体)
---

# MODULE-cli-common-container-name コンテナ名の導出

## 目的

`claude-dev` は「カレントディレクトリ = 1セッション」を単位に動く(FR-env-01)。その対応付けを
決めているのが本機能である。ここが唯一の命名規則であり、`start` で作るコンテナ名も、`stop` /
`attach` / `forward` が探すコンテナ名も、すべてこの関数の戻り値で一致する。

## 処理の流れ

1. `project_name`(同一モジュール内の私有ヘルパ。畳み込み済み)を呼ぶ。
2. `project_name` は `basename "$(pwd)"` を取り、`tr '[:upper:]' '[:lower:]'` で小文字化し、
   `sed 's/[^a-z0-9._-]/-/g'` で `[a-z0-9._-]` 以外を `-` へ置換する。
3. 変換後の文字列をそのまま標準出力へ返す(`container_name` は `project_name` の別名であり、
   両者の戻り値は常に同値)。

## 呼び出され方

- 契機: サブコマンドがコンテナを特定する必要が生じたとき(引数 `NAME` の既定値として)。
- 前提条件: カレントディレクトリが対象プロジェクトのルートであること。
- 引数: なし(カレントディレクトリだけを見る)。

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| (なし) | - | - | 入力は `pwd` のみ |

- 認可: CLI を実行できるホストユーザ。追加の認可は無い。

## 連携先と連携内容

連携先なし。私有ヘルパ `project_name` は同一モジュール内なので畳み込む
(`.claude/directions/relations.md` §1)。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 標準出力へコンテナ名(小文字・`[a-z0-9._-]` のみ)1行 |
| 永続化 | なし |
| 発火するイベント | なし |
| ログ | なし |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| ディレクトリ名が英数字を含まない(例: 日本語のみ) | 全文字が `-` へ置換された名前を返す。エラーにはしない | 別プロジェクトでも同じ名前になり同一セッション扱いになる |
| 別パスの同名ディレクトリ | 同じ名前を返す | 同一セッション扱いになる(既知の制限) |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | `claude-dev` と `claude-dev-mac` の同名関数を1機能として扱い、OS 差分は本文に書く(両者の実装は同一) | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| コンテナ名がディレクトリ名だけで決まる | 別パスの同名ディレクトリが同一セッションになる | なし(意図した設計。`docs/03-impl/relations/MODULE-cli-start.md` にも記載) |
