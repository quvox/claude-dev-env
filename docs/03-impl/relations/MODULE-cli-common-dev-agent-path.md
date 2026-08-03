---
id: MODULE-cli-common-dev-agent-path
module: MOD-cli-common
kind: function-call
sync: sync
impl: claude-dev-mac::dev_agent_path
callers: MODULE-cli-ssh-keys-reset, MODULE-cli-start, MODULE-cli-stop
callees: なし
contracts: なし
design: DSN-mod-01, DSN-mod-02
requirements: FR-env-04, FR-env-10
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: macOS の専用 ssh-agent とブリッジのファイル配置を決める
---

# MODULE-cli-common-dev-agent-path 専用 ssh-agent の配置規則(macOS)

## 目的

macOS では Docker Desktop が UNIX ドメインソケットをコンテナへ bind できないため、専用
ssh-agent のソケットに加えて **TCP ブリッジ**の PID とポートをファイルで持ち回る(FR-env-10)。
その配置規則を1か所に閉じ込め、`start` / `stop` / `ssh-keys reset` が同じ場所を前提にできる
ようにするための機能である(FR-env-04)。

## 処理の流れ

1. 第2引数の種別で分岐し、`${DEV_AGENT_DIR}`(= `~/.claude-dev/agents`)配下のパスを組み立てる。
2. `sock` → `<name>.sock`(専用 ssh-agent のソケット)。
3. `pid` → `<name>.pid`(専用 ssh-agent の PID)。
4. `bpid` → `<name>.bridge.pid`(TCP ブリッジプロセスの PID)。
5. `bport` → `<name>.bridge.port`(ブリッジが待ち受けるローカルポート)。
6. いずれにも当たらない場合は何も出力しない。

## 呼び出され方

- 契機: 専用 agent / ブリッジを起動・参照・停止するとき。
- 前提条件: なし(ディレクトリの作成は呼び出し元が行う)。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `$1` | 文字列 | 必須 | コンテナ名(= プロジェクト名) |
| `$2` | 文字列 | 必須 | `sock` / `pid` / `bpid` / `bport` のいずれか |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

連携先なし。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 標準出力へパス1行(未知の種別なら空) |
| 永続化 | なし(パスを返すだけ。ファイル生成は呼び出し元) |
| 発火するイベント | なし |
| ログ | なし |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 第2引数が未知の値 | 何も出力せず終了ステータス 0 | 呼び出し元は空パスを使い、後続のファイル操作が失敗する |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | Linux 版(`claude-dev`)には本関数が存在しない。Linux はソケットを直接 bind できるため、ブリッジの PID/ポートを持つ必要が無い | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| macOS 専用 | Linux 版と共通化されておらず、配置規則が2実装に分かれている | なし |
