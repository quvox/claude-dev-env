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
- 何が不完全か: `/browser-qa`(`/verify-tests` の qa scope) の運用に必要な設定値が決まっていない。具体的には
  プロファイル名 / モデル・reasoning / QA のタイムアウトと最大出力 / 最大調査ステップ /
  書き込み許可ディレクトリ / QA シードコマンドとリセットコマンド / **ブラウザ排他ロック** /
  CDP 探索を必須にする変更範囲 の8項目。
- なぜ今は OK か: QA レーンをまだ運用していない(`02-design/environments.md`「QA(E2E + CDP探索)」=
  無効)。使っていない機能の設定値であり、決めても検証できない。独立監査(`docs` / `readiness`)は
  有効である。**その モデル・reasoning の行は「未定(いつ決めるか)」のままで、
  未記入なのでキットの既定が効く**(2026-08-12 に `task-issue-sweep` が実態へ揃えた。
  「確定している」という以前の記述は事実と違っていた)。
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
  compose 既定ネットワークを削除しうる** — これは正規化の非可逆性による衝突(2026-08-04 に解消済み)と同じ事象である。
- なぜ今は OK か: 同時に扱うプロジェクト数は数十のオーダーで、その範囲では衝突確率が実用上
  無視できる(誕生日問題で 100 プロジェクトでも約 0.03%)。一方、本変更前の現行の欠陥は
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
  `DSN-env-03` / `D0-env-08` 項7 / issues: なし(元の欠陥の `024` は本変更で解消済み・削除)

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
- 2026-08-22 **`check-ssot.py` の CS21(件数の主張)が、複数レンジの summary を偽と報告する**: `docs/00-requests/acceptances.md` の summary は `AC-01〜AC-03 と AC-06〜AC-08` と全数を正しく書いているのに、検査は最初のレンジだけを読んで残りを「summary が実体より狭い」と出す(`docs/01-requirements/usecases.md` の `UC-01〜UC-03 と UC-06`、`docs/03-impl/tests/e2e.md` の `E2E-01〜E2E-03 と E2E-06` も同型で、計4件すべて誤検知)。文書側は正しいので直さない。キットの検査の側の話であり、凍結が解けたら `/kit-improve` で扱う(F2 文書整合フロー)
- 2026-08-22 **`docs/02-design/environments.md:58` が E2E 台本の ID を固定の置き場の外で使っている**(`check-ssot.py` CS22)。e2e の失効判定は `system.md` と `testing.md` しか見ないので、この言及は失効判定に効かない。定義も言及も `system.md` へ寄せるか、`testing.md` を新設して `e2e_scripts_in` を宣言し直すかの二択(F2 文書整合フロー)

- 2026-08-20 `docs/pendings.md` の「残務(文書整合ほか)」節: 残務行の 48 行中 40 行が日付の直後に `docs/` 始まりのパスを置いていないため、`.claude/scripts/doc-health.py:437` の `LEFTOVER_RE` が第2トークンをパスとして取る前提が崩れ、`:486` の実在検査(`docs/` 始まりのパスが消えていたら落とす)が大半の行に効いていない(規範は `.claude/directions/issues-pendings.md` §2.1 でこの形を load-bearing と明記する。キット凍結中なので規範側の判断は `/kit-improve` が持つ)。
- 2026-08-20 **`docs/02-design/environments.md` の `source:` と `verified.against:` が、同ファイル `:177`-`:188`(監査と QA が走るサンドボックスの強度)の根拠2文書を持たない**(F3 実装整合フロー / 独立レビュー lens: claude が検出)。同段落は `docs/00-requests/decisions/dist.md` の `D0-dist-04` 項6 と `docs/01-requirements/functional.md` の `FR-env-12-5` を根拠に引くが、`source:` は `docs/01-requirements/system.md` と `docs/02-design/architecture.md` の2件だけで、`verified.against:` も同じ2件しか持たない。上流が動いたときにこの段落が失効することを機械が言えない。**段落の内容そのものは上流と一致している**ことは確認した(`dist.md:82`-`:88` / `functional.md:324` / `architecture.md:258`-`:263`)ので、これは記述の誤りではなく追跡欄の取りこぼしである。次に `environments.md` を触るタスク、または `/verify-docs` が `source:` を取り直す。
- 2026-08-20 **キットの規範 `.claude/directions/orchestration.md` §1.1.1 が、コンテナ内では正常な `bwrap` の非ゼロを codex 起動の可否として読む**: 同節は「起こす前に1回だけ確かめる2行」として `bwrap --unshare-user --unshare-net --ro-bind / / /bin/true; echo $?` を挙げて「0 なら codex を使える」と定め、§1.3 の表は非ゼロを「workspace-write で起こせる環境ではない」としてフォールバックさせる。claude-dev コンテナ内でこの1行が exit 1 を返すのは正常であり(`docs/02-design/environments.md`「codex を起こす側が前提にしてよいこと」)、その環境では codex がまったく起こされない。これが 2026-08-20 に人間の裁定で削除した issue `102` の報告文「bwrap が非ゼロのため codex を起こせず」の出どころである(経緯は `docs/histories/2026-08-20-document-codex-sandbox-preconditions.md`)(2026-08-20 実測。同梱の colabtmux 両バイナリと稼働中のバイナリには `bwrap` / `bubblewrap` / `landlock` / `sandbox` の文字列が0件で、判定は colabtmux 側ではない)。可否の判定は `codex sandbox -- /bin/true` が exit 0 かどうかで行い、コンテナ内では既定3鍵のまま(`--sandbox workspace-write` を付けずに)起こすのが正しい。**キットは CLAUDE.md §3 により製品 DoD 未達の間は凍結されており、直せるのは `/kit-improve` だけである。**
- 2026-08-20 **コンテナが置く codex の既定3鍵が、ホスト側の codex にも効く**: entrypoint は3鍵を `/workspace/.codex/config.toml` に置くが、これはホストのプロジェクトディレクトリそのものである。同じディレクトリでホスト側の `codex` を起こすと `sandbox_mode = "danger-full-access"` / `approval_policy = "never"` / `[features] use_legacy_landlock = true` が効き、ホスト側の codex はサンドボックスと承認なしで走り、`sandbox_mode = "workspace-write"` を要求する起動は exit 101 で panic する(2026-08-20 実測)。置き場所は `AC-06`(設定と履歴がプロジェクトごとに独立していること)と `CTR-cli-container` が定めたものなので、変えるには 00 の合意が要る。P-004 は同じディレクトリに**認証情報**が平文で在ることを受容しているが、**設定がホスト側の動作を変えること**は覆っていない。次に codex の設定の置き場所を触るタスク、または人間が置き場所を決めるときに裁定する。
- 2026-08-20 **`make clean` を `D0-env-08` の破壊的操作の定義に加えるかが未裁定**: 同決定の用語は破壊的操作を `claude-dev stop` / `logout` / `reset` の3つと**明示的に列挙**しており、`make clean` は入らない。そのため `make clean` は今も**管理ラベルを持たない Claude コンテナを集合として削除する**(規則 A の「ラベル無しは名前を表示して残す」が掛からない)。2026-08-20 の`fix-session-list-undercount` は数え落としだけを直し、削除の範囲は変えていない(和集合が新たに加えるのは管理ラベルを持つ = 本システムが作ったコンテナだけである)。**どちらが正かは 00 の決定なので、`docs/issues/046` の「対処案」の指摘をここへ移す**。次に `D0-env-08` を触るタスク、または人間が `make clean` の対象を決めるときに裁定する。
- 2026-08-20 **`docs/pendings.md` P-006 の「手順10・12」がどの手順を指すか確定できない**: 2026-08-07 の起票時点の `docs/03-impl/tests/e2e.md` の E2E-01 には**上位の手順10 が存在しなかった**ので、文脈(手順8-14・8-15・8-16 と並んでいる)から**手順8-10・8-12** を指すと読めるが、断定できないので書き換えていない。**2026-08-20 に E2E-01 手順10(セッション一覧の数え方)を新設したため、この表記は別の手順とも読めるようになった**。次に P-006 を触るタスクが起票者の意図を確かめて確定する。
- 2026-08-19 **`docs/03-impl/infra/local/docker-resources.md`:「Docker 資源の一覧」の本文が、実在しない `docs/issues/040` を根拠として引いている**: `:18` は「直前に削除した理由(source の `docs/02-design/architecture.md` が未検証 = `docs/issues/040` の高)」と書くが、`docs/issues/040` は既に削除されていて `docs/issues/index.md` にも無い。読者が根拠を辿れない。本タスクの closure 外の既存記述で、機械検査には掛からない(`/doc-check ssot` の C12 が検出)。次に同ファイルを触るタスクが、事実を本文へ書くか参照を落とすかを決める。
- 2026-08-19 **`FR-env-07-11`・`-12` がどの UC のフローにも「シナリオ外要件」にも現れない**: `docs/01-requirements/usecases.md` の `UC-03` の基本フロー3 は「許可・書き換え・拒否のいずれか」までで、所有者ラベルの**付与**という第4の作用を持たない。代替 `A1`〜`A3` / 例外 `E1`〜`E4` にも無く、`:159`-`:165` の「シナリオ外要件」表にも `FR-env-07` の行が無い。2026-08-12 の残務(issue 080 残件)は `FR-env-01` / `FR-env-03` だけを対象にしており、この2条項は覆われていない。次に `FR-env-07` か `usecases.md` を触るタスクが行を足す(`/doc-check ssot` の A1 が検出)。
- 2026-08-19 **`docs/02-design/system.md`「要件カバレッジ確認」の主担当が複数モジュールの行がある**: `:186` は「1条項につき主担当モジュールはちょうど1つ」と定めるのに、`NFR-avail-02` / `NFR-avail-03` / `NFR-sec-01` / `NFR-ops-02` / `-03` / `-05` / `NFR-scale-01` / `-02` の8行は割り当てモジュール列に2つ以上を書いている(非機能要件は条項に分けず1要件1行なので `充足` は1度しか書かれておらず、機械検査には掛からない)。本タスクの closure 外の既存記述。次に非機能要件のカバレッジを触るタスクが、主担当を1つに決めるか本文の言い回しを直すかを判断する(独立レビュー Codex が検出)。
- 2026-08-18 **テストの状態列の語彙が2つある**: `.claude/directions/03-impl.md` は `実装済み` / `未検証(テスト未実装)` / `テスト対象外(理由)` の3語だけを許し、`build-index.py` はその語を数えて `tests/index.md` の進捗を作る。しかし `docs/03-impl/tests/strategy.md`「状態列の語彙の定義」は `対象外(理由)` と定義しており、`tests/images.md` の「契約の結合テスト」「機能間連携仕様書 ⇄ テスト」の2行も同じ語を使っている(独立レビュー Codex が `task-bundle-external-binaries` の `/doc-check` で検出)。**同型の欠陥は他の `tests/*.md` にも在りうる**。`task-bundle-external-binaries` は書き直した節の中にあった 02 側の同型の誤り(`対象外(理由)` → `適用外(理由)`)だけを直し、この 03 側は触っていない(書き直す節の外にあるため)。次に `tests/` を横断で触るタスクが語彙を1つへ揃える。**2026-08-10 の「状態列が『対象外(理由)』を使っている」の残務と同じ根であり、そちらと一度に直すのが安い。**
- 2026-08-18 **`DSN-dist-01` の見出しが射程より狭い**: `task-bundle-external-binaries` がこの判断の射程を同梱外部バイナリまで広げたが、見出しは「エージェント CLI の導入は…」のままである。改名は「旧子見出しの `deletes` + 新しい子見出しの `anchors`」を要し、`CS19` が同時に要求する親「設計判断」の `sections` 掲載と両立しない(2026-08-10 の残務が記録している既知の制約と同じ型)。本文の冒頭に射程を広げた旨と日付を書いて当座をしのいでいる。キットの凍結が解けて `change-set.md` §2 と `CS19` の両立が直ったら、見出しを射程に合わせて改名する。
- 2026-08-11 **`FR-env-03` 受入基準19 が1条項で4つの義務を負っている**: (1) 削除対象が0件なら確認を求めず終了コード 0、(2) 共有ボリュームが空であることを確認できなければこの経路に入らない、(3) 管理ラベル付きコンテナの集合を確認できなければ入らず失敗に数えて 1、(4) ラベル無しの稼働中コンテナがあれば名前と書き戻しを表示する。**条項単位の充足・検証状態を4つに分けて数えられない**(`task-fix-logout-zero-target-path` の `/doc-check` が最弱点として挙げ、`task-fix-logout-records-and-marker` で義務が1つ増えた)。分けるには 02 のカバレッジ表と 03 のテスト表に行を足すことになり、**人間が承認した方針(「条項 ID は動かさない」)を超える**ためどちらのタスクでも分けていない。次に `FR-env-03` を要件側から動かすタスクで、条項を分けるかを判断する。
- 2026-08-11 `docs/03-impl/contracts/cli-container.md` の frontmatter `impl:` が `claude-dev::main#start, claude-dev-mac::main#start` だけを挙げているのに、本文は `spawned_resources` / `stop` / `logout` / `reset` / ロック / 遊休判定 / 破壊結果の記録 / 共有ボリュームの列挙まで実装上の事実として記述している(独立レビュー Codex が `task-fix-logout-zero-target-path` の `/doc-check ssot` で検出。指摘の重大度「低」)。契約の実装範囲が起動側だけに見えるので、`impl:` を実態へ広げるか、契約の担当範囲の書き方を決めるかを次に契約を触るタスクで判断する。
- 2026-08-11 `docs/02-design/relations.md` に **`PLAN-cli-logout` の「連携の詳細」節が無い**(`PLAN-cli-stop` / `PLAN-cli-reset` / `PLAN-entrypoint-claude` / `PLAN-docker-proxy-serve` / `PLAN-cli-common-*` には在る)。`reset` の「失敗の扱い」だけが「列挙の問い合わせの失敗を0件と区別する」を持ち、`logout` 側には同じ意図を書く場所が無い(`task-fix-logout-zero-target-path` の申し送り。`CTR-cli-container` のエラーケースが同じ倒し方を持つので**振る舞いは定まっている** — バグではなくドキュメント整合の穴)。次に `PLAN-cli-logout` を触るタスクが節を立てる。
- 2026-08-11 **実機 E2E-01 手順8 が未実施**: `task-fix-logout-zero-target-path` の3つの修正(`docs/histories/2026-08-11-fix-logout-zero-target-path.md`)は隔離ハーネス(資源名を `cdx-e2e-*` へ書き換えた `claude-dev` の複製)で実機 Docker に対して修正前後の差分として確認したが、**E2E-01 手順8 そのものは流していない**。手順8 は `claude-dev login`(対話 OAuth)から始まり `logout --yes` / `reset --yes` を含み、実行すると操作者の Claude / Codex 認証と claude-dev のイメージ・ボリュームが実際に消えるため、無人のフェーズ3 では実行できない(`sheet.md` 論点4 = 案A で人間が承認)。**残っている確認は (a) 実イメージ `claude-dev-claude` での手順8-18・8-19、(b) macOS 版(`claude-dev-mac`)の実行、(c) 手順8 の他の部分手順の回帰**の3つ。`logout` 分岐は両 OS でバイト単位で同一であることを確認済み。次に環境を作り直す機会があるときにまとめて流す。**2026-08-11 の `task-fix-logout-records-and-marker` も同じ状態である**(隔離ハーネスで T1〜T4 と対照2件を確認済み。手順8-18 の (c) と手順8-19、手順8-10 の追加分が実機未実施として増えた。前タスクの `sheet.md` 論点4 の裁定を同型として適用した)。
- 2026-08-11 コード引用の行番号のずれ: `task-fix-logout-zero-target-path` の実装で `claude-dev` / `claude-dev-mac` の `logout` 分岐が **+58 行**、続く `task-fix-logout-records-and-marker` で**さらに +44 行**になったため(**合計 +102 行**)、旧 1119 行目以降を指す `path:line` 引用が **closure 外の 03-impl ドキュメント9件**で古くなった — `MODULE-cli-start` / `-stop` / `-reset` / `-common-net-other-running-containers` / `-common-container-project-dir` / `-common-compose-project-name` / `features.md` / `contracts/entrypoint-firewall.md` / `index.md`(**2026-08-19 の `task-stop-cleanup-and-project-env` で `+102` の一律補正は成立しなくなった** — フェーズ3 の実装が `claude-dev` を +309 行にし、続く修正が区間ごとに -11 / -7 / +4 とずれ幅を分けたため、**1件ずつ実コードに当てて取り直すしかない**。`MODULE-cli-common-destructive` の `claude-dev-mac:1133` は変更範囲の内側なので同様。**ずれは掃除するまで増え続ける**)。**2026-08-19 の4回目の `/doc-check ssot` が全 03-impl の引用を実コードに当てて数え直した**: 現に腐っているのは **10 文書 190 トークン** — `contracts/cli-container.md`(87)/ `contracts/docker-api.md`(38。`validateExecCreate` は現在 `docker-proxy/main.go:760`-`:777`)/ `MODULE-cli-common-compose-project-name`(18)/ `MODULE-cli-common-destructive`(12)/ `features.md`(9)/ `MODULE-cli-logout`(8)/ `MODULE-cli-common-net-other-running-containers`(7)/ `contracts/entrypoint-firewall.md`(6)/ `MODULE-cli-common-container-project-dir`(4)/ `MODULE-cli-common-lock`(1)。closure の6文書(`index.md` / `MODULE-cli-start` / `-stop` / `-reset` / `-common-spawned-resources` / `-common-write-project-ssh-keys`。計 76 トークン)は同日に取り直し済みである。`.claude/directions/03-impl.md` は「行番号は編集ごとに腐る」ことを前提に安定なアンカーを勧めており機械検査も無いので、バグではなく残務として記録する。**次にこれらのドキュメントを触るタスクが同じ降下で直すこと。****2026-08-20 の `fix-start-auxiliary-halts-and-tmux-runtime-env` が `03-impl/contracts/cli-container.md` の参照を実測した: 129 トークン(ファイル名つき 43 / 裸の `:NNN` 86)。裸の側は直前の名前つき参照に係るので、1件ずつ実コードに当て直すしかない。同タスクが触った行の引用は現在値へ取り直したが、残りは持ち越した。**同タスクは `claude-dev` を +26 行 / `claude-dev-mac` を +26 行 / `scripts/entrypoint-claude.sh` を +25 行にしている**ので、`claude-dev` の 1464 行目より後ろ・`claude-dev-mac` の 1541 行目より後ろ・`entrypoint` の 15 行目より後ろを指す引用はさらにずれる。**2026-08-20 の `fix-session-list-undercount` で `claude-dev` / `claude-dev-mac` の `list` 分岐が各 +15 行になった**ので、**両ファイルの 2169 行目より後ろを指す引用はさらに +15 ずれる**(closure 外で該当するのは `MODULE-cli-reset`(6箇所)/ `MODULE-cli-common-spawned-resources`(1箇所)/ `03-impl/index.md`(`claude-dev:2607` / `claude-dev-mac:2649` の各2箇所)/ `docs/issues/097` である。**履歴(`docs/histories/`)は当時の事実なので直さない**)。
- 2026-08-10 `INDEX.md`:全体 4層構成へ移行する前のパス(`docs/00-requests/decisions.md` / `glossary.md` / `acceptance.md` / `docs/01-requirements/core.md` / `docs/03-impl/cli.md` ほか)と `docs/_steering/` / `docs/knowledge/` / `docs/feedback/log.md` を指したままで、実在するファイルとほとんど対応していない。
- 2026-08-10 `README.md`:「ドキュメント」表 `docs/01_getting-started.md`〜`docs/10_ghcr-images.md` と `docs/impl/INDEX.md` を指したままで、いずれも 4層構成への移行で実在しない。
- 2026-08-10 frontmatter `id` の重複:`docs/03-impl/tests/images.md` と `docs/03-impl/environments/images.md` がどちらも `id: images` で、CLAUDE.md §7「`id` は `docs/` 全体で一意」に反する(契約の共有 id と `index.md` の例外には当たらない)。テンプレート `03-tests-module.md`(`id: <module-slug>`)と `03-environment.md`(`id: <topic>`)がどちらも `images` を導くため、直すにはキット側の命名規約を決める必要がある(キットは CLAUDE.md §3 により製品 DoD 未達の間は凍結)。
- 2026-08-10 `MOD-makefile` の本数:`relations-query.py --health` が 16 本(目安の 15 本超)として 02 の分割定義の見直しを提案している。orchestrator 削除で 19 本 → 16 本に減ったが目安は超えたままである。
- 2026-08-11 `docs/03-impl/relations/` の「実装上の判断」の書式が2つある:新設・改訂した5本は `.claude/directions/delegation.md` §3 の1行形式(`[委任ID] 決めたこと — 理由 / 見直す条件`)だが、既存 56 本は3列テーブル(`# | 判断内容 | 根拠(委任ID)`)で**見直す条件を持たない**。独立レビュー(Codex)が `MODULE-cli-logout` / `-reset` / `-start` / `-stop` について指摘した。全 56 本の一括移行になるので `task-promote-shared-helpers` では扱わない(検査 CS17 は `[DS-nn]` の行だけを見るため機械的には落ちない)。
- 2026-08-11 シェル抽出器の決定 D がラベル全体を落とす:`help|*)` のように**名前付きラベルと catch-all が同じラベルに同居する**と、`*` を含むという理由でラベル全体が入口から外れ、`help` の側も巻き添えで落ちる(`.claude/scripts/cgx/shell_regex.py:169`)。`docs/issues/097` が実測込みで追跡しており、直すならキットの凍結が解けてから(`|` で分割して `*` の要素だけを落とす形にする)。
- 2026-08-11 01 層に終了コード 130 の記述が無い:`acquire_lock` がロック取得より前に `trap '_release_all_locks; exit 130' INT TERM` を仕掛ける(`claude-dev:602` / `claude-dev-mac:685`)ため、`start` / `stop` / `login` / `login-codex` もロック取得後の `INT`・`TERM` で 130 を返す。`01-requirements/functional.md` が 130 に触れるのは `FR-env-03-23`(`logout` / `reset` の**削除の途中**)だけで、それ以外の経路の 130 はどの受入基準にも無い。03-impl 側は 2026-08-11 の `/relations all --apply` で `MODULE-cli-start` / `-stop` / `-logout` / `-reset` の戻り値欄に記載済み。**利用者から見える値なので、01 へ上げるかは要件側の判断**(上げるなら `/task-new`)。
- 2026-08-12 **issue 004 の残件4項目**(`task-issue-sweep` が原則8のゲート行4として降格): 03-impl が「ドキュメントだけから再実装・再試験できる」深度に達していない領域が4つ残る — 永続データモデルの記述 / モデル・effort ポリシー / 観点6(テストデータの準備と後始末)/ 02 契約の復号レベルのエラーケース。どの `AC-nn` も塞いでいない。起点は `D0-scope-07`。
- 2026-08-12 **issue 006 の残件**(同上): E2E シナリオの実施手順に固定入力・観測点・合否判定の根拠・後始末が揃っておらず、実施者によって結果が変わりうる。`docs/03-impl/tests/e2e.md` を次に触るタスクが揃える。
- 2026-08-12 **issue 066 の残件**(同上): `NFR-perf-01` / `NFR-avail-03` / `NFR-sec-01` / `NFR-scale-01` / `NFR-ops-02` の5件で、「要件」列が述べる内容の一部しか「目標値」「測定方法」列が測っていない(起票時の6件のうち `NFR-perf-03` は 2026-08-08 に廃止済み)。
- 2026-08-12 **issue 072 の残件**(同上): 仕様ドキュメントのどこにも書かれておらず実装者が値か方針を発明するしかない箇所が5件(2026-08-06 に人間が案C=据え置きを裁定した分)。
- 2026-08-12 **issue 080 の残件**(同上): 破壊的操作(`stop` / `logout` / `reset`)の条項がどの UC のフローにも現れず、`docs/01-requirements/usecases.md` の「シナリオ外要件」表にも `FR-env-01` / `FR-env-03` の行が無い。E2E-01 手順8 が上流の UC を持たない検証になっている。
- 2026-08-12 **旧表記「受入基準 N」の残り 61 箇所**(`task-issue-sweep` が 127 箇所を直した残り。追跡していた issue は同タスクで削除したので、以後はこの行が持つ): 条項ID へ機械変換できた 127 箇所(18 ファイル)は直したが、`docs/03-impl/tests/e2e.md`(43)と `cli-logout.md`(8)ほかの**散文中の参照**は `FR-env-01` 受入基準 14〜27 のような**範囲表記**を含み、条項ID の記法では表せない。範囲を条項ID で書く規約を決めてから直す。
- 2026-08-12 **実機 E2E の残務(`task-issue-sweep` 分)**: E2E-01 手順8 の全体は未実施(`logout` / `reset` を実機で流すとホストの稼働中セッションと認証・イメージが失われる。前タスクと同じ扱い)。加えて **手順8-15 の VM 部分**(`/dev/kvm` が要る)と **新設した手順8-20**(macOS 実行機が要る)、**E2E-03 手順5・6** が未実施である。代替として確認したもの: 051 / 088 / 047 は実 Docker、101 は隔離ハーネス、023 は検証ロジックの切り出し、087 は新設した単体テスト2本。
- 2026-08-12 **残る issue 6 件のうち 4 件に `origin_layer` が無く、5 件に `closes_when` が無い**(`005` / `010` / `028` / `055` は両方欠落、`094` は `closes_when` のみ欠落)。`.claude/directions/issues-pendings.md` §3 はどちらも必須としており、`check-ssot.py` の CS20 が 4 件を報告し続ける。いずれも `task-issue-sweep` より前から在る欠落で、それぞれの issue を次に扱うタスクが埋める(独立レビュー Codex が検出。2026-08-20 に `076` / `079` / `081` / `046` の削除を反映して件数を取り直した)。
- 2026-08-19 削除済み `docs/issues/024` を指す参照が**3件**残る(`issues/028-modify-name-uniqueness-does-not-satisfy-nfr-scale-01.md:21`・`:58`・`:68`。**CS11 は 00〜03 層しか走査しないので、この6件はどの機械検査にも現れない**)。024 は経緯の履歴が複数あって指す先が一意に決まらないため、参照を落とすか事実を本文へ書くかを次に同ファイルを触るタスクが決める。(経緯: 2026-08-20 の F3 が `046` の残り3件を履歴 `docs/histories/2026-08-20-fix-session-list-undercount.md` を指す形へ直し、2026-08-20 の F2 が `docs/issues/002` の2件 — `03-impl/relations/MODULE-cli-common-write-project-ssh-keys.md:86` / `MODULE-cli-ssh-keys-reset.md:30` — と `docs/issues/092` の1件 — `02-design/architecture.md:192` — を、指す先の履歴を選ばずに**参照そのものを落とす**形で直し、2026-08-20 の F2(`docs/pendings.md` の部分再検証)が同じ形で `pendings.md:88`・`:106` の2件を落としたので `check-ssot.py` の CS11 は OK になった)。
- 2026-08-19 `docs/01-requirements/usecases.md` の `UC-01` 節: 新設条項 `FR-env-07-13` の実機確認(`E2E-01` 手順9)は `UC-01` に載るが、`UC-01` の関連要件に `FR-env-07` が無い(`FR-env-07` は `UC-03` の関連要件であり、`UC-03` は Docker API の検査・中継だけを扱う)。同じ形が `E2E-01` 手順8 について 2026-08-12 の残務に既に在る。UC の関連要件を条項単位で持つ規約を決めてから直す(独立レビュー Codex が検出。重大度「中」)。
- 2026-08-19 `docs/03-impl/tests/e2e.md` の「実機確認の手順」節: E2E-01 手順7-3 の「出力に `SSH 鍵が未設定` の行が現れたら、**すぐに**同名の代役コンテナを立てる」に観測可能な同期点も上限時間も無く、競合の窓に入れるかが実行機の速度に依存する。`check-ssot.py` の CS8 は「すぐに」を曖昧語に数えない(独立レビュー Codex が検出。重大度「低」)。
- 2026-08-19 **`.gitignore` が `.DS_Store` を無視していない**: `._*`(AppleDouble)は入っているが `.DS_Store` は入っていない(macOS から同期している経路で作られる。2026-08-20 時点で現物は0件)。誰かが `git add -A` すると仕様ドキュメントでないファイルが版管理に入る。機械検査には掛からない。次に `.gitignore` を触るタスクが1行足す。
- 2026-08-19 **`claude-dev stop --volumes` を名前より前に書くと、フラグが名前として解釈される**: `claude-dev stop --yes --volumes` を実行すると `--yes` を `<name>` と読み、「`--yes` は存在しません」と表示して**終了コード 0 で終わる**(実測)。`--yes` は `[A-Za-z0-9._-]` の範囲内なので `FR-env-01-18` は発火せず、存在しないコンテナとして `FR-env-01-8` の経路に入る — **仕様には違反していない**。だが `logout` / `reset` が `--yes` を受けるので利用者は `stop` にも付けがちで、そのとき**セッションは停止されないのに成功したように見える**。ヘルプは `claude-dev stop [NAME] [--volumes]` と位置を示しているが、誤りは表示されない。次に `stop` の引数解析を触るタスクが、先頭のフラグを名前として受理しない形にするか、未知のフラグを名前と読んだときに警告するかを決める。
- 2026-08-20 `docs/03-impl/index.md:47`・`:54`・`:56` の検証記録が、2026-08-20 の規約刷新で廃止された `check-changeset.py` を指したままである。**日付で固定された検証記録**なので書き換えると当時の事実でなくなる(当時その道具で確認したこと自体は本当である)。道具名に「(現在は廃止)」を添えるか記録をそのまま残すかを、次に `03-impl/index.md` を触るタスクが決める(02 側の現在形の記述 — `docs/02-design/system.md` の HTML コメント — は 2026-08-20 の構築記録 `fix-fr-env-07-13-owner-and-codex-sandbox-defaults` が削除した)。
- 2026-08-20 **構築記録 `fix-session-list-undercount` の突き合わせで2件の食い違い**(F3 実装整合フロー / 独立レビュー lens: claude が検出。`build-record.md` §2 により記録名を挙げてキューへ出す): (1) `docs/build-records/fix-session-list-undercount.md:73` の `BR-05` の根拠 `Makefile:263-271` は**同タスク自身の変更で動いた後の行を指していない** — `clean:` は `Makefile:283` で、削除対象の列挙と `read -p` の確認は `:284`-`:290` である(`:263`-`:271` は `status` レシピの問い合わせ失敗の分岐)。critical を上げた根拠の位置そのものが外れている。(2) 同記録の `## 影響範囲(closure)` に、コミット `25c40e6` が実際に編集した手書きの SSOT 文書3件 — `docs/02-design/relations.md`・`docs/03-impl/tests/e2e.md`・`docs/03-impl/tests/makefile.md` — が載っていない(うち e2e.md と makefile.md は同記録の進捗メモが編集を自認している)。closure は並行実行の非交差証明と verify の射程の入力なので、両方が外れる。記録は流れが消してよいものではないので、次に同記録へ触るタスク(昇格または `--repair`)が2件を直す。
- 2026-08-20 **`claude-dev list` / `make status` の列挙に固定名 `claude-dev-docker-proxy` を除く条件が無い**(F3 実装整合フロー / 独立レビュー lens: claude が検出)。`docs/02-design/contracts/cli-container.md:565`-`:566` は集合の定義に「名前が `fwd-` で始まるものと固定名 `claude-dev-docker-proxy` を除く」を含めるが、`03-impl/relations/MODULE-cli-list.md:29`-`:30` と `MODULE-makefile-status.md:26`-`:30` は `fwd-` の除外だけを書き、実装(`claude-dev:2212`-`:2213` / `Makefile:267` の `awk`)にも固定名の条件が無い。現在 proxy が一覧に出ないのは**管理ラベルを持たず別イメージ由来だからで、偶然による成立**である(proxy に管理ラベルを付けるか同じベースイメージにした瞬間に `FR-env-01-36` が落ちる)。今は誰の目にも見える変化が無いので残務に置く。次に同じ列挙を触るタスクが、固定名の除外を実装に入れるか、02 の集合の定義から落とすかを決める。
- 2026-08-20 `Makefile:295`-`:297`(`clean` の `ids=` の代入): 3回の `docker ps -a` の非ゼロが末尾の `awk` の終了状態で消えるため、Docker が答えないと削除対象0件として静かに `✅ 全リセット完了` を出す。`docs/02-design/contracts/cli-container.md` の同節は**表示側にだけ**警告行を求めており削除側の振る舞いを定めていないので、契約の裁定が要る(`make status` 側の同型は 2026-08-20 に修めた。経緯は `docs/histories/2026-08-20-fix-make-status-hides-docker-query-failure.md`)。
- 2026-08-20 **用語集の8語に「含む例」「含まない例」が両方とも空欄**(`docs/00-requests/terminology.md:28`-`:35` の `claude-dev` / `Claude コンテナ` / `Codex CLI` / `Codex サンドボックス` / `docker-proxy` / `forward プロキシ` / `DooD` / `VM モード`)。`.claude/directions/00-requests.md` は用語に例を求めており、`/verify-docs all` の A0 が毎回報告する。いずれも識別子に近い固有名で、例を埋めるには「何をこの語に含めないか」の線引きを決める必要がある(境界のある語 — 安全・破壊的操作・管理ラベル・セッション由来の資源など — は既に埋まっている)。次に用語集を触るタスクが同じ降下で埋める。**起点は原則8のゲートで降格した削除済み issue 071 の残件である**(2026-08-12 の同鍵の残務は「23 語のうち 17 語」と古い実測値を持っていたので、2026-08-20 の F2 がこの行へ統合して削除した)。
- 2026-08-20 `docs/03-impl/features.md` の「到達しない関数についての判断」の隣に `.claude/directions/callgraphs.md` §6 が求める「棄却した候補辺・確認済みの境界辺」節が無いため、`MODULE-entrypoint-claude` の callees 3件が `callgraph-check.py` の CG3 に毎回「中」で出る。3件とも実在することは確認済みで、`scripts/entrypoint-claude.sh:496`(`init-firewall.sh`)/ `:507`(`vm-up.sh`)/ `:545`(`dood-portsync.sh --loop`)がいずれも `/usr/local/bin/` の絶対パスで起動しており、shell 抽出器がソースへ解決できないだけである(2026-08-20 の F3 で行番号を再測。前の版の 476 / 487 / 522 は `2217c84` より前の値で、以後ずれていた)。**同じ節の不在が CG4 の「参考」12件の再提起も生んでいる**: `Makefile::help` の 11 件と `Makefile::setup → login` は、いずれも対象名が `@echo` の文字列の中にしか出てこない(`Makefile:52`-`:68` / `:82`。`setup` の前提条件は `Makefile:76` の `env network volumes build install` で `login` を含まない)ため**辺は実在せず棄却が正しい**が、棄却が残らないので毎回戻る。同節に確認済み3件と棄却12件を記録すれば再提起が止まる。
- 2026-08-20 **`doc-health.py --sweep` が、真で未解消の残務行を「対象が実在しない」として落とす**(`.claude/scripts/doc-health.py:486`)。`LEFTOVER_RE`(同 `:437`)の第2群が `(\S+)` であるため、日付の次が **バッククォートで囲んだパスに続けて空白なしで日本語が続く行**では、`` `docs/03-impl/features.md`「到達しない関数についての判断」の隣に `` の全体が1トークンとして取られ、`.strip("`")` が内側のバッククォートを外せないまま `docs/` 始まりのパスとして存在検査に掛かって失敗する。**2026-08-20 の F2 がこの型で1行を実際に落とした**(同日の履歴 `docs/histories/2026-08-20-doc-check-ssot-coverage-gap-and-false-completeness-claim.md` に本文が残る。落とされた行は閉じバッククォートの後に空白を入れて復帰させた)。**キットは CLAUDE.md §3 により凍結中で、`/kit-improve` の持ち物である。**直し方は第2群をパスとして使う前に「バッククォートで囲まれた先頭トークン」だけを取り出すこと。
- 2026-08-20 **`/verify-tests` の qa scope を「適用外(UI 無し)」で記録した**(F4 試験フロー)。根拠: `docs/02-design/system.md:447`-`:464`(DSN-ui-01「UI はホスト CLI に限り、Web GUI を持たない」。noVNC は利用者が開発中の Web アプリを見る窓であり本システム自身の UI ではない)。**`.claude/scripts/flow-config.json` の `f4_scopes` から `qa` を外す作業はキット凍結中(CLAUDE.md §3)につき未実施** — `/kit-improve` がまとめて持つこと。
- 2026-08-20 **`make status` / `make clean` の列挙規則に対応する 01 の条項が無い**: `docs/02-design/contracts/cli-container.md:565` は「表示(`claude-dev list` / `make status`)」の集合の定義として `FR-env-01-35`・`FR-env-01-36` を根拠に引くが、両条項の EARS の主語は `claude-dev list` だけで `make status` を含まない(`docs/01-requirements/functional.md:81`-`:82`)。`docs/02-design/system.md:225`-`:226` の担当も `MOD-cli-list` のみである。構築記録 `fix-session-list-undercount` は `make status` の0件表示と `make clean` の削除範囲を外部挙動の変化として自ら申告しており、その振る舞いを持つ条項が 01 に無い。条項を足すか契約の主語を `claude-dev list` へ狭めるかを、次に `FR-env-01` か同契約を触るタスクが決める(F2 の後追い独立レビューが検出。重大度「中」)。
- 2026-08-20 **`docs/02-design/contracts/cli-container.md:598` が委ねる「エラーケース」の行が同節に無い**: 同行は「問い合わせが失敗したときは 0 件と同一視しない(「エラーケース」)」と書くが、`## エラーケース`(`:201`-`:249`)に在るのは stop のセッション由来資源・logout の削除対象集合・遊休判定の3行だけで、`claude-dev list` / `make status` の列挙そのものが失敗したときを扱う行が無い。読者が倒し方を辿れない。次に同契約を触るタスクが行を足すか委ね先を変える(F2 の後追い独立レビューが検出。重大度「中」)。
- 2026-08-20 **`docs/issues/094` の「同型の全件」表の `path:line` が現物と合わない**(F2 文書整合フロー / 独立レビュー lens: claude が検出): #1 は `00-requests/decisions/dist.md:85` / `01-requirements/functional.md:343` / `02-design/architecture.md:236` を指すが、実物は `D0-dist-04` 項6 が同 `:65` 以降、`FR-env-12-5` が同 `:324`、`DSN-dist-02` が同 `:260` である(#3〜#5 も同型にずれている)。`pendings.md` の 2026-08-11 の行(コード引用の行番号のずれ)は **03-impl → コードの引用**だけを対象にしており、issue 本文から SSOT への引用は覆っていない。読者が根拠を辿れない。次に issue 094 を扱うタスクが、行番号を取り直すか安定なアンカー(見出しと ID)へ替える。
- 2026-08-20 **24,000 バイトを超える仕様ドキュメントが 13 件在るのに、分割提案の記録がどこにも無い**(F2 文書整合フロー / 独立レビュー lens: claude が検出)。CLAUDE.md §7 は超過を分割提案の義務(指針)としている。(生成物 `03-impl/callgraphs/shell.md` を除く。最大は `02-design/contracts/cli-container.md` の 89,575 バイト)。次点は `03-impl/tests/e2e.md`(83,738)と `01-requirements/functional.md`(73,216)。分割は `id` の一意性・`source` の連鎖・合格証の版をすべて動かすので、次に該当ファイルを構造から触るタスクが提案の形で判断する。
