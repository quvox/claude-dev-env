---
id: 020-modify-cli-destructive-commands-have-no-mutual-exclusion
type: modify
severity: 中
found: 2026-08-03
found_in: task-impl-depth のフェーズ2(issue 004 の観点3「並行性と順序」。D0-scope-07 の起票の閾値に該当)
related: MODULE-cli-start, MODULE-cli-logout, MODULE-cli-reset, MODULE-cli-stop, FR-env-01, FR-env-03
summary: claude-dev CLI に排他機構が無く、start と logout/reset が同時に走ると認証が空のままコンテナが起動する(利用者は気づけない)
---

# 020 CLI の破壊的操作に排他が無い

## 事象

`claude-dev` / `claude-dev-mac` には**ロックファイルも `flock` も1つも無い**
(`claude-dev` / `claude-dev-mac` / `scripts/entrypoint-claude.sh` / `orchestrator/` を走査して該当なし)。
そのため次の同時実行が保護されない。

| 同時に起きること | 観測される結果 |
|---|---|
| `start`(認証コピー中)と `logout` | **認証が空のままコンテナが起動する**(未ログイン状態。`start` は成功したように見える) |
| `start` と `reset` | 認証コピー済みのコンテナが直後に削除される、または新しい資源が作り直される |
| `logout` / `reset` と `login` | ログイン直後の認証が消える |
| 同じディレクトリで `start` を2つ | 一方が名前衝突で失敗する(**ポート競合の文言に当たらないため再試行されず `exit 1`**) |

再現手順:

1. 端末Aで `claude-dev start` を実行する(認証コピーの一時コンテナが動いている数秒間が窓)。
2. その最中に端末Bで `claude-dev logout` を実行する。
3. 起動したコンテナ内で `claude` が未ログインであることを確認する(`start` はエラーを出さない)。

## 影響

`FR-env-03`(認証の受け渡し)が満たされないまま起動が成功したように見える。利用者は
「ログインしたのに未ログインになる」現象として遭遇し、原因(同時実行)に到達しにくい。
`reset` / `logout` は**他プロジェクトの稼働中コンテナも巻き込んで削除する**ため、複数プロジェクトを
並行して使う運用では窓が広い。

severity を「中」とした根拠: データは壊れず、再 `login` と再 `start` で回復できる。
一方で**失敗が静か**であり、`D0-scope-07` の起票の閾値 (a)「利用者が失敗に気づけない」に当たる。

## 原因の見当

推測: CLI をシェルスクリプト1本として素朴に保つ設計判断(`DSN-mod-02`)の帰結で、
排他は「同時に使わない」という運用前提に委ねられている。前提はどこにも明文化されていない。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| 破壊的操作の排他 | 排他は無い(各 relations の「並行性」節に事実として記述) | `NFR-scale-01` は**異なるディレクトリでの同時起動**を前提とするが、`start` と `logout`/`reset` の同時実行については何も定めていない | **要確認**(排他を入れるか、「同時に実行しない」を前提として明文化するか) |

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | 共有資源(認証ボリューム)を触るコマンド(`start` の認証コピー / `login` / `login-codex` / `logout` / `reset`)を `flock` で直列化する | `claude-dev` / `claude-dev-mac` の該当分岐、`MODULE-cli-*` 5本、`FR-env-03` の受入基準 |
| B | 排他は入れず、`logout` / `reset` に**稼働中コンテナがある場合の確認プロンプト**を足す(`reset` は既にあるが `logout` に無い) | 同2本と `MODULE-cli-logout` |
| C | 「これらを同時に実行しない」を前提として `01-requirements/system.md` に明記し、実装は変えない | ドキュメントのみ |

推奨は **A**(窓が短く、`flock` はシェルで完結する)。ただし `NFR-scale-01` の範囲を広げる判断を含む。

## 経緯

- 2026-08-03 起票。`task-impl-depth` のフェーズ2で各 relations の「並行性」節を書き下ろす際に確定。
  `D0-scope-07` の起票の閾値(2026-08-03 の決定シート#4=B で明文化)の (a)(b) を満たす。
  **本タスクではコードを変更しない。**
