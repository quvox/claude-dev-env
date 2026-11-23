---
id: 2026-11-23-docker-proxy-version-update
date: 2026-11-23
record: docs/build-records/docker-proxy-version-update.md
critical: false
origin_layer: 03
issue: なし
summary: docker-proxy のビルド用 Go を 1.27.4(go.mod の go 行は 1.27)、ビルド段と実行段の alpine を 3.24 へ上げた
---

# 2026-11-23 docker-proxy の Go と基底イメージの版更新

## 変更理由

### R-01 人間の更新指示

- 起点層・根拠: 人間の要望 2026-11-23「goやpythonおよび依存モジュールなど全てについて確認して、アップデートして」(`.claude/missions/2026-11-23-version-update/requests.md`)。版の選び方は `delegation.md` §2.3、ビルドとテストの版の一致は §2.4
- 変更が必要になった条件: docker-proxy のビルド段が `golang:1.24-alpine`(最新は 1.27.4)、`go.mod` が `go 1.22`、実行段が `alpine:3.21`(2026-11-01 にサポート終了済み)だった。開発イメージの Go は作業指示 2 で 1.27.4 に上がっており、テストの処理系とビルドの処理系がずれていた

## 変更内容の要約

- ビルド段 `golang:1.24-alpine` → `golang:1.27.4-alpine3.24`(開発イメージの `GO_VERSION` と同じ patch)
- `docker-proxy/go.mod` の `go 1.22` → `go 1.27`
- 実行段 `alpine:3.21` → `alpine:3.24`
- 検査ロジック(`docker-proxy/*.go`)は変えていない

## 更新した仕様ドキュメント

| 理由ID | 仕様ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|---|
| R-01 | docs/03-impl/environments/images.md | 1.6.0 → 1.7.0 | docker-proxy イメージの2段の構成を1段落で書き、DS-04 の行を3本足した(Go を開発イメージと同じ patch に揃える・go 行を処理系の系列へ上げる・alpine は最新の minor を名指す) |

## 実装したもの

| 理由ID | 対象 | 内容 | コミット |
|---|---|---|---|
| R-01 | .devcontainer/Dockerfile.docker-proxy | ビルド段と実行段の基底の版 | cedbe54 |
| R-01 | docker-proxy/go.mod | `go` 行 | cedbe54 |

## 実施した移行

なし

### ロールバック・復旧記録

| 理由ID | 不可逆点 | 切り戻し可能な条件・期限 | 切り戻し手順 / forward-fixのみの理由と復旧手順 | 復元元 | 確認日 | 復旧確認コマンド・結果 |
|---|---|---|---|---|---|---|
| R-01 | 適用外(critical: false。イメージは作り直せる) | — | — | — | — | — |

## 機能間連携仕様書の変化

なし(ビルド定義は relations の外。`MODULE-docker-proxy-serve` の impl / tests は変わらない)

## 検討した代替案

| 論点 | 採用した案 | 棄却した代替案 | 棄却の理由 / 崩れる条件 |
|---|---|---|---|
| ビルド段のタグ | patch まで名指す(`golang:1.27.4-alpine3.24`) | minor まで(`golang:1.27-alpine`) | 再ビルドのたびに patch が動き、開発イメージで走らせたテストの処理系と黙ってずれる / 崩れる条件: テストを開発イメージ以外で走らせるとき |
| go.mod の go 行 | 処理系の系列(`go 1.27`)へ上げる | `go 1.22` のまま | 外部依存も単体ビルドの利用者も無く困る人が居ない。据え置くと標準ライブラリの既定(GODEBUG)が旧系列のまま / 崩れる条件: ライブラリとして配るとき |
| go 行の書き方 | `go 1.27` | `go 1.27.4` | patch の固定は Dockerfile の1か所に置く(2か所に書いた版はいつか食い違う)/ 崩れる条件: Dockerfile 以外でビルドするようになったとき |
| 実行段のタグ | minor(`alpine:3.24`) | patch(`alpine:3.24.4`) | 実行段に処理系は無く §2.4 の一致の対象外。patch を追わせて OS の修正を取り込む / 崩れる条件: 実行段に処理系や共有ライブラリを足すとき |

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 知見 | 今回限り(docker-proxy のイメージ固有の版の判断で、images.md の DS-04 の行に既に書いた) | 基底の minor は時間とともにサポートが切れる(3.21 は着手時点で切れていた)。版の更新の周では実行段の基底のサポート期限も見る |
