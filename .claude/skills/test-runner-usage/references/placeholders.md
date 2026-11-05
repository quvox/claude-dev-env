# コマンドテンプレートのプレースホルダ

出典: `test-runner.md` 7.1 / 5章。一次情報は `test-runner --print-schema`。
出典の docs/ は配布元(systest)の一次資料であり、このプロジェクトには無い。

`adapters.yml` のコマンド文字列で使える変数。全19個。

| プレースホルダ | 内容 |
|---|---|
| `{artifacts}` | この実行の試験成果物出力ディレクトリ（絶対パス） |
| `{base_url}` | `environments.yml` の `base_url`（`${VAR}` は展開済み） |
| `{browsers}` | `--browsers` の値 |
| `{coverage_out}` | カバレッジ出力先（絶対パス） |
| `{duration}` | `--duration` の値 |
| `{env}` | 環境名 |
| `{exclude_filter}` | **`exclude_tags` / quarantine で除外したテスト名の正規表現**（除外が無ければ空） |
| `{files}` | `--files` のうちこのアダプタ担当ぶん（空白区切り、`root` からの相対） |
| `{grep}` | `--grep` の生の値 |
| `{name_filter}` | **タグと `--grep` から組んだテスト名の正規表現** |
| `{paths}` | 対象ファイル（空白区切り、`root` からの相対） |
| `{repeat}` | `--repeat` の回数 |
| `{report_out}` | **JUnit XML 出力先**（絶対パス） |
| `{root}` | アダプタの `root`（絶対パス） |
| `{run_id}` | 実行 ID |
| `{suite}` | スイート名 |
| `{tag_filter}` | `require_tags` を `@` 抜き・カンマ区切りにしたもの（bats 用。pytest へはそのまま渡せない） |
| `{tests_dir}` | `tests/` の絶対パス |
| `{workdir}` | コマンドの作業ディレクトリ（= `root`） |

**未知のプレースホルダは exit 2。**黙って空文字にすると「`--grep` が効いていない」ような沈黙した失敗になるため。エラーには使用可能な名前の一覧が出る。

**既知だが値が空の場合は空文字に展開される。**`--browsers` を渡さなければ `{browsers}` は空。

## 絶対に入れるべき2つ

| プレースホルダ | 入れないとどうなるか |
|---|---|
| `{report_out}` | ランナーがレポートを読もうとしない。**件数を検証できず「0件成功」に気づけない** |
| `{coverage_out}` | カバレッジ閾値が判定されない。**警告は出るがステップは通る** |

`{report_out}` を含めていてコマンドが成功したのにファイルが無い場合は警告が出る（strict テスト実行ゲートでは failed になる。`{coverage_out}` の欠落も同様）。

## `{name_filter}` の構成規則

タグを「テスト名に含まれる `@critical` という文字列」と定めた結果、絞り込みは名前フィルタで表現できる。

| 条件 | 生成される正規表現 |
|---|---|
| `require_tags: [@critical]` | `@critical` |
| `require_tags: [@critical]` + `--tag @perm` | `(?=.*@critical)(?=.*@perm).*` |
| `require_tags: [@critical]` + `--grep 注文` | `(?=.*@critical)(?=.*(?:注文)).*` |
| 条件なし | `""`（空文字） |

複数条件は**先読みで AND を表現する**。`@` を省略したタグは補完される。タグは `regexp.QuoteMeta` でエスケープされ、`--grep` は生のまま `(?: )` で囲まれる。

**この変換が「利用者は常に `--suite critical` と書く」を成り立たせている実体。**各言語のランナーは名前フィルタを必ず持っている。

| ランナー | 渡し先 |
|---|---|
| Playwright | `--grep '{name_filter}'` |
| Vitest / Jest | `-t '{name_filter}'` |
| pytest | `-k 'critical'` のような単純な部分一致の1語だけ（下記の制約を参照） |
| Go | `-run '{name_filter}'` |
| bats | `--filter-tags '{tag_filter}'` |

### pytest のフィルタの制約

pytest の `-k` は正規表現ではなく、部分一致の語を `and` / `or` / `not` で組む式。`-m` は登録したマーカー名を選ぶ式であり、テスト名のタグを選ぶものではない。このキットのタグはテスト名に埋め込む方式なので、pytest に直接渡せるのは `-k 'critical'` のような**単純な部分一致の1語**だけ。`{name_filter}` の先読み正規表現や `{tag_filter}` のカンマ区切りをそのまま渡してはいけない。

複合のタグ絞り込みとして生成された `{name_filter}` の正規表現は pytest 単体では表現できない。対象をファイルごとに分けて `{paths}` で絞るか、プロジェクト側で `conftest.py` による選別を実装する。単語への変換だけでは複合条件や `--grep` の意味を維持できない。

例（プロジェクトの pytest で実行する。パラメータ ID もテスト名の一部になる）:

```python
# test_filter.py
import pytest

@pytest.mark.parametrize("value", [pytest.param(1, id="@critical"), pytest.param(2, id="@smoke")])
def test_value(value):
    assert value > 0
```

```bash
pytest -q test_filter.py -k 'critical'
# 1 passed, 1 deselected
```

## `{exclude_filter}` の構成規則

`{paths}` はファイル単位でしか渡らないため、**同一ファイル内の除外対象（`exclude_tags`・quarantine）は名前で除外を引き継がないと実行される**。`{exclude_filter}` は、除外されたのに実行対象ファイルに同居しているテスト名を `regexp.QuoteMeta` でエスケープした OR 結合（`(?:名前1|名前2)`）。ネイティブランナーの除外オプション（Playwright なら `--grep-invert`）へ渡す。

**コマンドに `{exclude_filter}` が無く、除外対象が同居している場合は警告が出る**（strict テスト実行ゲートでは failed）。除外オプションが無いランナーでは、除外対象をファイルごと分ける。

### Go の正規表現（RE2）の制約

Go の `-run` は RE2 で、**先読み `(?=...)` を持たない。**複数条件の `{name_filter}` をそのまま Go に渡すとエラーになる。Go アダプタでは条件を1つに絞るか、`{tag_filter}` 側を使う。

## コマンドの実行環境

| 項目 | 動作 |
|---|---|
| 起動 | `/bin/sh -c "<コマンド>"`（`TESTRUNNER_SHELL` で変更可。Windows は `cmd /C`） |
| 作業ディレクトリ | そのアダプタの `root` を絶対パスに解決したもの |
| `PATH` | **呼び出し元のものをそのまま継承する** |
| 標準出力・標準エラー | 抑制しない。そのまま流れる |

**起動時の cwd はアダプタのコマンドに影響しない。**コマンドは常に `root` で実行される。「どこから起動したか」で結果が変わることはない。

`PATH` を継承するので、`./node_modules/.bin/vitest` のように**相対パスで実体を指すほうが安全**。`npx` や `pnpm` 経由は解決先が環境で変わる。

## テストプロセスへ渡される環境変数

`adapters.yml` の `env:` と、ランナー自身の環境変数もすべて引き継がれる。

| 変数 | 内容 |
|---|---|
| `TESTRUNNER_ENV` | 環境名 |
| `TESTRUNNER_SUITE` | スイート名（静的チェックでは空） |
| `TESTRUNNER_STEP` | ステップ名 |
| `TESTRUNNER_RUN_ID` | 実行 ID |
| `TESTRUNNER_ARTIFACTS` | この実行の出力ディレクトリ（絶対パス） |
| `TESTRUNNER_BASE_URL` | `base_url`（展開済み） |
| `BASE_URL` | 同じ値。Playwright / axe の慣習的な名前。`base_url` が空なら渡さない |
| `TESTRUNNER_SECRETS` | `secrets` の値（取得元の名前） |
| `TESTRUNNER_TEST_DATA_PREFIX` | テストが作るデータの接頭辞 |
| `TESTRUNNER_CLEANUP` | `cleanup` の値 |
| `TESTRUNNER_ACCOUNTS` | 使用を許可されたアカウント（カンマ区切り） |
| `TESTRUNNER_ALLOW_<CAP>` | ケイパビリティの値。`<CAP>` は `allow` のキーを大文字にしたもの |
| `TESTRUNNER_ALLOW_KEYS` | 定義されているケイパビリティ名（カンマ区切り、ソート済み） |
| `TESTRUNNER_MODE` | ステップの `mode`（設定時のみ） |
| `TESTRUNNER_UPDATE_GOLDEN` | `--update-golden` 時に `1` |
| `TESTRUNNER_REQUIRE_DOWN` | `require_down: true` のとき `1` |
| `TESTRUNNER_MEASURE_DURATION` | `measure_duration: true` のとき `1` |

`tests/support/guards.*` はこれを読んで実装する。**Playwright/Node 向けの参照実装（`guards.ts` `network.ts` `fixtures.ts`）が `tests/support/` に展開されている**ので、そこから始める。他言語への移植は下の概念コードから始め、条件付き許可の検証まで実装する。

```typescript
export function requireCapability(cap: 'write' | 'destructive' | 'external') {
  const v = process.env['TESTRUNNER_ALLOW_' + cap.toUpperCase()];
  // 完全許可だけを列挙する。external には完全許可の値がない。
  const fullAllow: Record<typeof cap, readonly string[]> = {
    write: ['true'], destructive: ['true'], external: [],
  };
  if (!fullAllow[cap].includes(v ?? '')) {
    throw new Error(
      `capability "${cap}" is not allowed on environment "${process.env.TESTRUNNER_ENV}". ` +
      `See tests/environments.yml`);
  }
}
```

**これは在/不在の検査だけである — `limited` / `stub` / `sandbox` のような条件付きの値は、その条件（接頭辞・送信先）の検査を実装するまで、拒否する側に倒す。**

移植の到達点は、同梱 TypeScript 実装の `tests/support/guards.ts` の `requireWrite` による接頭辞検証と、`tests/support/network.ts` の送信先制約の検証である。ただし参照実装の `sandbox` は遮断を行わず、送信先の差し替えをテスト設定側に委ねるため、移植先でもサンドボックスの送信先を検証する仕組みが必要。

**ガードは「テストが呼ぶもの」ではなく「フィクスチャの入口に置くもの」。**テスト作者が意識しなくても効く位置に置く。

## JUnit XML — 相互運用の契約

**各アダプタは JUnit XML を出力すること。**言語ごとに結果フォーマットが違うため、これを約束事にする代わりにランナー側はパーサを1つ持つだけで済む。

受け付ける形は `<testsuites>` 直下に `<testsuite>` が並ぶ形／`<testsuite>` 単体／入れ子（親のスイート名が `/` 区切りで前置される）。

判定順は `error` → `failure` → `skipped` → 成功。テスト識別子は `classname::name`、`classname` が無ければ `suite::name`。

**`--repeat` 時のファイル名**: 1回目は `{report_out}` そのまま、N 回目（N≧2）は拡張子の前に `.runN` を挿入する。

## カバレッジ

| 形式 | 出力元の例 | 行 | 分岐 |
|---|---|:-:|:-:|
| `lcov` | `vitest` / `jest` / `cargo-llvm-cov` | `DA:` | `BRDA:` |
| `cobertura` | pytest-cov | `<line hits>` | `condition-coverage` |
| `go-cover` | `go test -coverprofile` | ブロック範囲を展開 | **非対応** |

**`go-cover` は分岐カバレッジを持たない。**Go で `branches` の閾値を設定しても効かない。

`scope: diff` は `git merge-base <base> HEAD` から差分の追加・変更行を集め、カバレッジデータと交差を取る。`--unified=0` を使うので文脈行は含まれない。**差分が0行のときは閾値判定をスキップする**（測るものが無いのに未達で落とすのは誤り）。
