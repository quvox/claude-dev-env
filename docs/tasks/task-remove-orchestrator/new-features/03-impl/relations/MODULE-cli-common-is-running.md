---
target: docs/03-impl/relations/MODULE-cli-common-is-running.md
change: replace
version_bump: patch
reason: 'オーケストレーターの全面削除にともなう `callers` の修正(決定シート 概念1)。`MODULE-cli-orchestrate` を削除するので、この機能の `callers` から同 ID を外す。**外さないと `check-relations.py` の対称性検査と `CS2` が実在しない ID を指して落ちる**。本文の変更は無い(この機能の振る舞いも実装も変わらない)。 呼び出し元は 9 → 8 になる。。**`## 実装上の判断` を再掲する**: `.claude/directions/delegation.md` §3.1 に従って既存の判断行を1件ずつ読み直した結果、**すべて継続**である(オーケストレーターの削除で見直す条件が発火した行は1件も無い)。`CS19` はこの節が変更のたびに読み直されることを要求するので、変更が無い場合も再掲する'
id: MODULE-cli-common-is-running
module: MOD-cli-common
kind: function-call
sync: sync
impl: claude-dev::is_running, claude-dev-mac::is_running
callers: MODULE-cli-attach, MODULE-cli-code, MODULE-cli-firewall, MODULE-cli-forward, MODULE-cli-list, MODULE-cli-ports, MODULE-cli-start, MODULE-cli-stop
callees: なし
contracts: なし
design: DSN-mod-01, DSN-mod-02
requirements: FR-env-01
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: 指定コンテナが running 状態かを判定する
reflected: 2026-08-10
---

# MODULE-cli-common-is-running セッション稼働判定

## 目的

「そのセッションが動いているか」は本システムの状態モデルそのもので、`start` の attach 分岐・
`stop` の停止対象判定・`code` / `attach` / `forward` / `ports` / `firewall` の前提条件がすべて
この判定に乗る(FR-env-01)。

## 処理の流れ

1. `docker ps -q -f "name=^<name>$" 2>/dev/null` を実行する(完全一致の正規表現で絞る)。
2. 出力が1行以上あれば `grep -q .` が真になり終了ステータス 0、無ければ 1 を返す。

## 呼び出され方

- 契機: サブコマンドが稼働状態で分岐するとき。
- 前提条件: `docker` コマンドが実行できること。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `$1` | 文字列 | 必須 | コンテナ名。`^...$` で完全一致検索する |

- 認可: CLI を実行できるホストユーザ(= docker グループ)。

## 連携先と連携内容

連携先なし。`docker` CLI の呼び出しは外部コマンド実行であり、コールグラフの機能間の辺には現れない。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 終了ステータス。0 = 稼働中 / 1 = 非稼働 |
| 永続化 | なし |
| 発火するイベント | なし |
| ログ | なし(`docker ps` の stderr は破棄する) |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| Docker デーモンに接続できない | `docker ps` の stderr を `/dev/null` に捨て、出力が空になるため終了ステータス 1(=非稼働)を返す | 「未起動」と同じ扱いになり、呼び出し元は起動を試みるか日本語エラーで `exit 1` する |
| 同名コンテナが複数 | Docker が同名を許さないので発生しない | - |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | デーモン接続失敗を「非稼働」に丸めている(区別しない)。区別すると全サブコマンドに分岐が増えるため | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| Docker デーモン不在と非稼働を区別しない | デーモンが落ちている場合も「未起動」と表示される | なし |
