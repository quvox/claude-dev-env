---
id: 082-modify-module-docker-proxy-serve-tests-field-undercounts-the-test-functions
type: modify
severity: 低
found: 2026-08-07
found_in: /doc-check(task-stop-session-spawned-containers。独立レビュー(サブエージェント)の再監査 X-4)
related: docs/03-impl/relations/MODULE-docker-proxy-serve.md, docs/03-impl/tests/docker-proxy.md, docker-proxy/main_test.go, docker-proxy/binds_test.go, .claude/directions/relations.md
pattern: tests-frontmatter-undercounts-code-test-functions
pattern_survey: `docs/03-impl/relations/*.md` のうち frontmatter `tests:` が「なし(未実装…)」でない機能は 18 件。うち Go 実装の 2 モジュール(`MOD-docker-proxy` / `MOD-orchestrator`)について、`grep -c '^func Test'` の実数と `tests:` の列挙件数を突き合わせた。食い違うのは `MODULE-docker-proxy-serve`(コード 25 / 列挙 15)の1件のみ(orchestrator 側の各機能はテストファイルが機能ごとに分かれており一致する)
summary: MODULE-docker-proxy-serve の frontmatter tests: が 15 件しか列挙しないが、参照する2ファイルのテスト関数は 25 本ある。同じ 03 層の tests/docker-proxy.md は列挙外の 5 本を名指しており、層の中で数が合わない
---

# 082 `MODULE-docker-proxy-serve` の `tests:` がテスト関数を数え落とす

## 事象

`docs/03-impl/relations/MODULE-docker-proxy-serve.md` の frontmatter `tests:` は
**15 件**を列挙する。しかし挙げられている2ファイルのテスト関数は実際には **25 本**ある。

```
$ grep -c '^func Test' docker-proxy/main_test.go docker-proxy/binds_test.go
docker-proxy/main_test.go:17
docker-proxy/binds_test.go:8
```

さらに、**同じ 03 層の `docs/03-impl/tests/docker-proxy.md`(受入基準 ⇄ テスト対応表)は
`tests:` に無いテストを名指している**。少なくとも次の5本がそれに当たる。

- `docker-proxy/main_test.go::TestValidateContainerCreate_BlocksHostBind`
- `docker-proxy/main_test.go::TestValidateContainerCreate_AllowsNamedVolume`
- `docker-proxy/main_test.go::TestValidateContainerCreate_AllowsEmptyBody`
- `docker-proxy/binds_test.go::TestRewriteBinds_MountsBind`
- `docker-proxy/binds_test.go::TestRewriteBinds_EmptyProjectRejectsAbsolute`

つまり **`tests:` は「この機能を覆うテストの全件」ではなく、部分集合**になっている。

## 影響

- **`check-relations.py` は通る。** この検査が見るのは「`tests:` に挙げたテストが実在するか」で
  あって、逆向き(コードのテストが漏れなく挙がっているか)ではない。したがって**機械では
  検出できない**。
- **「このモジュールを変えたら何を回すか」を `tests:` から引けない。**
  `relations-query.py --impact docker-proxy/main.go` が返すテスト件数(15 件)は実数より少ない。
  実際にはファイル単位で `go test ./...` を回すので実害は出にくいが、
  **回帰の範囲を人が数えるときにこの数を信じると 10 本を落とす**。
- 本タスク(`task-stop-session-spawned-containers`)の
  `MODULE-docker-proxy-serve` 実装上の判断8 は「既存の単体テストは全件、分解の変更後も同じ
  判定結果を返すことを回帰として確かめる」と**本数を書かない形**で書いた。本数を書くと
  この不一致がそのまま作業指示に入るためである。

severity を「低」とする根拠: 実行される検証の範囲は `go test ./...` で変わらず、
誤った文書が通ることもない。壊れているのは**影響範囲の機械抽出の精度**だけである。

## 原因の見当

`tests:` は `/relations` が生成するのではなく AI が書く欄であり、
**追加されたテストを `tests:` へ足す手順がどこにも無い**(推測)。
`docs/03-impl/tests/docker-proxy.md` の対応表は受入基準の側から書くので、
テストが増えると自然に増えるが、`tests:` は増えない。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| `tests:` は全件か部分集合か | `MODULE-docker-proxy-serve` は 15 件だが、コードは 25 本、同層の対応表は 20 本を名指す | `.claude/directions/relations.md` の `tests:` の定義を確認する必要がある | **要確認**(規範の解釈が先) |

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | **`tests:` を全件に揃える**(`MODULE-docker-proxy-serve` に 10 本を足す) | `docs/03-impl/relations/MODULE-docker-proxy-serve.md` 1ファイル。以後も手で保つ必要が残る |
| B | **`check-relations.py` に逆向きの検査を足す**(`impl` のファイルに対応するテストファイルの `func Test` を数え、`tests:` の件数と突き合わせる) | `.claude/scripts/check-relations.py`。`/kit-improve` 案件。**推奨**(A だけでは同じ漏れが再発する) |
| C | **`tests:` は「代表的なもの」と規範で定め、件数の一致を求めない** | `.claude/directions/relations.md`。`relations-query.py --impact` のテスト件数の意味も併せて書き換える |

**推奨は B + A**(規範の意図が「全件」であることを確かめたうえで、揃えて検査を足す)。
C を採るなら `relations-query.py --impact` の出力に「代表値であり全件ではない」と明示する必要がある。
