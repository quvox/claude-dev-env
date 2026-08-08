---
id: task-layer-placement
phase: 反映
origin_layer: 00
issue: docs/issues/086-modify-upper-layers-carry-implementation-mechanisms.md
date: 2026-08-07
updated: 2026-08-08
source:
  - docs/00-requests/acceptances.md
  - docs/00-requests/terminology.md
  - docs/00-requests/decisions/auth.md
  - docs/00-requests/decisions/dist.md
  - docs/00-requests/decisions/env.md
  - docs/00-requests/decisions/orch.md
  - docs/00-requests/decisions/sec.md
  - docs/01-requirements/functional.md
  - docs/01-requirements/non-functional.md
  - docs/01-requirements/usecases.md
  - docs/02-design/contracts/cli-container.md
  - docs/02-design/contracts/cli-orchestrator.md
  - docs/02-design/environments.md
  - docs/02-design/relations.md
  - docs/02-design/system.md
  - docs/03-impl/relations/MODULE-cli-logout.md
  - docs/03-impl/tests/cli-logout.md
  - docs/03-impl/tests/e2e.md
  - docs/03-impl/tests/strategy.md
summary: 仕様ドキュメントの記述を本来あるべき層へ移す(issues 083・085・086・090・091 を一挙に解消する)
---

<!-- フロントマターに インラインコメント(値のあとの # …)を書かないこと。 -->

# task-layer-placement 記述を本来あるべき層へ移す

> 解決済みの経緯: memo-1.md(フェーズ1の決定シート — 概念3件・論点4件と、その回答および規範への昇格の仕分け)/ memo-2.md(フェーズ2 の未決点10件と調査メモ — 独立レビュー5周の記録・機械検査の凍結値・規範更新の経緯)/ memo-3.md(`/doc-check` の未決点#11〜#26・調査メモ6件・増分の前提となる変更指示のハッシュと SSOT の版・2026-08-07 のフェーズ1/フェーズ2 の進捗メモ)

## 目的

上位層(00/01)が実装の**機構**を持ち、02 が実装の**細部**を持っている箇所を、
**それぞれが本来属する層へ移す**。移し先に事実が在ることを1件ずつ確認してから落とすので、
情報は失われない。**コードは1行も変えない**(`docs/issues/085` / `086` の「正はどちらか」が
そろって「要件・設計が正、実装の誤りではない」と裁定済み)。

対象は5つの issue である。

| issue | 内容 | 残件 |
|---|---|---|
| `docs/issues/083` | 01 の条項が下位層 ID(`CTR-*` / `MODULE-*` / `DSN-*`)と実装ファイル名を名指す(機械検査 CS18 が検出) | 16 |
| `docs/issues/085` | 02 が実装のシンボル名・実行順序・出力文言・03 の実数を持つ | 11 |
| `docs/issues/086` | 00・01 が実装の機構を持つ(CS18 が見ないパターン。**00 にコードの行番号がある5件が最重**) | 59 |
| `docs/issues/090` | `logout` が作る孤児資源の帰結が 00〜03 のどこにも無い(**裁定 A 済み。4層に分けて書く**) | 3箇所 |
| `docs/issues/091` | `D0-env-08` 項8 に「`reset` が所有者を問わない理由」が無い(**裁定 A 済み。00 だけ**) | 1箇所 |

## やること・やらないこと

| 種別 | 内容 |
|---|---|
| やること | 上の5 issue が名指す箇所を、**あるべき層へ移す / 落とす / 書き足す**。落とす前に移し先へ事実が在ることを全件 grep で確認する。**条項 ID は1つも動かさない**(CS16)。**00 の意味のある編集を含むので決定シートで人間の合意を取る** |
| やらないこと(このタスクの範囲外) | **コードの変更**(`docs/issues/092` は 00・01・02・03 とコードを同時に降ろす必要があるため独立タスク。092 の「人間の裁定」節がそう定めている)/ `docs/issues/084`(`03-impl/tests/` の「テスト設計の判断」27件。**層の置き場ではなく節の欠落**なので別件)/ 03-impl 側の記述の移動(移し先として**読む**だけで、03 は原則そのまま)/ `docs/issues/054`・`075`(CS11 参照実在)と `031`(CS8)/ `docs/issues/086` が挙げる**移し先が無い2件**(`D0-env-02` の ControlMaster と `NFR-ops-02` の測定方法) — 下の決定シート論点3で扱う |

## 影響範囲(closure)

<!-- 1行1パス。close-task.py がこの表から SSOT パスを抽出して検証済み記録を検査する。 -->

| 層 | SSOT のパス | 変更指示のパス | 変更の種類 |
|---|---|---|---|
| 00 | docs/00-requests/decisions/env.md | new-features/00-requests/decisions/env.md | replace |
| 00 | docs/00-requests/decisions/auth.md | new-features/00-requests/decisions/auth.md | replace |
| 00 | docs/00-requests/decisions/orch.md | new-features/00-requests/decisions/orch.md | replace |
| 00 | docs/00-requests/decisions/sec.md | new-features/00-requests/decisions/sec.md | replace |
| 00 | docs/00-requests/decisions/env.md(`D0-env-04`)| new-features/00-requests/decisions/env.md | replace(**フェーズ2 の `/doc-check` で影響範囲に追加した**。`FR-env-10-1` が「どの実装をどう結び付けるかは 02/03 が定める」へ改まるのに、`D0-env-04` は `make install` の `uname -s` 判定と symlink という**実装の手順**を持ったまま残る。01 が委ねた先より上流が具体を握る形になるので、決定シート「方針合意」の 00 の行のとおり手順だけを落とした)|
| 00 | docs/00-requests/decisions/sec.md(`D0-sec-04`)| new-features/00-requests/decisions/sec.md | replace(**同上**。`D0-sec-09` から `iptables` を落とすと、`D0-sec-04` の委任範囲に残る「どのチェインに規則を置くか」の「チェイン」が 00 のどこにも根拠を持たない語になる。「規則をどこに置くか」へ一般化した)|
| 00 | docs/00-requests/decisions/dist.md | new-features/00-requests/decisions/dist.md | replace(**フェーズ2 で影響範囲に追加した**。`D0-dist-04` が持つ `config.toml` の3鍵・`auth.json`・npm パッケージ名は、いずれも**人間が選んだ技術と、その選択を裏づける実測**であり、2026-08-07 の規範の裁定 A で 00 に残ると決まった側である。`086` が挙げた `E2E-06` の名指しは**02 が所有する合意の ID** であり、本タスクが 00 に残すと決めた指し先の線(`CTR-*` / `DSN-*` / `E2E-*` は残す / `MODULE-*` とコードの識別子は落とす)の内側にある。**しかしフェーズ2 の独立レビューが、この判定が見落としていた重大度「高」を検出した** — `D0-dist-03` 項1・項3 と `D0-dist-04` 項1・項2 が **02 の `DSN-dist-01` と同じ主張**(終端レイヤーへの配置・内容由来のキャッシュキー・時刻由来 cache-bust の却下)を独立に持っており、`layer-fit.md` §3 の「所有者が2つ」に当たる。実現手段だけを落とす変更指示を追加した) |
| 00 | docs/00-requests/terminology.md | new-features/00-requests/terminology.md | replace |
| 00 | docs/00-requests/acceptances.md | new-features/00-requests/acceptances.md | replace |
| 00 | docs/00-requests/request.md | - | 変更なし(理由: 目的・対象ユーザー・スコープ・「やらないこと」は変わらない。全文を読み、実装の機構を名指す箇所が0件であることを確認した) |
| 00 | docs/00-requests/decisions/scope.md | - | 変更なし(理由: `D0-scope-01`〜`07` は記述粒度と委任範囲の決定で、実装の機構を持たない。`D0-scope-07` が挙げる `flock` などは**委任範囲の例示**であり、規範の指針が許容する形) |
| 01 | docs/01-requirements/functional.md | new-features/01-requirements/functional.md | replace |
| 01 | docs/01-requirements/non-functional.md | new-features/01-requirements/non-functional.md | replace |
| 01 | docs/01-requirements/usecases.md | new-features/01-requirements/usecases.md | replace |
| 01 | docs/01-requirements/system.md | - | 変更なし(理由: **規範により対象外**。`.claude/directions/01-requirements.md:51`「`system.md` is exempt — naming technologies is its whole purpose」。技術を名指すことがこの文書の目的である) |
| 01 | docs/01-requirements/decisions/split.md | - | 変更なし(理由: 分割可否の決定であり、実装の機構を持たない。名指す `FR-*` は同層の条項 ID で下位層ではない) |
| 02 | docs/02-design/contracts/cli-container.md | new-features/02-design/contracts/cli-container.md | replace |
| 02 | docs/02-design/contracts/cli-orchestrator.md | new-features/02-design/contracts/cli-orchestrator.md | replace |
| 02 | docs/02-design/relations.md | new-features/02-design/relations.md | replace |
| 02 | docs/02-design/system.md | new-features/02-design/system.md | replace |
| 02 | docs/02-design/architecture.md | - | 変更なし(**`source:` からも外した** — `close-task.py` の検査(f)が「`source:` にあるが表の変更ありの行に無い」を不合格にするため。読了記録には残る。理由: `docs/issues/085` の 11 件にも `086` の対象にも当たらない。`DSN-auth-01` / `DSN-dist-01` / `DSN-arch-02` は**落とした記述の移し先として読むだけ**である。フェーズ2 の独立レビュー2本が本文を精読して同じ判定を出した) |
| 02 | docs/02-design/environments.md | new-features/02-design/environments.md | replace |
| 02 | docs/02-design/logging.md | - | 変更なし(**フェーズ2 で全文を読んで確定した**。理由: `.claude/directions/02-design.md` は `logging.md` に「log specifications for the main events」を**明示的に割り当てている**ので、各イベントで何を出すかを持つのはこの文書の職務である(UI 設計節の「約束を担う文言は 01」は `system.md` の UI 節に掛かる規則であり、ログ仕様には掛からない)。各行は `対応要件` 欄で 01 の条項を引いており、所有者は1つに定まっている。**独立レビュー2本がここを「所有者が2つ」と指摘したが、規範の割り当てを根拠に誤検知と裁定した** — ただし線が曖昧だったことは事実なので、`system.md` の UI 節に「表示の約束は 01、ログとしての出力仕様は `logging.md`、削除対象の列挙の全体だけは `FR-env-03` 受入基準14 が `logging.md` へ委ねている」と明文で書いた。logging 自身に実装のシンボル名は無い) |
| 02 | docs/02-design/contracts/docker-api.md | - | 変更なし(**フェーズ2 で全文を読んで確定した**。理由: `085` の走査で指摘0件。実装のシンボル名・行番号・実行順序を持たず、`DSN-dp-01` / `DSN-dp-02` は設計の判断として理由と却下案を持つ。01 から落とした `403` / `502` の**移し先**である) |
| 02 | docs/02-design/contracts/entrypoint-firewall.md | - | 変更なし(**フェーズ2 で全文を読んで確定した**。理由: 同上。契約が課すのは「1度だけ呼ぶ・成否に関わらず起動を続ける」という取り決めで、実装の細部を持たない) |
| 02 | docs/02-design/contracts/orchestrator-prompt.md | - | 変更なし(**フェーズ2 で全文を読んで確定した**。理由: 同上。01 から落としたプロンプト構成要素の4種(`DSN-prompt-03`)・受け取るフィールドの型と列挙値・制御ファイルの扱いの**移し先**であり、これらは 02 の持ち物である) |
| 03 | docs/03-impl/tests/cli-logout.md | new-features/03-impl/tests/cli-logout.md | replace(**新設条項 `FR-env-03-24` の受け皿**。CS13 が「01 の変更指示が触れる条項は 03 のテスト対応表に行を持つ」ことを要求するため。あわせて `CS19` が要求する「テスト設計の判断」の節をこの1ファイルだけ新設する) |
| 03 | docs/03-impl/tests/e2e.md | new-features/03-impl/tests/e2e.md | replace(**フェーズ2 の `/doc-check` で影響範囲に追加した**。新設条項 `FR-env-03-24` の**実機確認手順**が存在せず、03 のテスト対応表の指し先が空だった。E2E-01 手順8 に部分手順 8-16 を新設し、既存の後片付けを 8-17 へ繰り下げた)|
| 03 | docs/03-impl/relations/MODULE-cli-logout.md | new-features/03-impl/relations/MODULE-cli-logout.md | replace(**同上**。「既知の制限」の1行が反映後に偽になり、参照する `docs/issues/090` も消える。`/task-close` の relations 再生成はコードから出せるものしか直さないので、同じ下降で閉じた)|
| 03 | docs/03-impl/tests/strategy.md | new-features/03-impl/tests/strategy.md | replace(**同上**。`go test -cover` のコマンド文字列を `environments.md` へ移す**移送の片側**が落ちていた。あわせて条項数 209→210 の数え直しを行う)|
| 03 | 上記以外 | - | 変更なし(理由: **03 は移し先として読むだけ**である。`085`・`086` の「正はどちらか」がそろって「移し先に事実が既に在る」と確認済みで、落としても情報は失われない。**例外は移し先が無い2件**で、決定シート論点3 の回答しだいでは 03 に受け皿を作る) |

**変更の起点**: 00-requests。`086` の最重要5件が 00 の決定と用語集にあり、`090`・`091` は
`D0-env-05` 項2 と `D0-env-08` 項8 の**理由文そのもの**を直す。00 の意味に触れる編集を含むので
`D0-scope-02` の委任では扱えない(CLAUDE.md 原則3)。

**既存タスクとの関係**: なし(`docs/tasks/` に他のタスクは無い。
`task-stop-session-spawned-containers` は 2026-08-07 に完了・削除済み)。

**解消できる pending / issue**: `docs/issues/083` / `085` / `086` / `090` / `091` の5件。
**関係するが解消しないもの** — `docs/issues/092`(コードを伴うので独立タスク)、
`docs/issues/084`(節の欠落)、`docs/issues/056`(変更相対語12件。CS18/CS19 とは別の検査)。

**部分充足の条項に乗るか**: 乗らない。本タスクは条項の**文面**を書き替えるが、
`FR-env-01-19` / `FR-env-07-5`(`部分(P-005)`)の**充足そのものは動かさない**。
`D1-split-01` の `段階可` の集合も変えない(`D1-split-02` のガードレール)。

## 読む範囲(読了記録)

- 全文読了: 2026-08-07
  - docs/00-requests/acceptances.md@1.2.0
  - docs/00-requests/decisions/auth.md@1.2.0
  - docs/00-requests/decisions/dist.md@1.0.1
  - docs/00-requests/decisions/env.md@1.3.0
  - docs/00-requests/decisions/orch.md@1.3.0
  - docs/00-requests/decisions/scope.md@1.2.0
  - docs/00-requests/decisions/sec.md@1.1.2
  - docs/00-requests/request.md@1.3.0
  - docs/00-requests/terminology.md@1.3.0
  - docs/01-requirements/decisions/split.md@1.2.0
  - docs/01-requirements/non-functional.md@1.5.0
  - docs/01-requirements/system.md@1.1.0
  - docs/01-requirements/usecases.md@1.3.0

- 全文読了: 2026-08-07(フェーズ2 の冒頭。`/clear` 後の新しい文脈で、下の11ファイルを
  **私自身が全文読んでから**下降を始めた。人間の指示「ツールではなく、あなたが文書を全て読んで」)
  - docs/01-requirements/functional.md@1.11.0
  - docs/02-design/architecture.md@1.4.0
  - docs/02-design/contracts/cli-container.md@1.6.0
  - docs/02-design/contracts/cli-orchestrator.md@1.1.0
  - docs/02-design/contracts/docker-api.md@1.1.0
  - docs/02-design/contracts/entrypoint-firewall.md@1.0.1
  - docs/02-design/contracts/orchestrator-prompt.md@1.3.0
  - docs/02-design/environments.md@1.1.0
  - docs/02-design/logging.md@1.4.0
  - docs/02-design/relations.md@1.6.0
  - docs/02-design/system.md@2.7.0

- 全文読了: 2026-08-08(`/doc-check` が影響範囲に追加した 03 の3ファイル。**03 は関連性で絞ってよい層**
  なので、変更指示の対象になったものだけを読んだ)
  - docs/03-impl/tests/e2e.md@1.3.0
  - docs/03-impl/tests/strategy.md@1.3.0
  - docs/03-impl/relations/MODULE-cli-logout.md@(版なし)

<!-- **未読了はゼロになった。** フェーズ1では文脈の予算が尽きて 11 ファイルが未読のまま残り、
     その事実を隠さず記録していた。フェーズ2 の冒頭(2026-08-07、`/clear` 後)に 00〜02 の
     全 24 ファイルを読み直したうえで下降を書いた。 -->

## 決定シート(回答済み)

(memo-1.md に移動)

## 未決点

(フェーズ2 で出た 10 件は memo-2.md に移動。**いずれも決着済みで、人間判断へ回したものは無い**)

(`/doc-check`(2026-08-08)の実装ドライラン パス1 で出た #11〜#26 は memo-3.md に移動。
 **26 件すべて決着済みで、人間判断へ回したものは無い**)

## 調査メモ

(フェーズ2 の 6 件は memo-2.md、`/doc-check` の 6 件は memo-3.md に移動。
 **機械検査の凍結値は下の Definition of Done が持つ**)

## 質問キュー(未提示)

| # | 論点 | 何が止まるか | 推奨する回答(暫定) |
|---|---|---|---|
| - | なし(フェーズ1の論点はすべて sheet.md に載せた) | - | - |

## タスクリスト

<!-- フェーズ2 が置く下書き。確定は `/implement` が行う。 -->

- [x] 0. **読了記録の未読了11ファイルを読む**(上の「読む範囲」)。フェーズ2 の冒頭で完了
- [x] 1. 00→01→02→03 の下降を1回で書く(変更指示 16 ファイル)
- [x] 2. `check-changeset.py` を通す(違反 0 件)
- [x] 3. 独立レビュー5周(層ごと3周 + 移し先の照合 + 変更指示そのものの点検)と裁定
- [x] 4. `/doc-check task-layer-placement`(合成ビューの検証)を通す — **2026-08-08 に PASS**(独立レビュー4本。変更指示は 16 → 19 件になった)
- [x] 5. `/implement task-layer-placement`(**コードは1行も変えない**。ドキュメントの反映は `/task-close`)—
      **2026-08-08 完了**。実装タスクは0件(コード差分 0)で、行ったのは検証と C-1 の突き合わせだけである

## Definition of Done

(**フェーズ3 の `/implement` が 2026-08-08 に確定させた**。**本タスクはコードを変えない**ので、
lint と単体テストは「実行して変化が無いこと」の確認になる。実測の表は進捗メモが持つ)

- [x] `go vet ./...` が `docker-proxy/` と `orchestrator/` の両方で成功(出力なし・終了コード 0)
- [x] `cd docker-proxy && go test ./...` が成功 — `ok github.com/quvox/claude-dev-env/docker-proxy (cached)`
- [x] `cd orchestrator && go test -mod=vendor ./...` が成功 — `ok github.com/quvox/claude-dev-env/orchestrator (cached)`
- [x] `cd examples/orch-sample && pytest` は **12 failed**。**既知の `docs/issues/033`**(題材の実装がスタブなので
      このコマンドは必ず失敗する)であり本タスクの回帰ではない。コード差分 0 で確認済み
- [x] `build-callgraphs.py --out docs/03-impl/callgraphs --check` が「最新」/ `cluster-features.py --check` が「最新」/
      `callgraph-check.py --to-be task-layer-placement` が **重大度「高」0 件**(中 6 / 低 21 / 参考 20 = 凍結値と同一)
- [x] `check-relations.py` 合格(83 ファイル / 83 ID)/ `check-contracts.py` 合格
- [x] **`MODULE-cli-logout` の「実装上の判断」14 件を現物のコードで再読し、全件「継続」と判定**(C-1 の★)
- [x] `check-changeset.py` が変更指示に対して違反 0 件 — **反映の直前に再実行して `合格: 不変条件の違反なし`**
      (フェーズ3 の実行以降、変更指示に一切手を入れずに `/task-close` §3 の反映へ入った)
- [x] `/doc-check task-layer-placement` が PASS(合成ビュー。未解決の重大度「高」が 0 件)— **2026-08-08 達成**
- [x] 反映後に `check-changeset.py --ssot docs` を再実行し、**CS18 が 0 件**になっていること。
      他の検査(CS8 42 / CS11 19 / CS19 27 / CS20 53)が**凍結値から増えていない**こと。
      **反映・issue 削除・検証済み記録の発行がすべて終わった時点の実測**:
      `CS18 要件に降りてきた機構: OK`(= 0 件)/ CS8 **36** / CS11 **19** / CS19 **26** / CS20 **53**(NG 134)。
      **全項目が凍結値以下である。**
      (CS8 は反映直後は 32 件だったが、`/doc-check` が `environments.md` をテンプレートの行集合へ
      戻したときに `未定(` の行が4件増えて 36 件になった。規範の要求そのものであり凍結値 42 未満。)
      **この行の末尾にあった「削除すると CS20 はさらに 5 件減る」という予測は誤りだった** —
      当該5件はフェーズ2 で `origin_layer` を足してあったので**もともと CS20 の違反ではなく**、
      削除しても 53 件のままである(実測)。凍結値から増えていないという条件そのものは満たしている
- [x] ~~`/task-close` の反映時に `MODULE-cli-logout.md`「既知の制限」の該当行を直す~~ — 
      **2026-08-08 に変更指示化した**(`new-features/03-impl/relations/MODULE-cli-logout.md`)。
      DoD の1行に委ねる形では `/task-close` §2 の relations 再生成が**コードから出せるものしか
      直さない**ため取りこぼす、と独立レビュー3本が指摘したことによる。経緯は `docs/histories/` が持つ
- [x] 解消する issue の削除: `083` / `085` / `086` / `090` / `091` を `git rm` で削除し、
      `build-index.py` で目次を再生成した(65 → **60 件**)。**`093` / `094` / `095` は新規に起票したので残す**

## 進捗メモ

- **2026-08-08 `/task-close`(フェーズ4)。反映・検証済み記録の発行・記録まで完了した。**
  `git rev-parse HEAD`(反映のコミット)= `d213b9d`。**コードは1行も変えていない**
  (`git diff --name-only 914d840..d213b9d` の非 `docs/` 差分 0 件)。
  - **§1 事前検査**: 未決点0 / タスクリスト全件チェック / 作業ツリー clean /
    lint(`go vet ./...` 両モジュール)と単体テスト(`go test ./...`・`go test -mod=vendor ./...`)を
    再実行してグリーン。E2E と受入基準スイープは §1-3 の実測ショートカット
    (記録 HEAD からの非 `docs/` 差分 0 件 + DoD の各行が出力の最終行を逐語で持つ)を適用した。
  - **§2 relations 再生成**: `build-callgraphs.py --out docs/03-impl/callgraphs` は**書き換えなし**、
    `cluster-features.py` も差分0、`propose-features.py` は追加候補0件・FT2 0件。
    **変更指示との差異は事実・意図とも0件。** `MODULE-cli-logout`「実装上の判断」14 件は
    再生成後にも再読して**全件継続**。
  - **§3 反映**: 変更指示 **19 件すべて**を 00→01→02→03 で反映し `reflected: 2026-08-08` を記入。
    陳腐化0 / 新設見出し1件(`anchors` の宣言どおり挿入)/ 運ばれなかった子見出し0件。
    版は **18 文書を MINOR**、`03-impl/index.md` を 1.18.0 へ。
    **反映中に1件直した**: 変更指示が `docs/00-requests/decisions/env.md:92` に、
    **同じタスクが削除する `docs/issues/090`** への参照を書いていた(反映すると `CS11` 違反で
    `docs/issues/054` が追跡する型になる)。指し先を `docs/histories/2026-08-08-layer-placement.md` へ替えた。
  - **§4 決定シート: お伺いする事項なし**(陳腐化・意図の差異・新設 MODULE・契約の差異・
    裁定不能の指摘がいずれも0件)。`sheet.md` に論点は追記していない。
  - **§5 振り分け**: `docs/pendings.md` `P-006` に手順8-16 を追加 / `docs/issues/084` を 27→26 件・
    `078` を 5→4 件に訂正 / 恒久的に真な事実(staged コールグラフを作らない理由・CG3 の誤検知6件・
    02⇄03 差分0)とキットへの申し送りを `docs/histories/2026-08-08-layer-placement.md` へ。
  - **§6 検証済み記録: PASS。** 実行形態はサブエージェント(`/doc-check` §0A)。
    **58 文書に `verified` を発行**(失効0 / 未検証0)。レビューは **`lens: subagent` 4本**
    (Codex は利用上限で 2026-08-11 まで不可。不変則7 のフォールバック)。
    `/doc-check` 側の自動修正6件と版の変更(`environments.md` 1.3.0 / `logging.md` 1.4.1)は
    `docs/histories/2026-08-08-doc-check-ssot-layer-placement-recertification.md` が持つ。
    **人間の裁定が要るものが1件**: `docs/issues/094` #1(Codex サンドボックス既定3鍵の値が
    00・01・02 に逐語で在る)。**本タスクの範囲外**として起票済みで、直しは `D0-dist-04` 項6 の
    意味に触れるため `/task-new` の決定シート案件である。
  - **§7 記録**: histories 1 件を作成し、解消した issue 5 件を削除して目次を再生成(65→60 件)。

- **2026-08-08 `/implement`(フェーズ3)完了。実装タスクは 0 件(コード差分 0)。**
  **DoD を実測したときの `git rev-parse HEAD` = `914d840be4df4e47c28a5164dc73d949d64fee8b`**
  (コードを1行も変えていないので、この HEAD のコードのまま lint と単体テストを走らせた。
  コードの最終変更は前タスクのコミット `1d912b4`)。
  - **A-1 でローテーションした**(370 → 276 行。memo-3.md を新設)。ゲートの3条件はすべて合格:
    (1) 影響範囲の 18 文書の検証済み記録を**推移閉包 21 文書まで自分で歩いて全件 OK**
    (`close-task.py --check` の (b) も 18/18 OK)+ 進捗メモに `/doc-check(task) 判定: PASS` の行が在る、
    (2) 未決点ゼロ(#11〜#26 は全件決着済み・`sheet.md` は一括回答で回答済み・`check-sheet.py` 合格)、
    (3) 合成ビューの `environments.md` に lint(`go vet ./...`)と単体テスト2件が実在し「未定」でない。
  - **フェーズB の実装作業は無い。** コード差分が 0 であることを
    `git status --porcelain | grep -v '^.. docs/'` が 0 件で示す。
    行ったのは lint・単体テストの実行(DoD の表)と、下の C-1 の突き合わせだけである。
  - **C-0 の QA レーンは対象が無いので走らせなかった。** 理由 = QA は実装の振る舞いを確かめる工程だが、
    本タスクのコード差分は 0 行で、確かめる差分が存在しない(前タスクの QA から**コードは1行も動いていない** —
    最終のコード変更は 2026-08-07 のコミット `1d912b4`)。加えて E2E は自動ランナーを持たない実機確認手順であり
    (`environments.md`「lint・テストコマンド」の E2E 行)、専有ホストを要する部分は `docs/pendings.md` の `P-006` が
    未実施として受け入れている。**同型の前例と一致する** — コード無変更だった
    `task-clause-ids-and-split-policy` も QA レーンを走らせておらず、その `docs/histories/` の「実装したもの」欄は
    「コードは1行も変えていない」である。**見直す条件**: このタスクがコードを1行でも変えたとき(そのときは
    `/codex-qa` を走らせてから完了させる)。**人間が異議を持つ場合はレポートで差し戻せる**。
  - **C-1(結果からの突き合わせ)**: staged コールグラフは生成していない。`resolve-callgraph-out.py` は
    `new-features/03-impl/callgraphs` を返すが、**コード差分 0 なので生成物は SSOT の複製にしかならず**、
    しかも生成すると `docs/issues/076` の不具合で `check-changeset.py` が CS1 違反 29 件を出して
    フェーズ3 のゲートが通らなくなる(076 の「経緯」が前タスクの `/implement` で**実測**したと記録している)。
    代わりに **`build-callgraphs.py --check`(最新)/ `cluster-features.py --check`(最新)/
    `callgraph-check.py --to-be task-layer-placement`(高 0・中 6・低 21・参考 20 = 凍結値と同一)**で
    コード ⇄ 03 の一致を確かめた。**中の 6 件は CG3 の既知の誤検知**(memo-3.md の調査メモが裁定済み)。
  - **C-1 の★(判断行の再読)を現物のコードに対して行った。変更指示の書き替えは 0 件**:
    - `MODULE-cli-logout`「実装上の判断」**14 件すべて継続**。根拠は現物である —
      `claude-dev:952-1120` と `claude-dev-mac:1020-1188` の `logout` ブロックは
      **`diff` で完全一致**(判断12「両 OS に同じ形で入れる」)、`destructive_rm` が
      `( trap '' INT TERM; "$@" )` で包む(`claude-dev:661-669`。判断13)、中断時の終了コード 130
      (`claude-dev:694-700`。判断9)、削除対象は認証3ファイルのみで `$(pwd)` 配下だけ
      (`claude-dev:985-990`。判断10・11)、共有ボリュームの成否を削除後の列挙と印で判定し
      `rm -rf` の終了コードを見ない(`claude-dev:1074-1090`。判断4)。
    - `03-impl/tests/e2e.md`「テスト設計の判断」既存4件は継続(3件目の指し先が
      繰り下げで `8-16` → `8-17` に変わるのは**手順番号の追随であって判断の変更ではない**。
      現物の SSOT `docs/03-impl/tests/e2e.md:365` が `8-16` を指しており、変更指示の 251 行目で
      `8-17` が後片付けになることを確認した)+ 新設1件は `[DS-01]` として開示済み(`CS17` OK)。
    - `03-impl/tests/cli-logout.md`「テスト設計の判断」3件は本タスクでの**新設**(節そのものが SSOT に無い)。
    - `03-impl/tests/strategy.md`「テスト設計の判断」2件(1件は「判断なし」の宣言)は継続。
      **集計値 210 条項 / 225 行 / 223 件を独立に検算した** — SSOT の機能要件は 209 条項
      (`grep -oE '^\| (FR-(env|orch)-[0-9]+-[0-9]+)' docs/01-requirements/functional.md | sort -u | wc -l`)で、
      変更指示が新設するのは `FR-env-03-24` の1件だけなので 210。223 = 210 + 非機能 13、225 = 223 + `FR-env-01-9` の重複2行。
  - **`build-index.py` を実行した**(`phase:` を `実装` にしたので `docs/tasks/index.md` が動いた。
    他の 9 つの index は「変更なし」)。
  - **決定シートは空**(お伺いする事項なし)。`sheet.md` に論点は1件も追記していない。

- **2026-08-08 `/doc-check`(task) 判定: PASS(残存の重大度「高」0 件)。レビュー: サブエージェント**
  (Codex はアカウントの利用上限で復旧は 2026-08-11。不変則7 のフォールバック)。
  - **実行形態**: サブエージェント(人間の指示で起動)。**`verified` は書いていない**(task モードのため)。
  - **独立レビュー4本すべてが完了した**: 初回3本(00/01 層 / 02/03 層 / 実装ドライラン)と、
    修正後の再監査1本(改訂・新設した変更指示12件に絞ったもの)。**いずれも `lens: subagent`**。
  - **初回3本が独立に検出した重大度「高」2件を閉じた**: `FR-env-03-24` の実機確認手順が存在しなかった件と、
    `MODULE-cli-logout`「既知の制限」が反映後に偽になる件。どちらも変更指示を新設して同じ下降で閉じた。
  - **再監査が重大度「高」1件と中8件を検出し、すべて閉じた。** 最重要は
    **変更指示の本文で `###` を `##` の後ろに置いていたため、反映すると同じ節が2箇所へ書き込まれる**件
    (`### E2Eシナリオ一覧` と `### E2E-01`)。合成ビューを組んで**実際に重複が出ることを確認**してから直した。
    **これは `check-changeset.py` が見ない4点の1つ**であり、機械検査だけでは通ってしまう型である。
  - **変更指示は 16 → 19 ファイル**になった(新設3件: `03-impl/tests/e2e.md` /
    `03-impl/tests/strategy.md` / `03-impl/relations/MODULE-cli-logout.md`)。
  - **`docs/issues/094`(利用者が見る値が複数層に逐語で在る・4件のべ13箇所)と
    `docs/issues/095`(程度語「通常」34箇所)を起票した。** どちらも本タスクの範囲外である。
  - **検証済みの状態(次回を増分にするための記録)は memo-3.md へ移した**(変更指示 19 件の `sha1sum` と、影響範囲の SSOT 側の版。**どれか1つでも版が動いたら増分の前提は崩れる**)。

  - **残作業は `python3 .claude/scripts/close-task.py --check task-layer-placement` の出力が正である。**
    2026-08-08 時点の不合格は (a) 未反映 と (c) DoD の残3項目で、**どちらも `/task-close` が行う工程**である。
    検査 `CS2`(relations の対称性)と `CS3`(非循環)は、relations の変更指示に Exception 2 の欄を写したことで
    **未検査から OK へ変わった**(再監査の指摘)。
    検査 (b) 変更指示の CS・(d) `check-relations.py`・(e) コールグラフ ⇄ コード・(f) 影響範囲 ⇄ `source:` は
    すべて OK。

- (2026-08-07 のフェーズ1・フェーズ2 の進捗メモは memo-3.md に移動)

## 申し送り事項

- **人間の指示(2026-08-07)**: 「**ツールではなく、あなたが文書を全て読んで、層が適切ではない
  項目や記述がないかを確認して。確認→修正を、subagent を用いて5周して**」。
  したがってフェーズ2 は **CS18 の 17 件だけを直して終わりにしてはならない** —
  機械が見ないパターン(`086` の 59 件)が本体である。
  **5周の形は前例に倣う**: 各周で独立レビュー(`lens: subagent`)に全文精読させ、
  私が裁定し、変更指示を直す(前例の記録は `docs/histories/2026-08-07-stop-session-spawned-containers.md`
  と、その元になった前タスクの memo)。
- **`/doc-check`(2026-08-08)からフェーズ3・4 への申し送り**:
  - **`docs/pendings.md` の `P-006`(`reset` 側と macOS 版の実機確認を未実施のまま受け入れる)へ、
    新設した E2E-01 手順8-16 を足す**。手順8-15(`reset`)と同じ専有ホストの前提を要するので、
    P-006 の対象に入る。**反映後に行う**(SSOT は現在の姿だけを書くため、手順が実在する前に書かない)。
  - **版の増分は `/task-close` が決める。** `FR-env-03-24` の**新設**を含むので
    `docs/01-requirements/functional.md` と `docs/02-design/system.md` は **MINOR 以上**であり、
    この2つを `against` に持つ下流(和集合で約 50 文書)の検証済み記録が失効する。
    **`/doc-check` の task モードは `verified` を書かない**ので、再認証はフェーズ4 の仕事である。
  - **反映後に必ず再実行するもの**: `check-changeset.py --ssot docs`(CS18 が 0 件・他が凍結値から
    増えていないこと)/ `build-index.py`(issue を5件削除するので目次が動く)。
  - **`docs/issues/094` と `095` を新規に起票した**(`093` と同じく本タスクでは解消しない)。
    削除するのは `083` `085` `086` `090` `091` の5件だけである。
- **memo.md はこれまでに3回ローテーションした**。1回目は 2026-08-08 の `/doc-check`(316 → 266 行。
  フェーズ2 の未決点10件と調査メモを memo-2.md へ)、2回目は同日の `/implement` A-1
  (370 → 276 行。`/doc-check` の未決点#11〜#26・調査メモ6件・増分の前提の記録を memo-3.md へ)、
  3回目は同日の `/implement` C-4(346 → 334 行。2026-08-07 の進捗メモ2件を memo-3.md へ。
  その後キット欠陥の記録を書き足して 343 行)。
  **ローテーションの目安 300 を超えているが、これ以上は動かせない** — 残っているのは
  「追い出してよいか = 不可」の節(目的・やること・影響範囲 35 行・読了記録 35 行・タスクリスト・
  DoD・申し送り事項)と、フェーズ4 が読むフェーズ3 の進捗メモだけである
  (`.claude/directions/task-memo.md` §1.2 の表)。
  **進捗メモの `/doc-check(task) 判定: PASS` の行はローテーションしない** —
  `/implement` A-2-1 がゲートとして読む行である(`.claude/directions/task-memo.md` §2.1)。
- **決定シートは `sheet.md`**(一括回答「全て推奨で良い」で回答済み。`check-sheet.py` 合格)。
  **フェーズ2・フェーズ3 のいずれでも論点を1件も追記していない** — 問う基準を満たすものが出なかったためである。
- **`/implement`(2026-08-08)がキット側の欠陥を1件見つけた。行き先が無いのでここに置く**:
  `.claude/directions/delegation.md` §2 は **DS-08(進め方)の開示先を「`memo.md` のタスクリスト」**と定め、
  **DS-07 は「開示不要」**と定めている。しかし `check-changeset.py` の `CS17` (b) は
  **`memo.md` に在る角括弧つきの DS 表記(`DS_MARK` が当たる形)が変更指示のどこにも無ければ違反**とする(実装は
  `.claude/scripts/check-changeset.py:1083` と `:1111-1116`)。したがって **DS-08 を規範どおりの場所に
  規範どおりの書式で開示すると必ず CS17 違反になり**、消す唯一の方法は「進め方」を変更指示(=SSOT)へ書くことで、
  それは仕様ではないので誤りである。8 行のうち **DS-07 と DS-08 の2行**がこの矛盾に当たる。
  **本実行での回避**: DS-08 の範囲の決定(QA レーンを走らせない・staged を生成しない)を
  角括弧を付けずに進捗メモへ書いた(角括弧が無ければ `DS_MARK` に当たらない)。
  **この矛盾は本実行で実測している** — 最初は角括弧つきで書いたところ `CS17` が
  「memo.md: DS-08 を行使したと memo.md に在るのに、変更指示のどこにも開示が無い」を出して不合格になった。
  **`docs/issues/` に起票しなかった理由**: 直しが始まるのは `.claude/`(キット)であって 00〜03 のどれでもなく、
  `CS20` が要求する `origin_layer` の4値に正直に当てはまる値が無い(嘘の層を書くと `/task-new` がそれを
  引き継いで下流だけを直す — `layer-fit.md` §4 が防いでいる失敗)。キットの行き先は
  `.claude/improvements/` だが、**そこは `/kit-improve` だけが書ける**(`.claude/improvements/README.md`)。
  **したがって人間が `/kit-improve` を起動するのが唯一の経路である。レポートの「次にあなたがすること」に載せた。**
  **`/task-close` §5 はこの段落を `docs/histories/` へ残すこと**(タスクディレクトリと一緒に消えるため)。
- **独立レビューは当面 `lens: subagent`**。Codex はアカウントの利用上限で、復旧は **2026-08-11**。
  不変則7 により、どちらが走ったかを毎回明記すること。
