# 機能間連携仕様書(03-impl/relations/)— 中核の仕組み

日本語で書く。

## なぜ在るか

仕様ドキュメントと実装の作業が収束しない理由は2つある: **不整合が機能と機能の継ぎ目に生き残ること**と、
**検証のたびにコードを探索し直し、文脈を燃やして精度が落ちること**である。
機能間連携仕様書は両方を取り除く — **コールグラフを grep できる索引に変える**ので、
呼び出し元・呼び出し先の問いが、コードの走査ではなくシェル1行で済む。

この仕組みが無価値にならないための、譲れない性質が2つある:

1. **実装と 1:1 である。** 実在する機能単位1つにつき文書1本。それ以上でも以下でもない。
   コードから導かれるので、**モジュール分割さえ決まれば、文書化されていないコードベースを
   完全に文書化できる。**
2. **AI がコールグラフを起点として機能単位へ畳み込む**(`/relations`)。道具が作るのは
   `03-impl/callgraphs/`(関数と呼び出し関係だけ)であり、**それは仕様ではない**。
   AI の仕事は**コードを読んで**、目的・処理の流れ・連携の詳細・異常系を書くことであり、
   **契機とモジュール境界を念頭に置いて機能単位へまとめる**ことである。
   **コールグラフのすべての関数をそのまま仕様にしてはならない。** 書式と限界は
   `.claude/directions/callgraphs.md` に在る。
   グリーンフィールドでは順序が逆になる: relations を先に書き、コールグラフは実装後に作って照合する。
   **先に書くことは、全部書くことを意味しない** — 実装が存在する前、これらの文書は実装者への
   作業指示であり、その範囲は §4.1 である(理由と、層の残りについての同じ規則は `03-impl.md`)。
   設計が想定する連携は `02-design/relations.md` に在り、**その差もまた検出の仕組みである**(§7)。

## 1. 何が文書1本になるか(単位)

**単位は `docs/03-impl/features.md`(機能表)が定義する。** 機能表の1行 = この文書1本であり、
**ID は同一**である(`relations/<機能ID>.md`)。規範は `.claude/directions/features.md`。
ここに書いてあるのは機能表の切り方の要約であり、**正は features.md 側に在る。**

単位は**実効的な機能の実装**であって、名目上の関数ではない:

- 利用者の操作やイベント(内部・サーバ側・定時)で起動される機能。
  **その内部の下位関数は同じ文書に畳み込む** — private なヘルパに専用のファイルを与えない。
- 上のものから呼ばれる、**別のモジュール**の機能。**モジュール境界を越えると新しい文書が始まる。**
- バックエンドの入口が内部で分岐するとき(`lambda_handler` / `app.py` が `cmd` の値で分岐する等)、
  **分岐ごとに1文書である** — **ディスパッチャ本体にも1文書**を与え、その callees が分岐になる。
- フロントエンド ⇄ バックエンドは常にモジュール境界である: フロント側の呼び出し元と
  バックエンドのハンドラは、`callees` / `callers` で結ばれた2つの文書になる。

**本番実行系から到達しないものはそもそも機能ではないので、文書を持たない**
(その試験と除外の一覧は `.claude/directions/features.md` §0.1 が所有する — ここには書き写さない)。
§0.1 が除外するものは `03-impl/tests/`、または `02-design/environments.md` +
`03-impl/environments/` に書く。
生成コードと純粋なデータクラスも文書を持たない。
**分割定義に在って入口を1つも持たないモジュールは、空の文書ではなく所見である。**

## 2. 置き場と命名

```
docs/03-impl/relations/
├── index.md                  # generated — never hand-written
├── MODULE-auth-login.md
├── MODULE-auth-session-create.md
└── MODULE-front-login-form.md
```

ファイル名 = `MODULE-<feature-slug>.md` であり、その語幹が**そのまま** ID である
(`id: MODULE-auth-login`)。**採番はしない**: 振り直しは得るものより高くつき、
スラグは grep の結果の中でそれ自体が説明になる。
`<feature-slug>` = ケバブケースの `<module-slug>-<feature>` なので、ファイルはモジュール順に並ぶ。

## 3. Frontmatter(grep のため、すべての欄を1行に書く)

```yaml
---
id: MODULE-auth-login
module: MOD-auth
kind: rest-api
sync: sync
impl: src/api/auth.py::login_handler, src/legacy/auth2.py::login
callers: USER-enduser, MODULE-front-login-form
callees: MODULE-auth-session-create, MODULE-audit-log-write, EXTERNAL-idp
contracts: CTR-api-login, CTR-schema-session
design: DSN-auth-01, DSN-auth-03
requirements: FR-auth-01, FR-auth-02, NFR-sec-02
tests: tests/api/test_auth.py::test_login_ok, tests/api/test_auth.py::test_login_locked
updated: 2026-08-01
summary: 資格情報を検証し、セッショントークンを発行して返す
---
```

| 欄 | 規則 |
|---|---|
| `id` | = ファイルの語幹。必須。 |
| `module` | これが属する 02 のモジュール(`MOD-<slug>`。02 のモジュール分割定義に実在すること)。 |
| `kind` | `user-action` / `event` / `function-call` / `rest-api` / `tool` / `other` の**1つ**。`other` は本文に理由が要る(指針 — 理由の有無を見るスクリプトは無い)。**注意**: 契約は同じ名前の `kind:` を**別の5値の語彙**で使う(正は `.claude/directions/02-design.md`「contracts/」)— `rest-api` / `event` / `other` は綴りが重なるだけである。文書の種類で読み分ける。 |
| `sync` | `sync` か `async`。 |
| `impl` | `path::symbol` の一覧 — **区切りは `::`**。これは `callgraphs/` のシンボル ID と**同一に**書く。その同一性こそが、突き合わせを1回の集合演算に落としているものである(`.claude/directions/callgraphs.md` §5.1)。**同じ機能が複製されているなら全部並べる**(重複していること自体が情報である)。パスはリポジトリ相対で、実在すること。 |
| `callers` | これを起動するものの ID。外部は `USER-<actor>` / `EVENT-<name>` / `SCHEDULER-<name>` / `EXTERNAL-<system>`。`EXTERNAL-<system>` の値は `01-requirements/system.md` の外部依存表の ID 列と一致させる(§5 — 同一 ID であって、対応づけではない)。`なし` が正当なのは `kind: user-action` / `event` / `rest-api` / `tool` のときだけである(**`なし` と書く。欄を空にしない** — `check-relations.py` は必須欄の空を拒む)。呼び出し元の無い `function-call` は死にコードである — 報告すること。機械が覆うのは `function-call` の場合だけで、4種の正当性の一覧は指針であり、読み手が守る。 |
| `callees` | **モジュール境界を越えて**これが呼ぶものの ID と、`EXTERNAL-<system>`。同じモジュールの private なヘルパは並べない(畳み込まれている)。 |
| `contracts` | この機能が読み書きする契約の ID(`03-impl/contracts/` の `CTR-*`)。無ければ `なし`。 |
| `design` | 上流 02 の ID(`DSN-*`)。複数可。`なし` は本文に理由を述べたときだけ。 |
| `requirements` | 上流 01 の ID(`FR-*` / `NFR-*` / `UC-*`)。複数可。 |
| `tests` | この機能を覆うテストの識別子。無いときは `なし(未実装)` — 決して空にせず、決して省かない。 |
| `updated` | `YYYY-MM-DD`。この文書を最後にコードへ同期した日。必須である: 版を持たない層では、**この鏡がいつ撮られたか**を知る唯一の手がかりである。 |
| `summary` | 1行80字以内で、何をするか。`index.md` で読み手が見るのはこれである。 |

**値を複数行に折り返さず、ここで YAML のブロックリストを使わない** — 参照の手段は `grep` であり、
それは行単位である。ゆえに逆引きはコマンド1本になる:

```bash
grep -l 'callees:.*MODULE-auth-session-create' docs/03-impl/relations/   # who calls it
grep -l 'impl:.*src/api/auth.py'               docs/03-impl/relations/   # which doc owns a file
grep -l 'requirements:.*FR-auth-01'            docs/03-impl/relations/   # requirement → code
```

## 4. 本文 — frontmatter は必須、散文は選択的

`.claude/templates/03-relation.md` を使う。**この層の機械的な価値は frontmatter に宿っており**
(中核の 02⇄03 検査も、どの道具も、それしか読まない — 実測)、
**コードを言い換えた散文は、コードが動いた瞬間に古くなる。** だから:

- **必須の内容**: frontmatter(§3)。**実装上の判断**(開示行、または「判断なし: <理由>」— CS19)。
  そして 戻り値・副作用 の中の、**書き込む資源の名前**(テーブル / バケット / キュー —
  CG7 の材料である。**呼び出し辺を持たない結合は、他のどこにも見えない**)。
  2つ以上の機能が共有する資源の形式をここに複製することは決してない:
  `callgraphs.md` §5.11 に従い、その `CTR-*` を `contracts:` に並べる。
- **それ以外は、保守する人が機構から再構成してはならない意味を担うときに書く**:
  外から観測できるエラーと境界の振る舞い、境界を越える影響、状態遷移と不変条件、
  自明でない流れ、なぜその分岐が在るか、外部からの制約、既知の罠。
  **残る中身が純粋に導ける機構だけである節に限り、「(コードを参照)」を1行書く** —
  **見出しそのものを決して消さず**(原則9)、**埋めるためにコードを言い換えない。**
  連携先と連携内容 の下の callee ごとの `###` の小節は残す(検査器がそれを数える)。
  ただし callee 1つにつき1行 — 何のために呼ぶか と 失敗したときどうなるか — で完結した小節である。

固定の見出し:

- **目的** — この機能がなぜ存在するか(1段落)。`requirements` へ辿れること。
- **処理の流れ** — 実際に何をするかを、順に、判断と副作用の水準で。番号付きの段。
  内部の分岐を含める。**シグネチャより長いコード片は書かない。**
- **呼び出され方** — 契機、事前条件、型つきの引数、誰が認可されるか。
- **連携先と連携内容** — `callees` の項目1つにつき小節1つ: 何のために呼ぶか / 何を渡すか /
  何を受け取るか / **失敗したときどうなるか**。**この節がこの文書の要点そのもの**であり、
  frontmatter に並んでいるのにここに無い callee は、未完成の文書である。
- **戻り値・副作用** — 戻り値の形、永続化される状態、発行されるイベント、ログ。
  **書き込む資源(テーブル・バケット・キュー・トピック)を明示的に名指す。**
  呼び出し辺を持たない連携はここにしか現れず、言い回しを変えると**誰も機械的に気づかない**
  (検査 CG7 / `callgraphs.md` §5.11)。読む側は「連携先と連携内容」でその資源を名指し、
  共有の `CTR-*` を指す。**その形式を所有するのは契約であって、この散文ではない。**
- **異常系** — すべての異常経路を、実際に外から観測される振る舞いつきで
  (ステータスコード、文言、再試行、巻き戻し)。「適切にエラーを返す」は禁止である。
- **実装上の判断** — 実装時に下した判断を、**1件1行、`.claude/directions/delegation.md` §3 が
  所有する開示の形で**: 委任の ID(`DS-*` / `D0-*` / `D1-*`)、決めたこと、**理由**、**見直す条件**。
  最後の2つのどちらかを欠く行は `/verify-docs` の C 検査が落とす。
  **02 の設計判断を黙って覆してはならない。**
  **この見出しこそが「なぜこの実装なのか」の答えが在る場所である** —
  空にすると、次の読み手はコードへ行って推測することになるので、**`CS19` がそれを落とす**:
  判断を書くか、「判断なし: <理由>」と書く。
  **このモジュールに触れるすべてのタスクが、これらの行を読み直し、1行ずつ 継続 / 更新 / 削除 の
  印を付ける**(`delegation.md` §3.1)— それが、実装が動いた後も答えを真に保っているものである。
- **既知の制限** — 既知の限界と、`docs/issues/` の項目が在るならそこへの指し。

### 4.1 実装が存在する前に埋める見出し

実装が存在する前(`/build` §2、グリーンフィールド)には鏡に映すコードが無いので、
**実装者が要る見出しだけを埋め、残りは `/build` §4 が作られた結果から補完するために残す。**
なぜこれが近道ではなく正しい範囲なのか:
`.claude/directions/03-impl.md` の「★ 実装がまだ無いとき」の節。

| 節 | 実装前の扱い |
|---|---|
| 目的 | 1行。`requirements` の ID を引くだけでよい |
| **処理の流れ** | **書く。実装者がこれから作るものの記述そのもの**。上流に無い判断がステップに混じるなら、それは未決点か委任 |
| 呼び出され方 | 契機と認可だけ。引数の型と制約は契約(`CTR-*`)を指す |
| **連携先と連携内容** | **書く**。02 の `PLAN-*` から導き、`失敗したときどうなるか` まで書く |
| 戻り値・副作用 | **書き込む資源の名前だけ**(検査 CG7 の材料になるので省略しない)。戻り値・共有資源の形式は契約を指す(`callgraphs.md` §5.11) |
| 異常系 | **書かない**。実装前の正は 01 の受け入れ基準(EARS)と契約のエラー応答であり、ここに写すと二重管理になる |
| **実装上の判断** | **書く**。文書生成段階で行使した委任を、開示の1行形式で(`delegation.md` §3。実装者に再決定させないため) |
| 既知の制限 | 書かない(実装前に分かるはずがない) |

ここで見出しが埋まっていないのは、指摘すべき空白ではない —
**その見出しの持ち主は実装であり、`/build` §4 が作られた結果から埋める。**
**見出しそのものは決して消さない**(原則9)。

**テストについて書くのは `tests:` の欄(参照)だけである。** テストの内容・手順・フィクスチャ・
期待値を本文に置いてはならない — **`03-impl/tests/<module-slug>.md` が正**であり、
両方に書けば必ずずれる(`03-impl.md` の tests の節)。
テストコードのシンボルを `impl:` や `callees:` に入れることも決してない
(コールグラフに無いので、突き合わせが黙って外れる)。

## 5. プロジェクト全体の ID 規約

| 層 | 種別 | ID の形 | どこで定義されるか |
|---|---|---|---|
| 00 | 要求 | `RQ-<category>-nn` | `00-requests/*.md` |
| 00 | 受け入れシナリオ | `AC-nn` | `00-requests/acceptances.md` |
| 00 | 決定事項 | `D0-<category>-nn` | `00-requests/decisions/*.md` |
| 01 | 機能要件 | `FR-<domain>-nn` | `01-requirements/functional*.md`(業務ドメインごとに分割したら `functional-<domain>.md`。分割の引き金も正も `01-requirements.md`) |
| 01 | 非機能要件 | `NFR-<category>-nn` | `01-requirements/non-functional.md` |
| 01 | ユースケース | `UC-nn` | `01-requirements/usecases.md` |
| 01 | システム要件 | `SR-nn` | `01-requirements/system.md` |
| 01 | 決定事項 | `D1-<type>-nn` | `01-requirements/decisions/*.md` |
| 02 | 設計判断・設計項目 | `DSN-<area>-nn` | `02-design/*.md` |
| 02 | モジュール | `MOD-<slug>` | `02-design/system.md` の モジュール分割定義 |
| ux | 画面 | `SCR-nn` | `docs/ux/flows.md` の画面一覧(`SCR-nn` の台帳。規範は `ux.md` — UX 文書は検証連鎖の外に居る) |
| 02 | 想定機能連携 | `PLAN-<feature-slug>` | `02-design/relations.md` |
| 02/03 | 契約 | `CTR-<name>` | `02-design/contracts/` と `03-impl/contracts/` で**同一ID** |
| 03 | 機能間連携仕様書 | `MODULE-<feature-slug>` | `03-impl/relations/` |
| 03 | E2Eシナリオ | `E2E-nn` | **02 のテスト戦略**で定義(既定は `02-design/system.md`。分割したらその移設先 — `02-design.md`)、`03-impl/tests/e2e.md` で対応付け |
| 01/02/03 | 外部システム | `EXTERNAL-<system>` | `01-requirements/system.md` の外部依存表(ID 列)。02 の境界表・relations の `callers`/`callees` は**同一ID**で参照する |

**`CTR-*` を 02 と 03 で共有しているのは意図的である**: 両側が同じ ID であることが、
「設計された契約と実装された契約は一致しているか」を grep 1行に落としている。
粒度は違ってよいが、**中身の違いは所見である。**

## 6. 道具立て — 読まずに答える方法

この仕組みの見返りは道具が決める。**手で grep する前に、必ず下の表を引く。**
**「コードを漁って文脈を燃やす」を止めることが、この全体の要点である。**

| スクリプト | 答える問い | 主な用途 |
|---|---|---|
| `build-callgraphs.py` | **コードの関数・呼び出し関係・エンドポイントは何か** | `/relations` の起点。`--check` で鮮度、`--format json` で中間表現 |
| `propose-features.py` | **機能表に足すべき行は何か**(機能候補・共通基盤候補・統合候補) | 境界を決めるための材料。**確定はしない** |
| `cluster-features.py` | **機能間の辺・共有関数・未到達・資源結合は何か** | ★`callees:` の材料。`feature-graph.md` を生成 |
| `callgraph-check.py` | **機能表・コールグラフ・機能間連携仕様書は一致しているか(FT/CG 検査)** | ★取りこぼし(FT2・CG4・CG7)と過剰主張(CG3)の検出 |
| `scan-entrypoints.py` | エントリポイント候補(**抽出器が無い言語向けの最後の手段**) | Tier3 のフォールバック |
| `relations-coverage.py` | **コードと仕様ドキュメントのどちらかにしか無いものは何か** | 03-impl の網羅性。未記載・古い記述・要確認を出す |
| `relations-query.py` | **これを変えると何に響くか / 誰が呼ぶか / 何をテストすべきか** | 波及の導出、決定シート、実装前の確認 |
| `check-relations.py` | **仕様ドキュメント集合として内部矛盾が無いか** | 対称性・参照実在・必須項目 |
| `build-index.py` | 目次と進捗の再生成 | `index.md` は**手書きしない** |
| `check-buildrecord.py` | **構築記録は突き合わせ可能な形か**(構築記録ゲート。fail-closed) | `build-record.md` |

### 6.1 よく使う呼び出し

```bash
# ★ コールグラフを生成(機能単位へ集約する前の材料)
# 生成先は常に SSOT である。自分で決めず解決させる(callgraphs.md §3.1)
CG_OUT=$(python3 .claude/scripts/resolve-callgraph-out.py) || exit 2
python3 .claude/scripts/build-callgraphs.py --out "$CG_OUT"
python3 .claude/scripts/build-callgraphs.py --out "$CG_OUT" --check   # 実装と同期しているか
python3 .claude/scripts/build-callgraphs.py --format json     # 中間表現(下流はこれを読む)

# ★ 機能表に足すべき行(境界の材料)と、機能間の関係
python3 .claude/scripts/propose-features.py
python3 .claude/scripts/cluster-features.py --out "$CG_OUT"
python3 .claude/scripts/cluster-features.py --out "$CG_OUT" --check   # 実装・機能表と同期しているか

# ★ 機能表・コールグラフ・機能間連携仕様書の整合(FT/CG。ID は --list で出る)
python3 .claude/scripts/callgraph-check.py

# 抽出器が無い言語だけ、正規表現でエントリポイント候補を拾う(最後の手段)
python3 .claude/scripts/scan-entrypoints.py src/api

# ★ このファイルを変えると何に響くか(要件・契約・走らせるテストまで出る)
python3 .claude/scripts/relations-query.py --impact src/auth.py

# 呼び出し関係
python3 .claude/scripts/relations-query.py --callers  MODULE-auth-login
python3 .claude/scripts/relations-query.py --upstream MODULE-db-session-create --depth 4
python3 .claude/scripts/relations-query.py --path MODULE-front-login-form MODULE-audit-log-write

# 要件から実装とテストを引く
python3 .claude/scripts/relations-query.py --requirement FR-auth-01

# 構造の健全性(肥大モジュール・循環・到達不能・テストなし・要件なし)
python3 .claude/scripts/relations-query.py --health

# 連携図(Mermaid をそのまま貼れる)
python3 .claude/scripts/relations-query.py --graph --module MOD-auth

# 網羅性と内部整合
python3 .claude/scripts/relations-coverage.py src/api
python3 .claude/scripts/check-relations.py
```

`--format json` を足すと検査器の出力が機械処理できる形になる。**どのスクリプトがそれを取るかは
測るのであって、並べない** — 手で数えた一覧は古くなる(ここに在ったものは「4本」と言っていたが、
答えは10本だった):

```bash
for s in .claude/scripts/*.py; do printf '%-24s %s\n' "$(basename $s)" "$(grep -c -- '--format' $s)"; done
```

`--format json` と `--format=json` は、その旗を取るところではどちらも受け付ける。
**結果を報告で要約するときは、実行したコマンドを逐語で書く**
(読み手がそれを再実行できることが、この道具立ての価値の半分である)。

### 6.2 道具の限界(常に念頭に置くこと)

- **`scan-entrypoints.py` は再現率優先の正規表現である。** 偽陽性は捨ててよいが、
  **捨てた理由を報告に書く。** 逆に、候補ゼロは「入口が無い」を意味しない —
  パターンがこの技術構成を覆っていないだけかもしれない。そのときは
  `.claude/scripts/entrypoint-patterns.local.json` にパターンを足す。
- **`relations-query.py` はコードではなく文書を読む。** 文書が古ければ答えも古い。
  **だから `callgraph-check.py` と対で使う。**
- **`callgraph-check.py` は「経路が無い」の断定を控えることがある。** 経路上に未解決の呼び出し
  (動的ディスパッチ、名前衝突 …)が在ると CG3 を「低」に落とす。**道具に見えていないだけかも
  しれない**からである — **そこは AI がコードを読んで判断する領域である。**
- **`cluster-features.py` は機能表より賢くなれない。** 入口が表から欠けていると、
  その下流がまるごと「到達不能」になる。**未到達が大量に出たら、まず入口の登録漏れを疑う。**
- **確度 `候補` の辺は実在しないかもしれない。** 名前衝突の候補を数えて繋いだものなので、
  AI がコードを読んで採否を決め、**棄却したものを理由つきで報告する。**
- **資源結合(CG7)を `callees` に入れることはできない** — その規則と*本当の*行き先は
  `callgraphs.md` §5.11 に在る(ここには書き写さない)。所見を読むときに知っておく価値のある
  限界: 機械が見られるのは**資源名が本文に現れているかどうかだけ**であり、
  短い資源名(3文字未満)は照合されない。
- **どちらが正かを決める道具は無い。** 道具は事実の食い違いを表に出すだけである。
  **事実の**食い違いはコードを正として直し、修正を報告する。
  自分で裁定できない**意図の**差異だけが人間に届く(CLAUDE.md 原則2。その振り分けの表は
  `.claude/directions/03-impl.md`)。**「判断できなかった」だけでは問う理由にならない**
  (`.claude/directions/delegation.md` §1)。

### 6.3 `check-relations.py` が強制するもの(すべてエラー。警告ではない)

1. `id` がファイルの語幹と一致する。ID の重複が無い。
2. `module` が 02 のモジュール分割定義に実在する。
3. すべての `impl` のパスがディスク上に実在し、区切りが `::` である(`:` 1つではない)。
4. すべての `callers` / `callees` が既知の `MODULE-*` の ID か正しい外部の接頭辞であり、
   **決して自分自身ではない。**
5. **対称性**: `A.callees ∋ B` ⟺ `B.callers ∋ A`。**非対称は、機能間の不整合が隠れる最も典型的な
   形である** — だからこそ読むのではなく機械で見る。
6. すべての `contracts` / `design` / `requirements` の ID が、それを所有する層に実在する。
7. `callers` が空の `kind: function-call` → 死にコードの所見。
8. すべての必須欄が在り、1行で書かれている。`kind` / `sync` が語彙の中に収まっている。
   `tests` が空ではなく `なし(未実装)` である。

**FT3(機能表と `relations/MODULE-*.md` の 1:1)はここには無い** — その検査IDを実装するのは
`callgraph-check.py` 1本だけである(同じ規則を二度実装しない。inspection-21 V-2)。
`/relations` と `/verify-impl` はこのスクリプトを走らせる段で `callgraph-check.py` を併走させるので、
検出の穴は開かない(`/retrofit` §6 手順2 も同じ段で併走させる)。
ただし **relations が1件も無いのに機能表に行が在る**とき、このスクリプトは検査対象が空であること
を合格と呼ばず、終了コード1 で拒む(表ではなく `NG` の行として印字する。
母集団の片側が全部無い状態は導入途中ではない)。

さらに「連携先と連携内容」の下の callee ごとの `###` の見出しを数える:
見出しの無い callee は警告(「見出しになっていない」と「本文に全く現れない」を区別する)、
見出しの重複はエラーである。**判定できないのは各小節の中身**であり、そこは読み手に残る。

relations を変えたら必ず `check-relations.py` と `build-index.py` を走らせる。
`/verify-impl` では、**SSOT を書き換える前に**必ず走らせる。

## 7. 02 ⇄ 03 の突き合わせ(抜けが早く表に出る仕組み)

`02-design/relations.md` は `PLAN-<feature-slug>` の行を持つ: **設計が期待する**つながりを、
この文書と同じ `kind` / `sync` / 呼び出し元 / 呼び出す先 / 契約 の語彙で書いたものである。
2つの集合を突き合わせる:

| 状況 | 意味 | 対処 |
|---|---|---|
| PLAN が在り MODULE が無い | 設計されたが実装されていない | 未実装。実装タスクの範囲か、`docs/issues/` 行きか判断する |
| MODULE が在り PLAN が無い | 設計を経ずに実装された | 設計漏れ、または設計外の実装。02 起点で修正する |
| 両方在るが callees が違う | 連携の取りこぼし | 差異ごとに 02 と 03 のどちらが正かを判定する。**事実の差異はコードを正として直し、意図の差異だけをシートへ**(原則2 の振り分けの正は `.claude/directions/03-impl.md`)。**推測で寄せない** |
| 両方在るが contracts が違う | 契約不一致 | `CTR-*` を突き合わせ、実装が正なら 02 を、設計が正なら実装を直す(タスク化) |

この突き合わせが `/verify-impl` の検査 E であり、
**考慮漏れを実装中ではなく実装*前*に見えるようにしているもの**である。
