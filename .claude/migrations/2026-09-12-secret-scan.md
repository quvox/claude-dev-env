---
id: 2026-09-12-secret-scan
since: 2026-09-12
kind: judgment
detect: test -f tests/gates.yml && python3 -c "import re,sys,os;p='tests/adapters.yml';t=(open(p,encoding='utf-8').read() if os.path.isfile(p) else '')+chr(10);m=re.search(r'\n([ \t]*)checks:[ \t]*\n(.*?)(?=\n\1\S|\Z)',chr(10)+t,re.S);v=re.search(r'\n[ \t]+secret_scan:[ \t]*(.*?)[ \t]*\n',chr(10)+m.group(2)+chr(10)) if m else None;c=(v.group(1) if v else '').strip();q=(c[:1] in (chr(34),chr(39)));c=(c[1:].split(c[0])[0] if q else re.split(r'\s#',c)[0].split('#')[0]).strip();sys.exit(1 if c and c not in ('false','null','~') and not re.match(r'\A[<\[].*[>\]]\Z',c) else 0)"
paths: tests/adapters.yml
summary: adapters.yml の checks: に、資格情報の混入を見る静的チェックのコマンドを書く
---

## 何が変わったか

構築の各テスト実行ゲートが `secret_scan` という静的チェックのステップを呼ぶようになった。
**呼ぶ側(`tests/gates.yml`)を足すのは `2026-09-12-critical-gates` であり、
こちらは実際に打つコマンドを書く移行である** ★ — **2つを分けてあるのは、
呼ぶ側だけ足して止まった導入が「済んだ」と判定されていたからである**(inspection-27 C-10)。

**コマンドを書かないあいだは skipped のまま通る** — 構築の組は `strict` を持たないので
止まらないが、**その間、資格情報の混入は1度も検査されていない。**

## 手順

1. `tests/adapters.yml` の **`checks:`** に `secret_scan` のコマンドを書く。
   **`adapters:` の側には書かない** — 言語に紐づかない検査なので、多言語リポジトリでは
   言語の数だけ走ることになる。

   ```yaml
   checks:
     secret_scan: <このプロジェクトが選んだコマンド>
   ```

   **道具の選定はこのプロジェクトの判断である**(例: `gitleaks` / `trufflehog` / `git-secrets`)。
   **選んだ文字列は `docs/02-design/environments.md` の表にも同じものを書く** —
   その行を足すのは `2026-09-12-test-command-table` の移行である。

## 移らなかったときに何が起きるか

- 構築のどのテスト実行ゲートでも `secret_scan` が skipped になり、**鍵・トークンの混入が
  1度も検査されないまま緑になる。** 止まらないので、気づく手掛かりが無い。

**テスト基盤(`tests/`)を入れていないプロジェクトには、この移行は掛からない**
(`detect` が `tests/gates.yml` の実在を先に見る)。
