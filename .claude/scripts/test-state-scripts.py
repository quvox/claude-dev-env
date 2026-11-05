#!/usr/bin/env python3
"""状態層スクリプト(stamps / check-debt / check-buildrecord / check-sheet /
check-mission / check-ux)と check-ssot の自己検査をまとめて走らせる fixture。

各スクリプトの --selftest が壊した事例で検知できることを示す(実体はそれぞれのファイル)。
**どれを走らせるかは下のタプルが正である** — この説明に一覧を書き写さない(必ずずれる)。
make check はこのファイルを実行するので、スクリプトを直して自己検査が追随していなければ
ここで止まる。check-ssot は最小の fixture でスモークする(この fixture が回すのは
CS8 / CS18 / CS24 / CS25 / CS26 である。check-ssot 自身の --selftest は CS21 と CS23 を
持つが、make check はそれを呼んでいない。壊した事例の網羅は各 cs 関数の docstring が持つ)。
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    for name in ("stamps.py", "check-debt.py", "check-buildrecord.py", "check-sheet.py",
                 "check-mission.py", "check-ux.py", "check-contracts.py", "check-baseline-verdicts.py"):
        r = subprocess.run([sys.executable, str(HERE / name), "--selftest"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(f"NG {name} --selftest\n{r.stdout}\n{r.stderr}", file=sys.stderr)
            return 1

    # check-ssot: 曖昧語・下位層IDを仕込んだ SSOT で違反が出ること、綺麗なら 0 で通ること
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / ".claude").mkdir()
        (root / "CLAUDE.md").write_text("# x\n", encoding="utf-8")
        d = root / "docs/01-requirements"
        d.mkdir(parents=True)
        (d / "functional.md").write_text(
            "---\nid: fr\n---\n## 要件\n適切に処理する。MODULE-x を使う。\n", encoding="utf-8")
        r = subprocess.run([sys.executable, str(HERE / "check-ssot.py"), "docs"],
                           cwd=td, capture_output=True, text=True)
        if r.returncode != 1 or "CS8" not in r.stdout or "CS18" not in r.stdout:
            print(f"NG check-ssot が違反を見逃した\n{r.stdout}\n{r.stderr}", file=sys.stderr)
            return 1
        (d / "functional.md").write_text(
            "---\nid: fr\n---\n## 要件\n3回まで再試行する。\n"
            "\n## 今回決めた既定(開示)\n\n- 判断なし: 決めた既定が無い\n", encoding="utf-8")
        r = subprocess.run([sys.executable, str(HERE / "check-ssot.py"), "docs"],
                           cwd=td, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"NG check-ssot が綺麗な SSOT で落ちた\n{r.stdout}\n{r.stderr}",
                  file=sys.stderr)
            return 1
        # CS26: **git を引けない場所では判定しない**(黙って OK も出さない)。
        # この fixture の一時ディレクトリは git リポジトリではないので、ここが
        # 「判定不能」と名乗ることが、git の無い環境で check-ssot が落ちないことの証拠である。
        if "判定不能" not in r.stdout:
            print(f"NG CS26 が git の無い場所で判定不能を名乗らなかった\n{r.stdout}",
                  file=sys.stderr)
            return 1

        # CS24: 要件が `分割可否` を述べていなければ落ちる(未記載は既定ではなく違反)
        (d / "functional.md").write_text(
            "---\nid: fr\n---\n## FR-auth-01 認証\n利用者は自分の名前で入る。\n"
            "\n## 今回決めた既定(開示)\n\n- 判断なし: 決めた既定が無い\n", encoding="utf-8")
        r = subprocess.run([sys.executable, str(HERE / "check-ssot.py"), "docs"],
                           cwd=td, capture_output=True, text=True)
        if r.returncode != 1 or "分割可否 が無い" not in r.stdout:
            print(f"NG CS24 が 分割可否 の未記載を見逃した\n{r.stdout}\n{r.stderr}",
                  file=sys.stderr)
            return 1

        # CS24: **雛形を写しただけの欄は決定ではない。** 差し込み記号を落としてから値を探す
        # のでなければ、選択肢の見本がそのまま「記載済み」と数えられる。
        fr_head = "---\nid: fr\n---\n## FR-auth-01 認証\n"
        fr_tail = "\n## 今回決めた既定(開示)\n\n- 判断なし: 決めた既定が無い\n"
        for why, value, want in (
                ("差し込み記号のままの欄を決定と数えた", "<不可分 | 段階可(理由)>", 1),
                ("選択肢を消し忘れた行を決定と数えた", "不可分 / 段階可(理由: 後追いでよい)", 1),
                ("理由の無い `段階可` を通した", "段階可", 1),
                ("空の理由の `段階可` を通した", "段階可(理由: <>)", 1),
                ("空の文句を理由として通した", "段階可(理由: 特になし)", 1),
                ("理由の在る `段階可` を落とした", "段階可(理由: 参照系から先に出す)", 0),
                # 理由の本文に `不可分` と書けるので、欄の全体を走査すると正しい記入を弾く
                ("理由の中の `不可分` を選択肢の残りと読んだ",
                 "段階可(理由: 検索と編集は不可分ではなく独立して使える)", 0),
                # 理由の中に補足の括弧が在っても、最初の閉じ括弧で切らない
                ("理由の中の入れ子の括弧で切った",
                 "段階可(検索(参照)と編集は不可分ではなく独立して使える)", 0),
                ("全角の括弧を読まなかった", "段階可（理由: 全角の括弧でも読む）", 0),
                # 裁定 A-1: 理由の質を文字数で判定する仕組みは含めない
                ("短い理由を文字数で弾いた", "段階可(理由: 別売り)", 0),
                ("`不可分` に理由を求めた", "不可分", 0)):
            (d / "functional.md").write_text(
                fr_head + f"- **分割可否: {value}**\n" + fr_tail, encoding="utf-8")
            r = subprocess.run([sys.executable, str(HERE / "check-ssot.py"), "docs"],
                               cwd=td, capture_output=True, text=True)
            # **報告の見出しで判定する。** 終了コードは他の検査(この fixture は条項の表を
            # 持たないので CS25)でも 1 になるので、CS24 の当否には使えない。
            hit = 0 if "CS24 分割可否の記載: OK" in r.stdout else 1
            if hit != want:
                print(f"NG CS24 {why}(値: {value})\n{r.stdout}\n{r.stderr}", file=sys.stderr)
                return 1

        # CS25: 正常系だけの受け入れ基準は落ちる。**逃げ道と抜け道を名指しで塞ぐ** —
        # ここに並んでいるのはどれも、独立検査が実際に通してみせた入力である。
        head = ("---\nid: fr\n---\n## FR-auth-01 認証\n- **分割可否: 不可分**\n")
        tbl = ("\n| 条項 ID | 種別 | 基準 |\n|---|---|---|\n"
               "| FR-auth-01-1 | 正常系 | WHEN 押す the system SHALL 開く |\n")
        tail = "\n## 今回決めた既定(開示)\n\n- 判断なし: 決めた既定が無い\n"
        full = ("| FR-auth-01-2 | 境界値 | IF 上限 THEN 拒否 |\n"
                "| FR-auth-01-3 | 異常系 | IF 落ちる THEN 伝える |\n")
        cases = [
            ("正常系だけを見逃した", head + tbl + tail, 1),
            ("そろった表を落とした", head + tbl + full + tail, 0),
            # 種別の欄は**完全一致**で見る。部分一致だと逃げ道より安く回避できる
            ("種別欄の「境界値なし」を条項と数えた",
             head + tbl + "| FR-auth-01-2 | 境界値なし | |\n"
             "| FR-auth-01-3 | 異常系なし | |\n" + tail, 1),
            # 中身の無い条項2行が、この検査を黙らせる最短手になってはならない
            ("中身の無い条項を数えた",
             head + tbl + "| FR-auth-01-2 | 境界値 | <> |\n"
             "| FR-auth-01-3 | 異常系 | |\n" + tail, 1),
            # 受け入れ基準でない表(検討メモ)を条項と数えない
            ("要件の中の別の表を条項と数えた",
             head + "\n| 項目 | 説明 |\n|---|---|\n| 上限 | 境界値は 02 で決める |\n"
             "| 失敗 | 異常系は 03 のもの |\n" + tbl + tail, 1),
            # フェンスの中は見ない(CS11・CS21 と作法を揃える)
            ("フェンスの中の表を条項と数えた",
             head + "\n```\n| FR-x-1 | 境界値 | 例示 |\n| FR-x-2 | 異常系 | 例示 |\n```\n"
             + tbl + tail, 1),
            ("フェンスの中の見出しで要件を打ち切った",
             head + "\n```markdown\n## 例示の見出し\n```\n" + tbl + full + tail, 0),
            # 種別の列は見出し行から特定する(位置を決め打ちしない)
            ("種別が2列目でない完全な表を落とした",
             head + "\n| # | 条項 ID | 種別 | 基準 |\n|---|---|---|---|\n"
             "| 1 | FR-auth-01-1 | 正常系 | WHEN 押す the system SHALL 開く |\n"
             "| 2 | FR-auth-01-2 | 境界値 | IF 上限 THEN 拒否 |\n"
             "| 3 | FR-auth-01-3 | 異常系 | IF 落ちる THEN 伝える |\n" + tail, 0),
            # 逃げ道: 空の文句は長さで弾く(語の列挙は1文字足せば抜ける)
            ("空の文句を理由として通した",
             head + "- 境界値なし(該当なしのため)\n- 異常系なし(特に無し)\n"
             + tbl + tail, 1),
            ("中身のある理由を落とした",
             head + "- 境界値なし(入力は真偽値だけで、上限も空も外から区別できない)\n"
             "- 異常系なし(保存を伴わないので外から見える失敗が無い)\n" + tbl + tail, 0),
            # 短いが正当な理由は通す(長さで substance は測れない)
            ("短いが正当な理由を落とした",
             head + "- 境界値なし(上限が無い)\n- 異常系なし(副作用が無い)\n" + tbl + tail, 0),
            # フェンスは ``` と ~~~ の2種類あり、同じ印でだけ閉じる
            ("~~~ フェンスの中の表を条項と数えた",
             head + "\n~~~markdown\n| FR-x-1 | 境界値 | 例示 |\n| FR-x-2 | 異常系 | 例示 |\n~~~\n"
             + tbl + tail, 1),
            ("閉じないフェンスで黙った",
             "---\nid: fr\n---\n```\n\n## FR-auth-01 認証\n- **分割可否: 不可分**\n"
             + tbl + full + tail, 1),
            # `種別` の欄が在るだけの表(検討メモ)は受け入れ基準の表ではない
            ("種別欄だけの検討メモ表を条項と数えた",
             head + "\n| 観点 | 種別 | 02 での扱い |\n|---|---|---|\n"
             "| 上限 | 境界値 | 02 で決める |\n| 障害 | 異常系 | 03 で決める |\n" + tbl + tail, 1),
            # 逃げ道は表の外でだけ数える(条項の本文が免除の宣言に化けない)
            ("条項の本文の逃げ道で免除した",
             head + "\n| 条項 ID | 種別 | 基準 |\n|---|---|---|\n"
             "| FR-auth-01-1 | 正常系 | WHEN 境界値なし(外から観測できる違いが無いため)でも開く |\n"
             + tail, 1),
            # 中身の無い印を条項と数えない(`TBD` を2本足す最短手を塞ぐ)
            ("TBD を条項と数えた",
             head + tbl + "| FR-auth-01-2 | 境界値 | TBD |\n"
             "| FR-auth-01-3 | 異常系 | 未定 |\n" + tail, 1),
            # 見出しの深さが1段違うと要件が1件も登録されない — **沈黙と不在を区別する**
            ("見出しの深さ違いで黙った",
             head.replace("## FR-auth-01", "### FR-auth-01") + tbl + full + tail, 1),
            ("要件がまだ無い文書で鳴った",
             "---\nid: fr\n---\n# 機能要件\n\nまだ書いていない。\n" + tail, 0),
        ]
        for why, body, want in cases:
            (d / "functional.md").write_text(body, encoding="utf-8")
            r = subprocess.run([sys.executable, str(HERE / "check-ssot.py"), "docs"],
                               cwd=td, capture_output=True, text=True)
            # **CS25 の行だけを見る**(終了コードは全検査の総和なので、他の検査の反応を
            # CS25 のせいにしてしまう)。違反の文面は1種類ではない — 条項の欠落のほかに
            # 「フェンスが閉じていない」も出る。
            hit = "CS25 境界値と異常系の条項: 違反" in r.stdout
            if hit != bool(want):
                print(f"NG CS25 が {why}\n{r.stdout}\n{r.stderr}", file=sys.stderr)
                return 1

    # CS26: 消えた条項 ID。**git を要するのはこの検査だけ**なので、git が無い環境では
    # この場合を飛ばす(上の「判定不能」がその環境の受け持ちである)。
    if shutil.which("git"):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".claude").mkdir()
            (root / "CLAUDE.md").write_text("# x\n", encoding="utf-8")
            d = root / "docs/01-requirements"
            d.mkdir(parents=True)
            head = "---\nid: fr\n---\n## FR-auth-01 認証\n- **分割可否: 不可分**\n"
            rows = ("\n| 条項 ID | 種別 | 基準 |\n|---|---|---|\n"
                    "| FR-auth-01-1 | 正常系 | WHEN 押す the system SHALL 開く |\n"
                    "| FR-auth-01-2 | 境界値 | IF 上限 THEN 拒否 |\n"
                    "| FR-auth-01-3 | 異常系 | IF 落ちる THEN 伝える |\n")
            tail = "\n## 今回決めた既定(開示)\n\n- 判断なし: 決めた既定が無い\n"
            (d / "functional.md").write_text(head + rows + tail, encoding="utf-8")
            for args in (["init", "-q"], ["add", "-A"],
                         ["-c", "user.email=t@t", "-c", "user.name=t",
                          "commit", "-qm", "base"]):
                subprocess.run(["git"] + args, cwd=td, check=True, capture_output=True)
            # 番号を振り直した(2 を消して 3 を 2 にした)= 違反
            (d / "functional.md").write_text(
                head + rows.replace("| FR-auth-01-2 | 境界値 | IF 上限 THEN 拒否 |\n", "")
                .replace("FR-auth-01-3", "FR-auth-01-2") + tail, encoding="utf-8")
            r = subprocess.run([sys.executable, str(HERE / "check-ssot.py"), "docs"],
                               cwd=td, capture_output=True, text=True)
            # **CS26 の行だけを見る**(終了コードは全検査の総和である)
            if "CS26 条項 ID の消失: 違反" not in r.stdout or "FR-auth-01-3" not in r.stdout:
                print(f"NG CS26 が消えた条項 ID を見逃した\n{r.stdout}", file=sys.stderr)
                return 1
            # 退役(`種別` に `delete` と書いて行を残す)は違反ではない
            (d / "functional.md").write_text(
                head + rows.replace("| FR-auth-01-3 | 異常系 | IF 落ちる THEN 伝える |",
                                    "| FR-auth-01-3 | delete | (退役) |") + tail,
                encoding="utf-8")
            r = subprocess.run([sys.executable, str(HERE / "check-ssot.py"), "docs"],
                               cwd=td, capture_output=True, text=True)
            if "CS26 条項 ID の消失: OK" not in r.stdout:
                print(f"NG CS26 が `delete` の退役を違反にした\n{r.stdout}", file=sys.stderr)
                return 1

        # CS26 の局所番地形(課題311): 要件の見出しの下で表の1列目に番地だけを書く形
        # (`| # | 種別 | 基準 |` / `| 2-2 |`)。規範は `#` の欄を番地と呼ぶので、この形も
        # 条項として読めなければならない — 読めないと母集団が空になり、黙って判定不能になる。
        # 番地にハイフンが入る(`2-2`)ので、条項 ID の末尾を切って要件を推す読み方も落とす。
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".claude").mkdir()
            (root / "CLAUDE.md").write_text("# x\n", encoding="utf-8")
            d = root / "docs/01-requirements"
            d.mkdir(parents=True)
            # 要件の中の検討メモの表(1列目が数字でも条項ではない)と、空行で切れて
            # 見出し行なしに再開する受け入れ基準の表(実物の 01 に在る形)を含める
            memo = "\n| 観点 | 説明 |\n|---|---|\n| 7 | 検討メモ |\n"
            head = ("---\nid: fr\n---\n## FR-auth-01 認証\n- **分割可否: 不可分**\n"
                    "\n本文の参照 FR-auth-02-9 は条項ではない。\n" + memo)
            rows = ("\n| # | 種別 | 基準 |\n|---|---|---|\n"
                    "| 1 | 正常系 | WHEN 押す the system SHALL 開く |\n"
                    "| 2 | 境界値 | IF 上限 THEN 拒否 |\n"
                    "| 2-2 | 境界値 | IF 下限 THEN 拒否 |\n"
                    "\n| 3 | 異常系 | IF 落ちる THEN 伝える |\n"
                    "| FR-auth-01-4(2) | 異常系 | IF 切れる THEN 伝える |\n"
                    # 段落の後の見出し行の無いパイプ行は表の続きではない(条項 2-2 と同じ数字)
                    "\n補足の段落。\n| 2-2 | 見出しの無い別の行 |\n")
            tail = "\n## 今回決めた既定(開示)\n\n| 9 | 範囲の外の表 |\n"
            (d / "functional.md").write_text(head + rows + tail, encoding="utf-8")
            for args in (["init", "-q"], ["add", "-A"],
                         ["-c", "user.email=t@t", "-c", "user.name=t",
                          "commit", "-qm", "base"]):
                subprocess.run(["git"] + args, cwd=td, check=True, capture_output=True)
            r = subprocess.run([sys.executable, str(HERE / "check-ssot.py"), "docs"],
                               cwd=td, capture_output=True, text=True)
            if "CS26 条項 ID の消失: OK" not in r.stdout:
                print(f"NG CS26 が局所番地形の条項を読めなかった\n{r.stdout}", file=sys.stderr)
                return 1
            # 2-2 を行ごと消した = 違反(要件の見出しは残っている)
            (d / "functional.md").write_text(
                head + rows.replace("| 2-2 | 境界値 | IF 下限 THEN 拒否 |\n", "") + tail,
                encoding="utf-8")
            r = subprocess.run([sys.executable, str(HERE / "check-ssot.py"), "docs"],
                               cwd=td, capture_output=True, text=True)
            if "CS26 条項 ID の消失: 違反 1 件" not in r.stdout or "FR-auth-01-2-2" not in r.stdout:
                print(f"NG CS26 が局所番地形の消えた条項を見逃した\n{r.stdout}", file=sys.stderr)
                return 1
            # 番地に括弧を含む複合形の条項を消した = 違反
            (d / "functional.md").write_text(
                head + rows.replace("| FR-auth-01-4(2) | 異常系 | IF 切れる THEN 伝える |\n", "")
                + tail, encoding="utf-8")
            r = subprocess.run([sys.executable, str(HERE / "check-ssot.py"), "docs"],
                               cwd=td, capture_output=True, text=True)
            if "CS26 条項 ID の消失: 違反 1 件" not in r.stdout or "FR-auth-01-4(2)" not in r.stdout:
                print(f"NG CS26 が括弧を含む複合形の消えた条項を見逃した\n{r.stdout}",
                      file=sys.stderr)
                return 1
            # 空行の後に再開した表の条項を消した = 違反(再開した表を読めていなければ鳴らない)
            (d / "functional.md").write_text(
                head + rows.replace("| 3 | 異常系 | IF 落ちる THEN 伝える |\n", "") + tail,
                encoding="utf-8")
            r = subprocess.run([sys.executable, str(HERE / "check-ssot.py"), "docs"],
                               cwd=td, capture_output=True, text=True)
            if "CS26 条項 ID の消失: 違反 1 件" not in r.stdout or "FR-auth-01-3" not in r.stdout:
                print(f"NG CS26 が空行の後に再開した表の消えた条項を見逃した\n{r.stdout}",
                      file=sys.stderr)
                return 1
            # 退役(`delete`)は違反ではない。検討メモの表・範囲の外の表・本文の参照が
            # 消えても条項の消失ではない
            (d / "functional.md").write_text(
                head.replace("FR-auth-02-9", "別の要件").replace(memo, "")
                + rows.replace("| 2-2 | 境界値 |", "| 2-2 | delete |")
                + "\n## 今回決めた既定(開示)\n\n- 判断なし: 決めた既定が無い\n",
                encoding="utf-8")
            r = subprocess.run([sys.executable, str(HERE / "check-ssot.py"), "docs"],
                               cwd=td, capture_output=True, text=True)
            if "CS26 条項 ID の消失: OK" not in r.stdout:
                print(f"NG CS26 が局所番地形の退役か範囲の外を違反にした\n{r.stdout}",
                      file=sys.stderr)
                return 1

            # 要件まるごとの移行は違反ではない — フェンスの中の例示の見出しを
            # 「見出しが残っている」と数えると、移行が条項ごとの違反に化ける
            (d / "functional.md").write_text(
                "---\nid: fr\n---\n## 例示\n\n```markdown\n## FR-auth-01 認証\n```\n" + tail,
                encoding="utf-8")
            r = subprocess.run([sys.executable, str(HERE / "check-ssot.py"), "docs"],
                               cwd=td, capture_output=True, text=True)
            if "CS26 条項 ID の消失: OK" not in r.stdout or "移行と読める消失" not in r.stdout:
                print(f"NG CS26 がフェンスの中の見出しで要件の移行を違反にした\n{r.stdout}",
                      file=sys.stderr)
                return 1

        # 条項を1件も読めない構成は「未検査」と名乗る(黙って OK にしない)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".claude").mkdir()
            (root / "CLAUDE.md").write_text("# x\n", encoding="utf-8")
            d = root / "docs/01-requirements"
            d.mkdir(parents=True)
            (d / "functional.md").write_text(
                "---\nid: fr\n---\n## 要件\n条項の表が無い。\n", encoding="utf-8")
            for args in (["init", "-q"], ["add", "-A"],
                         ["-c", "user.email=t@t", "-c", "user.name=t",
                          "commit", "-qm", "base"]):
                subprocess.run(["git"] + args, cwd=td, check=True, capture_output=True)
            r = subprocess.run([sys.executable, str(HERE / "check-ssot.py"), "docs"],
                               cwd=td, capture_output=True, text=True)
            if ("CS26 条項 ID の消失: 未検査 — 判定不能" not in r.stdout
                    or "現在の版にも" not in r.stdout):
                print(f"NG CS26 が条項を読めない構成で未検査と名乗らなかった\n{r.stdout}",
                      file=sys.stderr)
                return 1

    print("OK 状態層+一括検査: stamps / check-debt / check-buildrecord / check-sheet /"
          " check-mission / check-ssot")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
