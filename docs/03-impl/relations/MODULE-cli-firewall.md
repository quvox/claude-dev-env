---
id: MODULE-cli-firewall
module: MOD-cli-firewall
kind: tool
sync: sync
impl: claude-dev::main#firewall, claude-dev-mac::main#firewall
callers: なし
callees: MODULE-cli-common-container-name, MODULE-cli-common-is-running
contracts: なし
design: DSN-mod-01, DSN-mod-02
requirements: FR-env-05
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: コンテナ内のファイアウォールルールを表示する
---

# MODULE-cli-firewall ファイアウォールルールの確認

## 目的

`MODULE-firewall-init` が適用したブラックリストが実際に効いているかを、コンテナに入らずに
確認できるようにする(FR-env-05)。

## 処理の流れ

1. `MODULE-cli-common-container-name` で対象コンテナ名を決める。
2. `MODULE-cli-common-is-running` が偽なら「❌ コンテナが起動していません」を表示して `exit 1`。
3. `docker exec <name> iptables -L OUTPUT -n --line-numbers` を実行し、出力をそのまま流す。

## 呼び出され方

- 契機: 利用者が `claude-dev firewall` を実行したとき。
- 前提条件: 対象コンテナが稼働中で、`NET_ADMIN` 権限付きで起動していること。
- 引数: なし。

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| (なし) | - | - | 対象はカレントディレクトリ由来のコンテナ |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

### MODULE-cli-common-container-name

- 何のために呼ぶか: 対象コンテナ名の決定。 / 何を渡すか: なし。 / 何を受け取るか: コンテナ名。
- **失敗したときどうなるか**: 想定されない。

### MODULE-cli-common-is-running

- 何のために呼ぶか: 未起動での exec を避けるため。 / 何を渡すか: コンテナ名。 / 何を受け取るか: 終了ステータス。
- **失敗したときどうなるか**: 「❌ コンテナが起動していません」を出して `exit 1`。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | `iptables` の終了ステータス(未起動時は 1) |
| 永続化 | なし(読み取りのみ) |
| 発火するイベント | なし |
| ログ | `iptables -L OUTPUT` の出力をそのまま端末へ |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| コンテナが未起動 | 日本語エラーを出して `exit 1` | 利用者は `start` する |
| `iptables` の権限が無い(`NET_ADMIN` 無しで起動) | `iptables` が Permission denied で失敗し非0終了する | ルールを確認できない |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | `docker exec` に `-u` を付けない(`iptables` の参照に root が要るため)。`MODULE-cli-common-resolve-container-user` の上書き対象外である | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| `OUTPUT` チェインしか表示しない | INPUT/FORWARD や ipset の中身は見えない | なし |
