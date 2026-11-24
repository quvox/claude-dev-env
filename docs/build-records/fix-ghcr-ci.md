---
slug: fix-ghcr-ci
state: awaiting-verify
critical: false
origin: human-report
issue: なし
started: 2026-11-24T23:25:25+09:00
updated: 2026-11-25T00:55:00+09:00
commit: d929a715fc9e004e110334fbeb1ff46dc8bb1176
summary: 日次ビルド(GHCR)の arm64 の claude-vnc が、Playwright の Chromium の置き場の名前が変わったため見つけられずに失敗し続けていたのを直す
---

# fix-ghcr-ci — 日次ビルド(GHCR)の失敗の原因究明と修正

## 目的・やらないこと

- 目的: 人間の要望(2026-11-24「github actionsでエラーが出ている。原因を究明して、解決して」— `.claude/missions/2026-11-24-fix-ghcr-ci/requests.md`)に従い、ワークフロー「Build and push images to GHCR」の失敗の原因を確かめて直す。
- やらないこと: agy の導入方式の変更(版の解決と導入のあいだに新版が出たときの失敗は `docs/03-impl/environments/images.md` の落とし穴の表に「再実行で解決」として既に載っている受容済みの事象であり、方式を変えるのは `D0-dist-07` の判断の変更になる)。ワークフロー定義の変更。docker-proxy のイメージ。

## 影響範囲(closure)

- .devcontainer/Dockerfile.claude
- docs/03-impl/environments/images.md

## 作業コミットに入れた入力

- なし

## 主張

- 触ったモジュールのテスト: green(ビルド定義に自動テストは無い。代わりに Dockerfile から2つの RUN の本体をそのまま抜き出し、`ubuntu:24.04` の中で実物の Playwright の置き場(amd64 = 手元で `npx -y playwright@latest install chromium` した `chromium-1255/chrome-linux64/`、arm64 = CI と同じ配布 zip を展開した `chromium-1255/chrome-linux-arm64/`)をマウントして実行 → 修正前 `old pw-arm64 gui: ERROR: GUI 用 Chromium が見つかりません（Playwright Chromium 未導入） rc=1` / 修正後 `new pw-arm64 gui: rc=0 exec "/home/dev/.cache/ms-playwright/chromium-1255/chrome-linux-arm64/chrome" "$@"`・`new pw-arm64 headless: rc=0`・`new pw-empty headless: … rc=1`)
- lint / build: green(`docker buildx build --check -f .devcontainer/Dockerfile.claude .` → `Check complete, no warnings found.` / 実際のワークフロー: `gh workflow run ghcr-images.yml --ref work/2026-11-24-fix-ghcr-ci` → run 45425605050 `success`(prepare・build 6本・merge 3本がすべて success。agy は解決・導入とも 1.5.16。公開タグ `202611250026` と `latest`))
- 資格情報の混入検査(secret_scan): 未設定(このリポジトリには `tests/` の宣言ファイル自体が無い。埋めるのはテスト基盤を入れるタスク)
- 版がビルドと揃った環境で走ったか: 未宣言(`02-design/environments.md` に版の固定の見出しが無い)。見比べられた範囲では一致 — 最終の確認は配布物を作るワークフローそのもので行った。手元の再現は Playwright の版(chromium v1255)を CI のログと一致させた
- 外部挙動の変化: あり(後方互換)— arm64 の配布イメージでヘッドレス用ランチャー `chromium-browser` と `CHROME_PATH` 等が再び入る。日次ビルドが再び公開できるようになった
- 認証・決済・不可逆・個人情報・監査への接触: なし
- E2E・全件テスト・ブラウザQA: 実施していない(/verify-tests に委ねる — 及第ライン)

## 基本要件の点検

- R1: BR-01 / BR-03 / BR-05 / BR-06 / BR-07 / BR-09 / BR-10 / BR-11 / BR-13 — このタスクはイメージのビルド定義の中で、導入済みの Chromium の実行ファイルを探す条件だけを広げる。アカウント・識別子・不可逆な操作・秘密の生成・認可・秘密の突き合わせ・ブラウザからの状態変更・保存先・画面のどれも作らず変えない

| ID | 判定 | 理由 | 落とし先 |
|---|---|---|---|
| BR-01 | 非該当 | R1 | — |
| BR-02 | 非該当 | 利用者や外部から値を受け取る経路を足さず、変えない。探索の対象はビルド中に同じイメージの中へ導入したディレクトリである | — |
| BR-03 | 非該当 | R1 | — |
| BR-04 | 非該当 | プロセスの外と値をやり取りする経路を足さず、変えない(探索結果をランチャーへ書く既存の経路はそのまま) | — |
| BR-05 | 非該当 | R1 | — |
| BR-06 | 非該当 | R1 | — |
| BR-07 | 非該当 | R1 | — |
| BR-08 | 非該当 | 探索結果のパスをランチャーへ `printf '%s'` で書く既存の出し方に触れない。新しい出力先を足さない | — |
| BR-09 | 非該当 | R1 | — |
| BR-10 | 非該当 | R1 | — |
| BR-11 | 非該当 | R1 | — |
| BR-12 | 非該当 | 成果物の起動の入口にも版の名乗り(イメージの版ラベル)にも触れない | — |
| BR-13 | 非該当 | R1 | — |

## 決定シート(回答済み)

- 論点1(修正をマージ前に作業ブランチから実際のワークフローで確かめるか。手動起動は全部通れば `latest` を公開する)— 回答 2026-11-25(このウィンドウ): 「起動していいよ」→ A(作業ブランチを指定して手動起動する)を採る。概念の明確化は「曖昧さなし」1件のみ。

## 質問キュー(出口のシートの種)

- なし(論点1は回答済み — 決定シート(回答済み)へ転記した)

## 調査メモ

- check-ssot.py docs の凍結: `NG 違反 38 件`(すべてクロージャの外。images.md は 0 件)。手を付けない。
- relations-query.py --impact .devcontainer/Dockerfile.claude / .github/workflows/ghcr-images.yml: 機能 0 / 要件 0 / 契約 0 / テスト 0(ビルド定義は relations の外)。
- `gh run list --workflow "Build and push images to GHCR"`: 直近 40 回(2026-10-15〜2026-11-24)がすべて failure。
- 失敗B(恒常): 直近の各回で `build (claude-vnc, … arm64 …)` が `#44 0.040 ERROR: GUI 用 Chromium が見つかりません（Playwright Chromium 未導入）`(run 45323407077 ほか 45084810094 / 44962174691 / 44648621234 / 43999325284 / 43649231182 / 43529528445 で同一)。
- 失敗Bの原因: 同じ run の arm64 のログ `#20 12.11 Chrome for Testing 159.0.8154.6 (playwright chromium v1255) downloaded to /home/dev/.cache/ms-playwright/chromium-1255`、取得元 `…/builds/cft/159.0.8154.6/linux-arm64/chrome-linux-arm64.zip` — arm64 の展開先が `chrome-linux-arm64/` になった。探索条件は `.devcontainer/Dockerfile.claude:244` と `:393` の `-path "*/chrome-linux/chrome" -o -path "*/chrome-linux64/chrome"` で、これに当たらない。
- 失敗Bの副作用(黙った欠落): `:244`(ヘッドレス用ランチャー `chromium-browser` と `CHROME_PATH` 等の環境変数)は見つからないと何もせずに通るので、arm64 の claude / claude-vnc の両イメージでヘッドレス用ランチャーが黙って欠けていた。
- 失敗A(本日だけ): run 45323407077 の claude / claude-vnc の amd64・arm64 の4本が `agy の版が指定と一致しません（指定 1.5.15 / 導入 1.5.16）`。前日までの回には現れない。2026-11-24 23:2x 時点の配布元の manifest は amd64 / arm64 とも `"version": "1.5.16"`(15 回引いて 15 回とも同じ)。prepare(04:01 頃)の解決と導入(04:08〜04:13)のあいだに新版が出た事象で、`docs/03-impl/environments/images.md:232` の落とし穴の行が既に名指して「ワークフロー・`make update-claude` を再実行する」としている。

## 進捗メモ(再開点)

- 2026-11-24 23:25 着手。ブランチ確認 OK(`work/2026-11-24-fix-ghcr-ci`)。計器: 課題票 6 / 残務 21 行 / 未検証記録 5 / 未回答シート 1。起点層 03-impl(構造は同じで、実装詳細だけが変わる)。00: 変更なし(目的・範囲・受け入れシナリオに触れない)/ 01: 変更なし(振る舞いの条項は変わらない — arm64 で Chromium を使える状態に戻すだけ)/ 02: 変更なし(構造・契約・選んだ技術に触れない)。シートの問いなし(開示のみ)— シートは作らない。
- 2026-11-24 23:40 `.devcontainer/Dockerfile.claude` の2か所(ヘッドレス用ランチャー・GUI 用ランチャー)の探索条件を `-path "*/chrome-linux*/chrome"` へ広げた。
- 2026-11-24 23:40 [DS-02] ヘッドレス用ランチャーの層も Chromium が見つからなければビルドを止める(GUI 用と揃える)— 理由: 見つからないと黙って通り、arm64 でランチャーと環境変数が欠けたイメージが作られていた / 見直す条件: Chromium を入れない派生イメージを作るとき。開示先 `docs/03-impl/environments/images.md`。
- 2026-11-24 23:45 再現と修正の確認(実物の置き場で): amd64 は手元で `PLAYWRIGHT_BROWSERS_PATH=<scratch> npx -y playwright@latest install chromium`(chromium v1255 → `chromium-1255/chrome-linux64/chrome`)、arm64 は CI と同じ配布 zip `…/cft/159.0.8154.6/linux-arm64/chrome-linux-arm64.zip` を展開(`chrome-linux-arm64/chrome`)。Dockerfile から2つの RUN の本体をそのまま抜き出し、`ubuntu:24.04` の中でその木をマウントして実行: 修正前 = arm64 の GUI 用 `rc=1`(CI と同じ文言)・ヘッドレス用 `rc=0` だがランチャー無し / 修正後 = amd64・arm64 とも両方 `rc=0` で正しいパスのランチャー / 空の木 = 修正後は両方 `rc=1`(止まる)。不具合の再現は修正前に落ち修正後に通ることで足りるので欠陥注入を重ねない。
- 2026-11-24 23:50 影響: `merge` ジョブは `needs: [prepare, build]` で、build の1本の失敗で毎回 skipped — 2026-09-09 以降(最後の success は run 34279906129、2026-09-08)、docker-proxy を含むどのイメージも GHCR へ公開されていない。初回の失敗 run 34404788223 も同じ原因(chromium-1243 の時点で既に当たらない)。
- 2026-11-24 23:58 段4 タスク内整合確認: images.md の記述(ランチャー2つ・`chrome-linux*/chrome` の探索・見つからなければ止める)とコードが一致。差異なし。Dockerfile は relations の外で鏡の文書は無い。`docs/ux/` はクロージャ外。images.md を 1.7.0 → 1.8.0。
- 2026-11-24 23:59 出口のシートを提示(論点1件: 実際のワークフローでの確認をいま作業ブランチから走らせるか)。回答待ち。
- 2026-11-25 00:26 回答を転記しシートを削除。作業ブランチを push し、`gh workflow run ghcr-images.yml --ref work/2026-11-24-fix-ghcr-ci` → run 45425605050 が 00:50 に success(全ジョブ)。images.md を 1.8.0 で確定、履歴 `docs/histories/2026-11-24-fix-ghcr-ci.md`、索引を再生成。残務・課題票で解消するものなし(closure のパスを持つ残務の行は無い)。

## 直さなかった指摘(独立レビュー・探索的QA)

- なし

## 申し送り

- 作業ブランチから公開したイメージ(`202611250026` / `latest`)は、main にこの修正を足した中身である。main へのマージ後、次の定時実行で同じ中身が再公開される。
