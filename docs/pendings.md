# 意図的な棚上げ(pendings)

<!-- 「これは未完成でよい」と能動的に決めたことだけを書く。書式は .claude/directions/issues-pendings.md §2。
     タスク化したら削除、仕様として確定したら削除して 01/02 に「対象外(理由)」として書く。 -->

## P-001 E2E スクリプトをコールグラフの解析対象外に置く

- 決めた日: 2026-08-02
- 決めた人: 人間(task-docs-restructure 決定シート2 の論点9)
- 何が不完全か: `scripts/e2e6-codex.sh` を `callgraph-config.local.json` の excludes に入れたため、
  このスクリプトの関数・呼び出し関係は機械検査の対象にならない。副次的に、内部の未使用ヘルパ
  `c_skip`(`c_ok` / `c_ng` と対になる出力関数で、スキップを出力する分岐が実装されていない)も
  未到達関数として検出されなくなった。
- なぜ今は OK か: E2E-6 の実機検証スクリプトは製品の機能ではなくテスト資産であり、機能表
  (境界の定義)に載せる対象ではない。記述は `03-impl/tests/e2e.md` が担う。
- どうなったら解消が必要か: E2E スクリプトが増えて相互に呼び合うようになったとき、または
  テスト資産にも呼び出し関係の機械検査を効かせたくなったとき。そのときは excludes から外し、
  テスト用の機能表を別に持つか、`tests/` 側の検査手段を用意する。
- 関連: `docs/03-impl/tests/e2e.md`(2026-08-03 の `/task-close` で SSOT へ反映済み)/ issues: なし

## P-002 PR での CI 自動実行を導入しない

- 決めた日: 2026-08-03
- 決めた人: 人間(task-docs-restructure。`02-design/environments.md` の「CI」節が「未定」として保持)
- 何が不完全か: PR や変更時に `go vet` と `go test` を自動実行する CI が存在しない。
  検査は各自が手元で実行する運用に依存しており、実行漏れを機械的に防げない。
- なぜ今は OK か: 自動テストを持つのは Go の `docker-proxy/` 1 モジュールだけで、
  実行時間が短く手元で完結する。利用者が社内の少人数に閉じており、実行漏れの被害範囲が小さい。
- どうなったら解消が必要か: 開発者が増えて手元実行の運用が守られなくなったとき、または
  Go 以外に自動テストを持つ領域が増えたとき。導入時は `02-design/environments.md` の
  「CI」節の「PR / 変更時」の行を実値へ置き換える(MINOR 変更)。
- 関連: 02-design/environments.md の「CI」節 / issues: なし

## P-003 QA レーン(独立QA)の各設定を未定のままにする

- 決めた日: 2026-08-03
- 決めた人: 人間(task-docs-restructure。`02-design/environments.md` の「Codex実行設定」が「未定」として保持)
- 何が不完全か: `/codex-qa` の運用に必要な設定値が決まっていない。具体的には
  プロファイル名 / モデル・reasoning / QA のタイムアウトと最大出力 / 最大調査ステップ /
  書き込み許可ディレクトリ / QA シードコマンドとリセットコマンド / **ブラウザ排他ロック** /
  CDP 探索を必須にする変更範囲 の8項目。
- なぜ今は OK か: QA レーンをまだ運用していない(`02-design/environments.md`「QA(E2E + CDP探索)」=
  無効)。使っていない機能の設定値であり、決めても検証できない。独立監査(`docs` / `readiness`)は
  有効で、そちらに必要な設定は確定している。
- どうなったら解消が必要か: QA レーンを開始するとき。開始前に上記8項目をすべて決め、
  `02-design/environments.md` の該当行を実値へ置き換える(MINOR 変更)。とくに**ブラウザ排他ロック**は
  同時実行で相互に壊すため、運用開始の前提条件である。
- 関連: 02-design/environments.md の「Codex実行設定」 / issues: なし

## P-004 認証情報をホストのプロジェクトディレクトリに平文で置く形を受け入れる

- 決めた日: 2026-08-04
- 決めた人: 人間(`task-impl-depth` のフェーズ4。`docs/issues/040` の裁定=案A「実装が正」に伴う受容)
- 何が不完全か: `D0-auth-03` が自ら記録している2つの残リスクが、受容の記録を持たないまま
  決定事項の本文だけに書かれていた。
  1. **認証情報がホストのプロジェクトディレクトリ配下に平文で存在する**
     (`<プロジェクト>/.claude/.credentials.json` / `.claude.json` / `<同>/.codex/auth.json`。
     `claude-dev:749`〜`:766` がコピーする)。`.gitignore` への自動追記で git 追跡からは外れるが、
     **バックアップ・同期ツール・他コンテナからのバインドマウント・zip や rsync による配布には乗る**。
  2. **`~/.claude.json` がファイル単位の symlink** である
     (`scripts/entrypoint-claude.sh:212`)。アトミック書き込み(一時ファイル → rename)で
     実体ファイルに置き換わりうる。`D0-auth-03` が当初この形を却下した理由はまさにこれで、
     **懸念は解消していない**(観測された障害は無い)。ディレクトリ単位の symlink はこの問題を受けない。
- なぜ今は OK か: 利用者は自分のサーバで自分のプロジェクトを扱う少人数に閉じており、
  ホストのホームディレクトリと同じ信頼境界の内側にファイルが増えるだけである
  (ホストの `~/.claude/` には元から同じ認証情報がある)。`NFR-sec-01` が禁じている4項目
  (Docker 生ソケット / SSH 秘密鍵 / イメージへの焼き込み / confinement の緩和)には**触れていない**。
  2 は実際の障害が観測されておらず、壊れた場合の影響は再ログインで回復する。
- どうなったら解消が必要か: (a) プロジェクトディレクトリを他者と共有する・配布する運用が入るとき、
  (b) 複数利用者が同じホストを共有するとき、(c) `~/.claude.json` が実体ファイルに化ける事象が
  観測されたとき。(a)(b) では共有ボリュームからの直接参照か、コンテナローカルへのコピーへ戻す
  変更(コード変更)を検討する。(c) はファイル単位 symlink をやめる。
- 関連: `docs/00-requests/decisions/auth.md`(`D0-auth-02` / `D0-auth-03`)/
  `docs/01-requirements/functional.md`(`FR-env-03` 受入基準2・7)/
  `docs/01-requirements/non-functional.md`(`NFR-sec-01`)/ issues: なし(`040` は解消済みで削除)

## P-005 compose 一意化名のハッシュ衝突を検出せず受け入れる

- 決めた日: 2026-08-04
- 決めた人: 人間(`task-fix-destructive-scope` の `/doc-check`(3回目)決定シート #4。推奨案で回答)
- 何が不完全か: `COMPOSE_PROJECT_NAME` を `<正規化名>-<起動ディレクトリの絶対パスの SHA-256 先頭6桁>`
  にして compose 資源をプロジェクト間で一意にする(`DSN-env-03` / `D0-env-08` 項7)が、
  **先頭6桁 = 24 ビットしか使わないため、異なる絶対パスが同じ値になる可能性が残る**。
  **衝突を検出する手段も、衝突したときの振る舞いも定義していない。**
  衝突した2ディレクトリでは、一方の `claude-dev stop` が**他方の compose コンテナと
  compose 既定ネットワークを削除しうる** — これは `docs/issues/024` と同じ事象である。
- なぜ今は OK か: 同時に扱うプロジェクト数は数十のオーダーで、その範囲では衝突確率が実用上
  無視できる(誕生日問題で 100 プロジェクトでも約 0.03%)。一方 `024` の現行の欠陥は
  **正規化(`[a-z0-9_-]` 以外を `-` に置換)が非可逆であるため、`~/work/My.App` と
  `~/other/my-app` のような「ありふれた組み合わせ」で確実に衝突する**。
  本変更は「高い確率で起きる衝突」を「実用上無視できる確率の衝突」に変えるものであり、
  衝突検出を入れないことは残る差分の受容である。
  桁数を増やすと `docker ps` の出力から人がプロジェクトを見分けにくくなる
  (`DSN-env-03` の却下案「ハッシュだけにする」と同じ理由)。
- どうなったら解消が必要か: **同時に扱うプロジェクト数が数百規模になったとき**、または
  衝突が実際に観測されたとき。そのときの選択肢は (a) 桁数を増やす
  (**既存の compose 資源が `stop` の対象から外れるので移行期の扱いを併記する**。
  `CTR-cli-container`「compose 資源の識別」が明記している)、(b) `start` 時に
  `docker ps --filter label=com.docker.compose.project=<一意化名>` で既存を引き、
  `claude-dev.project-dir` ラベルが自分と違えば衝突として中止する。
- 関連: **条項 `FR-env-01-19` と `FR-env-07-5`**(02 の要件カバレッジ表がこの2条項の充足を
  `部分(P-005)` と書く裏付け。条項ID を振る前の表記では `FR-env-01` 受入基準19 と
  `FR-env-07` 受入基準5)/ `docs/02-design/contracts/cli-container.md`「compose 資源の識別」/
  `DSN-env-03` / `D0-env-08` 項7 / issues: `docs/issues/024`(本変更が閉じる元の欠陥)

## P-006 `reset` 側と macOS 版の実機確認を未実施のまま受け入れる

- 決めた日: 2026-08-07
- 決めた人: 人間(task-stop-session-spawned-containers 決定シート 論点6 = B。
  理由「実行できないものは出来なくて当たり前」)
- 何が不完全か: `docs/03-impl/tests/e2e.md` の **E2E-01 手順8-14 の 1・2・7 / 手順8-15 /
  手順8-16 / 手順10・12**(`reset` がセッション由来の資源を所有者を問わず削除すること、削除失敗の扱い、
  2セッション同時での非巻き込み、**`logout` の後にセッション由来の資源が `stop` で回収できないこと**)と、
  **`claude-dev-mac` 全般**が実機で実行されていない。
  **手順8-16 は 2026-08-08 に `task-layer-placement` が新設したもの**で(`FR-env-03-24` の実機確認手順)、
  手順8-15 と同じ「他に作業中のセッションが無い専有ホスト」を前提とするため本項の対象に入る。
  対応表の状態は `未検証(テスト未実装)` のままで、シェル実装に自動テストランナーを
  設けない方針(`DSN-test-01` / `SR-32`)は変わらない。
- なぜ今は OK か: **実行できる環境が無い**。E2E-01 手順8 自身が「他に作業中のセッションが無い
  時間帯に行う」を前提として書いており、このホストでは別プロジェクトの Claude セッションが
  常時稼働している。macOS 版は実行機が無い。**代替として確認済みのもの**: 別セッションを
  巻き込まないことは `stop` 側で実機確認した(所有者の違う資源・所有者ラベルを持たない資源の
  いずれも無傷)/ macOS 版と Linux 版で該当コードに差分が無いことを
  `diff <(grep spawned claude-dev) <(grep spawned claude-dev-mac)` の完全一致で確認した。
- どうなったら解消が必要か: **専有できるホスト**(他の Claude セッションが無い時間帯)または
  macOS 機が使えるようになったとき。あるいは `reset` のセッション由来資源の削除で
  実際に不具合が観測されたとき。そのときは E2E-01 手順8-15 / 手順8-16 / 手順10・12 を実行する
  (ドキュメントもコードも変更を伴わない)。
- 関連: `docs/03-impl/tests/e2e.md`(E2E-01 / E2E-03)/ `docs/03-impl/tests/cli-reset.md`
  (`FR-env-01-25`)/ `docs/03-impl/tests/cli-stop.md` / issues: なし

## P-007 利用者がホスト側から手で付けた所有者ラベルの資源も片付け対象に入ることを受け入れる

- 決めた日: 2026-08-07
- 決めた人: AI(`D0-scope-02` の委任。**`SR-05`「信頼できる社内開発用途に限る」の前提の下で
  悪用の経路にならないと判断した**)
- 何が不完全か: `claude-dev stop` / `reset` は所有者ラベル(`claude-dev.role=spawned` /
  `claude-dev.owner-project-dir`)を持つ資源を削除する。このラベルは **docker-proxy 以外に
  ホスト側から `docker run --label` で手でも付けられる**ので、利用者が意図的に同じラベルを
  付けた資源は、セッション由来でなくても削除対象に入る。
- なぜ今は OK か: ラベルを手で付けるのは利用者自身の操作であり、`SR-05` が定める利用範囲
  (信頼できる社内開発用途)では第三者がラベルを仕込む経路が無い。**docker-proxy 側は利用者が
  指定した同名ラベルを上書きする**ので、コンテナ内からの偽装は成立しない
  (`CTR-docker-api` のエラーケース)。
- どうなったら解消が必要か: 利用範囲が `SR-05` の前提を超えたとき(第三者が同じホストの Docker を
  触れる運用になったとき)。そのときは所有者ラベルに docker-proxy だけが作れる値を持たせるか、
  片付け対象を別の手段で確認する必要がある。
- 関連: `docs/03-impl/relations/MODULE-cli-stop.md`「既知の制限」/ `CTR-cli-container` の規則 D /
  `SR-05` / issues: なし

## 残務(文書整合ほか)

- 2026-08-10 `INDEX.md`:全体 4層構成へ移行する前のパス(`docs/00-requests/decisions.md` / `glossary.md` / `acceptance.md` / `docs/01-requirements/core.md` / `docs/03-impl/cli.md` ほか)と `docs/_steering/` / `docs/knowledge/` / `docs/feedback/log.md` を指したままで、実在するファイルとほとんど対応していない。
- 2026-08-10 `README.md`:「ドキュメント」表 `docs/01_getting-started.md`〜`docs/10_ghcr-images.md` と `docs/impl/INDEX.md` を指したままで、いずれも 4層構成への移行で実在しない。
- 2026-08-10 `.claude/scripts/`:2026-08-10 のキット書き換えでプロジェクト固有の `*.local.json` が失われた。`callgraph-config.local.json` は task-remove-orchestrator で作り直したが、`entrypoint-patterns.local.json` / `changeset-invariants.local.json` の有無は未確認。
- 2026-08-10 `docs/issues/030`:`03-impl/index.md` の乖離件数の記述を問題にしているが、根拠に挙げる issue のうち `013` / `014` は task-remove-orchestrator で削除された。index.md の実測値を書き直したあとに閉じられるか再判定する。
- 2026-08-10 `docs/03-impl/tests/*.md`:状態列が「対象外(理由: …)」を使っているが、2026-08-10 のキット書き換え後の `build-index.py` は「テスト対象外」だけを数えるため、`tests/index.md` の第3列が全て 0 になる差分が出る(本タスクの範囲外なので `git checkout` で戻した)。語彙をどちらへ揃えるか決めて一括で直す。
- 2026-08-10 `docs/03-impl/features.md`「到達しない関数についての判断」:再生成した `feature-graph.md` が挙げる未到達 8 件のうち、`claude-dev::_destructive_done` / `_release_all_locks` と `claude-dev-mac::` の同名対 4 件に仕分けの行が無い(削除前から無い)。
- 2026-08-10 `.claude/directions/change-set.md` §2:「親の本文が変わり、かつ子見出しを改名する」を一つの変更指示で表せない(親を `sections` に載せると `merge_existing` が改名した子を拒否し、親を外すと `CS19` が「判断の節が `sections` に無い」で落ちる)。task-remove-orchestrator では改名する子を指示本文の冒頭へ出して回避した。
- 2026-08-10 `.claude/scripts/compose-changeset.py`:`docs/03-impl/features.md` の変更指示は `## 機能一覧` の差分表しか適用されず、`sections` に挙げた他の節(統合した機能 / 昇格させた共通基盤機能 / 到達しない関数についての判断)と frontmatter の `keywords` に届かない。`.claude/directions/change-set.md` 例外1 の「§2 frontmatter still applies」と食い違う。
- 2026-08-10 `.claude/scripts/`(git 追跡外):task-remove-orchestrator が CLAUDE.md §3 の例外として最小修正を 6 箇所入れた。`compose-changeset.py` = `verified:` ブロックの除去 / relations・`features.md` への版要求の撤回 / 変更指示 frontmatter の反映 / `features.md` の `## 機能一覧` 以外の sections の適用 / `features.md` の `updated` 打刻、`close-task.py` = 条件 (b) から `change: delete` の対象を除外。**版管理の外にあるので、キットを配り直すと失われる。**
- 2026-08-10 `.claude/directions/change-set.md` §2:最初の見出しより前の本文(frontmatter 直後の HTML コメント)を `sections` にも `deletes` にも載せられないため、陳腐化した検証記録の削除が反映時の手作業として残る。task-remove-orchestrator では `01-requirements/functional.md` / `non-functional.md` / `03-impl/index.md` の 5 件を手で消した。
- 2026-08-10 `docs/issues/009`:指摘の実体(約27件のシグネチャ不一致)は orchestrator の relations ごと消えたため 0 件になった。残るのは「省略記法を許容するかの規約が無い」という規約側の欠落だけで、`related` は実在しない ID を指したままである。
- 2026-08-10 `docs/issues/` の `related` の陳腐化:orchestrator の削除で消えた ID / パスを指したままの issue が **9 件**ある — `004`(MODULE-orchestrator-controller ほか 4)/ `009`(MODULE-orchestrator-* 10)/ `030`(同 5)/ `054`(decisions/orch.md ほか 3)/ `056`(issues/038)/ `066`(NFR-perf-03 / tests/orchestrator.md ほか)/ `072`(contracts/cli-orchestrator.md ほか)/ `094`(FR-orch-03-3 / CTR-cli-orchestrator)/ `095`(contracts/orchestrator-prompt.md)。あわせて `095` の `pattern_survey` の実測値は「24 箇所」だが `check-changeset.py --ssot` の現在値は 6 箇所である。**9 件まとめて1回で棚卸しする**(1件ずつ直すと同じ走査を9回することになる)。
- 2026-08-10 frontmatter `id` の重複:`docs/03-impl/tests/images.md` と `docs/03-impl/environments/images.md` がどちらも `id: images` で、CLAUDE.md §7「`id` は `docs/` 全体で一意」に反する(契約の共有 id と `index.md` の例外には当たらない)。テンプレート `03-tests-module.md`(`id: <module-slug>`)と `03-environment.md`(`id: <topic>`)がどちらも `images` を導くため、直すにはキット側の命名規約を決める必要がある(キットは CLAUDE.md §3 により製品 DoD 未達の間は凍結)。
- 2026-08-10 規範案(キット凍結中のため実施は製品リリース後):変更指示の語彙が SSOT へ漏れても、どの機械検査も落ちない。`| FR-env-12-12 | delete | 廃止する… |` の行はフェーズ2 の `/doc-check`(タスクモード)PASS・`compose-changeset.py` のドライラン・反映のすべてを通り抜け、`/doc-check ssot` の目視で初めて見つかった。SSOT 側で `種別` 列が `正常系` / `境界値` / `異常系` 以外の値を持つ受入基準行と、frontmatter の `change:` / `sections:` / `version_bump:` を落とす `CS` 検査を足す。
- 2026-08-10 `MOD-makefile` の本数:`relations-query.py --health` が 16 本(目安の 15 本超)として 02 の分割定義の見直しを提案している。orchestrator 削除で 19 本 → 16 本に減ったが目安は超えたままである。
