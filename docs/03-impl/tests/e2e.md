---
id: e2e
scope: E2E
version: 1.1.0
updated: 2026-08-04
source:
  - docs/02-design/system.md
  - docs/01-requirements/usecases.md
summary: E2Eシナリオ E2E-01〜E2E-06 ⇄ テスト対応
keywords: [テスト, E2E]
verified:
  at: 2026-08-04
  version: 1.1.0
  against:
    - doc: docs/02-design/system.md
      version: 2.0.0
    - doc: docs/01-requirements/usecases.md
      version: 1.1.0
---

# E2E テスト対応

## E2Eシナリオ ⇄ テスト対応表

| E2E ID | 対応 UC | シナリオ | テスト識別子 | 状態 |
|---|---|---|---|---|
| E2E-01 | UC-01 | `claude-dev start`(ブラウザ確認あり / `--no-vnc`)→ `/workspace` マウント・認証・ファイアウォール・tmux → `claude` 起動 → 再実行での再接続 | 手順のみ(下記「実機確認の手順」E2E-01) | 未検証(テスト未実装) |
| E2E-02 | UC-02 | `claude-dev forward` → 8100 番台の割当と SSH トンネル → クライアントのブラウザで表示 → `claude-dev ports` で確認 | 手順のみ(同 E2E-02) | 未検証(テスト未実装) |
| E2E-03 | UC-03 | コンテナ内で危険な `docker run` → 拒否 / `/workspace` bind の許可 / 通常操作の透過 | 手順のみ(同 E2E-03)。判定ロジックは `cd docker-proxy && go test ./...` が単体で検証済み | 未検証(テスト未実装) |
| E2E-04 | UC-04 | `orchestrate` → ブレインストーミング → plan 確定 → worker 並列 → 要判断1件のみ待機・他は継続 → 回答で復帰 → 完了 | 手順のみ(同 E2E-04)。`make orch-sample` で題材を配置して実走する | 未検証(テスト未実装) |
| E2E-05 | UC-05 | 実行中に端末を全終了 → `orchestrate` 再実行 → 合流/再開・完了済みの非再実行・plan と履歴の保持 | 手順のみ(同 E2E-05) | 未検証(テスト未実装) |
| E2E-06 | UC-06 | `claude-dev login-codex` → デバイス認証 → 別プロジェクトで `start` → 再ログイン不要で `codex` が起動し、シェルコマンドが成功して `/workspace` を読み書きできる。landlock の疎通確認が通り、読み取り専用の明示指定で読み取りが成功する | `scripts/e2e6-codex.sh`(実機で実行する検証スクリプト。自動テストランナーからは呼ばれない) | 未検証(テスト未実装) |

## 通過する機能(トレーサビリティ)

| E2E ID | 通過する MODULE-ID |
|---|---|
| E2E-01 | MODULE-cli-start → MODULE-cli-common-require-setup → MODULE-cli-common-container-name → MODULE-cli-common-ensure-infrastructure → MODULE-cli-common-select-ssh-keys → MODULE-entrypoint-claude → MODULE-firewall-init / MODULE-portsync-dood。再接続は MODULE-cli-common-is-running → MODULE-cli-common-resolve-container-user → MODULE-cli-common-get-novnc-url |
| E2E-02 | MODULE-cli-forward → MODULE-cli-common-container-name / MODULE-cli-common-is-running。確認は MODULE-cli-ports、解除は MODULE-cli-unforward |
| E2E-03 | MODULE-docker-proxy-serve(コンテナ内の docker クライアントから見た経路。起動は MODULE-cli-start の `ensure_docker_proxy_container`) |
| E2E-04 | MODULE-cli-orchestrate → MODULE-orchestrator-main → MODULE-orchestrator-controller → MODULE-orchestrator-mode / MODULE-orchestrator-plan / MODULE-orchestrator-worker / MODULE-orchestrator-worktree / MODULE-orchestrator-review / MODULE-orchestrator-trigger / MODULE-orchestrator-handoff / MODULE-orchestrator-dashboard / MODULE-orchestrator-slack。題材は MODULE-sample-project-scaffold → MODULE-sample-project-mathkit |
| E2E-05 | MODULE-cli-orchestrate → MODULE-orchestrator-main → MODULE-orchestrator-state / MODULE-orchestrator-state-io / MODULE-orchestrator-session |
| E2E-06 | MODULE-cli-login-codex → MODULE-cli-start → MODULE-entrypoint-claude(codex 認証のコピーと既定設定の補完) |

## テスト環境

| 項目 | 値 |
|---|---|
| ツール | 実機操作(`claude-dev` / `make`)。自動テストランナーは無い |
| 起動するサービス | Claude コンテナ(対象プロジェクト用)、docker-proxy(自動で起動する)、E2E-04/05 は tmux と実エージェント |
| ブラウザ・CDP エンドポイント | `http://localhost:9222`(コンテナ内 Chrome。ブラウザ確認ありのイメージのみ) |
| シードコマンド | `make orch-sample`(E2E-04 / E2E-05 の題材配置) |
| リセットコマンド | `make orch-sample-clean`(題材の初期化)、`claude-dev stop`(コンテナと compose 生成物の片付け) |
| ブラウザ排他ロック | 未定(QA レーンが未運用のため。`docs/02-design/environments.md` の Codex実行設定と一致させる)。**追跡先は `docs/pendings.md` の P-003**。QA レーンを開始する前に決めること — 決めずに同時実行すると互いのブラウザ状態を壊す |

## 実機確認の手順

自動化されていないため、次の手順を人が実行する。**既存の作業用プロジェクトでは行わない**
(専用のディレクトリを作る)。

### E2E-01

1. 空のディレクトリを作り、その中で `claude-dev start` を実行する。
2. コンテナが起動し、noVNC の URL が表示され、tmux にアタッチされることを確認する。
3. コンテナ内で `ls /workspace` がホスト側のディレクトリと一致すること、`id` の UID/GID が
   ホストと一致すること、`docker inspect` にホストの秘密鍵ファイルと Docker 生ソケットの
   マウントが無いことを確認する。
4. 起動ログにファイアウォールのサマリが出ていることを確認する。
5. tmux をデタッチし、SSH を切断してから入り直し、`claude-dev start` を再実行して同じコンテナへ
   再接続することを確認する。
6. `--no-vnc` でも同様に起動し、noVNC の URL が表示されないことを確認する。
7. **同名コンテナの衝突で稼働中のコンテナが失われないこと**(`FR-env-01` 受入基準12・13)を
   確認する。
   **★衝突は「basename が同じ2つのディレクトリで順番に `start` する」だけでは起きない。**
   同名コンテナが稼働中なら手順6 の再接続経路に入って `exit 0` するからである
   (`claude-dev:715`)。衝突が起きるのは**手順6 の稼働判定を通り抜けたあと、手順13 の
   `docker run` に達するまでの数秒の間に同名コンテナが現れたとき**だけなので、
   その窓を意図的に作って確認する。
   1. 専用の空ディレクトリ(例: `/tmp/e2e-x/web`)を作る。同名の `web` コンテナが**無い**ことを
      `docker ps -a --filter name=^web$` で確かめる。
   2. そのディレクトリで `CLAUDE_DEV_NO_ATTACH=1 claude-dev start` を**バックグラウンドで**起動し、
      出力をファイルへ落とす。
   3. 出力に `SSH 鍵が未設定` の行(`claude-dev:167`。手順4 の時点)が現れたら、**すぐに**
      同名の代役コンテナを立てる: `docker run -d --name web busybox sleep 600`。ID を控える。
      さらに `docker exec web touch /tmp/marker-a` で目印を作る(削除の判別に使う)。
   4. `start` の終了を待つ。**期待する結果**: (a) 終了コードが 1、
      (b) 出力に**同名のコンテナが稼働中である旨**・**別ディレクトリの同名プロジェクトである
      可能性**・**既存のコンテナに手を触れていないこと**が含まれる、
      (c) 3 で控えた ID が**そのまま稼働している**、
      (d) `docker exec web ls /tmp/marker-a` が成功する。
   5. **不合格の条件**: 代役コンテナが消えている / ID が変わっている / `marker-a` が無い /
      終了コードが 0 になる。
   6. **回帰の確認**: 代役コンテナを消し(`docker rm -f web`)、同じディレクトリで
      `claude-dev start` が**通常どおり成功する**(終了コード 0)こと、もう一度実行すると
      「`web` は実行中。接続します...」の再接続経路に入ること(`FR-env-01` 受入基準4)を確かめる。
   7. 後片付け: `claude-dev stop web` を実行し、`docker volume rm claude-dev-chrome-web` と
      一時ディレクトリを削除する。**`stop` は共有 docker-proxy を止めることがある**ので
      (`docs/issues/045`)、他に稼働中の Claude コンテナがあるときは
      `docker ps --filter name=claude-dev-docker-proxy` で残っていることを確認し、
      消えていたら `claude-dev:418`〜`:426` と同じ `docker run` で作り直す。
   - macOS(`claude-dev-mac`)でも同じ手順を実行する。実行できない場合は
     **未実施であることを記録する**(手順を省いたことを黙って残さない)。

### E2E-02

1. コンテナ内で任意の Web アプリを `0.0.0.0` で待ち受けさせる。
2. ホストで `claude-dev forward <port>` を実行し、8100 番台のポートと SSH トンネルのコマンドが
   表示されることを確認する。
3. クライアント PC でトンネルを張り、ブラウザで表示されることを確認する。
4. `claude-dev ports` に当該フォワードが出ることを確認する。
5. 同じポートで再度 `forward` して二重に作られないこと、`unforward` で解除できることを確認する。

### E2E-03

1. コンテナ内で `docker run -v /:/host alpine true` を実行し、拒否されることを確認する。
2. `docker run --privileged` / `--network host` / `--pid host` がそれぞれ拒否されることを確認する。
3. `/workspace` 配下を bind した `docker run` が成功し、ホスト側の実パスが見えることを確認する。
4. bind を含まない `docker run alpine true` が成功することを確認する。

### E2E-04

1. `make orch-sample` で題材を配置する。
2. 題材のディレクトリで `claude-dev orchestrate` を実行する。
3. ブレインストーミングで plan を確定し、実行モードへ入ることを確認する。
4. 複数の worker が並行して動くこと、要判断が出たタスクだけが待機し他が継続することを確認する。
5. 待機中のタスクへ回答し、そのタスクが復帰することを確認する。
6. 完了時に成果が統合され、完了が通知されることを確認する。
7. `.orchestrator/*.jsonl` に委譲・結果・仮定・介入が記録されていることを確認する。

### E2E-05

1. E2E-04 の実行中に、tmux クライアントをすべて閉じる。
2. 入り直して `claude-dev orchestrate` を再実行し、同じ状態へ戻ることを確認する。
3. 完了済みタスクが再実行されないこと、plan と履歴が消えていないことを確認する。

### E2E-06

1. `claude-dev login-codex` でデバイス認証を済ませる。
2. 別のプロジェクトディレクトリで `claude-dev start` を実行する。
3. `scripts/e2e6-codex.sh` を実機で実行する(または同等の手順を手で行う)。
   - コンテナ内で `codex` が再ログインなしに起動すること。
   - codex に依頼した作業でシェルコマンドが**成功**し、`/workspace` を読み書きできること。
     成否は終了コードではなく最終メッセージと成果物で判定する。
   - `codex sandbox --enable use_legacy_landlock -- /bin/true` が exit 0 であること。
   - `codex sandbox --enable use_legacy_landlock -- /bin/sh -c 'touch /tmp/x'` が失敗すること。
   - `--sandbox read-only` を明示した依頼で読み取りが成功すること。
4. トークンが更新された後に別のコンテナを起動し、再ログインが不要であることを確認する。

## 未検証(テスト未実装)の全件

| # | E2E ID | なぜ未実装か | 閉じる予定 |
|---|---|---|---|
| 1 | E2E-01 | 対象がホスト CLI(Bash)であり、自動テストランナーを設けない方針(`DSN-test-01`)。実行に実 Docker とホスト環境を要する | 自動化の予定は無い。方針を変える場合は 02 の `DSN-test-01` から見直す |
| 2 | E2E-02 | 同上。加えてクライアント PC のブラウザ操作を含む | 同上 |
| 3 | E2E-03 | 判定ロジックは単体テストで検証済み。経路全体(コンテナ → proxy → Engine)の確認に実 Docker を要する | 同上 |
| 4 | E2E-04 | 実 tmux と実エージェント(課金を伴う推論)を要するため自動化していない | 同上 |
| 5 | E2E-05 | 同上。加えて端末破壊の再現を要する | 同上 |
| 6 | E2E-06 | 検証スクリプト `scripts/e2e6-codex.sh` はあるが、自動テストランナーからは呼ばれない(実機で人が実行する) | 同上 |

## 対象外としたシナリオ

| E2E ID | 対応 UC | 対象外とする理由 |
|---|---|---|
| なし | — | 全 UC(UC-01〜UC-06)が E2E-01〜E2E-06 に対応しており、対象外としたシナリオは無い |
