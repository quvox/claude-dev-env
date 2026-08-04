---
id: task-fix-destructive-scope
phase: 反映
origin_layer: 00
issue: docs/issues/020-modify-cli-destructive-commands-have-no-mutual-exclusion.md
date: 2026-08-04
updated: 2026-08-04
source:
  - docs/00-requests/decisions/env.md
  - docs/01-requirements/functional.md
  - docs/02-design/contracts/cli-container.md
  - docs/02-design/relations.md
  - docs/02-design/system.md
  - docs/02-design/logging.md
  - docs/03-impl/features.md
  - docs/03-impl/relations/MODULE-cli-common-lock.md
  - docs/03-impl/relations/MODULE-cli-stop.md
  - docs/03-impl/relations/MODULE-cli-logout.md
  - docs/03-impl/relations/MODULE-cli-reset.md
  - docs/03-impl/relations/MODULE-cli-start.md
  - docs/03-impl/relations/MODULE-cli-login.md
  - docs/03-impl/relations/MODULE-cli-login-codex.md
  - docs/03-impl/contracts/cli-container.md
  - docs/03-impl/tests/cli-stop.md
  - docs/03-impl/tests/cli-logout.md
  - docs/03-impl/tests/cli-reset.md
  - docs/03-impl/tests/cli-start.md
  - docs/03-impl/tests/cli-common.md
  - docs/03-impl/tests/e2e.md
  - docs/03-impl/index.md
summary: 破壊的操作(stop / logout / reset)が他プロジェクトの資源を巻き込むのを止める(issue 020/024/025/029/045)
---

<!-- タスクの背骨。フェーズ1で作られフェーズ4で削除されるまで、このファイルだけで
     どのフェーズからでも再開できること(/clear を挟んでも)。
     ・仕様ドキュメントではない(version / verified を持たない)
     ・未決点はここに置く。仕様ドキュメントには絶対に書かない
     ・削除は /task-close の機械ゲート経由(close-task.py)。rm 禁止 -->

# task-fix-destructive-scope 破壊的操作を「自分が作った資源」に限る

> 解決済みの経緯: memo-1.md(フェーズ1の決定シートと回答、および論点1=A の前提の誤り)/ memo-2.md(フェーズ2 で解消した未決点28件と、その反映先。`/doc-check` の決定シート5件を含む)/ memo-3.md(フェーズ2 前半の進捗メモ4件: フェーズ1宣言・00→03 の下降・初回の独立監査・`/doc-check` 1回目)/ memo-4.md(フェーズ2 の進捗メモ3件: `/doc-check` 1回目の不合格・決定シート5件の反映・セッション上限での中断)

## 実行順(★重要)

**3本連続タスクの1本目。** `task-relations-code-sync`(2本目)と `task-spec-measurability`(3本目)は
影響範囲が重なるため**並行実行しない**(CLAUDE.md フェーズモデル)。重なりの実測:

| 組 | 重なるファイル |
|---|---|
| 本タスク ∩ 2本目 | `03-impl/contracts/cli-container.md` / `03-impl/index.md` / `MODULE-cli-start` / `-stop` / `-reset` / `-logout` |
| 本タスク ∩ 3本目 | `01-requirements/functional.md` / `03-impl/index.md` |

**本タスクが1本目である理由**: コードを変えるので、先に2本目(relations をコードへ追随)を
回すと同じファイルを二度直すことになる。かつ `issue 029`(`logout` が確認なしで他プロジェクトの
作業中セッションを落とす)は利用者に実害があり、先に止める価値が高い。

**フェーズ2 で影響範囲が増えたので、重なりも増えた**(3本目の memo.md の closure と突き合わせて実測):

| 組 | フェーズ2 で増えた重なり |
|---|---|
| 本タスク ∩ 2本目 | `03-impl/features.md` / `03-impl/relations/MODULE-cli-common-lock.md`(新設)/ `MODULE-cli-login` / `-login-codex` |
| 本タスク ∩ 3本目 | **`02-design/system.md`**(3本目は `MOD-firewall` の記述と測定不能語で触る。本タスクは `#### SCR-01 cli-commands` だけを触るので**節は重ならない**が、同じファイルなので合格証は再取得になる)/ **`02-design/relations.md`**(3本目は `PLAN-vm-mode-healthd` の概要の語。本タスクは `## 一覧` の cli 行。**同じ節を触る**ので、先に閉じた側の結果へもう一方を貼り直す必要がある)/ `03-impl/tests/e2e.md` |

## 目的

**「破壊的操作は自分が作った資源にだけ効く」を実装と仕様の両方で成立させる。** 現在は対象の
絞り込みが甘く、5件の issue が同じ根を持つ。

| issue | 事象 | severity |
|---|---|---|
| `020` | CLI に排他機構(ロック)が1つも無い。`start` と `logout`/`reset` が同時に走ると**認証が空のまま起動する**(利用者は気づけない) | 中 |
| `024` | `stop` の compose 名の正規化が非可逆で、**別ディレクトリの compose コンテナとネットワークを巻き込んで削除しうる** | 中 |
| `025` | `logout` / `reset` が削除の失敗を握りつぶして「削除しました」と表示し、**プロジェクト配下の認証コピーを消さない** | 中 |
| `029` | `logout` が**確認なしでホスト上の全 claude-dev コンテナを強制削除**する(他プロジェクトの作業中セッションが予告なく落ちる) | 中 |
| `045` | `stop` の遊休判定が `--filter ancestor=<現在のイメージ>` なので**古いイメージで稼働中のコンテナを数え落とし**、共有 docker-proxy を消す(`FR-env-01` 受入基準9 違反) | 中 |

起点層は **00**: 「破壊的操作の対象をどう定めるか」は横断的な方針であり、`D0-env-08` として
起こしてから 01 → 02 → 03 へ降ろす(`task-fix-start-cleanup` の決定シート論点5 で
「まとめて直すタスクを立てるならそこで起こす」と裁定済み)。

**フェーズ2 の結論**: **5件すべてを閉じる形が書けた**(未決点 U-1〜U-3 は 2026-08-04 に人間が
すべて推奨案=A で裁定し、変更指示へ反映済み)。**人間判断の未決点はゼロ**なので、
`/doc-check` が PASS すれば `/implement` を無人で開始できる(原則7)。

## やること・やらないこと

| 種別 | 内容 |
|---|---|
| やること | 対象の絞り込み方式を決めて実装する(論点1=A: 管理ラベル + **compose 名の一意化**=U-1)/ `D0-env-08` を 00 に起こす(論点2=A)/ `logout` に確認を入れる(論点3=A)/ 削除失敗を検出して非0で返す(論点4=A)/ **`logout` がプロジェクト配下の認証3ファイルを消す**(U-2)/ `stop` の遊休判定を直す(`045`)/ 排他を**6コマンド**に入れる(論点5=A + U-3 で `login` / `login-codex` を追加)/ 該当 relations・契約・tests・index を実態へ / 実機確認 |
| やらないこと | **`docs/issues/028`(命名の一意化)**。利用者に見える名前と 11 呼び出し元が動くので独立タスク(論点6=A)/ **`038` / `032` の relations 乖離**(2本目)/ 測定不能語と NFR の測定可能性(3本目)/ **`docs/issues/046`(`list` / `make status` / `make clean` の同じ数え落とし)**。フェーズ2 で起票した。対象コマンドが違うので本タスクでは直さない / **`logout` の削除対象を `fwd-*` へ広げること**(現行の対象範囲を広げない) |

## 影響範囲(closure)

<!-- close-task.py はこの表から SSOT パスを抽出して合格証を検査する。
     frontmatter の source: と一致させること。 -->

| 層 | SSOT のパス | 変更指示のパス | 変更の種類 |
|---|---|---|---|
| 00 | docs/00-requests/decisions/env.md | new-features/00-requests/decisions/env.md | replace(**起点**。`D0-env-08`=決定 / `D0-env-09`=委任(ロックの手段) / `D0-env-10`=委任(ラベルの名前と値)を新設。**あわせて既存の `D0-env-05` 項1・項2 を上書き**する — compose 名の作り方・削除対象のラベル値・「docker-proxy は削除しない」の3点が新しい決定と両立しないため(U-21)) |
| 00 | (上の行に統合。**`D0-env-05` の上書きは決定シート #2 = U-21 で人間が回答済み**(2026-08-04、案A)。**別ファイルにはしない** — 同じ `target` に2つの変更指示を作ってはならない(`change-set.md` §2)ので、上の `new-features/00-requests/decisions/env.md` の `sections:` に `## D0-env-05 …` を含める形で反映済み) | — | — |
| 00 | docs/00-requests/request.md | - | 変更なし(理由: 目的・スコープは不変。「やらないこと」5項目と衝突しない) |
| 00 | docs/00-requests/acceptances.md | - | 変更なし(理由: `AC-01`〜`AC-06` の観点は変わらない。`AC-06` を実読して `logout` に言及が無いことを確認したので確認プロンプトの追加と衝突しない。**3本目のタスクが `AC-02` を触る**) |
| 00 | docs/00-requests/terminology.md | - | 変更なし(理由: 「破壊的操作」「管理ラベル」の定義は `D0-env-08` の本文に閉じた。用語集への行追加は**3本目 `task-spec-measurability` へ送る**(申し送り事項))。**★2026-08-04 `/doc-check`(3回目)の警告: このファイルは `verified` を持たない(1.1.0 = 未検証)。`close-task.py` は本表から抽出した全パスの合格証を検査する fail-closed ゲートなので、このままだと条件 (b) で `/task-close` が拒否される**(実測済み。closure 18 件中このファイルだけが NG)。**変更なしのファイルを表に載せていることが原因であり、ゲートを避けるために行を消すのは「合格証の範囲を黙って狭める」ことになるのでしない**(`.claude/directions/task-memo.md` §1 の警告)。**決定シート #5 で人間に諮る** |
| 01 | docs/01-requirements/functional.md | new-features/01-requirements/functional.md | replace(`FR-env-01` の受入基準9 を強化 + **14〜20** を追加 / `FR-env-03` に **14〜22** を追加) |
| 01 | docs/01-requirements/non-functional.md | - | **変更なし(下降中に判定した)**。理由: `NFR-sec-02` は「レビュー前コードの**外向き通信**が制御されていること」であり、認証情報の残存を測る要件ではない(フェーズ1 の closure の注記は誤読だった)。認証削除の観測可能な振る舞いは `FR-env-03` 受入基準18 に置いた。`NFR-scale-01` は既存の文言のままで本変更と両立する(ロックをプロジェクト単位に分けたのはこの要件を守るため) |
| 02 | docs/02-design/contracts/cli-container.md | new-features/02-design/contracts/cli-container.md | replace(**識別方法の正**。`COMPOSE_PROJECT_NAME` の一意化 / 管理ラベル / 3つの削除規則 / 残したものの列挙 / ロックキーの文字集合 / 遊休判定 / compose 資源の識別 / 排他のロックキー(6コマンド)/ `DSN-env-01`〜`DSN-env-03`) |
| 02 | docs/02-design/relations.md | new-features/02-design/relations.md | replace(**★フェーズ2 で追加**。`PLAN-cli-common-lock` を新設(呼び出し元=6コマンド)し、`PLAN-cli-stop` / `-logout` / `-reset` の契約欄に `CTR-cli-container` を入れ、`PLAN-cli-login` / `-login-codex` に lock を足す) |
| 02 | docs/02-design/system.md | new-features/02-design/system.md | replace(**★フェーズ2 で追加。独立レンズが検出**。`#### SCR-01 cli-commands` の公開フラグ一覧に `--yes` を追加し、対象セッション名の受理文字集合(**`stop` 限定**)と破壊的操作の状態を書く。**★`/doc-check` が2見出しを追加**: `## モジュール分割定義`(`MOD-cli-common` の責務に排他ロックを追記 / `MOD-cli-reset` の依存を `—`→`MOD-cli-common` / 機能数 82→83。機能数 11→12 で `DSN-mod-06` の上限15 は超えない)と `### E2Eシナリオ一覧`(E2E-01 のシナリオ欄に破壊的操作の検証を追記)。**テスト戦略 `DSN-test-01` は変更なし**) |
| 02 | docs/02-design/logging.md | new-features/02-design/logging.md | replace(**★2026-08-04 `/doc-check`(3回目)が追加**。`## 主要イベントのログ仕様` に破壊的操作の新しい利用者向け出力を **11 行**追加(排他で取れない / 残骸の引き継ぎ / 削除対象の確認 / ラベル無しで残したもの / 共有資源を残した理由 / 削除できなかった資源 / 削除した認証コピーのパス / 中断時の部分削除 / 旧い名前の compose 資源 / 受理できない名前)+ 「成功の文言を出してよい条件」の共通制約。**前例**: `FR-env-01` 受入基準12 が同じ粒度で既にこの表に載っている。**この表が無いと `MODULE-cli-start` 判断8 の「表示内容の要件は `02-design/logging.md` が定める」が指す先に定義が存在しない**) |
| 03 | docs/03-impl/features.md | new-features/03-impl/features.md | replace(**★フェーズ2 で追加**。`MODULE-cli-common-lock` を1行追加 + 統合の件数 11→12 + 昇格の判断表に1行) |
| 03 | docs/03-impl/relations/MODULE-cli-common-lock.md | new-features/03-impl/relations/MODULE-cli-common-lock.md | **add**(★フェーズ2 で追加。ファンイン6の共有基盤) |
| 03 | docs/03-impl/relations/MODULE-cli-stop.md | new-features/03-impl/relations/MODULE-cli-stop.md | replace(目的 / 処理の流れ / 連携先 / 実装上の判断) |
| 03 | docs/03-impl/relations/MODULE-cli-logout.md | new-features/03-impl/relations/MODULE-cli-logout.md | replace(処理の流れ / 呼び出され方 / 連携先 / 実装上の判断) |
| 03 | docs/03-impl/relations/MODULE-cli-reset.md | new-features/03-impl/relations/MODULE-cli-reset.md | replace(同上) |
| 03 | docs/03-impl/relations/MODULE-cli-start.md | new-features/03-impl/relations/MODULE-cli-start.md | replace(処理の流れ / 連携先 / 実装上の判断。ラベル付与側 + 排他 + compose 名の一意化) |
| 03 | docs/03-impl/relations/MODULE-cli-login.md | new-features/03-impl/relations/MODULE-cli-login.md | replace(**★U-3=A で追加**。共有資源単位のロックを対話認証の全区間で保持する) |
| 03 | docs/03-impl/relations/MODULE-cli-login-codex.md | new-features/03-impl/relations/MODULE-cli-login-codex.md | replace(**★U-3=A で追加**。同上。`login` と同じキー `shared` を使う) |
| 03 | docs/03-impl/contracts/cli-container.md | - | **変更指示なし**(理由: この文書の `## 実装上の事実` は `path:line` で埋まった**コードの鏡**であり、実装前に書くと存在しない行番号を書くことになる。`/task-close` §2 がコードから再生成する。フェーズ2 の時点で 02 とこの文書に差が出るのは正しい状態=03 は現状のコードを映す) |
| 03 | docs/03-impl/tests/cli-stop.md | new-features/03-impl/tests/cli-stop.md | replace(`FR-env-01` 受入基準 15・18・19・20 の行) |
| 03 | docs/03-impl/tests/cli-logout.md | new-features/03-impl/tests/cli-logout.md | replace(`FR-env-03` 受入基準 14〜22 の行。14〜18・22 は `reset` と共通または `reset` 側で、主担当がこの表) |
| 03 | docs/03-impl/tests/cli-reset.md | - | **変更なし(下降中に判定した)**。理由: `FR-env-03` 受入基準 14〜18・22 は `logout` と共通(または `logout` の受入基準20 と対になる非対称)で、重複を作らないため対応表は `cli-logout.md` が持つ(このファイルの既存の書き方=「主担当モジュールの対応表が持つ」と同じ)。3つの表はいずれも変わらない |
| 03 | docs/03-impl/tests/cli-start.md | new-features/03-impl/tests/cli-start.md | replace(`FR-env-01` 受入基準14 の行) |
| 03 | docs/03-impl/tests/cli-common.md | new-features/03-impl/tests/cli-common.md | replace(**★フェーズ2 で追加**。`FR-env-01` 受入基準 16・17 の行 + `MODULE-cli-common-lock` の行) |
| 03 | docs/03-impl/tests/e2e.md | new-features/03-impl/tests/e2e.md | replace(**★フェーズ2 で追加**。`### E2E-01` に手順8(13項目)を追加 + 手順7-7 の `issue 045` 応急処置を修正後の期待値へ。**★`/doc-check` が2見出しを追加**: `## E2Eシナリオ ⇄ テスト対応表` と `## 通過する機能(トレーサビリティ)`(E2E-01 の範囲に破壊的操作と `MODULE-cli-common-lock` を反映)) |
| 03 | docs/03-impl/index.md | - | **変更指示なし。ただし `/task-close` が手で更新する**(★2026-08-04 `/doc-check`(3回目)が理由を訂正: **このファイルは全体が生成物ではない**。`build-index.py` が書き換えるのは `## 目次` の GENERATED ブロックだけで、**`## この層の状態` は手書きである**(`build-index.py --check` の対象に `docs/03-impl/index.md` は現れない)。実装後にしか決まらないので変更指示にはしないが、`/task-close` が**3点**を手で直す必要がある: (1) **機能間連携仕様書の本数 82 → 83**、(2) `check-relations.py` 最終結果の件数 `82 ファイル / 82 ID` → `83 / 83`、(3) 「実装の欠陥として起票済み」の集計(実際に閉じた issue を外し `046` を足す)。タスクリスト14 に明記した) |
| 03 | docs/03-impl/feature-graph.md / callgraphs/ | - | 変更なし(理由: ツールだけが書く生成物。変更指示の `target` にならない。実装後に `build-callgraphs.py` / `cluster-features.py` で再生成する) |
| — | claude-dev / claude-dev-mac | (コード) | 修正の本体 |

## 決定シート(回答済み)

- フェーズ1 の6論点と委任 a・b → `memo-1.md`
- フェーズ2 の U-1〜U-3(全件 A) → 「未決点」表(反映先を各行に記録)/ 経緯は `memo-2.md`
- **`/doc-check` が提示した5論点(U-20〜U-24)→ 2026-08-04 に人間が全件 A で回答済み。**
  反映先は「未決点」表の各行。
- **`/doc-check`(3回目)が提示した論点 #3・#4・#5 → 2026-08-04 に人間が「全て推奨で」と回答済み。**
  - **#3 `stop <name>` を確認プロンプトの対象外にする根拠**(推奨=項3 に明示的に免除を書く)→
    `D0-env-08` **項3 に免除を明記した**(「対象は集合として列挙する `logout` / `reset` の2つに限る。
    `stop <name>` は利用者が明示的に指した削除なので確認を求めない」)。**項1 ではなく項3 が根拠**
    であることを契約の「エラーケース」の該当行にも反映した。
  - **#4 compose 一意化名のハッシュ衝突**(推奨=残存リスクとして受容)→ **`docs/pendings.md` の
    P-005 として記録**し、契約の「compose 資源の識別」から参照した。**衝突は検出しない。**
    本変更の値打ちは「ありふれた組み合わせで確実に起きる衝突」を「実用上無視できる確率の衝突」に
    変えることであって、衝突をゼロにすることではない、と明記した。
  - **#5 `terminology.md` 未検証で `/task-close` が止まる**(推奨=本タスクで発行せず)→
    **`docs/issues/044` を実読して確認した: 合格証の発行は3本目 `task-spec-measurability` の
    担当と人間が裁定済みで、しかも発行には 01/02 への下降が前提**(まだ行われていない)。
    したがって**本タスクでは発行しない**。3本目を先に回すのは実行順の根拠(コードを変える本タスクが
    先)と衝突するので採らない。→ **フェーズ4 で人間が例外として承認する**。
    ゲートの構造的な欠陥そのものは `.claude/improvements/`
    **`KIT-close-task-demands-certificates-for-unchanged-closure-rows.md`** に起票した
    (「変更なし」行の合格証まで要求してしまう。推奨は案A=「変更なし」行を機械的に除外)。
  **未回答の論点は無い。**

### フェーズ3(実装)の決定シート — **2026-08-04 に人間が回答済み**

- **#1 = A(現状のまま)。** 遊休判定は契約の字面どおりのまま変えない。02 の変更指示も
  実装も**変更なし**。「過剰に数える=消さない側」なので `FR-env-01` 受入基準9 は破らない。
- **#2 = B(サブエージェントで代替する)。** Codex の代替として**新しい文脈の Claude Code
  サブエージェント**に同一条件(同じ対象・範囲・基準・形式、こちらの指摘は渡さない、
  読み取り専用)で差分監査を依頼した。**レンズは「サブエージェント」であり Codex ではない**
  (CLAUDE.md 不変則7: 代替を Codex 監査として報告してはならない)。結果は下の進捗メモ。

| # | 論点 | 選択肢 | 推奨 | 未回答時の既定 | 根拠 |
|---|---|---|---|---|---|
| 1 | **遊休判定の集合に利用者の compose コンテナが入る**(質問キュー Q-1)。契約どおりに実装した結果、`claude-dev-net` に接続している稼働中コンテナ**すべて**(docker-proxy と `fwd-*` を除く)が「稼働中」に数えられる。**Claude コンテナ内から起動した `docker compose` の資源も `claude-dev-net` に接続する**ため(本ホストで実測 40 件)、`stop` / `logout` で docker-proxy がほぼ回収されず、**`reset` は毎回「完全な初期化になっていない」**になる | **A. 現状のまま**(仕様どおり。過剰に数える=消さない側なので受入基準9 は破らない。docker-proxy が残る害は「使われていない小さなコンテナが1つ残る」だけ) / **B. 除外対象に `com.docker.compose.project` ラベルを持つコンテナを足す**(契約の遊休判定の定義を変える = **同層 02 の変更指示を書き直す**) / **C. 本タスクは A のままにし、`docs/issues/` に起票して別タスクで扱う** | **A**(仕様が明示的に「過剰に数える=消さない側なので受入基準9 を破らない」と述べており、実装は契約の字面どおり。B は 02 の契約を書き換えるので本タスクの下降をやり直すことになる) | **A** | 契約 `CTR-cli-container`「遊休判定」/ `D0-env-08` 項2 / `MODULE-cli-reset` 判断7 / `FR-env-01` 受入基準9 |
| 2 | **独立レンズ(Codex)が結論を出さずに終了した。サブエージェントで代替するか**(CLAUDE.md 不変則7 により無断で代替しない) | **A. 代替しない**(本監査は C-0 の補助であってゲートではない。`/task-close` の `/doc-check` で改めてレンズが立つ) / **B. 同条件でサブエージェント(新しい文脈の Claude Code)に同じ監査を依頼する**(独立性は下がる — 同系統のモデルは盲点を共有する) | **A** | **A**(不変則7 の既定) | CLAUDE.md 不変則7 / `/implement` C-0。**ツールの問題なので issue / pending には起票しない**(不変則6) |

**#2 の実測**: `codex exec --sandbox read-only -m gpt-5.6-terra`(reasoning high)で
差分監査を **2 回**実行した(2 回目はプロンプトを絞り、`.claude/` を読ませず本文で結論を出すよう
明示)。**どちらも終了コード 0 だが、コードを読み進めた途中で出力が途切れ、指摘の一覧を
出さずに終了した**(1 回目 7,181 行 / 2 回目 9,707 行の出力の末尾がいずれもファイルの
`sed` ダンプ)。フェーズ2 の 3 回のタイムアウトに続いて **5 回連続でレンズが立っていない**。
`git status --porcelain` の比較で Codex による書き込みが無いことは確認済み。

## 未決点

<!-- 帰着は「ドキュメント記載」「委任決定(D-ID)」「人間判断」の3つのいずれか。
     人間判断が1つでも残る間は /implement を開始しない(CLAUDE.md 原則7)。 -->

| # | 未決点 | 帰着 | 検出元 |
|---|---|---|---|
| (なし) | — | — | — |

<!-- 2026-08-04 /doc-check(3回目)のドライラン パス1 で立った8点は、すべて上流が答えを
     持っていたため「ドキュメント記載」で帰着した(人間判断はゼロ)。内訳は進捗メモの
     自動修正(1)〜(7)と、次の1点:
     ・確認プロンプトは1文字読みか1行読みか → SSOT の MODULE-cli-reset が
       「`read -n 1` で1文字だけ読む」と記録しており、D0-scope-02(観測可能な振る舞いを
       変えない)が答えを決めていた。logout も同じ読み方に揃えた(自動修正5)。
     ・ハッシュ源の与え方(`echo` か `printf`)は observable な値ではなく、start と stop が
       同じ関数を共有すること(MODULE-cli-start 判断3)で一致が保証されるため、
       D0-scope-02 の委任範囲内(未決点ではない)。 -->

**未決点はゼロ。** フェーズ2 で立った 28 件はすべて帰着済みで、経緯と反映先は `memo-2.md` にある。
帰着の内訳: **人間判断8**(フェーズ2 の U-1〜U-3 と `/doc-check` の U-20〜U-24。すべて回答=A)/
ドキュメント記載15 / 委任決定4(`D0-env-09`)/ 仕様どおりと裁定1(U-18)。

## 調査メモ

<!-- パス2で確かめた事実。1行1事実、path:line 付き。SSOT ではない(derived cache)。 -->

- `stop_proxy_if_idle` の実体は `claude-dev:382`〜`:391`。欠陥の行は `claude-dev:384` の
  `docker ps --filter "ancestor=$IMG_CLAUDE" --filter "ancestor=$IMG_CLAUDE_VNC" -q | wc -l`。
- **Claude コンテナは `--network "$NETWORK"` で起動する**(`claude-dev:905`。`NETWORK="claude-dev-net"` は
  `claude-dev:28`)。**遊休判定をネットワーク接続で行える根拠**。
- **docker-proxy も同じネットワークに接続する**(`claude-dev:422`)→ 遊休判定から**固定名で除外**する。
- **`fwd-*` 中継コンテナも同じネットワークに接続する**(`claude-dev:1199`)→ 遊休判定から
  **`fwd-` 接頭辞で除外**する。名前生成は `claude-dev:1186` / `:1223` の `FWD_NAME="fwd-${NAME}-${CPORT}"`。
- **`login` / `login-codex` の一時コンテナも同じネットワークに接続し、`--name` を持たない**
  (`claude-dev:521`〜`:522` と `:590`〜`:591` の `docker run --rm -it --network "$NETWORK"`)。
  → 遊休判定はこれを「稼働中」として数える(**過剰に数える=消さない側**なので受入基準9 は破らない)。
- **`start` の認証コピーの一時コンテナは `--network` を持たない**(`claude-dev:753`〜`:766`)
  → 遊休判定に混じらない。
- **`~/.claude-dev` は Linux 版・macOS 版の両方にある**: `claude-dev:67` の
  `DEV_AGENT_DIR="${DEV_DIR}/agents"` と `claude-dev-mac:80` の `DEV_DIR="${HOME}/.claude-dev"`。
  → ロックの置き場所を `${HOME}/.claude-dev/locks` にできる根拠。権限の前例は `claude-dev:174` の
  `chmod 700 "$DEV_DIR" "$DEV_AGENT_DIR"`。
- **`trap` は Linux 版・macOS 版のどちらにも1つも無い**(`grep -c "trap " claude-dev` = 0、
  `claude-dev-mac` = 0)→ ロックの解放に `trap` を入れるのは新規の導入である。
- `set -e` は `claude-dev:8` と `claude-dev-mac:13`。
- `stop` の `fwd-` 一括削除は `claude-dev:1144`。`reset` の `fwd-` 全削除は `claude-dev:1405`。
- **`--filter ancestor` は他に3箇所ある**: `MODULE-cli-list`(処理の流れ1)/ `MODULE-makefile-status`
  (同2)/ `MODULE-makefile-clean`(同2)。**`docs/issues/046` として起票した**(本タスクの範囲外)。
- **compose 資源にはホスト CLI のラベルが届かない**(compose は Claude コンテナ内で docker-proxy 経由に
  資源を作る)。`COMPOSE_PROJECT_NAME` の生成は `claude-dev:820`〜`:821` の
  `sed 's/[^a-z0-9_-]/-/g'`(非可逆)。→ 未決点 U-1 の根拠。
- `AC-06`(`docs/00-requests/acceptances.md:80`〜`:97`)は `logout` に一言も触れていない
  → 確認プロンプトの追加は `AC-06` と衝突しない。

**2026-08-04 `/doc-check`(3回目)のパス2 で確かめた事実:**

- **`reset` は `claude-dev-vm-*` ボリュームを消していない**(`claude-dev:1408` / `claude-dev-mac:1382`
  のコメントが「共有 3 ボリューム + `claude-dev-chrome-*`」と明示。生成は `claude-dev:881`)。
  契約 `CTR-cli-container` の資源表は `claude-dev-vm-` を本システムの接頭辞として挙げているので
  片手落ちだが、**対象範囲の拡大は本タスクの「やらないこと」**。→ `docs/issues/047` に起票した。
- **`docs/03-impl/index.md` は全体が生成物ではない**。`build-index.py` の `--check` 出力に
  このファイルは「目次(4件)」としてしか現れず、**`## この層の状態` は手書き**である
  (`.claude/scripts/build-index.py:52` の `"index": "docs/03-impl/index.md"` は目次ブロックの
  書き出し先)。→ closure 表の理由を訂正し、タスクリスト14 に本数 82→83 を明記した。
- **`docs/02-design/logging.md` の `## 主要イベントのログ仕様` には既に
  「コンテナ名の衝突による起動の中止」(`FR-env-01` 受入基準12)が載っている**。
  → 本変更の新しい出力を同じ粒度で載せる前例になる(自動修正2 の根拠)。
- **`02-design/system.md` の `### 結合テスト対象` の `CTR-cli-container` 行は責任モジュールが
  `MOD-entrypoint` 単独**だった。管理ラベル・遊休判定・ロックキーは `MOD-entrypoint` を
  一切通らない。→ 2行に分けた(自動修正3)。
- `relations-query.py --health` の「呼び出し先が多い機能(> 7)」に **`MODULE-cli-start` が 12 件**で
  載っている。本タスクで `MODULE-cli-common-lock` が増えて **13 件**になる。
  分割は 02 の分割定義の見直し事項であり、本タスクでは行わない(報告のみ)。

**2026-08-04 `/doc-check`(フェーズ2 の検証)のパス2 で確かめた事実:**

- **`reset` が docker-proxy を無条件に削除するのは現行の実装・現行の SSOT どちらもそうである**
  (`docs/03-impl/relations/MODULE-cli-reset.md` の手順2 が「全 Claude コンテナ・全 `fwd-*`・
  `claude-dev-docker-proxy` を `docker rm -f` する」)。**したがって U-20 は本タスクが新たに作る
  不整合である**: 変更前は全コンテナを消してから proxy を消していたので整合していたが、
  本タスクが「ラベル無しコンテナは残す」と決めたことで「残したコンテナの足元の proxy を消す」形になる。
- `docs/00-requests/decisions/scope.md` の `D0-scope-02` の本文に
  **「利用者のリポジトリを触らない」という文言は無い**(委任範囲は実装内部の構造の選択、
  ガードレールは「観測できる振る舞いを変えない」)。この文言の実体は
  `docs/03-impl/relations/MODULE-cli-reset.md:98` の実装上の判断2 が `D0-scope-02` を根拠として
  記録したものである。→ `D0-env-08` 項4 の「`D0-scope-02` の…判断を撤回する」は出所の書き方が
  曖昧(決定シート #2 の付随修正に含めた)。
- `docs/00-requests/terminology.md` は version 1.1.0 で **`verified` を持たない**(未検証)。
  ただしこれは `docs/issues/044` で人間が裁定済みで、**合格証の発行は3本目
  `task-spec-measurability` の担当**と決まっている。本タスクの阻害要因ではない。
- `.claude/scripts/check-changeset.py` は**引数にタスク slug を渡すと対象0ファイルで
  「★ 不変条件の違反なし」と表示する**(fail-open)。正しい引数は `new-features` へのパス。
  → `/kit-improve` 案件(申し送り事項に記載)。
- `docs/02-design/relations.md` の `## 一覧` の実データ行は **63 行**(コメントの「63 行」は
  現時点では正しい)。本タスクが `PLAN-cli-common-lock` を足すと 64 行・全83機能になる。
- `docs/02-design/system.md` の分割定義で **`MOD-cli-reset` の依存欄だけが「—」** だった
  (他の CLI モジュールは `MOD-cli-common`)。`PLAN-cli-common-lock` を呼ぶので要更新。

## 質問キュー(未提示)

| # | 質問 | 前提 | いつ聞くか |
|---|---|---|---|
| ~~Q-1~~ **(2026-08-04 回答済み = 案A「現状のまま」。決定シート #1)** | **遊休判定の集合に利用者の compose コンテナが入り、docker-proxy と `claude-dev-net` が事実上ほぼ回収されなくなる**。契約の遊休判定は「`claude-dev-net` に接続している稼働中コンテナから docker-proxy と `fwd-*` を除いた集合が空のときだけ削除」と定めるが、**Claude コンテナ内から起動した `docker compose` のコンテナは `claude-dev-net` に接続する**(実測: 本ホストで 40 件。`docker-localstack-1` の `NetworkSettings.Networks` = `claude-dev-net` のみ)。仕様どおり「過剰に数える=消さない側」なので `FR-env-01` 受入基準9 は破らないが、(a) `stop` / `logout` で docker-proxy が残り続ける、(b) **`reset` が毎回「完全な初期化になっていない」になる**、(c) 残した理由の表示が数十行になる。契約が想定していた残存理由は「ラベルを持たない Claude コンテナ」だけで、この経路は想定外だった | 契約「遊休判定」/ `D0-env-08` 項2 / `MODULE-cli-reset` 判断7 | **フェーズC の決定シート**(実装は仕様どおりに済んでおり、`/implement` を阻害しない) |

## タスクリスト

<!-- /implement が確定させる下書き。番号は実装順の目安。 -->

- [ ] 1. `/task-doc task-fix-destructive-scope`(00→03 の1回の下降 + 実装ドライラン) _Depends:_ 決定シートの回答
- [x] 2. **未決点 U-1〜U-3 の回答を変更指示へ反映する**(2026-08-04 完了。全件 A)
- [x] 3. `/doc-check task-fix-destructive-scope` が PASS(**3回目=2026-08-04 に新しいセッションで PASS。** 1回目=不合格(高5件)→回答済み / 2回目=セッション上限で中断 / 3回目=自動修正8件を適用して PASS。**ただし独立レンズは立たなかった**(Codex が capacity とタイムアウトで2本とも失敗)。代替の可否は決定シート #1) _Depends:_ 2
- [x] 4. `MODULE-cli-common-lock` を実装する(`acquire_lock` / `release_lock` を Linux 版・macOS 版の両方へ) _Depends:_ 3 — **2026-08-04 完了**(commit `edeead2`)
- [x] 5. `start` に管理ラベル3つの付与と2段のロックを入れる(docker-proxy にはラベルを付けない。**共有資源単位のロックは認証コピー〜`docker run` 完了まで保持**) _Depends:_ 4 — **完了**(commit `552adad`)
- [x] 6. `stop` の遊休判定を `claude-dev-net` の接続ベースへ置き換え、`fwd-*` を名前で扱い、**本体削除の前に `project-dir` ラベルを読む** _Depends:_ 4 — **完了**(commit `8a2c7cf`)
- [x] 7. `logout` に確認・`--yes`・管理ラベルによる限定・**docker-proxy の遊休判定**・削除失敗の列挙と非0終了・**`INT`/`TERM` 時の列挙と終了コード 130** を入れる _Depends:_ 4 — **完了**(commit `09b2faa`)
- [x] 8. `reset` に `--yes`・非 TTY 中止(終了コード 1)・管理ラベルによる限定・**共有資源の遊休判定**・削除失敗の列挙・**`INT`/`TERM` 時の列挙と終了コード 130** を入れる _Depends:_ 4 — **完了**(commit `dbd4c9a`)
- [x] 9. `COMPOSE_PROJECT_NAME` の一意化(`<正規化名>-<絶対パスの SHA-256 先頭6桁>`)を実装し、`start` と `stop` が同じ関数を使うようにする。旧名の資源は消さず案内する _Depends:_ 3 — **完了**(commit `552adad` / `8a2c7cf`)
- [x] 10. `logout` がカレントディレクトリの認証3ファイルを削除し、削除したパスを表示するようにする(ディレクトリと `settings.json` は残す) _Depends:_ 4 — **完了**(commit `09b2faa`)
- [x] 11. `login` / `login-codex` に共有資源単位のロックを入れる(対話認証の全区間で保持) _Depends:_ 4 — **完了**(commit `48ff60e`)
- [x] 12. `E2E-01` 手順8 を実機で実行する(Linux。macOS は実行可否を記録する) _Depends:_ 5〜11 — **13項目すべて実行して合格**(実行方法の内訳は進捗メモ)。**macOS は未実施**(macOS ホストが無い)
- [x] 13. `build-callgraphs.py` → `cluster-features.py` → `callgraph-check.py`(重大度「高」ゼロ)→ `check-relations.py` → `check-contracts.py` → `build-index.py` _Depends:_ 12 — **全通過**(進捗メモ)
- [ ] 14. `/task-close task-fix-destructive-scope`。**★`close-task.py` の条件 (b) は
      `docs/00-requests/terminology.md`(未検証・本タスクは触らない)で必ず失敗する。
      2026-08-04 に人間が「フェーズ4 で例外承認」と決めた論点なので、そこで承認を得て進める**
      (勝手に合格証を発行しない = `docs/issues/044` の裁定 / closure 表から行を消さない =
      合格証の範囲を黙って狭めない)。**`03-impl/index.md` の `## この層の状態` を手で3点直す**(このファイルは `## 目次` だけが生成物で、この節は手書きである): (a) **機能間連携仕様書の本数 82 → 83** と `check-relations.py` 最終結果の `82 ファイル / 82 ID` → `83 / 83`、(b) **「実装の欠陥として起票済み」の集計から実際に解消した issue を外す**(現行16件。`020`/`024`/`025`/`029` のうち閉じたもの。**`046` は新規に増える**)、(c) **`045` の扱い**: 現行の同節は「`045` の本来の置き場は `MODULE-cli-stop` の『既知の制限』であり、`MODULE-cli-stop` を影響範囲に含む次のタスクで書く」と約束しているが、**本タスクが `045` を修正するので「既知の制限」には書かず、解消したので不要になったと記録する**(約束を黙って落とさない) _Depends:_ 13

## Definition of Done の検証結果(2026-08-04 フェーズ C-4)

| # | DoD 項目 | 結果 | 根拠 |
|---|---|---|---|
| 1 | `issue 020` の全4行が再現しない | **合格** | 6コマンドすべてで排他を実測(`shared` 保持中は `logout`/`reset`/`login`/`login-codex` が終了コード 1、プロジェクト単位保持中は `start`/`stop` が 1。`start` は `.claude-dev.yaml` すら作らない) |
| 2 | `issue 024` の再現手順で他プロジェクトの compose 資源が消えない | **合格** | `/tmp/e2e-y/My.App` と `/tmp/e2e-y2/my-app` が `my-app-2efe44` / `my-app-250f4b` に分かれ、一方の `stop` で他方の compose コンテナが残った(E2E-01 手順8-6) |
| 3 | `issue 025` の再現手順で成功文言が出ず、消えなかった資源が列挙され非0で終わる。事象(2) も解消 | **合格** | 使用中ボリュームで `reset --yes` が「全リセット完了」を出さず 1 件列挙して終了コード 1(手順8-10)。認証3ファイルの削除を実測(手順8-8) |
| 4 | `issue 029` の再現手順で確認プロンプトが出て、`n` で何も消えない | **合格** | 確認一覧にラベル無しコンテナが載らず、`n` で何も削除されない(手順8-9)。非TTY は終了コード 1 |
| 5 | `issue 045` の再現手順で共有 docker-proxy が消えない | **合格** | 本ホストの実測で**旧方式 0 件 / 新方式 40 件**。旧コードなら「Claude コンテナなし」と判定して docker-proxy を削除する状態で、新コードは残す(手順8-2) |
| 6 | `E2E-01` 手順8 の 13 項目すべてが不合格の条件に当たらない | **合格(Linux)** | 進捗メモに実行方法の内訳。7項目を実スクリプト、6項目をサンドボックス版(定数名だけ差し替えた同一コード)で実行。**独立レンズの指摘を反映したあとに全経路を再実行して再度合格を確認した** |
| 6b | 独立レンズの重大度「高」の指摘が残っていない | **合格** | 指摘13件(高1/中5/低7・誤検知0)。**高1件と中5件・低4件を修正**し、仕様どおりの3件は既知の制限へ記録した。レンズは**サブエージェント**(決定シート #2 = B で人間が承認。Codex ではない) |
| 7 | Linux 版と macOS 版で同じ成否・同じ出力 | **部分的**。macOS は**未実施**(macOS ホストが無い) | 新規・変更コードが**文字列として完全一致**することを機械照合(排他ロック基盤・`logout`・`reset` は完全一致。`stop` の差分は macOS 固有の `stop_ssh_bridge` 2行のみ) |
| 8 | lint とテストがグリーン | **合格**(ただし既知の例外1件) | `go vet ./...` × 2 / `go test ./...` / `go test -mod=vendor ./...` すべて合格。`cd examples/orch-sample && pytest` の 12 件失敗は**本タスクと無関係の既知の状態**(題材プロジェクトは実装がスタブ。`docs/issues/033`)。`git stash` した状態でも同じ 12 件が失敗することを実測 |
| 9 | `callgraph-check.py` 高ゼロ / `check-relations.py` / `check-contracts.py` / 鮮度検査 | **合格** | 高 **0**(中3 は影響範囲外の既存指摘)/ 82 ファイル 82 ID 合格 / 契約合格 / `build-callgraphs --check` 最新 / `cluster-features --check` 最新 |
| 10 | `03-impl/tests/` の該当ファイルが更新済み。`03-impl/index.md` の集計が実態と一致 | **`/task-close` で実施** | tests の変更指示はフェーズ2 で作成済み(状態列は `未検証(テスト未実装)` のまま。シェルに自動テストランナーが無く実機確認で代替する既存の方針どおり)。`index.md` の3点の手修正はタスクリスト14 |
| 11 | SSOT へ反映・`verified` 発行・histories へ記録・`close-task.py` の4条件 | **`/task-close` で実施** | — |

## Definition of Done

- [ ] `docs/issues/020` の事象表の**全4行**が再現しない(`start` × `logout` / `start` × `reset` /
      `logout`・`reset` × `login` / 同一ディレクトリの二重 `start`)。**`login` も排他の対象に
      含めたので、この issue は本タスクで閉じられる**
- [ ] `docs/issues/024` の再現手順(正規化後に衝突する2ディレクトリ)で他プロジェクトの compose 資源が
      消えない(`E2E-01` 手順8-6)
- [ ] `docs/issues/025` の再現手順で「削除しました」と表示されず、消えなかった資源が列挙され非0で終わる。
      **事象(2)**: `logout` 後に同じディレクトリで `start` しても未ログインで起動する(`E2E-01` 手順8-8)
- [ ] `docs/issues/029` の再現手順で確認プロンプトが出て、`n` で何も消えない
- [ ] `docs/issues/045` の再現手順(`make upgrade` 後の `stop`)で共有 docker-proxy が消えない
- [ ] `E2E-01` 手順8 の**13項目**すべてが**不合格の条件に当たらない**(Linux。macOS は実行可否を記録)
- [ ] Linux 版と macOS 版で**同じ成否・同じ出力**である(`D0-scope-03`。macOS を実行できない場合は
      未実施であることを記録する)
- [ ] lint とテストがグリーン(`docs/02-design/environments.md` の厳密なコマンド文字列)
- [ ] `callgraph-check.py` 重大度「高」ゼロ / `check-relations.py` 合格 / `check-contracts.py` 合格 /
      `build-callgraphs.py --check` が最新 / `cluster-features.py --check` が最新
- [ ] `03-impl/tests/` の該当ファイルが更新済み。`03-impl/index.md` の集計が実態と一致
- [ ] SSOT へ反映・`verified` 発行・histories へ記録・`close-task.py` の4条件を通過

## 進捗メモ
- 2026-08-04 **`/doc-check task-fix-destructive-scope`(3回目。新しいセッション=`/clear` 後)
  判定: PASS。レンズ: なし(Codex が2本とも失敗)→ **後続の追記のとおり Codex 復旧後に1周実施**。**
  **独立レンズは立たなかった**: `docs` / `readiness` の2本を並行起動したが、1回目は両方とも
  Codex 側の `Selected model is at capacity`(範囲の読み込みを終えた直後。284k / 398k トークン消費)、
  §3 の許す1回の再試行でも `readiness` は同じ capacity、`docs` は **900 秒のタイムアウトで打ち切り**
  (`environments.md` の監査タイムアウト)。**ツールの問題なので issue / pending には起票しない**
  (CLAUDE.md 不変則6)。`git status --porcelain` の比較で Codex による書き込みが無いことを確認済み。
  **代替(サブエージェント)は無断で立てていない**(不変則7)。決定シートに1件載せた。
  **自動修正 8 件**を適用した(下記)。**未決点ゼロは維持**。
  - 自動修正: (1) 契約の「排他(ロックキー)」に **`ensure_infrastructure`(ネットワーク・共有
    ボリュームの作成)を保護対象外**として明記 + 「ロックが守る資源」を「共有ボリュームの**中身**」へ
    限定(`login` / `login-codex` の判断1 が「契約が定める」として既に前提にしていたのに契約側の
    記述が無く、`FR-env-01` 受入基準16 の字面に反していた)。`FR-env-01` 受入基準16 も同じ語へ。
    (2) **`02-design/logging.md` を影響範囲に追加**し `## 主要イベントのログ仕様` に破壊的操作の
    出力 11 行を追加(`MODULE-cli-start` 判断8 が指す先に定義が無かった)。
    (3) `02-design/system.md` の `### 結合テスト対象` を影響範囲に追加し、`CTR-cli-container` を
    **起動側 / 破壊的操作の対象の識別**の2行に分けて後者の責任モジュールを
    `MOD-cli-stop` / `-logout` / `-reset` にした(契約に当事者が増えたのに責任モジュールが
    `MOD-entrypoint` のままで、新しい部分をどこも観測していなかった)。
    (4) `02-design/relations.md` の `### PLAN-cli-common-*(共有基盤)` を影響範囲に追加
    (「用意系だけが副作用を持つ」「用意系はすべて冪等」が**排他系**と両立しない)。
    (5) `MODULE-cli-reset` / `-logout` の `## 呼び出され方` に**確認プロンプトが受理する入力**の表を
    戻した(replace が SSOT の表=「`read -n 1` で**1文字だけ**読む」を落としており、破壊的操作の
    確認が1文字か1行かで観測可能に分かれるのに未規定になっていた。現行の読み方を維持=`D0-scope-02`)。
    (6) `MODULE-cli-common-lock` 判断10 の「認証コピーの終わりで明示解放」→
    「コンテナ作成の確定(手順15 の再試行ループを抜けたところ)」(2026-08-04 の修正に追随)。
    (7) `03-impl/tests/cli-common.md` の「4コマンド」3箇所 →「6コマンド」。
    (8) closure 表の `03-impl/index.md` の理由を訂正(**全体が生成物ではない**。`build-index.py` が
    書くのは `## 目次` だけで `## この層の状態` は手書き)+ タスクリスト14 に**本数 82→83** と
    **`045` の「既知の制限」への約束の始末**を明記。
  - **起票した issue 2件**: `047`(`reset` が `claude-dev-vm-*` ボリュームを消さない。対象範囲の
    拡大なので本タスクの「やらないこと」に当たる)/ `048`(02 の「共有基盤どうしは呼び合わない」が
    同じ文書の一覧表の2本の辺と矛盾。本タスクとは無関係に以前から存在)。
  - 機械検査: `callgraph-check.py --to-be` 重大度「高」**0**(中3 は `MODULE-entrypoint-claude` の
    CG3 = 影響範囲外の既存指摘)/ `check-relations.py` 合格(82/82)/ `check-contracts.py` 合格 /
    `build-callgraphs.py --check` 最新 / `cluster-features.py --check` 最新 /
    `build-index.py --check` 差分なし / `check-changeset.py` I1 と I3〜I9 合格。
    **I2(23件)と I10(1件)は偽陽性であることを機械的に確認した**(I2 が「存在しない」とした
    callee 7種は**全件が合成ビューに実在する**。スクリプトが `new-features/` の中しか見ないため)。
    `sections` 49個中 45個が SSOT と文字列一致・4個は新設見出し(`change-set.md` §2 が認める)・
    本文欠落0。
  - **受入基準の網羅を機械照合した**: `FR-env-01` の 21 件・`FR-env-03` の 23 件が**全件**
    `03-impl/tests/` の対応表に行を持つ(欠落0)。

- 2026-08-04 **`/doc-check`(3回目)の続き: Codex が復旧したので独立監査を1周実行した。
  判定: PASS(維持)。レンズ: Codex(`gpt-5.6-terra` / reasoning max、3本)。**
  タイムアウトを避けるため**スコープを分割**して3本並行: `docs`(00〜02層)/ `docs`(03層+E差分)/
  `readiness`。**上位2本が完走**(指摘 17 + 6 = 23件。高8 / 中13 / 低2)、
  **`readiness` は再び900秒でタイムアウト**(3回連続。`audit_failed`)。
  Codex による書き込みが無いことを `git status --porcelain` の比較で確認済み。
  - **誤検知 1 件**: 「`features.md` の `replace` が既存82行を消す」→ `change-set.md` の
    **Exception 1**(機能表は差分の表で書く)を私がプロンプトに転記しなかったことによる。
    変更指示の記法は規範どおりで正しい。**プロンプトの不備であって文書の欠陥ではない。**
  - **範囲外として棄却 5 件**(`FR-env-09` 受入基準10 の「してよい」/ ブロック対象ドメイン集合の
    未定義 / NFR の測定範囲(**3本目のスコープ**)/ pendings P-003 と `environments.md` の
    食い違い(`docs/issues/031` で追跡中)/ 要確認の「期限なし」)。
  - **確認済み・自動修正 8 件を追加適用**:
    (a) **`MODULE-cli-common-lock` のロック方式を `mkdir`+`owner` から
    「向き先に `<PID> <操作名>` を入れたシンボリックリンク(`ln -s`)」へ変更**(`D0-env-09` の
    委任決定)。**`mkdir` 方式には「ロックはあるが所有者が未記録」という窓があり、
    独立レンズが「1秒待って残骸と判定する規則では、1秒以上停止したプロセスがあると
    2プロセスが同じ臨界区間に入る」と指摘した**。`ln -s` は生成と所有者記録が1回の原子的操作なので
    **この中間状態が原理的に消え、時間依存の判定を全廃できる**。判断8 を差し替え、
    「1秒待つ」分岐と曖昧語「十分な時間」も同時に解消。`E2E-01` 手順8-3・8-4 の手順も
    シンボリックリンクの作り方へ更新した。
    (b) `FR-env-03` 受入基準5 に**「管理ラベルを持つ」実行中コンテナ**という限定を追加
    (受入基準17 と矛盾していた。ラベル無しコンテナを停止するかが一意に決まらなかった)。
    (c) `FR-env-01` 受入基準9 に **`stop`/`logout` は `claude-dev-net` を削除する経路自体が無い**
    ことを明記(`D0-env-08` 項2 の「3コマンド共通」との対応関係が読めなかった)。
    (d) `MOD-cli-reset` の責務欄を「全削除して初期状態へ戻す」から**共有資源を残す場合がある**形へ
    (新しい受入基準9 と両立していなかった)。
    (e) `D0-env-09` の**委任範囲から「待ち時間を設けるか」を外した**(同じ決定のガードレールと
    `FR-env-01` 受入基準16 が「待たない」と定めており、委任範囲と矛盾していた)。
    (f) `logging.md` の「削除対象の確認」行が INFO と ERROR を1行に混ぜていたので**3行へ分割**
    (確認 / 非TTY中止 / 遊休判定の問い合わせ失敗)。
    (g) `logging.md` に**起動ディレクトリの絶対パスを出す根拠**を追記(「出してはならない情報」の
    「ホーム配下の構造」との関係が未定義だった)。
    (h) `02-design/relations.md` の「原則として呼び合わない」を**実在する2本を名指しする**形へ
    (曖昧語の解消。どちらが正かは `docs/issues/048`)。
  - **起票した issue 2件**: `049`(**`AC-02` が例外なしで「`start` でポート非公開」を要求するが、
    既定のブラウザ確認ありは noVNC ポートを公開する** — `D0-env-02` は例外を明記しているのに
    `AC-02` が落としている。**3本目が `AC-02` を触るのでそこで直すのが効率的**)/
    `050`(**解釈できない Docker API ボディを中継してよいという `FR-env-07` 受入基準8 が、
    根拠である `D0-sec-05` のガードレール「拒否すべき操作を通してはならない」と両立しない**)。
  - **人間判断が要る残件 2 件**(いずれも**未決点ではなく、`/implement` を阻害しない**。
    決定シート #3・#4): `stop <name>` を確認プロンプトの対象外とする根拠 / compose 一意化名の
    ハッシュ衝突時の扱い。
  - 機械検査(再実行): `callgraph-check.py --to-be` **高0**/中3(範囲外)、`check-relations.py` 合格、
    `check-contracts.py` 合格、`check-changeset.py` I1・I8・I9 合格、曖昧語 0。
  - **★`close-task.py` の条件 (b) を先に実測した(フェーズ4 での不意打ちを避けるため)**:
    closure から抽出される仕様ドキュメントは **18 件**で、そのうち
    **`docs/00-requests/terminology.md` だけが「合格証がない(未検証, 現在 1.1.0)」で NG** になる。
    このファイルは本タスクが**触らない**(closure 表の「変更なし」行)が、`close-task.py` は
    表の全パスを検査するため、**このままだと `/task-close` がタスク削除を拒否する**。
    `docs/issues/044` で「合格証の発行は3本目 `task-spec-measurability` の担当」と人間が
    裁定済みなので、**本タスクで勝手に発行することも、ゲートを避けるために行を消すこともしない**
    (後者は「合格証の範囲を黙って狭める」= `.claude/directions/task-memo.md` §1 が名指しで
    警告している失敗)。**決定シート #5 で人間に諮る。**

- 2026-08-04 **`/implement` フェーズB を完走した(タスク4〜11。コミット 6 本)。**
  ゲート: 合格証チェーンは `terminology.md` を除き全件 verified(同ファイルは決定シート #5 で
  「フェーズ4 で人間が例外承認」と裁定済み)/ 未決点ゼロ / `environments.md` の lint・テスト
  コマンドは確定済み。
  - **フェーズBで見つけて直した実装上の欠陥1件**: `release_lock` を
    `local key="$1" lockfile="${LOCK_DIR}/${key}.lock"` と書くと、**同じ `local` 文の中では
    `${key}` がまだ展開されない**ため `lockfile` が `.../.lock` になり、ロックが解放されず
    配列からも外れなかった。単体テストで検出し、`lockfile` を別の文に分けて修正した
    (両版)。コードにコメントとして理由を残した。
  - **仕様に対する逸脱1件(改善方向)**: 管理ラベルを `LABEL_OPTS` 変数にまとめず、
    `docker run` の引数として引用付きで直接渡した。`claude-dev.project-dir` の値は利用者の
    パスでスペースを含みうるため、`$VAR` で展開すると語分割されてラベルが壊れる。
    変更指示(`MODULE-cli-start` 手順13・14)を実際の形へ更新した。
  - **macOS 版の `--kvm`/`--vm` 早期拒否の位置**: 変更指示の判断11 は「早期拒否は
    `require_setup` より前なのでロックを取らない」と書いていたが、**実コードでは
    `ensure_project_config`(= 最初の副作用)が早期拒否より前**にあるため、ロックは
    早期拒否より前に取られる。副作用ゼロで `trap` が解放するので害は無く、むしろ
    `require_setup` のイメージビルドも走らない分だけ受入基準16 に対して安全側である。
    判断11 を実態へ更新した。
- 2026-08-04 **`E2E-01` 手順8 の 13 項目をすべて実行して合格した(Linux)。**
  **実スクリプト(`./claude-dev`)で実行**: 8-1(管理ラベル3つの付与。docker-proxy には
  `claude-dev.` で始まる管理ラベルが付かないことも確認)/ 8-2(遊休判定がイメージ非依存。
  **旧方式 `--filter ancestor` が 1 件しか数えないのに対し新方式は 42 件**数え、
  `docs/issues/045` の数え落としが閉じたことを実測)/ 8-3 の一部(プロジェクト単位のキー)/
  8-4(残骸の引き継ぎ。`aaa.lock.stale.*` が残らないことも確認)/ 8-5 の後半
  (`stop <name>` はラベル無しでも削除し、その旨を表示)/ **8-6(`docs/issues/024` の再現手順。
  `/tmp/e2e-y/My.App` と `/tmp/e2e-y2/my-app` の compose 名が `my-app-2efe44` と
  `my-app-250f4b` に分かれ、一方の `stop` で他方の compose コンテナが消えないことを実測)**/
  8-7(受理しない名前)/ **8-11(無関係なディレクトリ `/tmp` から `stop my-app` を実行しても
  `claude-dev.project-dir` ラベルからハッシュ源を得て正しく片付ける)**。
  **サンドボックス版(定数名だけを `cdtest-*` に差し替えた同一コード)で実行**: 8-3 の全体
  (6コマンドすべて)/ 8-5 の前半(`logout` がラベル無しコンテナを消さず表示する・
  docker-proxy を残す)/ 8-8(認証3ファイルの削除と `settings.json` の保持)/ 8-9(確認と
  非対話時の中止)/ 8-10(使用中ボリュームで削除失敗を列挙して終了コード 1。
  「全リセット完了」を出さない)/ 8-12(`reset` の遊休判定)/ 8-13(`INT` と `TERM` の
  両方で終了コード 130・部分削除の列挙・ロックが残らないこと)。
  **サンドボックスにした理由**: このホストで本物の `logout` / `reset` を実行すると、
  利用者の実際の Claude / Codex 認証を削除し、**いま動作中の Claude コンテナ(本セッション
  自身を含む)を落とし**、イメージまで消す。取り返しがつかない操作なので無人で実行しない。
  差し替えたのは定数(ボリューム名・ネットワーク名・proxy 名・イメージ名・ラベル接頭辞)と
  ロックの置き場所だけで、**通る分岐は実コードと同一**である。
  **macOS は未実施**(macOS ホストが無い)。ただし新規・変更コードの Linux 版と macOS 版が
  **文字列として完全一致**することを機械照合した(排他ロック基盤・`logout`・`reset` は完全一致。
  `stop` の差分は macOS 固有の `stop_ssh_bridge "$NAME"` の 2 行だけ)。
- 2026-08-04 **フェーズC-1 の機械検査を全通過**: `build-callgraphs.py` 再生成 →
  `cluster-features.py` 再生成(機能 82 / 辺 123)→ `callgraph-check.py --to-be` **重大度
  「高」0**(中3 は `MODULE-entrypoint-claude` の CG3 = 影響範囲外の既存指摘)→
  `check-relations.py` 合格(82/82)→ `check-contracts.py` 合格 → `relations-coverage.py`
  (未記載 30 件はすべて orchestrator / scripts の既存分。**本タスクの変更に起因するものは 0**)→
  `build-index.py` 実行(`docs/tasks/index.md` を更新)。
  **CG4 の取りこぼし 2 件を変更指示へ反映**: `MODULE-cli-reset` の `callees` に
  `MODULE-cli-common-container-exists` と `MODULE-cli-common-image-exists` を追加し、
  連携先の節と実装上の判断10(実在するものだけを削除対象に列挙する理由)を足した。
  あわせて **`MODULE-cli-common-lock` の `## 異常系`(10行の表)と `## 既知の制限`(5項目)を
  実装から確定させた**(フェーズ2 が意図的に空けていた節)。
- 2026-08-04 **申し送り事項の「キットの緊張点」(U-18)を本タスクの範囲で解消した。**
  `MODULE-cli-start` / `-stop` / `-logout` / `-reset` / `-login` / `-login-codex` の **6本すべて**で、
  変更指示の `sections:` に **`## 戻り値・副作用` / `## 異常系` / `## 既知の制限` を追加し、
  実装から確定させた本文を書いた**。フェーズ2 の時点ではこれらの節が変更指示に無く、
  SSOT 側に**旧挙動の記述が残ったまま**だった(実測: `MODULE-cli-logout` の異常系に
  「一時コンテナの `rm -rf` が失敗しても『削除しました』と表示して 0 で終わる」、
  `MODULE-cli-reset` に「標準入力が TTY でない → 空入力として扱いキャンセル」、
  `MODULE-cli-stop` の既知の制限に「compose プロジェクト名の正規化が非可逆」など、
  **本タスクが直した内容と正面から矛盾する記述が 6 本すべてに存在した**)。
  そのまま `/task-close` を回すと、変更指示が触らない節に旧挙動が残って
  **SSOT が自己矛盾する**(CLAUDE.md 原則2 違反)。`/implement` C-1 が
  「異常系と既知の制限は実装が持ち主なので、実装した結果から埋める」と定めているとおりに埋めた。
  **キット側の一般解(グリーンフィールド前提の `relations.md` §4.1 を既存実装の変更にも
  当てはめるか)は依然 `/kit-improve` 案件である**(申し送り事項に残す)。
- 2026-08-04 **lint とテスト**: `go vet ./...`(docker-proxy / orchestrator)合格 /
  `cd docker-proxy && go test ./...` 合格 / `cd orchestrator && go test -mod=vendor ./...` 合格。
  **`cd examples/orch-sample && pytest` は 12 件失敗するが、これは本タスクと無関係の既知の状態**
  である(題材プロジェクトはテストだけを置き実装はスタブ = `NotImplementedError`。
  **`docs/issues/033` として起票済み**)。本タスクの変更を `git stash` した状態でも同じ 12 件が
  失敗することを実測して確認した。

- 2026-08-04 **独立レンズを実施した。レンズ: サブエージェント(新しい文脈の Claude Code)。
  Codex ではない**(決定シート #2 = B で人間が代替を承認した。CLAUDE.md 不変則7)。
  読み取り専用・同一条件(同じ対象=`git diff d2c55e7..HEAD -- claude-dev claude-dev-mac`、
  同じ8項目の判定基準、同じ出力形式)で依頼し、**こちらの指摘・修正案・期待する結論は渡していない**。
  **指摘 13 件(高1 / 中5 / 低7)。誤検知 0 件。**
  - **判定と対処**:

    | # | 重大度 | 内容 | 判定 | 対処 |
    |---|---|---|---|---|
    | 1 | **高** | **残骸の引き取りが「生きているロック」を奪い、2プロセスが同じ臨界区間に入る** | **確認済み(自分でも再現を実測した)** | **修正した**。`mv` の後に `readlink` で中身を検証し、観測した残骸と違って PID が生きていれば `ln -s` で元に戻して取得失敗にする |
    | 2 | 中 | プロジェクト名が `shared` だと2つのキーが同じファイルを指し `start` が永久に失敗する | **確認済み(実測)** | **修正した**。ロックファイルを種別で名前空間に分ける(`proj-<key>.lock` / `shared.lock`) |
    | 3 | 中 | `logout` の一時コンテナが起動できなくても「空になった」と区別できず成功と報告する | 確認済み | **修正した**。列挙の直前に印を出させ、印が無ければ失敗に数える |
    | 4 | 中 | `logout` の最後の削除のあとに中断検査が無く、そこで中断すると 0 を返す | 確認済み | **修正した**。共有ボリューム消去の直後にも検査を置く |
    | 5 | 中 | 端末の `Ctrl-C` は子プロセスにも直接届くので「進行中の1件を終えてから」が成立しない | 確認済み | **修正した**。削除コマンドを `( trap '' INT TERM; ... )` のサブシェルで起動する(`SIG_IGN` は `exec` した子へ継承される。`setsid` は macOS に無いので使わない) |
    | 6 | 中 | 残したラベル無しコンテナが 30 秒ごとに認証を書き戻すため `logout` が巻き戻る | 確認済み。**ただし削除対象を広げることは受入基準17 が禁じている**ので、実装で選べるのは知らせることだけ | **警告を出すようにした**。`02-design/logging.md` の変更指示にも行を追加した |
    | 7 | 低 | `require_setup` の位置が Linux と macOS で違い、ロック取得の成否のタイミングが食い違う | 確認済み | **修正した**。Linux もロック取得の後に置く |
    | 8 | 低 | ネットワーク不在を「問い合わせ失敗」と扱うため `reset` が docker-proxy を消せない | **仕様どおり**(契約の「エラーケース」が「ネットワークが存在しない」を明示的に失敗として扱う) | **既知の制限に記録**(`MODULE-cli-stop` / `-reset`) |
    | 9 | 低 | 削除対象0件のとき、非 TTY でも終了コード 0 になる | **仕様どおり**(受入基準19 が受入基準15 より先に効く) | **既知の制限に記録** |
    | 10 | 低 | `reset` が遊休判定の問い合わせ失敗を告知せず「非管理コンテナは無かった」と読める | 確認済み | **修正した**(`logout` と同じ告知を出す) |
    | 11 | 低 | 引き取りに負けた側の表示が、既に死んでいる PID を「保持者」として示す | 確認済み | **修正した**(#1 の修正で実際の保持者を示す) |
    | 12 | 低 | 集合削除の各要素が他プロセスのプロジェクト単位ロックと排他になっていない | 確認済み。**両方のキーを取ると別プロジェクトの `start` を長時間止め `NFR-scale-01` を損なう** | **既知の制限に記録** |
    | 13 | 低 | `stop` の `xargs -r` は GNU 拡張で macOS の `xargs` には無い | 確認済み(本変更より前から存在) | **修正した**(明示ループへ) |

  - **修正の途中で自分のテストがもう1件検出した**: 印による判定を入れたとき
    `_auth_left=$(... | grep -v ...)` の `grep -v` が「一致行が無い(=印だけ=ボリュームが空)」
    ときに 1 を返し、`set -e` で `logout` が終了コード 1 になった。`|| true` を足して修正した。
  - **修正後に全経路を再実行して合格を確認した**: 排他(6コマンド)/ 残骸の引き継ぎ /
    生きているロックを奪わないこと / プロジェクト名 `shared` / `logout` の全経路 /
    `reset` の全経路 / 削除失敗の列挙 / `INT`・`TERM` での終了コード 130 / `stop` の対象限定。
  - 機械検査(再実行): `callgraph-check --to-be` **高0** / `check-relations` 合格 /
    `check-changeset` I1・I8・I9 合格 / `go vet` と `go test` グリーン。
  - **`E2E-01` 手順8-3 に確認項目を1つ追加した**(プロジェクト名が `shared` のときの起動)。

- **memo.md の行数について**: 約 400 行で `.claude/directions/task-memo.md` §2 の
  ローテーション閾値(300 行)を超えているが、**追い出せるものは追い出し済み**である
  (`memo-1.md` にフェーズ1の決定シート、`memo-2.md` に解消済み未決点28件、
  **`memo-3.md` に進捗メモ4件** — 2026-08-04 の `/doc-check`(3回目)が441行を検出して実施)。
  進捗メモは規定どおり**直近5件**の枠内(4件+行数の注記)で、
  **`判定: PASS` の行は `/implement` A-2-1 が読むので絶対に動かさない**(§2.1)。
  残っている節はいずれも規則上追い出せない: 影響範囲・タスクリスト・DoD・申し送り事項は**不可**、
  調査メモは**フェーズ3 のタスク4〜11 が使う**、進捗メモは直近5件を残す規定。
  影響範囲の表が 24 行あるのが主因(骨格 120 行の想定より大きいタスクである)。
  **次に memo.md を開いたスキルは、再ローテーションを試みても縮まない。**

## 申し送り事項

- **2本目 `task-relations-code-sync` は本タスクを閉じてから着手する**(重なるファイルはフェーズ2 で
  増えた。「実行順」の表を参照)。
- **3本目 `task-spec-measurability` はさらにその後**。あわせて **`00-requests/terminology.md` へ
  「破壊的操作」「管理ラベル」の2行を追加する**ことを3本目のスコープに入れてほしい
  (本タスクでは `D0-env-08` の本文に定義を閉じた)。
- `docs/issues/028`(命名の一意化)は本タスクでも閉じない。管理ラベル方式を採ったことで
  **`claude-dev.project-dir` が「どのディレクトリで起動したか」を事実として持つ**ため、
  同名衝突時の案内は改善する(緊急度は下がるが、名前の一意性自体は未解決)。
- **`docs/issues/046`(`list` / `make status` / `make clean` の `--filter ancestor` による数え落とし)を
  フェーズ2 で起票した**。本タスクが導入する管理ラベルをそのまま使えるので、次に `MODULE-cli-list` を
  触るタスクで一緒に直すのが効率的。`make clean` が確認なしに全 Claude コンテナを削除する点も同 issue に
  書いた(`D0-env-08` の対象に含めるかは別の判断)。
- **キットの不具合**: `.claude/skills/codex-audit/audit-schema.json` は OpenAI の strict 構造化出力の
  要件を満たしていない(`findings.items` の `related` が `required` に無い)。そのまま `codex exec
  --output-schema` に渡すと HTTP 400 `invalid_request_error` で失敗する。本実行はスクラッチパッド上の
  修正版スキーマ(全 object の `required` を全キーに、`additionalProperties: false`)で再実行した。
  **`/kit-improve` で恒久修正が必要**(ツールの問題なので issue / pending には起票しない。CLAUDE.md 不変則6)。
- **キットの緊張点(`/kit-improve` 案件)**: `.claude/directions/relations.md` §4.1 と `/task-doc` §2 は
  「実装前の 03 は frontmatter / 処理の流れ / 連携先と連携内容 / 実装上の判断だけを書く」と定めるが、
  既存実装を変更するタスクでは**書かない節に旧挙動の記述が残り、合成ビューが矛盾する**
  (本タスクでは「排他機構を持たない」「確認プロンプトは無い」「削除の失敗をすべて握る」が
  `### 並行性` / `## 異常系` / `## 既知の制限` に残る)。独立レンズがこれを重大度「高」で指摘した(U-18)。
  グリーンフィールド前提の §4.1 を**既存実装の変更**にも当てはめるかの判断が要る。
  現状は「`/implement` C-1 と `/task-close` §2 が実際の姿へ書き換える」という設計に従って書いていない。
- **`.claude/scripts/check-changeset.py` の不具合(`/kit-improve` 案件)**: **引数にタスク slug を
  渡すと「対象: 0 ファイル」で全項目 OK・「★ 不変条件の違反なし」と表示して終了する**(fail-open)。
  正しい引数は `new-features` ディレクトリへのパスである。`close-task.py` のような fail-closed の
  ゲートと違い、**間違った呼び方が「合格」に見える**ので危険。使用法の検証(存在しないパスなら
  非0で終わる)を入れるべき。
- **`.claude/scripts/check-changeset.py` の限界**: `new-features/` の中だけを読むため、
  部分的な変更指示では **I2(callee が存在しない)と I10(機能表と relations の差)が必ず偽陽性**になる
  (合成ビュー = SSOT + 変更指示 を見ていない)。本タスクでは I1 と I3〜I9 だけを根拠にした。
  スクリプト自身の docstring も「未配線」と述べている。
- **2026-08-10 19:52 以降に `/doc-check full`** を新しいセッションで1回(前タスクからの申し送り)。
