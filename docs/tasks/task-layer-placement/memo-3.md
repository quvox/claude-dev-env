# task-layer-placement 解決済みの経緯 3(フェーズ2〜`/doc-check` の未決点・調査メモ・増分の前提)

<!-- `/implement task-layer-placement`(2026-08-08)がローテーションで移した。
     memo.md が 370 行になっていたため(`.claude/directions/task-memo.md` §2、および
     memo.md の申し送り事項が「次にこのファイルを開くスキルがもう一度ローテーションすること」と
     指示していたため)。**要約はしていない — 原文のまま移した**。 -->

## 未決点

**`/doc-check`(2026-08-08)の実装ドライラン パス1 で出た点と、その決着**(#11〜#26)。
**いずれも決着済みで、人間判断へ回したものは無い。**

| # | 出た点 | 決着 | 記録先 |
|---|---|---|---|
| 11 | 新設条項 `FR-env-03-24` の実機確認手順として 03 のテスト対応表が指す「E2E-01 手順8」に、`logout` の後で `stop` を走らせる並びが1つも無い(**指し先が空**。独立レビュー3本が独立に検出) | **ドキュメント記載**: `03-impl/tests/e2e.md` の変更指示を新設し、部分手順 8-16 を作った。既存の後片付けは 8-17 へ繰り下げ(`8-16` を名指す記述が他に無いことを確認済み)。指し先を `手順8-16` に確定 | 変更指示 `03-impl/tests/e2e.md` / `03-impl/tests/cli-logout.md` |
| 12 | `MODULE-cli-logout`「既知の制限」の「この帰結は `D0-env-05` 項2 の理由と食い違う」が**反映後に偽になり**、参照する `docs/issues/090` も消える(独立レビュー3本が検出) | **ドキュメント記載**: フェーズ2 は DoD の1行に委ねていたが、`/task-close` §2 の relations 再生成は**コードから出せるものしか直さない**ので自動では直らない。`03-impl/relations/MODULE-cli-logout.md` の変更指示を新設して同じ下降で閉じた | 変更指示 `03-impl/relations/MODULE-cli-logout.md` |
| 13 | 03 のテスト対応表の判断1「見直す条件」(`reset` 側だけに固有の手順が生じたとき)が**書いた時点で既に真**だった(受入基準9 が `logout` 側 8-5 と `reset` 側 8-12 に分かれている) | **ドキュメント記載**: 判断の意図(状態を持つ場所を1つに保つ)は変えず、現物に合う条件へ書き直した | 変更指示 `03-impl/tests/cli-logout.md` |
| 14 | `FR-env-12-9` / `UC-06` A3 の「対象外とする理由は **02 の設計判断**が持つ」が**空手形**(`workspace-write` は 02・03 のどこにも無い。実在は `D0-dist-04` 項6) | **ドキュメント記載**: 指し先を `D0-dist-04` 項6 へ直した | 変更指示 `01-requirements/functional.md` / `usecases.md` |
| 15 | `FR-env-08-4` に書いた「**ダッシュボード側の表示は要件として課していない**」が、未解決の `docs/issues/063`(バナーは実装済み・単体テスト4件つきだが正常系を課す条項が無い)と**逆向きの断定**になる | **ドキュメント記載**: 断定をやめ、063 への言及に替えた。**要件を課すか否かを決めるのは 063 の解消であって本タスクではない**(SSOT は現在の姿だけを書く) | 変更指示 `01-requirements/functional.md` |
| 16 | `environments.md` に `go test -cover` の行を足しただけで `03-impl/tests/strategy.md` 側からコマンド文字列を落としていない(**移送の片側落ち**。`relations-query.py --health` の側は両側を処理している) | **ドキュメント記載**: `03-impl/tests/strategy.md` の変更指示を新設し、コマンド欄を `environments.md` への指し先へ替えた。あわせて条項数 209→210 の数え直しも同じ下降で直した | 変更指示 `03-impl/tests/strategy.md` |
| 17 | `D0-env-06` の内容欄が付与位置を 02 へ委ねた直後に、理由欄と却下案欄が「イメージ側」に固定している(**同じ決定の中で委ねた事柄を別の欄が決めている**) | **ドキュメント記載**: 付与位置は人間の選択なので 00 に残し、02 へ委ねるのは変数の名前と値の形式だけにした | 変更指示 `00-requests/decisions/env.md` |
| 18 | `D0-env-04` が `make install` の `uname -s` 判定と symlink という実装の手順を持ったまま。同じ事柄を `FR-env-10-1` は「02/03 が定める」へ改める(**01 が委ねた先より上流が具体を握る**) | **ドキュメント記載**: 影響範囲に `D0-env-04` を追加し、手順だけを落とした(技術の選択は残す)。決定シート「方針合意」の 00 の行の内側 | 変更指示 `00-requests/decisions/env.md` |
| 19 | `D0-sec-09` から `iptables` を落とすと、`D0-sec-04` の委任範囲に残る「どのチェインに規則を置くか」の**「チェイン」が 00 のどこにも根拠を持たない**  | **ドキュメント記載**: 影響範囲に `D0-sec-04` を追加し、「規則をどこに置くか」へ一般化した(委任の意味は変えない) | 変更指示 `00-requests/decisions/sec.md` |
| 20 | 決定シート 概念3 の推奨は「`NFR-ops-02` の測定方法を設計の検査へ書き替える」で人間が承認したが、その**前提(03 に受け皿が無い)は事実と違い**、書き替えると目標値「OS 分岐が 0 件」を測れなくなる | **上流が既に答えているので文書に記載**(D15 の (a))。人間の決定そのものは「**落とさずに残し、受け皿を作る**」であり、**受け皿は既に実在する**(`docs/03-impl/tests/cli-common.md:37`・`:72`)ので、原文のまま残すことが決定に従う唯一の形である。**問う基準は満たさない**(決定と衝突していない)ため決定シートへは載せない。**人間が異議を持つ場合は本レポートで差し戻せる** | 変更指示 `01-requirements/non-functional.md` の `reason` (f) |
| 21 | **変更指示の本文で `###` を `##` の後ろに置いていた**(`02-design/system.md` の `### E2Eシナリオ一覧` と `03-impl/tests/e2e.md` の `### E2E-01`)。本文の中で `##` の子として読めるため、**反映すると同じ節が2箇所へ書き込まれる**(`.claude/directions/change-set.md` が実測失敗として挙げる型。合成ビューを組んで**実際に2箇所に出ることを確認した**。再監査が検出) | **ドキュメント記載**: 本文を「深い見出しを先に」の順へ並べ替え、親の節が子を飲み込まない形にした。合成ビューで見出しの重複が 0 件になることを確認済み | 変更指示 `02-design/system.md` / `03-impl/tests/e2e.md` |
| 22 | `NFR-sec-03` から落とす「E2E-04 の実機確認手順で当該 worker ウィンドウ内の `env` を確認する」も、**E2E-04 の手順に `env` を見る部分手順が1つも無い**という #11 と同型の空手形だった(再監査が検出) | **ドキュメント記載**: E2E-04 に手順8 を新設した。**この2件で「`03-impl/tests/` の識別子欄が指す実機確認手順が実在しない」箇所は 0 件になる**(`手順8-N` の全指し先と `E2E-04` を機械照合して確認) | 変更指示 `03-impl/tests/e2e.md` |
| 23 | `00` の `D0-env-05` 項2 が「回収手段は `claude-dev reset` と手動だけになる」という**利用者から見た帰結の断定**を持ち、01 の `FR-env-03-24` と同じ主張になっていた(02 からは同じ一文を落としているのに 00 に適用していない。再監査が重大度「高」で検出) | **ドキュメント記載**: 00 は「この帰結を承知のうえで `logout` には掛けない」という決定と理由だけを持ち、以後どの操作で消せるかは項2 の末尾が既に `FR-env-03` の受入基準へ指している | 変更指示 `00-requests/decisions/env.md` |
| 24 | relations の変更指示(`MODULE-cli-logout.md`)が `change-set.md` Exception 2 の relations 欄を frontmatter に持たず、**`CS2`(対称性と ID)と `CS3`(非循環)が未検査のまま合格していた**(再監査が検出) | **ドキュメント記載**: 現行の relations 欄13行をそのまま写した。`CS2` / `CS3` が働き、いずれも OK になった | 変更指示 `03-impl/relations/MODULE-cli-logout.md` |
| 25 | 変更指示の `reason` が宣言していない編集・事実誤りが6件(`SCR-01` の状態行の具体を落とした件 / `NFR-ops-02` を「原文のまま」と書きつつ指し先を足していた件 / `strategy.md` の判断を「5件」と数えた件(現物は2件)/ `MODULE-cli-logout` の「影響欄は変えない」/ `D0-env-06` の移し先の名指し / `logging.md` の行名)| **ドキュメント記載**: 6件とも `reason` を実態に合わせた。**`reason` は `/task-close` §2 が突き合わせに使う唯一の記録**なので、事実と違うまま残せない | 各変更指示の `reason` |
| 26 | `[DS-01]` を1件行使した(`03-impl/tests/e2e.md` の「テスト設計の判断」に**部分手順16 を手順8-15 より後に置く**判断を追加)。`CS17` が「memo の記録 0 件」と表示していた | **委任で決定・開示済み**: 理由 = `logout` が Claude コンテナを消すので、先に置くと以降の部分手順の前提が壊れる / 見直す条件 = `logout` が Claude コンテナを削除しなくなったとき。開示行は変更指示の本文に書いた | 変更指示 `03-impl/tests/e2e.md`「テスト設計の判断」 |

## 調査メモ

- **`/doc-check`(2026-08-08)が合成ビューで実測した機械検査**(現在の SSOT に変更指示 18 件を当てた姿。
  `python3 .claude/scripts/check-changeset.py --ssot <合成ビュー>`):

  ```
  CS8  曖昧語・未決点:      42 → 35 件
  CS11 参照実在:            19 → 19 件
  CS18 要件に降りてきた機構: 17 →  0 件  ★ DoD の目標
  CS19 理由の網羅:          27 → 26 件
  CS20 issue の起点層:      53 → 53 件
  NG 違反:                 158 → 133 件
  ```

  **凍結値から増えたものは1つも無い。** CS8 の 7 件減は、変更指示が触った節の程度語「通常」を
  意味を保って直した分である(`acceptances.md` / `decisions/sec.md`×2 / `usecases.md`×2 /
  `02-design/system.md` / `03-impl/tests/e2e.md`)。CS19 の 1 件減は `03-impl/tests/cli-logout.md` に
  「テスト設計の判断」を新設した分。

- **コード ⇄ 03 の不変則は保たれている**: `build-callgraphs.py --out docs/03-impl/callgraphs --check` と
  `cluster-features.py` がいずれも「最新」を返す。`check-relations.py` 合格(83 ファイル / 83 ID)、
  `check-contracts.py` 合格、`callgraph-check.py` は 高 0 / 中 6 / 低 21 / 参考 20。
  **中の 6 件は CG3(callees に宣言があるが機械が辺を出せない)で、relations 本文が根拠を持つことを
  現物で確認したので誤検知と裁定した**(shell の `exec` 起動とインターフェース越しのディスパッチを
  抽出器が辺として出せないだけである)。

- **タスク配下の staged callgraphs は生成しない。** `resolve-callgraph-out.py` は
  `new-features/03-impl/callgraphs` を返すが未作成である。**本タスクはコードを1行も変えない**ので
  生成しても SSOT の複製にしかならず、しかも `docs/issues/076`(staged callgraphs を変更指示と
  誤認する)が既知の不具合として追跡している。`/task-close` §2 がコードから再生成する。

- **02 ⇄ 03 の連携差分(check E)は 0 件**: PLAN 64 件すべてに `MODULE-*` があり、MODULE のみ 19 件は
  `docs/02-design/relations.md:103` の除外宣言(`MOD-orchestrator` の内部関数 18 本 +
  自己検証題材の実装本体)と全件一致する。契約の差分 0 / slug 不対応 0。

- **条項の 1:1**: 合成ビューの機能要件は **210 条項**(重複・欠番なし)で、02 の要件カバレッジ表・
  03 のテスト対応表のいずれとも過不足なく一致する。E2E-01〜06 が UC-01〜06 を覆う。

## 進捗メモ(2026-08-08 `/doc-check` が残した「検証済みの状態」= 次回を増分にするための記録)

変更指示のハッシュ(`sha1sum`):

```
e8d44f7969f60d2f110a7ed2bf711dd31375c5b8  00-requests/acceptances.md
af4046ffa6345bad19cc3066df8bdad27e9f6c23  00-requests/decisions/auth.md
208ba3da8f5cc1f5d312e64e655ae06ab887476a  00-requests/decisions/dist.md
133c58a7bfc1fe562e13738abffdfbe4cc71a908  00-requests/decisions/env.md
dba8fe930b2152f66d6923c0eab612f32e659199  00-requests/decisions/orch.md
6cd09552228b07528aaf5c9c7c0449b04cc00947  00-requests/decisions/sec.md
d1762e134d16ed701e16edff91df881ab713b5b1  00-requests/terminology.md
709cf3a47561e34046b83e0a899ce75565008e24  01-requirements/functional.md
c856c58155b71208741e84a877f5c309529a6952  01-requirements/non-functional.md
c35d2fd592154e1c5e8c6d3941f4412235297f55  01-requirements/usecases.md
9ba9bfed570691442af04baf95751000cad771b2  02-design/contracts/cli-container.md
e7002f9b38b78ac47d555fa33d2b8dce7c940250  02-design/contracts/cli-orchestrator.md
f77a070b637e277411ee38d430c3a557c90f6132  02-design/environments.md
3e96b558e750b8ceac17c8a6c3f90acbf3581a6a  02-design/relations.md
83308b360c39b666a9d0473a00eec23fbda03213  02-design/system.md
ba0068a5e596537a79fa45da7d8de6efff40c4ce  03-impl/relations/MODULE-cli-logout.md
5a4e04f497f070ecd267e656478b5cef67e59df5  03-impl/tests/cli-logout.md
a1f63b5c265f8497dcfe731e3ac3966333667bdc  03-impl/tests/e2e.md
82ff79fe509a8915cff98a93881cbffbdbf856a4  03-impl/tests/strategy.md
```

影響範囲(closure)の SSOT 側の版:

```
00-requests: acceptances@1.2.0 / terminology@1.3.0 / request@1.3.0 /
             decisions: auth@1.2.0 dist@1.0.1 env@1.3.0 orch@1.3.0 scope@1.2.0 sec@1.1.2
01-requirements: functional@1.11.0 / non-functional@1.5.0 / usecases@1.3.0 /
                 system@1.1.0 / decisions/split@1.2.0
02-design: architecture@1.4.0 / system@2.7.0 / relations@1.6.0 / environments@1.1.0 /
           logging@1.4.0 / contracts: cli-container@1.6.0 cli-orchestrator@1.1.0
           docker-api@1.1.0 entrypoint-firewall@1.0.1 orchestrator-prompt@1.3.0
03-impl: tests/cli-logout@1.4.0 / tests/e2e@1.3.0 / tests/strategy@1.3.0 /
         relations/MODULE-cli-logout@(版なし)
```

**どれか1つでも版が動いたら増分の前提は崩れる**(全件をやり直す)。

## 進捗メモ(2026-08-07 フェーズ1・フェーズ2 — `/implement` C-4 が移した)

- 2026-08-07 フェーズ2 の下降(`/clear` 後の新しい文脈)。**この順で書いた**:
  - **0 完了**: 読了記録の未読了11ファイルを私自身が全文読んだ(読む範囲の節を更新済み)。
  - **00 完了**: `acceptances.md` / `terminology.md` / `decisions/{auth,env,orch,sec}.md` の
    6ファイル。`decisions/dist.md` は**変更なし**と判定(理由は「影響範囲」の表に追記した)。
  - **01 完了**: `functional.md` / `non-functional.md` / `usecases.md` の3ファイル。
  - **02 完了**: `system.md` / `relations.md` / `environments.md` /
    `contracts/{cli-container,cli-orchestrator}.md` の5ファイル。
  - **03 完了**: `tests/cli-logout.md` の1ファイルだけ(新設条項 `FR-env-03-24` の受け皿。CS13 の要求)。
  - `check-changeset.py`: **合格(違反 0 件)**。`sections` の SSOT 側見出しとの文字列一致、
    `anchors` の参照先の実在も別途スクリプトで照合済み(CS が見ない4点のうち2点)。
- 2026-08-07 フェーズ1。前タスク `task-stop-session-spawned-containers` を `/task-close` で
  完了・削除し(コミット `914d840`)、規範 `KIT-where-technology-decisions-belong` を
  `/kit-improve --apply` でキットへ適用してから本タスクを宣言した。
  **この順序は人間の指示による**(規範が本タスクの判定基準そのものであるため)。
