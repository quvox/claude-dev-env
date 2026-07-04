# 変更履歴: 03_security.md

> 対応文書: `docs/03_security.md`（旧 `docs/security.md`）

## 2026-06-08
- `docs/security.md` → `docs/03_security.md` にリネーム（番号付け整理）。
- 冒頭に「この文書の役割」を追記。
- 完全性確認に伴う実装整合修正:
  - Docker Socket Proxy のエンドポイントポリシーを実装に一致させた。`/containers/{id}/attach` は「明示的に拒否」ではなく接続ハイジャックによる中継（許可）であると訂正。全面拒否は `/swarm`・`/plugins`・`/configs`・`/secrets` のパス前方一致のみと明記し、privileged exec の拒否も追記。
  - 認証情報の保護（§2）の図を実装に一致させた。`start` 時の認証ファイルコピーは claude-dev CLI 側、entrypoint は symlink 化・パーミッション調整・書き戻しを担当、と修正。
- 「KVM デバイスの扱いと特権の非対称性」セクションを追加。デバイス渡しの条件・用途・proxy の Devices 拒否との非対称性・リスク評価を記載。
- KVM デバイス渡しを `--kvm` のオプトインに変更したのに合わせ、デバイス渡しの条件・リスク評価を「既定で渡さず、`--kvm` 指定セッションのみ隔離を緩める」に更新。

## 2026-07-04（/workspace 配下 bind の許可）
- §5 に「/workspace 配下 bind の許可」を追加。DooD で最も危険な任意ホストパス bind は拒否したまま、呼び出し元プロジェクトの /workspace 配下（＝エージェントが既に全 RW を持つ範囲）だけ bind を許可する緩和を設計。
- proxy が送信元 IP から呼び出しコンテナを特定し /workspace のホスト側 source(PROJECT_DIR)を得て、/workspace/… を PROJECT_DIR/… に書き換え。特定不能時は従来どおり拒否（安全側）。..・symlink 脱出は封じ込め検査で拒否。既定有効・CLAUDE_DEV_ALLOW_WORKSPACE_BINDS=0 で無効化可。攻撃耐性表・Binds 検査行を更新。
- VM モード（virtiofs uid 制約で DB 等の chown 失敗）と異なり実ホスト fs bind で chown も通る。両者は併存。

## 2026-07-04（整合性確認による調整）
- 設計↔実装仕様の徹底整合確認（独立3試行）を受けた微修正。無効化値を `0`（`false`/`no`/`off` も可）と明記し実装仕様(50)・コードと一致させた。緩和と VM モードの併存・攻撃耐性表の記述整合を確認。

## 2026-07-04（/workspace bind 封じ込めを字句的に修正・残存リスク明記）
- 実機で /workspace 配下 bind が全拒否される不具合を修正。原因は封じ込めの symlink 実体解決（EvalSymlinks/Lstat）が、ホスト FS を持たない proxy コンテナ内では常に失敗し既存祖先が / に落ちて全 bind を拒否していたこと。
- 封じ込めを字句的（Clean＋.. 拒否＋prefix）に限定。proxy はホスト symlink を解決できず（socket のみ・proxy へは docker exec 可能ゆえホスト FS マウントも不可）、プロジェクト内 symlink のホスト外脱出は残存リスクとして §残存リスクに明記（無効化は CLAUDE_DEV_ALLOW_WORKSPACE_BINDS=0、より強い隔離は VM モード）。
