---
id: environments
version: 1.0.0
updated: <YYYY-MM-DD>
source:
  - docs/01-requirements/system.md
  - docs/02-design/architecture.md
summary: <1行>
keywords: [開発環境, コマンド]
# verified: verify 系フロー(/verify-docs、03層代表は /verify-impl)だけが書く
---

<!-- ここに書かれたコマンド文字列が正であり、全スキルがこの厳密な文字列を使う。
     見出し構造を変えないこと(スキルが見出し名で参照する)。
     未定の項目は削除せず「未定(いつ決めるか)」と書く。
     ★ テストの依存と環境のスクリプト(tests/scripts/ の下)を書くのは /test-env で、
     決めた文字列を報告に出す。この表へ書き写すのは /build である。
     仕組みそのものの説明は docs/03-impl/environments/ に残す。 -->

# 開発環境・開発ツールの基本設計

## セットアップ手順

1. <>

| 用途 | コマンド |
|---|---|
| セットアップ | `<厳密な文字列>` |
| テストの依存を入れる | `<厳密な文字列>` |
| テスト環境の起動 / 停止 / 作り直し | `<厳密な文字列>` / `<>` / `<>` |

## lint・テストコマンド

<!-- レベルごとに分けて厳密な文字列で書く。既存リポジトリなら実際に実行して確認した文字列。
     テスト基盤導入済みの既定形: 単体 ./tests/tools/test-runner --gate f4-unit --env local、
     結合 ./tests/tools/test-runner --gate f4-integration --env local、
     E2E ./tests/tools/test-runner --gate f4-e2e --env local、
     重要テスト ./tests/tools/test-runner --gate f4-critical --only <試験区分> --env local、
     要件とテストの対応の一覧 ./tests/tools/test-runner --report traceability --json。
     構築フローの実装ループは ./tests/tools/test-runner --gate f1-fast --env local。
     f1-fast を裸で呼ぶと unit+integration 全件。F1 では docs/03-impl/tests/<module>.md の対応表に載るテストの識別子・パスを --grep / --files に渡し、触ったモジュールに絞るのが既定。
     ★ --grep / --files は f1-fast の unit と integration の両方に掛かる。片方の試験区分しか持たないモジュールを絞ると、持っていない側が0件になる — --grep(と --tag)なら run 全体が不合格、--files だけならその側のステップが黙って skipped になって通る。どちらも困るので f1-unit / f1-integration に替える(存在する試験区分だけを呼ぶ)。
     ★ f4-critical は --only で、その run が回す試験区分に当たるステップだけに絞って呼ぶ(丸ごと回すと単体だけの run が E2E 環境に縛られる)。
     ★ 資格情報の混入検査(secret_scan)は F1 の各テスト実行ゲートと F4 の f4-unit が呼ぶ静的チェックである。コマンドを adapters.yml の checks: に書かないと F1 では skipped のまま通り続けるので、この表にも行を持たせて担当と文字列を決める(言語に紐づかない検査なのでアダプタ側には書かない — 多言語リポジトリで言語の数だけ走る)。**f4-unit は strict なので、空のままでは unit が green にならない = 出荷できない。** 道具の選定はプロジェクトの判断(例: gitleaks / trufflehog / git-secrets)。
     ★ 要件とテストの対応の突き合わせに使うレポートも、コマンドとしてこの表に持たせる(/verify-tests の「表の網羅」③ が打つ。表に無いコマンドを発明させないため)。
     資格情報の値はこのファイルにもテストにも書かない(delegation.md DS-01)。
     置き場は tests/.env.<環境名>、入手先の案内は tests/environments-guide.md(配布物2)。 -->

| 用途 | コマンド | 備考 |
|---|---|---|
| lint | `<>` | <> |
| 資格情報の混入検査 | `<>` | adapters.yml の `checks.secret_scan` にも同じ文字列を書く |
| 単体テスト | `<>` | <> |
| 結合テスト | `<>` | <> |
| E2Eテスト | `<>` | <未定(いつ決めるか)> |
| 重要テスト(除外なし) | `<>` | `f4-critical`。`--only <試験区分>` で絞って呼ぶ |
| 要件とテストの対応の一覧 | `<>` | `--report traceability`。`/verify-tests` の「表の網羅」が使う |
| 構築時(単体+結合) | `<>` | `f1-fast`。`--grep` / `--files` で触ったモジュールに絞る |
| 構築時(単体だけ) | `<>` | `f1-unit`。結合テストを持たないモジュール |
| 構築時(結合だけ) | `<>` | `f1-integration`。単体テストを持たないモジュール |
| build | `<>` | <> |

## コンテナ・実行環境

| サービス | イメージ・起動方法 | ポート | 依存 |
|---|---|---|---|
| <> | <> | <> | <> |

### ビルドとテストの版の固定

<!-- 単体・結合・E2E のテストを、出荷物を作るビルドと同じ版で走らせるための宣言
     (.claude/directions/delegation.md §2.4)。**この見出しが在ることが宣言であり、
     在れば、版が一致しない / 確かめられないテストの実行は合格にならない。**
     見出しを消さない。埋めるのは /build である。
     「固定している場所」には版を書き写さず、版が書いてあるファイルを名指す
     (版を2か所に書くと、いつか食い違う)。 -->

| 項目 | 固定している場所 | テストの環境での一致の確かめ方 |
|---|---|---|
| 言語の処理系とツールチェーン | <> | <> |
| 実行基盤(コンテナの基底イメージ・OS) | <> | <> |
| 製品の依存(ロックファイル) | <> | <> |

ビルドとテストを走らせる環境: <>

## ブラウザQAの宛先 allowlist

<!-- E2E と探索的QA(**両方のレーン**)が到達してよい宛先の、唯一の正。
     節の名前はブラウザ由来だが、**ここの値は /browser-qa と /cli-qa の両方が負う**
     (.claude/skills/cli-qa/SKILL.md §2)。
     **外部へ出る宛先を書かない** — 委任の既定が「外部ネットワークに出ない」だからである
     (.claude/directions/delegation.md DS-01)。
     それを強制する機構(MCP の起動引数・Chrome の名前解決規則・Playwright の launchOptions)の正は
     .claude/directions/orchestration.md §1.1.2 である。
     画面を持たないプロジェクトは、**ブラウザでの実行条件の側だけ**を「適用外(画面なし)」の
     1行にする(**見出しは削除しない**)。
     ★ **下の宛先の表は消さない**(2026-09-15。inspection-28 C-19)—
     **あの表は画面とコマンドの共通の正**であり、画面が無くてもコマンドがネットワークへ
     出るなら、探索的CLI QA はあそこを読んで宛先を決める。
     節ごと1行に潰すと、**コマンド側が使う宛先の一覧まで消える。**
     消してよいのは、アプリの起動コマンド・アプリの URL・E2E のシードとリセットの
     コマンドといった、**ブラウザを動かすための条件だけ**である。
     ★ **それは qa 試験区分を外す宣言ではない** — サブコマンドが在れば探索的CLI QA が走る。
     **qa 試験区分の適用外を宣言する場所は1つだけで、02 の「操作面の宣言」の節である**
     (docs/02-design/system.md。.claude/directions/02-design.md が正)。
     ここの1行は、そのうち**ブラウザのレーンが走らない**ことを言うだけである。 -->

| 宛先 | 値 |
|---|---|
| スキーム | `http` / `ws`(画面が WebSocket を使うなら **`ws` を必ず書く** — 突き合わせはスキームまで見るので、`http` だけだとライブ表示に入れない) |
| ホスト | `localhost` / `127.0.0.1` / `[::1]`(**この値を強制側へそのまま貼らない** — 綴りは `.claude/directions/orchestration.md` の「1.1.2 ブラウザQAの口は MCP で足す」が正である。) |
| docker network | `<CIDR>` / `<compose のサービス名>` |
| 追加の宛先 | `<ホスト / CIDR>` — `<なぜここへ到達する必要があるのか>`(**理由を書けないなら足さない**。同じ構内や VPN の私設アドレスなど) |
| この表に無いもの | **許さない**(公開インターネットへは出ない。これが天井であり、床は上の `ホスト` の行である) |

### ブラウザ検証の実行条件

<!-- /browser-qa が読むのは、この文書を含めて4つだけである(.claude/directions/reading.md)。
     起動に要るものがここに無ければ、そのレーンは立ち上げられないか、読む量の上限を破るかの
     どちらかになる。
     ★ **アプリ起動・E2E シード・E2E リセットの3行は、この表だけが持つ**(持ち主。
     conventions.md §4.1)。docs/03-impl/tests/e2e.md と docs/03-impl/tests/strategy.md は
     **写さずにこの節を参照する** — 逐語で一致させる運用は 3枚の写しになり、必ずずれた
     (conventions.md §4.2)。**値を変えるときに直すのはここ1か所である。** -->

| 用途 | コマンド・値 |
|---|---|
| アプリ起動 | `<厳密な文字列>` |
| アプリの URL | `<http://localhost:3000>` |
| E2E シード | `<厳密な文字列>` |
| E2E リセット | `<厳密な文字列>` |

### CLI 検証の実行条件

<!-- /cli-qa と cli の試験が読む、**このプロジェクトでコマンドをどう叩くか**の唯一の正。
     .claude/skills/cli-qa/SKILL.md §1 の 2 がこの節を名指しているので、**見出しを変えない**。
     ★ **隔離をここに書くのが要点である** — コマンドの試験の事故は、ほぼすべて
     「開発者自身の環境を壊す」形で起きる(なぜ要るかと一般的な手口は
     .claude/skills/test-design/references/cli-variant.md「テスト環境の隔離 の CLI 版」。
     **このプロジェクトで実際に打つものはここが持つ**)。
     人が直接打つサブコマンドを持たないプロジェクトは、本文を「適用外(コマンドの面なし)」の
     1行にする(**見出しは削除しない**)。これも qa 試験区分を外す宣言ではない — 上の節と同じ。 -->

| 用途 | コマンド・値 |
|---|---|
| 成果物のビルド | `<厳密な文字列>` |
| 実行ファイルの場所 | `<dist/bin/my-tool。ビルドの出力先>` |
| 隔離した作業環境の用意 | `<厳密な文字列。$HOME・設定・資格情報をこの木の外へ漏らさない作り方>` |
| 隔離した作業環境の後始末 | `<厳密な文字列>` |
| 壊してはならないもの | `<この隔離の外に在って、触られると困るもの。無ければ「なし」>` |

## CI

| タイミング | 実行内容 | 失敗したらどうなるか |
|---|---|---|
| <push> | <lint + 単体 + 結合> | <マージ不可> |

## コールグラフ抽出設定

<!-- build-callgraphs.py の設定は .claude/scripts/callgraph-config.local.json が実体。
     ここにはその要約と、人間が知っておくべき限界を書く。
     規範: .claude/directions/callgraphs.md -->

| 項目 | 値 |
|---|---|
| internal_roots | `.`(既定のまま — local の配列は和集合でマージされ **local では絞れない**。当面の絞り込みは `excludes` に兄弟パッケージ等を列挙する。恒久策はスクリプト修正(汎用的な直しなので `/kit-improve` でいつでも)) |
| 有効な言語 | <python> |
| 抽出器が無い言語 | <なし。覆われない領域があるなら明記: > |
| Tier | <python=2(標準 ast) / go=2 / typescript=2 / rust=2(tree-sitter) / infra=2> |
| ツール環境 | `.claude/.venv`(キット専用。**プロジェクトの環境には入れない**) |
| 用意するコマンド | `python3 .claude/scripts/setup-tools.py` |
| 任意ツール | <未使用> / <hcl2json を .claude/.tools に導入済み(Terraform 用)> |
| 出力先 | `docs/03-impl/callgraphs/`(常に SSOT — `.claude/directions/callgraphs.md` §3.1)。解決は `resolve-callgraph-out.py --ssot` |
| 鮮度検査 | `CG_OUT=$(python3 .claude/scripts/resolve-callgraph-out.py) && python3 .claude/scripts/build-callgraphs.py --out "$CG_OUT" --check` |
| CI で検査するか | <はい: setup-tools.py → `if CG_OUT=$(python3 .claude/scripts/resolve-callgraph-out.py); then 上の --check が非ゼロならビルド失敗; else echo "鮮度検査は判定不能(タスク2件以上)"; fi` — 失敗させるか・判定不能と出して飛ばすかを `if` 分岐で確定する(`.claude/directions/callgraphs.md` §3.1 の `if` 形)> |

## 未解決事項

<!-- 通常は空(「なし」)。未決点は構築記録(docs/build-records/)に置く(CLAUDE.md 原則7)。
     この節は逆生成(/retrofit)が「仕様か不具合か分類できない挙動」を置く場所で、
     空でない間はこの仕様ドキュメントの検証が通らない(/verify-docs の検査 C — 非空の未解決事項は検証を止める)。 -->

- なし
