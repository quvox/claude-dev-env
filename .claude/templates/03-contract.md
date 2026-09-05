---
id: <name>
version: 1.0.0
updated: <YYYY-MM-DD>
source:
  - docs/02-design/contracts/<name>.md
kind: rest-api
openapi: inline
summary: <1行>
keywords: []
# verified: verify 系フロー(/verify-docs、03層代表は /verify-impl)だけが書く
---

<!-- 実装されている契約。ID は CTR-<name> で 02-design/contracts/ と同一。
     **内容は実装と完全一致**(実際のバリデーション・実際の既定値・実際のエラーレスポンス)。

     frontmatter の値の後ろに `# コメント` を書かない(検査スクリプトが値の一部として読む)。
     kind の語彙: rest-api | data-schema | event | storage | other
     (語彙の正: .claude/directions/02-design.md「contracts/」。ここの並びは手控えである)。
     (relations の kind とは**別語彙** — rest-api/event/other は綴りが重なるだけ。文書種で読み分ける)
     openapi は kind: rest-api のとき必須: inline | <リポジトリ内の OpenAPI ファイルのパス>。
     ★ 既定の kind: rest-api を REST でない契約に残さない(check-contracts.py CT1 が
       openapi: を要求する。語彙の正: .claude/directions/03-impl.md「contracts/」)。
     実装シンボルは frontmatter ではなく OpenAPI の `x-impl` に書く
     (.claude/directions/03-impl.md。区切りは `::`)。

     ★ REST API の契約は **OpenAPI 3.1 形式で書く**(.claude/directions/03-impl.md)。
       **リポジトリに既に OpenAPI ファイルがあるなら、それを `openapi: <path>` で指す。**
       写し取って二重管理してはならない(必ずずれる)。

     設計との差異を見つけたら「実装が正」と決めつけず報告する。 -->

# CTR-<name> <契約名>

- 実装: `<path>::<symbol>`(リクエスト検証の実体)
- 当事者: <> → <>
- 対応する設計: docs/02-design/contracts/<name>.md

## API 定義(OpenAPI / 実装のとおり)

<!-- `openapi: inline` ならこのブロックが本体。既存の OpenAPI ファイルがあるなら
     フロントマターの `openapi:` でそれを指し、このブロックは書かない。 -->

```yaml openapi
openapi: 3.1.0
info:
  title: <契約名>
  version: 1.0.0
paths:
  /v1/auth/login:
    post:
      operationId: login
      responses:
        "200": { description: 認証成功 }
        "400": { description: 入力不正 }
        "401": { description: 認証失敗 }
      x-impl: "backend/api/auth.py::login_handler"
      x-validated-at: "backend/api/schema.py::LoginRequest"   # x-validated-at は自由拡張の例(検査対象は x-impl のみ — CT6)
```

<!-- `x-impl` は実装シンボル(callgraphs のシンボルIDと同一表記)。
     これがあると `check-contracts.py` が「コールグラフのエントリポイント ⇄ 契約」を
     機械的に突き合わせられる。 -->

## 実装上の事実

| 項目 | 実際の値 | 定義箇所 |
|---|---|---|
| 認証 | <> | `<path>:<line>` |
| 既定値 | <> | `<path>:<line>` |
| 上限・制約 | <> | `<path>:<line>` |

<!-- OpenAPI に載せられるものは OpenAPI に載せる。ここに書くのは
     「どこで検証しているか」のような、コードの位置に紐づく事実だけ -->

## 設計との差異

<!-- 差異が無ければ「差異なし」と明記する。あるなら事実だけを書く(勝手に寄せない)。
     事実の差異(パス・メソッド・型)は実装を正として直し、「どちらが正か」に
     「実装(修正済)」と書く。**意図の差異だけ**を「要確認」にして決定シートへ
     (原則2。振り分けの正は .claude/directions/03-impl.md)。
     パスとメソッドの差異は `check-contracts.py` が機械的に出す。 -->

| 項目 | 設計(02) | 実装(03) | どちらが正か |
|---|---|---|---|
| <> | <> | <> | 要確認 |

## 既知の制限

| 制限 | 影響 | 関連する課題票 |
|---|---|---|
| <> | <> | <docs/issues/NNN-...> |
