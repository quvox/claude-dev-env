---
id: 024-modify-stop-can-delete-other-projects-compose-resources
type: modify
severity: 中
found: 2026-08-03
found_in: task-impl-depth のフェーズ2(D0-scope-07 の起票の閾値を 03-impl 全体へ掃引した際に確定)
related: MODULE-cli-stop, CTR-cli-container, MODULE-cli-start, FR-env-01, NFR-scale-01
summary: compose プロジェクト名の正規化が非可逆なため、stop が別ディレクトリの compose コンテナとネットワークを巻き込んで削除しうる
---

# 024 `stop` が別プロジェクトの compose 資源を削除しうる

## 事象

コンテナ名は `basename $(pwd)` を小文字化し `[a-z0-9._-]` 以外を `-` に置換して作る
(`claude-dev:245`〜`:247`)。compose プロジェクト名はさらに `[a-z0-9_-]` 以外を `-` に置換する
(`claude-dev:820`)。**この変換は非可逆で衝突する。**

例: `~/work/My.App` と `~/other/my-app` はどちらも compose プロジェクト名 `my-app` になる
(`.` が `-` に落ちる)。

`stop` は**ラベルだけ**で削除対象を決める(`claude-dev:1134`〜`:1136`):

```
docker ps -a --filter "label=com.docker.compose.project=${_cproj}" -q | xargs -r docker rm -f
docker network rm "${_cproj}_default"
```

そのため一方のディレクトリで `claude-dev stop` を実行すると、**もう一方のディレクトリで
起動した compose コンテナとそのネットワークも削除される**。実行者側には削除件数も対象名も
表示されないため、**成功表示(`✅ <name> を停止しました`)と区別できない**。

再現手順:

1. `~/work/My.App` で `claude-dev start` し、コンテナ内で `docker compose up -d` する。
2. `~/other/my-app` で `claude-dev start` し、同じく `docker compose up -d` する。
3. 後者で `claude-dev stop` を実行する。
4. 前者の compose コンテナが消えていることを確認する(前者のセッションは残る)。

## 影響

他プロジェクトの実行中サービス(DB・キュー等)が予告なく削除される。**データの破壊**に至りうる
(名前付きボリュームは残るが、実行中の処理は失われる)。実行者は気づけず、巻き込まれた側は
原因に到達しにくい。

severity を「中」とした根拠: ディレクトリ名が正規化後に衝突する場合に限られる。ただし
`.` を含むディレクトリ名は珍しくなく、被害はデータ側に及ぶ。

## 原因の見当

推測: 「1ディレクトリ = 1セッション」を名前だけで表現する設計(`D0-scope-02`)の帰結。
`start` 側の `COMPOSE_PROJECT_NAME` 生成と `stop` 側の再計算が同じ変換を使うことは保証されているが、
**変換の一意性は誰も保証していない**。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| プロジェクト名の一意性 | 正規化は非可逆で衝突しうる(`MODULE-cli-stop` / `CTR-cli-container` の「既知の制限」に事実として記述) | `NFR-scale-01` は「名前・ポート・プロファイルの一意化で衝突を避ける」と**一意化を要求**している | **設計が正**(実装が一意化を保証していない) |

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | プロジェクト名に**パスのハッシュ短縮値**を付ける(例: `my-app-3f2a1b`)。`start` と `stop` の双方が同じ関数を使う | `claude-dev` / `claude-dev-mac` の名前生成、`CTR-cli-container`、`MODULE-cli-start` / `-stop`、既存セッションの移行手順 |
| B | `stop` が削除前に対象コンテナ名を表示し、`--yes` が無ければ確認する | 同2本と `MODULE-cli-stop` |
| C | `stop` の compose 片付けを、当該 claude-dev コンテナが作ったものに限定する(ラベルに起動元コンテナ ID を足す) | 起動側と停止側の両方 |

推奨は **A**(根本の一意性を回復する。既存セッション名が変わる移行を伴う)。

## 経緯

- 2026-08-03 起票。`task-impl-depth` のフェーズ2で `D0-scope-07` の起票の閾値((a) データ破壊 +
  実行者が気づけない / (b) 未追跡)を 03-impl 全体へ掃引した際に確定。**コードは変更しない。**
