# タグの言語ごとの書き方

出典: `testing-structure.md` 2.4。
出典の docs/ は配布元(systest)の一次資料であり、このプロジェクトには無い。

名前ベースのフィルタは**どのランナーにも必ずある**ので、共通語彙は「テスト名に含まれる `@critical` という文字列」と定めている。

```typescript
test('@critical @perm 未認証ユーザーは注文履歴にアクセスできない', async ({ page }) => { ... });
```
```python
@pytest.mark.critical                       # marker との併用は任意
def test_未認証ユーザーは注文履歴にアクセスできない():   # @critical @perm
    ...
```
```go
t.Run("@critical @perm 未認証ユーザーはアクセスできない", func(t *testing.T) { ... })
```
```rust
#[test]
fn critical_perm_未認証ユーザーはアクセスできない() { ... }   // 記号が使えないので接頭辞
```
```bash
# bats test_tags=critical,perm
@test "@critical @perm 未認証ユーザーはアクセスできない" { ... }
```

Rust で拾われる接頭辞は `critical` `perm` `a11y` `perf` `slow` `flaky` `smoke` `golden` `bv` `neg` `st` `conc` `vol` に限定される（任意の識別子を分解するとテスト名の単語をタグと誤認するため、既知語だけに絞っている）。

Go の `//go:build critical` は使わない。**コンパイル時に効くため「critical だけ除外して残りを回す」ができず**、除外と限定を同じ語彙で扱えない。
