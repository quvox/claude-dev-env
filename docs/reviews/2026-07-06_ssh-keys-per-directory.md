# レビュー: SSH 鍵のディレクトリ単位切り替え（claude-dev）

対象: `claude-dev`（`load_ssh_keys_from_config` / `_parse_ssh_keys_yaml` / `ensure_ssh_agent`）、実装仕様 `docs/impl/10_cli.md`、利用者向け `docs/01_getting-started.md` / `docs/04_cli-reference.md` / `docs/03_security.md`
日付: 2026-07-06

## 変更概要
- プロジェクト直下 `.claude-dev.yaml`（`ssh_keys:`）を最優先、無ければグローバル `~/.config/claude-dev.yaml` を使う鍵解決に変更。
- ホストの環境 agent を使わず、**プロジェクト専用 ssh-agent**（`~/.claude-dev/agents/<name>.sock`）を起動/再利用し、解決した鍵だけを登録・転送。
- 既登録鍵は指紋照合でスキップ（パスフレーズ再入力回避）。鍵 0 件時は SSH 転送しない。

## 観点別所見

### 1. 要件・ユースケース合致
- ○ 「ディレクトリごとに ssh-add する鍵を変えたい」を満たす。専用 agent により別プロジェクトの鍵はコンテナから見えない（隔離）。
- 実機相当の検証（サンドボックス、bash 実行）で確認:
  - projA→鍵a のみ / projB→鍵b のみ に隔離されること
  - 設定なしディレクトリはグローバル（自動生成含む）へフォールバックすること
  - 再実行で agent を再利用し、既登録鍵を再 add しないこと（冪等・パスフレーズ再入力なし）

### 2. 無駄な処理
- 起動ごとに鍵数分 `ssh-keygen -lf` を実行するが、パスフレーズ付き鍵の再入力回避という明確な便益がありコストは軽微。許容。

### 3. 処理時間
- 追加コストは agent 起動（初回のみ）と指紋照合のみ。無視できる。

### 4. セキュリティ脆弱性
- ○ 秘密鍵ファイルは非マウント（従来の不変条件を維持）。転送は agent ソケットのみ。
- ○ むしろ最小権限が向上：環境 agent（全鍵保持しうる）を丸ごと転送せず、そのプロジェクトの指定鍵のみに限定。
- 対応済み: 専用ソケット置き場 `~/.claude-dev` / `agents` を `chmod 700` に設定（他ローカルユーザーからの接続防止・多層防御）。ソケット実体は ssh-agent が `0600` で作成。
- 既知の制限（見送り、理由付き）:
  - 専用 agent はパスフレーズ復号済みの鍵をホスト上に常駐保持する（従来方式・macOS 版と同じ姿勢）。用途上許容。
  - Unix ソケットパス長（約 108 byte）制限。深い `$HOME` や極端に長いディレクトリ名で `ssh-agent -a` が失敗し得るが、その場合は警告して SSH 転送なしで継続する（クラッシュしない）。一般的な `$HOME` では問題にならないため、名前ハッシュ化等の追加対応は見送り。

## 結論
要件を満たし、整合性・安全性ともに問題なし。実装仕様（10_cli.md）および利用者向けドキュメントと一致。

---

## 追記 2026-07-06: macOS 版（claude-dev-mac）も per-directory 化

`claude-dev-mac`（方式D: 専用 agent＋socat TCP ブリッジ）も同方針で per-directory 化した。

- 専用 agent／ブリッジを**プロジェクト（ディレクトリ）ごと**に分離（`~/.claude-dev/agents/<name>.{sock,pid,bridge.pid,bridge.port}`）。ブリッジはプロジェクトごとに別ポート。
- 鍵解決は `<PROJECT_DIR>/.claude-dev.yaml` → グローバル `~/.config/claude-dev.yaml`（未選択時のみ対話選択）。既登録鍵は指紋照合でスキップ。
- `stop` は当該プロジェクトのブリッジのみ停止（agent は鍵保持のため残置）。`ssh-keys reset` は全プロジェクト agent/ブリッジ＋旧 LEGACY を掃除。
- サンドボックスで e2e 検証済み: ディレクトリ隔離（projA→鍵a / projB→鍵b）、プロジェクトごと別ポート、ブリッジ往復でコンテナ相当ソケットが当該鍵のみ参照、stale ソケット再生成、stop の局所停止。

### 設計↔実装仕様の整合性確認（徹底確認）
- 周回1（3観点の並行独立監査: mac／Linux／全 docs 横断 sweep）で不整合4件を検出し修正:
  1. `docs/impl/INDEX.md` の 11_cli-mac 説明が「SSH agent 魔法ソケット」という廃止済み方式のままだった → 方式D（per-project 専用 agent＋socat TCP ブリッジ）に修正。
  2. `docs/impl/10_cli.md` の `ensure_ssh_agent` 説明に `SSH_ASKPASS_REQUIRE=force` の記載漏れ → 追記。
  3. `docs/impl/11_cli-mac.md` の start SSH 手順が制御フロー（socat 判定は `ensure_ssh_bridge` 内・`.claude-dev.yaml` 案内は鍵なし分岐のみ）とずれていた → 実コードに一致させ書き直し。
  4. `docs/09_macos-support.md` の「Linux 版: ホストの $SSH_AUTH_SOCK をそのまま bind mount」が旧方式の現在形記述だった → 専用 agent ソケットの直 bind mount に修正。
- 周回2（前回結果を持ち越さない独立監査）で**実装を誤らせる不整合ゼロ・doc↔code 不一致ゼロ**を確認し、確認作業を終了（残る LOW 指摘は `03_security.md` §1 マウント一覧が Linux 前提という既存の粒度差で、矛盾ではない）。

---

## 追記 2026-07-06: SSH 鍵解決を「ローカル `.claude-dev.yaml` のみ」に簡素化

利用者要望により、グローバル `~/.config/claude-dev.yaml` へのフォールバック・自動生成・（mac の）start 時対話選択を廃止し、**SSH 鍵はプロジェクト直下 `.claude-dev.yaml` の `ssh_keys` のみ**を見る方式に統一した。

- Linux `claude-dev`: `USER_CONFIG` 削除、`load_ssh_keys_from_config` はローカルのみ、0 件時は `.claude-dev.yaml` への記述を案内。
- mac `claude-dev-mac`: `USER_CONFIG`/`config_has_ssh_selection`/`load_config_ssh_keys`/`write_config_ssh_keys` 削除。`resolve_ssh_keys_for_start` はローカルのみ。`ssh-keys` は**カレントプロジェクトの `.claude-dev.yaml`** に対話保存、`reset` は**プロジェクト単位**（該当 `.claude-dev.yaml` の ssh_keys 除去＋当該 agent/ブリッジ停止＋LEGACY 掃除）。
- サンドボックス検証: ローカルのみ採用・グローバル非参照（既存グローバルがあっても無視）、ローカル無し→0 件、`ssh-keys` 相当がカレントの `.claude-dev.yaml` に保存、`reset` のファイル処理（ssh_keys のみ→削除／他記述→保持）を確認。

### 設計↔実装仕様の整合性確認（徹底確認・簡素化分）
- 周回1（mac／Linux＋全 docs sweep の並行独立監査）で不整合を検出・修正:
  1. `claude-dev-mac` の start SSH 部コメントが旧挙動（グローバル選択／対話保存）のまま → ローカルのみに修正。
  2. `claude-dev-mac` の `ssh-keys` ヘッダコメントが保存先を「config」と無限定表記 → `./.claude-dev.yaml` に明記。
  （Linux 側＋docs 全体 sweep は不整合ゼロ。削除シンボルの残存参照なしを grep で確認。）
- 周回2（独立監査）で軽微1件を検出・修正:
  3. `docs/04_cli-reference.md` の mac 差分説明が「VM/KVM と直結案内のみ」と断言し、`ssh-keys` サブコマンドと SSH 転送方式差が抜けていた → 4 点の差分に補記。
- 以上いずれも「実装を誤らせる矛盾」ではない。core（設計/実装仕様/コードのパス・関数名・引数・分岐・メッセージ）は両周回とも一致を確認。両スクリプト `bash -n` OK。
