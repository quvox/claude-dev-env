---
target: docs/02-design/environments.md
change: replace
sections:
  - "## lint・テストコマンド"
  - "## コンテナ・実行環境"
  - "## ドキュメント整合検査コマンド"
deletes: []
reason: '2つの受け皿を作る。どちらも**同じ下降で上位層から落とすものの移し先**であり、先に作らないと情報が消える(`.claude/directions/layer-fit.md` §2「移送で最も多い誤りは片側だけで終わること」)。(a) 決定シート 概念3 の裁定に従い、`D0-env-02` から落とす**クライアント側の接続手順(SSH の ControlMaster 経由でトンネルを張る)**の受け皿を「コンテナ・実行環境」に作る。`docs/issues/086` が「移し先が無い2件」の1件として挙げていたものである。**00 の決定(必要なときだけ最小限を公開する)は変えず、実現手段だけをここへ移す**。(b) `docs/issues/085` の #6 の手当 — `02-design/relations.md` が `relations-query.py --health` というツール名と引数を本文に持っていたが、**実行するコマンドの正はこの文書である**のに「ドキュメント整合検査コマンド」の表にその行が無かった。表へ1行足し、relations.md 側は指し先だけにする。**表の他の行と実行順の意味は変えない**(構造の健全性の検査は既存の 1〜7 とは独立に走らせてよい補助検査なので、末尾に置く)。(c) 同じ `docs/issues/085` が **#6 と同じ形**と名指したもう1件 — `03-impl/tests/strategy.md` が持つカバレッジ計測のコマンド(`go test -cover ./...`)が**この文書の表に無い** — を、同じ下降で足す(`.claude/directions/02-design.md`「The command strings written here are authoritative」)'
---

## lint・テストコマンド

| 用途 | コマンド | 備考 |
|---|---|---|
| lint | `go vet ./...` | 各 Go モジュール(`docker-proxy/` と `orchestrator/`)のディレクトリで実行する。**Bash には自動 lint を設けていない**(`SR-32`) |
| 単体テスト(docker-proxy) | `cd docker-proxy && go test ./...` | プロキシの検査ロジック |
| 単体テスト(orchestrator) | `cd orchestrator && go test -mod=vendor ./...` | 制御ループ・状態・レビュー・プロンプト生成など |
| 単体テスト(自己検証題材) | `cd examples/orch-sample && pytest` | 題材プロジェクト |
| カバレッジ計測(docker-proxy) | `cd docker-proxy && go test -cover ./...` | テスト戦略が参照する計測手段(`03-impl/tests/strategy.md`)。合否の条件は課さない |
| 結合テスト | 上記2つの `go test` に含まれる | 契約ごとの責任モジュールは `system.md`「結合テスト対象」が正。シェル側の契約は実機確認 |
| E2Eテスト | 自動テストランナーは無い。`make orch-sample` で題材を配置し `claude-dev orchestrate` で実走する | シェル系 E2E(E2E-01〜03)は実機確認。手順は `03-impl/tests/e2e.md` |
| build | `make build` | `claude`(ブラウザ確認なし)+ `claude-vnc` + `docker-proxy` を一括ビルド |
| build(個別) | `make build-claude` / `make build-claude-vnc` / `make build-docker-proxy` / `make build-orchestrator` | `claude-vnc` はベースに続けてビルドする |
| 再ビルド(キャッシュ無し) | `make upgrade` | 全イメージを作り直す |

## コンテナ・実行環境

| サービス | イメージ・起動方法 | ポート | 依存 |
|---|---|---|---|
| Claude コンテナ(ブラウザ確認あり) | `claude-dev-claude-vnc`。`claude-dev start` で起動 | noVNC のみ 6080 番台から動的割当 | 共有ネットワーク、共有ボリューム3本 |
| Claude コンテナ(なし) | `claude-dev-claude`。`claude-dev start --no-vnc` | 公開しない | 同上 |
| docker-proxy | `claude-dev-docker-proxy`。最初のコンテナ起動時に自動で立つ | 共有ネットワーク内のみ(ホストへ公開しない) | ホストの Docker ソケット |
| forward プロキシ | `claude-dev forward <port>` で都度起動 | ホスト側 8100 番台から動的割当 | 対象の Claude コンテナ |
| ゲスト VM(任意) | `claude-dev start --vm` | ゲスト内で完結。必要なポートはホストの 127.0.0.1 へ同期 | `/dev/kvm` |

- 実行環境の前提は `01-requirements/system.md`(`SR-10`〜`SR-15`)が正。
- ネットワーク名・ボリューム名・命名規則といった具体的な構成値は `03-impl/infra/local/` が正。
- **クライアント PC からの到達手順**: `claude-dev forward` が割り当てるのは**サーバ(ホスト)側の
  ポート**であり、クライアント PC からはそこへ **SSH トンネル**を張って到達する
  (`claude-dev forward` はそのコマンドを表示する)。**SSH の ControlMaster による接続の多重化を
  前提とする** — 転送のたびに認証をやり直さずに済ませるためである。**macOS ではポートが直結の
  ため、この手順は不要である**(`FR-env-10` 受入基準2)。

## ドキュメント整合検査コマンド

仕様ドキュメントが互いに整合しているかを機械検査する。**この順で実行し、すべて合格して初めて
ドキュメントが整合しているとみなす。**

| # | 用途 | コマンド | 合格条件 |
|---|---|---|---|
| 0 | 生成先の解決(1・2 の前に1回) | `CG_OUT=$(python3 .claude/scripts/resolve-callgraph-out.py)` | 出力先のパスを返す(終了コード 0)。**出力先を自分で決めてはならない**(進行中タスクがあるときはタスク配下、無ければ `docs/03-impl/callgraphs/` を返す) |
| 1 | コールグラフの鮮度 | `python3 .claude/scripts/build-callgraphs.py --out "$CG_OUT" --check` | 「最新」を返す(終了コード 0)。古い場合は `--out "$CG_OUT"` を付けたまま `--check` を外して再生成してから 2 以降をやり直す |
| 2 | 機能間関係グラフの鮮度 | `python3 .claude/scripts/cluster-features.py --out "$CG_OUT" --check` | 「最新」を返す(終了コード 0)。古い場合は `--out "$CG_OUT"` を付けたまま `--check` を外して再生成してから 3 以降をやり直す |
| 3 | コールグラフ ⇄ 機能表 ⇄ 機能間連携仕様書 | `python3 .claude/scripts/callgraph-check.py` | 重大度「高」が 0 件(終了コード 0)。低・参考は残ってよい |
| 4 | 機能間連携仕様書の内部整合 | `python3 .claude/scripts/check-relations.py` | 「合格」と表示され終了コード 0 |
| 5 | 契約(02 ⇄ 03 ⇄ コード) | `python3 .claude/scripts/check-contracts.py` | 重大度「高」が 0 件(終了コード 0)。REST API を持たないため CT1〜CT3 は該当なし |
| 6 | コードとドキュメントの片側漏れ | `python3 .claude/scripts/relations-coverage.py` | 片側にしか無いものが 0 件 |
| 7 | 目次・進捗の再生成 | `python3 .claude/scripts/build-index.py --check` | 差分なし。差分がある場合は引数なしで再生成する |
| 8 | 構造の健全性(**モジュール間・機能間の循環の有無**) | `python3 .claude/scripts/relations-query.py --health` | 循環が 0 件(終了コード 0)。**`02-design/relations.md` の `PLAN-cli-common-*` が「循環しない」と課している期待を、この検査が担保する** |

- **前提**: `python3 .claude/scripts/setup-tools.py` を1回実行してキット専用の実行環境
  (`.claude/.venv`)を用意しておくこと。**プロジェクトの環境には入れない。**
- 実行位置はリポジトリルート。いずれのスクリプトも書き込むのは生成物(`--check` を外したとき)だけで、
  仕様ドキュメント本文は書き換えない。
- 作業中のタスクの変更指示を合成して検査したいときは `3` に `--to-be <task-slug>` を付ける
  (未実装のシンボルをエラーにしない)。`4`〜`6` と `8` は合成ビューに対応しないため、SSOT へ反映した後に
  実行する。
