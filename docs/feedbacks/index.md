# 気づき 一覧

<!-- このファイルは build-index.py が生成する。手書きしない。 -->

<!-- BEGIN GENERATED: build-index.py -->

| ID | 日付 | 概要 |
|---|---|---|
| [001-test-assets-are-out-of-scope-for-features](001-test-assets-are-out-of-scope-for-features.md) | 2026-08-02 | 機能表とコールグラフは製品コードの境界を書く場所であり、テスト資産は載せずに tests/ で記述する |
| [002-external-dependency-decisions-need-a-fixed-checklist](002-external-dependency-decisions-need-a-fixed-checklist.md) | 2026-07-30 | 外部依存を同梱する決定は「版の追随・実行権限・設定の上書き経路・deprecated 依存の回帰検知」を必ず埋めないと、決定として完了しているのに使えない状態が残る |
| [003-agent-success-must-be-judged-by-side-effects](003-agent-success-must-be-judged-by-side-effects.md) | 2026-07-31 | エージェント(LLM)は失敗を自己申告せず出力を捏造する。成否は応答文ではなく副作用(終了コード・生成物)で判定する |
| [004-upstream-must-not-copy-downstream-measurements](004-upstream-must-not-copy-downstream-measurements.md) | 2026-07-30 | 00 に下流が正本として持つ実測値(モジュール数・一覧・パス)を書き写すと、下流が正しく育つほど 00 が静かに嘘になる |
| [005-spec-ahead-of-code-needs-an-explicit-marker](005-spec-ahead-of-code-needs-an-explicit-marker.md) | 2026-07-31 | 仕様だけ先に更新した期間を示す目印が無いと、「決定は完了しているのに実装が無い」状態が誰にも気づかれない |
| [006-delegation-covers-granularity-not-new-design](006-delegation-covers-granularity-not-new-design.md) | 2026-07-31 | 委任「記述の粒度を決めてよい」は、新規の仕様・手順を設計してよいという意味ではない。撤回の判断基準は「独立監査が収束するか」 |
| [007-edit-structured-formats-with-a-parser-not-line-matching](007-edit-structured-formats-with-a-parser-not-line-matching.md) | 2026-07-31 | 構造化フォーマットの部分編集を行単位の文字列一致で実装すると、破壊しないつもりで意味を変える。構文を扱う箇所は全てパーサに寄せる |
| [008-security-measures-need-an-explicit-failure-policy](008-security-measures-need-an-explicit-failure-policy.md) | 2026-07-31 | セキュリティ手段を決める決定には、その手段が失敗・利用不能なときの方針(fail-open / fail-closed / degrade して警告)を必ず併記する |
| [009-platform-support-decisions-must-enumerate-every-feature](009-platform-support-decisions-must-enumerate-every-feature.md) | 2026-07-31 | プラットフォーム対応の決定を「対応する機能の列挙」で書くと、後から足された機能が漏れて誰の判断範囲でもなくなる |
| [010-isolation-inside-isolation-is-not-required](010-isolation-inside-isolation-is-not-required.md) | 2026-07-31 | 実行環境そのものが隔離境界の内側であれば、その内側でさらにサンドボックスを張る必要はない。ただし逸脱として理由付きで明記する |
| [011-do-not-nest-shell-quoting-three-levels-deep](011-do-not-nest-shell-quoting-three-levels-deep.md) | 2026-07-18 | シェルのクォートを3段ネストすると文字列が裸で露出しブレース展開でスクリプトが分裂する。生成は最外で行い、ネスト段数そのものを減らす |
| [012-do-not-work-in-parallel-with-a-background-subagent](012-do-not-work-in-parallel-with-a-background-subagent.md) | 2026-08-03 | バックグラウンドのサブエージェントと同じ作業ツリーで並行作業すると、相手が「自分が起動していない変更」を異常と判断して取り消す |
| [013-apply-an-adjudication-from-its-originating-layer](013-apply-an-adjudication-from-its-originating-layer.md) | 2026-08-04 | 裁定を反映するときは「その裁定が最初にどの層で決まったか」を先に確認する。下流だけ直すと次の検証が必ず見つける |
| [014-apply-facts-you-already-recorded](014-apply-facts-you-already-recorded.md) | 2026-08-04 | 調査メモに自分で書いた事実(set -e 等)を、後の裁定で適用し忘れる。裁定の直前に調査メモを読み返す |
| [015-partial-fixes-resurface-in-the-next-verification](015-partial-fixes-resurface-in-the-next-verification.md) | 2026-08-04 | 同じ層・同じ性質の乖離を「高だけ取り込む」と切ると、残りが次の検証で必ず再浮上する。切るなら層ごと切る |
| [016-tracking-is-not-adjudication](016-tracking-is-not-adjudication.md) | 2026-08-04 | 「issue で追跡済み」は「人間が裁定済み」ではない。02⇄03 差分の PASS 条件は追跡ではなく裁定 |
| [017-recheck-a-carried-forward-recommendation](017-recheck-a-carried-forward-recommendation.md) | 2026-08-04 | 引き継いだ推奨案は「受け皿が実在するか」を確かめてから提示する。前の実行が書いた推奨をそのまま人間に出すと、成立しない案を選ばせることになる |
| [018-mv-atomicity-is-about-the-path-not-the-contents](018-mv-atomicity-is-about-the-path-not-the-contents.md) | 2026-08-04 | `mv` の原子性は「そのパスの rename に成功するのは1プロセスだけ」であって「引き取った中身が観測したものと同じ」ではない。観測してから操作するなら、操作した対象が観測したものかを必ず検証する |
| [019-bash-traps-that-silently-do-nothing](019-bash-traps-that-silently-do-nothing.md) | 2026-08-04 | bash で「書いたのに効かない」3つの罠 — 同じ `local` 文の中では前の変数がまだ展開されない / `&` で起動した子は SIGINT を無視するので `trap ... INT` が無効になる / 端末の Ctrl-C は子プロセスにも直接届く |
| [020-static-callgraph-is-blind-to-interface-dispatch](020-static-callgraph-is-blind-to-interface-dispatch.md) | 2026-08-05 | 静的コールグラフはインターフェース越しの呼び出しを見られない — 実装済みの機能に出る CG3「低(実装前)」は実装漏れではなく、CG4 の確度「候補」は `exec.Cmd.Run()` のような同名衝突である。どちらもツールの限界であって仕様の欠陥ではない |
| [021-a-quality-attribute-can-be-declined-not-only-measured](021-a-quality-attribute-can-be-declined-not-only-measured.md) | 2026-08-05 | 「測れない非機能要件」への選択肢は《測れる形に書き直す》《測らないと明記する》の2つではなく、《その品質特性自体を追わないと決めて要件を削除する》という3つ目がある。AI は3つ目を選択肢に並べていなかった |
| [022-lens-substitution-can-be-approved-standing-not-per-run](022-lens-substitution-can-be-approved-standing-not-per-run.md) | 2026-08-05 | 独立レンズの代替可否は「1実行ごとの承認」だけでなく「常設の承認」でも与えられる。人間が先に判断を与えれば、実行のたびに決定シートで問い直す必要はない |
| [023-a-format-without-operating-rules-pushes-them-onto-every-project](023-a-format-without-operating-rules-pushes-them-onto-every-project.md) | 2026-08-06 | 規範が「書式」だけを定めて「運用規則」を定めないと、その空白は決定シートへ落ち、全プロジェクトが同じ問いを個別に埋め直すことになる |
| [024-cleanup-scope-is-defined-by-ownership-not-by-harm](024-cleanup-scope-is-defined-by-ownership-not-by-harm.md) | 2026-08-07 | 片付けの範囲は「残ると害があるか」で資源ごとに切るのではなく「誰が作ったか」で一息に決める。害の有無で切ると、説明できない例外が資源の種類だけ増える |
| [025-unrunnable-verification-is-accepted-not-outstanding](025-unrunnable-verification-is-accepted-not-outstanding.md) | 2026-08-07 | 環境が無くて実行できない検証は「やり残し(issue)」ではなく「受容(pending)」である。AI は環境を作る段取りを推したが、人間は環境の制約を所与として受け入れた |
| [026-a-kit-rewrite-invalidates-change-sets-already-verified](026-a-kit-rewrite-invalidates-change-sets-already-verified.md) | 2026-08-10 | 検証済みの変更指示は「規範が変わらない」ことに依存していた。キットを書き換えると、合格証を持つ成果物が黙って反映不能になる。壊れ方は反映の直前まで見えない |

件数: 26

<!-- END GENERATED: build-index.py -->
