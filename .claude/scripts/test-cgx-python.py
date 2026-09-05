#!/usr/bin/env python3
"""Python 抽出器の分岐検出(`cgx/python_ast.py`)の fixture。

**置く理由は `make check` がこれを実行することである。** 規範は
`.claude/directions/callgraphs.md` §5.7 が持ち、**その境界は合成コードでしか固定できない**
(実プロジェクトの現物は変わっていく)。

いま固定しているのは 2026-08-25 に足した `dispatch_guards`(ガード節の宣言)の境界である
— ct_matchsupport の課題票 243 と、その最初の実装に対する独立検査の反例。
**宣言したものだけが落ちること**と、**宣言していない同じ形が落ちないこと**の両側を見る。
"""
import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cgx import python_ast as pa                                  # noqa: E402

SETS = {
    "IDENTIFIED": ["PAY_BY_CREDIT_CARD", "PAY_BY_CONVENI", "CHECK_PAYMENT"],
    "OPERATION_CMDS": ["WITHDRAW_APPLICATION", "COMPLETE_MANUAL_REFUND"],
}
REL = "backend/app.py"

# 実測の形(課題票 243): 前段が3値の合成入口を作り、本物の3分岐が別に在る
GUARD = '''
def lambda_handler(e, c):
    if route == "applicant" and cmd in IDENTIFIED and not p.get("id"):
        return err("no id")
    if cmd == "PAY_BY_CREDIT_CARD":
        return pay_card(p)
    elif cmd == "PAY_BY_CONVENI":
        return pay_conveni(p)
    elif cmd == "CHECK_PAYMENT":
        return check(p)
    elif cmd in OPERATION_CMDS:
        return ops(p)
'''

# 独立検査の反例(2026-08-25): **同じ形の本物のハンドラ**。宣言しないかぎり落ちてはならない
VIP = '''
def lambda_handler(e, c):
    if tenant == "vip" and cmd in ("A", "B"):
        return vip_batch(p)
    if cmd == "A":
        return ordinary_a(p)
    if cmd == "B":
        return ordinary_b(p)
'''

NESTED = '''
def lambda_handler(e, c):
    with lock():
        if cmd == "A":
            return a(p)
        elif cmd in OPERATION_CMDS:
            return ops(p)
'''


# 同じ値のガードと本物(独立検査・2周目)。**宣言は値の単位で効く**ので、宣言すると両方落ちる。
# そしてこの形では偽の入口が生まれないので、**宣言する必要が最初から無い。**
SAME_VALUE = '''
def lambda_handler(e, c):
    if tenant == "vip" and cmd == "A":
        return vip_a(p)
    if cmd == "A":
        return ordinary_a(p)
'''


def branches(src: str, guards: set[str] | None = None,
             fn_name: str = "lambda_handler",
             hits: set[str] | None = None) -> list[tuple[str, list]]:
    tree = ast.parse(src)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef))
    got = pa._find_dispatch(fn, {"cmd"}, SETS)
    return pa._drop_declared_guards(REL, fn_name, got, guards or set(), hits)


def values(src: str, guards: set[str] | None = None) -> list[str]:
    return [v for v, _ in branches(src, guards)]


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    def ck(name: str, cond: bool, note: str = "") -> None:
        checks.append((name, cond, note))

    guard_id = f"{REL}::lambda_handler#CHECK_PAYMENT|PAY_BY_CONVENI|PAY_BY_CREDIT_CARD"

    got = values(GUARD)
    ck("(a) 宣言が無ければ、前段も今までどおり拾う(振る舞いを変えない)",
       "CHECK_PAYMENT|PAY_BY_CONVENI|PAY_BY_CREDIT_CARD" in got, str(got))

    got = values(GUARD, {guard_id})
    ck("(b) 宣言したガード節は落ちる",
       "CHECK_PAYMENT|PAY_BY_CONVENI|PAY_BY_CREDIT_CARD" not in got, str(got))
    ck("(b) 本物の3つは残る",
       {"CHECK_PAYMENT", "PAY_BY_CONVENI", "PAY_BY_CREDIT_CARD"} <= set(got), str(got))
    ck("(b) 他の複数値の分岐は残る",
       "COMPLETE_MANUAL_REFUND|WITHDRAW_APPLICATION" in got, str(got))

    # 落とした本文は分岐に残らない = ディスパッチャ本体の差分に回る(_without_branches)
    bodies = dict(branches(GUARD, {guard_id}))
    calls = sorted({n.func.id for st in bodies["CHECK_PAYMENT"] for n in ast.walk(st)
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)})
    ck("(b) ガードの本文を他の分岐へ混ぜない(辺の水増しをしない)",
       calls == ["check"], str(calls))

    got = values(VIP)
    ck("(c) 同じ形の本物のハンドラは、宣言しないかぎり落ちない",
       "A|B" in got, str(got))
    ck("(c) 細かい分岐も残る", {"A", "B"} <= set(got), str(got))

    got = values(VIP, {f"{REL}::lambda_handler#A|B"})
    ck("(d) 宣言すればその1つだけが落ちる",
       "A|B" not in got and {"A", "B"} <= set(got), str(got))

    got = values(NESTED, {f"{REL}::lambda_handler#COMPLETE_MANUAL_REFUND|WITHDRAW_APPLICATION"})
    ck("(e) ネストした分岐にも宣言が効く", got == ["A"], str(got))

    got = values(GUARD, {f"{REL}::other_fn#CHECK_PAYMENT|PAY_BY_CONVENI|PAY_BY_CREDIT_CARD"})
    ck("(f) 関数名が違う宣言は効かない(取り違えを落とさない)",
       "CHECK_PAYMENT|PAY_BY_CONVENI|PAY_BY_CREDIT_CARD" in got, str(got))

    # (g) 同じ値のガードと本物は先に1つへ畳まれているので、宣言すると**両方**落ちる。
    #     偽の入口はそもそも生まれないので、この形を宣言してはならない(規範 §5.7)。
    got = values(SAME_VALUE)
    ck("(g) 同じ値なら入口は1つに畳まれる(偽の入口が生まれない)", got == ["A"], str(got))
    calls = sorted({n.func.id for st in dict(branches(SAME_VALUE))["A"] for n in ast.walk(st)
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)})
    ck("(g) 畳んだ入口が両方の呼び出しを持つ", calls == ["ordinary_a", "vip_a"], str(calls))
    ck("(g) その値を宣言すると本物ごと落ちる(だから宣言しない)",
       values(SAME_VALUE, {f"{REL}::lambda_handler#A"}) == [], str(got))

    # (h) 照合しなかった宣言は hits の差として返る = 生成物の表に出る材料になる
    hits: set[str] = set()
    miss = f"{REL}::lambda_handler#B|A"          # 値の順が違う(抽出は辞書順に正規化する)
    branches(VIP, {f"{REL}::lambda_handler#A|B", miss}, hits=hits)
    ck("(h) 効いた宣言だけが hits に入る",
       hits == {f"{REL}::lambda_handler#A|B"}, str(hits))
    ck("(h) 効かなかった宣言は差として残る", miss not in hits, str(hits))

    for name, ok, _ in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    ng = [(n, note) for n, ok, note in checks if not ok]
    if ng:
        print(f"\n{len(ng)} 件 FAIL", file=sys.stderr)
        for n, note in ng:
            print(f"--- {n}\n{note}", file=sys.stderr)
        return 1
    print(f"OK Python 抽出器の分岐検出 {len(checks)} 項目")
    return 0


if __name__ == "__main__":
    sys.exit(main())
