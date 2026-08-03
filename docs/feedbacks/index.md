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

件数: 12

<!-- END GENERATED -->
