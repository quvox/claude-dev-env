---
id: environments
version: 1.6.0
updated: 2026-08-20
source:
  - docs/01-requirements/system.md
  - docs/02-design/architecture.md
summary: 開発環境の構成・セットアップ手順・lint/テスト/ドキュメント整合検査の厳密なコマンド文字列・Codex実行設定
keywords: [開発環境, コマンド, lint, テスト, Codex]
verified:
  at: 2026-08-20
  version: 1.6.0
  against:
    - {doc: docs/01-requirements/system.md, version: 1.3.0}
    - {doc: docs/02-design/architecture.md, version: 1.7.0}
---

<!-- 2026-08-04 /doc-check ssot task-impl-depth(新しい実行): **合格証を再発行した(1.0.0)。**
     直前に削除した理由(source の docs/02-design/architecture.md が未検証 = docs/issues/040 の高)は、
     人間が案A(実装が正)で裁定し architecture.md 1.2.0 が再認証されたことで解消した。
     本文には問題を見つけていない。
     残る「中」: 「Codex実行設定」のモデル・reasoning 行がプレースホルダ「未定」のままで、
     docs/pendings.md P-003 の記述と食い違う。**本実行でもこの行を「不在」と
     扱い規範の既定(gpt-5.6-terra / max)を明示指定した。**
     (2026-08-12 追記: この食い違いは task-issue-sweep が解消した。「未定」の行は
     「未定(いつ決めるか)」の定型へ揃え、決める契機を各行に書いた。追跡していた
     issue は同タスクで削除したので、その参照をここから外した。)
     ★本実行の独立監査は起動できなかった(Codex がアカウントの利用上限に達し 2026-08-10 まで復旧しない)。
     これはツールの問題で本文の欠陥ではないが、合格証は Claude 単独の検証に基づく。 -->

# 開発環境・開発ツールの基本設計

## セットアップ手順

1. リポジトリを取得する。
2. `make setup` を実行する(`.env` の作成 → ネットワーク作成 → 共有ボリューム作成 →
   イメージのビルド → CLI の導入 の順に進む)。
3. `make login` で Claude の認証を済ませる。Codex を使う場合は `claude-dev login-codex` も実行する。
4. 任意のプロジェクトディレクトリで `claude-dev start` を実行する。

| 用途 | コマンド |
|---|---|
| セットアップ | `make setup` |
| CLI の導入 / 除去 | `make install` / `make uninstall` |
| 認証(Claude) | `make login` |
| 認証(Codex) | `claude-dev login-codex` |
| 配布イメージの取得 | `claude-dev pull` |
| 状態の確認 | `make status` |

## lint・テストコマンド

| 用途 | コマンド | 備考 |
|---|---|---|
| lint | `go vet ./...` | `docker-proxy/` のディレクトリで実行する。**Bash には自動 lint を設けていない**(`SR-32`) |
| 単体テスト(docker-proxy) | `cd docker-proxy && go test ./...` | プロキシの検査ロジック |
| カバレッジ計測(docker-proxy) | `cd docker-proxy && go test -cover ./...` | テスト戦略が参照する計測手段(`03-impl/tests/strategy.md`)。合否の条件は課さない |
| 結合テスト | 上記の `go test` に含まれる | 契約ごとの責任モジュールは `system.md`「結合テスト対象」が正。シェル側の契約は実機確認 |
| E2Eテスト | 自動テストランナーは無い。実機で `claude-dev` を操作する | シェル系 E2E(E2E-01〜03・E2E-06)はすべて実機確認。手順は `03-impl/tests/e2e.md` |
| build | `make build` | `claude`(ブラウザ確認なし)+ `claude-vnc` + `docker-proxy` を一括ビルド |
| build(個別) | `make build-claude` / `make build-claude-vnc` / `make build-docker-proxy` | `claude-vnc` はベースに続けてビルドする |
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

## CI

| タイミング | 実行内容 | 失敗したらどうなるか |
|---|---|---|
| 日次 03:30 JST | エージェント CLI のバージョン解決 → マルチアーキ(amd64/arm64)でイメージをビルド → GHCR へ push(タイムスタンプタグ + `latest`) | その日の配布イメージが更新されない(前日のイメージは残る) |
| 手動実行 | 上と同じ。エージェント CLI のバージョンを入力で指定できる | 切り戻しができない |
| PR / 変更時 | **自動化していない。** `go vet` と `go test` は手元で実行する運用 | — |

**PR での自動テスト実行は導入していない。** docker-proxy に閉じた検査なので CI 化の障壁は低い。
導入するかどうかと、その時期は `docs/pendings.md` の **P-002** が持つ(意図的な棚上げであり、
この文書の未解決事項ではない)。

## ドキュメント整合検査コマンド

仕様ドキュメントが互いに整合しているかを機械検査する。**この順で実行し、すべて合格して初めて
ドキュメントが整合しているとみなす。**

| # | 用途 | コマンド | 合格条件 |
|---|---|---|---|
| 0 | 生成先の解決(1・2 の前に1回) | `CG_OUT=$(python3 .claude/scripts/resolve-callgraph-out.py)` | 出力先のパスを返す(終了コード 0)。**出力先を自分で決めてはならない**(進行中タスクがあるときはタスク配下、無ければ `docs/03-impl/callgraphs/` を返す) |
| 1 | コールグラフの鮮度 | `python3 .claude/scripts/build-callgraphs.py --out "$CG_OUT" --check` | 「最新」を返す(終了コード 0)。古い場合は `--out "$CG_OUT"` を付けたまま `--check` を外して再生成してから 2 以降をやり直す |
| 2 | 機能間関係グラフの鮮度 | `python3 .claude/scripts/cluster-features.py --out "$CG_OUT" --check` | 「最新」を返す(終了コード 0)。古い場合は `--out "$CG_OUT"` を付けたまま `--check` を外して再生成してから 3 以降をやり直す |
| 3 | コールグラフ ⇄ 機能表 ⇄ 機能間連携仕様書 | `python3 .claude/scripts/callgraph-check.py` | 重大度「高」が 0 件(終了コード 0)。**中・低・参考は残ってよい**(残っている件数と内訳の正は `03-impl/index.md`「この層の状態」である) |
| 4 | 機能間連携仕様書の内部整合 | `python3 .claude/scripts/check-relations.py` | 「合格」と表示され終了コード 0 |
| 5 | 契約(02 ⇄ 03 ⇄ コード) | `python3 .claude/scripts/check-contracts.py` | 重大度「高」が 0 件(終了コード 0)。REST API を持たないため CT1〜CT3 は該当なし |
| 6 | コードとドキュメントの片側漏れ | `python3 .claude/scripts/relations-coverage.py` | 片側にしか無いものが、**既知の誤検出を除いて** 0 件。**既知の誤検出の内訳と件数は `03-impl/index.md`「`relations-coverage.py` 最終結果」が正である**(このスクリプトは終了コード 1 を返し続ける) |
| 7 | 目次・進捗の再生成 | `python3 .claude/scripts/build-index.py --check` | 差分なし。差分がある場合は引数なしで再生成する |
| 8 | 構造の健全性(**モジュール間・機能間の循環の有無**) | `python3 .claude/scripts/relations-query.py --health` | 循環が 0 件(終了コード 0)。**`02-design/relations.md` の `PLAN-cli-common-*` が「循環しない」と課している期待を、この検査が担保する** |

- **前提**: `python3 .claude/scripts/setup-tools.py` を1回実行してキット専用の実行環境
  (`.claude/.venv`)を用意しておくこと。**プロジェクトの環境には入れない。**
- 実行位置はリポジトリルート。いずれのスクリプトも書き込むのは生成物(`--check` を外したとき)だけで、
  仕様ドキュメント本文は書き換えない。
- 作業中のタスクの変更指示を合成して検査したいときは `3` に `--to-be <task-slug>` を付ける
  (未実装のシンボルをエラーにしない)。`4`〜`6` と `8` は合成ビューに対応しないため、SSOT へ反映した後に
  実行する。

## コールグラフ抽出設定

| 項目 | 値 |
|---|---|
| internal_roots | リポジトリルート(`claude-dev` / `claude-dev-mac` / `scripts/` / `Makefile` / `docker-proxy/`) |
| 有効な言語 | shell / make / go / python / typescript / infra |
| 抽出器が無い言語 | **Dockerfile と GitHub Actions**。この2つはコールグラフに現れないため、モジュール分割定義から外し `03-impl/environments/` と `03-impl/infra/local/` が記述を持つ(`DSN-mod-05`) |
| Tier | shell=3 / make=3 / go=2 / python=2 / typescript=2 / infra=2 |
| ツール環境 | `.claude/.venv`(キット専用。**プロジェクトの環境には入れない**) |
| 用意するコマンド | `python3 .claude/scripts/setup-tools.py` |
| 除外するパス | `workspace/` / `tmp/` / `scripts/e2e6-codex.sh`(E2E の実機検証スクリプトであり、機能ではなく検証手段のため。決定シート2 論点9) |
| 出力先 | `docs/03-impl/callgraphs/` |
| 鮮度検査 | `python3 .claude/scripts/build-callgraphs.py --out "$(python3 .claude/scripts/resolve-callgraph-out.py)" --check` |
| CI で検査するか | いいえ(未定。PR での自動実行を導入する際に併せて決める) |

## Codex実行設定

| 項目 | 値 |
|---|---|
| Codex連携 | 有効(Claude コンテナに同梱。`codex` は PATH 上。認証は共有ボリューム経由) |
| ドキュメント監査 | 有効 |
| QA(E2E + CDP探索) | 無効(未運用。開始時期は未定) |
| フロントエンド | CLI(`codex exec`)。MCP サーバは登録していない |
| 監査の経路 | (a) scoped(スコープ渡し)。添付方式は予備 |
| コマンド | `codex` |
| **必須フラグ** | **無い。コンテナ内では entrypoint が置く既定3鍵で landlock が効く**(2026-08-20 実測: 旗を付けない `codex sandbox -- /bin/true` が exit 0)。`-c features.use_legacy_landlock=true` を足しても結果は変わらない |
| プロファイル | 未定(いつ決めるか)— QA レーンを開始するとき。`docs-audit` / `qa` は未作成で、codex 既定設定で走らせる |
| モデル・reasoning(増分監査) | 未定(いつ決めるか)— **独立レビューのモデルをプロジェクトで固定したくなったとき**。**未記入の行は不在として扱われ、キットの既定が効く** |
| モデル・reasoning(full監査) | 未定(いつ決めるか)— 同上 |
| モデル・reasoning(QA) | 未定(いつ決めるか)— QA レーンを開始するとき |
| **独立レビューを Codex 以外で代替してよいか** | **よい。`codex` CLI がこのホストで使えないときはサブエージェントで代替する**(2026-08-05 に人間が常設で承認した。実行のたびに確認しない)。**どのレンズが走ったかをレポートに必ず明記する** |
| 代替レビュー(サブエージェント)のモデル・reasoning | 未定(いつ決めるか)— 代替レンズの強度をプロジェクトで固定したくなったとき。**未記入なのでキットの既定が効く** |
| タイムアウト / 最大出力 | 監査 900 秒 / QA 未定。最大出力は未定 |
| 最大調査ステップ | 未定 |
| 書き込み許可ディレクトリ | 未定(いつ決めるか)— QA レーンを開始するとき(未運用のため) |
| CDP エンドポイント | `http://localhost:9222`(コンテナ内 Chrome) |
| QA シードコマンド | 未定(いつ決めるか)— QA レーンを開始するとき |
| QA リセットコマンド | 未定(いつ決めるか)— 同上 |
| ブラウザ排他ロック | 未定(いつ決めるか)— 同上。`docs/pendings.md` P-003 で追跡する。**QA レーン開始の前提条件である** |
| Claude のシェルからの到達方法 | コンテナ内 CLI(同一コンテナ内で `codex` を直接呼ぶ) |
| 証跡の保管場所と保持期間 | スクラッチパッドのみ(永続化しない) |
| full 最終監査で「中」が PASS をブロックするか | いいえ |
| CDP 探索を必須にする変更範囲 | 未定(いつ決めるか)— QA レーンを開始するとき(未運用のため) |
| 段階導入フェーズ | 1 観測モード |

**既定3鍵で landlock を効かせる理由**: このコンテナでは codex 既定の bubblewrap サンドボックスが
起動できない(seccomp が `CLONE_NEWUSER` を拒否し、AppArmor が `mount --make-rslave /` を拒否する。
`DSN-dist-02`)。legacy landlock バックエンドはユーザー名前空間を使わないため、コンテナの
confinement を緩めずに動く。**3鍵目(`[features] use_legacy_landlock = true`)が欠けると、
サンドボックスを張る呼び出しはすべて exit 1(bwrap)になる**(2026-08-20 実測: 3鍵目だけを欠いた
設定では `codex sandbox -- /bin/true` も `-c sandbox_mode=read-only` も exit 1)。そのとき
`codex exec` の終了コードは 0 のままなので、成否は終了コードではなく最終メッセージと成果物で
判定する。

**サンドボックス疎通確認**: 既定3鍵が置かれた状態で、`codex sandbox -- /bin/true` が exit 0、
かつ `codex sandbox -- /bin/sh -c 'touch /tmp/x'` が exit 1(`Permission denied`)であること。
`--enable use_legacy_landlock` を明示しても同じ結果になる(旗の経路の回帰確認)。
`codex doctor` はこの故障を検知しない。確認の実体は `scripts/e2e6-codex.sh` が持つ。

**監査での禁止事項**: 監査(`docs` / `readiness` / `diff`)では承認・サンドボックスを迂回する
フラグを使わない(read-only + landlock で足りる)。**QA レーンのみ例外**として
`-c sandbox_mode="danger-full-access"` で走らせる(landlock 経路では書き込みが成立しないため。
「コンテナ自体が隔離空間であり、これ以上の隔離は不要」という `D0-sec-06` の一貫適用。
2026-07-31 の人間判断)。QA の他の制約(専用シード・ブラウザ排他・テスト成果物ディレクトリ以外を
書かない・終了時にリセット)はそのまま守る。git 未初期化のリポジトリでは `--skip-git-repo-check`
を付ける(これは迂回ではない)。

**イメージ更新時の注意**: `use_legacy_landlock` は codex 0.148.0 時点でも deprecated のままで、
撤去されてはいない(2026-08-20 に `codex features list` で実測)。同梱バージョンはビルド時に
最新へ解決されるため、イメージを更新したら上記の疎通確認を再実行する。撤去されるとこのコンテナで
サンドボックスを張る手段が無くなるので、退避先は添付方式である。

**codex を起こす側が前提にしてよいこと**: コンテナの外から codex を起こす道具(艦隊の窓・
スクリプト・人間の手)が、起動の前に何を確かめてよく、何を確かめてはいけないかを定める。
下の値はすべて 2026-08-20 に `claude-dev-claude:latest`(codex 0.148.0)の実機で測ったものである。

| 事柄 | 値 | 起こす側が取るべき扱い |
|---|---|---|
| `bwrap --unshare-user --unshare-net --ro-bind / / /bin/true` | exit 1(`No permissions to create new namespace`) | **既知・正常である。codex が使えるかどうかの判定に使ってはならない** — `DSN-dist-02` が「使わない」と決めた経路の状態を見ているだけである |
| `codex sandbox -- /bin/true` | exit 0 | **可否の判定はこれで行う。** 非ゼロなら既定3鍵が届いていない |
| `codex sandbox -- /bin/sh -c 'touch /tmp/x'` | exit 1 | 読み取り専用が成立している証拠である |
| `sandbox_mode = "workspace-write"` を要求する起動 | exit 101 の panic(`permission profiles requiring direct runtime enforcement are incompatible with --use-legacy-landlock`) | **このコンテナでは成立しない**(`FR-env-12-9` が対象外と定めた帰結の実体)。書き込みを伴う自動化は既定3鍵のまま走らせる |
| 既定3鍵の置き場所 | `<プロジェクト>/.codex/config.toml`(コンテナ内の `~/.codex` はここへの symlink) | **ホストから見えるパスである。** 同じディレクトリでホスト側の `codex` を起こすと同じ3鍵が効き、ホスト側でも `workspace-write` は上と同じ panic になる |

**最後の行の測り方**: このリポジトリの直下と `docs/` から `codex features list` を実行すると
`use_legacy_landlock` が true、`/tmp` から実行すると false になり、ホストの
`~/.codex/config.toml` に `[features]` の節は無い。効く条件そのものは codex 側の解決規則であり、
本システムが定めたものではない。**置き場所は `AC-06`(設定と履歴がプロジェクトごとに独立して
いること)と `CTR-cli-container` が定めたものなので、ここでは変えない。**

## 将来設定(運用開始時に決めるもの・未解決事項ではない)

**上表の「未定」の帰着**: 「未定」と書いてある項目(PR での CI 自動実行、Codex のプロファイル名・
モデル・QA レーンの各設定)は、いずれも**まだ運用していない機能の設定値**であり、
「まだ誰も決めていない要確認事項」ではない。したがって未解決事項には数えず、下流の検証を
ブロックしない。運用を始める時点で決めるものとして `docs/pendings.md`(**P-002** = PR での CI 自動実行 /
**P-003** = QA レーンの各設定)で追跡する。決めた時点でこの文書の該当行を「未定」から実値へ
置き換える(MINOR 変更)。

## 未解決事項

- なし。
