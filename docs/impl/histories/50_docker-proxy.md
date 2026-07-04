# 変更履歴: 50_docker-proxy.md

> 対応文書: `docs/impl/50_docker-proxy.md`

## 2026-06-08
- 新規作成。`docker-proxy/`（Go）の定数・リクエスト処理フロー・検査ロジック（container create / exec create）・接続ハイジャック中継・テスト観点を記述。

## 2026-07-04（/workspace 配下 bind の許可・書き換え）
- validateContainerCreate の Binds/Mounts 拒否ループを processBinds 方式へ変更。allowWorkspaceBinds（env CLAUDE_DEV_ALLOW_WORKSPACE_BINDS、既定有効）時、送信元 IP→resolveProjectDir（GET /containers/json で IP 一致コンテナの /workspace マウント source を解決・TTL60s キャッシュ・テスト用に var で注入可）で PROJECT_DIR を得る。
- containWorkspacePath: /workspace 配下のみ許可し PROJECT_DIR/<相対> へ書換、/workspace 外拒否・filepath.Clean で .. 脱出拒否・既存祖先の EvalSymlinks で symlink 脱出拒否。rewriteBinds: top と HostConfig を map[string]json.RawMessage で保持し Binds(src のみ)・Mounts(Source のみ)だけ再エンコードして他フィールドを保全。変更時 r.Body/Content-Length を更新。projectDir="" (無効/未解決)は絶対 bind を全拒否＝従来動作。
- 追加定数 workspaceMount/projectCacheTTL、dockerHTTP(unix クライアント)。docker-proxy/binds_test.go(新規)で封じ込め・書換・Mounts・空 projectDir・結合(validateContainerCreate 経由の body 書換)を検証。既存テスト（host bind/bind mount 拒否）は未解決フォールバックで引き続き緑。
- 検証: go build/vet/test 緑（新規8件＋既存全件）。**実機 E2E は proxy イメージ再ビルド＋proxy 作り直しが必要**（共有・常駐のため稼働中プロジェクトに一時影響）。

## 2026-07-04（整合性確認による調整）
- 仕様↔コードの徹底整合確認（独立試行）を受けた微修正。無効化受理値に `off` を追記（コード allowWorkspaceBinds と一致）。カバーするコード一覧とテスト節に `binds_test.go` を反映。関数/定数・挙動・TTL・フォールバックはコードと一致を確認。

## 2026-07-04（containWorkspacePath を字句的封じ込めに修正）
- 実機不具合修正: containWorkspacePath の symlink 検査（EvalSymlinks/existingAncestor）を削除。proxy コンテナはホスト FS を持たず、ホストパス（/home/.../<project>）が proxy 内に存在しないため existingAncestor が / に落ち、封じ込め検査が常に false＝/workspace 配下 bind を全拒否していた。字句的封じ込め（Clean＋.. 拒否＋prefix）に統一。evalSymlinksOr/existingAncestor ヘルパー削除。
- binds_test.go: TestContainWorkspacePath_SymlinkEscape を TestContainWorkspacePath_LexicalOnly に置換（symlink は非解決で字句的に受理・.. は拒否を検証）。go build/vet/test 緑。
- 実機 E2E（hisol-work・proxy 再ビルド＋作り直し後）: docker run -v /workspace/docker/init.sql:/t.sql:ro が REWRITE→/home/t-kubo/workspace/hisol-work/docker/init.sql にマウントされ実ファイル読取成功。proxy ログに REWRITE binds を確認。
