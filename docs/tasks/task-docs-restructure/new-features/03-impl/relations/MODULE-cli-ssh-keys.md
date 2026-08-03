---
target: docs/03-impl/relations/MODULE-cli-ssh-keys.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-cli-ssh-keys
module: MOD-cli-ssh-keys
kind: tool
sync: sync
impl: claude-dev::main#ssh-keys, claude-dev-mac::main#ssh-keys
callers: なし
callees: MODULE-cli-common-container-name
contracts: なし
design: DSN-mod-01, DSN-mod-02
requirements: FR-env-04
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: ssh-keys の引数を reset / select へ振り分けるディスパッチャ
---

# MODULE-cli-ssh-keys ssh-keys のディスパッチャ

## 目的

`claude-dev ssh-keys` の第2引数で動作を分ける入口(FR-env-04)。分岐先の
`reset` / `select` はそれぞれ独立した機能として扱い、ここは振り分けと使い方表示だけを持つ。

## 処理の流れ

1. `MODULE-cli-common-container-name` で `NAME` を決める(Linux 版はこの位置で解決し、
   分岐先の `reset` が使う。macOS 版は `reset` 分岐の中で解決する)。
2. `$(pwd)/.claude-dev.yaml` を対象パスとして持つ。
3. 第2引数で分岐する: `reset` → `MODULE-cli-ssh-keys-reset` の処理、
   空文字または `select` → `MODULE-cli-ssh-keys-select` の処理、
   それ以外 → 「使い方: claude-dev ssh-keys [reset]」を表示して `exit 1`。

## 呼び出され方

- 契機: 利用者が `claude-dev ssh-keys [reset|select]` を実行したとき。
- 前提条件: カレントディレクトリが対象プロジェクトであること。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `$2` | 文字列 | 任意 | `reset` / `select` / 空。それ以外は使い方を表示して `exit 1` |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

### MODULE-cli-common-container-name

- 何のために呼ぶか: `reset` が停止する専用 ssh-agent のファイル名(= プロジェクト名)を決めるため。
- 何を渡すか: なし。 / 何を受け取るか: コンテナ名。
- **失敗したときどうなるか**: 想定されない。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 分岐先の終了ステータス。未知の引数のときは 1 |
| 永続化 | 本機能自体は無し(分岐先が行う) |
| 発火するイベント | なし |
| ログ | 未知の引数のときだけ使い方を表示する |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 未知の第2引数 | 「使い方: claude-dev ssh-keys [reset]」を表示して `exit 1` | 何も変更されない |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 内部分岐を1機能にまとめず、`reset` / `select` をそれぞれ独立した機能として立てる(`.claude/directions/relations.md` §1 のディスパッチャ規則) | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 使い方表示に `select` が現れない(実際は受け付ける) | 利用者から見て隠れた引数になっている | なし |
