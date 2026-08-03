---
id: docker-api
version: 1.0.0
updated: 2026-08-03
source:
  - docs/02-design/contracts/docker-api.md
kind: other
impl: docker-proxy/main.go::validateContainerCreate
summary: コンテナからの Docker Engine API 要求を docker-proxy が検査・書き換え・拒否する取り決め(実装側)
keywords: [契約, CTR, 実装]
verified:
  at: 2026-08-03
  version: 1.0.0
  against:
    - doc: docs/02-design/contracts/docker-api.md
      version: 1.0.0
---

# CTR-docker-api コンテナ → docker-proxy(実装)

- 実装: `docker-proxy/main.go::validateContainerCreate`(コンテナ作成の検査)、
  `docker-proxy/main.go::validateExecCreate`(コマンド実行の検査)、
  `docker-proxy/main.go::rewriteBinds`(bind の書き換え)、
  `docker-proxy/main.go::containWorkspacePath`(パスの封じ込め)
- 当事者: Claude コンテナ → MOD-docker-proxy → ホストの Docker Engine
- 対応する設計: `docs/02-design/contracts/docker-api.md`

## 実装上の事実

| 項目 | 実際の値 | 定義箇所 |
|---|---|---|
| 待ち受け | `http.ListenAndServe(listenAddr, handler)` の単一ハンドラ透過プロキシ(ルート登録は無い) | `docker-proxy/main.go:371` |
| 遮断するパス | 版接頭辞を除いた `cleanPath` が `/swarm` / `/plugins` / `/configs` / `/secrets` に前方一致すれば、**メソッドを問わずボディを見ずに** `403`(本文 `blocked: <path> is not allowed`) | `docker-proxy/main.go:274`〜`279`(`blockedPathPrefixes`), `:330`〜`336` |
| 判定の順序 | 上記のパス遮断 → (POST の create / exec create だけ)Privileged → PidMode=host → NetworkMode=host → UsernsMode=host → bind の書き換え/拒否 → 危険なケーパビリティ → デバイス割り当て | `docker-proxy/main.go:318`〜`354`, `:506`〜`551` |
| Privileged | `true` なら拒否(`privileged containers are not allowed`) | `docker-proxy/main.go:506` |
| PidMode | `host` なら拒否 | `docker-proxy/main.go:511` |
| NetworkMode | `host` なら拒否 | `docker-proxy/main.go:514` |
| UsernsMode | `host` なら拒否 | `docker-proxy/main.go:517` |
| bind | `allowWorkspaceBinds` が有効かつ呼び出し元を特定できたときのみ、`/workspace` 配下を実ホストパスへ書き換える。それ以外は絶対パスの bind をすべて拒否する | `docker-proxy/main.go:526`〜`531`, `158` |
| パスの封じ込め | `filepath.Clean` 後に `projectDir` 配下かを検査する(symlink の実体解決はしない) | `docker-proxy/main.go:137` |
| 危険なケーパビリティ | `CapAdd` の各要素を大文字化し `dangerousCapabilities`(**`SYS_ADMIN` / `SYS_PTRACE` / `SYS_RAWIO` / `SYS_MODULE` / `DAC_READ_SEARCH` の5件**)に該当すれば拒否(`capability <名前> is not allowed`) | `docker-proxy/main.go:264`〜`271`, `:541`〜`544` |
| デバイス割り当て | 1件でもあれば拒否(`device mappings are not allowed`) | `docker-proxy/main.go:548` |
| コマンド実行の検査 | exec 作成要求の `Privileged` が `true` なら拒否 | `docker-proxy/main.go:560`〜`572` |
| ボディが解釈できない | 警告ログを出して**中継を許可する**(`return nil`) | `docker-proxy/main.go:493`〜`496` |
| `HostConfig` が無い | 検査せず許可する | `docker-proxy/main.go:500` |
| 呼び出し元の特定 | 接続元 IP からプロジェクトディレクトリを解決し、結果をキャッシュする | `docker-proxy/main.go:70`, `88`, `257` |
| 切替スイッチ | `allowWorkspaceBinds` は環境変数 **`CLAUDE_DEV_ALLOW_WORKSPACE_BINDS`** で切り替える。小文字化した値が `0` / `false` / `no` / `off` のときだけ無効(=全ホスト bind を拒否)、それ以外(未設定を含む)は有効 | `docker-proxy/main.go:32`〜`41` |
| 拒否時の応答 | `http.Error` による `403 Forbidden`。本文は平文 `blocked: <理由>`(`Content-Type: text/plain; charset=utf-8`)。同時に `BLOCKED ...` をログへ出す | `docker-proxy/main.go:333`, `:342`, `:351` |
| 中継の失敗 | `ErrorHandler` が `502 Bad Gateway`(本文 `proxy error: <err>`)を返しログへ出す | `docker-proxy/main.go:312`〜`315` |
| 起動時にソケットが無い | `Fatal` で終了する | `docker-proxy/main.go:294`〜 |

## 設計との差異

差異なし。

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| symlink の実体解決を行わない(字句的な封じ込めのみ) | ホスト側の symlink による脱出は検出できない。プロキシはホストのファイルシステムを持たないため実体解決が原理的にできない | なし |
| 解釈できないボディを中継する | 独自解釈で正常な操作を弾かない代わりに、検査をすり抜ける要求が Docker Engine まで届く(最終判断は Docker が行う) | なし |
| ログが全プロジェクト分で混ざる | 共有常駐のため、拒否の記録から呼び出し元を特定するには接続元 IP を追う必要がある | なし |
