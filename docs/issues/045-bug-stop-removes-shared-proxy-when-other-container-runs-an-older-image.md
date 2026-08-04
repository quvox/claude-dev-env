---
id: 045-bug-stop-removes-shared-proxy-when-other-container-runs-an-older-image
type: bug
severity: 中
found: 2026-08-04
found_in: task-fix-start-cleanup のフェーズ3(実機確認の後片付けで実際に発生。Claude が観測)
related: FR-env-01, MODULE-cli-stop, MODULE-cli-common-ensure-infrastructure, CTR-cli-container, docs/issues/024, docs/issues/025
summary: stop の遊休判定が `--filter ancestor=<現在のイメージ>` なので、古いイメージで稼働している Claude コンテナを数え落とし、共有 docker-proxy を削除する。FR-env-01 受入基準9 に反し、他プロジェクトのコンテナから Docker が使えなくなる
---

# 045 `stop` が古いイメージの稼働コンテナを数え落として共有 docker-proxy を消す

## 事象

**2026-08-04 に実機で観測した。** `claude-dev stop web` を実行したところ、
**別プロジェクトの Claude コンテナ(`claude-dev-env`)が稼働中なのに**
共有の `claude-dev-docker-proxy` が「Claude コンテナなし」として削除された。

```
✅ web を停止しました
🐳 Docker Socket Proxy コンテナを停止しました（Claude コンテナなし）
$ docker ps --format '{{.Names}}' | grep claude-dev-env
claude-dev-env          ← 稼働中である
```

原因は遊休判定の書き方である。

```
count=$(docker ps --filter "ancestor=$IMG_CLAUDE" --filter "ancestor=$IMG_CLAUDE_VNC" -q 2>/dev/null | wc -l)
```
(`claude-dev:384` 付近)

`docker ps --filter ancestor=<名前>` は **その名前が今指しているイメージ ID から作られたコンテナ**
だけに一致する。観測時の値は次のとおりで、`claude-dev-env` は**古いイメージ**で動いていたため
数に入らなかった。

| 対象 | イメージ |
|---|---|
| 稼働中の `claude-dev-env` | `sha256:8e71ac11409a…`(`docker inspect` の `.Image`) |
| 現在の `claude-dev-claude-vnc:latest` | `68e296de0c73` |

イメージを再ビルド・再取得(`make upgrade` / `claude-dev pull`)すると `latest` が別 ID を指すため、
**その前に起動していたコンテナはすべて数え落とされる**。長く起動したままのコンテナがあるほど起きやすい。

## 影響

- **`FR-env-01` 受入基準9「IF 他プロジェクトの Claude コンテナが稼働中ならば、`stop` は
  docker-proxy を停止してはならない」に反する**(実装が誤り。要件は明確なので、どちらが正かの
  裁定は要らない)。
- 稼働中の他プロジェクトのコンテナは `DOCKER_HOST=tcp://claude-dev-docker-proxy:2375` を
  持ったままなので、**コンテナ内から `docker` が一切使えなくなる**(`docker: Cannot connect…`)。
  作業中の利用者にはコンテナが壊れたように見える。
- **利用者は気づけない**: `stop` の出力は「Claude コンテナなし」と述べるだけで、
  数え落としたコンテナがあることを示さない。
- 復旧は「どれかのディレクトリで `claude-dev start` を実行する」(= `ensure_docker_proxy_container`
  が作り直す)だが、それを知らなければ分からない。**データは失われない。**

## 原因の見当

**推測**: 実装当時は「イメージ名 = 一意」という前提が置かれていた。`ancestor` フィルタが
**タグではなくイメージ ID で照合する**ことと、`latest` が動く前提が噛み合っていない。

## 正はどちらか

**実装が誤り。** `FR-env-01` 受入基準9 が「他プロジェクトの Claude コンテナが稼働中なら止めない」と
明示している。数え方の欠陥であり、要件・設計を変える理由は無い。

## 対処案

| 案 | 内容 |
|---|---|
| A | 数え方を**イメージに依存しない印**に変える(起動時に `--label claude-dev.managed=1` を付け、`docker ps --filter label=claude-dev.managed=1` で数える)。`CTR-cli-container` の起動オプションが増える。既存の稼働コンテナはラベルを持たないので、移行期は B と併用する |
| B | `ancestor` に**イメージ ID の履歴**を足す(`docker images -q claude-dev-claude-vnc` の全 ID を列挙して `--filter ancestor=<id>` を並べる)。ラベル不要だが、削除済みイメージで動くコンテナは依然数え落とす |
| C | コンテナ**名の規約**で数える(現状の命名はディレクトリ名なので規約が無く、`docs/issues/028` の一意化と一体で決める必要がある) |

**推奨は A**(印を明示的に持たせるのが最も確実)。ただし `CTR-cli-container` の変更を伴うので
**コード変更を含む別タスク**である。`docs/issues/024` / `025`(`stop` / `logout` / `reset` が
他プロジェクトの資源を巻き込む)と同根なので、まとめて扱うのが効率的。

## 経緯

- 2026-08-04 起票(`task-fix-start-cleanup` のフェーズ3)。実機確認の後片付けで
  `claude-dev stop web` を実行した際に発生し、**その場で `docker-proxy` を再作成して復旧した**
  (`claude-dev:418`〜`:426` と同じ `docker run` を手で実行し、`claude-dev-env` から
  `docker ps` が通ることを確認した)。本タスクの範囲外なので修正はしていない。
