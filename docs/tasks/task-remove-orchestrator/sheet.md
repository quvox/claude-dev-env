# task-remove-orchestrator 決定シート

**記入方法**: 下の「一括回答」に **1行**書けば終わりです。
個別に決めたいものがあるときだけ、そのブロックの **★あなたの記入** の後ろに書いてください。
(あなたが ★あなたの記入 に書いた内容を AI が書き換えることはありません。**唯一の例外**:
新しい論点を追記したとき、末尾「記入完了」の日付だけは AI が消します — 再記入をお願いします。)

各ブロックには **AI推奨** と **未回答時の既定** という**別々の案**が載っています。

## 一括回答(ここだけ埋めれば先へ進めます)

<!-- ★ 下の行は 2026-08-08 の人間の指示を AI が転記したものである(通常は AI が書かない欄。
     経緯は memo.md「決定シート(回答済み)」の「転記の根拠」)。原文:
     「orchestratorに関する全ての記述、機能、実装を削除して、辻褄を合わせたい。新しいタスクを
      作って、作業を始めて。とにかく全く無かったことにしたい。いちいち質問しなくて良いから、
      一気にやりきってほしい」
     違う判断があれば、この行を書き換えるか個別ブロックへ記入してください。 -->

**★あなたの記入**: すべて推奨どおり

## 概念の明確化(00/01。上から確認してください。最大7件)

### 1. 語の外延 —「オーケストレーター」

- **場所**: `docs/00-requests/terminology.md:36`〜`:44` / `docs/00-requests/request.md:56`(RQ-orch-01)
- **明確にしたいこと**: 何を「削除対象」と1件に数えるか。含む例と含まない例
- **AI推奨**: **含む** = `orchestrator/`(Go 実装一式と `instructions/`)・`claude-dev orchestrate`
  サブコマンド・`make build-orchestrator` / `make orch-sample` / `make orch-sample-clean`・
  自己検証題材(`examples/orch-sample/` と `scripts/orch-sample.sh`)・
  通知フック(`scripts/save_prompt.sh` / `scripts/sendslackmsg.sh`。→ 概念2)。
  **含まない** = docker-proxy(`RQ-env-04`)・VM モード(`RQ-env-05`)・ブラウザ確認(`RQ-env-02`)・
  Codex CLI の同梱(`RQ-env-03`)・`scripts/wait-limit-reset.sh`(コンテナ内補助資産、`FR-env-01`)。
  理由: 削除の単位を「`RQ-orch-01` から降りてきたもの」と定義すると、要求カバレッジ表
  (`functional.md:539`)が1本の線を引いてくれる。崩れる条件: `RQ-env-*` 側から降りた機能が
  orchestrator にしか使われていなかった場合(現時点で該当は無い)
- **未回答時の既定**: AI推奨のとおりにする
- **波及**: 機能 27 本 / 機能要件 9 件(69 条項)/ 非機能要件 4 件 / 契約 2 件 / モジュール 4 件
- **間違えたときの戻し方**: フェーズ2 の変更指示を書く時点で、残った層に orphan の参照が出れば
  気づく(`check-changeset.py --ssot` の CS11 参照実在が拾う)。境界を引き直して変更指示を
  書き直せば戻る(実装はまだ触っていない)
- **過去の回答**: なし(decisions / 決定シート写し / feedbacks / histories 走査済み)

**★あなたの記入**:

### 2. 範囲の境界 —「通知フック(`MOD-hooks`)を含めるか」

- **場所**: `docs/02-design/system.md:63` / `docs/02-design/relations.md:74`〜`:75` /
  `scripts/save_prompt.sh` / `scripts/sendslackmsg.sh`
- **明確にしたいこと**: 今回削除するのはどれか。残すものを名指し
- **AI推奨**: **今回は hooks も削除する**。理由: `MOD-hooks` の対応要件は `FR-orch-07` だけで
  (`system.md:63`)、それを消すと**要件の裏付けを1つも持たない実装**が残る。残すには 00 に
  「エージェントの通知」という新しい要求を起こす必要があり、それは「orchestrator を無かったことに
  する」という本タスクの範囲を超えて**新機能を作る**ことになる(原則4「上流に無いものを作らない」)。
  下流の代償: **コンテナ内の Claude Code が終わったときの Slack 通知が無くなる**(利用者から
  見える振る舞いの減少)。崩れる条件: この Slack 通知を orchestrator と独立に使い続けたい場合。
  そのときは残す判断が正しく、`RQ-env-*` 配下に新しい要求として起こす別タスクになる
- **未回答時の既定**: AI推奨のとおりにする(hooks も削除する)
- **波及**: 機能 2 本 / `NFR-sec-03`(削除)/ `NFR-avail-03` の「通知」/ `SR-*` の外部依存 Slack /
  `logging.md` の「通知の送信失敗」行 / `docs/issues/013` / `docs/issues/067`
- **間違えたときの戻し方**: 削除するのはスクリプト2本と `Dockerfile.claude` の3行、
  `MODULE-hooks-*` 2件だけなので、`git revert` で全て戻る。気づくのは Slack 通知が来なくなった
  最初のセッション
- **過去の回答**: なし(decisions / 決定シート写し / feedbacks / histories 走査済み)

**★あなたの記入**:

### 3. 範囲の境界 —「抽出物と過去の記録を含めるか」

- **場所**: `docs/orch/00.md` `docs/orch/01.md` `docs/orch/02.md` / `docs/histories/` / `docs/feedbacks/`
- **明確にしたいこと**: 「全く無かったことにする」が SSOT の外まで及ぶか
- **AI推奨**: **及ばない(残す)**。理由: `docs/orch/` は直前のコミット `fce4552` が
  「別プロジェクトへ分離する前段」として意図して作った抽出物で、消すと分離の素材が失われる。
  `docs/histories/` と `docs/feedbacks/` は**過去に何が起きたか**の記録であり、
  SSOT(現在の姿)ではないので原則1 の対象外。今回の削除自体も histories に1件記録する。
  下流の代償: リポジトリに orchestrator という語が `docs/orch/` と `docs/histories/` に残る。
  崩れる条件: 「リポジトリ全体から語を消したい」が目的だった場合
- **未回答時の既定**: AI推奨のとおりにする(残す)
- **波及**: なし(SSOT の検証対象外。`check-changeset.py --ssot` の走査対象にも入らない)
- **間違えたときの戻し方**: 後から `git rm` するだけで消せる(依存が無い)。逆に消してから
  戻すのは `git revert` が要る。残す側が可逆性で有利である
- **過去の回答**: なし(decisions / 決定シート写し / feedbacks / histories 走査済み)

**★あなたの記入**:

## 次に問う候補(回答不要。今回載せなかったもの)

- 「ORCHESTRATOR.md」/「`.orchestrator/`」/「worker」/「介入トリガー」

## 論点(概念以外。従来の決定シート)

### 論点 1. `request.md` の目的から並列開発を落とす(00 の意味を変える編集)

- **選択肢**: A. 目的3件のうち「AIオーケストレーターを1体立てる」を削除し、背景の
  「人間が進行管理を兼ねているために並列度を上げられない」も落として、目的を
  「隔離」と「配布」の2件にする / B. 目的の文は残し、`RQ-orch-01` だけを削る
- **AI推奨**: **A**。理由: B は「やりたいこと」が要求表に無い状態を作り、
  `functional.md:531` の要求カバレッジ確認が空を指す行を持つことになる。00 は
  「今のシステムが何のためにあるか」を述べる層なので、実装が無いものを目的に残せない。
  下流の代償: このプロダクトの説明が「複数プロジェクトを並列に進める」から
  「レビュー前コードをホストから隔離し、同一構成を配布する」へ縮む。README の①②の②も消える。
  崩れる条件: orchestrator を別プロジェクトとして復活させ、このリポジトリから使う構成にする場合
  (そのときは `docs/orch/` を起点に新しい要求を起こす)
- **未回答時の既定**: AI推奨のとおりにする
- **根拠(上流)**: `docs/00-requests/request.md:20`〜`:35`(背景と目的)。この文書に上流は無い
- **根拠(同層)**: `docs/00-requests/request.md:59`〜`:68`「やらないこと」— 4・5 が
  orchestrator 専用の除外であり、同層の先例として「目的が消えれば除外も消える」形になっている
- **根拠(下流)**: `relations-query.py --impact orchestrator/main.go` で要件 3 件・契約 1 件。
  `RQ-orch-01` からは `FR-orch-01`〜`09` の 9 件(69 条項)が降りている(`functional.md:539`)
- **間違えたときの戻し方**: `docs/orch/00.md` が `RQ-orch-01` と `D0-orch-01`〜`18` の**原文**を
  保持しているので、書き戻す材料は失われない。気づくのは「並列開発をやりたい」と再び言うとき
- **過去の回答**: なし(decisions / 決定シート写し / feedbacks / histories 走査済み)

**★あなたの記入**:

### 論点 2. 「やらないこと」4・5 の削除と番号の扱い

- **選択肢**: A. 行 4(ブレインストーミングの自動化)と行 5(完了基準の自動タスク化)を削除し、
  1〜3 の番号は動かさない / B. 削除して 1〜3 のまま詰め直す(結果的に同じ)/
  C. 行は残し「orchestrator が無いので該当しない」と書く
- **AI推奨**: **A**。理由: 4・5 はどちらも orchestrator の機能に対する除外なので、
  対象が消えれば除外そのものが意味を失う。C は「存在しない機能について、やらないと宣言する」
  という空の記述を SSOT に残す。1〜3 の番号を動かさないのは、`acceptances.md:110`〜`:113` と
  `docs/01-requirements/system.md:33`(SR-05)が「やらないこと 1 / 2」を番号で参照しているため。
  下流の代償: 番号 4・5 が欠番になる(`FR-*` の条項 ID と同じ扱いで、欠番は埋めない)。
  崩れる条件: 「やらないこと」に新しい行を足すとき(そのときは 6 から振る)
- **未回答時の既定**: AI推奨のとおりにする
- **根拠(上流)**: `docs/00-requests/request.md:59`〜`:68`
- **根拠(同層)**: `docs/01-requirements/functional.md:64`「条項 ID は一度振ったら動かさない:
  欠番を埋めない・並べ替えない」— 同じキットの中の先例
- **根拠(下流)**: `acceptances.md:110`〜`:113`「対象外とするシナリオ」4 行のうち 2 行
  (作業者ごとの隔離 / 信頼できない第三者のコード)が 1・2 を参照し、残り 2 行が 4・5 を参照して
  一緒に消える。`system.md:33`(SR-05)が 2 を参照して残る
- **間違えたときの戻し方**: 表の 2 行を書き戻すだけ。気づくのは 00 を読み直したとき
- **過去の回答**: なし(decisions / 決定シート写し / feedbacks / histories 走査済み)

**★あなたの記入**:

### 論点 3. 対象の消えた `docs/issues/` の扱い

- **選択肢**: A. orchestrator / hooks / 自己検証題材だけを対象とする issue をファイルごと削除し、
  削除した ID を histories に一覧する / B. 全て残す / C. 残すが `type` を `future` に変える
- **AI推奨**: **A**。理由: issue は「まだタスク化していない**現存する**問題」を置く場所であり
  (`.claude/directions/issues-pendings.md`)、事象を起こすコードが消えれば問題も消える。
  B を採ると `check-changeset.py --ssot` の CS11(参照実在)が、削除された
  `MODULE-orchestrator-*` を指す `related:` を毎回違反として出し続ける。
  下流の代償: 過去に見つけた欠陥の分析が issue ファイルとしては失われる(histories に ID と
  1行要約だけが残る)。崩れる条件: orchestrator を別プロジェクトで復活させ、同じ欠陥を
  引き継ぎたい場合 — そのときは `git show` で全文を取れる
- **未回答時の既定**: AI推奨のとおりにする
- **根拠(上流)**: `.claude/directions/issues-pendings.md`(issue は現存する問題の置き場)
- **根拠(同層)**: `docs/03-impl/index.md:61` が「実装の欠陥として起票済み 21 件」を
  「`## 既知の制限` から参照されているもの」と定義しており、参照元が消える issue は
  この集計からも自動的に外れる
- **根拠(下流)**: 削除候補は `001` / `003` / `007` / `011` / `012` / `013` / `014` / `015` /
  `021` / `022` / `026` / `033` / `057` / `058` / `059` / `061` / `062` / `063` / `064` /
  `067` / `068` の 21 件(フェーズ2 で1件ずつ本文を読んで確定する。**orchestrator 以外にも
  かかる issue は残して記述だけ直す**)
- **間違えたときの戻し方**: `git revert` でファイルが戻る。気づくのは同じ欠陥を再発見したとき
- **過去の回答**: なし(decisions / 決定シート写し / feedbacks / histories 走査済み)

**★あなたの記入**:

### 論点 4. システム要件 `SR-21` / `SR-22` / `SR-23` / `SR-31` の縮小と削除

- **選択肢**: A. `SR-22`(Go の依存は標準ライブラリに限る。TUI に限り外部ライブラリを許容し
  vendor へ同梱)と `SR-23`(自己検証題材は Python + 自動テスト)を削除し、`SR-21` を
  「docker-proxy は Go で実装し単一バイナリで配布する」へ、`SR-31` を
  「docker-proxy に自動テストがあり、変更時に実行できる」へ縮める /
  B. `SR-22` を「Go の依存は標準ライブラリに限る」だけ残す
- **AI推奨**: **A**。理由: 外部ライブラリを持つ Go モジュールは `orchestrator/` だけで
  (`docker-proxy/go.mod` は依存 0 本)、それが消えると `SR-22` の後半(TUI の例外)は
  対象を失う。前半だけを残す B も成り立つが、**依存を1本も持たない単一モジュールに対して
  「標準ライブラリに限る」と課す制約は、破りようが無いので観測点を持たない**
  (`NFR-ops-04` 第2文が「測らない」と書いたのと同じ理由)。
  下流の代償: 将来 docker-proxy に外部依存を入れたくなったとき、それを止める記述が
  SSOT から消える。崩れる条件: docker-proxy に外部ライブラリを入れる話が出たとき
  (そのときは 00 の決定として起こす)
- **未回答時の既定**: AI推奨のとおりにする
- **根拠(上流)**: `docs/00-requests/decisions/orch.md:180`〜`:186`(`D0-orch-14`。
  `SR-22` の例外の唯一の根拠であり、本タスクで削除される)
- **根拠(同層)**: `docs/01-requirements/system.md:50`〜`:54`。同じ表の `SR-20`(Bash)と
  `SR-24`(マルチステージ)は orchestrator に依存しないので残る
- **根拠(下流)**: `docs/02-design/system.md:393`〜`:395`(カバレッジ表の `SR-21` / `SR-22` /
  `SR-23` の行)、`docs/02-design/environments.md:56`(`go test -mod=vendor`)、
  `docs/03-impl/tests/strategy.md`
- **間違えたときの戻し方**: 表の行を書き戻すだけ。気づくのは docker-proxy に依存を足すとき
- **過去の回答**: なし(decisions / 決定シート写し / feedbacks / histories 走査済み)

**★あなたの記入**:

### 論点 5. 「利用者向けの出力は日本語」の行き先(要件へ再ホームするか、設計判断に留めるか)

<!-- 2026-08-08 フェーズ2 の /doc-check で追記した。検査 A4(層の帰属)と独立レビュー docs の
     指摘 C11 が同じ箇所を別の角度から指した。 -->

- **選択肢**: A. **`NFR-ops-05` として 01 へ新設**し、`02-design/logging.md` はそれを指す /
  B. 02 の設計判断 `DSN-log-03` として書き、01 には持たない / C. どこにも書かない(記述を落とす)
- **AI推奨**: **A**。理由: 「利用者へ向けた文が日本語である」は**外から観測できる約束**であり、
  層の帰属(`.claude/directions/layer-fit.md`)では 01 が持つ。この約束の唯一の要件上の根拠だった
  `FR-orch-08` 受入基準3 が本タスクで消えるため、B にすると**外から見えるものが 02 だけにある**状態、
  C にすると**実装が日本語で出力しているのにどの層もそれを述べていない**状態(原則2 の破れ)になる。
  下流の代償: 非機能要件が 1 件増え、02 のカバレッジ表と 03 のテスト対応表にそれぞれ 1 行増える
  (`docs/03-impl/tests/cli-common.md`。状態は `未検証(テスト未実装)` で、`NFR-ops-02` と同じ
  E2E-01 の実機確認が担う)。崩れる条件: 日本語を読まない利用者が `request.md`「対象ユーザー」に
  加わったとき(そのときは 00 から降ろし直す)。
- **未回答時の既定**: AI推奨のとおりにする
- **根拠(上流)**: `docs/00-requests/request.md`「対象ユーザー」— 「社内の開発者(日本語話者)」。
  **00 に無いものを作ってはいない**
- **根拠(同層)**: `docs/01-requirements/functional.md` の `FR-env-06` 受入基準7
  (`forward` の対象コンテナ未起動時に「日本語のエラーを表示して終了コード 1」)が、
  この約束の一部を既に条項として持っている。`NFR-ops-05` はそれを全体へ広げたもの
- **根拠(下流)**: `docs/02-design/logging.md`「ログレベルの定義と使い分け」がこの文を持ち、
  実装は `claude-dev` の説明・警告・エラーの各行で現に日本語を出している(実機で確認済み)。
  02 のカバレッジ表の割り当ては `MOD-cli-common` / 各 `MOD-cli-*` / `MOD-entrypoint` の 3 系統
- **間違えたときの戻し方**: 気づくのは「英語で出したい出力が出てきたとき」。
  `NFR-ops-05` の行と、02 のカバレッジ 1 行・03 のテスト 1 行を消せば戻る(実装は変えていない)
- **過去の回答**: なし(decisions / 決定シート写し / feedbacks / histories 走査済み)

**★あなたの記入**:

## 委任にしてよいか確認したい項目

なし(標準委任 `DS-01`〜`DS-08` の範囲を超える委任は今回発生しない)。

## 今回 AI が決めたこと(回答不要。開示)

<!-- フェーズ1 の時点では実装判断をしていない。フェーズ2・3 で行使した DS はここへ追記する -->

- (フェーズ1 では無し)

## 方針合意(個別diff承認は行いません)

- 各ドキュメントへの変更方針:
  - `00-requests/request.md`: 目的3件 → 2件、`RQ-orch-01` 行の削除、「やらないこと」4・5 の削除、
    完成イメージの `orchestrate` 段落の削除、対象ユーザー表の orchestrator 記述の削除。
  - `00-requests/terminology.md`: オーケストレーター関連 9 語と「判断に迷いやすい区別」3 行の削除。
  - `00-requests/acceptances.md`: `AC-04` / `AC-05` の削除、対象外シナリオ 2 行の削除。
  - `00-requests/decisions/orch.md`: ファイルごと削除。`sec.md` は `D0-sec-03` を削除、
    `dist.md` は `D0-dist-04` 項5 を書き換え、`env.md` は `D0-env-06` の理由から語を落とす。
  - `01-requirements/functional.md`: `FR-orch-01`〜`09` と `FR-env-12-12` の削除、要求カバレッジ表の更新。
  - `01-requirements/non-functional.md`: `NFR-perf-03` / `NFR-avail-01` / `NFR-sec-03` /
    `NFR-ops-04` の削除、`NFR-avail-03` から「通知」を外す。
  - `01-requirements/usecases.md`: `UC-04` / `UC-05` の削除、シナリオ外要件と AC⇄UC 表の更新。
  - `01-requirements/system.md`: 論点4 のとおり。外部依存表から Slack 行を削除。
  - `01-requirements/decisions/split.md`: `D1-split-01` の件数(34 件 → 21 件)と関連の更新。
  - `02-design/architecture.md`: 構成図・責務表・データの流れ・外部境界から orchestrator を外し、
    `DSN-arch-02` 項3 と `DSN-arch-03` を縮め、`DSN-orch-01` / `DSN-orch-02` を削除。
  - `02-design/system.md`: `MOD-orchestrator` / `MOD-sample-project` / `MOD-cli-orchestrate` /
    `MOD-hooks` の削除(29 → 25 モジュール)、`DSN-mod-06` の縮小、カバレッジ表の該当行の削除、
    テスト戦略と結合テスト対象の更新、`E2E-04` / `E2E-05` の削除、`SCR-02`〜`SCR-06` の削除と
    `DSN-ui-01` / `DSN-ui-02` の書き換え。
  - `02-design/relations.md`: `PLAN-cli-orchestrate` / `PLAN-orchestrator-main` /
    `PLAN-makefile-build-orchestrator` / `PLAN-makefile-orch-sample` /
    `PLAN-makefile-orch-sample-clean` / `PLAN-sample-project-scaffold` / `PLAN-hooks-*` の削除と
    連携図の更新。
  - `02-design/environments.md`: orchestrator の lint / テスト / build 行、`make orch-sample`、
    コールグラフ抽出設定の `internal_roots` と `除外するパス` の更新。
  - `02-design/logging.md`: orchestrator の出力先・追記型ログ 4 種・監視/アラート表の更新、
    `DSN-log-02` の削除。
  - `02-design/contracts/`: `cli-orchestrator.md` と `orchestrator-prompt.md` を削除、
    `cli-container.md` の当事者から `MOD-cli-orchestrate` を外す。
  - `03-impl`: 対象 27 本の `MODULE-*.md` と 4 本の `tests/*.md`、2 本の `contracts/*.md` を削除。
    `features.md`(83 → 56 本)・`index.md`・`environments/images.md`・`tests/index.md` /
    `strategy.md` / `e2e.md` / `makefile.md` を更新。生成物(`callgraphs/` / `feature-graph.md` /
    各 `index.md`)はツールで再生成。
  - 実装: `orchestrator/` / `examples/orch-sample/` / `scripts/orch-sample.sh` /
    `scripts/save_prompt.sh` / `scripts/sendslackmsg.sh` を削除。`Makefile` / `claude-dev` /
    `claude-dev-mac` / `.devcontainer/Dockerfile.claude` / `.gitignore` / `scripts/vm-healthd.sh` /
    `README.md` / `INDEX.md` を修正。
- 変更指示を書き終えた時点で差分サマリを提示します。個別のdiff承認は取りません。

**★あなたの記入**(異議のある方針だけ書いてください。空欄 = 全方針に合意):

## 記入完了

**★あなたの記入**(記入を終えたら日付を書いてください。例: 2026-08-07): 2026-08-08
<!-- ★ 一括回答と同じく、2026-08-08 の人間の指示(「いちいち質問しなくて良いから、一気に
     やりきってほしい」)を AI が転記したものである。 -->
