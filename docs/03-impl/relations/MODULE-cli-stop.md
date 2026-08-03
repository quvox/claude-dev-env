---
id: MODULE-cli-stop
module: MOD-cli-stop
kind: tool
sync: sync
impl: claude-dev::main#stop, claude-dev-mac::main#stop
callers: なし
callees: MODULE-cli-common-container-exists, MODULE-cli-common-container-name, MODULE-cli-common-dev-agent-path, MODULE-cli-common-is-running
contracts: なし
design: DSN-mod-01, DSN-mod-02
requirements: FR-env-01, FR-env-07
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: セッションを停止し、遊休なら docker-proxy と ssh ブリッジも止める
---

# MODULE-cli-stop セッションの停止

## 目的

セッションと、そのセッションから作られた副産物(ポートフォワード用コンテナ・compose 資源・
共有 docker-proxy)を、他プロジェクトに影響を与えずに片付ける(FR-env-01・FR-env-07)。

## 処理の流れ

1. `MODULE-cli-common-container-name` で対象コンテナ名を決める(引数 `NAME` 優先)。
2. `MODULE-cli-common-container-exists` で存在を確認し、`fwd-<name>-*` の各コンテナと本体を
   `docker rm -f` する。
3. 当該コンテナ内から起動された compose コンテナ群をラベル
   `com.docker.compose.project=<正規化NAME>` で特定して `docker rm -f` する。
4. 当該プロジェクトの compose デフォルトネットワーク `<正規化NAME>_default` が残っていれば
   `docker network rm` する(`docker compose down` 相当。名前付きボリューム・共有
   `claude-dev-net`・docker-proxy は残す)。
5. **macOS 版のみ**: `stop_ssh_bridge <NAME>` で当該プロジェクトの socat ブリッジを停止する
   (専用 ssh-agent は鍵を保持するため残す)。`MODULE-cli-common-dev-agent-path` で
   `.bridge.pid` / `.bridge.port` の位置を得る。
6. `stop_proxy_if_idle`(本機能に畳み込み)を呼ぶ。`MODULE-cli-common-is-running` で
   docker-proxy の稼働を確認し、Claude コンテナが0件なら proxy を `docker rm -f` する。

## 呼び出され方

- 契機: 利用者が `claude-dev stop [NAME]` を実行したとき。
- 前提条件: なし(未起動でもエラーにしない)。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `NAME` | 文字列 | 任意 | 省略時はカレントディレクトリ由来のコンテナ名 |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

### MODULE-cli-common-container-name

- 何のために呼ぶか: 停止対象と compose プロジェクト名の決定。 / 何を渡すか: なし。 / 何を受け取るか: コンテナ名。
- **失敗したときどうなるか**: 想定されない。

### MODULE-cli-common-container-exists

- 何のために呼ぶか: 停止中の残骸も削除対象に含めるため。 / 何を渡すか: コンテナ名。 / 何を受け取るか: 終了ステータス。
- **失敗したときどうなるか**: 削除がスキップされ残骸が残る。次回 `start` が消す。

### MODULE-cli-common-is-running

- 何のために呼ぶか: docker-proxy を止めてよいか(Claude コンテナが0か)を判定するため。
- 何を渡すか: docker-proxy のコンテナ名。 / 何を受け取るか: 終了ステータス。
- **失敗したときどうなるか**: 非稼働と判定され、proxy の削除がスキップされる(害はない)。

### MODULE-cli-common-dev-agent-path

- 何のために呼ぶか: macOS の socat ブリッジの PID / ポートファイルの位置を得るため。
- 何を渡すか: コンテナ名と種別(`bpid` / `bport`)。 / 何を受け取るか: ファイルパス。
- **失敗したときどうなるか**: 未知の種別なら空パスとなり、ブリッジ停止がスキップされる(ブリッジが残る)。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 0 |
| 永続化 | コンテナ `<name>`・`fwd-<name>-*`・`<正規化NAME>` の compose コンテナを削除。compose ネットワーク `<正規化NAME>_default` を削除。遊休時のみ `claude-dev-docker-proxy` を削除。macOS では `~/.claude-dev/agents/<name>.bridge.{pid,port}` を後始末する |
| 発火するイベント | なし |
| ログ | 標準出力へ停止結果 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 対象が存在しない | 削除をスキップし、メッセージを出して 0 で終わる | なし |
| 他プロジェクトのコンテナが稼働中 | `stop_proxy_if_idle` が0件でないと判断し、docker-proxy を残す | 他プロジェクトの Docker アクセスが維持される |
| compose ネットワークが他から使用中 | `docker network rm` が失敗するが処理は続行する | ネットワークが残る |
| VM モードのセッション | compose がゲスト内 Docker で完結するため手順3〜4の対象外 | なし |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 名前付きボリューム・共有ネットワーク `claude-dev-net` は消さない(`docker compose down` 相当にとどめる) | D0-scope-02 |
| 2 | macOS の専用 ssh-agent は停止しない(鍵を保持したままにして再 start を速くする。停止するのはブリッジのみ) | D0-scope-03 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| compose 資源の特定をラベルに依存する | ラベルを持たない手動起動コンテナは残る | なし |
