---
slug: fix-ghcr-ci
state: building
critical: false
origin: human-report
issue: なし
started: 2026-11-24T23:25:25+09:00
updated: 2026-11-24T23:25:25+09:00
commit: -
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

- (段5 で埋める)

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

- 問いなし

## 質問キュー(出口のシートの種)

- なし

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

## 直さなかった指摘(独立レビュー・探索的QA)

- なし

## 申し送り

- なし
