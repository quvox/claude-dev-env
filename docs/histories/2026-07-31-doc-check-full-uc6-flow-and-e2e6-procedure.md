---
slug: doc-check-full-uc6-flow-and-e2e6-procedure
layer: history
title: 検証指摘の修正（UC-6 に AS-6 の 2 操作を形式化、カバレッジ表・テスト対応表・運用メモ・steering の不整合を解消）
date: 2026-07-31
trigger: 検証指摘の修正（/doc-check full。独立監査 Codex の 9 レンズ分の指摘を裁定した結果）
origin_layer: requirements
affected:
  - doc: docs/01-requirements/core.md
    version: 1.9.0
    change: UC-6 の基本フローに AS-6 の 2 操作（通常依頼＝シェル実行と読み書き／読み取り専用での調査依頼）と、`workspace-write` を対象外とする代替フローを追加。事後条件と関連要件（12-4／12-9／12-5,12-6）を明示。あわせて要件5 に受け入れ基準 5-3（ファイアウォール適用に失敗しても起動を中止せず警告を起動ログへ出す。成否はサマリとスモークテストの警告行で判別できる）を追加——設計・実装は既にこの振る舞いだったが要件だけが沈黙していた（決定シート #3・feedback/log.md [18]）。※本フェーズの 1.8.0→1.9.0 の中で反映（追加バンプなし）
  - doc: docs/02-design/system.md
    version: 1.9.0
    change: 要件カバレッジ確認の core/12 行で `e2e` をモジュールとして挙げていた表記を、E2E-6（03-impl/e2e.md。分割定義外の標準例外）へ改めた。テスト戦略の備考「`codex --version` が期待バージョンを返す」を「prepare が解決し build-arg `CODEX_VERSION` として渡した具体バージョンと完全一致」に具体化。さらに、モジュール分割定義の cli 行が core/11 を持つのに要件カバレッジ確認の core/11 行が cli を挙げておらず表どうしが食い違っていたため、cli/cli-mac（noVNC ポートの動的割当と URL 表示）を追記し、11-1/11-2/11-3 の担当を明示した。※本フェーズの 1.8.0→1.9.0 の中で反映（追加バンプなし）
  - doc: docs/03-impl/entrypoint.md
    version: 1.7.0
    change: 運用メモの「（存在する限り entrypoint は触らない）」が、同文書の手順10・データアクセス表が定める不足鍵補完（要件 core/12-6）と矛盾していたため、「存在する場合に行うのは不足既定鍵の追記だけで、既に書かれている鍵と値は変更しない」に修正。さらに手順10 へ**不足鍵の判定規則と TOML 上の追記位置**を明記（トップレベル 2 鍵は最初のテーブル見出しの直前、`use_legacy_landlock` は `[features]` 見出しの直後、見出しが無ければ末尾に見出しごと、位置を特定できない TOML は何も書かず警告のみ。決定シート #1・feedback/log.md [17]）。エラーハンドリング表の firewall 行の対応要件を core/5 → core/5-3 に具体化。※本フェーズの 1.6.0→1.7.0 の中で反映（追加バンプなし）
  - doc: docs/03-impl/e2e.md
    version: 1.4.0
    change: 既知の制限の「`make build` 相当」を「`make build`、または `make build-claude` と `make build-claude-vnc` の両方」に具体化（意味不変）。※当初は「E2E-6 の実施手順（固定フィクスチャ・再現用）」表を D-19 の委任として追加したが、独立監査で 3 回連続して新規の重大度 高が出たため同一実行内で撤回し、フェーズ2 降下時の内容へ戻した（feedback/log.md [15]→[16]）。E2E-6 の再現可能な手順の整備は未着手のまま決定シートへ回している
  - doc: docs/03-impl/cli.md
    version: 1.8.0 -> 1.9.0
    change: テスト対応表が、02-design が cli に割り当てた受け入れ基準のうち core/12-7・7-5・11-1・6-1 の行を欠いていた（分割定義 cli 行とテスト戦略の備考が cli/cli-mac の担当と定めているもの）。4 行を実機確認の観測方法付きで追加（12-7=`docker inspect` の `HostConfig.SecurityOpt` が空／7-5=2 プロジェクト同時起動で `COMPOSE_PROJECT_NAME` が別値／11-1=noVNC ポートの動的割当と URL 表示／6-1=`start` 直後に noVNC 以外のポートが公開されていない）。あわせて SSH 鍵の行の「core/要件4-4 ほか」という範囲不定の記載を 4-1〜4-4 の明示に改めた。いずれも状態は 未検証(自動テストなし)
  - doc: docs/03-impl/firewall.md
    version: 1.0.0 -> 1.1.0
    change: 新設した要件 core/5-3（適用失敗時は起動を中止せず警告する）に対応するテスト行を追加し、既存行の対応要件を core/5 → core/5-1 に具体化。実装は変更していない
  - doc: docs/03-impl/portsync.md
    version: 1.0.0 -> 1.0.1
    change: エラーハンドリング表の「6080/5999/9222 等を転送対象から除外」の「等」が除外集合を確定していなかったため、「`EXCLUDE`（既定 `6080 5999 9222`、`CLAUDE_DEV_DOOD_PORTSYNC_EXCLUDE` で上書き）に列挙されたポートだけ」に書き換えた（意味は不変・PATCH）
  - doc: docs/_steering/tech.md
    version: （版なし）
    change: 「Codex実行設定」節が自己矛盾していた——QA 行（2026-07-31 の人間判断）が QA を `sandbox_mode="danger-full-access"` で走らせると定める一方、後続の行が「監査・QA で `--sandbox danger-full-access` を使うことは禁止」と書いていた。後続の行を「監査では使わない／QA レーンのみ例外（範囲と維持する制約は QA 行）」に整理した
---

# 変更記録:検証指摘の修正（UC-6 に AS-6 の 2 操作を形式化、カバレッジ表・テスト対応表・運用メモ・steering の不整合を解消）

## 変更理由・背景

`/doc-check full`（codex-landlock-sandbox 作業のフェーズ2 の締め）で、独立監査に Codex を 9 レンズ
（初回: 00／01／02／03／readiness、最終: A 縦整合／B+C+D、修正後の絞り込み再監査 2 回）走らせ、その指摘を
裁定した結果の修正である。要件・契約・振る舞いそのものは変えていない（すべて上流から機械的に導ける補完、
または既に人間が承認済みの決定への追従）。

裁定の内訳と、修正に至った理由:

1. **UC-6 が AS-6 の中身を取りこぼしていた**（独立監査 01 レンズが検出。Claude 自身は未検出）。
   AS-6 は「ファイルの読み書きやコマンド実行を伴う作業を依頼する」「読み取り専用で調査だけを依頼する」
   の 2 操作を持ち、それぞれ要件 12-4 と 12-9 の根拠になっている。しかし UC-6 の基本フローは `codex` の
   **起動まで**しか形式化しておらず、AS-n → UC → E2E の追跡が番号の上でしか成立していなかった。
   acceptance.md（上流）から機械的に導けるため自動修正とした。
2. **カバレッジ表が存在しないモジュール `e2e` を挙げていた**（独立監査 02 レンズ・Claude 双方が検出）。
   `03-impl/e2e.md` は分割定義外の標準例外であってモジュールではない。表記の問題であり意味は変えていない。
3. **entrypoint.md が自己矛盾していた**（Claude が検出）。運用メモだけが不足鍵補完の追加前の記述
   （「存在する限り触らない」）で残っており、同文書の手順10・データアクセス表・要件 core/12-6 と食い違っていた。
4. **E2E-6 の手順が再現不能だった**（独立監査 readiness レンズが検出。重大度 高）——**この指摘は未解決のまま
   決定シートへ回した**。当初は D-19（03-impl の記述粒度）の委任範囲と判断して固定フィクスチャの手順表を
   書いたが、絞り込み再監査を 2 回かけても毎回**新規の重大度 高**が出続けた（合否判定の自己矛盾 → 実行コマンド
   未指定と次コンテナ引継ぎの観測欠落 → `login-codex` 手順の欠落・複数プロジェクトの生成手順とコンテナ間
   `cmp` が実行不能な記法・人工的なファイル差分がトークン更新の代理になっていない）。収束しないことから
   「再現可能な E2E 手順を書き下ろすのは記述粒度の調整ではなく新規の仕様記述であり委任範囲外」と判断し、
   追加分を全て撤回して降下時の内容へ戻した（feedback/log.md [15]→[16]）。E2E-1〜5 も同様に手順を持たず、
   E2E-6 だけを詳細化するのは文書としても不均衡である。
5. **cli.md のテスト対応表に、割り当てられた受け入れ基準の行が複数欠けていた**（最終監査 A レンズと
   絞り込み再監査が検出。重大度 高）。上流から導ける表の欠落として補完し、あわせて 02-design 側の
   分割定義とカバレッジ表の食い違い（cli の core/11）も解消した。
6. **steering の「Codex実行設定」節が自己矛盾していた**（最終監査 A レンズが検出）。2026-07-31 の人間判断
   （QA のみ `danger-full-access`。`docs/knowledge/container-is-the-only-isolation-boundary-for-agent-qa.md`）
   を QA 行に追記した際、旧来の一律禁止行が更新されずに残っていた。承認済みの決定への追従として整理した。

## 変更内容の要約

上記 1〜6 を、影響範囲の各ドキュメントへ反映した（詳細は frontmatter の `affected` の各 `change:` 行）。

要件文・受け入れ基準・モジュール間契約・モジュール分割定義・E2Eシナリオ一覧（02-design）・決定台帳は
変更していない。`docs/03-impl/entrypoint.md` は本記録の対象だが、**コードが未了のため合格証は発行して
いない**（後述）。

## 決定シートの回答（2026-07-31）

| # | 論点 | 回答 | 反映 |
|---|---|---|---|
| 1 | 既存 `config.toml` への不足鍵の追記位置 | 案A: TOML 構造を尊重 | entrypoint.md 手順10 に記載。未決点 closure（log [17]） |
| 2 | E2E 実施手順の整備 | 案A: 別作業として起票 | `docs/tasks/e2e-procedures.md` を起票。e2e.md は合格証なしのまま |
| 3 | ファイアウォール適用失敗時の要件 | 案A: 現状を要件に明文化 | core/5-3 を追加・firewall.md/entrypoint.md へ traceability（log [18]） |
| 4 | steering の「別ベンダーワーカー」断定 vs D-22 未決 | 案B: D-22 を決定へ昇格（フォールバック付き）。進め方は別作業の `/change` | `docs/tasks/heterogeneous-vendor-reviewer.md` を起票。本記録では 00 層を変更していない |
| 5 | 契約の深度・orchestration の判定語 | 案A: 別作業として起票 | `docs/tasks/spec-depth-contracts-and-wording.md` を起票 |

## 積み残し

- `03-impl/entrypoint.md` は check B（03-impl ⇄ コード）で不合格。`scripts/entrypoint-claude.sh` が
  既定 2 鍵の生成のみで、3 鍵目（`features.use_legacy_landlock`）と不足鍵補完が未実装のため。
  剥落理由は「②実装が未了」であり①文書の誤りではない
  （`docs/knowledge/docs-ahead-of-code-deadlocks-doc-check.md` と同型・4 回目の再発）。
- 未決点 1 件（既存 `config.toml` へ不足鍵を追記するときの TOML 上の配置規則）が新規に発生し、
  `docs/tasks/codex-landlock-sandbox.md` の未決点へ記録した。`/implement` のタスク2 をブロックする。
- `03-impl/e2e.md` は、E2E-6（および E2E-1〜5）が再現可能な実施手順を持たないという重大度 高の指摘が
  未解決のため合格証を発行していない。整備は `docs/tasks/e2e-procedures.md` として起票済み。
- steering `product.md` の「別ベンダーのワーカーに担わせ」という断定と D-22（未決）の不整合は、
  D-22 を決定へ昇格する方向で解消することが決まった（決定シート #4）が、00 層の変更は本記録では
  行っていない。`docs/tasks/heterogeneous-vendor-reviewer.md` として起票済みで、当該作業が終わるまで
  不整合は既知の残存事項として残る。
- モジュール間契約の深度・UI 状態の網羅・orchestration の判定語は
  `docs/tasks/spec-depth-contracts-and-wording.md` として起票済み。
