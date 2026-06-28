---
summary: Docker APIを安全に中継するGo製リバースプロキシの検査ロジック・接続ハイジャック処理・テスト仕様を記述する。
keywords: [ Docker Socket Proxy, Go, リバースプロキシ, API検査, セキュリティ, hijack, コンテナ ]
---

# 実装仕様: docker-proxy/（Docker Socket Proxy）

> **この文書の役割**: Claude コンテナから Docker API を安全に利用させるための Go 製リバースプロキシの実装仕様。セキュリティ上の位置づけは `docs/03_security.md`、ビルドは [40_devcontainer.md](40_devcontainer.md) を参照。

## 要件（なぜ必要か）

生の `/var/run/docker.sock` をコンテナへ渡すと、ホストファイルシステムのバインドマウントや privileged コンテナ起動を通じてホストを掌握できてしまう。そこで Docker API を中継しつつ、**危険な操作だけをリクエスト検査で拒否**するプロキシを共有コンテナとして挟む。Claude コンテナは `DOCKER_HOST=tcp://claude-dev-docker-proxy:2375` 経由でのみ Docker を操作する。

## カバーするコード

```
docker-proxy/
├── main.go        プロキシ本体（中継 + リクエスト検査 + hijack 対応）
├── main_test.go   検査ロジック・正規表現の単体テスト
└── go.mod         module 定義
```

## 定数・ルール定義

- `listenAddr = ":2375"`、`socketPath = "/var/run/docker.sock"`。
- `dangerousCapabilities`: `SYS_ADMIN`, `SYS_PTRACE`, `SYS_RAWIO`, `SYS_MODULE`, `DAC_READ_SEARCH`（追加を拒否）。
- `blockedPathPrefixes`: `/swarm`, `/plugins`, `/configs`, `/secrets`（メソッド問わず全面拒否）。
- 正規表現:
  - `containerCreateRe`: `POST /containers/create`（`/v{ver}` プレフィックス許容）。
  - `containerExecCreateRe`: `POST /containers/{id}/exec`。
  - `hijackEndpointRe`: `exec/{id}/start` / `containers/{id}/attach` / `exec/{id}/resize` / `containers/{id}/resize`（HTTP コネクション乗っ取りが必要なストリーミング系）。

## リクエスト処理フロー（`main` のハンドラ）

1. パスから `/v{ver}` プレフィックスを剥がした `cleanPath` を作る。
2. `blockedPathPrefixes` に前方一致したら `403 Forbidden`。
3. `POST` かつ `containerCreateRe` 一致 → `validateContainerCreate`。違反は `403`。
4. `POST` かつ `containerExecCreateRe` 一致 → `validateExecCreate`。違反は `403`。
5. `POST` かつ `hijackEndpointRe` 一致 → `handleHijack`（後述）。
6. 上記以外 → `httputil.ReverseProxy` で Unix ソケットへ中継（`ALLOW` ログ）。

ReverseProxy は `Director` で `scheme=http`/`host=docker` を設定し、`Transport.DialContext` で Unix ソケットへダイヤルする。

## 検査ロジック

### `validateContainerCreate`
リクエストボディを `readAndRestoreBody`（読み取り後に `io.NopCloser` で復元し中継可能にする）で取得し、`HostConfig` を最小構造体へ unmarshal。パース不能時は中継を許可（Docker 側の検証に委ねる）。`HostConfig` が次のいずれかに該当すれば拒否:
- `Privileged: true`
- `PidMode/NetworkMode/UsernsMode == "host"`
- `Binds` のホストパス（`/` 始まり）。名前付きボリューム（`/` 始まりでない）は許可。
- `Mounts` の `Type == "bind"`
- `CapAdd` に `dangerousCapabilities` を含む（大文字化して照合）
- `Devices` が 1 件以上（デバイスマッピング全面拒否）

### `validateExecCreate`
ボディの `Privileged: true` を拒否。

### `handleHijack`
`httputil.ReverseProxy` が HTTP Upgrade（`Upgrade: tcp`）のストリーミングを扱えないため、生 TCP で中継する。Docker ソケットへ `net.Dial("unix", ...)` し、`http.Hijacker` でクライアント接続を奪取。元 HTTP リクエストを Docker へ書き出した後、双方向に `io.Copy`（Docker→Client、Client→Docker）。Client→Docker 側は HTTP サーバの `bufio.Reader` に残ったバッファを先に流してから生コネクションをコピーする。各方向は完了時に `CloseWrite` で半クローズし、panic は recover でログ化。

## テスト（main_test.go）

`validateContainerCreate` / `validateExecCreate` と 2 つの正規表現に対する単体テスト。主な観点:
- 許可: クリーンな create、名前付きボリューム、`HostConfig` なし、空ボディ、安全な cap（`NET_ADMIN`）、通常 exec。
- 拒否: ホストバインド、bind マウント、privileged、`PidMode`/`NetworkMode`/`UsernsMode=host`、危険 cap（`SYS_ADMIN`）、デバイスマッピング、privileged exec。
- 正規表現: `containerCreateRe` / `hijackEndpointRe` がバージョン付き/なしパスを正しく判定する。

実行: `cd docker-proxy && go test ./...`。

## 注意点

- 検査はブラックリスト的に「既知の危険オプション」を拒否するもので、Docker API 全面の安全性を保証するものではない。`blockedPathPrefixes` と検査項目の更新で対応する。
- パース不能なボディは通す設計のため、検査は正規の JSON ボディを前提とする。
