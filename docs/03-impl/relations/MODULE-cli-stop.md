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
updated: 2026-08-04
summary: セッションを停止し、遊休なら docker-proxy と ssh ブリッジも止める
---

# MODULE-cli-stop セッションの停止

## 目的

1つのプロジェクトの Claude セッションと、そのセッションから作られた副産物
(ポートフォワード用コンテナ・compose 資源・共有 docker-proxy)を片付ける
(FR-env-01・FR-env-07)。**他プロジェクトの資源に触れないことを意図するが、実装には影響しうる
経路が2つある**: compose プロジェクト名の正規化が衝突すると別プロジェクトの compose コンテナを
巻き込んで削除する(`docs/issues/024`)、および `stop_proxy_if_idle` の「Claude コンテナ0件」判定と
他プロジェクトの起動が競合すると共有 docker-proxy を消す(下の「異常系」)。

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

| 引数 | 型 | 必須 | 実装が行う検証 | 受理/拒否と結果 |
|---|---|---|---|---|
| `NAME` | 文字列 | 任意 | **非空かどうかだけ**を見る | 非空ならその文字列をコンテナ名として使う。省略・空文字ならカレントディレクトリ名を小文字化し `[a-z0-9._-]` 以外を `-` に置換した値を使う |
| 第2引数以降 | — | — | — | **黙って無視する** |

**`NAME` の境界値の実際の扱い**(検証が無く、名前の文字列一致だけで対象を決める):

| 入力 | 実際の結果 |
|---|---|
| 実在するコンテナ名 | 停止・削除して `✅ <name> を停止しました` |
| 実在しない名前・綴り違い・大文字を含む名前 | `ℹ️ <name> は存在しません` と表示して**終了コード 0**(綴り違いと本当に無い場合を区別しない) |
| compose 名として衝突する名前 | ラベル一致で**別プロジェクトの compose 資源も削除しうる**(`docs/issues/024`) |

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
| 戻り値 | **対象が無い場合も 0**。ただし**本体コンテナの削除だけは失敗を握らない**(`docker rm -f "$NAME"` に `|| true` が無く、`set -e`(`claude-dev:8`)により非0で終了する。`claude-dev:1125`)。中継コンテナ・compose コンテナ・compose ネットワーク・proxy の削除は `|| true` で握るため 0 のまま |
| 永続化 | コンテナ `<name>`・`fwd-<name>-*`・`<正規化NAME>` の compose コンテナを削除。compose ネットワーク `<正規化NAME>_default` を削除。遊休時のみ `claude-dev-docker-proxy` を削除。macOS では `~/.claude-dev/agents/<name>.bridge.{pid,port}` を後始末する |
| 発火するイベント | なし |
| ログ | 標準出力へ停止結果 |

### 並行性

**排他機構(ロックファイル等)を持たない。** 削除はすべて `docker rm -f` で、**存在しない対象への
削除は `|| true` で握る**ため、同じ `stop` が二重に走っても失敗しない(冪等)。

| 同時に起きること | 実際の結果 |
|---|---|
| 同じ対象に `stop` を2つ | 先行が消し終わってから後続が始まれば、後続は `container_exists` が偽で「存在しません」を表示して 0 で終わる。**`container_exists` の判定と `docker rm -f` の間で追い越されると、後続の `docker rm -f` が「No such container」で失敗し `set -e` により非0終了する**(冪等ではない) |
| `stop` と `start`(同じディレクトリ) | 保護は無い。`stop` が後なら**起動直後のコンテナが消える**。`start` が後なら停止済みの残骸を消して作り直す |
| `stop` と他プロジェクトの `start` | `stop_proxy_if_idle` の「Claude コンテナ0件」判定と、他プロジェクトの `ensure_docker_proxy_container` が競合しうる。**判定から削除までが原子的でない**ため、他プロジェクトが起動した直後に proxy を消してしまう可能性がある(その場合、他プロジェクトのコンテナ内から Docker が使えなくなる。復旧は `claude-dev start` の再実行) |
| `stop` と `forward` | 中継コンテナを `fwd-<name>-*` の一括削除で消すため、`forward` が直後に作った中継が消える(またはその逆)。害は「フォワードが無い」だけで、`unforward` と同じ状態になる |

**順序**: 中継コンテナ → 本体 → compose コンテナ → compose ネットワーク →(macOS)ブリッジ →
docker-proxy の順に片付ける。**この順序は固定**。**本体の削除に失敗した場合だけはそこで
非0終了して後続に進まない**(`set -e`)。それ以外の削除は失敗を握って後続を続ける。

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 対象が存在しない | 削除をスキップし、メッセージを出して 0 で終わる | なし |
| 他プロジェクトのコンテナが稼働中 | `stop_proxy_if_idle` が0件でないと判断し、docker-proxy を残す | 他プロジェクトの Docker アクセスが維持される |
| 判定の直後に他プロジェクトが起動した | 0件と判定済みのため docker-proxy を削除する | 他プロジェクトのコンテナ内から Docker が使えなくなる(再 `start` で復旧) |
| compose ネットワークが他から使用中 | `docker network rm` が失敗するが処理は続行する | ネットワークが残る |
| 引数 `NAME` に実在しない名前を渡した | 「存在しません」と表示して 0 で終わる。**綴り違いと本当に無い場合を区別しない** | 利用者は停止できたと誤解しうる |
| VM モードのセッション | compose がゲスト内 Docker で完結するため手順3〜4の対象外 | なし |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 名前付きボリューム・共有ネットワーク `claude-dev-net` は消さない(`docker compose down` 相当にとどめる) | D0-scope-02 |
| 2 | macOS の専用 ssh-agent は停止しない(鍵を保持したままにして再 start を速くする。停止するのはブリッジのみ) | D0-scope-03 |
| 3 | すべての削除で失敗を握る(片付けの途中で止まると、より中途半端な状態が残るため) | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| compose 資源の特定をラベルに依存する | ラベルを持たない手動起動コンテナは残る | なし(閾値の外: 残ったコンテナは `docker ps` で**確認できる**。ラベルの衝突そのものは `docs/issues/024` が扱う) |
| compose プロジェクト名の正規化が非可逆 | 大文字違い・記号違いの別ディレクトリが同じ正規化名になり、**他プロジェクトの compose コンテナを巻き込んで削除しうる** | `docs/issues/024-modify-stop-can-delete-other-projects-compose-resources.md` |
| docker-proxy の遊休判定が原子的でない | 他プロジェクトの起動と競合すると、使用中の proxy を消してしまうことがある | `docs/issues/020-modify-cli-destructive-commands-have-no-mutual-exclusion.md` |
