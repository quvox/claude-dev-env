---
id: <name>
version: 1.0.0
updated: <YYYY-MM-DD>
source:
  - docs/02-design/system.md
kind: rest-api
openapi: inline
summary: <1行>
keywords: []
# verified: verify 系フロー(/verify-docs、03層代表は /verify-impl)だけが書く
---

<!-- 契約 ID は CTR-<name> で、docs/03-impl/contracts/ と同一 ID を使う
     (同一 ID であることが 02⇄03 の契約一致検査を機械的にする)。

     frontmatter の値の後ろに `# コメント` を書かない(検査スクリプトが値の一部として読む)。
     kind の語彙: rest-api | data-schema | event | storage | other
     (語彙の正: .claude/directions/02-design.md「contracts/」。ここの並びは手控えであって、
     増減はそちらで行う)。
     (relations の kind とは**別語彙** — rest-api/event/other は綴りが重なるだけ。文書種で読み分ける)
     openapi は kind: rest-api のとき必須: inline | <リポジトリ内の OpenAPI ファイルのパス>。
     ★ 既定の kind: rest-api を **REST でない契約に残さない** — 残すと check-contracts.py CT1 が
       決して存在しない openapi: を要求する。新設するときは frontmatter に
       正しい kind を書き、03 側へは /build のタスク内整合確認で写す(.claude/directions/02-design.md「contracts/」)。

     ★ REST API の契約は **OpenAPI 3.1 形式で書く**(.claude/directions/02-design.md)。
       表で書き直さない。OpenAPI に書けることは OpenAPI に書く。
       OpenAPI に書けないもの(設計判断・却下案)だけを本文に書く。
       責任モジュール(結合テスト)の正は 02-design/system.md の「結合テスト対象」表 —
       ここには書かない(二重管理になる)。

     ★ **REST でない契約はこの雛形を使わない** — `.claude/templates/02-contract-nonrest.md` が
       その雛形である。この雛形の本文は OpenAPI 専用で、型・必須かどうか・既定値・制約・
       エラーの場合を書く欄を持たない。

     実装スニペットは書かない。粒度は 03 と違ってよいが、本質が違えば指摘対象。 -->

# CTR-<name> <契約名>

- 当事者: <呼ぶ側> → <呼ばれる側>
- 対応要件: FR-<domain>-01

## API 定義(OpenAPI)

<!-- `openapi: inline` ならこのブロックが契約の本体。
     `openapi: <path>` ならこのブロックは書かず、そのファイルが本体になる。
     どちらの形でも `check-contracts.py` が検査する。 -->

```yaml openapi
openapi: 3.1.0
info:
  title: <契約名>
  version: 1.0.0
paths:
  /v1/auth/login:
    post:
      operationId: login
      summary: <1行>
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [email, password]
              properties:
                email: { type: string, format: email, maxLength: 255 }
                password: { type: string, minLength: 8 }
      responses:
        "200":
          description: 認証成功
          content:
            application/json:
              schema:
                type: object
                required: [token]
                properties:
                  token: { type: string }
                  mfa_required: { type: boolean }
        "400":
          description: 入力不正
          content:
            application/json:
              schema: { $ref: "#/components/schemas/Error" }
        "401":
          description: 認証失敗
        "503":
          description: 上流障害。指数バックオフで再試行可
      x-idempotent: false
      x-retryable: ["503"]   # x-retryable は自由拡張の例。規範の対象は x-idempotent / x-ordering /
                             # x-concurrency(02-design.md。検査は無い — 執行者は読み手)。
                             # 機械検査は 03 側の x-impl のみ(CT6)
components:
  schemas:
    Error:
      type: object
      required: [code, message]
      properties:
        code: { type: string }
        message: { type: string }
```

<!-- **エラー応答の無い契約は未完成。** 正常系だけを書いた OpenAPI は指摘対象になる。
     振る舞いが順序性・冪等性・並行性に依存するなら `x-idempotent` / `x-ordering` /
     `x-concurrency` で明示する(書かないのは「依存しない」の意味になる)。 -->

## OpenAPI に書けないこと

<!-- ここだけが散文。OpenAPI で表現できるものを二重に書かない -->

### 設計判断

<!-- **この節は空にできない**(検査 CS19)。判断が無かったなら「判断なし: <理由>」と書く -->

#### DSN-<area>-nn <タイトル>

- 判断: <>
- 理由: <>
- 却下した案: <案と却下理由>

### 順序性・冪等性・並行性の背景

<`x-` 拡張に書いた値の理由。依存しないなら「依存しない」と明記>

### 版と互換性

<!-- **共通方針は写さない。** `docs/02-design/architecture.md` の「契約の版と互換性の方針」が正である。
     (要旨: 壊さない変更の範囲・壊すときのやり方・旧版を残す期間)
     ここに書くのは**この契約だけの例外**である。無いなら「例外なし」と1行書く。
     **この節を空にしない** — 空欄は「共通方針どおり」と「決めていない」を区別できない -->

<例外なし / <この契約だけ共通方針と違う点と、その理由>>

### 認可の考え方

<誰が呼べるか、なぜその境界か。OpenAPI の securitySchemes では表せない意図>
