---
slug: fix-session-list-undercount
state: verified
critical: true
origin: derived
issue: docs/issues/046-bug-list-and-make-targets-undercount-containers-from-older-images.md
started: 2026-08-20T09:23:05+09:00
updated: 2026-08-20T05:43:36+00:00
commit: 0761865
summary: list / make status / make clean の Claude コンテナ列挙を、イメージ由来から「管理ラベル ∪ イメージ ∪ 固定接頭辞」へ改める
---

# fix-session-list-undercount — セッション一覧の数え落としを直す

## 目的・やらないこと

- 目的: `claude-dev list` / `make status` / `make clean` が `--filter ancestor` だけで Claude
  コンテナを引くため、イメージを再ビルド・再取得した後に起動していたセッションを数え落とす
  (`docs/issues/046`)。列挙の根拠を管理ラベルとの論理和に改め、`FR-env-01` 受入基準5 を満たす。
- やらないこと: `stop` / `logout` / `reset` の遊休判定(すでに `claude-dev-net` 由来。issue 045 で
  解消済み)。`make clean` を `D0-env-08` の破壊的操作の定義へ加えるかの裁定(同決定は対象を
  `claude-dev` の3サブコマンドに限っており、本変更は削除対象の方針を変えない)。

## 影響範囲(closure)

- docs/01-requirements/functional.md
- docs/02-design/system.md
- docs/02-design/contracts/cli-container.md
- docs/03-impl/relations/MODULE-cli-list.md
- docs/03-impl/relations/MODULE-makefile-status.md
- docs/03-impl/relations/MODULE-makefile-clean.md
- docs/03-impl/tests/cli-list.md
- docs/03-impl/index.md
- claude-dev
- claude-dev-mac
- Makefile

## 主張

- 触ったモジュールのテスト: **MOD-cli-list / MOD-makefile に自動テストは無い**(`tests: なし(未実装)`。
  方針は `DSN-test-01` / `SR-32`)。代替として新設した実機確認手順(E2E-01 手順10)を Linux で実行:
  `./claude-dev list` → `  NAME:      cdx-t-oldimg` / `  NAME:      cdx-t-img` の2件が出て
  `fwd-cdx-t-9999` は出ない。`make status` → 最終行 `cdx-t-oldimg   Up 6 seconds`。
  **修正前の条件**(`docker ps --filter ancestor=claude-dev-claude --filter ancestor=claude-dev-claude-vnc`)
  → `fwd-cdx-t-9999` / `cdx-t-img` の2件で **`cdx-t-oldimg` を落とす**(欠陥の再現)。
  `make clean` の集合(削除は行わず `docker inspect` で確認)→ `/cdx-t-oldimg` `/fwd-cdx-t-9999`
  `/cdx-t-img` の3件が1回ずつ。後片付け後 `docker ps -a --format '{{.Names}}'` → 0 件。
  **macOS 版(`claude-dev-mac`)は実行機が無く未実施**。`list` 分岐は
  `diff <(sed -n '/^list)/,/^    ;;/p' claude-dev) <(sed -n '/^list)/,/^    ;;/p' claude-dev-mac)`
  で本変更の範囲が完全一致であることを確認した(差分は既存の FORWARD 行の1行だけ)。
- lint / build: `cd docker-proxy && go vet ./...` → 出力なし(終了コード 0)。
  `bash -n claude-dev` / `bash -n claude-dev-mac` → 出力なし(**Bash に自動 lint は無い** — `SR-32`)。
  `make -n status` / `make -n clean` → 解析成功。
  **`make build` は実行していない**: イメージ定義(`.devcontainer/Dockerfile.*`)を触っておらず、
  本変更でイメージの内容は変わらない(変えたのはホスト側のスクリプトと Makefile のレシピだけである)。
- 外部挙動の変化: **あり**。(a) `claude-dev list` / `make status` に、これまで出なかった稼働中
  セッション(管理ラベルを持つが現在のイメージ由来でないもの)が出る。(b) 中継コンテナ(`fwd-*`)が
  セッションの行として出なくなる。(c) `make status` は0件のとき1行で「ありません」と表示する。
  (d) `make clean` が管理ラベルを持つコンテナも消す(**本システムが作ったものだけで、範囲は広がらない**)。
- 認証・決済・不可逆への接触: **あり(critical: true)**。closure の `MODULE-makefile-clean` は
  共有ボリューム(認証を含む)とコンテナとイメージを削除する不可逆な操作である。本変更はその
  **対象の集合**を変えた(削除の手順そのものは変えていない)。
- E2E・全件テスト・ブラウザQA: 実施していない(/verify-tests に委ねる — 収束契約)

## 基本要件の点検

| ID | 判定 | 理由 | 落とし先 |
|---|---|---|---|
| BR-01 | 非該当 | closure にアカウント・権限・認証情報を作る/変える/消す機能が無い(列挙条件の変更のみ。`make clean` は共有ボリュームを消すが、資格情報の主体を作り変える機能ではない) | - |
| BR-02 | 非該当 | closure の3機能はいずれも引数を取らない(`claude-dev list` / `make status` / `make clean`)。外部から値を受け取る経路が無い | - |
| BR-03 | 非該当 | 利用者が値を決める識別子を新たに作らない。コンテナ名の文字種は `FR-env-01` 受入基準18 が既に定め、本変更は触らない | - |
| BR-04 | 該当 | ホストの Docker Engine という外部へ問い合わせ、その応答(コンテナ ID・名前)を列挙に使う | `MODULE-cli-list` / `MODULE-makefile-status` / `MODULE-makefile-clean` の「異常系」— 問い合わせが失敗したときに 0 件と同一視しないこと(`CTR-cli-container`「エラーケース」の既定に従う) |
| BR-05 | 該当 | `make clean` は停止中を含む Claude コンテナ・共有ボリューム・イメージを一括削除する | 既存の確認で充足: `Makefile:263-271` が削除対象の種別を列挙して `read -p` で確認を取る。`D0-env-08` 項3 が名前の列挙を求めるのは `logout` / `reset` の2つで、`make clean` は同決定の破壊的操作の定義に入らない |
| BR-06 | 非該当 | 推測されると困る値を作らない(列挙と表示のみ) | - |

## 決定シート(回答済み)

- 問いなし(開示のみ)

## 調査メモ

- `Makefile:252` / `Makefile:272` / `claude-dev:2169` / `claude-dev-mac:2250` が `--filter ancestor` で列挙している(残る4箇所。`stop` 系は `net_other_running_containers` へ移行済み)
- `claude-dev:1695-1697` が Claude コンテナに `claude-dev.managed=1` / `claude-dev.role=claude` / `claude-dev.project-dir` を付ける。ラベルを付けるのはこの1箇所だけである
- `claude-dev:2099` — `fwd-*` 中継コンテナは `$IMG_CLAUDE` から起動する。したがって `--filter ancestor=claude-dev-claude` に一致し、**現状の `list` と `make status` は中継コンテナをセッションとして表示する**(closure 内の同型の欠陥。本タスクで直す)
- `docs/02-design/contracts/cli-container.md:430-447`「識別の手段は資源ごとに違う」が、Claude コンテナ=管理ラベル / `fwd-` =固定接頭辞 / docker-proxy =固定名 と定めている
- `docs/02-design/contracts/cli-container.md:535-562`「遊休判定」がイメージと管理ラベルを判定の根拠にしてはならないと定める(理由はどちらも数え落とすこと)。ただし節の適用範囲は遊休判定である
- `docs/01-requirements/functional.md:55` — `FR-env-01` 受入基準9 は同じ数え落としを遊休判定について明文で禁じている。受入基準5(list)には同じ但し書きが無い
- `docs/issues/046` の frontmatter に `origin_layer:` が無い(2026-08-04 起票。起点は 01 と裁定した — 受入基準5 に数え方の但し書きを足すため)
- check-ssot.py docs の凍結時点: NG 違反 13 件 / 変更相対語の候補 7 件(本タスク着手前)

## 進捗メモ(再開点)

- 2026-08-20 09:23 closure 確定・構築記録作成。シートは問いゼロ(開示のみ)。`check-sheet.py` が SH4 免除で合格
- 2026-08-20 09:30 [DS-05] 列挙条件を「管理ラベル ∪ イメージ」の和集合にし `fwd-` を除く — 理由: 片方だけではどちらも数え落とす / 見直す条件: ラベル導入前のコンテナがホストから無くなったとき(記録先: `MODULE-cli-list.md`)
- 2026-08-20 09:30 [DS-05] 共通関数を作らず各実装の1箇所に直接書く — 理由: 3ファイルに1箇所ずつでファイルをまたいだ共有ができない / 見直す条件: 同一ファイル内で2箇所以上が必要になったとき(記録先: 同上)
- 2026-08-20 09:32 [DS-02] 問い合わせ失敗を0件と同一視せず不完全である可能性を表示 — 理由: `CTR-cli-container`「エラーケース」の既定 / 見直す条件: 同契約が変わったとき(記録先: 同上)
- 2026-08-20 09:35 01 に `FR-env-01-35`・`FR-env-01-36` を新設(数え方の但し書きと中継コンテナの除外)。02 の契約に「稼働中セッションの一覧の列挙」節、02 のカバレッジ表に2行、02 の PLAN 3行の契約列を更新
- 2026-08-20 09:45 03 の `MODULE-cli-list` / `-makefile-status` / `-makefile-clean` を更新(実装上の判断は表から開示の1行形式へ。既存行は 継続/更新 を付け直した)
- 2026-08-20 09:50 実装: `claude-dev` / `claude-dev-mac` の `list`(各 +15 行)、`Makefile` の `status` / `clean`。`bash -n` と `make -n` は通る
- 2026-08-20 09:55 実機確認(E2E-01 手順10 を新設して実行)。修正前の条件で数え落ちを再現し、修正後に解消することを確認。テスト用資源は後片付け済み
- 2026-08-20 10:00 [DS-01] 手順10 の作り方(1行ビルドで別イメージ ID を作る / `make clean` は流さず集合だけ見る)を `tests/e2e.md` の「テスト設計の判断」へ(理由と見直す条件つき)
- 2026-08-20 10:03 履歴・残務・issue 削除・生成物の再生成。条項参照を条項ID へ揃えた(残務 2026-08-12 を増やさないため)。commit 25c40e6 / 0761865

## override(人間の明示)

- なし(override 不使用)

## 申し送り

- **`docs/pendings.md` は他の作業エージェントと共有している**(本タスクの実行中に別タスクが同ファイルを
  更新している)。追記のときは読み直してから書くこと。
- **`docs/pendings.md` P-006 の「手順10・12」**は 2026-08-07 の表記で、文脈からは 手順8-10・8-12 を
  指すと読めるが断定できないので書き換えていない。**本タスクが E2E-01 に手順10 を新設したので、
  この表記は別の手順とも読めるようになった**(残務に1行を残した)。
- **macOS 版の実機確認が未実施**(実行機が無い)。`list` 分岐は本変更の範囲が両 OS で完全一致である
  ことを `diff` で確認済み。E2E-01 手順10 の macOS 実行は P-006 と同じ条件で待つ。
- `critical: true` は `@triage` の想定(false)を上げたものである。理由は closure に `make clean`
  (認証を含む共有ボリュームの不可逆な削除)が入るため。独立レビューの対象に必ず含めること。
