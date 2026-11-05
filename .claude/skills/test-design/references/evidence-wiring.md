# 試験成果物の配線と、最終状態のスクリーンショット

出典: 配布元のテスト設計スキル3章(**配布元の資料であり、このプロジェクトには無い**)。**試験成果物の置き場と git に入れない規則の正は `.claude/directions/flows.md` §2 である**(同梱されている)。**E2E を書く前にやる。省略禁止。**
出典の docs/ は配布元(systest)の一次資料であり、このプロジェクトには無い。
展開先の実測とレポートの読み方は `tests/e2e/README.md`「試験成果物の出力先」。

## 1. なぜ先にやるのか

**`test-runner` は画面写真・動画・trace を書かない。**(実行結果の要約は自分で書く。撮影するのはテストの側である。)ランナーがするのは `TESTRUNNER_ARTIFACTS` を子プロセスへ渡すことだけで、スクリーンショット・動画・trace の取得は各テストフレームワークの機能である。

**そして Playwright の既定は `screenshot: 'off'` である。**設定を書かなければ1枚も残らない。「撮れているはず」で進めると、落ちた実行の画面が1枚も無い状態が定着する。試験フローの判定はこの証拠を根拠にするので、後回しにしない。

配線しない場合の既定出力先 `test-results/` は実行ごとに分かれないため、**前の実行の証拠を上書きし続ける。** 変更のたびに自動でテストを回す仕組み(CI)を持つプロジェクトでは、回収の対象を `artifacts/` にしていることが多い — **このキットはその仕組みを配らないので、持っているかどうかはプロジェクト次第である**(`02-design/environments.md` と `03-impl/environments/` が正)。

## 2. 出力先の4つの規則

1. **出力先は `TESTRUNNER_ARTIFACTS` の下に統一する** — `playwright.config.ts` の `outputDir` をこの環境変数から組み立てる（`adapters.yml` 側で `--output={artifacts}/e2e` を渡してもよい）
2. **`tests/` の下に書かない** — git に入る場所であり、試験成果物は出力である。明示的に撮るスクショ・保存するレスポンス・ダンプもすべて同じ環境変数の下へ
3. **手元では常時撮影、自動で回す環境では撮らない** — 手元は `screenshot` / `video` / `trace` を `on`（`artifacts/` は gitignore 済みなので容量を気にしない）、自動で回す環境を持つなら `process.env.CI` のような印で分岐して落とす（**その仕組みはこのキットが配るものではない**）
4. **html レポートは `outputDir` の兄弟に置く** — 内側に置くと Playwright が起動を拒否する（`outputDir` は起動時に掃除されるため）。`open: "never"` も省略しない（自動で回す環境で止まる）

```typescript
// playwright.config.ts
const artifacts = process.env.TESTRUNNER_ARTIFACTS
const out = artifacts ? path.join(artifacts, 'e2e') : 'test-results'
const capture = !process.env.CI && process.env.TESTRUNNER_ENV !== 'production'

export default defineConfig({
  outputDir: out,
  use: {
    screenshot: capture ? 'on' : 'off',   // ★ 既定は 'off'。書かないと1枚も残らない
    video:      capture ? 'on' : 'off',
    trace:      capture ? 'on' : 'off',
  },
  reporter: [
    ['list'],
    ['junit', { outputFile: process.env.PLAYWRIGHT_JUNIT_OUTPUT_NAME || path.join(out, 'junit.xml') }],
    ...(capture ? [['html', { outputFolder: out + '-report', open: 'never' }] as const] : []),
  ],
})
```

## 3. 最終状態のスクリーンショットを確実に残す

**最も欲しい1枚は「テストが最後に到達した画面」**である。ここが最も落ちやすい。

### 撮影をテスト本文に書かない（最重要）

```typescript
// 【誤】テスト本文の末尾に置く
test('注文できる', async ({ page }) => {
  await page.getByRole('button', { name: '注文する' }).click()
  await page.screenshot({ path: 'final.png' })      // ← 3つとも間違い
})
```

1. **アサーションが落ちた時点で例外が飛ぶので、この行は実行されない。**証拠が最も必要な場面でだけ消える
2. 相対パスは `artifacts/` の外（プロセスの cwd）に落ち、**まとめて回収する仕組みがあっても拾われない**
3. 書き忘れたテストだけ証拠が無いという、一番困る形になる

**撮影はフィクスチャの teardown に置く。**`use(page)` の後は、テストが失敗しても必ず通る。

```typescript
// tests/e2e/fixtures.ts
export const test = base.extend({
  page: async ({ page }, use, testInfo) => {
    const cap = captureEachStep(page, testInfo.outputPath('steps'), { testInfo })   // 操作ごと
    await use(page)
    await cap.finish(testInfo.title)                                   // ★ 最終状態 + 白紙検査
  },
})
```

`tests/support/screenshots.ts` の `finish()` が、**待機 → `fullPage` で最終状態を1枚 → 白紙検査 → レポートへ添付**までを行う。テスト側は `import` 先を変えるだけで、撮影のコードを1行も書かない。

### 4つの規則

| 規則 | 理由 |
|---|---|
| **パスは `testInfo.outputPath()` で作る** | `outputDir` の下のテスト別ディレクトリに入り、**リトライ・並列ワーカーでも上書きされない**。固定ファイル名は `--repeat 3` で最後の1枚だけが残る |
| **最終状態は `fullPage: true`** | 既定は表示領域だけ。一覧・エラーメッセージが折り返しの下にあると写らない |
| **撮る前に「見えていること」を待つ** | 操作直後は描画途中。`await expect(...).toBeVisible()` を通してから撮る（`animations: 'disabled'` も付ける） |
| **`page` / `context` / `browser` を自分で閉じない** | 閉じた後は撮れない。`chromium.launch()` を自分で書くのも同じ理由で禁止（フィクスチャの `page` を使う） |

### 白紙の1枚で緑になっているテストは、何も検証していない

**真っ白なキャプチャが1枚だけ残って成功しているのは、次の2つが同時に起きている状態である。**

- 画面が描画される前に撮っている（待機条件が無い）
- **そのテストにアサーションが無い**（あれば白紙で落ちる）

つまりこれは撮影の問題ではなく**テストの空洞化**（`/test-design` §5）が可視化されたものである。撮影ヘルパ側で機械的に落とす。

```typescript
// screenshots.ts の finish() が行う検査
const blank = await page.evaluate(() => {
  const b = document.body
  if (!b) return true
  const text = (b.innerText || '').trim()
  const marks = b.querySelectorAll('img,svg,canvas,video,input,button,table,[role]').length
  return text.length < 5 && marks === 0
})
// テストが成功しているのに白紙 → 失敗させる（テストが落ちている場合は上書きしない）
```

- `about:blank` のまま終わっているテストも同じ扱い
- canvas だけの画面・意図的な空状態は、`test.info().annotations.push({ type: 'allow-blank-screenshot', description: '<理由>' })` で明示的に外す（**理由を書かせる。既定で許さない**）

### 白紙のもう1つの原因 — テストがスキップされている

**実行されなかったテストの白紙と、実行して真っ白だった白紙は、画像を見ても区別が付かない。**区別できないと「テストが動いたつもり」で先に進む。だから**証拠の側に刻む。**

| 状況 | 残すもの |
|---|---|
| 実行して成功 | `final.png`（`fullPage`） |
| 実行して失敗 | `final.png`（落ちた瞬間の画面）＋ Playwright の `test-failed-1.png` |
| **スキップ** | **`final-skipped.png` ＋ `SKIPPED.txt`**（テスト名・ファイル・`test.skip` に書かれた理由）。html レポートへの添付名も `final (SKIPPED — 実行されていない)` にする |

`tests/support/screenshots.ts` の `finish()` が `testInfo.status === 'skipped'` を見てこれを行う（**`captureEachStep` に `testInfo` を渡していないと効かない**）。

**スキップは f4-e2e のテスト実行ゲート違反である**（失敗0・**スキップ0**）。白紙を見つけたら、まず `summary.json` の skipped 件数を見る。

```bash
test-runner --gate f4-e2e                      # skipped があればテスト実行ゲートで落ちる
find artifacts -name 'SKIPPED.txt' -exec head -5 {} +
```

- **`test.skip(!process.env.XXX, '...')` の形を安易に書かない。**環境変数が1つ無いだけで**全件スキップのまま緑**になり、`suites.yml` の `min_count`（発見件数と閾値を比較する）もすり抜ける。前提が無いなら**落とす**（`test.fail()` でもスキップでもなく、setup の失敗として扱う）
- スキップや不安定なテストは `/verify-tests` §1・§2 の振り分けと記録に従う。`quarantine.yml` に期限を置いても、課題票や試験区分の判定を代替しない。スキップを足して失敗を隠さない。

### E2E のアサーションは「遷移した」ではなく「何が出ているか」

白紙キャプチャの根本原因はここにある。

```typescript
// 【誤】遷移しただけを確認 — 画面が空でも通る
await page.goto('/orders/123')
await expect(page).toHaveURL(/orders/)

// 【正】その画面に何が出ているかを確認 — 空なら落ちる
await page.goto('/orders/123')
await expect(page.getByRole('heading', { name: '注文詳細' })).toBeVisible()
await expect(page.getByText('注文番号: 123')).toBeVisible()
```

## 4. 書いたら確認する（省略禁止）

タグの確認（`/test-design` §3）と同じ理由で、**配線が効いているかは実行して見るまで分からない。**

```bash
test-runner --suite e2e-full --env local --grep "<テスト名>"

find artifacts -name '*.png' | head                  # 1枚も無ければ配線できていない
find artifacts -name '*.png' -size -5k               # ★ 白紙・ほぼ単色の候補（開いて確認する）
ls artifacts/<run-id>/e2e/<テスト名>/                # final.png / steps/ / video.webm / trace.zip
```

**成功したときだけでなく、意図的に失敗させたときの証拠も見る。**配線に一時的な失敗を入れ、期待値を変えずに1回落とし、`test-failed-1.png` と `final.png` が残ることを確認する（確認後に必ず戻す）。

**見る対象は欠陥注入と別だが、実行は分けなくてよい** ★ — 欠陥注入が見るのは「テストが**製品の**不具合を検出できるか」、ここで見るのは「落ちたときに証拠が残るか」であって、**別のものを見ている。だが、どちらも「意図的に1回落とす」ことで観測できる。** 同じ失敗実行で両方を見てよい(E2E は1回が高価なので、分けると時間だけが倍になる)。

**まとめるなら、落とし方は「実装側に欠陥を入れる」ほうである** ★ — **配線を壊して落とした実行では、証拠は残るが、テストが製品の不具合を検出できることは1ミリも確かめられていない。** 配線だけを壊した実行を「欠陥注入も済んだ」と書かない(欠陥注入の定義は `delegation.md` §2.2 の表が「**実装側に**意味のある欠陥を一時的に入れて」と限っている)。逆向きは成り立つ — 実装側に欠陥を入れて落とした実行は、証拠の配線の確認にもそのまま使える。

**同時に見たときは、報告に2つとも書く** — 「不具合を検出できた」と「証拠が残った」は別の主張であり、片方しか書かないと、もう片方を確かめたかどうかが後から分からない。

## 5. レポートを見る — サーバは `0.0.0.0` にバインドする

人が結果を見るのは html レポート（`artifacts/<run-id>/e2e-report/index.html`）。スクショ・動画・trace が埋め込まれ、trace viewer も同梱されている。

**起動は `tests/scripts/serve-report.sh` に固定する。`playwright show-report` を手で叩かない。**

```bash
./tests/scripts/serve-report.sh          # 最新 run を自動検出し 0.0.0.0:9323 で出す → http://<host>:9323
PORT=9400 ./tests/scripts/serve-report.sh
```

このスクリプトが担っているのは次の2つで、**どれも手順として書くと守られない類のもの**である。

| | 内容 |
|---|---|
| **最新 run への差し替え** | 前のサーバが残ったまま同じ URL を案内すると、**前の run の結果を見て合否を判断する**ことになる。試験成果物は run-id で突き合わせる前提（配布元の規範。**このプロジェクトには無い** — 冒頭の断りを見る）なので、利便性ではなく判断の正しさの問題。`artifacts/<run-id>/*-report`（アダプタが複数あるプロジェクトでは `e2e-webapp-a-report` のように複数できる）と `tests/e2e/*-report`（`playwright` を直接実行したときの出力）の中から mtime が最も新しいものを選び、**同じポートで動いている既存の `show-report` だけを `pkill -f` で止めてから**差し替える |
| **`0.0.0.0` バインド固定** | 既定の `localhost` バインドは、**コンテナ・リモートの開発サーバ・VM の中で起動すると外から開けない**（ポートを公開しても届かない）。テストを回す場所とブラウザを開く場所は普通違うため、ホストは常に `0.0.0.0` 固定（切り替えるオプションは無い） |

- `<run-id>` 指定・`status`・`stop` のサブコマンドは無い。常に最新の run を自動検出する。止めたいときは `pkill -f "show-report .*--port <PORT>([[:space:]]|$)"`（`\b` は BSD/macOS の `pkill` が解釈できず静かに不一致になる。`--port` がコマンド末尾に来る起動のされ方もあるため `$` の終端一致も要る）を直接叩く
- **`0.0.0.0` は同一ネットワークの誰からでも開ける。**レポートには画面のスクリーンショットとテストデータが写っているので、共有ホスト・踏み台では手元側でポート転送（`ssh -L 9323:localhost:9323`）を使い、サーバ側は `0.0.0.0` のまま外部に晒さない構成にする
- **人に渡すときは URL と run-id を出す。**「レポートを見てください」だけでは、どこを開くのか・どの実行の話なのかが伝わらない
- trace を単体で開くときは `playwright show-trace <trace.zip> --host 0.0.0.0 --port 9322`（html レポートの失敗テストからも開ける）。インストール不要で他人に調査を頼むなら、`trace.zip` を渡して <https://trace.playwright.dev/> にドラッグ&ドロップさせる（アップロードされずブラウザ内で処理される）
