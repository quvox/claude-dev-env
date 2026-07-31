---
slug: codex-landlock-sandbox
layer: task
title: コンテナ内 codex を全経路で使える状態にする（landlock 既定＋不足鍵補完＋QA 方針）
date: 2026-07-31
updated: 2026-07-31
phase: 実装
source:
  - docs/03-impl/entrypoint.md
  - docs/03-impl/e2e.md
history:
  - docs/histories/2026-07-31-codex-landlock-default-config.md
---

# タスク:コンテナ内 codex を全経路で使える状態にする

## 前提（ゲート状況の記録）

`/implement` のゲートは「対象 03-impl と source チェーンが全て verified」を要求するが、着手時点で
2 件が未検証だった。停止せず着手した判断と根拠を残す。

| 文書 | 状態 | 剥落理由 | 判断 |
|---|---|---|---|
| `03-impl/entrypoint.md` | 未検証 | **②実装が未了**（コードは 2 鍵生成のまま）。①文書の誤りではない | ゲートの趣旨は「未検証の仕様から実装しない」であり、上流 00/01/02 は全て verified、剥落理由が本作業の対象そのもの。`docs/knowledge/docs-ahead-of-code-deadlocks-doc-check.md` と feedback/log.md [5][7][11]（人間が是認済み・今回で 4 回目）に沿って着手する |
| `03-impl/e2e.md` | 未検証 | E2E-1〜6 が再現可能な実施手順を持たない（重大度 高・未解決） | 剥落理由は本作業と無関係で、別作業 `e2e-procedures` が所有する。本作業が実装する entrypoint の挙動は e2e.md の解決に依存しない。ただし**タスク4 で e2e.md を触る場合は当該指摘を悪化させないこと**に限定する |

上流（`02-design/system.md` 1.9.0 / `01-requirements/core.md` 1.9.0 / 00 層 4 文書）はいずれも verified。
未決点はゼロ（決定シート #1 の人間回答で closure 済み）。

## 目的

codex 既定の bubblewrap サンドボックスがコンテナ内で起動できない問題に対し、user namespace を
必要としない legacy landlock バックエンドを既定設定で有効化し、`--sandbox read-only` 等を明示指定
する呼び出し（監査エージェント等）でも codex が動く状態にする。併せて既存 `config.toml` への
不足鍵補完と QA レーンのサンドボックス方針を確定する。

## 影響範囲(closure)

| 層 | ファイル | 変更の要点 | 予定バンプ |
|---|---|---|---|
| 00 | docs/00-requests/decisions.md | D-27 ⑥ を landlock 採用・不足鍵補完・QA 方針で書き換え | MINOR |
| 00 | docs/00-requests/glossary.md | 用語「Codex サンドボックス」に 2 バックエンド（bwrap/landlock）を反映 | MINOR |
| 00 | docs/00-requests/acceptance.md | AS-6 に読み取り専用での作業依頼の期待結果・不合格条件を追加 | MINOR |
| 01 | docs/01-requirements/core.md | 要件12: 12-5 既定 3 鍵、12-6 不足鍵補完、12-9 明示 sandbox 指定時の成功を追加 | MINOR |
| 02 | docs/02-design/system.md | 判断5 差し替え、データモデル、テスト戦略備考、E2E-6 | MINOR |
| 03 | docs/03-impl/entrypoint.md | 手順10 の生成内容と不足鍵補完、データアクセス表、テスト対応表 | MINOR |
| 03 | docs/03-impl/e2e.md | E2E-6 に landlock 疎通確認、既知の制限を更新 | MINOR |
| steering | docs/_steering/tech.md | 「Codex実行設定」の QA 方針行を更新 | （版なし） |
| 03(差分検証) | cli.md, cli-mac.md, devcontainer.md, ghcr-workflow.md, makefile.md, docker-proxy.md, firewall.md, portsync.md, hooks.md, orchestrator.md, sample-project.md, container-tools.md, vm-mode.md | system.md のバンプによる失効。本文変更なしの見込み | なし |

## 決定シート(回答済み)

| # | 論点 | 回答 | 反映先 |
|---|---|---|---|
| 1 | 既定 config.toml に landlock フィーチャを入れるか | 追加する | decisions.md D-27 ⑥（決定事項） |
| 2 | 既存 config.toml の扱い | 不足鍵だけ追記 | decisions.md D-27 ⑥ / core 12-6 |
| 3 | QA レーン（workspace-write が動かない） | danger-full-access で codex QA を許す。理由「コンテナ自体が隔離空間だから、これ以上の隔離は不要」（D-1 の一貫適用） | tech.md「Codex実行設定」＋ docs/knowledge/（プロセス設定であり製品要件ではないため decisions.md には書かない） |
| 4 | 版更新時の regression 検知 | E2E-6 に疎通確認を追加 | system.md E2Eシナリオ一覧 / 03-impl/e2e.md |
| 5 | 不足鍵補完の対象鍵 | A: 3 鍵すべて（不在時のみ補完、既存の鍵と値は不変） | core 12-6 / entrypoint.md 手順10 |
| 6 | 起動時に疎通確認を走らせるか | A: 入れない（E2E-6 と tech.md の運用メモで担保） | 記載不要（採らない案として system.md 判断5 の却下案に記録） |
| 7 | CODEX_VERSION のピン留め | A: 現状維持（CI が latest を解決してピン留め） | 変更なし（D-27 ② のまま） |

## 未決点

| # | 対象 | 未決点 | 帰着 | 状態 |
|---|---|---|---|---|
| 1 | entrypoint（タスク2 不足鍵補完） | 既存 `config.toml` へ不足鍵を追記するときの TOML 上の配置規則 | **人間判断で closure（2026-07-31、決定シート #1 = 案A「TOML 構造を尊重」）。`03-impl/entrypoint.md` 手順10 に記載済み・feedback/log.md [17]** | **closure 済み** |

> 未決点は残っていない（`/implement` の入口条件を満たす）。
> 検出元: `/doc-check full`（2026-07-31）の独立監査 `readiness`（Codex）。Claude 自身のパス1では未検出。

## 調査メモ

| # | 調べたこと | 判明した事実(根拠) | 実装での使いどころ |
|---|---|---|---|
| 1 | 既定 config.toml 生成箇所 | `scripts/entrypoint-claude.sh:243-254`（`[ ! -f "$LOCAL_CODEX/config.toml" ]` の分岐で 2 行を `printf` し `chown`） | ここに不足鍵補完を足す |
| 2 | landlock 有効化の書式 | `codex exec/sandbox` の `--enable <FEATURE>` は `-c features.<name>=true` と等価（`codex exec --help`）。config.toml では `[features]` テーブルに `use_legacy_landlock = true` | 生成する 4 行目以降の書式 |
| 3 | config.toml 経由で効くか | 新規コンテナで `[features] use_legacy_landlock = true` を置くと `codex sandbox -- /bin/true` が exit 0、`touch /tmp/x` は Permission denied（2026-07-31 実測） | 12-9 の実装根拠 |
| 4 | 監査経路の動作 | `codex exec -s read-only` はフラグ付きで読み取り成功・書き込み拒否・名前解決不可。`codex exec review --uncommitted -c sandbox_mode="read-only"` はフラグ付きで P1 指摘、無しは bwrap エラーで無指摘（2026-07-31 実測） | E2E-6 の確認観点 |
| 5 | workspace-write の可否 | landlock 経路でも書き込み失敗（apply_patch・シェル書き込みとも）。QA は danger-full-access が必要（2026-07-31 実測） | 決定シート #3 の根拠 |
| 6 | 失敗の見え方 | いずれの失敗でも `codex exec` の終了コードは 0。判定は最終メッセージと成果物で行う | E2E-6 の合否判定方法 |
| 7 | deprecation | 起動時に「`[features].use_legacy_landlock` is deprecated and will be removed soon」と警告。`CODEX_VERSION` は build 時に latest 解決（`.devcontainer/Dockerfile.claude:510,538`） | 撤去時の退避（添付方式）を 03 の既知の制限へ |
| 8 | TOML 鍵の検出 | 生成する 3 鍵はいずれも `^\s*<key>\s*=` の形。`[features]` はテーブル見出しなので鍵の有無は `use_legacy_landlock` 行の有無で判定できる | 不足鍵補完の実装方法 |
| 9 | 現行コードの実装状態 | `scripts/entrypoint-claude.sh:243-255` は **2 鍵のみ生成**（`sandbox_mode`/`approval_policy`）。250 行のコメントに「既存ファイルは内容を読まず一切変更しない」とあり、不足鍵補完は**未実装**。3 鍵化と補完はタスク1・2 で新規に書く（2026-07-31 `/doc-check full` の check B で確認） | タスク1・2 の着手点 |
| 10 | 追記位置の TOML 上の制約 | TOML はテーブル見出し以降の鍵が当該テーブルに属するため、単純な末尾追記はトップレベル鍵の意味を変えうる（未決点 1 の技術的根拠） | タスク2 の実装方式 |

## 質問キュー

なし（E2E 手順の再現性の指摘は決定シート #2 の回答により **別作業 `e2e-procedures` として起票**した。
本作業の範囲外。`03-impl/e2e.md` は当該作業が終わるまで合格証なしのまま）

## タスク

- [x] 1. entrypoint の既定 config.toml 生成を 3 鍵（`sandbox_mode` / `approval_policy` /
      `features.use_legacy_landlock`）に拡張する
      _要件: core/12-5_ _Boundary: scripts/entrypoint-claude.sh_ _Depends: なし_
- [x] 2. 既存 `config.toml` に対する不足鍵補完を追加する（既存の鍵と値は書き換えない・冪等）。
      **追記位置は entrypoint.md 手順10 の配置規則に従う**——トップレベル 2 鍵は最初のテーブル見出しの直前、
      `use_legacy_landlock` は `[features]` 見出しの直後（無ければ末尾に見出しごと）、位置を特定できない
      TOML は何も書かず警告のみ
      _要件: core/12-6_ _Boundary: scripts/entrypoint-claude.sh_ _Depends: 1_
- [x] 3. 実機確認（12-5/12-6/12-9 と E2E-6 の landlock 疎通確認）
      _要件: core/12-5,12-6,12-9_ _Boundary: 実機_ _Depends: 2_
- [x] 4. 03-impl（entrypoint.md のテスト対応表 / e2e.md）を実装結果に同期し、history の affected を追記

## Definition of Done

- [ ] 上記タスクの全チェックが完了している
- [ ] 「未決点」セクションが空である
- [ ] `go vet ./...`（各 Go モジュール）— 本作業は Bash のみのため「対象外: Go 変更なし」で可
- [ ] `cd docker-proxy && go test ./...` / `cd orchestrator && go test -mod=vendor ./...` が全パスする
      （本作業は Bash のみだが回帰確認として実行する）
- [ ] 受け入れ基準 12-5 / 12-6 / 12-9 の実機確認が完了している（判定は成果物と終了コードで行い、
      codex 自身の応答を根拠にしない）
- [ ] 影響する E2E シナリオ: E2E-6（landlock 疎通確認 2 コマンド ＋ 既存の認証共有・シェル実行成功）。
      デバイス認証部分は無人自動化不可のため既存確認を援用し、追加観測点のみ再実施する
- [ ] 独立QA(`/codex-qa`): 本作業の対象がコンテナ初期化シェルで UI を持たないため「対象外: UI なし・
      E2E は実機確認方式」と記す。ただし codex QA の方針変更（決定シート #3）を tech.md に反映済みであること
- [ ] `docs/03-impl/entrypoint.md` と `docs/03-impl/e2e.md` が実装結果と一致している
- [ ] history エントリ `docs/histories/2026-07-31-codex-landlock-default-config.md` の affected に
      今回更新した全ドキュメントが `change:` 一行付きで記録されている
- [ ] `/doc-check` を 1 回実行し、自分の修正が原因の失効が残っていない
- [ ] 「質問キュー」が解消済み（なし。E2E 手順は別作業 `e2e-procedures` へ移送済み）
- [ ] 「調査メモ」の各行を振り分け済み
- [ ] 本作業の 質問/修正/委任判断 が `docs/feedback/log.md` に記録されている

## 進捗メモ

- 2026-07-31: フェーズ1（決定）完了。決定シート 7 件すべて回答済み。
- 2026-07-31: フェーズ2 の降下完了。closure の 7 文書を 00→03 の順に編集し、各 1 回だけバンプ
  （decisions 1.7.0 / glossary 1.3.0 / acceptance 1.3.0 / core 1.9.0 / system 1.9.0 /
  entrypoint 1.7.0 / e2e 1.4.0）。steering(tech.md) の QA 方針行も更新。history エントリ
  `2026-07-31-codex-landlock-default-config.md` を作成し、先行エントリ
  `2026-07-31-codex-audit-attached-mode-in-steering.md` に方針が置き換わった旨を追記。
  feedback/log.md に質問 3 件（[12][13][14]）、knowledge に
  `container-is-the-only-isolation-boundary-for-agent-qa.md` を追加。
- 2026-07-31: `/doc-check full` 実施。独立監査は Codex 9 レンズ（初回 00/01/02/03＋readiness、
  最終 A／B+C+D、修正後の絞り込み再監査 2 回）。結果: **00/01/02 と 03-impl 13 件は PASS**。
  `03-impl/entrypoint.md` は **check B（03-impl⇄コード）で不合格**＝合格証を剥がした。剥落理由は
  「②実装が未了」（コードは 2 鍵生成のまま・不足鍵補完なし）であって①文書の誤りではない
  （`docs/knowledge/docs-ahead-of-code-deadlocks-doc-check.md` と同型・4 回目）。
  `03-impl/e2e.md` も合格証なし（下記）。
  修正した点: core.md UC-6 に AS-6 の 2 操作（通常依頼・読み取り専用依頼）をフロー追加／system.md の
  カバレッジ表の `e2e` 表記・「期待バージョン」・core/11 の担当を明確化／entrypoint.md 運用メモの
  自己矛盾（「存在する限り触らない」）を修正／cli.md のテスト対応表に欠けていた 4 基準の行を追加
  （1.8.0→1.9.0）／portsync.md の「等」を具体化（1.0.0→1.0.1）／tech.md「Codex実行設定」の
  監査 vs QA のサンドボックス方針の自己矛盾を解消。history は
  `2026-07-31-doc-check-full-uc6-flow-and-e2e6-procedure.md`。
  **未決点 1 件が新規に発生**（既存 config.toml への追記位置の TOML 規則。決定シート #1）。
  `03-impl/e2e.md` も合格証なし（E2E 手順が再現不能という重大度 高 の指摘が未解決。質問キュー #1）。
  **次は決定シート #1・#2 の回答（または既定の適用）→ フェーズ3（`/implement`）で
  `scripts/entrypoint-claude.sh` を修正 → 最後に `/doc-check` で entrypoint.md を再検証して循環を閉じる。**
- 2026-07-31: フェーズ3（`/implement`）。タスク1〜4 完了。
  - コード: `scripts/entrypoint-claude.sh` に `ensure_codex_config()` を実装（commit acfdc62）。
    既定 3 鍵生成＋不足鍵補完。判定・追記とも awk（mawk 前提）、書き戻しは `cat tmp > 本体` で
    所有者/パーミッション保持、失敗時は元ファイル温存＋警告のみ、`|| true` で起動を止めない。
  - 検証: ホスト側の関数単体ハーネス 12 ケース（配置規則・冪等・利用者設定保持・TOML 妥当性を
    `tomllib` で確認）＋ `claude-dev-claude:latest` 上の実機確認で 12-5 / 12-6 / 12-9 を実施。
    Go 回帰テスト（docker-proxy / orchestrator）も green。
  - 03-impl 同期: entrypoint.md のテスト対応表 3 行を「実施済み・観測内容」へ、手順10 にドット記法・
    インラインテーブルの判定理由、実装上の判断に mawk 前提と書き戻し方式を追記。e2e.md の E2E-6 を
    config 経由（フラグ不要）が本体になるよう更新（commit 7edd5f9）。
  - 調査メモの振り分け: 10 行中 9 行は実装・03-impl・tech.md に既収載か陳腐化のため破棄。row 10
    （TOML の追記位置の罠）のみ `docs/knowledge/append-missing-defaults-must-respect-file-structure.md`
    へ昇格。mawk 前提は steering ではなく entrypoint.md の実装上の判断に置いた（steering の軽量性テスト）。
  - **残: 独立レビュー（codex diff）の裁定 → 版バンプ → `/doc-check` 再認証 → DoD 検証。**
