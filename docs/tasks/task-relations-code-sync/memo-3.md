# task-relations-code-sync 解決済みの経緯(フェーズ2〜3 で決着した分)

<!-- 2026-08-05 /implement C-4 のローテーション。memo.md から節ごと逐語で移した。要約していない。 -->

## 未決点

| # | 未決点 | 帰着 | 検出元 |
|---|---|---|---|
| 1 | **`FR-orch-05` 受入基準2「未完了 plan が残る状態で `orchestrate` したらその run を継続する」を「実装済み」と言える範囲**。`tests/orchestrator.md` の当該行は実在しない `TestReadyTasks_Basic` を根拠にしていた。実在するもので当該基準に触るのは `archive_test.go::TestCountUndone`(未完了数の計算)と `controller_test.go::TestResume_UsesResumeFlagAfterCrash`(同一 Attempt の再開)の2件だが、**「継続するか新規で始めるか」の分岐そのものは `main.go` にあり単体テストが無い**(`MODULE-orchestrator-main` の tests は `terminalConfirm` の1件だけ)。この2件で「実装済み」とするか、「未検証(テスト未実装)」へ落とすかは**覆う範囲の判断** | **既定を適用して解決**(質問キュー #1 を提示 → 未回答 → 既定 B)。変更指示は「未検証(テスト未実装)」で確定し、全件表にも #47 を追加した | 自分のパス1 / `docs/issues/019` |
| 2 | `03-impl/index.md` の「実装の欠陥として起票済み」を **15 → 16 件**にした(`MODULE-docker-proxy-serve` の既知の制限が `issue 005` を参照するようになるため、同 issue が数え方の定義に入る) | **ドキュメント記載**(`D0-scope-06`。数え方の定義から一意に決まる) | 自分のパス1 |
| 4 | **独立レンズが「深度が足りない」系を 29 件返した**(公開シグネチャの網羅・JSON スキーマの型・書き込み順・TUI 契約・再試験手順)。本タスクは「既にある記述をコードへ合わせる」範囲なので**深度の追加は行わない** | **`docs/issues/004` へ機能単位で記録**(同 issue は人間が「残件は経緯の3項目」と裁定済み。今回それを機能単位へ展開した) | 独立レンズ(Codex `readiness`) |
| 3 | `MODULE-cli-reset` の `summary` が 106 字で `.claude/directions/relations.md` §3 の「1行・80字以内」に反していた(`check-changeset.py` の I2 が検出。`check-relations.py` は長さを見ない) | **ドキュメント記載**(意味を変えずに 80 字以内へ詰めた。範囲外の修正だが、同じ frontmatter を書き直す指示の中にあるため据え置きにできない) | 自分のパス1 |

**2026-08-05 `/doc-check task-relations-code-sync` の結果: 新しい未決点は 0 件**(未解決の未決点も 0 件)。
本タスクの「実装」は 27 ファイルの変更指示を SSOT へ書き写す作業であり、書き写しに必要な値・方針は
すべて変更指示の本文に確定して書かれている。`/doc-check` が見つけた 2 件は**未決点ではなく
「タスクの範囲をどこまで広げるか」の指摘**なので、下の決定シートへ載せた
(原則7 のゲート = 未決点ゼロ は満たしている)。

## レンズの判定(2026-08-05。独立レンズ = Codex `readiness`)

**誤検知と判定したもの(理由を必ず添える。不変則2)**

| 指摘 | 誤検知と判定した理由 |
|---|---|
| 02 契約の「最終行に1個」と受理側の探索が両立しない | `03-impl/contracts/orchestrator-prompt.md` の `## 設計との差異` が「**どちらも正**。契約は worker に課す義務、実装は受理側を緩めて版差に耐える」と裁定済み。レンズの読み取り範囲に同ファイルを入れなかったため見えていない |
| 02 契約に型違い・`null` の扱いが無い | 同ファイルの `## 実装上の事実` に「型が合わないフィールドがあるとき=オブジェクトごと復号失敗」「未知のフィールド=黙って無視」がある(同上の範囲外) |
| `MODULE-cli-start` が entrypoint の詳細を別文書へ委ねている | **1機能=1文書**の分割どおり(`MODULE-entrypoint-claude` が手順17・18 と永続化欄で持つ)。本タスクの変更はその参照を明示的に足した |
| 02 契約の `start` の順序が relation と両立しない | 契約は「イメージと共有インフラの用意は**ロックの保護対象外**であり、ロックを取る前に走ってよい」と**許可**しているだけで、実装が後に置くことと矛盾しない(relation の判断11 が理由を持つ) |
| controller の判断1 に「旧実装の `runCancel()` をやめた」がある(過去基準) | 却下した案を判断の理由として挙げる形式で、00 の「却下した案」と同型。現状記述を損なわない |
| trigger の既知の制限「条件4/5 の事前検出はフェーズ2以降」 | 00 が先送りと決めた範囲を「いまできないこと」として書いた既知の制限であり、現状記述である |
| `MODULE-orchestrator-main` の変更指示が「frontmatter を変更しない」と言いつつ `tests` を変える | 当該指示のコメントは `tests` の付け替えとその根拠(`main.go:194` の `terminalConfirm`)を明記している。レンズの読み違い |

### `/doc-check(task)` のレンズ判定(2026-08-05。独立レンズ = Codex `readiness` と Codex `docs`)

| 指摘 | 重大度 | 裁定 | 内容 |
|---|---|---|---|
| `MODULE-cli-start`「### 並行性」の表の2行が同じ入力で相反する(basename が同じ別ディレクトリ) | 高 | **確認済み・自動修正した** | コードで裏取り(`claude-dev:245`〜`:251` / `:396`〜`:401`)して1行目が正と確定し、2行目に「basename が異なる場合だけ」の限定とキーの定義を足した。**現行 SSOT にも同じ矛盾があり(`:288`〜`:289`)、同じ節を書き替える指示の中なので同時に直した** |
| `MODULE-cli-reset` の最終形に「本変更より前に起動した可能性がある」が残り、参照先の時点が無い | 低(`docs` レンズは中) | **確認済み・人間判断が必要**(修正案は採らない) | 事実は正しい(**Codex `readiness` / Codex `docs` / Claude の3者が独立に同じ箇所を検出した**)。ただしレンズの修正案「表示文言を置き換える」は**採れない**: `claude-dev:2110` ほかが実際にこの文言を出力しており、ドキュメントだけを変えると原則2(コード ⇄ 03-impl の一致)を破る。**文言そのものが変更相対である**という事実を `docs/issues/056` の追加検出節に記録し、決定シート #7 に載せた |

**Codex `docs`(2026-08-05 の再試行で成功。対象 27+27 ファイル・読み取り 56 ファイル)の裁定**

| 指摘 | 重大度 | 裁定 | 内容 |
|---|---|---|---|
| `tests/orchestrator.md` に「未検証(テスト未実装)」が 47 行残る | 高 | **確認済み。CLAUDE.md 不変則3 の例外に該当し PASS をブロックしない** | 件数も内訳も Claude 側の実測と一致(43 = 受入基準行 + 4 = 機能行)。各行に「なぜ未実装か」と「閉じる予定」がある。解消は本タスクの DoD ではなく、テストを書くタスクの仕事である |
| 全件表の「**閉じる予定**」列は SSOT に将来計画を持ち込んでいる | 中 | **誤検知**(理由: 列そのものがキットのテンプレート `.claude/templates/03-tests-module.md:53` が定めた必須の列で、`:57` のコメントが「全件ここに集約し、閉じる予定を書く」と明記している。CLAUDE.md 原則9 は「テンプレートの見出し構造を変えない」と定めるため、本ドキュメントの欠陥ではない)。**ただし「SSOT に計画を書かない」という §1 との緊張は実在する**ので、`/kit-improve` 案件として申し送りに記録した |
| `02-design/contracts/cli-container.md` の「この一意化が入る前に起動した compose 資源」が導入前を基準にしている | 中 | **確認済み・自動修正した** | Claude が本実行で「本変更より前に」から言い換えた直後の文をレンズが読み、**言い換えても時点基準のままだと指摘した**。`03-impl/contracts/cli-container.md` 側が既に採っている「観測できる性質で識別する」形(「古い名前の compose 資源が既存環境に残っている場合」)へ揃えた。**レンズの `quote` は逐語ではなく要約だった**(実文は「…は古い名前(`<正規化名>` だけ)を持つため、`stop` の片付け対象から外れる」) |
| `02-design/contracts/orchestrator-prompt.md`「停止させたい場合は `D0-orch-15` から改める」が将来の変更手順の指示 | 中 | **確認済み・自動修正した**(Claude は当初これを「起点層を指す有用な記述」として低と見ていた。レンズの指摘のほうが CLAUDE.md §1 に忠実である) | 「検証を行わないことの根拠は `D0-orch-15`(スキーマ強制はツールでは行わない)である」へ言い換えた。追跡性を保ったまま命令形を消した |
| `03-impl/index.md`「次にそのモジュールを触るタスクで『既知の制限』へ載せる」/ `MODULE-cli-stop` 判断8「現行も同じ変換を二箇所に書いているが」 | 低 | **確認済み・自動修正した** | 前者は数え方の定義の言い直しへ(集計の維持は `docs/issues/030` が追跡しており情報は失われない)。後者は「同じ変換が二箇所にあると…」へ |
| 他タスク `task-spec-measurability` の memo に未回答の決定シートと未決点が残る | 中 | **誤検知**(理由: `memo.md` は仕様ドキュメントではない — version も verified も持たず、C9 の「未解決事項」は仕様ドキュメントの節を指す。`.claude/directions/task-memo.md` は未決点を memo に置くことを**要求**している。加えて当該タスクはフェーズ1(決定)であり、未回答の決定シートを持つのが正常な状態である。本タスクの `sections` と衝突する `new-features/` も存在しない) |

**軽微(修正せず記録した)もの**: `03-impl/index.md` の**冒頭コメント**(過去の `/doc-check` の
検証履歴)に「MODULE 82」という古い数が残る。現在は 83 で、`## この層の状態` の表は 83 と正しい。
履歴コメントであり集計の維持は `docs/issues/030` が追跡しているため、本タスクでは触らない。


### #7 / #8 の既定を適用した記録(2026-08-05)

**人間はプロセス質問(P1 / P2)にだけ回答し、#7 / #8 は未回答だったため、シートに明記した
既定(#7 = A / #8 = A)を適用した。**

#### #8 = A: コード欠陥2件を新しい issue へ切り出した

| 新 issue | 内容 | 参照の付け替え先 |
|---|---|---|
| `docs/issues/057-bug-broken-open-json-silently-drops-the-intervention-queue.md` | 壊れた `intervention/open.json` で判断待ちキューが黙って失われる(`FR-orch-05` 受入基準7 違反) | `MODULE-orchestrator-state-intervention` の異常系 / `03-impl/index.md` の「01(要件)との差異」 |
| `docs/issues/058-bug-unknown-severity-passes-the-review-gate.md` | 未知の `severity` が「重大でない」扱いで品質ゲートを通過する(**正がどちらかは要確認**) | `MODULE-orchestrator-review` の処理の流れ3 / `03-impl/index.md` の「01(要件)との差異」に行を追加 |

`03-impl/index.md` の「実装の欠陥として起票済み」を **16 → 18 件**にした
(`038` は「記述の乖離」の issue だったため、この2件は従来この集計に入っていなかった)。

#### #7 = A: 変更相対の言い回しを直した

**実数は決定シートの見積もり(15箇所)より多く、44 行 / 16 ファイル**だった。分類:

| 判定 | 件数 | 内訳 |
|---|---|---|
| **正当(直さない)** | 19 | **コードが実際に出す文面の引用**「本変更より前に起動した可能性があります」(`FR-env-01` 受入基準15 / `FR-env-03` 受入基準17 / `02-design/logging.md` / `02-design/contracts/cli-container.md` 規則A / `MODULE-cli-logout` / `-reset` / `tests/e2e.md`)/ **日付で固定された決定の改訂記録**(`00-requests/decisions/env.md` `auth.md` の「2026-08-04 に改めた」・`01-requirements/functional.md:28`。`D0-orch-15` と同じ様式)/ **却下した案の記録**(`02-design/system.md:303` の「(旧実装)」・`MODULE-orchestrator-controller` 判断1) |
| **実問題(直した)** | 25 | 下の表のファイル |

**closure に追加したファイル(4本)**: `docs/01-requirements/functional.md`(受入基準15 の注釈)/
`docs/03-impl/features.md`(到達しない関数の判断)/ `docs/03-impl/relations/MODULE-cli-logout.md` /
既存の変更指示に節を追加したのが `02-design/contracts/cli-container.md`(3節)/
`02-design/system.md`(1節)/ `MODULE-cli-reset` `-start` `-stop`(計6節)。
**`00-requests/` は変更なし**(該当4件がすべて正当だったため、00 層の合意は不要だった)。

**言い換えの方針**: 時点を**観測できる性質**で言い直す(「本変更より前に起動した」→
「管理ラベルが付く前に起動された」/「一意化名が導入される前に作られた」)。意味は変えていない。

**検証**: 反映される本文(変更指示のコメント欄を除く)に `本変更` / `本タスク` / `現行も` /
`次のタスク` が **0 件**であることを機械的に確認した。

## 質問キュー(提示済み・既定を適用)

| # | 質問 | 前提 | いつ聞くか |
|---|---|---|---|
**2026-08-05 にフェーズ2末尾で提示した。人間はプロセス質問(P1 / P2)にだけ回答し、
論点1・2 は未回答だったため、シートに明記した既定を適用した**(1 = B「未検証(テスト未実装)」/
2 = A「`## 未検証(テスト未実装)の全件` にも #47 として足す」)。**どちらも変更指示に反映済み。**
`/task-close` までの間に人間が覆す場合は、`tests/orchestrator.md` の該当2行を差し替えるだけでよい。

| 1 | **`FR-orch-05` 受入基準2 のテスト対応を「実装済み(`TestCountUndone` + `TestResume_UsesResumeFlagAfterCrash`)」とするか、「未検証(テスト未実装)」とするか。** | 実在しない `TestReadyTasks_Basic` は必ず外す(ここは判断の余地なし)。**変更指示は推奨案どおり「未検証(テスト未実装)」で書いてある**(独立レンズが「実装済みと書きながらコメントで質問キューへ回すのは矛盾」と指摘したため確定させた)。「実装済み」を選ぶ場合は当該行を2件のテスト名へ差し替える | **フェーズ2 の末尾**(このシートで) |
| 2 | **`03-impl/tests/orchestrator.md` の `## 未検証(テスト未実装)の全件` に `FR-orch-05` 受入基準2 の行を足すか。** 質問1 が「未検証」に決まった場合だけ発生する(同節は本タスクの `sections:` に入っていないので、足すなら closure の行が1つ増える) | 質問1 = 未検証 なら**足すのが一貫している**(同節は「全件」を名乗っている) | **同上**(質問1 と一緒に) |

## 決定シート(フェーズ2末尾。2026-08-05 `/doc-check task-relations-code-sync` が提示)

**根拠の所在**: 本 memo.md(解決済みの経緯は `memo-1.md` / `memo-2.md`)。
指摘の詳細は `docs/issues/056` の「/doc-check(task) の追加検出」節と `docs/issues/054` の「経緯」末尾。

| # | 論点 | 選択肢 | 推奨案(理由・崩れる条件) | 未回答時の既定 | 根拠(上流/同層/下流) |
|---|---|---|---|---|---|
| 7 | **`issue 056` のクラス(変更相対・タスク相対の言い回し)が SSOT にあと 15 箇所残る。** 056 の表は「〜へ改める / 本変更で」の形だけを拾っており、「**本変更より前に起動した…**」という散文(利用者向けメッセージの引用ではないもの)と「**本タスク**」というタスク相対の参照を拾っていなかった。うち **6 箇所は本タスクが書き替えるファイルの、`sections:` に入っていない節**にある(`MODULE-cli-reset` 既知の制限 / `MODULE-cli-stop` 冒頭・処理の流れ・既知の制限 / `MODULE-cli-start` 既知の制限) | **A**: 6 箇所(closure 内のファイル)を本タスクで直し、closure 外の 9 箇所は `056` に残して別タスクへ回す(`056` は閉じない) / **B**: 15 箇所すべてを本タスクで直す(`01-requirements/functional.md` と `MODULE-cli-logout` / `features.md` / `02-design/system.md` / `02-design/contracts/cli-container.md` が closure に加わり、**01 層が「変更なし」でなくなる**) / **C**: どちらも直さず 8 箇所だけで `056` を閉じる | **A**。`docs/feedbacks/015`(「同じ層・同じ性質の乖離を部分的に切ると次の検証で必ず再浮上する。切るなら層ごと切る」)は 056 自身が推奨の根拠に挙げており、**同じファイルの別の節に残す**のはその教訓の直接の反例になる。一方 B は 01 層を開けるので `functional.md` の版が上がり `02-design/system.md` 以下の再認証が連鎖する(フェーズ2 を一度やり直す規模)。A なら追加は `sections:` を数行増やすだけの機械的な言い換えで、`056` は「残り 9 箇所」で開いたまま次のタスクへ渡せる。**崩れる条件**: 3本目 `task-spec-measurability` が closure 外の 9 箇所を拾わないと決めた場合(そのときは B を選ぶほうが安い) | **A** | 上流: CLAUDE.md §1(SSOT はいまの姿だけ)/ `docs/feedbacks/015` 同層: `docs/issues/056` の裁定(案A = 8 箇所すべてを closure に入れる)の趣旨 下流: `03-impl/index.md` の集計、`docs/issues/056` を閉じられるか |
| 8 | **`019` / `032` / `038` / `056` を削除すると、SSOT に残る参照が実在しなくなる。** とくに **`038` は経緯ではなく現役のトラッカー**で、人間が「実装の修正は別タスク」と裁定した**未修正のコード欠陥2件**の追跡先になっている(`03-impl/index.md:84` と `MODULE-orchestrator-state-intervention` 異常系 = 壊れた `open.json` が空キュー扱いで判断待ちが失われる / `MODULE-orchestrator-review` 処理の流れ3 = `severity` の値域を検証しないため未知の値がゲートを通過する) | **A**: コード欠陥2件を**新しい issue 2本**へ切り出し、`03-impl/index.md` と relations 2本の参照をそこへ付け替える(参照の付け替えは本タスクの closure 内。`index.md` は `## 01(要件)との差異` 節が増える) / **B**: `038` を**削除せず開いたまま**にし、表の記述系の行だけを閉じた旨を追記する(DoD の「`038` を削除できる状態」を下ろす) / **C**: そのまま削除し、`docs/issues/054` の一般問題として扱う(推奨しない) | **A**。`054` は severity「低」= 「経緯が辿れない」問題として起票されているが、ここで失われるのは**経緯ではなく未修正欠陥の追跡先**であり、`03-impl/index.md` の「実装の欠陥として起票済み(16 件)」の集計にも入っていない(`038` は記述の issue として数えられていた)ため、**削除すると誰も追っていない状態になる**。A は本タスクの範囲(記述をコードへ合わせる)に収まり、新しい issue には既にコードで裏取りした事実がそのまま書ける。**崩れる条件**: 「コード欠陥は relations の異常系に書いてあれば追跡できている」と判断するなら C で足りる | **A** | 上流: CLAUDE.md 原則8(見つけた問題を黙って扱わない)/ `docs/issues/054` 同層: `03-impl/index.md`「01(要件)との差異」は「すべて人間が裁定済み。追跡先を明記する」と自ら書いている 下流: `close-task.py` 条件d(DoD)と `docs/issues/030`(集計の維持) |

### プロセスに関する質問(不変則6・7。未決点ではないので原則7 のゲートを塞がない)

| # | 論点 | 選択肢 | 推奨案(理由) | 未回答時の既定 | 根拠 |
|---|---|---|---|---|---|
| P3 | **独立レンズは走ったが、走らせ方に再現性のある落とし穴があった**: `docs` / `readiness` の初回起動は**2本ともタイムアウト**(900 秒。終了コード 124)。**対象集合を絞り「探索的なシェルスクリプトを組まない」と明示した再試行で2本とも成功した**。`environments.md`「Codex実行設定」のタイムアウトは 900 秒で、モデル・reasoning は「未定」のため規範の既定(`gpt-5.6-terra` / `max`)を明示指定している。この組み合わせでは**対象が 50 ファイル超かつ読み取り範囲に 00・01 の全層を含めると時間内に返らない**。どう固定しますか | **A** `environments.md` のタイムアウトを延ばす(例 1800 秒) / **B** タイムアウトは変えず、**呼び出し側の規則として「1本の監査は対象 30 ファイル以内・層ごとに分割」を明文化**する(`/doc-check` §0.5 の予算表に足す = `/kit-improve`) / **C** 何もしない(毎回2回起動する) | **B**。今回は**対象を絞った再試行で 2 本とも成功**しており、原因はモデルの遅さではなく**1回の監査に載せた範囲の広さ**である。タイムアウトを延ばす(A)と失敗の発見が遅れるだけで、`/doc-check` §0.5 が既に「8本まで」「スコープで分ける」と言っている趣旨に沿うのは B。**崩れる条件**: 30 ファイル以内でもタイムアウトするなら A を併用する | **C(何もしない)**。本タスクの進行はこの回答を待たない | 本レポートの「独立監査」節 / `docs/issues/031`(監査モデルが未定) / `/doc-check` §0.5 の予算表 |

**サブエージェントによる代替は不要**(不変則7): 本実行では **Codex が `readiness` / `docs` / 再監査の
3本すべてで実際に走った**ので、代替の可否を問う必要が生じていない。

## 決定シート(回答済み)

**memo-2.md に移動**(2026-08-05 に人間が「全部推奨どおり」と回答した論点1〜6 と委任 a、
その推奨・根拠・反映先の全文)。**回答の要点だけ再掲**:

| # | 回答 | 本フェーズでの反映 |
|---|---|---|
| 1 | A(02 に「必須だが検証はしない」を明記) | `new-features/02-design/contracts/orchestrator-prompt.md` |
| 2 | A(`issue 009` (a) の17件は含めない) | どの変更指示にも入れていない |
| 3 | A(`032` の中・低すべて直す) | 18行すべてを変更指示へ |
| 4 | A(実装が誤っていたら issue 起票のみ) | `docs/issues/001` へ2シンボルを追記(コードは無変更) |
| 5 | A(`017` の relations 2行も直す) | **空振り**(3行とも既に解消済み。`docs/issues/017` に記録) |
| 6 | A(`056` の8箇所すべて直す) | 5ファイルの変更指示(02 が2本) |
| a | 承認(既存の `D0-scope-06` と一致するので 00 は変更なし) | 判定した全行にこの委任を適用。行使の記録は「調査メモ」 |

## 調査メモ

- `docs/issues/038` の表 #7〜#32 と `docs/issues/032` の表が**行単位の作業リスト**になっている
  (各行に「ドキュメントの記述」と「コードの事実」が `path:line` 付きで併記されている)。
- 2026-08-04 に実測した例(**未修正のまま残っている**): `MODULE-orchestrator-term.md:48`,`:61` は
  `selectMenu` の引数を「`options` = 文字列の並び」、`rawKeyMode` / `ttyRestoreSane` / `sttyRun` を
  「エラーを返す」と書くが、実コードは `orchestrator/term.go:96`(`items []menuItem`)/
  `:34`(`(func(), bool)`)/ `:44`(戻り値なし)/ `:48`(`bool`)である。
- **高5件(`038` の #1〜#5)は `task-impl-depth` で解消済み**(2026-08-04 にコードで再確認)。
- `check-relations.py` は**合格**している(対称性・参照実在・必須項目)。食い違いは**本文の叙述**に
  集中しており、機械検査では捕まらない種類である。
- 2026-08-05 に確認: **`02-design/relations.md` は orchestrator の内部を1モジュール
  `MOD-orchestrator` として扱い、`PLAN-orchestrator-main` の行に「同一モジュール内部で完結
  (03 側では内部の機能へ展開される。粒度差であって連携の欠落ではない)」と明記している**
  (`docs/02-design/relations.md:95`)。したがって `038` #11 / #12(`callers` / `callees` の
  追加)は **02 の想定連携を変えない**ので、02 起点にはならない(CLAUDE.md 原則3 の判定)。
### パス2(技術調査)で確定させた事実 — 2026-08-05

**コードは 2026-07-06(`b634206`)以降変わっていない**ので、以下は本タスクの実装フェーズでも有効である。

- `orchestrator/controller.go:47`〜`:48` `planMu` / `mergeMu`。Store 書き込みのうち
  `:73` `run_start` / `:467` `suspended` / `:1039` `finished_incomplete` / `:1083` `transition` は
  **`planMu` の外**。`updateSummaryLocked`(`:720` / `:1004`)は `planMu` 保持中に
  `updateSummary`(`:1087`〜`:1091`)= `WriteSummary` + `Notify` を呼ぶ。
- `orchestrator/dashtui.go:82`〜`:87` `dashModel.send` は満杯時に `default` で操作を破棄。
  バッファは `controller.go:240` / `:380` の `make(chan dashAction, 8)`。
- `orchestrator/review.go:161`〜`:167` `GateOutcome{Passed, LastSevere, FormatError, FormatErrorCount}`。
  `:179` `RunGate` は `(GateOutcome, error)`。`formatErrs` は `:181`・`:197` のローカル変数で、
  live な `Task.ReviewFormatErrors` へ書くのは `controller.go:685` / `:699`。
  レビュアログは `:79` の `WorkerLogPath(t.ID + ".review")` = `workers/<taskID>.review.log`。
  監査イベントは `:94` `review_reformat_ok` / `:101` `review_result` / `:198` `review_format_error` /
  `:242` `revise_error`。
- `orchestrator/term.go:34` `rawKeyMode() (func(), bool)` / `:44` `ttyRestoreSane()`(戻り値なし)/
  `:48` `sttyRun(...) bool` / `:96` `selectMenu(title string, items []menuItem, def int) string` /
  `:84`〜`:88` `menuItem{Value,Label,Desc}` / `:75` `printModeBanner` は **stderr** /
  `:131` メニュー本体は **stdout** / `:137`〜`:142` は `n==0` で `continue`(タイムアウトなし)。
- `orchestrator/session.go:167`〜`:178` `Ensure` は**対象を問わず** `remain-on-exit on`。
  `:215` `Run` は `cmd` をクォートせず渡す(呼び出し元は `controller.go:224` が
  `shellSingleQuote`、`:280` は素のまま)。`tmuxRun` は `:118`。**直接 `exec.CommandContext` を使うのは**
  `:89` `DetectSession` / `:150` `Has` / `:186` `PaneDead`。
- `orchestrator/worker.go:221` `Dispatch(ctx, p *Plan, t *Task, feedback string)`。
  `:423`〜`:427` `ExecGit.run` は `CombinedOutput` を返すが、`:429` / `:434` / `:449` / `:454` は
  出力を `_` に捨てる。`:465` `HasCommits` は**製品コードから呼ばれない**(`:69`〜`:70` に宣言のみ)。
- `orchestrator/mode.go:191` `ResolveArgsOne` は**製品コードから呼ばれない**
  (前景は `controller.go:843` の `ResolveArgs`、独立ウィンドウは `:929` の `IntervenePrompt`)。
- `orchestrator/state.go:209`〜`:214` `OpenIntervention{id,task_id,trigger_reason,opened_at}`
  ⇄ `:192`〜`:200` `Intervention{id,task_id,trigger_reason,question,answer,ts}`(**別型**)。
  `:546` / `:551` サイドカーはストア直下の任意名で、製品用途は `handoff_note.md` だけ
  (`controller.go:324` が書き `mode.go:67` が読む)。`:232`〜`:239` `NewStore` は `filepath.Join` のみ。
  `ArchiveRun` は `MkdirAll` 後に1件ずつ `os.Rename`(既存は上書き、不在はスキップ)。
- `orchestrator/streamlog.go:85`〜`:86` 非 JSON 行は素通し、`:111`〜`:112` の `default` で
  **未知の `type` は破棄**、`:101` `system` の未知 `subtype` も破棄。`:159` / `:233` が
  `dashboard.go:176` の `oneline` を呼ぶ。
- `orchestrator/trigger.go:17`〜`:24` `TriggerPhase` は `PhasePreDispatch`(=0)/ `PhasePostDispatch`。
  `:29`〜`:40` `TriggerContext{Phase,Task,Plan,State,Result,Config,StuckThisAttempt}`。
- `orchestrator/main.go:25` `--workspace` の既定は `defaultWorkspace()`。`:55`〜`:57` で絶対化、
  `:58` `NewStore`。掃除と退避は `:80`〜`:87` の `--fresh` 経路だけ。`:133`〜`:137` が
  goal 非空かつ plan 不在のとき最小 `Plan` を保存。`fmt.Print*` は7箇所、`os.Stderr` は 0 件、
  致命は `:45` `log.Fatalf`。`:194` `terminalConfirm`。
- `orchestrator/config.go:48` `DefaultSlackChannel = "U5SJG0XEK"`、`:50`〜`:62` 既定は10項目、
  `:113`〜`:115` `worker_grace_seconds` は `n >= 0`(0 が有効値)。
- `orchestrator/controller.go:1306`〜`:1318` `depsFailed` は**不存在の依存 ID も真**にする
  → `:1353` `MarkBlockedByFailedDeps` が `blocked` へ落とす。`:1402`〜`:1414` `NormalizeForResume` は
  **空文字の Status も `pending` へ**正規化する。
- `claude-dev:2006`〜`:2011` 非 TTY かつ `--yes` 無しで `exit 1`(`reset`)。`:988`〜`:993` が `logout`。
  主コンテナの `docker run -d` は `claude-dev:1381` / `claude-dev-mac:1414`、docker-proxy は
  `claude-dev:710` / `claude-dev-mac:777`。`xargs` の使用は両スクリプトで 0 件
  (`claude-dev:1651` / `claude-dev-mac:1609` が明示ループ)。
- **`claude-dev:245`〜`:247` `project_name` は `basename "$(pwd)"` を小文字化して `[^a-z0-9._-]` を `-` に
  置換した値で、`:250`〜`:252` `container_name` はそれをそのまま返す。`:396`〜`:401` `_lock_path` は
  プロジェクト単位のロックを `proj-<NAME>.lock`(共有単位は `shared.lock`)に置く。
  したがって**別ディレクトリでも basename が同じならロックキーもコンテナ名も同じ**である
  (`docs/issues/028` の事実と同一。2026-08-05 の `/doc-check(task)` が
  `MODULE-cli-start`「### 並行性」の矛盾を直すために確定させた)。**`acquire_lock` は待たない**
  (`:455` の `ln -s` が原子的な取得で、失敗すれば `:460` 以降で保持者を表示して非0)。
- `scripts/entrypoint-claude.sh:243`〜`:406` codex `config.toml` の既定鍵補完 /
  `:517`〜`:608` `/workspace/CLAUDE.md` のマーカー範囲の再生成 / `:611`〜`:674` VNC 時の
  `.mcp.json` と `.claude.json` の更新。

### フェーズ1 からの調査メモ

**memo-2.md に移動**(`02-design/relations.md` が orchestrator 内部を1モジュールとして扱う根拠、
02 契約の「必須」列と「既定値」列の並び、`D0-orch-15` の 2026-08-04 改めの本文)。

## 進捗メモ(フェーズ1 の最古2エントリ。memo.md から移動)

- 2026-08-04 フェーズ1。`issue 038` を起点に `032` / `019` を同時対象として宣言。
  3本連続タスクの2本目(1本目 `task-fix-destructive-scope` の完了後に着手)。
  決定シート4論点 + 委任1件を提示。
- 2026-08-05 フェーズ1(続き)。**タスク0(着手時の再突き合わせ)を完了**。
  1本目の反映で `038` の cli 系 5 行 + 追加#7・#8 + `028` 追加分が消えたことをコードで確認し、
  残件を **22 + 18 + 1 + 1 = 実質 40 件**として closure を21ファイルで確定した
  (`03-impl/contracts/cli-container.md` を外し、`MODULE-cli-start` / `MODULE-docker-proxy-serve` と
  orchestrator 17本を明示)。**新たに `docs/issues/056` を起票**(SSOT に残る変更相対の言い回し
  8箇所。うち2箇所は現行実装について事実と異なる)。決定シートに**論点5・論点6 を追加**して再提示。
- 2026-08-05 **フェーズ1 完了**。人間が「全部推奨どおり」と回答(論点1〜6 = A、委任 a 承認)。
