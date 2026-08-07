---
id: task-stop-session-spawned-containers
phase: 反映
origin_layer: 00
issue: なし
date: 2026-08-07
updated: 2026-08-07
source:
  - docs/00-requests/decisions/env.md
  - docs/00-requests/terminology.md
  - docs/01-requirements/functional.md
  - docs/01-requirements/decisions/split.md
  - docs/02-design/architecture.md
  - docs/02-design/contracts/cli-container.md
  - docs/02-design/contracts/docker-api.md
  - docs/02-design/system.md
  - docs/02-design/relations.md
  - docs/02-design/logging.md
  - docs/03-impl/relations/MODULE-cli-stop.md
  - docs/03-impl/relations/MODULE-docker-proxy-serve.md
  - docs/03-impl/relations/MODULE-cli-reset.md
  - docs/03-impl/tests/cli-stop.md
  - docs/03-impl/tests/cli-reset.md
  - docs/03-impl/tests/docker-proxy.md
  - docs/03-impl/tests/e2e.md
  - docs/03-impl/tests/strategy.md
  - docs/03-impl/infra/local/docker-resources.md
summary: claude-dev stop が、そのセッションのコンテナ内から起動された Docker コンテナ群(compose 以外を含む)も片付けるようにする
---

<!-- フロントマターに インラインコメント(値のあとの # …)を書かないこと。 -->

# task-stop-session-spawned-containers セッション内から起動されたコンテナの片付け

> 解決済みの経緯: memo-1.md(フェーズ1の決定シートの回答の写し)/ memo-2.md(フェーズ2と `/doc-check` の未決点 26 件)

## 目的

`claude-dev stop` が片付けるのは、本体コンテナ・`fwd-<name>-*`・**compose ラベル
`com.docker.compose.project=<一意化名>` を持つコンテナ**だけで、セッション内から
`docker run`(compose を経由しない経路)で作られたコンテナはホストに残り続ける。
これを片付けの対象に入れる(利用者要望)。

## やること・やらないこと

| 種別 | 内容 |
|---|---|
| やること | セッションのコンテナ内から docker-proxy 経由で作られた**コンテナとネットワーク**を識別できるようにし、`claude-dev stop` と `claude-dev reset` の片付け対象に入れる(削除は `docker rm -f` / `docker network rm`)。識別のための印(所有者を表すラベル)の付与を docker-proxy が行う。00 の決定(`D0-env-05` 項2 のライフサイクル / `D0-env-08` の識別)から 03 まで1回で下降する |
| やらないこと(このタスクの範囲外) | **名前付きボリュームの削除**(`D0-env-05` 項2 の「保持する」を維持)/ `logout` への適用(概念4 の回答)/ VM モード(ゲスト内 Docker はホストに現れないので現状どおり対象外)/ ラベル注入より前に作られた既存コンテナ・ネットワークの遡及的な片付け(識別する印が無い)/ `docs/issues/005`(解釈できないボディの中継)の根本解消 / コンテナ名の一意化(`docs/issues/028`)/ 遊休判定の方式変更 |

## 影響範囲(closure)

| 層 | SSOT のパス | 変更指示のパス | 変更の種類 |
|---|---|---|---|
| 00 | docs/00-requests/decisions/env.md | new-features/00-requests/decisions/env.md | replace |
| 00 | docs/00-requests/terminology.md | new-features/00-requests/terminology.md | replace |
| 00 | docs/00-requests/request.md | - | 変更なし(理由: 目的・対象ユーザー・スコープは変わらない。「やらないこと」5件のいずれにも当たらない) |
| 00 | docs/00-requests/acceptances.md | - | 変更なし(理由: AC は利用者視点の代表シナリオ6件で、`stop` の後片付けはどの旅程にも現れない。同型の先例 `docs/histories/2026-07-19-stop-compose-teardown.md` も AC を増やしていない) |
| 00 | docs/00-requests/decisions/sec.md | - | 変更なし(理由: `D0-sec-05` の委任範囲は「検査の厳密さと安全側の倒し方」であり、拒否判定を変えない所有者ラベルの付与はガードレール「拒否すべき操作を通してはならない」に触れない) |
| 00 | docs/00-requests/decisions/auth.md | - | 変更なし(理由: 認証の受け渡しに触れない) |
| 00 | docs/00-requests/decisions/dist.md | - | 変更なし(理由: 配布・同梱に触れない) |
| 00 | docs/00-requests/decisions/orch.md | - | 変更なし(理由: オーケストレーターに触れない) |
| 00 | docs/00-requests/decisions/scope.md | - | 変更なし(理由: 記述粒度と委任の範囲は変わらない。本変更は観測可能な振る舞いを変えるので `D0-scope-02` の委任では扱えず、00 起点として扱う) |
| 01 | docs/01-requirements/functional.md | new-features/01-requirements/functional.md | replace |
| 01 | docs/01-requirements/decisions/split.md | new-features/01-requirements/decisions/split.md | replace |
| 01 | docs/01-requirements/usecases.md | - | 変更なし(理由: `stop` は UC-01〜06 のどのフローにも現れない。**これは本タスクが作った欠落ではなく既存の状態**であり、`docs/issues/080` が起票済み。要件単位では `FR-env-01` が UC-01 に現れるので A1 は通り、E2E-01 の上流 UC も UC-01 で成立する) |
| 01 | docs/01-requirements/non-functional.md | - | 変更なし(理由: 目標値・測定方法のどれにも影響しない) |
| 01 | docs/01-requirements/system.md | - | 変更なし(理由: 技術前提・実行環境・依存は変わらない) |
| 02 | docs/02-design/contracts/cli-container.md | new-features/02-design/contracts/cli-container.md | replace |
| 02 | docs/02-design/contracts/docker-api.md | new-features/02-design/contracts/docker-api.md | replace |
| 02 | docs/02-design/system.md | new-features/02-design/system.md | replace |
| 02 | docs/02-design/relations.md | new-features/02-design/relations.md | replace |
| 02 | docs/02-design/logging.md | new-features/02-design/logging.md | replace |
| 02 | docs/02-design/architecture.md | new-features/02-design/architecture.md | replace(**`/doc-check` 2026-08-07 で影響範囲に加えた**。当初「責務もデータの流れも変わらない」としたが、docker-proxy の責務に所有者ラベルの注入が加わり、Docker 操作の結果が3値から4値になるため事実と合わなくなる) |
| 02 | docs/02-design/environments.md | - | 変更なし(理由: lint・テスト・ビルドのコマンド文字列は変わらない) |
| 02 | docs/02-design/contracts/cli-orchestrator.md | - | 変更なし(理由: オーケストレーターの起動に触れない) |
| 02 | docs/02-design/contracts/entrypoint-firewall.md | - | 変更なし(理由: ファイアウォールに触れない) |
| 02 | docs/02-design/contracts/orchestrator-prompt.md | - | 変更なし(理由: プロンプト契約に触れない) |
| 03 | docs/03-impl/relations/MODULE-cli-stop.md | new-features/03-impl/relations/MODULE-cli-stop.md | replace |
| 03 | docs/03-impl/relations/MODULE-docker-proxy-serve.md | new-features/03-impl/relations/MODULE-docker-proxy-serve.md | replace |
| 03 | docs/03-impl/relations/MODULE-cli-reset.md | new-features/03-impl/relations/MODULE-cli-reset.md | replace |
| 03 | docs/03-impl/contracts/cli-container.md | - | 変更なし(理由: **コードの鏡**で、全行が `path:line` の「定義箇所」を持つ事実表である。実装前に書くと存在しない行番号を書くことになるため、`D0-env-10` のガードレールどおり `/task-close` がコードから確定させる。確定させる内容は「申し送り事項」に書いた) |
| 03 | docs/03-impl/contracts/docker-api.md | - | 変更なし(理由: 同上。所有者ラベルの付与の実装事実は `/task-close` が `docker-proxy/main.go` の行番号つきで書く) |
| 03 | docs/03-impl/tests/cli-stop.md | new-features/03-impl/tests/cli-stop.md | replace |
| 03 | docs/03-impl/tests/cli-reset.md | new-features/03-impl/tests/cli-reset.md | replace |
| 03 | docs/03-impl/tests/docker-proxy.md | new-features/03-impl/tests/docker-proxy.md | replace |
| 03 | docs/03-impl/tests/e2e.md | new-features/03-impl/tests/e2e.md | replace |
| 03 | docs/03-impl/tests/strategy.md | new-features/03-impl/tests/strategy.md | replace |
| 03 | docs/03-impl/infra/local/docker-resources.md | new-features/03-impl/infra/local/docker-resources.md | replace |
| 03 | docs/03-impl/index.md | - | 変更なし(理由: 「この層の状態」「02 との差分」は実装後にしか数えられない集計であり、層代表の `version` と検証済み記録は `/task-close` と `/doc-check` が扱う。実装前に書くとコードの鏡ではなくなる) |
| 03 | docs/03-impl/features.md | - | 変更なし(理由: 機能(83本)の増減が無く、境界も動かない) |

**変更の起点**: 00-requests(`decisions/env.md`)。`D0-env-05` 項2 が「`stop` 時に片付けるもの」を
compose 資源に限っており、その集合を広げる判断だから。あわせて `D0-env-08` 項1(集合として列挙して
消す対象の限定)と `D0-env-10`(管理ラベルを付ける資源の種類)に届く。**下流だけ直すと
`D0-env-05` 項2 と実装が食い違う**(CLAUDE.md 原則3)。

**既存タスクとの関係**: なし(`docs/tasks/` に進行中のタスクは無い。`ls docs/tasks/` は `index.md` のみ)。

**解消できる pending / issue**: なし。関係するが解消しないもの — `docs/issues/005`
(解釈できないボディを中継する)は本変更で「ラベルを注入できない要求」という新しい観測点を得るが、
根本(fail-closed へ倒すか)は本タスクの範囲外。

## 読む範囲(読了記録)

- 全文読了: 2026-08-07
  - docs/00-requests/acceptances.md@1.2.0
  - docs/00-requests/decisions/auth.md@1.2.0
  - docs/00-requests/decisions/dist.md@1.0.1
  - docs/00-requests/decisions/env.md@1.2.0
  - docs/00-requests/decisions/orch.md@1.3.0
  - docs/00-requests/decisions/scope.md@1.2.0
  - docs/00-requests/decisions/sec.md@1.1.2
  - docs/00-requests/request.md@1.3.0
  - docs/00-requests/terminology.md@1.2.0
  - docs/01-requirements/decisions/split.md@1.1.1
  - docs/01-requirements/functional.md@1.9.0
  - docs/01-requirements/non-functional.md@1.5.0
  - docs/01-requirements/system.md@1.1.0
  - docs/01-requirements/usecases.md@1.3.0
  - docs/02-design/architecture.md@1.3.0
  - docs/02-design/contracts/cli-container.md@1.4.2
  - docs/02-design/contracts/cli-orchestrator.md@1.1.0
  - docs/02-design/contracts/docker-api.md@1.0.0
  - docs/02-design/contracts/entrypoint-firewall.md@1.0.1
  - docs/02-design/contracts/orchestrator-prompt.md@1.3.0
  - docs/02-design/environments.md@1.1.0
  - docs/02-design/logging.md@1.3.0
  - docs/02-design/relations.md@1.4.0
  - docs/02-design/system.md@2.5.0

## 決定シート(回答済み)

> **回答済み(2026-08-07)。回答待ちの論点は無い。**
> — **論点6(このホストで実行できない E2E の残りをどうするか)は B**:
> 未実施のまま `/task-close` へ進み、残りを `docs/pendings.md` へ**受容**として記録する。
> 人間の理由は「実行できないものは出来なくて当たり前」(AI 推奨は A(専有時間帯を作って実行)、
> 未回答時の既定は C(issue 起票)だった。**気づきは `docs/feedbacks/025-...` に記録した**)。
> **`/task-close` は `docs/pendings.md` の P-004 を最終化してから完了させる**
> (下の「申し送り事項」)。
> なお **論点5 は「未回答時の既定 A」で確定した** — `/doc-check` が論点5 を提示した直後に
> 人間が「実装に移って」と指示したため、シート自身が定める既定(A = `D0-env-10` の
> ガードレールを2ラベルへ広げる)を承認したものとして扱う。**A はコードを変えない**ので、
> 実装は既定のまま進められる(B ならコードが変わるため、その場合は本行を差し戻す)。
> <!-- 人間が記入する実体はこのファイル。**この行が sheet.md を名指す**ことで、memo.md を入口に
>      再開できる(directions/task-memo.md §1)。後続フェーズが sheet.md へ論点を追記したら
>      「回答待ち: sheet.md(論点 N 件)」に戻す。 -->

**フェーズ1の回答(概念6件 / 論点1〜3 / 委任1)は memo-1.md へ移動した**(変更指示へ反映済みのため)。
フェーズ2 で追記した論点の回答は次のとおり。

| # | 論点 | 回答 | 反映先 |
|---|---|---|---|
| 論点5 | 所有者ラベルを2つ注入することが `D0-env-10` のガードレールに収まるか | **既定を承認(A)**。2026-08-07、論点5 を提示した直後の「実装に移って」の指示による。`claude-dev.role=spawned` と `claude-dev.owner-project-dir` の**2つを注入する現行の 02・03 のまま実装する**。**00 の2箇所(`D0-env-10` のガードレール1行 / `D0-env-08` 項8 の「所有者を表す管理ラベル」)を「所有者と種別を表す2つ」へ書き直す**のは `/task-close` の反映で行う | `new-features/00-requests/decisions/env.md`(**フェーズ3 の C-1 で書き足す**)/ 実装は不変 |
| 論点4 | 独立レビューが実行できなかったときの代替 | **B**(サブエージェントを独立レビュー役に立てる)。2026-08-07 に実行し、指摘4件をすべて「確認済み・自動修正可能」と裁定して反映した。**実際に走ったレビュー役は `lens: subagent`**(Codex ではない。不変則7 が求める明示) | 未決点4〜7 / `new-features/01-requirements/functional.md`(`FR-env-01-24` と `FR-env-03` 条項14・17)/ `new-features/03-impl/relations/MODULE-cli-stop.md`(手順6・7・8-3 と判断19)/ `new-features/03-impl/tests/e2e.md`(手順8-14-6)/ `new-features/03-impl/tests/cli-stop.md` |

## 未決点

(memo-2.md に移動。**26 件すべて帰着済みで、未決点は0件である**)

## 調査メモ

(memo-2.md に移動。フェーズ3 の実装で使い切った。**実装で新たに判明した事実は
`new-features/03-impl/relations/MODULE-*.md` の「実装上の判断」に書いてある** — 調査メモは
導出キャッシュであり、恒久的に真な事実の置き場ではない)

## 質問キュー(未提示)

| # | 論点 | 何が止まるか | 推奨する回答(暫定) |
|---|---|---|---|
| - | なし(フェーズ1の論点はすべて sheet.md に載せた) | - | - |

## タスクリスト

<!-- フェーズ2 が置いた下書き。確定は `/implement` が行う。
     1タスク = 1コミット、依存順(印を付ける側 → 読む側 → テスト)。 -->

- [x] 1. docker-proxy: 呼び出し元の解決を2値化する(`/workspace` のマウント元 + `claude-dev.project-dir` ラベル)。`GET /containers/json` の構造体に `Labels` を足し、キャッシュも2値で持つ _要件:_ FR-env-07-11 _Boundary:_ `docker-proxy/main.go` _Depends:_ -
- [x] 2. docker-proxy: `POST /containers/create` と `POST /networks/create` へ所有者ラベルを注入する(拒否判定の後・ボディ再構成は1回・利用者の同名ラベルは上書き・失敗しても拒否しない) _要件:_ FR-env-07-11, FR-env-07-12 _Boundary:_ `docker-proxy/main.go` _Depends:_ 1
- [x] 3. docker-proxy: 単体テストを足す(付与される / 他フィールドが変わらない / 上書きされる / 解決できないとき付与せず拒否もしない / ボディ不正で元のまま通す) _要件:_ FR-env-07-11, FR-env-07-12 _Boundary:_ `docker-proxy/main_test.go` _Depends:_ 2
- [x] 4. claude-dev / claude-dev-mac: `stop` に手順8(所有者ラベルでコンテナ → ネットワークを削除・種別つき表示・0件なら無表示・失敗は握る・標準出力は捨てる)を入れ、遊休判定より前に置く _要件:_ FR-env-01-22, -23, -24, -26, -27 _Boundary:_ `claude-dev` の `stop)` 分岐 / `claude-dev-mac` の同一箇所 _Depends:_ 2
- [x] 5. claude-dev / claude-dev-mac: `reset` に `claude-dev.role=spawned` の列挙(確認プロンプトに出す)と削除(失敗は握らない)を入れ、遊休判定より前に置く _要件:_ FR-env-01-25, -26, -27 _Boundary:_ `claude-dev` の `reset)` 分岐 / `claude-dev-mac` の同一箇所 _Depends:_ 2
- [x] 6. E2E-01 手順8-14・8-15 と E2E-03 手順5・6 を実機で実行し、結果を記録する _要件:_ FR-env-01-22〜27, FR-env-07-11 _Boundary:_ 実機(ドキュメントは変更しない) _Depends:_ 3, 4, 5

## Definition of Done

- [x] lint(`go vet ./...`)がグリーン
- [x] 単体テスト(`cd docker-proxy && go test ./...`)がグリーン(39 本)
- [x] 受入基準テスト(`FR-env-07-11` / `-12`)が実装済みでグリーン
- [x] シェル2本の構文検査(`bash -n`)が通る
- [x] コールグラフを再生成し `callgraph-check.py --to-be` の重大度「高」が0件
- [x] `check-relations.py` / `check-contracts.py` が合格
- [x] `check-changeset.py` が合格 — **規範更新(2026-08-07)で CS18・CS19 が増えたが、両方とも決着した**。
      CS19 の 10 件はキットの欠陥で、同日 `/kit-improve --apply` を当てて **OK**。CS18 の 11 件は
      **既存の SSOT 由来で本タスクの範囲外**(`docs/issues/083`)。詳細は下の表の 9 行目
- [x] `03-impl/tests/` の変更指示を実装結果に合わせて更新した
- [x] E2E-03 手順5・6(所有者ラベルの付与)を実機で確認した
- [x] E2E-01 手順8-14 の 3・4・5・6(`stop` の片付け)を実機で確認した
- [x] **E2E-01 手順8-14 の 1・2・7 / 手順8-15 / 手順10・12(`reset` 側)と macOS 版**
      — **未実施のまま受容すると人間が決めた**(`sheet.md` 論点6 = B、2026-08-07。
      理由「実行できないものは出来なくて当たり前」)。受容の記録は `docs/pendings.md` **P-006**、
      代替として確認したことも同じ項が持つ。下の「E2E の未実施分」も参照
- [ ] SSOT 反映 / `/doc-check` PASS / histories — **`/task-close` で実施**

`git rev-parse HEAD` = **8435b0b**(検証時点。以降のコミットは無し)。
コマンドは `docs/02-design/environments.md`「lint・テストコマンド」の厳密な文字列を使った。
各項目の実際の最終出力行は次の表が持つ。

| # | 項目 | コマンド | 最終出力行 | 判定 |
|---|---|---|---|---|
| 1 | lint | `go vet ./...`(`docker-proxy/` で実行) | (出力なし。終了コード 0) | ✅ |
| 2 | 単体テスト | `cd docker-proxy && go test ./...` | `ok  	github.com/quvox/claude-dev-env/docker-proxy	0.018s` | ✅ 39 本(25 → +14) |
| 3 | シェルの構文 | `bash -n claude-dev` / `bash -n claude-dev-mac` | (出力なし。終了コード 0) | ✅(Bash に自動 lint は設けない方針 `SR-32`) |
| 4 | 受入基準テスト | `FR-env-07-11` / `-12` は上の単体テスト14本 | 同上 | ✅ |
| 5 | コールグラフ再生成 | `build-callgraphs.py --out <staged>` / `cluster-features.py --out <staged>` | `機能 83 / 機能間の辺 129(確定 122 / 候補 7) / 共有関数 29 / 未到達 19` | ✅ |
| 6 | `callgraph-check.py --to-be` | 同左 | `### 指摘 47 件`(**重大度「高」0 件**。中6 は CG3 で本タスクの範囲外モジュール) | ✅ |
| 7 | `check-relations.py` | 同左 | `合格: 対称性・参照実在・impl パス・必須項目・機能表との 1:1すべて問題なし。` | ✅ |
| 8 | `check-contracts.py` | 同左 | `合格: 契約に不整合なし。` | ✅ |
| 9 | `check-changeset.py` | 同左 | **規範更新前は** `合格: 不変条件の違反なし`(**staged 導出物を一時退避して実行**。退避しないと `docs/issues/076` により CS1 違反 29 件で落ちる)。**2026-08-07 の規範更新の直後は CS18 が 11 件・CS19 が 10 件を出した**。CS19 の 10 件は**キット側の欠陥**で、人間の合意を得て `/kit-improve KIT-cs19-section-name-and-test-templates --apply` を当てた結果 `CS19 理由の網羅: OK(判断の節を持つ変更指示 10 件)`。CS18 の 11 件は**既存の SSOT 由来で本タスクの範囲外**(`docs/issues/083`。本タスクが作った3件は直した)。CS1 の 29 件は従来どおり `docs/issues/076`(staged 導出物)で、退避すれば出ない | ✅(**残る 40 件はすべて他所で追跡済み** — CS1 29 = `076` / CS18 11 = `083`) |
| 10 | `03-impl/tests/` の更新 | — | `tests/docker-proxy.md` の2条項を `実装済み` にし、未検証の全件から2件を削除 | ✅ |
| 11 | E2E(E2E-03 手順5・6) | 実機確認(隔離した proxy 経由) | コンテナ・ネットワークの双方に `claude-dev.role=spawned` と `claude-dev.owner-project-dir=/tmp/e2e-verify-owner` が付き、利用者指定の `/etc` は上書きされ `keep=me` は残った。特定できない呼び出し元では付かず、作成は成功した | ✅ |
| 12 | E2E(E2E-01 手順8-14 の 3・4・5・6) | 実機確認(`./claude-dev stop`) | `🧹 このセッションが作った資源を削除しました:` にコンテナ2件・ネットワーク1件が種別つきで出た。0件のときは1行も出ず、ラベルを読めない対象では片付けを試みず、所有者ラベルを持たない資源と別セッションは無傷 | ✅ |
| 13 | E2E(E2E-01 手順8-14-1・2・7 / 手順8-15 / macOS 全般) | — | **未実施**。理由は下の「E2E の未実施分」 | ⏸ |
| 14 | SSOT 反映 / `/doc-check` PASS / histories | — | `/task-close` で実施 | — |

**E2E の未実施分と、その理由**:

- **手順8-14-1・2(2つのセッションを同時に立てて別セッションの資源が消えないこと)と
  手順8-15(`reset` が所有者を問わず消すこと)、手順10・12(`reset` の削除失敗と遊休判定)**:
  **このホストでは別プロジェクトの Claude セッション `ct_matchsupport` が稼働中**であり、
  `claude-dev reset` は管理ラベルを持つコンテナを集合として削除するので**それを消してしまう**。
  E2E-01 手順8 は「他に作業中のセッションが無い時間帯に行う」と自ら定めており、その条件を
  満たしていない。**代わりに、別セッションを巻き込まないことは `stop` 側で確認した**
  (所有者の違う資源・所有者ラベルを持たない資源・`ct_matchsupport` のいずれも無傷)。
- **macOS(`claude-dev-mac`)**: 実行環境が無い。**Linux 版との差分が無いことは機械的に確認した**
  (`diff <(grep spawned claude-dev) <(grep spawned claude-dev-mac)` が完全一致)。
- どちらも**手順を省いたのではなく未実施である**。専有できる環境で実行すること。

## 進捗メモ

- 2026-08-07 **規範更新後の再検査**(人間の指示。キットが 2026-08-07 16:19 に更新され、
  `.claude/directions/delegation.md`(標準委任 `DS-01`〜`DS-08`・問う基準・開示義務)が新設され、
  検査 `CS17`(開示の形と開示漏れ)・`CS18`(要件に降りた機構)・`CS19`(理由の網羅)が増えた)。
  **SSOT は1文字も触っていない**(タスク進行中のため。原則1)。直したのは変更指示・`sheet.md` と、
  範囲外の分の起票である。
  - **変更指示に「テスト設計の判断」を新設**(`03-impl/tests/` の5件。`anchors:` 付きの新設見出し)。
    **委任で決めたこと**: `DS-01` で (a) テスト識別子を E2E の**部分手順まで**書く、(b) 状態列は
    `未検証(テスト未実装)` のまま置き実機確認の結果を状態にしない、(c) 単体テスト14本を
    `docker-proxy/labels_test.go` に分け `resolveProjectDir` の差し替えで実 Docker を使わない、
    (d) 検証は書き戻されたボディの JSON を読み直す形にする。いずれも該当ファイルに
    `[DS-01] … — 理由: … / 見直す条件: …` の形で書いた(`CS17` が形式を検査する)。
  - **`02-design/architecture.md` の「設計判断」と `system.md` の「分割の根拠」を影響範囲に加えた**
    (`CS19` は、その節を触る変更が既存の判断を全件読み直すことを要求する)。読み直した結果、
    **設計判断8件のうち `DSN-arch-02` の1行だけが更新**で、残り7件と分割の根拠6件は継続である。
    `DSN-arch-02` の更新は**この再検査が見つけた実質的な欠落**である: 状態の置き場の表が
    Docker リソースの所有を「ホスト CLI / Makefile」・識別を「`claude-dev-` 接頭辞」としており、
    **docker-proxy が印を付けるセッション由来の資源(名前は利用者が決める)を表せていなかった**。
  - **`CS18`(要件に機構を書かない)で、本タスクが新しく書いた3箇所から `CTR-cli-container` を
    落とした**(`FR-env-01` の内容欄 / `FR-env-01-22` / `FR-env-07-11` → 「02 の契約が定める」)。
    **要件の意味は変えていない**。既存 27 箇所は範囲外 → `docs/issues/083`。
  - **`sheet.md` を新書式へ**(「一括回答」の節 / 論点6 の「間違えたときの戻し方」/
    「今回 AI が決めたこと」の開示節)。**記入済みの ★あなたの記入 は1文字も触っていない**。
    `check-sheet.py` は合格(以前は「一括回答の節が無い」を出していた)。
  - **範囲外として起票**: `docs/issues/083`(要件 27 箇所が下位層 ID と実装ファイル名を名指す)/
    `docs/issues/084`(`03-impl/tests/` の全 32 件に「テスト設計の判断」が無い。うち5件は本タスクの
    変更指示で解消するので反映後は 27 件)。
  - **キット側の欠陥を1件見つけた** → `.claude/improvements/KIT-cs19-section-name-and-test-templates.md`
    (`status: 検討中`)。**`CS19` は `sections:` の要素を素の見出し名と比べるが、
    `change-set.md` と `CS1` は `## ` 込みで書くことを要求する** — どちらの書き方でも合格できず、
    **判断の節を持つファイルを触る変更指示はこの版のキットでは合格できない**。修正は比較の
    正規化1行で、当てた実測では `CS19` の10件がすべて OK になる(他の検査 ID は不変)。
    **人間の合意が要る**(`/kit-improve` は `--apply` に `status: 合意済み` を要求する)。

- 2026-08-07 **階層の点検・5周**(人間の指示「あなたが文書を全て読んで、階層が適切ではない項目や
  記述がないかを確認して。確認→修正を、subagent を用いて5周して」)。**各周: 独立レビュー
  (`lens: subagent`)が全文精読 → 私が裁定 → 修正**。SSOT は無変更で、直したのは変更指示だけ。
  - **1周目(00・01 の変更指示)**: 指摘 86 件 → **採用6件**。退けた最大の理由は
    **用語集の語は全層で使える**(`00-requests.md`「Every layer follows this glossary」)ことと、
    **`D0-env-08` が識別方法を人間の決定として定めている**こと。採用の中心は
    **私が前回入れた本文の HTML コメントが、落としたはずの機構名と 02 の行番号を復活させていた**件
    (本文は SSOT に反映されるので、変更の説明は `reason:` に置く)と、
    **`D0-env-08` 項8 の括弧が 02 と食い違っていた**件(所有者ラベルの値は
    `claude-dev.project-dir` の写しであってマウント元ではない)。
  - **2周目(02 の変更指示6件)**: 指摘 22 件 → **採用 27 箇所**。実行順序・シェル構文・
    コマンド文字列・内部手段・**03 の手順番号への序数参照**(`MODULE-cli-reset` 手順6 /
    E2E-01 手順8。本タスクで実際に手順が繰り上がっており 02 が嘘になる直前だった)。
  - **3周目(03 の変更指示9件)**: 指摘 32 件 → **採用 31 箇所**。最重要は
    **`tests/e2e.md` が「`docker-proxy.md` の未検証3・4 が追跡する」と書いていたのに、
    その2行は同じタスクで削除済み**(現時点で虚偽)。ほかに `memo.md` への宙吊り参照2件
    (タスク削除で必ず消える)、**03 が受容を決めていた1件**(→ `docs/pendings.md` P-007)、
    `infra` が用語を再定義して 00 と食い違っていた1件。
  - **4周目(SSOT 00〜02 の全文)**: 指摘 83 件。**触れる節にあった 13 件は変更指示で移動**し、
    **残りは起票**: `docs/issues/085`(02 が実装の細部を持つ 11 件)/
    `docs/issues/086`(00・01 が機構を持つ 59 件。**00 にコードの行番号がある5件が最重**)。
    あわせて**規範自体の穴**を発見 — 00 は「technology は決めない」と定めるのに決定台帳は
    人間の技術選定を記録する器でもある。判定を保留し
    `.claude/improvements/KIT-where-technology-decisions-belong.md`(検討中)を起こした。
  - **5周目(修正そのものの点検。2本)**: 指摘 13 件 → **採用 10 件**。
    - **削られた記述 約80件を1件ずつ移し先で grep 照合**させた結果、**消失は1件**:
      `MODULE-docker-proxy-serve` 判断8 から落とした「既存の単体テストを全件回帰として流す」
      要求の移し先が空だった(`tests/docker-proxy.md` に `[DS-01]` 行として補った)。
    - **★最重要(フェーズ2 由来の欠陥)**: `MODULE-cli-stop` と `MODULE-cli-reset` の
      **既存の「実装上の判断」21 行から、理由が無言で削られていた**(変更指示は「3件を足す」
      としか宣言していないのに、既存行が短縮されていた)。**反映すると SSOT からその理由が
      消える** — `delegation.md` §3 が「これが無い状態こそ規範が解こうとしている問題」と
      書くものである。SSOT と1行ずつ突き合わせて**全 21 行の理由を復元**した
      (8行は SSOT の全文に戻し、13行は失われた理由節を追記。`reset` 判断5 の
      `D0-scope-07` への唯一の参照と「標準入力へ `y` を流し込む形は受け付けない」も復元)。
    - **自分が作った矛盾を2件直した**: `FR-env-03-3`/`-8` を「30 秒**以内**に反映」と書き替えて
      いたが、02 の機構は「30 秒**周期**のポーリング」なので**最悪の遅延が 30 秒を超え、01 と 02 が
      食い違う**(観測できる言い方に戻した)/ `FR-env-03-11` の書き替えが**握りつぶす実装も通す**
      形に弱まっていた。
    - ほかに、`MODULE-cli-stop` の「例外は名前付きボリュームとイメージ**だけ**」が
      `FR-env-01-22`(所有者を特定できなかった資源も対象外)と食い違っていた件、
      **存在しない issue 5件への参照**(`020` `024` `025` `029` `045` は解消して削除済み)、
      E2E-01 手順8-16 の後片付けが**直前の `reset` の後では大半が空振り**する件を直した。
    - **保留**: `D0-env-08` 項1 の資源列挙と項2 の `claude-dev-net` は
      `docs/issues/086` の「00 に技術名を書いてよいか」の裁定待ち群と同じ性質なので触っていない。

- 2026-08-07 **階層の点検(1回目)**(人間の指示「記述している内容が別の階層(より下位の)
  ドキュメントに書くべきものはないか。あるなら全て移動する」)。**変更指示の中だけで完結**。
  **移した先に事実が在ることを1件ずつ確認してから落としている** — 消したのではない。
  - **01(`functional.md` / `decisions/split.md`)**: 下位層 ID(`CTR-cli-container` / `DSN-env-03`)、
    実装ファイル名(`.credentials.json` / `settings.json` / `auth.json` / `config.toml` ほか)、
    ラベル名 `claude-dev.project-dir`、`DOCKER_HOST` のエンドポイント、共有ネットワーク名、
    前提コマンド名、同期の実現方法(「30 秒ごとに検知して書き戻す」)、
    ハッシュ桁数を落とした。**条項 ID は1つも動かしていない**(CS16 合格)。
    **数値は観測できる上限として残した**(「更新を 30 秒以内に反映する」)。
    `check-changeset.py` の **CS18 が OK** になった。
  - **00(`decisions/env.md` / `terminology.md`)**: `docker rm -f` / `COMPOSE_PROJECT_NAME` /
    `docker ps --filter ancestor=...` / 認証ファイル3件の列挙 / 用語の対比行の識別方法を落とした。
    **決定の意味は1つも変えていない**(落としたのは「どうやるか」だけ)。
    **00 は人間の層なので、この4箇所は変更指示の中に理由をコメントで残してある** — 反映前に
    差し戻せる(`new-features/00-requests/decisions/env.md` の末尾コメント)。
  - **02 は移すものが無かった**: 実装識別子(関数名・`main.go`・行番号・`{{.Names}}` など)を
    全文検索して 0 件。02 に出てくる `docker ps --filter …` は利用者に案内する手順で、
    契約が持つべき観測面である。
  - **判断の線**(報告のため明示する): **利用者が見る・打つものは残す**(CLI 名・終了コード・
    受理する文字種・表示内容・`/workspace`)。**システムが内部でどう決めるかは落とす**
    (ラベル名・フィルタ・正規化・ハッシュ・ポーリング周期・ファイル名)。

- 2026-08-07 フェーズ3(`/implement`): **タスク1〜6 を完了し、コミット4本を積んだ**
  (`a271d83` docker-proxy / `1d912b4` CLI / `235a89a` issues/076 / `8435b0b` 変更指示の整合)。
  **入場ゲートは3条件とも通過**(検証済み記録 16/16・未決点0件・lint/テストは実値)。
  **委任で決めたこと**: `D0-scope-02` で (a) 注入の本体を `injectOwnerLabels` と
  `writeBackBody` に切り出し両経路から呼ぶ、(b) `resolveProjectDir` を2値にして `ok` を落とす
  (2つは別々に空になりうるので1つの `ok` では表せない)、(c) 列挙を `spawned_resources` の
  共有関数に切り出す、(d) `destructive_rm` が常に 0 を返すため成否を `_DESTRUCTIVE_DELETED` の
  増加で判定する。いずれも該当 MODULE の「実装上の判断」に `D-ID` つきで記録した。
  **設計と食い違った点は無い**。ただし `MODULE-docker-proxy-serve` の手順3-3 は
  「エラーで無ければ続けて注入する」と読めたが、実装では注入を
  `validateContainerCreate` の**中**に置いた(判断5 と判断8 を同時に満たす最短の形)ため、
  手順の文面を実装どおりに書き直した。
  **QA レーン(`/codex-qa`)は起動していない**: `docs/02-design/environments.md`
  「Codex実行設定」が **QA(E2E + CDP探索)= 無効(未運用)** と定め、書き込み許可ディレクトリも
  ブラウザ排他ロックも「未定」で `docs/pendings.md` P-003 が前提条件として追跡しているため、
  レーン自体が構成上まだ動かせない。**代わりに E2E を自分で実行した**(DoD 11・12)。

- 2026-08-07 `/doc-check`(task) 判定: **PASS**(残存: 重大度「高」0件 /「中」2件 /「低」4件。
  **中の1件は人間の裁定待ち** — `sheet.md` 論点5。もう1件は既存の `段階可 × 部分(P-005)` で、
  規範により PASS をブロックしない。低の4件は `docs/issues/079` `080` `081` `082` へ起票済み)。レビュー: **サブエージェント4本**(初回3本 + 修正後の再監査1本。Codex は利用上限で実行不可。
  代替は `sheet.md` 論点4 で人間が承認済み。**実際に走ったのは `lens: subagent`**)。
  **独立レビューは4本で計 46 件を指摘し、そのうち 33 件を「確認済み・自動修正可能」または
  「委任決定」として変更指示へ反映した**(未決点8〜26)。**再監査(4本目)は重大度「高」を1件
  出した**: `CTR-cli-container`「## エラーケース」の節ごと差し替えで**既存2行が落ちていた**
  (`INT` / `TERM` 中断の行は `FR-env-03-23` を 02 側で受ける唯一の行)。同型を全件走査するため、
  **置き換える全節の表を SSOT と行キーで突き合わせる検査を書いて回した**(候補6件のうち
  真の欠落は2件、残り4件は意図した書き換えと確認)。とくに重かったのは
  **`CTR-cli-container` の4節と `02-design/system.md` のモジュール分割定義が影響範囲から
  漏れており、`DSN-env-04` が覆した前提(「compose 資源にはラベルを付けられない」
  「管理ラベルを付けるのは Claude コンテナだけ」)を保持したまま合成ビューに残っていた**こと。
  この2ファイルは `sections:` を増やして解消した(**closure のファイル一覧は変わらない** —
  同じファイルの別の節を足しただけである)。
  **検査済みの状態**(次回の増分実行の起点。`sha1sum` を再実行して一致すれば A〜E を省略できる):

  ```
  91ac0f07394a9d540d170d58248c5ed590e00a9f  00-requests/decisions/env.md
  b67a2ff56f5454f086065dff6f73bbe862cc53c3  00-requests/terminology.md
  d450835de58892b0c36ba218b5125f77bcabc8e5  01-requirements/decisions/split.md
  14dd86da549530c448e55cf9ece807fc9afdf855  01-requirements/functional.md
  b3c2e6166cc805611c79fa544303caa98ee2e783  02-design/architecture.md
  1647e0f7800d223cb53fe7ec68525713c4f801c2  02-design/contracts/cli-container.md
  9e5c031051ddc027281f20f9f4e6ad05d07fdb65  02-design/contracts/docker-api.md
  7b321d6ed6815a82500e4752b994f15ec76b4d7a  02-design/logging.md
  b1ef479f4abe3722f4fbf2d63373db60eb17cb94  02-design/relations.md
  be4f151d91f87821b8f9abd430d2967123d98cbf  02-design/system.md
  5b8fd0e1d8b9ef6623ac00fe2dd1f47fdb429446  03-impl/infra/local/docker-resources.md
  f607da7deaaf81d2d355e450c1fd23fd96a7a572  03-impl/relations/MODULE-cli-reset.md
  9a22a1e13da44ce4a9f83da398f30da5f00e1e5c  03-impl/relations/MODULE-cli-stop.md
  640e0d840e06c6a0abfc3941d1a130fcf916ea3c  03-impl/relations/MODULE-docker-proxy-serve.md
  ca21bfbe7a47ab7d443651a545f82f2b328bfdfe  03-impl/tests/cli-reset.md
  53c99cac7ce2a2a7f07a23603cb7ec953164cc0b  03-impl/tests/cli-stop.md
  27fab8f44ba193bdd5c6b3694993eb93f9b4a822  03-impl/tests/docker-proxy.md
  afa4023fc03fe9ecca1fbc1c91fe8dcf72410ba3  03-impl/tests/e2e.md
  71dc47468c9c67fe847535834a074639a8d40409  03-impl/tests/strategy.md
  ```

  <!-- 2026-08-07(規範更新後の再検査)で更新した。**MODULE-*.md の3件は、この再検査で
       中身を触ったのではなく、上の記録がフェーズ3 の C-1(コミット 8435b0b)より前の値の
       まま取り残されていたので取り直した**(git status で未変更であることを確認済み)。 -->

  - closure 側 SSOT の版: 「読む範囲(読了記録)」の 24 ファイルの版から**1つも動いていない**
    (他タスクは存在せず、SSOT 00〜03 は本実行で1文字も書いていない)
  - 機械検査: `check-changeset.py` 合格 / `check-relations.py` 合格 / `check-contracts.py` 合格 /
    `callgraph-check.py` 高 0 件 / `build-index.py --check` 差分なし / `check-sheet.py` 合格
  - **`--ssot docs` の一括検査は NG 31 件で、着手前(調査メモ9)から増減していない**

## 申し送り事項

- **論点6(= B)の後始末**: `docs/pendings.md` の **P-006**(`reset` 側と macOS 版の実機確認を
  未実施のまま受容)を 2026-08-07 に起票した。**`/task-close` はこれを最終化する**
  — 反映後に E2E の状態が変わっていないこと(`未検証(テスト未実装)` のまま)を確かめ、
  P-006 の「何が不完全か」の手順番号が反映後の `e2e.md` と一致することを確認する。
  **`docs/issues/` へは起票しない**(人間が受容と決めたので、issue ではなく pending が正しい置き場)。
- **`/task-close` の前に片付ける必要があるもの**(2026-08-07 の規範更新に由来。上の進捗メモ):
  1. ~~キットの1行修正~~ — **2026-08-07 に人間の合意を得て適用済み**
     (`.claude/improvements/KIT-cs19-section-name-and-test-templates.md` の「適用の記録」。
     独立レビューは `lens: subagent`、指摘9件・高0件を裁定)。`check-changeset.py` の CS19 は OK。
     **本流のキットへは `.claude/improvements/patches/KIT-cs19-section-name-and-test-templates.patch`
     を人間が当てる**(このプロジェクトの `.claude/` は配布キットの複製である)。
  2. **`CTR-cli-container` の冒頭2行を反映時に書き直す**(階層の点検の5周目で判明)。
     `docs/02-design/contracts/cli-container.md` の `# ` 見出し直下の
     「発行側(`MOD-cli-start`)がラベルの付与をやめると読み手側の削除対象が空になる」と
     「責任モジュール(結合テスト): MOD-entrypoint」は **`DSN-env-04` 導入後は半分しか成り立たない**
     (`MOD-docker-proxy` が止めても空になる / 識別の責任は `MOD-cli-stop` ほかへ移った)。
     節ではないので `sections:` で差し替えられず、変更指示は「こう読め」という注記で覆っている。
     **反映時にこの2行を実際に書き直し、注記を削ること**(注記のまま SSOT に残すと
     「古い記述と読み替え指示が同居する」状態になる)。
  3. **`MODULE-docker-proxy-serve` の `tests:` を 39 本に揃える**。対応表が名指すのに frontmatter に
     無いものが9本ある(`docs/issues/082`)。`/relations` の再生成で入るはずだが、**入っていれば
     `082` を解消として閉じられる**ので確認する。
  4. **反映で新設される見出しが5つある** — `03-impl/tests/` の5ファイルの
     「## テスト設計の判断」(`anchors:` が挿入位置を持つ)。`/task-close` の反映は
     `sections:` と `anchors:` を見て入れること。
  3. **`02-design/architecture.md` の「設計判断」と `system.md` の「分割の根拠」は節ごと置き換える**。
     architecture 側は `DSN-arch-02` の表に1行増えるだけで、**他の7件は文面が同一である**
     (差分が出ないことが正しい)。system 側は6件とも同一である。
- **`/task-close` がコードから確定させるもの**(フェーズ2 で変更指示を書かなかった3ファイル。
  理由は「影響範囲(closure)」の各行に書いた。**書き忘れると 02 の `DSN-env-04` に対応する
  実装の事実が 03 に無い状態が残る**):
  1. `docs/03-impl/contracts/cli-container.md`「実装上の事実」 — **管理ラベル**の行に
     `claude-dev.role=spawned` / `claude-dev.owner-project-dir` を追記し、**`stop` / `reset` が
     所有者ラベルで削除対象を引く**行を足す(`定義箇所` は実装後の `claude-dev` の行番号)。
  2. `docs/03-impl/contracts/docker-api.md`「実装上の事実」 — **所有者ラベルの注入**の行
     (対象パス2つ・上書きの扱い・付与できないときの挙動)を足す(`定義箇所` は
     `docker-proxy/main.go` の行番号)。「既知の制限」に、印を付けられない要求の残存を足す。
  3. `docs/03-impl/index.md` — 「この層の状態」の集計と層代表の `version` の更新。
     **02 との差分の表から「設計済み・未実装」の行が消えること**を確認する。
     **`:73` の「02(設計)との差分は上記4件で、これ以外に差分は無い」の件数も数え直す**
     (`DSN-env-04` の分が実装で解消するので4件のままのはずだが、確認せずに残すと
     `/doc-check ssot` が偽の完全性の主張として拾う)。
  4. **`docs/03-impl/tests/docker-proxy.md`** — `FR-env-07-11` / `FR-env-07-12` の
     **テスト識別子(いま `-`)を実シンボル名で埋め、状態を `実装済み` にする**。あわせて
     同ファイル「未検証(テスト未実装)の全件」の **3・4 の行を削除する**(解消の条件
     「所有者ラベルの注入の実装と同時に単体テストを追加した時点」が満たされるため)。
     **これに連動して `docs/03-impl/tests/strategy.md` の集計(209 条項 / 224 行 / 222 件)は
     変わらない**(行の増減が無く、状態列だけが動くため)。
  5. **`docs/03-impl/relations/MODULE-docker-proxy-serve.md` の frontmatter `tests:`** —
     追加した単体テストのシンボル名を足す(いまは既存15本のみ)。`/relations` の再生成で
     自動的に入るが、入っていることを確認する。
- **`docs/issues/077`(未検証の全件の「対象」列が旧表記のまま)との関係**: 本タスクで足した行は
  条項 ID の表記(`FR-env-01-22`)で書いた。既存行は旧表記(`FR-env-01 — 受入基準 6`)のまま
  残るので、`077` の移行対象は減っただけで解消していない。
