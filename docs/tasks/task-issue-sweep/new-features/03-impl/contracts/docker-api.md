---
target: docs/03-impl/contracts/docker-api.md
change: replace
version_bump: minor
sections:
  - "## 実装上の事実"
deletes: []
reason: 'issue 087(所有者ラベルの注入に失敗したときコンテナ作成経路だけログが出ない)の 03 契約層。`02-design/logging.md`「所有者ラベルを付与せずに中継した」は付与しなかった理由を出すことを無条件に求めており(`FR-env-07` 受入基準12)、**仕様が既に正しく実装だけが追いついていない**。「付与できないとき」の行から、コンテナ経路だけログが出ないという事実の記述を外し、両経路で理由を出す実装後の姿へ改める。**拒否判定・注入の対象経路・上書きの規則は1文字も変えない**'
reflected: 2026-08-12
---

## 実装上の事実

| 項目 | 実際の値 | 定義箇所 |
|---|---|---|
| 待ち受け | `http.ListenAndServe(listenAddr, handler)` の単一ハンドラ透過プロキシ(ルート登録は無い) | `docker-proxy/main.go:497` |
| 遮断するパス | 版接頭辞を除いた `cleanPath` が `/swarm` / `/plugins` / `/configs` / `/secrets` に前方一致すれば、**メソッドを問わずボディを見ずに** `403`(本文 `blocked: <path> is not allowed`) | `docker-proxy/main.go:388`〜`393`(`blockedPathPrefixes`), `:449`〜`455` |
| 判定の順序 | 上記のパス遮断 → (POST の create / exec create だけ)Privileged → PidMode=host → NetworkMode=host → UsernsMode=host → bind の書き換え/拒否 → 危険なケーパビリティ → デバイス割り当て | `docker-proxy/main.go:437`〜`480`, `:637`〜`682` |
| **所有者ラベルの注入** | **拒否判定をすべて通過したあと**、トップレベル `Labels` へ `claude-dev.role=spawned` と `claude-dev.owner-project-dir=<呼び出し元コンテナの claude-dev.project-dir>` を書く。**利用者が同じキーを指定していたら上書きする**。対象は `POST /containers/create` と `POST /networks/create` の2経路(版接頭辞の有無を問わない)。**ボディの再構成は要求あたり1回**で、`r.Body` / `ContentLength` / `Content-Length` を同時に更新する | `docker-proxy/main.go:309`(注入), `:341`(書き戻し), `:350`(ネットワーク経路), `:401`(経路の正規表現), `:469`(分岐) |
| **付与できないとき** | 呼び出し元を特定できない・`claude-dev.project-dir` が空・ボディが JSON として読めない・注入に失敗した、のいずれでも**元のボディのまま中継し、拒否しない**。**付与しなかった理由は `NO-OWNER-LABEL` としてログへ出す**(ネットワーク経路は「呼び出し元を特定できない」と「ボディを書き換えられない」の2つ、コンテナ経路は「呼び出し元を特定できない」のみ)。**コンテナ経路でも、所有者は解決できたが注入に失敗した場合にログを1行出す**(理由は「ボディを書き換えられない」) | `docker-proxy/main.go:309`〜`:336`(所有者が空なら no-op), `:350`〜`:367` |
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
