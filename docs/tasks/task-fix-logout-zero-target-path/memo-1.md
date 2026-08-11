# task-fix-logout-zero-target-path 保管 1

> `memo.md` から移した詳細。2026-08-11 フェーズ3 の C-4-2 で回転した(要約ではなく移動)。

## 調査メモ

| # | 調べたこと | 判明した事実 | 出どころ |
|---|---|---|---|
| 1 | 0件の早期終了の条件 | 削除対象コンテナ0件・認証コピー0件・`_auth_empty=1` の3つが揃うと「削除対象がありません」を出して `exit 0`。手前で集めた `_unmanaged` を参照しない | `claude-dev:993`〜`:1002` / `claude-dev-mac:1061`〜`:1070` |
| 2 | ラベル無しコンテナの表示ブロックの位置 | 通常経路の `:1016`〜`:1017`(確認プロンプト内)と `:1108`〜`:1113`(結果表示。書き戻し警告つき)の2箇所にある。どちらも早期終了より後ろ | `claude-dev:1016`, `:1108`〜`:1113` |
| 3 | 「空」の判定手段 | `docker run ... ls -A /auth` の標準出力が空文字列かだけを見る。手順10 が使う印 `__CLAUDE_DEV_AUTH_LISTED__` を持たないため、一時コンテナが起動できない場合も「空」になる | `claude-dev:993`〜`:997` / 対比は `claude-dev:1078`〜`:1087` |
| 4 | `reset` に同じ穴があるか | **無い。** `reset` は0件の早期終了経路を持たず、`_auth_empty` に相当する判定も持たない(共有ボリュームは `docker volume rm -f` で器ごと消す)。**`docs/issues/053` が案B の理由に書く「A だけだと同じ穴が `reset` 側に残る」は事実として誤りである** | `claude-dev` に `_auth_empty` は `:993` の1箇所のみ / `reset` の削除は `claude-dev:2149` |
| 5 | 「列挙の失敗を0件と同一視しない」の先例 | 02 契約のエラーケースが2行で同じ倒し方を既に定めている。(a)「セッション由来の資源を引く問い合わせそのものが失敗した」→「**列挙が空で返ったこと(0件)と、問い合わせが失敗したことを同一視してはならない**」、(b)「遊休判定に使う Docker への問い合わせが失敗した」→「判定不能を『遊休』と読み替えてはならない」 | `docs/02-design/contracts/cli-container.md:138`, `:141` |
| 6 | `reset` 側の同じ意図が 02 に書かれているか | `PLAN-cli-reset` の「失敗の扱い」が「**列挙の問い合わせそのものが失敗した場合も『消えなかった資源』として扱う**(0件と区別する)」と明記している。`PLAN-cli-logout` には「連携の詳細」節そのものが無い | `docs/02-design/relations.md:187`〜`:188` |
| 7 | 02 が logout に課している表示の状態 | UI 設計の「破壊的操作の状態(`logout` / `reset`)」に「**残した資源**」が既に在り、削除対象の集合が空かどうかで条件づけられていない | `docs/02-design/system.md:443` |
| 8 | logging.md が持つ該当行 | 「管理ラベルを持たないため削除しなかったコンテナ」(INFO)と「管理ラベルを持たないコンテナを残したことによる認証の巻き戻り」(WARN)の2行。どちらも `FR-env-03` 受入基準17 に紐づき、**削除対象が1件以上あるときに限る条件を持たない** | `docs/02-design/logging.md:64`, `:65` |
| 9 | 「利用者が失敗に気づけない」の定義 | `D0-scope-07` の観測点の定義 = 「上のいずれにも現れず、**成功時と同じ表示・同じ終了コード**になる」。052・053 はともにこの定義に当たる | `docs/00-requests/decisions/scope.md:129`〜`:134` |
| 10 | 充足の前提(★ の確認) | `FR-env-03-19` と `FR-env-03-17` はどちらも充足 `完全`。**部分充足の条項に依存していない** | `docs/02-design/system.md:224`, `:226` |
| 11 | closure の検証済み記録 | closure の全 SSOT ドキュメントの `verified.version` が自身の MAJOR.MINOR と一致(原則6 を満たす)。ただし `03-impl/contracts/cli-container.md` の `against` は 02 契約 1.7.0(現行 1.8.0)、`03-impl/tests/cli-logout.md` の `against` は functional.md 1.12.0(現行 1.13.1)で、いずれも**再検証候補**である(`against` は有効性の条件ではない) | 各ファイルの frontmatter |
| 12 | E2E-01 の既存の観測点 | 手順8-11 がラベル無しコンテナの表示を確認し、手順8-13 の (d) が「認証コピーが1つも無い状態で再度 `logout`」= **まさに0件経路**を確認している。052 の確認項目はこの (d) に足せる | `docs/03-impl/tests/e2e.md:147`, `:181`〜`:182` |
| 13 | 走らせるべきテスト(DoD の種) | `relations-query.py --requirement FR-env-03` は「検証しているテスト 0 件 / この要件は未検証(テスト未実装)」を返す。`MODULE-cli-logout` の `tests:` も「なし(シェル実装のため自動テストランナーが無く実機確認で代替する)」。したがって DoD の検証は **E2E-01 手順8 の実機確認**が担う | `relations-query.py --requirement FR-env-03` の出力 / `MODULE-cli-logout.md` frontmatter |
| 14 | 仕様ドキュメントの一括検査(母集団) | `python3 .claude/scripts/check-changeset.py --ssot docs` = **NG 違反 77 件**。うち本タスクに関係するのは「変更相対語」候補の `01-requirements/functional.md:119`(受入基準17 の「本変更」)と `03-impl/relations/MODULE-cli-logout.md:35`・`:235`・`:270`、および issues 052/053 の `origin_layer` 欠落。他は `docs/issues/095`(程度語「通常」)ほか既起票の母集団 | `check-changeset.py --ssot docs` の 2026-08-11 実行 |
| 16 | 手順10 の印の実装(手順6 が写す元) | `_auth_out=$( ( trap '' INT TERM; docker run --rm --entrypoint bash -v "${VOL_AUTH}:/auth" "$IMG_CLAUDE" -c 'rm -rf …; echo "__CLAUDE_DEV_AUTH_LISTED__"; ls -A /auth 2>/dev/null' ) 2>/dev/null || true)` → `grep -qxF` で印を確かめる。**`ls` の標準エラーを捨て `|| true` で終了コードも捨てている**ため、手順6 で終了ステータスを条件に使うには `2>/dev/null` と `|| true` を外して status を別に取る必要がある | `claude-dev:1077`〜`:1082` |
| 17 | 0件経路で再利用する表示ブロック | ラベル無しコンテナの列挙と書き戻し警告は `claude-dev:1108`〜`:1115`、問い合わせ失敗の1行は `:1116`〜`:1117`。mac 側は `claude-dev-mac:1176`〜`:1185`(警告)と `:1184`(問い合わせ失敗) | `claude-dev:1108`〜`:1117` / `claude-dev-mac:1176`〜`:1185` |
| 18 | `spawned_resources` の呼び方(089 の修正で写す元) | 定義は `claude-dev:586` / `claude-dev-mac:651`。`reset` は `claude-dev:1977`・`:1982`(mac は `:2001`・`:2006`)で `spawned_resources container "claude-dev.role=spawned"` を呼び、`:2091` で `_rc_spawned_c` と突き合わせて `_rc_unmanaged` から除く。**logout が写すのはこの突き合わせ1箇所である** | `claude-dev:586`, `:1977`, `:2091` / `claude-dev-mac:651`, `:2001` |
| 19 | 手順6 の現状の判定位置(差し替える対象) | Linux `claude-dev:993`〜`:997`(`_auth_empty`)と `:999`〜`:1002`(早期終了)。mac `claude-dev-mac:1061`〜`:1063` と `:1067`〜`:1070` | `claude-dev:993`〜`:1002` / `claude-dev-mac:1061`〜`:1070` |
| 15 | lane を critical にした根拠と反証 | 根拠: 認証情報の破棄経路であり、失敗形が「消えたと信じたのに残る」= 利用者が気づけない。反証(人間が `standard` へ落とす判断は可能): 用語集「安全」は claude/codex のログイントークンを**一過性**として「鍵情報」から除外し、`NFR-sec-01` の4項目にも `logout` は現れず、`NFR` の法令・コンプライアンスは対象外である。**`security_payment_privacy=true` は fail-closed の選択であって、プロジェクトの `安全` 定義に照らした事実認定ではない** | `docs/00-requests/terminology.md:20` / `docs/01-requirements/non-functional.md:40`, `:64`〜`:66` |


## 進捗メモ(フェーズ1・2)

- 2026-08-11 フェーズ1: 00〜02 を全文読了(lane: critical)。closure を確定し、`docs/issues/052` と
  `docs/issues/053` に欠落していた `origin_layer: 01` を補った。決定シート(概念3件・論点3件)を
  `sheet.md` に置いた。
- 2026-08-11 フェーズ1 完了: 人間がシートへ記入(概念3件に記入、論点3件は空欄 = 既定を承認)。
  発言「記入したので進めて」で返答済みと確定。**確定した方針 = 論点1 案A / 論点2 案B /
  論点3 畳む**。`docs/issues/089` を closure に加えた(行き先は既存の行のまま)。
  `check-sheet.py` 合格(SH4 / 読了記録とも OK)。`phase: ドキュメント` へ進め `/task-doc` を実行する。

- 2026-08-11 フェーズ2 下降: **00 完了**(変更なし — `D0-env-08` 項1・項5 と `D0-env-05` 項2 を
  読み直し、条件節を動かす必要が無いことを確認)。**01 完了**(`functional.md` の `FR-env-03` 節)。
  **02 完了**(`logging.md` / `contracts/cli-container.md` / **`system.md` を closure へ追加** —
  `SCR-01` の「表示は 01 が正」の列挙に受入基準19 が入らないと、0件経路の表示を 02 から辿れない。
  CS19 が要求する「分割の根拠」も `sections` に載せ、`DSN-mod-01`〜`07` を読み直した(全件継続))。
  次は 03。

- 2026-08-11 フェーズ2 実装ドライラン: パス1 で未決点2件(上表 2・3)。**どちらも問う基準を満たさない**
  (観測される振る舞いは受入基準18・19 が既に固定しており、残るのは実現方法)ので決めて開示した。
  行使した委任: **[DS-02]**(手順6 の判定に終了ステータスを足す)/ **[DS-03]**(0件経路で出す行の範囲)/
  **[DS-05]**(印の判定を関数に切り出さない)。開示先はすべて `MODULE-cli-logout` の「実装上の判断」
  15・16 と、`03-impl/tests/*.md` の「テスト設計の判断」4・5 / e2e.md の `[DS-01]` 1行。
  パス2 の事実は調査メモ 16〜19 に記録した。`check-changeset.py` **合格(違反なし)**。
- 2026-08-11 フェーズ2 の変更指示を書き切った(10 ファイル)。**02 の closure が2件増えた**:
  `system.md`(`SCR-01` の表示の列挙)と `relations.md`(`PLAN-cli-logout` の呼び出す先)。
  後者は 089 の修正が `spawned_resources` の呼び出しを増やすため(CS9 が両方向を要求する)。

- 2026-08-11 **/doc-check(task) 判定: PASS**。実行形態: 作成者セッション(サブエージェント不可のため
  §0A のフォールバック)。**独立レビュー: Codex**(`gpt-5.6-sol` / reasoning high、指摘 10 件)。
  レンズは作業ツリーへ書き込んでいない(`git status` 前後一致)。反復 1/2 で収束。
  **修正の区分**: 反映不能の解消(`02-design/system.md` の本文順序)= **MINOR**(指示の構造変更)/
  レンズ指摘 1・6 の解消(02 契約へ `logout` の問い合わせ失敗時を追記、03 契約の終了コードの
  自己矛盾の解消)= **MINOR** / 指摘 2・3・4・5 の解消(E2E の前提と部分手順番号)= **MINOR** /
  指摘 7・8 の解消(行番号と「4箇所」の事実修正)= **PATCH** / `logging.md` 1行新設 = **MINOR** /
  程度語と表示範囲の明確化 = **PATCH**。
  **変更指示の合計バイト: 179,746 → 183,224(+3,478)**。増加は (a) 02 契約と logging.md への
  行追加、(b) E2E の手段が実機で成立しないことが判明したための書き直し(削除では直せない)による。
  行使した委任: [DS-01] / [DS-02] / [DS-03] / [DS-05]。
  変更指示のハッシュ(sha256 先頭12桁):
    - 01-requirements/functional.md 7c15fd573f2f
    - 02-design/contracts/cli-container.md 9b743778ab97
    - 02-design/logging.md c3befb95cf83
    - 02-design/relations.md 62ffe6125dac
    - 02-design/system.md fd564c4bbb8e
    - 03-impl/contracts/cli-container.md 88081d27f074
    - 03-impl/relations/MODULE-cli-common-spawned-resources.md e8bab90644b8
    - 03-impl/relations/MODULE-cli-logout.md 7b53b3e9422f
    - 03-impl/tests/cli-logout.md 30b3afd63460
    - 03-impl/tests/e2e.md 504433923e4b
  closure の版: functional.md@1.13.1 / logging.md@1.5.0 / contracts/cli-container.md@1.8.0 /
  system.md@2.10.1 / relations.md@1.9.0 / 03-impl/index.md@1.22.1 / 03-impl/contracts/cli-container.md@1.7.0 /
  tests/cli-logout.md@1.5.0 / tests/e2e.md@1.6.0
  **最弱点**: `FR-env-03-19` が1条項で3つの義務(0件で 0 終了 / 確認できなければこの経路に入らない /
  ラベル無しコンテナの表示)を負っており、条項単位の充足・検証状態を3つに分けて数えられない。
  条項を分ける案は 02 カバレッジ表と 03 テスト表の行追加を伴い、人間が承認した方針
  (「受入基準19 に2点を足す」)を超えるため今回は分けていない。

