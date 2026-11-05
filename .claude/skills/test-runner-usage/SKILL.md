---
name: test-runner-usage
description: test-runner コマンドの実行と、tests/ 配下の6つの宣言ファイル（suites.yml / environments.yml / gates.yml / adapters.yml / quarantine.yml / test-plan.yml）の作成・修正・診断。skip だらけになる、テスト実行ゲートやスイートを実行する、テストの実行方法を調べる、adapters.yml を埋める、ステップが skipped になる、カバレッジが判定されない、スイートが0件になる、exit 3 で止まる、タグが効かない、といったときに使う。Use when running tests through test-runner, authoring or debugging suites.yml / gates.yml / adapters.yml / environments.yml / quarantine.yml, or diagnosing exit codes and silently skipped steps.
---

# test-runner の使い方

`test-runner` は**テスト実行の単一エントリポイント**。人・CI・コミット前チェックがすべてこのコマンドを呼ぶ。

**このスキルはツールの操作を扱う。**テストが実際に落ちていて「実装を直すのかテストを直すのか」を判断する場面は、このスキルではなく `/verify-tests` §2(振り分け)と `/build` §3(落ちたテストを通す方向へ直さない)へ。

**フローではなく、SSOT を書かない参照スキルである。**実行コマンドの正は `02-design/environments.md`。以下のコマンドは操作例であり、フローではその表のセルを逐語で実行する。テスト仕様の正は `docs/03-impl/tests/`(構造は `03-impl.md`「tests/」)。導入は `/setup`、ケース導出は `/test-design`、**環境を整えるのは `/test-env`**、症状からの振り分けは `references/environment.md` を読む。

**このスキルが負う規範の節** — `.claude/directions/reading.md` の `/test-runner-usage` の行。

## 一次情報はコマンドから出る

**記述に迷ったら、まずこれを実行する。**実行時に使っている定義から生成されるので、どのドキュメントよりも正しい。

**実際に打つのは `./tests/tools/test-runner` である** ★ — この資料では以降 `test-runner` と略記するが、**その名前で PATH は通っていない**(配る設定の許可も `./tests/tools/test-runner` の形で与えてある)。起動の仕組みは下の「どのディレクトリから起動してもよい」。

```bash
test-runner --print-schema          # 全キー・プレースホルダ・ステップ順・終了コード
test-runner --print-schema --json
test-runner help
```

`tests/` が未配置でも動く。

## 起動方法

実体は Go の単一バイナリ。プロジェクトには `tests/tools/test-runner`（`uname` を見て `tests/tools/bin/test-runner-<os>-<arch>` を exec するラッパ）として入っている。

```bash
./tests/tools/test-runner --gate f1-fast --files "src/order/order.test.ts tests/integration/order.test.ts"
```

**どのディレクトリから起動してもよい。**カレントディレクトリから親方向へ辿り、`tests/gates.yml` を持つ最も近い階層をルートにする（無ければ `.git` のある階層）。以降このドキュメントでは `test-runner` と表記する。

## 6つの宣言ファイル

`test-runner` は**テストの実行方法を持たない。**宣言を読んで各言語のランナーへ翻訳するだけ。

```
gates.yml        どのステップを、どの条件で実行するか
   ↓ suite:
suites.yml       そのステップの対象テストは何か
   ↓
quarantine.yml   そのうち外すものはあるか
   ↓
environments.yml その実行は許可されているか   ← ここで止まる場合がある（exit 3）
   ↓
adapters.yml     実際に打つコマンドは何か     ← これが無いと1件も実行できない
```

**`adapters.yml` が空だとテストは1件も動かない。**雛形は全部コメントアウトされた状態で配布される。導入時に必ず埋める。

6つめの `test-plan.yml`（任意）はこの連鎖の外にある。テスト仕様の対応表と「テスト設計の判断」で定めた要件 × 観点の写しで、`--report matrix` が実測との照合に使う（テスト仕様が正。照合はセルの有無のみ）。

各ファイルの全キーは `references/declarations.md`。

## 典型コマンド

```bash
# フローのテスト実行ゲートを評価する
test-runner --gate f1-fast --grep "@req:FR-order-01-2" # モジュールの対応表に載る識別子の例
test-runner --gate f1-unit --grep "@req:FR-tax-03-1"  # 単体しか持たないモジュールを絞るとき
test-runner --gate f1-integration --files "tests/integration/order.test.ts"  # 結合だけのとき
test-runner --gate f4-unit                   # 試験フローの単体
test-runner --gate f4-integration            # 試験フローの結合テスト
test-runner --gate f4-e2e --env dev              # 試験フローの E2E
test-runner --gate f4-critical --only unit    # 重要テストを除外なしで（回す試験区分だけ --only で絞る）
test-runner --gate f4-critical --only e2e --env dev   # e2e を回す run のとき
test-runner --suite smoke --env production   # 本番スモーク

# 構築フロー: docs/03-impl/tests/<module>.md の対応表からテストのパスを渡す例
test-runner --gate f1-fast --files "src/order/order.test.ts tests/integration/order.test.ts"

# 実装中の高速ループ
test-runner --suite unit --watch
test-runner --suite unit --grep "税率"

# タグが効いているかの確認（省略禁止。1件のタグ誤記を検出する唯一の手段）
test-runner --suite critical --list

# 新規シナリオの安定確認 / Flaky 検出
test-runner --suite e2e-full --env local --grep "注文ステータス" --repeat 3
test-runner --suite e2e-full --env dev --repeat 3 --report flaky

# レポート
test-runner --report traceability             # 受け入れ基準 ID → テスト
test-runner --report matrix                   # 要件 × 観点の実測集計（test-plan.yml があれば照合して欠落を exit 1 に）
test-runner --report suites                   # スイート棚卸し・critical 件数
test-runner setup                             # 設定の健全性検査（何も変更しない）
```

**F1 の既定は、触ったモジュールの対応表に載るテストの識別子・パスを `--grep` / `--files` に渡すこと。**裸の `--gate f1-fast` は unit+integration 全件になる。絞った結果が0件なら、それは合格ではなく対応表の欠落である — 絞り込みを疑い、`--list` で確かめる。

**ただし、そのモジュールが片方の試験区分しか持たないときは `f1-fast` を使わない** ★ — `f1-fast` は unit と integration の2ステップを持ち、`--grep` / `--files` は**両方に掛かる**。単体テストしか無いモジュールを絞ると結合側が0件になる。**0件の出方は指定の仕方で違う**:

| 絞り方 | 持っていない側が0件になったとき |
|---|---|
| `--grep`(と `--tag`) | 「明示したフィルタに一致するテストが0件」として **run 全体が不合格**(`strict` の有無に依存しない) |
| `--files` だけ | **その側のステップが黙って `skipped`** になり、通る（`strict` を持たない `f1-*` では失敗に昇格しない。在る側のステップは走る） |

前者は製品に不具合が無いのに止まり、後者は**何を確かめていないかが報告に出ないまま緑**になる。どちらも困るので、**存在する試験区分だけを呼ぶ `f1-unit` / `f1-integration` に替える**。ここで要らない結合テストを間に合わせで足すのは、規範が求めていない作業である。

**`f4-critical` は、除外を一切かけずに重要テストを通すテスト実行ゲートである** ★ — `f4-unit` / `f4-integration` / `f4-e2e` が呼ぶスイートは `@flaky` と一時除外（`quarantine.yml`）を除外するので、`@critical` を付けたテストが一時除外に入ったままでも各試験区分は緑になる。`f4-critical` は `critical-unit` / `critical-integration` / `critical-e2e`（いずれも `exclude_tags: []`）を通してその除外を取り戻す。**呼ぶときは `--only` で、その run が回している試験区分に当たるステップだけに絞る** — 丸ごと回すと、単体だけの run が E2E 環境の可用性に縛られる（手順の正は `/verify-tests` §1）。`@critical` が0件のプロジェクトでは、そのステップが「対象テスト0件」の skipped になる — 導入直後の正常な状態である。

`--gate` と `--suite` はどちらか必須（両方指定すると `--gate` が優先）。`--only` はテスト実行ゲート実行時のみ有効。

## 終了コードの契約

| コード | 意味 | 見方 |
|:-:|---|---|
| `0` | 合格 | |
| `1` | **テスト実行ゲート不合格** | テスト失敗／カバレッジ未達／`min_count` 違反／`forbid_skip` 違反／`require_negative_tests` 違反／`--tag`・`--grep` 明示指定で対象0件／strict（`strict: true` か `--strict`）での証拠欠落・未定義 skipped／`--report matrix` と `test-plan.yml` の照合失敗／quarantine 期限切れ／`setup` の未解決項目 |
| `2` | **引数・設定の誤り** | 未知のテスト実行ゲート・スイート・環境／YAML 解析失敗／`--only` の不一致／未知のプレースホルダ／ルートが見つからない |
| `3` | **環境ガード違反** | 許可されていないスイートを実行しようとした。**テストを1件も実行していない** |

**`1` と `3` の区別が重要。**`3` は「本番に危険な実行を投げた」ことを意味する。CI で検出したい場合はこのコードを見る。

## 結果の読み方

`artifacts/<run-id>/summary.json` が機械可読な出力（`--list` / `--dry-run` 以外では常に書かれる）。**まず見るべきは3つ。**

| フィールド | 何が分かるか |
|---|---|
| `steps[].discovered` と `steps[].tests.total` | 前者は解決された件数、後者は実際に実行された件数。**差があれば空振りしている** |
| `steps[].reason` | 失敗理由。カバレッジ未達の実測値もここに出る |
| `warnings` | 落とすほどではないが効いていない設定（base ref が無い、`artifacts/` が gitignore されていない 等） |

`quarantine.count` は一時除外中の件数。**一時除外中のテストは「守られていない機能」**なので、増加傾向を見る。

レポート4種の詳細は `references/reports.md`。

### 人が結果を見る手段は test-runner の外にもある

`test-runner` が出すのは `summary.json` とレポート4種（機械可読寄り）。**E2E の
結果を人が読むなら Playwright の HTML レポートのほうが早い。**スクリーンショット・
動画・trace が埋め込まれ、trace viewer も同梱される。

| 見たいもの | 開くもの |
|---|---|
| E2E の全体像・失敗の詳細 | `artifacts/<run-id>/e2e-report/index.html` |
| **最終状態の画面** | `artifacts/<run-id>/e2e/<テスト名>/final.png`（`final-skipped.png` / `SKIPPED.txt` があるテストは**実行されていない**） |
| 操作ごとの画面遷移 | `artifacts/<run-id>/e2e/<テスト名>/steps/index.html` |
| **なぜ落ちたかの深掘り** | trace viewer（`playwright show-trace <trace.zip>`、または <https://trace.playwright.dev/> に zip をドラッグ&ドロップ） |
| 件数・カバレッジ・機械処理 | `artifacts/<run-id>/summary.json` |

**レポートサーバは `tests/scripts/serve-report.sh` で起動する。手で `playwright
show-report` を叩かない。差し替えはスクリプトに任せる（内部で `pkill` を使う）。**

```bash
./tests/scripts/serve-report.sh          # artifacts/<run-id>/*-report の中から最新のものを自動検出し 0.0.0.0:9323 で出す → http://<host>:9323
PORT=9400 ./tests/scripts/serve-report.sh  # 別ポートで出す
```

- **前のサーバが残ったまま同じ URL を案内すると、前の run の結果で合否を判断する
  ことになる。**このスクリプトは毎回、**同じポートで動いている既存の `show-report`
  だけを `pkill -f` で止めてから**最新 run に差し替える（試験成果物は
  run-id で突き合わせる前提。**規則の正は配布元の規範であり、このプロジェクトには同梱されない**）
- 起動確認はポートの LISTEN 有無で行う（`ss` があれば `ss`、無ければ `lsof` で代替）。
  失敗したら「起動に失敗した可能性があります」とログの場所を出して終わる
- 既定の `0.0.0.0` はコンテナ・リモート開発サーバから開くため固定（切り替え手段は無い）。
  **同一ネットワークの誰からでも開ける**ので、共有ホストではポート転送（`ssh -L`）を使う
- `<run-id>` 指定・`status`・`stop` のサブコマンドは無い。常に最新の run を自動検出する。
  完全に止めたいだけなら `pkill -f "show-report .*--port <PORT>([[:space:]]|$)"`（`\b` は
  BSD/macOS の `pkill` が解釈できず静かに不一致になる。`--port` がコマンド末尾に来る
  起動のされ方もあるため `$` の終端一致も要る）を直接叩いてよい
  （サブコマンドが無いので、これが唯一の手動停止手段）

レポートが出ていない場合は `playwright.config.ts` に html レポーターが無い
（`tests/e2e/README.md`「試験成果物の出力先」）。

## 想定どおり動かないとき

**エラーにならず静かに効かない設定ミスが複数ある。**症状から引く診断手順を `references/troubleshooting.md` に置いた。よくある3つだけ先に挙げる。

| 症状 | 最初に疑うところ |
|---|---|
| ステップが `skipped` になる | `adapters.yml` にそのステップ名のコマンドが無い。またはステップ名の綴り間違い（**自由キーなので検出されない**。strict テスト実行ゲートなら failed で露出する） |
| カバレッジ閾値が判定されない | コマンドに `{coverage_out}` が入っていない。非 strict ではステップは通ってしまう（strict なら failed） |
| スイートが0件・件数が合わない | タグの綴り間違い（`@critcal`）。`--list` で確認する。`min_count` は発見件数と閾値を比較するが、個々のタグ誤記までは特定できない。`--tag` を明示指定した実行なら0件で failed になる |

## やってはいけないこと

- **`--update-golden` を CI や自動処理で実行しない。**保存済みの期待値ファイル(golden ファイル)の自動更新は互換性チェックの無効化と同義。人が明示的に叩き、差分は PR でレビューする
- **`--env production` で `smoke` 以外を流そうとしない。**`environments.yml` の `production.suites: [smoke]` が exit 3 で構造的に弾く。弾かれたら回避策を探すのではなく、実行対象が間違っている
- **`gates.yml` のステップを YAML の順序で制御しようとしない。**実行順は固定（`lint → types → ... → unit → ... → e2e → ...`）。速く軽いものから失敗を検出するため
- **`flaky_retries` に再実行を期待しない。**ランナーは読むだけで再実行しない。再実行の担当はプロジェクトが決める(自動で回す仕組みを持つならそこ、持たないなら試験フローの手順)

## ランナーが弾けない境界

**ランナーが強制できるのは「何を実行するか」までで、「テストが何をするか」は強制できない。**

`environments.yml` に `allow.external: blocked` と書いても、ランナーは `TESTRUNNER_ALLOW_EXTERNAL=blocked` を環境変数で渡すだけ。実際に通信を遮断したり、`test_data_prefix` を持たない書き込みを検出したりするのは `tests/support/guards.*` の責務であり、配布物2に `tests/support/guards.ts` / `network.ts` / `fixtures.ts` の参照実装が同梱されている。プロジェクトへの適用と、テストへの配線を確認する。

つまり宣言だけでは本番の安全は守られない。ケイパビリティを読む側の実装が無い状態を、あるものとして扱わない。

## 終わるときは「次にやること」を出す

**実行結果を報告して終わらない。**「落ちた」「通った」だけでは受け取った人が
次に何をすべきか分からない。**必ず次を出力する。**

```
<コマンド> の結果: <合格 / 不合格（exit N）>

  実行された    <ステップ名と件数。★ skipped は件数0の理由まで書く>
  実行されなかった <0件・skipped のステップと、その理由>
  レポート      <artifacts/<run-id>/e2e-report/index.html。
                 開いて見せるなら ./tests/scripts/serve-report.sh で起動し、
                 ★ URL（http://<host>:9323）と run-id まで書く
                 （手で show-report を叩かない。完全に止めたいだけなら
                 pkill を直接叩いてよい）>

次にやること
  <落ちたステップごとに、実装を直すのかテストを直すのか、
   それとも設定（アダプタ未定義・タグ誤記）の問題かの切り分け>
```

**`skipped` と `0 件` を「問題なし」として報告しない。**アダプタ未定義・タグの
綴り間違いで静かに空振りしているだけのことが多い。落ちたテストの直し方
（実装かテストか要件か）の判断は `/verify-tests` §2(振り分け)と `/build` §3(落ちたテストを通す方向へ直さない)へ。

## 参照

| 知りたいこと | ファイル |
|---|---|
| 6つの宣言ファイルの全キーと既定値 | `references/declarations.md` |
| コマンドテンプレートのプレースホルダ19種 | `references/placeholders.md` |
| 症状から引く診断手順 | `references/troubleshooting.md` |
| summary.json / traceability / flaky / suites | `references/reports.md` |
| clone 後の依存・環境の構築と検証 | **`/test-env`**(症状からの振り分けだけなら `references/environment.md`) |
