---
id: 088-bug-stop-does-not-report-a-failed-compose-default-network-removal
type: bug
severity: 低
found: 2026-08-07
found_in: /doc-check ssot task-stop-session-spawned-containers(独立レビュー(サブエージェント)の 03 ⇄ コード照合)
related: MODULE-cli-stop, FR-env-01, CTR-cli-container, claude-dev, claude-dev-mac
pattern: deletion-failure-is-swallowed-without-telling-the-user
pattern_survey: "`claude-dev` / `claude-dev-mac` の `stop)` 分岐で `docker rm -f` / `docker network rm` を呼ぶ全6箇所を走査した。失敗を `_spawned_failed` に積まないのは compose 既定ネットワーク(`claude-dev:1717`〜`:1719` / `claude-dev-mac:1675`〜`:1677`)の1箇所だけで、本体コンテナ・`fwd-*`・compose コンテナ・所有者ラベル経由のコンテナ / ネットワークの5箇所はいずれも成否を記録している。同型は他に無い(1件)"
summary: stop が compose 既定ネットワーク `<一意化名>_default` の削除に失敗したとき、成功時だけ列挙へ積むため利用者に何も表示されない
---

# 088 `stop` が compose 既定ネットワークの削除失敗を利用者に伝えない

## 事象

`claude-dev:1717`〜`:1719`(macOS 版は `claude-dev-mac:1675`〜`:1677`)は次の形で、
**成功したときだけ**列挙へ積む。

```bash
        if docker network rm "${_cproj}_default" >/dev/null 2>&1; then
            _spawned_deleted+=("ネットワーク: ${_cproj}_default")
        fi
```

同じ手順の所有者ラベル経由のネットワーク(`claude-dev:1743`〜`:1747`)は
`else _spawned_failed+=(...)` を持ち、失敗した名前を stderr へ出す。

再現手順:

1. コンテナ内から `docker compose up` で資源を作り、その compose 既定ネットワークに
   **別の(セッション外の)コンテナを接続**する。
2. `claude-dev stop <name>` を実行する。
3. `<一意化名>_default` が残っているのに、削除できなかった旨が1行も表示されないことを確認する。

## 影響

`docs/03-impl/relations/MODULE-cli-stop.md` の手順8-3 は「手順6・7 で消えた compose コンテナと
compose 既定ネットワークもこの列挙に含める」と定め、異常系の表は「失敗した名前を stderr へ出す」と
書いている。実装はネットワーク1件だけそれを満たさない。
利用者は残ったネットワークに気づけず、次の `docker compose up` で古いネットワークを掴む。
`FR-env-01` 受入基準11・24 は「握って続行する」を許すが、**表示までは免除していない**。
実害は「気づけない」ことに限られるので severity は「低」。

## 原因の見当

compose 既定ネットワークの削除は所有者ラベルの導入(`DSN-env-04`)より前からある行で、
所有者ラベル経由の削除に `_spawned_failed` を足したときに**同じ形へ揃えなかった**ためと推測する
(推測)。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| 削除失敗の表示 | compose 既定ネットワークだけ表示しない(`claude-dev:1717`) | `CTR-cli-container`「エラーケース」は握って続行しつつ失敗を列挙することを求める | **設計が正**(実装の取りこぼし) |

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | `else _spawned_failed+=("ネットワーク: ${_cproj}_default")` を Linux 版・macOS 版の2箇所に足す | `claude-dev` / `claude-dev-mac` 各1箇所。ドキュメントは既に正しいので 03 の異常系1行を戻すだけ |

## 経緯

- 2026-08-07 起票。`/doc-check ssot task-stop-session-spawned-containers` の独立レビュー
  (`lens: subagent`)が検出し、`claude-dev:1717`〜`:1719` で事実を確認した。
  **フェーズ4 の反映後なのでコードは変更せず**、`MODULE-cli-stop` の異常系に事実として1行足し、
  そこからこの issue を参照している。
