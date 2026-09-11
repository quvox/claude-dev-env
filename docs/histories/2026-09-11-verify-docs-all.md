---
id: 2026-09-11-verify-docs-all
date: 2026-09-11
record: なし(taskless — flow: verify-docs)
critical: false
origin_layer: 02
issue: なし
summary: F2 文書整合(全数)。共有ボリュームの本数を 4本→3本 へコードに合わせて戻し、E2E 台本 ID の写しと課題票の起点層を直し、00〜02 の21文書へ合格証を発行した
---

# 2026-09-11 F2 文書整合フロー(全数)の自動修正

## 変更理由

### R-01 02 のアーキテクチャが、実在しない共有ボリュームを1本数えていた

- 起点層・根拠: 原則2(事実の差異はコードに対して決着させる)。
  `docs/02-design/architecture.md:109` が「共有ボリューム4本」と述べていたが、
  `claude-dev:31`-`:33` / `claude-dev-mac:38`-`:40` が定義し `claude-dev:504`-`:506` が作る
  共有ボリュームは `claude-dev-auth` / `claude-dev-history` / `claude-dev-config` の**3本**である。
  `docs/03-impl/infra/local/docker-resources.md:50`-`:55` のリソース一覧も同じ3本を並べ、
  `claude-dev-chrome-<name>` は**コンテナごとに分離**と明記している。
- 変更が必要になった条件: 直前の F3(`auto-fix:` 7a786d2)が、`Makefile:37` が定義し
  `make setup`(`:124`-`:128`)が作る `claude-dev-chrome-data` を共有ボリュームとして数え、
  3本→4本 と書き換えていた。このボリュームはどのコンテナにもマウントされておらず、
  03 のリソース一覧にも1行も無い。02 の他の2文書(`environments.md:67`・
  `contracts/cli-container.md:719`)は3本のままで、02 の内部が食い違っていた。

### R-02 E2E 台本の ID が、失効判定の網の外に写されていた

- 起点層・根拠: CS22(02-design 内の `E2E-nn` は `system.md` / `testing.md` にだけ書ける。
  e2e の失効判定はその2ファイルしか見ない)。
- 変更が必要になった条件: `docs/02-design/environments.md:58` が
  「シェル系 E2E(E2E-01〜03・E2E-06)」と台本の ID を列挙していた。

### R-03 課題票4件が `origin_layer` を持っていなかった

- 起点層・根拠: 原則8 と `.claude/directions/issues-pendings.md` §1(課題票を起こす前に
  `origin_layer:` を決着させる。迷ったら上の層にする)。検査は CS20。

### R-04 UX の操作の流れが、上流の裁定と食い違う確認の規則を述べていた

- 起点層・根拠: `D0-env-08` 項3(`docs/00-requests/decisions/env.md:229`-`:233`)—
  「対象は `logout` / `reset` の2つに限る。`claude-dev stop` は確認を求めない」。
- 変更が必要になった条件: `docs/ux/flows.md:56` の見出しが `stop` を含むまま
  「不可逆な操作は、実行前に対象を示して確認を取る」と述べ、`stop` にも確認があるように読めた。
  独立レビュー(review-112055 / codex)の所見である。

## 変更内容の要約

- `docs/02-design/architecture.md:109` の「共有ボリューム4本」を「3本」へ戻した(R-01)。
  実在するが一覧に無い `claude-dev-chrome-data` は `docs/residual.md` へ1行で送った
  (所有者は 03 のリソース一覧であり、F3 の領分である)。
- `docs/02-design/environments.md:58` の台本 ID の列挙を、所有者への参照
  (`docs/03-impl/tests/e2e.md`「実機確認の手順」)へ置き換えた(R-02)。
- `docs/issues/005`(00)/ `010`(01)/ `028`(03)/ `055`(01)へ `origin_layer` を入れた(R-03)。
  値はいずれも各課題票自身の「正はどちらか」「対処案」の推奨から決めた。
- `docs/ux/flows.md:56` を「`logout` / `reset` は確認を取る。`stop` は確認を求めない」へ直した(R-04)。
- 00〜02 の21文書へ合格証(`verified`)を発行し、`against` を各文書の `source` の現在版から組み直した。

## 更新した仕様ドキュメント

| 理由ID | 仕様ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|---|
| R-01 | docs/02-design/architecture.md | 1.9.0 → 1.10.0 | 共有ボリュームの本数を 4本 → 3本(事実の訂正なので MINOR) |
| R-02 | docs/02-design/environments.md | 1.7.0 → 1.7.1 | E2E 台本 ID の列挙を参照へ置き換え(意味は変えていないので PATCH) |
| R-03 | docs/issues/005・010・028・055 | (版を持たない) | `origin_layer` を追加 |
| R-04 | docs/ux/flows.md | (版を持たない) | 確認の対象から `stop` を外した |
| - | 00〜02 の21文書 | 据え置き | `verified` の管理欄のみ更新(直していない文書の版は上げていない) |
