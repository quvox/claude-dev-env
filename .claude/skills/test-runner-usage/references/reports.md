# レポート

出典: `test-runner.md` 9章。
出典の docs/ は配布元(systest)の一次資料であり、このプロジェクトには無い。

5種類ある。

| 出力 | いつ | 用途 |
|---|---|---|
| `summary.json` | 実行ごとに自動 | 判定の根拠。試験フローの照合・報告に使う |
| `--report traceability` | 明示指定 | 受け入れ基準 ID → テストの対応表（試験フローの受け入れ照合。**機能全体を指す要件の ID ではなく、条項ごとの ID である** — 2026-09-15) |
| `--report matrix` | 明示指定 | 要件 × 観点の実測集計。`tests/test-plan.yml` があればセルの有無を照合し、欠落は exit 1（構築フローのテスト設計と試験フローの照合） |
| `--report flaky` | `--repeat 2` 以上と併用 | Flaky 検出（nightly） |
| `--report suites` | 明示指定 | スイート棚卸し（定期的な） |

すべて `--json` を付けられる。

---

## summary.json

`artifacts/<run-id>/summary.json`。**`--list` / `--dry-run` 以外では常に書かれる。**

```json
{
  "run_id": "20260908-133104-6100",
  "started_at": "2026-09-08T13:31:04Z",
  "seconds": 0.168,
  "gate": "f4-integration",
  "suite": "",
  "env": "local",
  "status": "failed",
  "failed_steps": ["unit", "critical"],
  "steps": [
    {
      "name": "unit",
      "suite": "unit",
      "env": "local",
      "status": "failed",
      "reason": "行カバレッジ 75.00% < 80.00%（scope: diff, 3/4 行）",
      "seconds": 0.05,
      "discovered": 2,
      "tests": {
        "cases": [{"suite": "demo", "class": "demo", "name": "ok1",
                   "status": "passed", "seconds": 0.02}],
        "total": 2, "passed": 2, "failed": 0, "errored": 0, "skipped": 0,
        "seconds": 0.05,
        "files": ["/abs/artifacts/<run-id>/unit/typescript.junit.xml"]
      },
      "coverage": {
        "lines_total": 4, "lines_covered": 3, "lines_percent": 75,
        "branches_total": 2, "branches_covered": 2, "branches_percent": 100,
        "scope": "diff", "format": "lcov"
      },
      "commands": [{"adapter": "typescript", "command": "sh ...", "dir": ".",
                    "exit_code": 0, "seconds": 0.04}]
    }
  ],
  "totals": {"tests": 6, "passed": 5, "failed": 1, "errored": 0, "skipped": 0},
  "quarantine": {"count": 1, "overdue": 0, "overdue_tests": []},
  "warnings": ["比較基準の ref が見つかりません..."],
  "tool": {"name": "test-runner", "version": "7466072-dirty"}
}
```

| フィールド | 意味 |
|---|---|
| `status` | `passed` / `failed`。**`skipped` / `listed` と `non_blocking` の失敗は数えない** |
| `non_blocking_failed_steps` | 失敗したがテスト実行ゲートを落とさなかったステップ |
| `steps[].discovered` | 解決されたテスト件数（実行前）。**`tests.total`（実行後）との差が空振りの手がかり** |
| `steps[].reason` | 失敗理由。複数ある場合は `; ` 区切り |
| `quarantine.count` | 一時除外件数。**一時除外中のテストは「守られていない機能」**なので常に出る |
| `warnings` | 落とすほどではない指摘 |

`--repeat` の各回の内訳は含まれない（`--report flaky` で出す）。

### ドキュメントへの転記

実行したスイート・件数・結果・カバレッジは `summary.json` を根拠に報告する。試験フローの照合・記録・鮮度スタンプは `/verify-tests` が所有し、このレポートの成功だけでは代替しない。

---

## `--report traceability`

`@req:<ID>` タグから要件 → テストの対応表を作る。**受け入れ基準とテストの対応を確認する索引になる。**要件そのものの一覧は読まないので、対応表の側から欠落を確認する。

```bash
test-runner --report traceability
test-runner --report traceability --json
test-runner --report traceability --suite e2e-full     # スイートを絞る
```

```json
{
  "requirements": [
    {"requirement": "FR-order-01-1",
     "tests": ["src/order/tax.test.ts::@critical @req:FR-order-01-1 税率が適用される"]}
  ],
  "untagged_tests": ["src/order/tax.test.ts::金額が負のときエラーになる"],
  "regressions": [
    {"requirement": "1234", "tests": ["tests/e2e/specs/x.spec.ts::regression #1234: ..."]}
  ],
  "counts": {"requirements": 3, "tests": 5, "tagged_tests": 3, "untagged_tests": 2}
}
```

- `--suite` を省略すると**全スイートの和集合**が対象
- `regressions` は `@regression:<id>` タグと `regression #<id>` 形式のテスト名（不具合修正前 の再現テスト）を拾う
- **受け入れ基準 ID の大文字小文字は保たれる**（タグ名の接頭辞だけ小文字化する）

`untagged_tests` が多いのは `@req:` の付け漏れ。`test-runner --report traceability` を明示実行して確認する（既定の f4-e2e はこのレポートを生成しない）。テスト仕様の対応表との照合は、`/verify-tests` の表の網羅（§1）で行う。

---

## `--report matrix`

`@req:<ID>` と**観点タグ**のクロス集計を出す。**テスト仕様の対応表と「テスト設計の判断」と突き合わせるための実測値。**

```bash
test-runner --report matrix
test-runner --report matrix --json
test-runner --report matrix --suite e2e-full     # スイートを絞る
```

```
要件 × 観点 マトリクス
  要件 4 件 / テスト 12 件（観点タグなし 5 件、@req: なし 1 件）

requirement           bv   neg  perm    st  conc   vol  none total
------------------------------------------------------------------
FR-auth-02-1           -     -     -     -     -     -     2     2  !
FR-order-01-1          2     1     1     -     1     -     1     5
FR-order-01-2          -     1     -     -     -     -     1     2
FR-order-01-3          -     -     -     1     -     1     -     2
```

### 観点タグ

| タグ | 観点 |
|---|---|
| `@bv` | 境界値 |
| `@neg` | 異常系 |
| `@perm` | 権限・認可 |
| `@st` | 状態遷移 |
| `@conc` | 同時実行・冪等性 |
| `@vol` | 大量データ |

**正常系にはタグを持たせない。**観点タグを1つも持たないものが `none` 列に入る。ここには正常系と**付け忘れの両方**が混ざる。

### 何が検出できるか

| 出力 | 意味 |
|---|---|
| `!` の付いた行 | **観点タグが1件も付いていない要件。**正常系だけを書いている疑い |
| 孤児（`@req:` の無いテスト） | タグの付け忘れ。どのセルにも属さない |
| `none` 列が多い | 観点タグの付け忘れ |

1テストが複数の観点・複数の要件に属せるため、**観点別の件数の合計は `total`（実数）と一致しない。**

### `tests/test-plan.yml` との照合

`tests/test-plan.yml`（テスト仕様で定めた要件 × 観点の機械可読な写し。`references/declarations.md`）が存在すれば、実測集計と自動で照合する。

| 照合結果 | 意味 | 扱い |
|---|---|---|
| `missing_requirement` | 計画にあるがタグに1件も現れない要件 | **exit 1** |
| `missing_cell` | 計画で `true` の観点セルに実測0件 | **exit 1** |
| `unexpected_cell` | 計画で `false` / 省略のセルに件数がある | 警告 |
| `unknown_requirement` | タグに現れたが計画に無い要件 | 警告 |

**`normal` の照合は近似**（正常系はタグを持たないため、「観点タグを1つも持たないテスト≧1件」で充足とみなす。付け忘れと区別できない）。出力の `normal_is_approximate` にも明記される。

ランナーが読むのは `test-plan.yml`（宣言ファイル）であり、ドキュメント（テスト仕様）そのものは読まない。**テスト仕様が正**で、乖離したらテスト仕様に合わせて `test-plan.yml` を作り直す。

### 制限

- **plan が無ければ実測集計のみ。**丸ごと欠けた要件・正常系の欠落は出力から分からない（タグに一度も現れない要件は行自体が存在しない。`--report traceability` も同じ）。テスト仕様の側から探す
- plan があっても照合は**セルの有無のみ**。セルに件数があっても、**そのケースの期待値・境界の選び方が正しい**ことは検証しない
- **計画（test-plan.yml）自体の正しさ**も検証しない。呼び出し元のフローで受け入れ基準と対応表に照らして確認する

---

## `--report flaky`

`--repeat` の結果から揺れを検出する。**`--repeat` が2未満では判定できない。**

```bash
test-runner --suite e2e-full --env dev --repeat 3 --report flaky
```

```json
{
  "runs": 4,
  "flaky": [{"test": "f::ゆれる", "results": ["passed","failed","passed","failed"],
             "passed": 2, "failed": 2}],
  "always_failed": [],
  "stable": 1
}
```

| 分類 | 条件 |
|---|---|
| `flaky` | 成功と失敗の両方がある |
| `always_failed` | 全回失敗（**Flaky ではなく実際の失敗**） |
| `stable` | それ以外 |

テキスト出力では `quarantine.yml` への追加候補を YAML で出す（`due` は実行日から14日後）。あわせて「`critical` スイートは quarantine で除外しない」ことを表示する。

**Flaky は「気づいたら対応する」では見つからない。**nightly で探しに行くジョブを持つ。

---

## `--report suites`

定期的な のスイート棚卸し。

```json
{
  "suites": [
    {"name": "critical", "tests": 2, "files": 2, "scanned_files": 3,
     "min_count": 1, "quarantined": 0, "require_tags": ["@critical"]},
    {"name": "empty-suite", "tests": 0, "files": 0, "scanned_files": 3,
     "min_count": 1, "warning": "min_count 1 未満（タグの綴り間違いが疑われます）"}
  ],
  "quarantine": {"count": 1, "overdue": 0},
  "untagged_tests": 2
}
```

`warning` が入る条件は `min_count` 未満、または0件。

**`critical` の件数を毎回出すことが目的。**クリティカルパスのテストが消えたことに誰も気づかない状態を防ぐ。**誰がいつ出すかはプロジェクトが決める** — 変更のたびに自動で回す仕組みを持つならそこで、持たないなら試験フローの報告に件数を載せる(**このキットはその仕組みを配らないので、「自動で見てくれる」とは書けない**)。

---

## 出力レイアウト

```
artifacts/<run-id>/
├─ summary.json                              常に書く（--list / --dry-run 以外）
├─ <ステップ名>/<アダプタ名>.junit.xml        1回目
├─ <ステップ名>/<アダプタ名>.junit.runN.xml   --repeat の N 回目（N≧2）
└─ coverage/<アダプタ名>.cov                  形式に関係なく .cov
```

`run-id` は `YYYYMMDD-HHMMSS-NNNN`（UTC）。

**`artifacts/` は git 管理しない。**判断軸は「入力か出力か」で、出力は再生成できるうえ git は全バージョンを永久に保持する。
