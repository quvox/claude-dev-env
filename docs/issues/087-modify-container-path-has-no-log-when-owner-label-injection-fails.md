---
id: 087-modify-container-path-has-no-log-when-owner-label-injection-fails
type: modify
origin_layer: 03
severity: 低
found: 2026-08-07
found_in: /doc-check ssot task-stop-session-spawned-containers(独立レビュー(サブエージェント)の 03 ⇄ コード照合)
related: MODULE-docker-proxy-serve, CTR-docker-api, docs/02-design/logging.md, docker-proxy/main.go, FR-env-07
pattern: なし
pattern_survey: ""
summary: docker-proxy のコンテナ作成経路は、呼び出し元を特定できたのに所有者ラベルの注入に失敗した場合だけログを1行も出さない(ネットワーク作成経路は出す)
---

# 087 所有者ラベルの注入に失敗したとき、コンテナ作成経路だけログが出ない

## 事象

`docker-proxy/main.go:707`〜`:711` のコンテナ作成経路のログ分岐は2つしかない。

```go
	if labelled {
		logger.Printf("OWNER-LABEL container: owner=%s", owner)
	} else if owner == "" {
		logger.Printf("NO-OWNER-LABEL container: caller not identified; relaying unlabelled")
	}
```

したがって **`owner` は解決できたが `injectOwnerLabels` が `changed=false` を返した場合**
(ボディが JSON として読めない / `Labels` が不正 / 再 marshal に失敗)は**1行も出ない**。

ネットワーク作成経路は `docker-proxy/main.go:358` と `:363` の2本を持ち、
「呼び出し元を特定できない」と「ボディを書き換えられない」を区別して出している。

再現手順:

1. Claude コンテナの中から、`POST /containers/create` へ**JSON として解釈できないボディ**を
   送る(`docs/issues/005` と同じ経路)。
2. docker-proxy の標準出力に `NO-OWNER-LABEL` も `OWNER-LABEL` も現れないことを確認する。

## 影響

`docs/02-design/logging.md:103` は「**所有者ラベルを付与せずに中継した**|INFO|付与しなかった理由」を
ログ仕様として要求しており、コンテナ作成経路のこの1ケースだけがそれを満たさない。
利用者・運用者から見ると、**片付け対象から外れた資源が生じたことを知る手段が無い**。
実害は「後から気づけない」ことに限られ、拒否判定にも作成の成否にも影響しないので severity は「低」。

## 原因の見当

`injectOwnerLabels` の戻り値が `(body, changed)` の2値で、「所有者が空だった」と
「所有者はあったが書けなかった」を呼び出し側が区別できないため。
ネットワーク経路は `readAndRestoreBody` の失敗を別に捕まえているので区別できている。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| 付与しなかったときのログ | コンテナ経路は「所有者が空」のときだけ出す(`main.go:707`〜`:711`) | `02-design/logging.md:103` が「付与しなかった理由」を INFO で要求する | **設計が正**(実装に1分岐足りない) |

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | `else if !labelled` の分岐を1本足し、`NO-OWNER-LABEL container: body not rewritable; relaying unlabelled` を出す | `docker-proxy/main.go` 1箇所 + 単体テスト1本。`MODULE-docker-proxy-serve` の「ログ」欄と異常系1行 |
| B | 何もしない(受容) | `docs/pendings.md` へ移す。ただし 02 の logging.md が要求している以上、受容には 02 の書き換えが要る |

推奨は A。

## 経緯

- 2026-08-07 起票。`/doc-check ssot task-stop-session-spawned-containers` の独立レビュー
  (`lens: subagent`)が検出し、`docker-proxy/main.go:707`〜`:711` で事実を確認した。
  **本タスクの影響範囲内のモジュール(`MOD-docker-proxy`)だが、コードの変更を伴うため
  フェーズ4 では直さない**(反映後の実装変更はタスクの境界を越える)。
  03 側は事実のとおりに書き直し、`MODULE-docker-proxy-serve` の異常系と
  `03-impl/contracts/docker-api.md` の「付与できないとき」からこの issue を参照している。
