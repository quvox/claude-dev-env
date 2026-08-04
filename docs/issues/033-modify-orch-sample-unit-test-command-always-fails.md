---
id: 033-modify-orch-sample-unit-test-command-always-fails
type: modify
severity: 低
found: 2026-08-03
found_in: task-impl-depth の /task-close 事前検査(§1-3 で lint・単体テストを実際に実行した)
related: docs/02-design/environments.md, docs/03-impl/tests/strategy.md, docs/03-impl/tests/sample-project.md, FR-orch-09
summary: 単体テストとして掲げられている `cd examples/orch-sample && pytest` はテンプレート上では必ず失敗する(実装がスタブのため)。テスト状態も「実装済み」と書かれている
---

# 033 自己検証題材の単体テストコマンドが常に失敗する

## 事象

`docs/02-design/environments.md`「lint・テストコマンド」と `docs/03-impl/tests/strategy.md:29` は
単体テスト(自己検証題材)として次を掲げる。

```
cd examples/orch-sample && pytest
```

実行すると **12 failed**(すべて `NotImplementedError`)になる。これは**設計どおり**である:
`examples/orch-sample/README.md` は「テンプレートには**テスト(期待仕様)だけ**を置き、実装は
スタブにして worker が完成させる」と明記しており、テンプレートは**わざと未実装**である。
テストが通るのは `make orch-sample` で `workspace/orch-sample/` へ scaffold し、
オーケストレーターが実装を完成させた**作業コピー**の側だけである。

再現手順:

1. `cd examples/orch-sample && pytest` を実行する。
2. 12 件が `NotImplementedError` で失敗することを確認する。
3. `examples/orch-sample/README.md` を読み、これが意図された状態であることを確認する。

## 影響

- **`/task-close` や `/implement` が `environments.md` の厳密な文字列に従って単体テストを走らせると、
  必ず失敗する。** 「テストがグリーン」というゲートを機械的に判定できない
  (今回は人間向けに「設計どおり」と説明して通した)。
- `docs/03-impl/tests/sample-project.md:29` は `FR-orch-09` 受入基準4 の状態を **「実装済み」**
  としているが、テンプレート上では緑にならない。**「テストが実装されている」と
  「テストが通る」を区別していない表**になっている。

severity を「低」とした根拠: 実装も要件も壊れていない。読み手と自動化が誤解するだけである。

## 原因の見当

推測: `strategy.md` を書いた時点で「題材の pytest」を単体テストの1レベルとして数えたが、
**テンプレート(正本)と scaffold 後の作業コピーのどちらで走らせるか**を書き分けなかった。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| 題材の pytest をどこで走らせるか | `strategy.md` は `cd examples/orch-sample && pytest`(テンプレート) | `environments.md` も同じ文字列。`README.md`(製品側)はテンプレートを直接開発しないと明記 | **README が正**(ドキュメントのコマンドが場所を誤っている) |

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | コマンドを `make orch-sample && cd workspace/orch-sample && pytest` に直し、テンプレートでは走らせないと明記する | `environments.md`(version 上げ)・`tests/strategy.md`・`tests/sample-project.md` |
| B | 題材の pytest を単体テストのレベルから外し、**E2E-04 の検証手順の一部**として位置づける | 同上 |
| C | テンプレート側にも通るテストを1本だけ置く(スモーク) | `examples/orch-sample/` にファイル追加 = **コード変更** |

推奨は **A**(現状の意図に最も近く、コマンドを実行可能にする)。

## 経緯

- 2026-08-03 起票。`task-impl-depth` の `/task-close` 事前検査(§1-3)で
  `environments.md` の厳密な文字列を実行して発覚。**本タスクの範囲外**(コードもテストも変えない)。
