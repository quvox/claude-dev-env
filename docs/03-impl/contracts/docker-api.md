---
id: docker-api
version: 1.3.0
updated: 2026-08-12
source:
  - docs/02-design/contracts/docker-api.md
kind: other
impl: docker-proxy/main.go::validateContainerCreate
summary: コンテナからの Docker Engine API 要求を docker-proxy が検査・書き換え・拒否する取り決め(実装側)
keywords: [契約, CTR, 実装]
verified:
  at: 2026-08-12
  version: 1.3.0
  against:
    - {doc: docs/02-design/contracts/docker-api.md, version: 1.1.0}
---

<!-- 2026-08-04 /doc-check ssot task-impl-depth(新しい実行): **合格証を再発行した(1.0.0)。**
     直前に削除した理由(source の docs/02-design/contracts/docker-api.md が未検証)は解消した。
     本文には問題を見つけていない。★本実行は独立レンズが1つも走っていない。 -->

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
| 待ち受け | `http.ListenAndServe(listenAddr, handler)` の単一ハンドラ透過プロキシ(ルート登録は無い) | `docker-proxy/main.go:497` |
| 遮断するパス | 版接頭辞を除いた `cleanPath` が `/swarm` / `/plugins` / `/configs` / `/secrets` に前方一致すれば、**メソッドを問わずボディを見ずに** `403`(本文 `blocked: <path> is not allowed`) | `docker-proxy/main.go:388`〜`393`(`blockedPathPrefixes`), `:449`〜`455` |
| 判定の順序 | 上記のパス遮断 → (POST の create / exec create だけ)Privileged → PidMode=host → NetworkMode=host → UsernsMode=host → bind の書き換え/拒否 → 危険なケーパビリティ → デバイス割り当て | `docker-proxy/main.go:437`〜`480`, `:637`〜`682` |
| **所有者ラベルの注入** | **拒否判定をすべて通過したあと**、トップレベル `Labels` へ `claude-dev.role=spawned` と `claude-dev.owner-project-dir=<呼び出し元コンテナの claude-dev.project-dir>` を書く。**利用者が同じキーを指定していたら上書きする**。対象は `POST /containers/create` と `POST /networks/create` の2経路(版接頭辞の有無を問わない)。**ボディの再構成は要求あたり1回**で、`r.Body` / `ContentLength` / `Content-Length` を同時に更新する | `docker-proxy/main.go:309`(注入), `:341`(書き戻し), `:350`(ネットワーク経路), `:401`(経路の正規表現), `:469`(分岐) |
| **付与できないとき** | 呼び出し元を特定できない・`claude-dev.project-dir` が空・ボディが JSON として読めない・注入に失敗した、のいずれでも**元のボディのまま中継し、拒否しない**。**付与しなかった理由をログへ1行出す**。**行の形は経路と理由で分かれる**: ネットワーク経路は `NO-OWNER-LABEL network:` を「呼び出し元を特定できない」と「ボディを書き換えられない」の2つで出す。コンテナ経路は `NO-OWNER-LABEL container:` を同じ2つで出す。**ただしボディ全体が JSON として読めない場合だけは、手前の `WARN: could not parse container create body` で早期 return するため、この行ではなく WARN 側に理由が出る**(`docker-proxy/main.go:619`) | `docker-proxy/main.go:309`〜`:336`(所有者が空なら no-op), `:350`〜`:367` |
| Privileged | `true` なら拒否(`privileged containers are not allowed`) | `docker-proxy/main.go:637` |
| PidMode | `host` なら拒否 | `docker-proxy/main.go:642` |
| NetworkMode | `host` なら拒否 | `docker-proxy/main.go:645` |
| UsernsMode | `host` なら拒否 | `docker-proxy/main.go:648` |
| bind | `allowWorkspaceBinds` が有効かつ呼び出し元を特定できたときのみ、`/workspace` 配下を実ホストパスへ書き換える。それ以外は絶対パスの bind をすべて拒否する | `docker-proxy/main.go:660`〜`665`, `202` |
| パスの封じ込め | `filepath.Clean` 後に `projectDir` 配下かを検査する(symlink の実体解決はしない) | `docker-proxy/main.go:181` |
| 危険なケーパビリティ | `CapAdd` の各要素を大文字化し `dangerousCapabilities`(**`SYS_ADMIN` / `SYS_PTRACE` / `SYS_RAWIO` / `SYS_MODULE` / `DAC_READ_SEARCH` の5件**)に該当すれば拒否(`capability <名前> is not allowed`) | `docker-proxy/main.go:378`〜`385`, `:673`〜`676` |
| デバイス割り当て | 1件でもあれば拒否(`device mappings are not allowed`) | `docker-proxy/main.go:679` |
| コマンド実行の検査 | exec 作成要求の `Privileged` が `true` なら拒否 | `docker-proxy/main.go:721`〜`733` |
| ボディが解釈できない | 警告ログを出して**中継を許可する**(`return nil`) | `docker-proxy/main.go:619`〜`622` |
| `HostConfig` が無い | 検査せず許可する | `docker-proxy/main.go:635` |
| 呼び出し元の特定 | 接続元 IP からプロジェクトディレクトリを解決し、結果をキャッシュする | `docker-proxy/main.go:101`, `125`, `371` |
| 切替スイッチ | `allowWorkspaceBinds` は環境変数 **`CLAUDE_DEV_ALLOW_WORKSPACE_BINDS`** で切り替える。小文字化した値が `0` / `false` / `no` / `off` のときだけ無効(=全ホスト bind を拒否)、それ以外(未設定を含む)は有効 | `docker-proxy/main.go:45`〜`54` |
| 拒否時の応答 | `http.Error` による `403 Forbidden`。本文は平文 `blocked: <理由>`(`Content-Type: text/plain; charset=utf-8`)。同時に `BLOCKED ...` をログへ出す | `docker-proxy/main.go:452`, `:461`, `:477` |
| 中継の失敗 | `ErrorHandler` が `502 Bad Gateway`(本文 `proxy error: <err>`)を返しログへ出す | `docker-proxy/main.go:431`〜`434` |
| 起動時にソケットが無い | `Fatal` で終了する | `docker-proxy/main.go:413`〜 |

## 設計との差異

差異なし。

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| symlink の実体解決を行わない(字句的な封じ込めのみ) | ホスト側の symlink による脱出は検出できない。プロキシはホストのファイルシステムを持たないため実体解決が原理的にできない | なし |
| 解釈できないボディを中継する | 独自解釈で正常な操作を弾かない代わりに、検査をすり抜ける要求が Docker Engine まで届く(最終判断は Docker が行う) | なし |
| **印を付けられない要求が残る** | 呼び出し元を特定できない要求・解釈できないボディの要求で作られた資源は所有者ラベルを持たないため、`stop` / `reset` の片付け対象から外れる。**存在を列挙する手段が無いので利用者への表示も行わない**(`FR-env-07` 受入基準12 が明示する帰結) | `docs/issues/005`(解釈できないボディの中継そのもの) |
| ログが全プロジェクト分で混ざる | 共有常駐のため、拒否の記録から呼び出し元を特定するには接続元 IP を追う必要がある | なし |
