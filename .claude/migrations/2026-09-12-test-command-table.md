---
id: 2026-09-12-test-command-table
since: 2026-09-12
kind: judgment
detect: test -f tests/gates.yml && python3 -c "import re,sys,os;p='docs/02-design/environments.md';t=open(p,encoding='utf-8').read() if os.path.isfile(p) else '';t=re.sub(r'<!--.*?-->','',t,flags=re.S);rows=re.findall(r'\n\|[ \t]*(資格情報の混入検査|重要テスト\(除外なし\)|要件とテストの対応の一覧|構築時\(単体\+結合\)|構築時\(単体だけ\)|構築時\(結合だけ\))[ \\t]*\\|([^\\n|]*)\\|',chr(10)+t);bare=lambda c:c.strip().strip(chr(96)+chr(42)+chr(95)+chr(32)).strip();good={u for u,c in rows if bare(c) and bare(c) not in ('-',chr(8212),'未定','TBD') and not re.match(r'\A<.*>\Z',bare(c))};sys.exit(1 if len(good)>=6 else 0)"
paths: docs/02-design/environments.md
summary: 02-design/environments.md の「lint・テストコマンド」の表に、増えた6行を足す
---

## 何が変わったか

`tests/` 側に足したテスト実行ゲートと検査を、**設計文書の表からも打てるようにする。**
**この表の文字列が正であり、スキルはこれを逐語で打つ** — 行が無いと、`/verify-tests` は
「コマンドが無い、または未定であること自体が red」として赤を記録する。

**この移行を、テスト実行ゲートを足す移行と分けてあるのは** ★、
`tests/gates.yml` を編んだところで中断すると、表の行が無いまま「済んだ」と
判定されていたからである(inspection-27 C-10)。

## 手順

1. `docs/02-design/environments.md` の「lint・テストコマンド」の表に6行足す。
   **「用途」欄の文字列は下のとおりにする** — 要否判定がこの字面を見る。
   コマンド欄はこのプロジェクトが実際に打つ文字列である。

   | 用途 | 備考 |
   |---|---|
   | `資格情報の混入検査` | `adapters.yml` の `checks.secret_scan` と同じ文字列 |
   | `重要テスト(除外なし)` | `f4-critical`。`--only <試験区分>` で絞って呼ぶ |
   | `要件とテストの対応の一覧` | `--report traceability`。`/verify-tests` の「表の網羅」が使う |
   | `構築時(単体+結合)` | `f1-fast`。`--grep` / `--files` で触ったモジュールに絞る |
   | `構築時(単体だけ)` | `f1-unit`。結合テストを持たないモジュール |
   | `構築時(結合だけ)` | `f1-integration`。単体テストを持たないモジュール |

   **書き方の正は雛形の該当箇所(`.claude/templates/02-environments.md`)である。**

## 移らなかったときに何が起きるか

- `/verify-tests` が打つべきコマンドを表から引けず、**「コマンドが無い」を理由に red を
  記録する。** 表の6行のうち1つでも欠けていれば、その用途で同じことが起きる。
- 資格情報の混入検査は、`adapters.yml` に書いた文字列と表の文字列がずれたまま放置される。

**テスト基盤(`tests/`)を入れていないプロジェクトには、この移行は掛からない**
(`detect` が `tests/gates.yml` の実在を先に見る)。
**`docs/02-design/environments.md` がまだ無いプロジェクトでは「要る」と出る** —
あの文書を作るのは `/build` であり、作ったときに6行を入れる。
