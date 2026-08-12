---
target: docs/00-requests/decisions/sec.md
change: replace
version_bump: patch
sections:
  - "## D0-sec-10 KVM デバイスは既定で渡さない"
deletes: []
reason: 'issue 054(解消して削除された issue のパスが仕様ドキュメントの根拠として残る)の 00 層1箇所。`D0-sec-10` の「★2026-08-04 追記」が「`CTR-cli-container` のエラーケースが正である(`docs/issues/018`)」と書いているが、この issue は 2026-08-04 の `task-impl-depth` で解消して削除済みであり、参照先が実在しない(`check-changeset.py --ssot` の CS11)。経緯を持つ `docs/histories/2026-08-04-impl-depth.md`(「解消した issue」欄が `018` を挙げる)へ付け替える。**決定の内容・理由・却下した案は1文字も変えない** — 変えるのは根拠の指し先だけである'
reflected: 2026-08-12
---

## D0-sec-10 KVM デバイスは既定で渡さない

- 区分: 決定
- 決めた日: 2026-07-30
- 内容: 既定では `/dev/kvm` 等を渡さない。`--kvm` を指定したときだけデバイスを渡す
  (無ければ警告してソフトウェアエミュレーションにする)。
  **★2026-08-04 追記**: **VM モード(`--vm` / `--vm-fresh`)は `/dev/kvm` を必須とし、無ければ
  中止して終了コード 1 で終わる**(ソフトウェアエミュレーションでは実用的な速度が出ないため、
  VM 無しで続行させるのではなく利用者に VM モードでない起動を選ばせる)。`--kvm` 単独指定の「警告して続行」は
  上のとおり変わらない。**`CTR-cli-container` のエラーケースが正**である
  (この追記の経緯は `docs/histories/2026-08-04-impl-depth.md`)。
- 理由: ブラウザでの確認はコンテナ内 Chrome で足り、CPU 仮想化デバイスを要さない。過剰な特権付与を避ける。
- 却下した案: 常時渡す — 必要のない利用者にまで特権を与える。
- 関連: RQ-env-05 / FR-env-08
