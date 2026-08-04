---
id: 030-modify-03-impl-index-understates-code-doc-divergences
type: modify
severity: 中
found: 2026-08-03
found_in: /doc-check ssot(check C12 / B4 / B5。開いている issue と完全性の主張の突き合わせ)
related: MODULE-orchestrator-session, MODULE-orchestrator-worktree, MODULE-orchestrator-handoff, MODULE-orchestrator-mode, MODULE-orchestrator-term
summary: docs/03-impl/index.md が「コードとの乖離として未解決のもの=1件」「02 との差分は上記2件を除いて差分なし」と書くが、開いている issue 009 / 013 / 014 / 018 / 019 がそれを否定する
---

## 事象

`docs/03-impl/index.md`(version 1.1.0、合格証あり)の「この層の状態」表と
「02 との差分(未解消のもの)」節が、次の2つの完全性を主張している。

| 箇所 | 主張 |
|---|---|
| 「コードとの乖離として未解決のもの」 | **1件**: macOS のコントローラ生存判定が無い(`docs/issues/003`) |
| 「02 との差分(未解消のもの)」 | 表に2行を挙げ、直後に「**上記2件を除いて差分なし**」 |

しかし `docs/issues/` には次が開いている(いずれも現行 SSOT に対して成立する)。

| issue | 種別 | 現行 SSOT で成立するか(機械確認の結果) |
|---|---|---|
| `009` | コード ⇄ 03-impl(本文の関数シグネチャ) | **成立**。例: `MODULE-orchestrator-session.md:27` は `NewSessionManager(cname)` と書くが実体は `orchestrator/session.go:50` の `NewSessionManager()`(引数なし)。`MODULE-orchestrator-session.md:31,37,39` の `DetectSession()` / `Has(window)` / `SwitchTo(window)` も実体は第1引数 `ctx context.Context` を取る。`MODULE-orchestrator-worktree.md:26` の `PrepareWorktree(taskID)` は実体 `(ctx context.Context, t *Task)`。`MODULE-orchestrator-handoff.md:30` の `WaitConsume(until)` は実体 `(ctx, poll time.Duration, until func() bool)` |
| `019` | 03-impl ⇄ コード(テスト識別子) | **成立**。`docs/03-impl/tests/orchestrator.md` の8識別子は `orchestrator/` `docker-proxy/` に `func Test…` として1件も存在しない(全8件を grep して 0 ヒットを確認) |
| `013` | 02 ⇄ 03(`logging.md`「通知の送信失敗 → WARN」⇄ Slack 実装) | **成立**(表に無い) |
| `014` | 02 ⇄ 03(`logging.md`「必須フィールド」⇄ 追記型ログ3本) | **成立**(表に無い) |
| `018` | 02 ⇄ 03(`--vm` + `/dev/kvm` 欠如で中止 ⇄ `CTR-cli-container`) | **成立**(表に無い) |

## 影響

`03-impl/index.md` は relations 層の**代表として版と合格証を持つ**ドキュメントであり(CLAUDE.md 不変則6)、
この2つの主張はその層全体について「コードと一致している」と読める。読み手は
`docs/issues/` を開かない限り乖離の量を誤解する。CLAUDE.md 原則2(コード ⇄ 03-impl は完全一致が
不変則)の現況を正しく示していないため、次に触る者が乖離を新規のものと誤認するか、
逆に「1件だけ」と信じて掃き出しを省く。

`013` / `014` / `018` と `009` の (b) 10件は **`task-impl-depth` の変更指示が既に修正しており**
(未反映)、反映後は解消する。**反映後も残るのは `009` の (a) 17件と `019` の8件**で、
どちらも「1件」という記述には含まれない。したがってこの issue は
`task-impl-depth` の完了では閉じない。

実装の振る舞いは正しく、影響は読み手の誤解に限られるので severity は「中」。

## 原因の見当

`009` は `task-docs-restructure` の `/doc-check` が起票し、(a) の規約が `/kit-improve` 待ちで
開いたまま残った。`019` は本タスクの `/doc-check` が起票した。どちらも
`03-impl/index.md`「コードとの乖離として未解決のもの」欄の更新を伴わなかった
(推測: この欄は `issue 003` が書かれた時点の記述のまま据え置かれた)。

## 正はどちらか

**ドキュメントが誤り**(実装は正しい)。乖離の実体は `009` / `019` が既に記録しており、
足りないのは代表ドキュメントの集計だけである。

## 対処案

| 案 | 内容 |
|---|---|
| A | `task-impl-depth` の `new-features/03-impl/index.md`(`## この層の状態` を replace する変更指示)の当該行を、反映後に残る乖離(`009` (a) 17件 / `019` 8件)を含む件数へ書き換える。**この issue のためにタスクの範囲を広げる必要はなく、既にある変更指示の1行の修正で足りる** |
| B | 反映後に `/doc-check ssot` を走らせ、その実行で `03-impl/index.md` の当該行を自動修正する(`009` / `019` の内容から機械的に導出できる) |
| C | 「コードとの乖離として未解決のもの」欄の定義を「`docs/issues/` の該当 issue へのリンクだけを置き、件数は書かない」へ変える(件数の陳腐化を構造的に防ぐ。`docs/issues/index.md` が生成物なのでそちらを参照させる) |

A と B はどちらも1行の修正で、コードは1行も変わらない。C は再発防止まで含むが
`03-impl/index.md` のテンプレート上の意味を変えるので、他プロジェクトへの波及を確認する必要がある。
