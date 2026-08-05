---
id: 2026-08-04-fix-destructive-scope
date: 2026-08-04
task: task-fix-destructive-scope
origin_layer: 00
issue: docs/issues/020-modify-cli-destructive-commands-have-no-mutual-exclusion.md
summary: 破壊的操作(stop / logout / reset)が他プロジェクトの資源を巻き込むのを止めた。管理ラベル・遊休判定のイメージ非依存化・compose 名の一意化・2段の排他ロック・削除失敗の非0終了で issue 020/024/025/029/045 を閉じた
---

# 2026-08-04 破壊的操作を「自分が作った資源」に限る

## 変更理由

**起点層は 00。** 破壊的操作の対象をどう定めるかは横断的な方針であり、5件の issue が同じ根を
持っていた。

| issue | 事象 |
|---|---|
| `020` | CLI に排他機構が1つも無く、`start` と `logout`/`reset` が同時に走ると**認証が空のまま起動する**(利用者は気づけない) |
| `024` | `stop` の compose 名の正規化が非可逆で、**別ディレクトリの compose コンテナとネットワークを巻き込んで削除しうる** |
| `025` | `logout` / `reset` が削除の失敗を握りつぶして「削除しました」と表示し、**プロジェクト配下の認証コピーを消さない** |
| `029` | `logout` が**確認なしでホスト上の全 claude-dev コンテナを強制削除**する(他プロジェクトの作業中セッションが予告なく落ちる) |
| `045` | `stop` の遊休判定が `--filter ancestor=<現在のイメージ>` なので**古いイメージで稼働中のコンテナを数え落とし**、共有 docker-proxy を消す(`FR-env-01` 受入基準9 違反) |

`D0-env-08`(破壊的操作の対象は「自分が作った資源」に限る)を 00 に起こし、
`D0-env-09`(排他の実装手段とロックの置き場所)と `D0-env-10`(管理ラベルの名前と値)を
委任として添えて 01 → 02 → 03 へ降ろした。あわせて既存の `D0-env-05` 項1・項2 を上書きした
(compose 名の作り方・削除対象のラベル値・「docker-proxy は削除しない」の3点が新しい決定と
両立しないため)。

## 変更内容の要約

- **所有権を「起動時に付けた管理ラベル」で表す**(`DSN-env-01`)。`start` が Claude コンテナに
  `claude-dev.managed=1` / `claude-dev.role=claude` / `claude-dev.project-dir=<絶対パス>` を付ける。
  **ラベルを付けるのは Claude コンテナだけ**で、docker-proxy と `fwd-*` は固定名・固定接頭辞で
  識別する(固定名の資源にラベルを足すと、既存資源がラベルを持たないという移行問題を必要も無く
  作り込むことになるため)。
- **集合として列挙する削除は管理ラベルを持つものに限る**。ラベルを持たない Claude コンテナは
  削除せず、名前を表示して残す。`stop <name>` は利用者が名前で指した1件なのでラベルの有無を
  問わず削除する(規則B)。
- **共有 docker-proxy / `claude-dev-net` の遊休判定を `claude-dev-net` への接続で行う**。
  イメージにもラベルにも依存させない(どちらも「数え落とす」方向に外れる)。
  問い合わせに失敗したら遊休でないと判定する(安全側)。**`reset` にも同じ判定を掛ける**。
- **compose プロジェクト名を `<正規化名>-<起動ディレクトリ絶対パスの SHA-256 先頭6桁>` に
  一意化する**(`DSN-env-03`)。`stop` はハッシュ源を `claude-dev.project-dir` ラベルから
  **本体削除の前に**読む。旧い名前の compose 資源は削除せず手動手順を案内する。
- **6コマンド(`start` / `stop` / `logout` / `reset` / `login` / `login-codex`)に2段の排他ロックを
  入れる**(`DSN-env-02`)。プロジェクト単位(キー=コンテナ名)と共有資源単位(キー=`shared`)。
  **待たない**。実体は「向き先に `<PID> <操作名>` を入れたシンボリックリンク」で、生成と所有者の
  記録が1回の原子的操作で成立する。
- **`logout` / `reset` に確認プロンプトと `--yes` を入れ、非 TTY かつ `--yes` 無しは何も削除せず
  終了コード 1** で終わる(`reset` の従来の「キャンセル扱いで 0」を改めた)。
- **削除の成否を1件ごとに記録し、1件でも失敗したら消えなかった資源を列挙して終了コード 1**。
  成功の文言は出さない。共有ボリュームの成否は「削除後の列挙結果」で判定する。
- **`logout` がカレントディレクトリの認証3ファイルを削除する**(ディレクトリと `settings.json` は
  残す)。他のディレクトリのコピーには触れない(場所を記録していないため。この限界を表示する)。
- **削除中の `INT` / `TERM` は進行中の1件を終えてから中断**し、削除済みと未削除を列挙して
  **終了コード 130** で終わる。

## 更新したドキュメント

| ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|
| docs/00-requests/decisions/env.md | 1.0.0 → **1.1.1** | `D0-env-08`(対象の限定)/ `D0-env-09`(排他の手段は委任)/ `D0-env-10`(ラベルの名前と値は委任)を新設し、`D0-env-05` 項1・項2 を上書き |
| docs/01-requirements/functional.md | 1.4.0 → 1.5.0 | `FR-env-01` 受入基準9 を `stop`/`logout`/`reset` の3コマンドへ広げ(判定はラベルにもイメージにも依存しない)、14〜21 を追加。`FR-env-03` に 14〜23 を追加(確認・非TTY中止・ラベル限定・削除失敗の非0終了・認証コピーの削除・中断時の 130) |
| docs/02-design/contracts/cli-container.md | 1.3.0 → **1.4.1** | `## 破壊的操作の対象の識別` を新設(識別手段・管理ラベル・削除の3規則・残したものの列挙・ロックキーの文字集合・遊休判定・compose 名の一意化・排他のキー表)。`DSN-env-01`/`-02`/`-03` を追加。エラーケースを 13 → 25 行 |
| docs/02-design/logging.md | 1.1.0 → **1.2.1** | `## 主要イベントのログ仕様` に破壊的操作の出力を12行追加し、起動ディレクトリの絶対パスを出す根拠と「削除に失敗した資源がある状態で成功の文言を出してはならない」共通制約を明記 |
| docs/02-design/relations.md | 1.0.0 → **1.3.0** | `PLAN-cli-common-lock` を新設(呼び出し元=6コマンド)。`## 一覧` が 64 行・全83機能に |
| docs/02-design/system.md | 2.0.0 → **2.2.0** | `#### SCR-01 cli-commands` に `--yes` と受理文字集合。`## モジュール分割定義` の `MOD-cli-common` の責務に排他ロック、`MOD-cli-reset` の依存を `MOD-cli-common` へ、機能数 82 → 83。`### 結合テスト対象` の `CTR-cli-container` を起動側と破壊的操作側の2行に分割。`### E2Eシナリオ一覧` に破壊的操作の検証 |
| docs/03-impl/features.md | (版なし) | `MODULE-cli-common-lock` を1行追加(83機能)。統合の件数 11 → 12、昇格の判断表に1行 |
| docs/03-impl/relations/MODULE-cli-common-lock.md | **新規 1.0.0** | 排他ロックの取得・解放・残骸の引き継ぎ。ファンイン6の共有基盤 |
| docs/03-impl/relations/MODULE-cli-start.md | (層で認証) | 管理ラベルの付与・2段ロック・compose 名の一意化。戻り値・異常系・既知の制限・副作用の順序・並行性を実装から確定 |
| docs/03-impl/relations/MODULE-cli-stop.md | (層で認証) | 遊休判定の置き換え・ラベルの先読み・旧名 compose の保護・名前の検証。同上 |
| docs/03-impl/relations/MODULE-cli-logout.md | (層で認証) | 確認・対象限定・遊休判定・削除失敗の列挙・認証コピーの削除・中断。破壊の範囲と順序・並行性も書き替え |
| docs/03-impl/relations/MODULE-cli-reset.md | (層で認証) | 同上 + 共有資源の遊休判定。`callees` に `container-exists` / `image-exists` を追加 |
| docs/03-impl/relations/MODULE-cli-login.md / -login-codex.md | (層で認証) | 対話認証の全区間で共有資源単位のロックを保持する |
| docs/03-impl/relations/MODULE-cli-common-container-exists.md / -image-exists.md | (層で認証) | `callers` に `MODULE-cli-reset` を追加(コードに合わせた対称性の回復) |
| docs/03-impl/contracts/cli-container.md | 1.3.0 → **1.5.0** | 実装上の事実を `path:line` ごと取り直し、管理ラベル・ロックの実体と区間・残骸回収・解放・遊休判定・削除結果の記録・共有ボリュームの消去判定の7行を追加 |
| docs/03-impl/tests/cli-common.md | 1.0.0 → 1.1.0 | `FR-env-01` 受入基準16・17 と `MODULE-cli-common-lock` の行 |
| docs/03-impl/tests/cli-logout.md | 1.0.0 → **1.2.0** | `FR-env-03` 受入基準14〜23 の行 |
| docs/03-impl/tests/cli-start.md | 1.1.0 → 1.2.0 | `FR-env-01` 受入基準14 の行 |
| docs/03-impl/tests/cli-stop.md | 1.0.0 → **1.2.0** | `FR-env-01` 受入基準15・18・19・20 の行 |
| docs/03-impl/tests/e2e.md | 1.1.0 → 1.2.0 | `E2E-01` に手順8(13項目)を追加。手順7-7 の `issue 045` 応急処置を修正後の期待値へ |
| docs/03-impl/index.md | 1.8.0 → **1.11.0** | 機能間連携仕様書の本数 82 → 83、`check-relations.py` の結果 83/83、起票済みの実装欠陥 16 → 15 件(解消5件を外し `046`/`047`/`051` を追加。認証時に `053` を含めて機械照合) |
<!-- 版は「反映(§3)で上げた値 → /doc-check ssot の2回の実行が指摘の修正で
     さらに上げた最終値」である。太字が最終値。 -->


## 実装したもの

| 対象 | 内容 | コミット |
|---|---|---|
| MODULE-cli-common-lock | `acquire_lock` / `release_lock` を両版へ新設。`ln -s` の原子性・`mv` + 中身の検証による残骸回収・`trap` による解放 | `edeead2` / `1232623` |
| MODULE-cli-start | 管理ラベル3つ・2段ロック・compose 名の一意化・名前衝突時に起動元ディレクトリを事実として表示 | `552adad` |
| MODULE-cli-stop | 遊休判定の置き換え・ラベルの先読み・旧名 compose の保護・`<name>` の文字検証 | `8a2c7cf` |
| MODULE-cli-logout | 確認 / `--yes` / 対象限定 / 遊休判定 / 削除失敗の列挙 / 認証3ファイルの削除 / 中断時 130 | `09b2faa` |
| MODULE-cli-reset | `--yes` / 非TTY中止 / 対象限定 / 共有資源の遊休判定 / 削除失敗の列挙 / 中断時 130 | `dbd4c9a` |
| MODULE-cli-login / -login-codex | 対話認証の全区間で `shared` を保持 | `48ff60e` |
| 独立レンズの指摘の反映 | 高1件(残骸の引き取りが生きたロックを奪う)・中5件・低4件を修正 | `1232623` |

## 機能間連携仕様書の変化

| 種別 | ID | 内容 |
|---|---|---|
| 追加 | MODULE-cli-common-lock | 排他ロックの取得・解放。呼び出し元は6コマンド |
| 変更 | MODULE-cli-start | `callees` に `MODULE-cli-common-lock` を追加。`design` に `DSN-env-01` / `-02` |
| 変更 | MODULE-cli-stop | `callees` に `MODULE-cli-common-lock`、`contracts` に `CTR-cli-container`、`design` に `DSN-env-01` / `-02` |
| 変更 | MODULE-cli-logout | 同上 |
| 変更 | MODULE-cli-reset | `callees` に `MODULE-cli-common-lock` / `-container-exists` / `-image-exists`、`contracts` に `CTR-cli-container` |
| 変更 | MODULE-cli-login / -login-codex | `callees` に `MODULE-cli-common-lock`、`design` に `DSN-env-02` |
| 変更 | MODULE-cli-common-container-exists / -image-exists | `callers` に `MODULE-cli-reset` |

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 解消した issue | docs/issues/020(削除) | 6コマンドに2段の排他ロックを入れた。事象表の4行すべてが再現しない |
| 解消した issue | docs/issues/024(削除) | compose プロジェクト名を絶対パスのハッシュで一意化した。残存リスクは P-005 |
| 解消した issue | docs/issues/025(削除) | 削除の成否を1件ごとに記録し、失敗を列挙して非0で終わる。認証コピーも消す |
| 解消した issue | docs/issues/029(削除) | 確認プロンプトと管理ラベルによる限定を入れた |
| 解消した issue | docs/issues/045(削除) | 遊休判定を `claude-dev-net` への接続へ置き換えた |
| 新規 issue | docs/issues/046 | `list` / `make status` / `make clean` が同じ `--filter ancestor` でコンテナを数え落とす |
| 新規 issue | docs/issues/047 | `reset` が `claude-dev-vm-*` ボリュームを消さない |
| 新規 issue | docs/issues/048 | 02 の「共有基盤どうしは呼び合わない」が同じ文書の一覧表の2本の辺と矛盾 |
| 新規 issue | docs/issues/049 | `AC-02` が例外なしで「`start` でポート非公開」を要求するが、既定は noVNC ポートを公開する |
| 新規 issue | docs/issues/050 | 解釈できない Docker API ボディを中継してよいという `FR-env-07` 受入基準8 が `D0-sec-05` と両立しない |
| 新規 issue | docs/issues/051 | CLI の出力に生の Docker ID が混じる(本変更より前から存在) |
| 棚上げ | docs/pendings.md P-005 | compose 一意化名のハッシュ衝突(先頭6桁 = 24 ビット)を検出せず受け入れる |
| 気づき | docs/feedbacks/018 | `mv` の原子性は「パス」の話であって「中身」の話ではない |
| 気づき | docs/feedbacks/019 | bash で「書いたのに効かない」3つの罠(`local` の展開順 / `&` の子は SIGINT を無視 / Ctrl-C は子にも直接届く) |

## 人間が判断した論点(フェーズ3・4)

| # | 論点 | 回答 | 帰結 |
|---|---|---|---|
| 3-1 | 遊休判定の集合に利用者の compose コンテナが入り、docker-proxy と `claude-dev-net` がほぼ回収されなくなる(本ホストで実測40件) | **A. 現状のまま** | 契約の字面どおり。「過剰に数える=消さない側」なので `FR-env-01` 受入基準9 は破らない。`MODULE-cli-stop` / `-logout` / `-reset` の「既知の制限」に記録した |
| 3-2 | 独立レンズ(Codex)が2回とも結論を出さずに終了した。サブエージェントで代替するか | **B. 代替する** | 新しい文脈の Claude Code サブエージェントに同一条件で差分監査を依頼した。**レンズはサブエージェントであり Codex ではない**(CLAUDE.md 不変則7)。指摘13件・誤検知0件で、うち**重大度「高」1件**(残骸の引き取りが生きたロックを奪う)を含む10件を修正した |
| 4-1 | `stop` の docker-proxy 削除が失敗したとき非0で終了してよいか(文書を実態へ揃えたが、元の設計意図は「握って続行」だった) | **A. 現状のまま** | コードは変更しない。docker-proxy の削除は `stop` の最後の手順なので、ここで止まっても中途半端な片付けが残らない。失敗が利用者に見える方が `D0-env-08` 項5 の趣旨に沿う。**この挙動は本変更より前から同じ**である |
| 4-2 | `docs/00-requests/terminology.md` に合格証が無いため削除ゲートが拒否する。どう閉じるか | **A. `--abort` で削除する(人間の例外承認)** | `terminology.md` は本タスクが**触らない**(closure の「変更なし」行)。合格証の発行は3本目 `task-spec-measurability` の担当と `docs/issues/044` で人間が裁定済みで、発行には 01/02 への下降が前提である。**ゲートが「変更なし」行にまで合格証を要求するのはキット側の欠陥**として `.claude/improvements/KIT-close-task-demands-certificates-for-unchanged-closure-rows.md` に起票済み。**したがって条件(b) の不合格1件は人間の例外承認で通した**(残る3条件 (a)(c)(d) はすべて通過している)。**実行したコマンドは `python3 .claude/scripts/close-task.py task-fix-destructive-scope --abort` で、「不合格 1 件のまま中断削除する」と警告が出た状態で削除した**。`--abort` の本来の意味は「中断」だが、ゲートを迂回する手段が他に無いためこれを用いた(この点も上記のキット改善案件に含む)。**引き継ぐべき残件は `terminology.md` の合格証1件だけで、3本目 `task-spec-measurability` が発行する** |

## 認証

- **`/doc-check ssot task-fix-destructive-scope` を2回実行した。** 1回目はセッション上限で中断し、
  2回目は**既存の合格証を根拠にせず最初から検証し直した**。
  **その判断は当たりで、中断が残した自己矛盾が実在した**: `MODULE-cli-stop` が
  「docker-proxy の削除失敗を握る/握らない」で食い違っていた(1回目が戻り値欄だけ直して
  判断3・順序の段落・異常系の3箇所を取り残していた)。
- **判定: PASS(47文書)。** 上流の版上げで失効した下流37文書も同一実行内で再認証した。
- **独立レンズ: Codex 5本中3本が完走、2本がタイムアウト。**
  **03層の A3 / E / C12 だけはレンズが立たず、Claude 単独の検証である**(正直な限界として記録する)。
- 追加で起票した issue: `053`(`logout` が列挙できない共有ボリュームを「空」と判定する)/
  `054`(SSOT が削除済み issue のパスを参照し続ける。10 ID・20ファイル以上の運用問題)/
  `055`(`FR-env-03` 受入基準17 が停止中のラベル無しコンテナの表示まで求めるが、02 は
  「列挙できない」を意図した限界としている)。**いずれも本タスクの範囲外**。

## 検証

- **`E2E-01` 手順8 の13項目すべてを実行して合格**(Linux)。7項目を実スクリプト、6項目を
  定数名だけを差し替えた同一コードのサンドボックスで実行した(本物の `logout` / `reset` は
  利用者の実際の認証を削除し、動作中のコンテナを落とすため無人で実行しない)。
  **macOS は未実施**(macOS ホストが無い)。新規・変更コードの Linux 版と macOS 版が
  文字列として完全一致することは機械照合した(差分は macOS 固有の `stop_ssh_bridge` 2行のみ)。
- **`issue 045` の実測**: 本ホストで旧方式(`--filter ancestor`)が 0 件、新方式が 40 件。
  旧コードなら「Claude コンテナなし」と判定して共有 docker-proxy を削除する状態だった。
- **`issue 024` の実測**: `/tmp/e2e-y/My.App` と `/tmp/e2e-y2/my-app` の compose 名が
  `my-app-2efe44` と `my-app-250f4b` に分かれ、一方の `stop` で他方の compose コンテナが残った。
- 独立レンズ(**サブエージェント**。Codex は5回連続で結論を出さずに終了したため、
  人間の承認を得て代替した)が13件を指摘し、誤検知は0件だった。
