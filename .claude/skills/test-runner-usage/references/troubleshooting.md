# 症状から引く診断手順

出典: `test-runner.md` 12章（制約・未実装・既知の弱点）を診断手順に変換したもの。
出典の docs/ は配布元(systest)の一次資料であり、このプロジェクトには無い。

**このリファレンスが扱うのは「ツールが期待どおり動いていない」場合。**テストが実際に落ちていて実装を直すのかテストを直すのかを判断する場面は `/verify-tests` §2(振り分け)と `/build` §3(落ちたテストを通す方向へ直さない)へ。

まず切り分ける。

```
exit 2 → 引数・設定の誤り。エラーメッセージに原因が出ている
exit 3 → 環境ガード違反。テストは1件も実行されていない
exit 1 かつ steps[].tests.total > 0 → テストが本当に落ちている（/verify-tests §2 と /build §3 へ）
exit 1 かつ steps[].tests.total == 0 → 空振り。以下を見る
exit 0 だが実行された気がしない → 以下を見る
```

---

## ステップが `skipped` になる

そのステップのコマンドが見つからない。3段階で確認する。

```bash
test-runner --gate f1-fast --dry-run       # 実行されるコマンドを表示
```

| 原因 | 確認方法 |
|---|---|
| `adapters.yml` にそのステップ名のコマンドが無い | `--dry-run` に出てこない。フォールバック先（`declarations.md` の表）も無い |
| **`gates.yml` のステップ名の綴り間違い**（`lnit:`） | 実行結果に見慣れないステップ名が出る。**自由キーなので警告されない** |
| **`adapters.yml` のステップ名の綴り間違い** | 同上。「コマンド未定義」で `skipped` |
| **テスト実行ゲートの予約キーの綴り間違い**（`inherit:`） | ステップとして扱われ `skipped` |
| そのアダプタの担当ファイルが0件 | `include` の glob か `root` を確認 |

**予約キーの正しい綴りは `--print-schema` で確認する。**

---

## スイートが0件・件数が合わない

```bash
test-runner --suite critical --list      # 対象テストを一覧する
test-runner --report suites              # 全スイートの件数と警告
test-runner --report matrix              # @req: と観点タグの付き方
```

| 原因 | 症状 | 気づく方法 |
|---|---|---|
| **タグの綴り間違い**（`@critcal`） | そのテストだけスイートに入らない | **`--list` のみ。**`min_count` は発見件数と閾値を比較するが、個々のタグ誤記までは特定できない。`--tag` を明示指定した実行なら0件で failed になる |
| `include` の glob がずれている | 全件0 | `--report suites` の `scanned_files` が0 |
| `include` を省略した | 対象が意図せず広がる（他スイートの include の総和にフォールバック） | `--report suites` の件数が想定より多い |
| `exclude_tags` に引っかかっている | 一部が消える | `--list` で出てこない |
| quarantine に載っている | 一部が消える | `summary.json` の `quarantine.count` |
| `default_scope: changed` で差分が空 | 0件 | `--base` を明示するか `--files` を渡す |

**`--list` を /build §3 の手順に入れているのは、1件のタグ間違いを検出する唯一の手段だから。**

### `--list` と実行件数が一致しないことがある

`{paths}` はファイル単位なので、**同一ファイル内に `exclude_tags` / quarantine の除外対象が同居していると、`--list` では消えているのに実行では走りうる**。除外を実行にも効かせるには、アダプタのコマンドに `{exclude_filter}`（除外テスト名の正規表現）を入れてネイティブランナーの除外オプションへ渡す（`references/placeholders.md`）。使わない場合は従来どおりで、同居があれば警告が出る（strict テスト実行ゲートでは failed。`test-runner.md` 12.7）。

また `default_scope: changed` は「変更された**テストファイル**」の選択であり、実装→テストの影響分析ではない。**実装だけを変更した PR では0件になる**（`min_count` があれば失敗、無ければ skipped で成功する）。

### 走査対象から外れているケース

以下は**そもそも走査されない**。

- 走査除外ディレクトリ: `.git` `.gradle` `.mypy_cache` `.next` `.pytest_cache` `.ruff_cache` `.tox` `.turbo` `.venv` `__pycache__` `artifacts` `build` `dist` `node_modules` `target` `vendor` `venv`、および `.` で始まるすべてのディレクトリ
- テストを抽出しない拡張子: `.json` `.yml` `.yaml` `.md` `.txt` `.sql` `.xml` `.snap` `.golden` など（`baseline.json` や `README.md` が幻のテストとして数えられるのを防ぐため）
- 4MB を超えるファイル

`.rb` `.java` `.kt` などは**ファイル単位で1テストとして扱われる**（スイートに含めた以上、件数0として黙って消えるのを避けるため）。

---

## JUnit が生成されないまま合格している

`{report_out}` を渡していない、またはアダプタのコマンドが JUnit を書かない場合、**非 strict では警告は出るが exit 0 のまま**で、件数・結果の検証がされずコマンドの終了コードだけで合否が決まる。`summary.json` にテスト件数が無いのがサイン。**テスト実行ゲートとして使う実行では `strict: true`（または `--strict`）を付ける**と、この状態が failed になる（雛形の f4-unit / f4-integration / f4-e2e は strict）。

## カバレッジ閾値が判定されない

**非 strict ではステップは通ってしまう**（strict なら `coverage:` を要求している場合に failed）。警告と `summary.json` を見る。

| 原因 | 確認 |
|---|---|
| コマンドに `{coverage_out}` が無い | 「カバレッジが出力されていません」の警告 + `summary.json` に `coverage` が無い |
| `scope: diff` で差分が0行 | `skipped_no_data: true`。仕様どおり（測るものが無い） |
| 比較基準の ref が見つからない | `warnings` に出る。全体スコープに読み替えられている。`--base` を明示する |
| Go で `branches` を設定した | **`go-cover` は分岐を持たない。**`branches_total` が0なら判定されない |
| カバレッジ形式が判定できない | exit 1（ステップ失敗）。`coverage:` キーを明示する |

パス照合は完全一致で見つからなければ末尾一致でも試すが、それでも合わない場合はカバレッジレポートのパス表記を確認する。

---

## exit 3 で止まる

**これは正常な動作。**回避策を探すのではなく、実行対象が間違っている。

```
error: suite "e2e-full" は environment "production" で実行できません。
       許可: [smoke]   (tests/environments.yml: production.suites)
```

| 原因 | 対応 |
|---|---|
| 本番でフルセットを流そうとした | 実行対象を `smoke` にする。本番は「テストする場所」ではなく「壊れていないことを確認する場所」 |
| `gates.yml` のステップに `env:` が書いてある | **`--env` を上書きする。**ガードもその実効環境で判定される |
| `require_confirm: true` の確認に失敗 | 環境名を正確に入力する |

---

## 「実行された気がしない」

```bash
test-runner --gate f4-integration --dry-run
```

`summary.json` の `steps[].discovered`（解決された件数）と `steps[].tests.total`（実行された件数）を比べる。**差があれば空振りしている。**

| discovered | tests.total | 意味 |
|:-:|:-:|---|
| 0 | 0 | スイート解決の問題（上記「スイートが0件」へ） |
| >0 | 0 | **`{report_out}` が無い**か、コマンドが実際にはテストを走らせていない |
| >0 | 少ない | ランナー側のフィルタ（`{name_filter}` の渡し方）が効きすぎている |

---

## 設定が効いているはずなのに効かない

**「読むだけ」の設定を評価しようとしていないか確認する。**

`flaky_retries` `retain_evidence` `require_review` `require_regression_test` `metrics_compare` `pr_diff_limit` は**ランナーが読むだけで何もしない**。それぞれ CI・ブランチ保護・PR レビュー・アダプタの責務（`declarations.md` の表）。

`allow.write` / `allow.destructive` / `allow.external` も**ランナーは止めない**。`TESTRUNNER_ALLOW_*` として渡すだけで、抑止は `tests/support/guards.*` の責務。この実装が無ければ宣言は宣言のままである。

---

## `--list` / `--dry-run` が exit 0 を返す

**仕様。**ステップ内でエラーが起きても `summary.json` を書く前に返るため exit 0 になる。

- `--list` は `min_count` を検証しない
- スイート解決のエラー（不正な `--grep` など）でステップは `failed` になるが終了コードは 0

ガード違反と引数エラーは `--list` でも exit 3 / 2 になる。

---

## `artifacts/` が git に入ってしまう

`tests/.gitignore` は **`tests/` 配下にしか効かない。**ランナーが書くのはルート直下の `artifacts/`。

```bash
git check-ignore -q artifacts/ && echo OK || echo "NG: ルートの .gitignore に追記が必要"
```

`test-runner` は毎回この除外を検査して警告し、`test-runner setup` は exit 1 にする。

---

## モノレポで動かない

**1回の実行は1ルートだけを見る。**

ルートは「カレントディレクトリから親方向へ辿って最初に見つかる `tests/gates.yml`」で決まる（無ければ `.git`）。パッケージごとに `tests/` を置いている場合は、そのパッケージ内で実行するか `--root` を指定する。

```yaml
- run: ./tests/tools/test-runner --gate f4-integration
  working-directory: packages/web
```

`git diff --name-only` はリポジトリルート基準でパスを出すが、ランナー側で接頭辞を外す変換が入っているので、**そのパッケージの `tests/` を `--root` で指して呼ぶ**(上の行のとおり)。**`cd` で移動してから裸の名前で呼ばない** ★ — 配る設定の許可は `./tests/tools/test-runner` の形で与えてあり、**繋いだコマンドは前後が別々に判定される**ので、移動した先からの裸の呼び出しは許可に当たらず、**無人で回す実行がそこで止まる。**

---

## 検出できない設定ミスの一覧

**ここに挙げたものは警告されない。**知っておくしかない。

| ミス | 何が起きるか | 気づく方法 |
|---|---|---|
| `gates.yml` のステップ名の綴り間違い | 未知ステップ扱いで `skipped` | 実行結果に見慣れない名前。strict テスト実行ゲートなら failed |
| テスト実行ゲートの予約キーの綴り間違い | ステップ扱いで `skipped` | 同上 |
| `adapters.yml` のステップ名の綴り間違い | コマンド未定義で `skipped` | 同上。strict テスト実行ゲートなら failed |
| タグの綴り間違い | そのスイートに入らない | `--list`。`--tag` 明示指定なら0件で failed |
| `include` の省略 | 対象が意図せず広がる | `--report suites` |
| `{coverage_out}` の欠落 | 閾値が判定されない | 警告。strict で `coverage:` 要求なら failed |
| `healthcheck` に危険なコマンド | **スイートを持たないためガードを通らず、本番でも実行される** | なし（設計上の境界） |

`suites.yml` / `environments.yml` / `gates.yml` のステップ属性 / `coverage` / `quarantine.yml` の**未知キーは訂正候補付きで警告される**（自由キーである上表のものを除く）。
