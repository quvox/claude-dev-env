# ツールと環境整備

このファイルは**運用の入口**である。ツールの一覧、環境の作り方、困ったときの対処を書く。
**規範(何が正しいか)はここには書かない** — 矛盾したら下の「正」の列にあるファイルが勝つ。

## 0. 三行で

- **ツールの依存はキット専用 venv (`.claude/.venv`) に閉じ込める。プロジェクトの環境にもホストにも
  何も入れない。**
- **Python は依存ゼロで動く**(標準 `ast`)。**Go / TypeScript / infra は tree-sitter と PyYAML が
  必須**なので `setup-tools.py` を1回走らせる(**`/setup` がこれを走らせる**ので、導入の経路では
  手で打たなくてよい)。**必須依存が無いと `build-callgraphs.py` は起動時に
  直し方を1行言って止まる**(縮退経路は無い — 半分見えない地図で検査を完走させない。
  inspection-17 判断1)。その言語を解析しない選択は `callgraph-config.local.json` の
  `enabled: false` で明示する。shell / make は正規表現のみ(Tier 3)で外部依存なし。

## 1. 環境整備

```bash
python3 .claude/scripts/setup-tools.py --check     # 何も変えずに、今どの精度が使えるかを報告
python3 .claude/scripts/setup-tools.py             # キット専用 venv を用意して依存を入れる
python3 .claude/scripts/setup-tools.py --host-tools # 任意ツール(hcl2json)も入れる(opt-in)
python3 .claude/scripts/setup-tools.py --clean     # .venv と .tools を消す(いつでも再構築できる)
```

### どこに何が入るか

| 置き場所 | 中身 | git |
|---|---|---|
| `.claude/.venv/` | pip で入れたツールの依存 | **管理外**(`.claude/.gitignore`) |
| `.claude/.tools/` | ホストのツールチェーンで入れる任意ツール(`hcl2json` 等) | **管理外** |
| `.claude/scripts/requirements.txt` | 入れたい依存の**名前**(段階ごとに増える) | 管理下 |
| `.claude/scripts/requirements.lock` | 実際に入った**バージョン**(初回導入時に生成) | 管理下。再現性が要るなら共有する |

**プロジェクトの `requirements.txt` / `pyproject.toml` / `package.json` には触らない。**
ツール側の都合とプロジェクトの依存が混ざると、どちらの都合で壊れたのか分からなくなる。

### venv を意識しなくてよい

第三者依存を使うエントリスクリプト(`build-callgraphs` / `callgraph-check` / `check-contracts` /
`cluster-features` / `propose-features`)は `.claude/.venv` があれば
**そのインタプリタで自己再実行する**。残りは標準ライブラリだけで動くので venv を要らない。
だから常に `python3 .claude/scripts/<script>.py` と打てばよい。
素の環境で走らせたいときだけ `CGX_NO_REEXEC=1` を付ける。

### 精度(Tier)と、誰が何を用意するか

| 段 | 何が要るか | 誰が用意するか |
|---|---|---|
| **Tier2(既定)** | `.claude/.venv` の pip パッケージだけ。**ホストの言語ツールチェーンは不要** | `setup-tools.py`。Python は**依存ゼロ**(標準 `ast`) |
| **任意ツール(opt-in)** | `hcl2json`(Terraform 用)。**ホストに Go が要る** | **人間**。`--host-tools` のときだけ `.claude/.tools/` の中にだけ入れる。**グローバルにも sudo でも入れない**。無くても `python-hcl2` で代替できる |
| **Tier3(降格。正規表現のみ — 呼び出し関係は不完全。shell / make は常時 Tier3 で上位 Tier が無い)** | 何も要らない | — |

**この表が「何をどこに入れるか」の正である**(`.claude/directions/callgraphs.md` §5.9 はここを引く)。
**Tier の定義、「Tier 3 の結果を『網羅した』と報告してはならない」、型解決による Tier1 を
持たない理由は `.claude/directions/callgraphs.md` §5.8 が正**(ここには書き写さない。
実装側の判断の記録は `.claude/scripts/callgraph-design.md` §6.1)。

## 2. ツール一覧

| スクリプト | 答える問い | 正(規範) |
|---|---|---|
| `setup-tools.py` | ツールは揃っているか。今どの精度が使えるか | このファイル |
| `build-callgraphs.py` | **コードの関数・呼び出し関係・エンドポイントは何か** | `directions/callgraphs.md` |
| `resolve-callgraph-out.py` | **その callgraphs をどこに置くか**(フロー分離後は常に SSOT を返す。`--ssot` を明示して呼ぶ) | `directions/callgraphs.md` §3.1 |
| `propose-features.py` | **機能表に足すべき行は何か**(機能候補・共通基盤候補・統合候補) | `directions/features.md` |
| `cluster-features.py` | **機能間の関係はどうなっているか**(機能表 × callgraph → 境界の辺・共有関数・未到達)。書き先は SSOT(`--out` は `build-callgraphs.py` と同じ値にする — 原則1) | `directions/features.md` |
| `callgraph-check.py` | **コールグラフと機能間連携仕様書は一致しているか**(FT/CG 検査。実装している ID は `--list`) | `directions/callgraphs.md` §6 |
| `check-contracts.py` | **契約(OpenAPI)は妥当か。設計 ⇄ 実装 ⇄ コードが一致しているか**(CT 検査。実装している ID は `--list`) | `directions/02-design.md` contracts 節 |
| `relations-query.py` | **これを変えると何に響くか**。呼び出し元・経路・構造の健全性 | `directions/relations.md` §6 |
| `check-relations.py` | 機能間連携仕様書の**内部整合**(対称性・参照実在・必須項目)。**機能表との1:1(FT3)は見ない** — その検査IDは `callgraph-check.py` が1本で持つ | `directions/relations.md` §6.3 |
| `check-ssot.py` | **SSOT 全体に仕様ドキュメントの一括検査**(CS 群 — 曖昧語・参照実在・同型走査・要件に降りた機構・理由の網羅・課題票の起点層・**件数の主張**(本文の数字と実体の数の突き合わせ)ほか。**この並びは抜粋であり、正の一覧は `--list`**、CS21 の自己検査は `--selftest`)。数秒で終わるので編集のたびに回せる。`/build` §1 が母集団の凍結に、`/verify-docs` §1 が検査のたびに使う | このスクリプトの `--list` と docstring |
| `check-backlog.py` | **未クローズの課題票と残務の計器**。数えて出すだけで**何も拒まない**(旗も設定も無い) | CLAUDE.md §3 / `directions/issues-pendings.md` §1・§2.1 |
| `check-debt.py` | **検証負債の計器**(未検証構築記録・鮮度スタンプの古さ・**全数の最終実行**・未回答シート・**試験区分の置き場の宣言漏れの件数**)。数えて出すだけで**何も拒まない**(宣言漏れも義務ではない — 内訳と直し方は `stamps.py check` の注記)。`--demote` は滞留した building を降格する。**鮮度スタンプの古さは記録日からの日数であって失効の判定ではない** — いま green かは `stamps.py check` が正 | CLAUDE.md §4 / `directions/flows.md` §4 |
| `check-mission.py` | **ミッションの予算の計器**(①台帳の `開始:` からの経過時間と `予算:`、②出した作業指示の本数と計画の見込みの2倍、③同じ要件への修繕の本数=3本目)。**数えて出すだけで何も拒まない** — 発火中に配車を止めるのは規範の禁止のほう(`orchestration.md` §3.0 の6)。読むのは `.claude/missions/<mid>/` の台帳と `orders/` だけ。**欄を持たない古い台帳では発火しない**。再開は人間が台帳に書く `- 再開許可:` の1行 | `directions/orchestration.md` §3.0 の6・§7 / `skills/mission/SKILL.md` §3 |
| `stamps.py` | **鮮度スタンプの記録と、デプロイゲートの判定**。verify 系フローが完走時に `record`(範囲を絞った run は `--covers <path>`、全数を回した run は `--full`)、デプロイ前に `check`(全フロー green で 0。red なら**回すべき最小の範囲**を印字)。`deps` は失効判定の依存集合(許可リスト)を印字する。**green は無条件には記録できず、`record` が拒むことがある**(条件の正は `flows.md` §2 — 見るのは**そのフローの依存の中だけ**であり、依存の外の汚れは拒まない。red はいつでも記録できる)。**記録先の `.claude/state/stamps.json` は git で共有する** — 打つのは1周に1回、明示のパスで(`flows.md` §2)。**`release` は別の仕事である** — 出したことを `.claude/state/releases.json` へ1件残し、**成果物の版の桁を構築記録の宣言から決める**(人間は桁を指定しない。`--current` は版だけを印字する。`flows.md` §9) | CLAUDE.md §3・§4 / `directions/flows.md` §2 |
| `check-buildrecord.py` | **構築記録は突き合わせ可能な形か**(BRC 検査 — 一覧は `--list`。frontmatter・critical フラグの fail-closed 照合・クロージャ・主張・基本要件の全件判定)。`/build` の構築記録ゲート | `directions/build-record.md` / `directions/baseline.md` |
| `check-baseline-verdicts.py` | **過去の構築記録の `非該当` を、クロージャの中身に照らして疑う計器**。`非該当` の行ごとに、その記録が宣言したクロージャのファイルを `baseline-evidence.json` の証拠パターンで走査する。**`verified` を含む全状態の記録を読む** — 他の見る者が届かない隙間がこれの持ち場である(**分担の正は `directions/baseline.md` §1 の4。ここでは言い直さない**)。**過去の記録は、その記録の `commit:` 時点の中身に照らす**(いまの作業ツリーに照らすと、後から同じファイルへ機能が増えれば偽陽性、移動・削除なら見逃しになる。`--worktree` で今の中身に切り替わる)。**数えて印字するだけで、疑いの有無では何も拒まない**(終了コード 0。使い方・前提エラーだけ 2)。**疑いの数と一緒に、「検査できなかった行」「部分的にしか検査できていない行」「記録に判定行が無い BR」も印字する**(最後の1つは、足したばかりの項目が過去の記録に対して盲目であることを言う。**遡って埋め直さない** — `baseline.md` §4.3)。**疑いを黙らせる口が2つある** ★ — ファイル単位の `skip_globs` と、**行単位の `adjudicated`**(`baseline-evidence.json` / `.local.json`。記録と `BR-nn` と `why` の3つを書く)。**`why` の自由文しか歯止めが無い**ので、**人間が裁定したものだけを入れる** — 計器を黙らせるために使えば、その行はもう誰も見ない | `directions/baseline.md` §1 の4 / `skills/verify-impl/SKILL.md` §1 |
| `relations-coverage.py` | 抽出器が無い言語の**網羅性**(正規表現ベース) | `directions/relations.md` §6 |
| `scan-entrypoints.py` | 抽出器が無い言語のエントリポイント候補(**最後の手段**) | `directions/relations.md` §6 |
| `build-facts.py` | **事実の生成器**。手で保守する文書の中の**機械の欄**(`<!-- BEGIN GENERATED: build-facts.py id=… -->` 〜 `<!-- END GENERATED: build-facts.py -->`)を`update` で埋め、`check` で**差分ゼロと参照先の実在**を見る。宣言は `docs/facts.json`(抽出器は `count_files` / `count_matches` / `capture` / `mirror_table` の**組み込み4つだけ**で、任意のコマンドは実行しない)。**F2 と F3 の検査の先頭で走らせる**(合格の条件に入っている)。宣言が無いプロジェクトでは 0 を返す | CLAUDE.md 原則1・原則10 / `directions/conventions.md` の「同じ事実を2か所に手で書かない」 |
| `build-index.py` | 各 `index.md` の再生成 | CLAUDE.md 原則10 |
| `doc-health.py` | **上流変更後の再検証候補**、**棚上げ・課題票の鮮度確認の候補**(記録日つきの一覧。判定は書かない)、文書・仕様IDから辿る**履歴逆引き索引**を生成する。`--check` は生成物の鮮度検査、`--health` は書き込まず警告件数を表示する。既存SSOT・確定済み履歴は変更しない。**今日の日付を使わないので、同じ入力なら同じ生成物になる**。残務(`docs/residual.md`)については `--as-of --sweep --record=<履歴>` が**重複と対象が実在しない行だけ**を落とし、`--rotate` が 50行以上のときファイルを `docs/residual-NNN.md` へ押し出す(**1行も落とさない**。錠つき — 2本が重なっても連番を採り合わない)。**`--next-issue-id` / `--next-pending-id` は課題票・棚上げの連番を錠の下で払い出す**(2026-09-05。手で数えると削除済みの再発行と並走の同番が起きる — issues-pendings.md §2.2・§3) | CLAUDE.md 原則6・原則10 / directions/issues-pendings.md §2.1・§8 |
| `check-sheet.py` | **SSOT を書き始めてよいか**(決定シートが人間に確認されたか — 「一括回答」に1行あるか、全ブロックが埋まっているか、またはチャット回答の構築記録への転記(逐語引用+日付)があるか。SH 検査 — 一覧は `--list`)。fail-closed。**SH10 は「問うてはならないことを問っていないか」** — エラー処理・テスト・ログ・設定(DS-01〜DS-04)の論点は根拠なしに載せられない | `directions/build-record.md` §3 / `skills/build/SKILL.md` §1 |
| `kit-patch.py` | **このキットをどう改造したか。本流へ戻すパッチは何か**(改造前に `status`、パッチは `diff --slug <slug>`)。配布・控え・差分の3者が `kit-dist.json` の include だけを正とする(`files` がその列挙。`.claude/improvements/` はどれにも入らない — 改善の作業跡は `diff` が消す)。**控えの取り直しは人間の操作ではない**: `diff` の成功時と、配布物の入れ替わり(`kit-manifest.json` の指紋)を見た `status` が自動で取り直す(旧 `snapshot --force` は廃止)。**パッチの置き場は道具が持つ**(`diff --slug` が `.claude/improvements/patches/KIT-<slug>.patch` へ書き、絶対パスを出す。`status` は書く前からその場所を出す)。**パッチは宛先を名乗る**(先頭の `# キット: <名前>` — `kit-dist.json` の `kit` から。本流の `make patch` がこれを読んで宛先を決める)。**手順の正は `/kit-improve`** — 単体で呼ぶのは `status` の確認までにする | `skills/kit-improve/SKILL.md` / CLAUDE.md §3(キットを直してよい2つの縛りと記録) / `scripts/kit-dist.json` |
| `kit-manifest.py` | **上書き展開した後、旧版の取り残しはどれか**。`check` が現物を4つに割る(旧版の取り残し / 改造 / 欠落 / キット管理外)。**tar は上書きしても削除しない**ので、廃止したスキルやスクリプトは展開先で生き続ける。`update` は配布側が版ごとの確定一覧(`.claude/kit-manifest.json`)を作り直す(`make check` が鮮度を見る) | `scripts/kit-dist.json` / 導入手順(`make dist` の出力) |
| `kit-migrate.py` | **新しい版を展開した後、このプロジェクトで要る移行はどれか**。`.claude/migrations/*.md`(1件 = 1ファイル)の `detect` を走らせ、**要るものだけ**を並べる(`check` は要るものが在れば 1)。載っているのは**上書き展開では直らないもの**だけである — 記録ファイルの引っ越し、配布物に含まれない設定ファイルへの追記、プロジェクト自身の宣言の作り直し。**手順を当てるのはこの道具ではなく `/kit-migrate`** である(機械に当てられない形の手順が混ざる) | `skills/kit-migrate/SKILL.md`(書式と当て方の正)/ `.claude/migrations/` |
| `check-kit-refs.py` | **キット内の参照は生きているか**(パスの実在・`CLAUDE.md §n` / `原則n` の範囲・`<file>.md §n` の見出し実在・**`reading.md` が名前で指した見出しの実在**・**検査ID(`CS`/`SH`/`BRC`/`LA`+数字)の実在**・**`baseline.md` の `| BR-nn |` 行が §2 の中だけに在ること**)。
対象は `.md` だけでなく `.py` と `scripts/*.md` も含む。**規範を改番・再構築した後に必ず回す** — 実測で、再構築後にエラーメッセージの案内先が4系統死んでいた(`make check` にも入っている) | CS11 の思想をキット自身へ(このスクリプトの docstring) |
| `check-language.py` | **記述言語と用語の表記は規約どおりか**(LA 検査 — ファイル区分ごとの言語・引用島の除外・規範用語集の禁止表記・規範用語集自身の壊れ・**単独で書いてはならない語**(LA5)。一覧は `--list`、残りは `--todo`)。**列挙を持たない** — ファイル区分は `directions/conventions.md` §3 の表を、禁止表記と単独で書かない語は `directions/glossary.md` の表を読む。移行の途中は `scripts/language-config.json` の `migrated` に載ったファイルだけを見る(`make check` にも入っている) | `directions/conventions.md` §3 / `directions/glossary.md` |
| `notify-slack.py` | **人間を呼ぶ**(艦隊運用専用。**AI が叩ける引数は `question` / `done` の2語だけ** — CLI 自体は `--notice <文>` も受けるが、それは colabtmux 監視専用の口で AI は使わない)。文面は `<時刻> [<プロジェクト>] <文>` で、名前は `colabtmux.conf` の `[project] name`(無ければディレクトリ名)。**叩けるのは3者だけ** — `question <ウィンドウ名>` は問いを持つ作業エージェント本人と `@triage`、そして**予算の計器が発火して配車を止めたときの中央エージェント**(その1場面だけ。`orchestration.md` §3.0 の6)、`done` は中央エージェント。送信は fail-open(失敗してもミッションは止めない)だが、**終了コード0は「送った」の意**なので、**送っていない3経路(未設定・送信失敗・Slack が `ok:false`)はどれも `3`**(結果は常に標準出力に1行。この `3` は下の約束の外に在る専用値である) | `directions/orchestration.md` §6.1 |

`make check` / `make dist` / `make patch` は**キット本流リポジトリ(キットのルートディレクトリを
含むリポジトリ — この `.claude/` の2階層上)側のターゲット**である。展開先のプロジェクトには Makefile は配られない — 展開先で使うのは
`kit-manifest.py check`・`kit-migrate.py`・`kit-patch.py` の3本だけ。

**終了コードの約束**(CI で使うときはここを見る):

| コード | 意味 |
|---|---|
| 0 | 問題なし(`--warn-only` を付けた場合も 0。**`-h`/`--help` の明示要求も 0** — 使い方エラーではない) |
| 1 | **検出あり**(差分・不整合・拒否) |
| 2 | 使い方・設定・解析のエラー |

`relations-query.py` と `scan-entrypoints.py` は表示専用、`resolve-callgraph-out.py` と
`propose-features.py` は解決・提案専用なので、いずれも 1 を返さない。
`callgraph-check.py` と `check-contracts.py` が 1 を返すのは**重大度「高」があるときだけ**
(「中」「低」だけなら 0。デプロイゲートに使うときはこの約束を前提にする)。

**例外は `notify-slack.py` 1つだけである** — 検査の道具ではなく送信の道具なので、この表の
「検出あり」に載る事象を持たない。**0 は「送った」ときだけ**、送っていない3経路(未設定・
送信失敗・Slack が `ok:false`)はまとめて **`3`**、引数の誤りは表どおり `2`。
1 を返さない。**`3` を表の中(1)に寄せない**のは、判定に使う側が「1 なら止める」で読むから
である — この道具はデプロイゲートではなく、非ゼロで止まるものは1つも無い
(`directions/orchestration.md` §6.1)。

## 3. 典型的な使い方

### 既存コードにこの体系を導入する

```bash
python3 .claude/scripts/setup-tools.py --check    # 何が使えるかを先に把握する
# → /relations all --apply --bootstrap            # コールグラフ生成 → 機能単位へ集約
# → /retrofit                                      # 既存文書を仕分けて 02 → 01 → 00 を作り直す
# → /verify-impl all → /verify-docs all
```

### 実装を変えた後(/verify-impl が回す並び)

```bash
CG_SSOT=$(python3 .claude/scripts/resolve-callgraph-out.py --ssot)
python3 .claude/scripts/build-callgraphs.py --out "$CG_SSOT"     # SSOT へ再生成
python3 .claude/scripts/cluster-features.py --out "$CG_SSOT"
python3 .claude/scripts/callgraph-check.py                       # コード ⇄ 機能間連携仕様書
python3 .claude/scripts/check-relations.py
```

### 構築フローの入口と出口

```bash
python3 .claude/scripts/check-backlog.py; python3 .claude/scripts/check-debt.py     # 入口(計器。読むだけ)
python3 .claude/scripts/check-ssot.py docs                                          # 母集団の凍結
python3 .claude/scripts/check-buildrecord.py <slug>                                  # 出口
```

### デプロイしてよいか

```bash
python3 .claude/scripts/stamps.py check    # 及第ラインのデプロイゲート。red なら verify 系を回して green を作る
```

red の各行は**回すべき最小の範囲**と、それを記録する `record --covers …` を出す。**全部回す
必要は無い** — 動いた依存だけを回して覆えばデプロイゲートは閉じる。何が依存かは `stamps.py deps`。

`callgraph-check.py` の **CG4 が「取りこぼし」**(コードにある連携が機能間連携仕様書に無い)、
**CG3 が「過剰主張」**(機能間連携仕様書にある連携がコードに無い)である。
**どちらが正かはツールが決めない。** パス・シグネチャ・呼び出しの有無といった**事実の差異は
コードを正として仕様ドキュメントを直し、直したことを報告する**(問わない)。
**意図の差異**(02 の期待と実装が違い、どちらも正でありうる)だけを決定シートに載せる。
振り分けの正は `.claude/directions/03-impl.md`(CLAUDE.md 原則2)。

### 変更の波及を知りたい

```bash
python3 .claude/scripts/relations-query.py --impact src/api/auth.py
python3 .claude/scripts/relations-query.py --requirement FR-auth-01
python3 .claude/scripts/relations-query.py --upstream MODULE-db-session-create --depth 4
python3 .claude/scripts/relations-query.py --health
python3 .claude/scripts/doc-health.py --health
```

**コードを探し回る前にこれを打つ。** それがコンテキストを食い潰さないための道具立てである。

### 現状を眺めたい

上記の読み取り専用スクリプト(`--check` 系・`--health`・`build-index.py --check`)をまとめて
走らせれば全体の状態が1画面で分かる。

## 3.1 実行の許可(いちいち聞かれないようにする)

キットは **`.claude/settings.json`(プロジェクト共有)に自分のスクリプトの許可リストを同梱している**。
`/relations` も verify 系フローも1回の実行で何本もスクリプトを走らせるので、
ここが無いと利用者は同じ確認に何度も答えることになる。

- **キットは実行の許可の既定モード(`defaultMode`)を配らない** ★(2026-08-24 に `bypassPermissions` を
  外した — 理由は `install-notes.txt`。プロジェクトの設定はリポジトリに書き込める人が変えられる)。
  **だから許可リストが実際に効く経路である。** ただし**それを打つ人が起動旗か個人設定で
  bypass を選んでいる環境では、許可リストは判定に関与しない** — codex 等の失敗を許可の問題と
  診断してよいのは、bypass が効いていない環境に限る(`/verify-docs` §2)。
- **`python3` の許可は `.claude/scripts/` のキット自身のツールを名指ししたものだけ**である
  (`python3` 全般を許可しているのではない)。**リストにはそれ以外も並ぶ** — `make`、中身を出さない
  git のサブコマンド、`ls` / `cat` / `rg` など、キットの手順が直に打つものである。
- **スクリプトを追加したら許可リストにも足すこと。** 忘れると黙って「毎回聞かれる」に戻る。
  配布時の `make check` がこの漏れを検出する(`PROMPTED` に挙げたものだけが例外)。
- **`scripts/test-*.py` は許可リストの対象外。** キット自身の自己テスト fixture であり、
  プロジェクト作業中に呼ばれるものではない(呼ぶのはキット本流の `make check`)。
  代わりに `make check` が**全部実行して通ることを見る** — 1本でも落ちれば止まる。
- `.claude/settings.local.json` は**配布物に含めない**が、**git では共有する** —
  そこに書くのは「このプロジェクトで全員に効かせたい追加の許可」であり、
  人によって在ったり無かったりすると、同じコードに対して道具が動いたり止まったりする。
  **個人・環境ごとの設定(自分だけの MCP サーバ、自分の資格情報)は
  `~/.claude/settings.json`(利用者ごとの設定)へ書く。**

## 4. CI での使い方

`--check` 系は**何も書き換えない**ので CI に置ける。推奨する並び:

```bash
python3 .claude/scripts/setup-tools.py                    # 依存を用意(lock があれば固定)
python3 .claude/scripts/stamps.py check                   # ★ デプロイゲート。CI が赤いとはこれである

# ここから下は**情報表示**である。終了コードでビルドを止めない(`|| true` を添えるか、
# CI 側で「失敗しても続ける」に設定する)— 所見の持ち主は verify 系フローであって CI ではない:
python3 .claude/scripts/build-callgraphs.py --selftest      # 決定性の不変則(道具自身の検査)
CG_SSOT=$(python3 .claude/scripts/resolve-callgraph-out.py --ssot)
python3 .claude/scripts/build-callgraphs.py --out "$CG_SSOT" --check   # コールグラフが実装と同期しているか
python3 .claude/scripts/callgraph-check.py                 # コード ⇄ 機能間連携仕様書
python3 .claude/scripts/check-contracts.py                 # 契約(OpenAPI)⇄ 設計 ⇄ コード
python3 .claude/scripts/check-relations.py                 # 機能間連携仕様書集合の内部整合
python3 .claude/scripts/build-index.py --check             # index が実ファイルと一致しているか
python3 .claude/scripts/doc-health.py --check               # 再検証候補・鮮度確認の候補・履歴逆引き索引が最新か
```

- **`--check` なしの `build-callgraphs.py` / `build-index.py` を CI で走らせない**
  (成果物を書き換えて「常に通る」状態になる)。
- **CI で拒む門は1つだけである** ★ — デプロイゲート(`stamps.py check`)。このキットの根幹は
  **「拒む場所は1つ」**であり(`directions/flows.md` §4)、CI に2つ目の拒否機構を置けば、
  その根幹を横から破ることになる。
- **上の情報表示の行は、構築の直後から次の再生成までのあいだ正当に赤い。**
  F1 は callgraphs を再生成しない(再生成するのは `/verify-impl` と `/relations` である —
  `principles.md` §1。**だから区間が閉じるのは、そのどちらかが先に走ったときである** —
  `directions/callgraphs.md` §6.1)ので、その区間で鮮度検査が
  「古い」と言い、退役・改名した入口の行が `callgraph-check.py` の FT1 として終了コード1 になるのは
  **仕様である**(`directions/callgraphs.md` §6.1)。及第ラインは検証を溜めることを積極的に
  許しているので、この区間は日単位で続きうる — **その終了コードでビルドを止めれば、常に赤い CI が
  できあがり、やがて本物の「高」も一緒に無視される**(inspection-21 V-10)。
- 導入初期は `--warn-only` を付けて件数だけ見え、慣れてから外すのが安全。
- **CI が緑でも Tier が落ちていることがある** — レポートの Tier と `degraded_reason` を見ること。
  精度が環境で変わらないよう、対象プロジェクトのビルドを要する抽出器は持たない(callgraph-design.md §6.1)。

## 5. 設定ファイル

| ファイル | 何を決めるか | 上書き |
|---|---|---|
| `scripts/callgraph-config.json` | `internal_roots` / `excludes` / **`vendor_markers`** / **`test_markers` / `tooling_markers`**(+ `include_tests` / `include_tooling`) / 言語の有効化 / `features`(提案の閾値) / `resources`(資源スキャン。`env_patterns` ほか) / `output_dir`・`source_roots`・`max_file_bytes` | `callgraph-config.local.json`(配列キーは和集合でマージ — `internal_roots` は local では**絞れない**。本節末尾の注記) |
| `scripts/entrypoint-patterns.json` | Tier3 のエントリポイント検出パターン | `entrypoint-patterns.local.json` |
| `scripts/flow-config.json` | **フロー層の設定**(`max_building_hours` = building の滞留を分ける時間 / `f4_scopes` = デプロイゲートが要求する F4 の試験区分一覧 / **`code_roots`**(製品コードとテストコードの置き場。鮮度スタンプの失効判定の許可リスト)/ `ui_roots`(qa 試験区分だけに効く UI の置き場)/ `scope_roots`(試験区分ごとのコードの置き場。宣言した試験区分は変更影響の判定をその範囲に絞る)/ **`code_excludes`**(コードの置き場の中に在るが検証の入力ではないパス。動いても失効させない。**既定は空**、狭く誤ると穴になるので迷ったら書かない。どの置き場より**真に狭い**項目だけを受け付ける — 外のパスも、置き場の親も、置き場と等しいものも落とす(置き場そのものを外したいなら `code_roots` から消す)。宣言は焼き込むので変えたら失効する。**欄を持たない古い記録も比べる**ので、後から足しても取りこぼさない)/ `e2e_scripts_in`(E2E 台本の置き場。`system` か `testing`))。**着手を拒むための値は無い** | `flow-config.local.json` |
| `scripts/critical-config.json` | **critical フラグの機械判定**(クロージャのパスに部分一致するパターン。check-buildrecord.py BRC2) | `critical-config.local.json`(和集合でマージ) |
| `scripts/requirements.txt` | venv に入れる依存の名前 | — |
| `scripts/callgraph-schema.json` | 抽出器と下流の**契約**(中間表現) | — |

**`tooling_markers` は開発環境を作るもの**(Makefile・CI 定義・compose・devcontainer)**を解析対象から外す**。
本番実行系から到達しないものは機能ではないという規範(`directions/features.md` §0.1)の機械側で、
照合はリポジトリ相対パスに対して行い、**規則は目印の形で決まる**
(前後が `/` ならディレクトリ、区切りを含めば部分文字列、裸なら basename の接頭辞。
表は `directions/callgraphs.md` §5.9.1)。外した件数は
`callgraphs/index.md` の「解析対象から外したもの」に出る(`directions/callgraphs.md` §5.9.1)。

設定を壊した場合(JSON でない・型違い)は既定値で走るか終了コード 2 で止まる —
黙って無制限にはならない(各スクリプトの docstring が正)。

**ベンダリングされた第三者ライブラリは、全言語共通で自動的に解析対象から外れる**
(`*.dist-info` などのメタデータで検出。名前に依存しない)。外したディレクトリは
`callgraphs/index.md` に必ず記録される — **黙って外すことはしない**。

**`internal_roots` の既定は `.`(リポジトリ全体)。local の配列キーは和集合でマージされるため、
`internal_roots` は `*.local.json` では絞れない**(何を書いても `.` が残り、エラーも警告も出ない)。
モノレポの当面の絞り込みは **local の `excludes` に兄弟パッケージ等を列挙する**
(和集合でも「足せば狭まる」方向 — §6 の既存案内と同型)。恒久策はスクリプト修正であり、
汎用的な直しなので `/kit-improve` でいつでも直してよい(CLAUDE.md §3)。
プロジェクト固有の値は `*.local.json` に書く(**配布物には入らないが、git では共有する** —
`.claude/.gitignore` §先頭のコメント)。

## 6. 困ったとき

| 症状 | 原因と対処 |
|---|---|
| `venv: 作成に失敗した` | Debian/Ubuntu で `python3-venv` が無い。**ホスト側の作業**(キットは apt を叩かない) |
| シンボル数が異常に多い / `ambiguous` だらけ | **第三者ライブラリが混ざっている**。`callgraphs/index.md` の「解析対象から外したもの」と「シンボルが集中しているディレクトリ」を見る。独自名でベンダリングしていて自動検出に掛からない場合は `callgraph-config.local.json` の `excludes` に足す |
| 自前コードが勝手に除外された | そのディレクトリに `*.dist-info` などの目印が紛れている。`vendor_markers` を `local.json` で上書きするか、目印を消す。除外は index.md に必ず出るので黙って消えることはない |
| エントリポイントが 0 件 | パターンが未対応かもしれない。**「無い」と結論しない**。`entrypoint-patterns.local.json` に追加する |
| `ambiguous` が大量に出る | まず `excludes` / `vendor_markers` の漏れを疑う(実測ではそれが原因だった)。候補は全部出ており、機能表クラスタリングが候補辺として算入するので境界は落ちない |
| `CG3` が「低: 断定できない」 | 経路上に未解決の呼び出しがある。**ツールが見えていないだけ**なので、コードを読んで判断し根拠を本文に書く |
| `--check` が毎回「古い」 | callgraphs を手で編集していないか。**手書きは禁止**(次の再生成で消える) |
| Tier が意図せず 3 に落ちた | `setup-tools.py --check` で不足を見る。降格理由は `callgraphs/index.md` の `降格理由` 列にも出る |
| 抽出器が無い言語がある | Python / Go / TypeScript(Vue含む) / infra(CFN・SAM・OpenAPI・Terraform)は実装済み。それ以外の言語は `scan-entrypoints.py` + `relations-coverage.py` で暫定的に見る。**覆えていないことを報告に明記する** |
| CI だけ落ちる | venv が作れず Tier3 に降格している可能性。ログの Tier と `degraded_reason` を見る |
| デプロイゲートが `未宣言` と言う / verify を何本回しても red のまま | `flow-config.json` の `code_roots` が空(= 未宣言)である。**verify では動かせない red** で、`promote` も全件保留になる。`flow-config.local.json` に製品コードとテストコードの置き場を書く — **最初の**宣言は lint/テストのコマンドを 02 に書くのと同じ1回であり、**以後は `/build` が毎回、触ったコードのパスが宣言の下に在るかを見直して足す**(`directions/flows.md` §2) |

## 7. ツールを増やすとき

- **中間表現(`callgraph-schema.json`)が契約。** 抽出器を足すのは `cgx/` に1ファイル追加して
  `cgx/__init__.py` の `EXTRACTORS` に1行足すだけ。出力器と検査器は触らない。
- **下流は Markdown を読まない。** 必ず `--format json` の中間表現を読む(表の書式変更で壊れないため)。
- **決定性を壊さない。** 行番号・タイムスタンプ・絶対パスを出さない。全配列を出力前に整列する。
  `build-callgraphs.py --selftest` がこれを検査する。
- 設計と残りの段は `.claude/scripts/callgraph-design.md`。
