---
id: 2026-08-04-doc-check-ssot-destructive-scope-certification
date: 2026-08-04
task: task-fix-destructive-scope
origin_layer: 02
issue: なし
summary: task-fix-destructive-scope の SSOT 反映後に /doc-check ssot を実行し、検出した指摘を修正して 46 件の合格証を発行した
---

# 2026-08-04 /doc-check ssot(task-fix-destructive-scope)の指摘修正と再認証

## 変更理由

`task-fix-destructive-scope` の変更指示 19 件が SSOT へ反映された(commit `d365eff`)結果、
`01-requirements/functional.md`(1.4.0 → 1.5.0)と `02-design/system.md`(2.0.0 → 2.1.0)の
MINOR 昇格によって、それらを `source` に持つ 46 件の仕様ドキュメントの合格証が失効した。
`/doc-check ssot task-fix-destructive-scope` を実行して失効分を検証し、
**その過程で検出した上流の記述漏れとコード ⇄ 03-impl の乖離を修正してから**再認証した。

起点層は **02**: 最大の指摘(`PLAN-cli-reset` の呼び出す先の欠落、
`CTR-cli-container` の結合テスト責任モジュールが 03 側の対応表に降りていない)はいずれも
02 の記述漏れが起点である。

## 変更内容の要約

- **02 の連携表の取りこぼしを補った**: `MODULE-cli-reset` が実装から確定した
  `container_exists` / `image_exists` への辺(CG4 の解消分)が 02 側に降りていなかった。
- **02 が新たに割り当てた結合テストの責任を 03 の対応表へ降ろした**: `CTR-cli-container`
  (破壊的操作の対象の識別)の責任モジュール 3 件の `tests/*.md` が「責任を持つ契約は無い」の
  ままだった。
- **独立監査(Codex)がコードとの乖離を 11 件検出し、うち 8 件を実装に合わせて訂正した**。
  1 件は振る舞いの隙間だったので `docs/issues/052` として起票した。
- `03-impl/index.md` の「実装の欠陥として起票済み」の一覧を、同じ行が宣言する数え方と
  機械的に一致させた。
- 46 件の合格証を発行した。**未検証のまま残るのは `00-requests/terminology.md` の 1 件だけ**
  (`docs/issues/044` の裁定により発行は `task-spec-measurability` の担当)。

## 更新したドキュメント

| ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|
| docs/00-requests/decisions/env.md | 1.1.0 → 1.1.1 | 反映時に落ちた frontmatter 直後の空行を戻した(内容は不変) |
| docs/02-design/relations.md | 1.1.0 → 1.2.0 | `PLAN-cli-reset` の呼び出す先に `PLAN-cli-common-container-exists` / `-image-exists` を追加し、その2つの呼び出し元に `PLAN-cli-reset` を追加した(03 側にだけ入っていた辺) |
| docs/02-design/system.md | 2.1.0 → 2.1.1 | frontmatter 直後の空行を戻した(内容は不変) |
| docs/02-design/logging.md | 1.2.0 → 1.2.1 | 同上 |
| docs/02-design/contracts/cli-container.md | 1.4.0 → 1.4.1 | ロックの保持者の記録を「`owner` に記録した」から手段に依存しない書き方へ(`owner` は撤回済みの `mkdir` 方式の名残で、`ln -s` 方式の実装にも 03 にも存在しない) |
| docs/03-impl/contracts/cli-container.md | 1.4.0 → 1.4.1 | 実装上の事実の `path:line` 6 箇所を現在のコードへ再採番(一括解放 `:415`→`:424`、`login` `:803`→`:808`、`login-codex` `:879`→`:884`、残骸回収 `:459`→`:472`、削除結果の記録 `:640`→`:617`、macOS の SSH ブリッジ付与 `:899`→`:1375`) |
| docs/03-impl/index.md | 1.9.0 → 1.10.0 | 「実装の欠陥として起票済み」を 15 件 → 14 件へ。`046` / `051` はどの「既知の制限」からも参照されていないので数え方の宣言どおり除外し、`024` は解消済みだが移行期の残りとして参照が残ることを明記し、`052` を追加した |
| docs/03-impl/tests/cli-stop.md | 1.1.0 → 1.2.0 | 契約の結合テスト表に `CTR-cli-container`(破壊的操作の対象の識別)の行を追加(02 が責任モジュールに指名したのに「責任を持つ契約は無い」のままだった) |
| docs/03-impl/tests/cli-logout.md | 1.1.0 → 1.2.0 | 同上 |
| docs/03-impl/tests/cli-reset.md | 1.0.0 → 1.1.0 | 同上 |
| docs/03-impl/relations/MODULE-cli-common-lock.md | (層で認証) | 関数シグネチャに第3引数(種別)を追加 / `chmod 700` の失敗は握って続行することを明記 / 副作用欄のロックファイル名を `proj-<key>.lock` と `shared.lock` へ |
| docs/03-impl/relations/MODULE-cli-start.md | (層で認証) | `design` に `DSN-env-03` を追加 / ロックファイル名を `proj-<name>.lock` へ / macOS の早期拒否時に `.claude-dev.yaml` が作られうることを異常系へ / `orchestrate` からの再帰起動が Linux 版だけの経路であることを明記 |
| docs/03-impl/relations/MODULE-cli-stop.md | (層で認証) | `design` に `DSN-env-03` を追加 / `NAME` の検証に受理する文字集合を明記 / docker-proxy の削除失敗を握らないことを戻り値欄へ / ロックファイル名を `proj-<name>.lock` へ |
| docs/03-impl/relations/MODULE-cli-logout.md | (層で認証) | 削除対象0件の早期終了経路ではラベル無しコンテナの列挙と書き戻しの警告を出さないことを明記し、既知の制限へ `docs/issues/052` を追加 |
| (再認証のみ)46 件 | 変更なし | `verified` の `version` と `against` を現在値へ更新 |

## 実装したもの

なし(コードは変更していない。`/doc-check` は仕様ドキュメントと合格証だけを書く)。

## 機能間連携仕様書の変化

| 種別 | ID | 内容 |
|---|---|---|
| 変更 | PLAN-cli-reset(02) | 呼び出す先に `PLAN-cli-common-container-exists` / `PLAN-cli-common-image-exists` を追加 |
| 変更 | PLAN-cli-common-container-exists(02) | 呼び出し元に `PLAN-cli-reset` を追加 |
| 変更 | PLAN-cli-common-image-exists(02) | 呼び出し元に `PLAN-cli-reset` を追加 |

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 新規 issue | docs/issues/052-bug-logout-skips-unmanaged-warning-when-nothing-to-delete.md | `logout` の削除対象0件の経路が、ラベル無しコンテナの列挙と「認証が書き戻される」警告に到達しない(受入基準17 と19 の隙間。独立監査 Codex が重大度「高」で指摘し、受入基準の条件節に照らして「中」へ改めた) |
