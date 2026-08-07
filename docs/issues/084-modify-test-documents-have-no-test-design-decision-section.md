---
id: 084-modify-test-documents-have-no-test-design-decision-section
type: modify
severity: 中
found: 2026-08-07
found_in: 規範更新後の再検査(check-changeset.py --ssot docs の CS19。新設された検査)
related: docs/03-impl/tests/, .claude/directions/delegation.md, .claude/templates/03-tests-module.md, .claude/templates/03-tests-e2e.md, .claude/templates/03-tests-strategy.md, docs/03-impl/index.md
pattern: why-section-absent-where-the-norm-requires-it
pattern_survey: docs/03-impl/tests/ の 32 ファイル(index.md を除く全件)を check-changeset.py --ssot docs の CS19 で走査し 32 件すべてに「## テスト設計の判断」が無い。同じ検査が要求する他の3節(MODULE-*.md の「実装上の判断」27 件 / architecture.md の「設計判断」/ system.md の「分割の根拠」)は全件が節を持ち中身も空でないので、欠落はテスト文書に限られる。うち5件(cli-stop / cli-reset / docker-proxy / e2e / strategy)は task-stop-session-spawned-containers の変更指示で新設済みなので、SSOT へ反映されると残りは 27 件になる
summary: 03-impl/tests/ の全 32 ファイルに「## テスト設計の判断」が無く、テストの作り方(DS-01 で AI が決めた部分)の理由がどこにも残っていない
---

# 084 テスト文書に「テスト設計の判断」の節が無い

## 症状

2026-08-07 の規範更新で、**どう検証するか**(種別の割り当て・分割・フィクスチャ・モックの境界・
テストデータの生成と後始末・並列度)は標準委任 `DS-01` として AI が決めてよい範囲になり、
その代償として **決めたことを1行で開示すること**が義務になった
(`.claude/directions/delegation.md` §2・§3)。開示先は `03-impl/tests/<module>.md` である。

`docs/03-impl/tests/` の **32 ファイルすべてにその節が無い**(検査 CS19)。

```
$ python3 .claude/scripts/check-changeset.py --ssot docs
  CS19 理由の網羅: 違反 32 件
      - 03-impl/tests/cli-attach.md: 「## テスト設計の判断」の節が無い(見出しは消さない。原則9)
      …(32 件)
```

## なぜ問題か

「なぜこのテストの形なのか」の答えが**テストコードを読んで想像するしかない**状態である。
実例: `docs/03-impl/tests/cli-stop.md` は 16 件を「未検証(テスト未実装)」としているが、
**それが方針(`DSN-test-01`: シェルに自動テストランナーを設けない)による意図的な選択なのか、
単に書いていないだけなのか**は、表からは読み取れない。CS19 が言う「沈黙と不在は区別できない」が
そのまま起きている。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| テストの作り方の理由 | どこにも書かれていない(テストコードにコメントとしてある場合はある) | `delegation.md` §3 が「該当層に1行で開示する」と定める | **要件・設計が正**(節を新設して埋める) |

**実装の誤りではない。** テストコードは変わらない。

## 全件(32 件)

`docs/03-impl/tests/` の `index.md` 以外の全ファイル。うち **5 件は
`task-stop-session-spawned-containers` の変更指示で新設済み**(`cli-stop.md` / `cli-reset.md` /
`docker-proxy.md` / `e2e.md` / `strategy.md`)なので、そのタスクが `/task-close` で反映されると
**残りは 27 件**になる。

## どう直すか(案)

1. ファイルごとに、既存のテストの形から**実際に選ばれている判断**を書き起こす
   (書式は `delegation.md` §3: `- [DS-01] 決めたこと — 理由: … / 見直す条件: …`)。
   **判断が無かったなら「判断なし: <理由>」と書く**(空にはできない)。
2. `MODULE-*.md` を触るタスクが来たときに、そのモジュールのテスト文書も同時に埋める
   (CS19 は変更指示の `sections:` に載せることを要求するので、**触れば必ず埋まる**)。
   1件ずつ潰す専用タスクを立てるか、触ったものから埋めるかは人間が決める。

**キット側にも欠けがある**: 雛形 `.claude/templates/03-tests-e2e.md` と
`.claude/templates/03-tests-strategy.md` には「テスト設計の判断」の見出しが無いのに、CS19 は
`03-impl/tests/` の**全ファイル**に要求する。`.claude/improvements/KIT-cs19-section-name-and-test-templates.md`
が追跡している(このプロジェクトの issue ではなくキットの問題)。

## 影響範囲

- `docs/03-impl/tests/` の 32 ファイル(反映後 27 ファイル)
- 節の追加だけで、対応表・状態列・集計(`strategy.md` の 209 条項 / 224 行 / 222 件)は動かない
- `docs/03-impl/index.md` が層代表として検証済み記録を持つので、埋めたあとに `/doc-check` が要る
