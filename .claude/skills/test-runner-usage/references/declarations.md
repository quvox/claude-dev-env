# 宣言ファイルのリファレンス

出典: `test-runner.md` 4章 / `testing-structure.md` 2〜4章。
出典の docs/ は配布元(systest)の一次資料であり、このプロジェクトには無い。
**一次情報は `test-runner --print-schema`。**乖離した場合はそちらが正しい。

`tests/` 直下の6ファイル。**すべて任意**で、無いものは空として扱い、実際に必要になった時点でエラーになる。suites / environments / gates は有効な定義を持って配られる。adapters は `checks:` / `adapters:` の見出しだけが有効でコマンド例はコメント、quarantine は `quarantined: []`、test-plan は全体がコメントである。YAML の値が `null` でも解析エラーにはしない。

---

## suites.yml

タグの組み合わせにスイート名と実行ポリシーを与える（配布元の規範の原則B。**配布元の `docs/` はこのプロジェクトには無い** — 冒頭の断りを見る）。

```yaml
suites:
  <スイート名>:
    include:      [<glob>, ...]
    require_tags: [<@tag>, ...]
    exclude_tags: [<@tag>, ...]
    default_scope: changed
    min_count:    <整数>
    adapter:      <アダプタ名>
    mode:         <文字列>
    non_blocking: <bool>
    exclude_quarantined: <bool>
```

| キー | 型 | 既定 | 備考 |
|---|---|---|---|
| `include` | 文字列配列 | — | **省略すると「他の全スイートの include の総和」にフォールバックする。**対象が意図せず広がるので、横断タグのスイートでも明示する |
| `require_tags` | 文字列配列 | `[]` | すべて満たす必要がある（AND）。`@` の有無・大文字小文字を問わない |
| `exclude_tags` | 文字列配列 | `[]` | どれか1つでも持てば除外（OR） |
| `default_scope` | `changed` のみ意味を持つ | `""` | 変更ファイルが取得できないときは無効 |
| `min_count` | 整数 | `0`（無効） | この件数を下回ったら失敗。0件成功の防止には strict と、明示した `--tag` / `--grep` の0件失敗もある |
| `adapter` | 文字列 | `""` | 拡張子判定を上書きし、このアダプタだけで実行 |
| `mode` | 文字列 | `""` | `TESTRUNNER_MODE` として渡すだけ。ランナーは解釈しない |
| `non_blocking` | bool | `false` | true ならこのスイートの失敗でテスト実行ゲートを落とさない |
| `exclude_quarantined` | bool | **`exclude_tags` に `@flaky` があれば true** | 明示すればそれが優先 |

### `min_count` を必ず入れる理由

タグの付け忘れやパス変更で「0件実行して成功」になる状態が、最も危険な失敗。テスト実行ゲートが空振りしていることに誰も気づかない。

### `non_blocking` の用途

quarantine 中のテストの可視化。一時除外したテストは普段の実行対象から外れるが、件数と結果が見えないと「**全部緑なのに守られていない機能が増えている**」状態に気づけない。落とさずに実行し、通るようになったら一時除外解除の判断材料にする。

失敗の事実は曲げない。`summary.json` では `steps[].status` は `failed` のまま、`steps[].non_blocking: true`、`non_blocking_failed_steps` に名前が入り、全体の `status` だけが `passed` になる。端末表示も `✗` ではなく `!`。

### `exclude_quarantined` の既定が `exclude_tags` から決まる理由

`critical` スイートは `exclude_tags: []` にする。**クリティカルパスのテストが不安定なら、それはテストの問題ではなく製品またはテスト設計の問題**として扱うため、quarantine で緑にしてはいけない。この意図を1箇所の記述から自動的に導いている。

### 標準的な定義

```yaml
suites:
  unit:                           # f1-fast / f1-unit / f4-unit
    include: ["src/**/*.test.*"]
    exclude_tags: ["@flaky"]

  integration:                    # f1-fast / f1-integration / f4-integration
    include: ["tests/integration/**/*.test.*"]
    exclude_tags: ["@flaky"]

  e2e-local:                      # 変更されたテストファイルのみ（既定の組では未使用）
    include: ["tests/e2e/**/*.spec.*"]
    exclude_tags: ["@flaky", "@slow"]
    default_scope: changed

  e2e-full:                       # f4-e2e
    include: ["tests/e2e/**/*.spec.*"]
    exclude_tags: ["@flaky"]

  critical:                       # クリティカルパス回帰スイート
    include: ["tests/e2e/**/*.spec.*", "tests/integration/**/*.test.*"]
    require_tags: ["@critical"]
    exclude_tags: []              # quarantine でも除外しない
    min_count: 1

  # 試験区分別のクリティカルパス回帰（f4-critical の3ステップが呼ぶ）。
  # 上の critical と狙いは同じだが、テストレベルごとに分けてあり、critical が
  # 見ていない src/**（単体）も対象に含む。除外を空にする意図は同じである。
  # min_count は @critical を1件でも付けてから有効にする（導入直後は0件が正しい）。
  critical-unit:                  # f4-critical の unit ステップ
    include: ["src/**/*.test.*"]
    require_tags: ["@critical"]
    exclude_tags: []
    # min_count: 1                  # ← 雛形はコメントアウトして配る

  critical-integration:           # f4-critical の integration ステップ
    include: ["tests/integration/**/*.test.*"]
    require_tags: ["@critical"]
    exclude_tags: []
    # min_count: 1

  critical-e2e:                   # f4-critical の e2e ステップ
    include: ["tests/e2e/**/*.spec.*"]
    require_tags: ["@critical"]
    exclude_tags: []
    # min_count: 1

  smoke:
    include: ["tests/smoke/**/*.spec.*"]
    require_tags: ["@smoke"]
    min_count: 1
```

---

## environments.yml

接続先と「そのテスト実行が何をしてよいか」を宣言する（配布元の規範の原則C・D。同上）。

```yaml
defaults:
  test_data_prefix: <文字列>
  cleanup:          <文字列>

environments:
  <環境名>:
    base_url:        <URL>
    secrets:         <文字列>
    allow:
      write:       true | false | limited
      destructive: true | false
      external:    true | false | stub | sandbox | blocked
      <任意のキー>: 同上
    suites:          [<スイート名>, ...]
    accounts:        [<アカウント名>, ...]
    require_confirm: <bool>
    test_data_prefix: <文字列>
    cleanup:          <文字列>
```

| キー | 備考 |
|---|---|
| `base_url` | `${VAR}` を環境変数で展開する。**未定義の変数があると exit 2。**値は書かず環境変数かシークレットストアから渡す |
| `secrets` | 取得元の名前だけ（値は書かない） |
| `allow` | ランナーは**解釈して止めない。**`TESTRUNNER_ALLOW_*` として渡すだけ |
| `suites` | **必須。省略は準備の失敗である** ★(2026-09-15。inspection-28 A-13)— 書き忘れを「全部やってよい」と読むと、**意図しない試験が本番に近い環境を壊しうる。** 全部許すつもりなら `["*"]` と**明示して書く**(書いてあれば、それは判断である)。**既にこの欄を省いている宣言は、`["*"]` を明示するか、実際に許す一覧へ直す** |
| `accounts` | `TESTRUNNER_ACCOUNTS` として渡す |
| `require_confirm` | true なら実行前に環境名の入力を求める。一致しなければ exit 3 |
| `defaults.*` | 各環境が未指定なら継承する |

### `allow` の値の意味

| 値 | `Allowed()` | `Restricted()` | `Blocked()` | 意味 |
|---|:-:|:-:|:-:|---|
| `true` | ○ | × | × | 無条件に許可 |
| `false` | × | × | ○ | 禁止 |
| `limited` | × | **○** | × | 条件付き（`test_data_prefix` 付きのみ書き込み可 など） |
| `stub` | × | **○** | × | 条件付き（外部通信をスタブへ） |
| `sandbox` | × | **○** | × | 条件付き（外部連携のサンドボックスへ） |
| `blocked` / `none` / 未定義 | × | × | ○ | 禁止 |

**`Allowed()` は「無条件許可」だけを意味する。**`limited` は false になる。条件付き許可を許可と同一視すると、条件の検証を忘れたまま通ってしまうため。

### `suites` — 実行対象の制限

`production` の `suites` を `[smoke]` にすることが、本番でフルセットを流せない状態の実体。違反は **1件も実行せず exit 3**。

```yaml
  production:
    base_url: ${PROD_BASE_URL}
    secrets: prod-readonly
    allow:
      write: limited              # test_data_prefix 付きのみ
      destructive: false
      external: blocked           # 一切の外部送信を禁止
    suites: ["smoke"]             # ← smoke 以外は実行不可
    accounts: [smoke-bot]
```

---

## gates.yml

フローごとの合否基準を機械可読にする（原則E）。人と、変更のたびに自動で回す仕組み(在れば)が同じこれを読む。

```yaml
gates:
  <テスト実行ゲートID>:
    # --- 予約キー ---
    inherits:                <テスト実行ゲートID>
    strict:                  <bool>
    quarantine_overdue:      fail
    flaky_retries:           <整数>
    retain_evidence:         always
    require_review:          <整数>
    require_regression_test: <bool>
    metrics_compare:         <bool>
    pr_diff_limit:           <整数>

    # --- 以外はすべてステップ名 ---
    <ステップ名>: true | false
    <ステップ名>:
      suite:  <スイート名>
      env:    <環境名>
      scope:  changed
      mode:   <文字列>
      coverage: { lines: <数値>, branches: <数値>, scope: diff|all, base: <ref> }
      forbid_skip:            <bool>
      require_negative_tests: <bool>
      require_down:           <bool>
      measure_duration:       <bool>
```

テスト実行ゲート ID は自由な文字列。このキットでは7本を使う — 構築(F1)が `f1-fast` / `f1-unit` / `f1-integration`（片方の試験区分しか持たないモジュールでは後の2つ。`/test-runner-usage` の「典型コマンド」）、試験(F4)が `f4-unit` / `f4-integration` / `f4-e2e` と、除外を一切かけずに重要テストを通す `f4-critical`（`--only` でその run の試験区分に絞って呼ぶ）。

### 予約キーのうち「読むだけ」のもの

**設定しても効かない。**誰が評価すべきかを知っておく。

| キー | 実際に評価すべき場所 |
|---|---|
| `flaky_retries` | CI（`gh run rerun --failed` の回数上限） |
| `retain_evidence` | アダプタ（成功時の試験成果物保持） |
| `require_review` | GitHub のブランチ保護 |
| `require_regression_test` | PR レビュー / PR テンプレート |
| `metrics_compare` | 自動で回す仕組みのデプロイ後ステップ(在れば) |
| `pr_diff_limit` | 自動で回す仕組み / PR レビュー |
| ステップの `mode` / `require_down` / `measure_duration` | テストコード（環境変数として渡される） |

実際に評価されるのは `inherits`（展開する。循環は exit 2）、`strict`（下記）、`quarantine_overdue: fail`（期限切れがあれば exit 1）の3つ。

### `strict` — 証拠が取れない状態を合格にしない

`strict: true` のテスト実行ゲート（CLI の `--strict` でも同じ）では、次を warn / skipped ではなく **failed** にする。

- suite 未定義による skipped
- アダプタのコマンド未定義による skipped（**ステップ名のタイプミスもここで露出する**）
- 対象テスト0件による skipped（`scope: changed` のステップは除く — 変更が無いのは正当）
- コマンド成功なのに JUnit XML（`{report_out}`）が無い
- `coverage:` を要求しているのにカバレッジ出力が1件も無い
- 除外対象が実行対象ファイルに同居しているのにコマンドに `{exclude_filter}` が無い

`inherits` で継承される。雛形では f4-unit / f4-integration / f4-e2e に付き、**f1-fast / f1-unit / f1-integration と f4-critical には付けない**。構築の3本は導入途中でも回せる高速ループの場だからであり、`f4-critical` は **`@critical` を1件も付けていない導入直後を「対象テスト0件」で落とさない**ためである（0件は skipped として見えるほうが、その事実を正しく伝える）。`@critical` を付け始めたら `critical-*` の `min_count` を有効にして、0件で緑になるのを止める。

### ステップの属性

| キー | 意味 |
|---|---|
| `suite` | 省略時、ステップ名がスイートステップならステップ名をスイート名として使う |
| `env` | **`--env` を上書きする。**ガードもこの実効環境で判定する |
| `scope: changed` | 変更ファイル由来のテストだけを対象にする |
| `coverage.scope: diff` | git 差分の追加・変更行だけを測る。既定は `all` |
| `forbid_skip` | スキップが1件でもあれば不合格 |
| `require_negative_tests` | 異常系と推定されるテストが0件なら不合格（テスト名の正規表現によるヒューリスティック。**網羅は保証しない**）。`@neg` タグはこの判定に使われず、`--report matrix` の `neg` 列の集計用 |

`coverage.scope: diff` は意図的な選択。既存コード全体を80%にするのは非現実的だが、**新規/改修分だけを測れば「触ったところは必ずテストがある」を強制できる**。

### スイートステップと静的チェックステップ

**スイートステップ**（スイートを解決してテストを実行する）:

```
unit  integration  e2e  cli  critical  smoke  a11y  perm
perf  migration  golden  install  compat  soak  load
```

これ以外、または `suite:` を持たないステップは**静的チェックステップ**（`lint` `format` `types` `secret_scan` `sca` `sast` `healthcheck` など）。

### 実行順序は固定

**YAML にどの順で書いても、実行順は変わらない。**

```
lint → format → types → secret_scan → sca → sast
→ unit → integration → golden → migration
→ e2e → cli → critical → install → compat
→ a11y → perm → smoke → healthcheck → perf → soak → load
```

一覧に無いステップ名はこの後ろに記述順で並ぶ。

**理由**: 失敗を最も安く検出できる順（速く軽いものから）に並べるため。順序を各プロジェクトの YAML の書き方に委ねると、`sca` を `unit` の後ろに書いただけで毎回テストを回してから依存脆弱性で落ちることになる。

**ステップの失敗は後続を止めない。**全ステップを実行し、最後にまとめて合否を判定する（1回の実行で得られる情報を最大化するため）。

---

## adapters.yml

言語ごとのテストランナーへの翻訳定義。**これが無いとテストは1件も実行できない。**

```yaml
checks:
  <ステップ名>: <コマンドテンプレート>    # リポジトリ横断のチェック

adapters:
  <アダプタ名>:
    root:     <パス>
    report:   junit
    coverage: lcov | cobertura | go-cover
    include:  [<glob>, ...]
    suites:   [<スイート名>, ...]
    env:      {<KEY>: <VALUE>}
    <ステップ名>: <コマンドテンプレート>
```

| キー | 既定 | 備考 |
|---|---|---|
| `root` | リポジトリルート | コマンドはここで実行される。`{paths}` もここからの相対 |
| `report` | `junit` | **現在 junit のみ対応。**Rust は `cargo2junit` を挟む |
| `coverage` | `""` | 空なら出力内容から自動判定 |
| `include` | — | 省略時は「`root` 配下」かつ「拡張子が既定マッピングに一致」 |
| `suites` | 全部 | 制限したい場合に指定 |
| `env` | `{}` | 例: `PLAYWRIGHT_JUNIT_OUTPUT_NAME` |

### `checks:` を分離する理由

`secret_scan` / `sca` / `sast` / `healthcheck` は言語に紐づかない。アダプタ側に書くと、多言語リポジトリで同じスキャナが言語の数だけ走る。

**静的チェックステップは `checks:` と各アダプタの両方が定義されていれば両方実行される。**

### 拡張子 → 既定アダプタ名

| アダプタ名 | 拡張子 |
|---|---|
| `go` | `.go` |
| `typescript` | `.ts` `.tsx` `.js` `.jsx` `.mjs` `.cjs` |
| `python` | `.py` |
| `rust` | `.rs` |
| `shell` | `.sh` `.bats` |
| `ruby` | `.rb` |
| `java` | `.java` |
| `kotlin` | `.kt` |

**アダプタ名をこの表に合わせると `include` を省略できる。**

### コマンド未定義時のフォールバック

そのステップのコマンドが無い場合、次の順で代替を探す。

| ステップ | フォールバック先 |
|---|---|
| `a11y` `perf` `soak` | `e2e` |
| `cli` | `e2e` |
| `critical` | `e2e` → `cli` |
| `e2e` | `cli` → `integration` |
| `format` | `lint` |
| `golden` | `cli` |
| `integration` | `unit`（`-t '{name_filter}'` も引き継いで名前を絞る） |
| `perm` | `e2e` → `integration` |
| `smoke` | `e2e` → `cli` |

すべて見つからなければそのステップは `skipped` になる。

### 埋める順序

| 順 | 場所 | 内容 |
|---|---|---|
| 1 | `checks.secret_scan` と各アダプタの `lint` / `types` | コミット前の軽量チェックで使う3つ |
| 2 | 各アダプタの `unit` / `integration` | **`{report_out}` と `{coverage_out}` を必ず入れる** — `{coverage_out}` が**コマンド文字列に無い**と、ランナーは測定結果を受け取れない。`coverage: lcov` は形式の宣言であって受け渡しではない。**カバレッジの下限を後から足した瞬間に、製品に不具合が無くても `strict` の実行が止まる**(「どのアダプタのコマンドにも `{coverage_out}` が無く測定できません」)。**測定結果を1つのファイルに書けない試験ツールでは、生成先から `{coverage_out}` へ写す一手を足す**(下の TypeScript の例) |
| 3 | 各アダプタの `e2e` | `{report_out}` に加え **`{artifacts}`**（試験成果物の出力先。省略すると `artifacts/` の外に落ち、まとめて回収する仕組みがあっても拾われない） |
| 4 | 残り（`checks.sca` `checks.sast` `checks.healthcheck`、`a11y` など） | |

### 例

```yaml
checks:
  secret_scan: "gitleaks protect --staged --no-banner"
  sca:         "trivy fs --exit-code 1 --severity HIGH,CRITICAL ."
  sast:        "semgrep --config auto --error ."

adapters:
  typescript:
    root: ./apps/web
    # ★ vitest は測定結果の出力先を「ディレクトリ」でしか指定できないので、
    #   ランナーが読む {coverage_out} へ写す一手を足す。**いったん rc= で受けて
    #   exit $rc で返す**（&& だとテストが落ちたときに写しが走らず、; だけだと
    #   最後の cp の成否が結果になって**テストの失敗が消える**。exit $? も同じ理由で
    #   誤り — 直前の cp の終了コードを返してしまう）。
    unit: "./node_modules/.bin/vitest run {paths} -t '{name_filter}' --coverage --coverage.reporter=lcov --coverage.reportsDirectory={artifacts}/cov --reporter=junit --outputFile={report_out}; rc=$?; cp -f {artifacts}/cov/lcov.info {coverage_out} 2>/dev/null || true; exit $rc"
    e2e:  "./node_modules/.bin/playwright test {paths} --grep '{name_filter}' --reporter=junit"
    lint: "./node_modules/.bin/eslint {files}"
    report: junit
    coverage: lcov
    env:
      PLAYWRIGHT_JUNIT_OUTPUT_NAME: "{report_out}"

  go:
    root: ./services/api
    unit: "gotestsum --junitfile {report_out} -- ./... -run '{name_filter}' -coverprofile={coverage_out}"
    report: junit
    coverage: go-cover
```

---

## quarantine.yml

Flaky の一時除外リスト。**無いのが正常な状態。**

```yaml
quarantined:
  - test:   "tests/e2e/specs/checkout.spec.ts::決済完了で在庫が減る"
    since:  2026-09-01
    due:    2026-09-30
    issue:  PROJ-1234
    owner:  <担当ロール>
    reason: "外部決済サンドボックスの応答遅延で稀に timeout"
```

| キー | 必須 | 備考 |
|---|:-:|---|
| `test` | ○ | `<path>::<テスト名>` 形式 |
| `due` | ○ | **省略すると「期限切れ」として扱う。**書き忘れを通さない |
| `since` `issue` `owner` `reason` | | 表示・レポート用 |

### 一致判定

完全一致に加え、**パスが一致しテスト名が部分一致**すれば一時除外対象とみなす。

```
quarantine.yml:  "...checkout.spec.ts::決済完了で在庫が減る"
テスト側:        "...checkout.spec.ts::@critical 決済完了で在庫が減る"
                  → 一致（タグを足しても一時除外が外れない）
```

タグを追記しただけで一時除外が外れると、静かに不安定なテストが普段の実行対象へ戻ってしまうため。

### 期限判定

`due` は UTC で解釈され、**翌日の 00:00:00 UTC を過ぎた時点で期限切れ**。`due: 2026-09-30` なら 2026-10-01 00:00:00 UTC を過ぎた時点で期限切れになる。`gates.yml` に `quarantine_overdue: fail` があれば exit 1。

**期限が仕組みの核。**無いと quarantine は「入れたら二度と出てこない墓場」になる。

**`@flaky` の印だけで外さない** ★(2026-09-15。inspection-28 A-5)— スイートの宣言の
`exclude_tags: ["@flaky"]` は、その印の付いたテストを**期限と無関係に**実行対象から外す。
**期限切れを見るのはここ(`quarantine.yml` の `due`)だけ**なので、印だけで外れたテストには
期限の検査が永久に掛からない。**印は「結果が揺れる」という分類であって、外す決定ではない。**
外すなら台帳に期限付きで登録する(手順の正: `verify-tests` の試験区分を回す段)。

---

## test-plan.yml

**任意。無いのが普通の状態**（承認済みマトリクスとの照合を使うプロジェクトだけが置く）。

テスト仕様の対応表と「テスト設計の判断」で定めた要件 × 観点の機械可読な写し。存在すれば `--report matrix` が実測集計と照合する（`references/reports.md`）。

```yaml
requirements:
  FR-order-01-1:
    normal: true          # ○ = true, — = false（省略は false と同じ）
    bv: true
    neg: true
    perm: true
    st: false
    conc: true
    vol: false
```

| キー | 備考 |
|---|---|
| `requirements.<受け入れ基準 ID>` | 受け入れ基準 ID は自由キー |
| `normal` `bv` `neg` `perm` `st` `conc` `vol` | 観点セル。bool。未知の観点キーは訂正候補付きで警告される |

**テスト仕様が正で、これは照合用の写し。**乖離したらテスト仕様に合わせて作り直す（このファイル側だけを直さない）。照合はセルの有無のみで、期待値の正しさ・境界の選び方・計画自体の妥当性は検証しない。`normal` の照合は近似（観点タグを1つも持たないテスト≧1件で充足とみなす）。

---

## 未知キーの検出

実装の知らないキーは訂正候補付きの警告として報告され、`summary.json` の `warnings` に残る。`test-runner setup` は**未解決項目として扱う**（exit 1）。

```
! config tests/suites.yml:13 suites.critical に未知のキー "min_cout"（"min_count" の誤りではありませんか）
```

**対象外**: `gates.yml` のステップ名と `adapters.yml` のコマンド名は自由キーなので検出できない。ここの綴り間違いは「未定義ステップ」として `skipped` に現れる（strict テスト実行ゲートなら failed）。`test-plan.yml` の受け入れ基準 ID も自由キーだが、観点セルのキーは検出対象。
