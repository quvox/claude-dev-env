---
id: 022-modify-merge-strategy-enum-is-not-validated
type: modify
severity: 中
found: 2026-08-03
found_in: task-impl-depth のフェーズ2(issue 004 の観点1・契約の型。D0-scope-07 の起票の閾値に該当)
related: CTR-cli-orchestrator, MODULE-orchestrator-config, MODULE-orchestrator-worktree, FR-orch-03
summary: merge_strategy の列挙を検証しないため、rebase の綴り間違いが黙って merge として実行される
---

# 022 `merge_strategy` の列挙を検証しない

## 事象

`orchestrator/config.go::applyConfigKV`(`:125`〜`:128`)は `merge_strategy` を**非空かどうかだけ**で
受理する。統合側の `orchestrator/worker.go::ExecGit.Merge`(`:454`)は
`case "rebase"` 以外を `default`(= `git merge --no-edit`)として扱う。

したがって `merge_strategy: rebse`(綴り間違い)や `merge_strategy: squash`(未対応の方式)は
**エラーにならず、`merge` として実行される**。警告もログも出ない。

再現手順:

1. `<workspace>/.orchestrator/config.yaml` に `merge_strategy: rebse` と書く。
2. orchestrator を起動し、タスクを1件完走させる。
3. 作業ブランチにマージコミットができていること(rebase されていないこと)を確認する。
4. 端末にも `audit.jsonl` にも警告が無いことを確認する。

## 影響

利用者は rebase を指定したつもりで**マージコミットが混ざった履歴**を得る。git 履歴は後から
作り直しにくいため、気づくのが遅れるほど手戻りが大きい。`FR-orch-03` 受入基準10 は
「`merge` / `rebase` 以外の値は `merge` として扱う」と現状を規定したが、**綴り間違いと
意図的な既定選択を区別できない**という問題は残る。

severity を「中」とした根拠: 実行は成功し状態も壊れないが、**利用者が失敗に気づけない**
(`D0-scope-07` の起票の閾値 (a))。同じ事象を追跡する issue は無い((b))。

## 原因の見当

推測: 整数キーには範囲検証を書いたが、文字列キーは「非空なら採用」で揃えたため、
列挙の検証が抜けた(`worker_permission_mode` は空文字を有効値にするため意図的に無検証)。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| 未知の値の扱い | 検証せず `merge` として実行する | `CTR-cli-orchestrator` は「列挙の検証をしない。未知の値は `merge` として扱う」と**現状を記述**。`FR-orch-03` 受入基準10 も同じ | **要確認**(検証して警告するか、現状のまま許容するか) |

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | `applyConfigKV` で `merge` / `rebase` のみ受理し、それ以外は**そのキーを適用せず警告を1行出す** | `orchestrator/config.go` と単体テスト、`CTR-cli-orchestrator`(02/03)、`FR-orch-03` 受入基準10 |
| B | 検証はせず、起動時に**実効値を1行表示する**(「統合方式: merge」)ことで気づけるようにする | `orchestrator/main.go` と 03 の1ファイル |
| C | 現状のまま(受入基準10 が既に規定している)。この issue を閉じる | なし |

推奨は **A**(設定の綴り間違いを黙って別の意味にしないのが原則)。ただし
「不正値は黙って無視する」という既存の共通規則を1キーだけ変える判断になる。

## 経緯

- 2026-08-03 起票。`task-impl-depth` のフェーズ2で `CTR-cli-orchestrator` の設定キー表を
  実値まで降ろす際に確定。**本タスクではコードを変更しない。**
