# レビュー: macOS 対応（claude-dev-mac）

対象: `claude-dev-mac`（新規）、`Makefile`（OS 判定 install）、`docs/09_macos-support.md`、`docs/impl/11_cli-mac.md`、および関連ドキュメント更新（INDEX/README/01/02/04/impl-00/impl-20）
日付: 2026-07-04
ブランチ: feature/v2-orchestration

## 背景

Linux 前提の `claude-dev` を macOS（Docker Desktop）でも動かすため、ホスト側 CLI の macOS 適応版 `claude-dev-mac` を新設した。コンテナ内資産（Dockerfile / entrypoint / firewall / docker-proxy / tmux.conf）は OS 非依存のため Linux 版とそのまま共有し、OS 依存はホスト CLI に閉じた。

## 観点別所見

### 1. 要件・ユースケースに合致しているか

- ユーザー要件「claude-dev を macOS でも動くように claude-dev-mac として作る」を満たす。設計方針は AskUserQuestion で確認済み:
  - 独立スクリプトを新規作成（既存 `claude-dev` は無変更）
  - VM/KVM は明確にエラーで拒否
  - `make install` は OS 判定し macOS では `claude-dev-mac` を `claude-dev` として配置（追加指示）
  - install は symbolic link ではなく `install(1)`+`sudo`（追加指示）
- Linux 版と同じサブコマンド体系（start/code/orchestrate/attach/stop/forward/unforward/ports/list/setup/login/logout/upgrade/firewall/reset/help）を提供。利用者コマンド名はどの OS でも `claude-dev`。
- `claude-dev` と `claude-dev-mac` の差分は意図した 10 種類のみであることを `diff` で確認（余分な変更・重複なし）。実装仕様 `docs/impl/11_cli-mac.md` の D1〜D5 と一致。

### 2. 無駄な処理が含まれていないか

- VM/KVM 関連ロジック（`KVM_OPTS`/`VM_OPTS`/長時間待機/進捗表示/`vm.env` 継承/`--append-system-prompt` 注入）を macOS 版から完全に除去。`--vm`/`--kvm`/`--vm-fresh` は `require_setup`（重いイメージビルド）**より前**に早期拒否し、無駄なビルドを避ける（実測で exit 1・ビルド未発生を確認）。
- `detect_docker_sock` は 2 候補（`/var/run/docker.sock`→`~/.docker/run/docker.sock`）の最初の 1 つを返すだけの軽量関数。

### 3. 処理時間を改善できる余地がないか

- tmux 起動待ちは 30 秒固定（VM の 420 秒分岐を削除）。
- 早期 VM 拒否によりエラーケースのビルド時間ゼロ化。
- それ以外はホスト側の軽量 docker CLI 呼び出しのみで、改善余地は小さい。

### 4. セキュリティ脆弱性がないか

- SSH 秘密鍵はマウントしない不変条件を維持。macOS ではホストの Unix ソケットを直接マウントできないため、Docker Desktop の魔法ソケット `/run/host-services/ssh-auth.sock` を `/tmp/ssh-agent.sock` へ転送（agent プロトコルのみ、鍵ファイルは渡らない）。
- 生 Docker ソケットはコンテナへ渡さず Docker Socket Proxy 経由（`DOCKER_HOST`）を維持。検出したソケットは Proxy へ **RO** マウント。
- `make install` の `sudo` は `/usr/local/bin` 配置のためのみ。`sed` によるプレースホルダ置換は repo パス（`$(BASE_DIR)`）に限定。
- ファイアウォール（iptables、`--cap-add NET_ADMIN/NET_RAW`）はコンテナ内で従来どおり適用。

## 静的検証結果

- `bash -n claude-dev-mac`: 構文 OK（`/bin/bash` 3.2.57 = macOS 標準 bash 互換構文であることも確認）。
- `make -n install`（Darwin）: `sudo install -m 0755` + `sed` プレースホルダ置換が展開されることを確認。`UNAME_S=Darwin` で `CLI=claude-dev-mac` に切替。
- install コピー相当（repo 外配置）での `BASE_DIR` フォールバック: 埋め込み repo パスに解決され、repo 資産（`.devcontainer/Dockerfile.claude`）を発見できることを確認。
- `detect_docker_sock`: `/var/run/docker.sock` を返すことを確認。
- `--vm` 早期拒否: exit 1、ビルド未発生を確認。
- `help`: macOS 版の文言（VM/KVM 非対応、localhost 直結）を確認。

## Apple Silicon 対応の方針（arm64 ネイティブ）

当初 `DOCKER_DEFAULT_PLATFORM=linux/amd64` によるエミュレーションで回避したが、ユーザー指示により **arm64 ネイティブ**へ変更。共有 `Dockerfile.claude` を arch 別対応にした（amd64 は従来と同一の後方互換）:

- **gcloud**: アーキ名を写像（`aarch64`/`arm64`→`arm`、`x86_64` はそのまま）。写像しないと arm64 で URL 404。
- **GUI ブラウザ**: `dpkg --print-architecture` で分岐。amd64=Google Chrome（従来どおり）、arm64=base 導入済みの Playwright Chromium。呼び出し側は共通ランチャー `/usr/local/bin/claude-dev-chrome` に統一（entrypoint・openbox メニュー）。
- **その他**（Go/Rust/Terraform/AWS CLI/fnm/Claude Code/Docker CLI）は元々アーキ自動判定で arm64 成立。
- CLI/Makefile の `DOCKER_DEFAULT_PLATFORM` 固定は撤廃（ネイティブビルド）。
- `make install` はコピーではなく `sudo ln -sf` の symlink に変更（ユーザー指示）。BASE_DIR は symlink 経由でも `readlink -f` が repo を解決する。

## セキュリティ（arch 追加分）

- `claude-dev-chrome` ランチャーはビルド時に生成する薄い `exec` ラッパーで、実行時にアーキ判定や外部取得を行わない。arm64 で使う Chromium は base の Playwright 導入物（追加のダウンロード経路を増やさない）。

## 実機動作確認結果（macOS Apple Silicon / Docker Desktop / ネイティブ arm64）

`make build-claude-vnc`（ネイティブ arm64、`DOCKER_DEFAULT_PLATFORM` 未設定）→ 空プロジェクトで `claude-dev start`（VNC あり）を実行し検証:

- **イメージ arch**: `claude-dev-claude`=arm64、`claude-dev-claude-vnc`=arm64（ネイティブ、エミュレーションなし）。
- **gcloud**: base（arm64）ビルド完走＝アーキ写像（aarch64→arm）が有効。
- **GUI ブラウザ（arm64）**: `/usr/local/bin/claude-dev-chrome` が Playwright Chromium（`ms-playwright/.../chrome-linux/chrome`）を指す。google-chrome-stable は arm64 では不在（設計どおり）。
- **VNC 起動**: コンテナ起動後、Chromium が `--no-sandbox --remote-debugging-port=9222` で起動。コンテナ内 `curl http://localhost:9222/json/version` が `Chrome/149.x`（DevTools Protocol 1.3）を返す＝chrome-devtools MCP 接続経路が成立。
- **noVNC**: ホスト `0.0.0.0:6080` に公開（手元ブラウザから直接アクセス可）。
- **tmux**: `main` セッション生成 OK。
- **install**: `make install`（Darwin）は `sudo ln -sf` の symlink（コピーではない）。`readlink -f` が repo を解決し BASE_DIR 正常。
- **stop**: コンテナ削除＋アイドル判定で Docker Socket Proxy 自動停止・残コンテナ 0。

（併せて `--no-vnc` 経路・SSH 魔法ソケット・DOCKER_HOST・proxy 経由 docker・claude バイナリ PATH も amd64 検証時に確認済み。これらは arch 非依存。）

## 結論

macOS（Apple Silicon / Docker Desktop）で `claude-dev-mac` により Claude Code 安全開発環境が **ネイティブ arm64** で起動・動作することを実機で確認した。VM/KVM 非対応の明示拒否、SSH agent の魔法ソケット転送、Docker Socket Proxy 経由の Docker、ポート直結、`sudo ln -sf` による symlink 配置、arm64 の GUI ブラウザ（Playwright Chromium）＋DevTools、いずれも設計・実装仕様と一致。amd64（Linux）は後方互換（従来どおり Google Chrome）。未対応・保留事項なし。

## ドキュメント整合性の徹底確認（3 フェーズ・独立試行）

CLAUDE.md「ドキュメントの完全性確認」に従い、独立したフレッシュな検証エージェント（各フェーズ 2 系統＋最終 1 系統）で客観的に確認し、発見を判定・修正した。

**Phase 1（設計書 09 ↔ 実装仕様書 11/20/31/40/00）** — 修正済み:
- [高] 09「OS 依存箇所は 4 点」→ 実際 §1〜§5 の 5 節。「5 点に集約（§1-4=ホスト CLI、§5=CPU アーキ）」へ修正。
- [高] 09 front matter（summary/keywords）に §5（arm64/Chromium/gcloud）・install 方式が欠落 → 追記、keywords に `arm64`。
- [中] 11 の節番号が `D5b` → `D5` の逆順 → `D5`(プラットフォーム)/`D6`(その他) に採番。
- [中] 31 のステップ番号「14」重複＋実行順ズレ → 実 entrypoint の実行順（firewall→VM→DooD→CLAUDE.md→MCP→VNC→tmux）に合わせ 12〜19 で連番化。
- [低] 09 設計原則「コンテナ内資産は不変」が §5 と見かけ矛盾 → 「arm64 対応のアーキ別分岐を除く」と明記。

**Phase 2（実装仕様書内の整合）** — Phase 1 の採番修正で D 番号・ステップ番号の連番性を回復。`update-claude` ターゲットが 20_makefile.md の一覧から欠落 → 追加。

**Phase 3（実装仕様書 ↔ 実装）** — 修正済み:
- [中] Docker ソケットのマウントを docs が実在しない変数 `DOCKER_SOCK` で記載 → 実コード（`ensure_docker_proxy_container` のローカル変数 `sock` / `start` はインライン `detect_docker_sock`）に合わせ 09・11 を修正。
- [低] 11 の BASE_DIR 解決に `dirname` を補記。
- Dockerfile↔40・entrypoint↔31 は gcloud アーキ写像・ブラウザ分岐・共通ランチャー `claude-dev-chrome`・実行順まで完全一致（不整合なし）。

**最終独立確認** — 実装を誤らせる [高] 不整合はゼロ。残った [中]/[低]（`claude-dev-mac` 冒頭コメントの「4 点」表現、`docs/impl/INDEX.md` の宙吊り参照）も修正:
- `claude-dev-mac` ヘッダを「ホスト CLI 差分 4 点＋ネイティブ arm64（イメージ側）」に更新。
- 既存の宙吊り参照だった `docs/impl/INDEX.md`（02_architecture・00_overview・README が参照）を新規作成し、全 12 実装仕様（新規 `11_cli-mac.md` を含む）を登録。
- [低] `readlink -f` / `realpath` の可用性は本 macOS（Darwin 25）で動作を実測済み（doc の「そのまま機能する」を裏付け）。

結果、設計書↔実装仕様書↔実装の三者に残存不整合なし（収束）。
