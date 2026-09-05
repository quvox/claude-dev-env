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
     未定の項目は削除せず「未定(いつ決めるか)」と書く。 -->

# 開発環境・開発ツールの基本設計

## セットアップ手順

1. <>

| 用途 | コマンド |
|---|---|
| セットアップ | `<厳密な文字列>` |

## lint・テストコマンド

<!-- レベルごとに分けて厳密な文字列で書く。既存リポジトリなら実際に実行して確認した文字列 -->

| 用途 | コマンド | 備考 |
|---|---|---|
| lint | `<>` | <> |
| 単体テスト | `<>` | <> |
| 結合テスト | `<>` | <> |
| E2Eテスト | `<>` | <未定(いつ決めるか)> |
| build | `<>` | <> |

## コンテナ・実行環境

| サービス | イメージ・起動方法 | ポート | 依存 |
|---|---|---|---|
| <> | <> | <> | <> |

## ブラウザQAの宛先 allowlist

<!-- E2E と /browser-qa のブラウザが到達してよい宛先の、唯一の正。
     **外部へ出る宛先を書かない** — 委任の既定が「外部ネットワークに出ない」だからである
     (.claude/directions/delegation.md DS-01)。
     それを強制する機構(MCP の起動引数・Chrome の名前解決規則・Playwright の launchOptions)の正は
     .claude/directions/orchestration.md §1.1.2 である。
     UI を持たないプロジェクトは、この節の本文を「適用外(UI 無し)」の1行にする
     (**見出しは削除しない**)。その1行が `qa` 試験区分の「適用外」の宣言を所有する
     (.claude/directions/02-design.md)。 -->

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
     どちらかになる。docs/03-impl/tests/e2e.md の「テスト環境」と**同じ値を持つ行は逐語で一致させる**こと
     (アプリ起動=起動するサービス、E2E シード=シードコマンド、E2E リセット=リセットコマンド)。
     どちらの表も相手に無い行を持ってよい。 -->

| 用途 | コマンド・値 |
|---|---|
| アプリ起動 | `<厳密な文字列>` |
| アプリの URL | `<http://localhost:3000>` |
| E2E シード | `<厳密な文字列>` |
| E2E リセット | `<厳密な文字列>` |

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
| Tier | <python=2(標準 ast) / go=2 / typescript=2(tree-sitter) / infra=2> |
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
