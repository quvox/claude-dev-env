# golden ファイルの運用

出典: `testing-structure.md` 11.9 / 14章。
出典の docs/ は配布元(systest)の一次資料であり、このプロジェクトには無い。

**期待される出力そのものをファイルとして保存し、次回の実行結果と丸ごと比較する**やり方。スナップショットとも呼ぶ。

```
tests/cli/golden/help-root.txt        ← 期待される出力を保存したファイル
tests/cli/golden/error-no-config.txt
tests/cli/golden/list-json.json
```

```bash
$ <tool> --help > /tmp/actual.txt
$ diff tests/cli/golden/help-root.txt /tmp/actual.txt    # 差分があれば失敗
```

通常のアサーションが「この値がこうであること」を1つずつ書くのに対し、golden は**出力全体を固定する**。`--help` の出力は数十行あるため1行ずつ書くのは非現実的。

## なぜ CLI で重要か

**CLI の出力は API である。**`--help` の項目が消えた、エラーメッセージの文言が変わった、`--json` のキー名が変わった — これらはユーザーのスクリプトを壊す。

golden にしておくと**出力が変わった瞬間に必ず差分が出て PR のレビューに乗る**ため、破壊的変更を意図せず出すことがなくなる。

## ★ test-runner は golden を実装していない

**取得も比較も、各テストフレームワークの機能でやる。**`test-runner` がするのは「更新モードである」という合図を渡すことだけで、**ファイルの読み書きも差分比較も一切しない。**

```
test-runner --update-golden
  └─ 実装の全部: 子プロセスに TESTRUNNER_UPDATE_GOLDEN=1 を渡す
```

つまり `adapters.yml` で**この環境変数を各ツールの更新オプションへ翻訳する**必要がある。翻訳を書かないと `--update-golden` は何の効果も持たない（エラーにもならない）。

| ツール | 比較の仕組み | 更新オプション |
|---|---|---|
| vitest / jest | `toMatchSnapshot()` | `--update` / `-u` |
| Playwright | `toMatchSnapshot()` / `toHaveScreenshot()` | `--update-snapshots` |
| pytest | `pytest-regressions` / `syrupy` 等 | プラグイン依存（`--force-regen` / `--snapshot-update`） |
| Go | 標準機能は無い。`flag.Bool("update", …)` の自作が定番 | 自作したオプション |

翻訳の書き方（環境変数が立っているときだけオプションを足す）:

```yaml
  # コマンドは /bin/sh -c で実行され、環境変数も渡っているので、
  # ${VAR:+...}（立っていれば足す）がそのまま使える。sh -c で包む必要はない。
  golden: "./node_modules/.bin/vitest run {paths} --reporter=junit --outputFile={report_out} ${TESTRUNNER_UPDATE_GOLDEN:+--update}"
```

**プレースホルダ（`{...}`）とシェル変数（`${...}`）は別物。**前者は `test-runner` が展開してからシェルに渡し、後者はシェルが展開する。`{TESTRUNNER_UPDATE_GOLDEN}` と書いても未知のプレースホルダとして exit 2 になる。

`golden` ステップのコマンドが無い場合は `cli` アダプタへフォールバックする（`test-runner-usage` の `references/declarations.md`）。CLI プロダクトでは `cli` に書けば足りることが多い。

## 運用ルール

### 1. 更新は明示コマンドのみ

```bash
test-runner --update-golden --suite golden
```

**CI では絶対に自動更新しない。**自動更新は「互換性チェックの無効化」と同義。

**更新の権限は `delegation.md` §2 の DS-01 が正であり、人間の明示指示だけで更新する。**差分が出たことだけを根拠に `--update-golden` で通さない。

### 2. 差分は PR で必ず人がレビューする

これによって出力形式の変更が**破壊的変更としてレビューに乗る仕組み**になる。golden の差分だけを含む PR は、実質的に互換性の変更提案である。

### 3. 比較前に正規化する

**正規化しないと毎回壊れて誰も差分を見なくなる。**マスクする対象:

| 対象 | 例 |
|---|---|
| バージョン番号 | `v1.2.3` → `v<VERSION>` |
| 日付・時刻 | `2026-09-09T02:04:05Z` → `<TIMESTAMP>` |
| 一時パス | `/tmp/xxxx1234/` → `<TMPDIR>/` |
| 実行時間 | `(1.23s)` → `(<DURATION>)` |
| ホスト名・ユーザー名 | |
| 絶対パス | リポジトリルートからの相対に落とす |

正規化は `tests/support/golden.<ext>` に置き、書き込み側と比較側で**同じ関数を通す**。片方だけに入れると永久に一致しない。

### 4. テキストで差分が読める形式にする

バイナリスナップショットにしない。差分が読めなければレビューできず、レビューできない golden は自動更新と同じになる。

## 対象の選び方

| 対象 | 入れる理由 |
|---|---|
| 全サブコマンドの `--help` | オプション名・既定値の変更が検出される |
| `--json` などの構造化出力 | **キー名の変更はスクリプトを壊す** |
| 主要なエラーメッセージ | 終了コードとセットで分岐に使われる |
| `--version` | 形式が変わるとパースが壊れる |

対象の粒度は受け入れ基準と契約から決め、DS-01 の判断として開示する。全サブコマンドを入れると検出力は上がるがメンテコストも上がる。

## git 管理する

**`tests/cli/golden/` は「入力」であり、`artifacts/` とは違う。**

判断軸は「入力か出力か」。golden は**見た目は出力の保存だが、役割は人がレビューして決めた期待値**なので git 管理する。ここが最も混同しやすい箇所であり、`artifacts/` をリポジトリ直下（`tests/` の外）に置いているのはこの混同を避けるためでもある。

同じ理由で `tests/nonfunctional/performance/baseline.json` も git 管理する。

## 失敗時に生成される作業ファイル

`**/*.actual` `**/__diff__/` `**/__received__/` は出力なので `tests/.gitignore` で除外されている。**golden 本体（期待値）は除外しない。**
