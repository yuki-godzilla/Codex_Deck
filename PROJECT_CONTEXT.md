# Codex Deck プロジェクト継続コンテキスト

## 1. 目的と運用

本書は、AI支援開発セッション間でCodex Deckの継続的に参照すべき判断、前提、進捗、未決事項、次の作業を短く引き継ぐための文書である。

- セッション開始時に`README.md`、`AGENTS.md`、`documents/ai/AI_Working_Rules.md`、関連する要件文書とともに読む。
- 上位目的と範囲は`README.md`、現在仕様は`Project_Specification.md`、詳細要件・PoC・設計は`docs/`を正本とする。
- 一時的な会話ログ、生ログ、秘密情報、端末固有パス、長い設計説明は記載しない。
- 継続的に参照する判断、実装/PoCの進捗、未決事項、次の推奨作業が変わった時だけ更新する。

## 2. 現在のプロジェクト概要

| 項目 | 内容 |
| --- | --- |
| プロジェクト | Codex Deck |
| 主目的 | Windows PC上のCodexを、スマートフォン、タブレット、PCブラウザから遠隔操作・監視・レビューするモバイルファーストWebクライアントを作る。 |
| 現在フェーズ | P0の互換性PoCとMVP実装基盤の整備。 |
| 実装状況 | PoC harness、framework非依存のScheduler/Bridge開始契約、App Server stdio adapterを実装済み。Web UI、API、DB、実 App Server結合test、依存関係、実行設定は未作成。 |
| 正本 | CodexのThread、Turn、Item、approval policy、sandbox設定。Deck DBは補助情報のみ。 |
| 主要端末 | iPhone、iPad、PCブラウザ。PCの単純縮小版ではない。 |

主要文書:

- `README.md`
- `Project_Specification.md`
- `AGENTS.md`
- `CLAUDE.md`
- `documents/ai/AI_Working_Rules.md`
- `docs/requirements/CODEX_DECK_REQUIREMENTS.md`
- `docs/research/CODEX_OFFICIAL_CAPABILITY_RESEARCH.md`
- `docs/poc/CODEX_DECK_POC_PLAN.md`

## 3. 確定事項

1. Codex Deckは独自AIエージェント、リモートデスクトップ、汎用Webシェルではない。Codexの公式操作体験をモバイルに適応するWebクライアントである。
2. Codex App ServerはDeck Bridgeからstdio JSONL/JSON-RPCで接続する。App Server WebSocketの直接外部公開はMVPで採用しない。
3. App Server、Codex CLI、VS Code拡張のセッション共有・同時操作は、PoCで確認できるまで保証しない。
4. workspaceはフォルダ単位で、Gitリポジトリは必須ではない。選択範囲は許可rootと明示登録に限定する。
5. 1 workspaceのActive workは1件だけとする。別workspace並行実行は必須要件だが、物理的なworker構成はPoCの結果で決める。
6. Web上の人間による直接コード編集と自由ターミナルは初期リリース対象外である。
7. Windows再起動、App Server障害、ブラウザ切断後にCodex依頼を自動再実行しない。中断、ログ、明示再開を優先する。
8. SMAIとはリポジトリ、プロセス、ポート、DB、ログ、設定、起動/更新/障害復旧、通知topicを共有しない。

## 4. 現在の進捗

| 領域 | 状態 | 内容 |
| --- | --- | --- |
| 公式仕様調査 | 確認済み | App Server、CLI設定、AGENTS.md、Windows sandboxを一次情報で調査し、確認済み/PoC必要/未確認を分類済み。 |
| 要件定義 | 確認済み | メイン要件、ユースケース、画面設計、PoC、リスクを作成済み。 |
| AI文書体系 | 確認済み | README、仕様書、継続コンテキスト、AI指示、共通ルール、設定例を導入。 |
| PoC-0 | 確認済み | `codex-cli 0.144.1`からTypeScript/JSON Schemaを生成し、tree hashを記録した。 |
| PoC-1 | 条件付確認済み | stdio handshake、Thread操作、主要Item、完了、resume、file/command approvalの`decline`、実行中Turnのsteer/interrupt受理、強制終了後の再送なし、再起動後の保存Thread読取を確認。実行中Turnの公式復帰は未確認で、中断扱いとする。 |
| PoC-2 | 条件付確認済み | CLI起点ThreadはID指定の`thread/read`で読めたが、同cwdの`thread/list`では検出できなかった。read-only Turnはworkspace A/Bおよび同一workspaceで同時に完了した。VS Code共有、同一Thread/承認競合、変更を伴う並行は未検証。 |
| アプリ実装 | 基盤実装中 | ユーザーの明示依頼により、PoC結果を越える互換性を前提にしないBridge/Scheduler基盤を実装した。 |

## 5. 未決事項

1. 同一`CODEX_HOME`でCLI、VS Code、App Server、複数workerを使ったときのThread共有と並行安全性。
2. 同一Threadを複数クライアントが閲覧・承認・停止・追加指示したときの排他と公式上の最終挙動。
3. App Server再起動後、実行中Turnへ再接続できるか、中断として扱うべきか。
4. Tailscale identity header、Deckの端末登録、短期session、紛失端末の失効をどう組み合わせるか。
5. iOS/iPadOS PWA pushをMVP必須にするか、アプリ内通知とntfyを必須fallbackにするか。
6. App Server Itemから差分、テスト結果、background terminalをどの粒度で構造化できるか。

## 6. 既知リスク・制約

- App ServerのWebSocketは実験的・未サポートとされるため、MVPの外部接続経路にしない。
- Codex更新でApp Server schemaやItem形状が変わる可能性がある。CLI versionと生成schemaの差分確認が必要である。
- PWAのbackground、push、WebSocket、clipboardはiOS/iPadOSで制約を受け得る。
- フルアクセス、ファイル閲覧、ログ、通知にはsecret漏えいリスクがある。mask/denyと監査が必要である。
- 大規模repo、巨大diff、長時間pytestログはモバイルを操作不能にし得るため、仮想化・chunk化が必要である。

詳細は`docs/requirements/CODEX_DECK_RISKS.md`を参照する。

## 7. 次に進める作業

1. **MVP基盤** — Deck event store、FastAPI APIを、fake App Serverを使う決定的テストとともに追加する。App Server adapterは実機結合testを追加する。
2. **P0: PoC-2残件** — VS Code共有、同一Thread/承認競合、変更を伴うworkspace別並行を検証する。
3. **最初のUI縦スライス** — workspace/Thread/Turnの最小画面を実装し、代表viewportで実画面検証する。
4. **P1** — 復旧、モバイルPWA、Windows自動起動、大規模repo性能を検証する。

アプリ本体の実装、フレームワーク初期化、依存関係の追加は、上記P0の結果とユーザーの明示指示を得るまで開始しない。

## 8. 参考URL

| 名称 | URL | 用途 | 最終確認 |
| --- | --- | --- | --- |
| Codex App Server | https://learn.chatgpt.com/docs/app-server | Thread、Turn、Item、JSON-RPC、approval | 2026-07-13 |
| Codex Config basics | https://learn.chatgpt.com/docs/config-file/config-basic | CLI/IDE共通設定、approval、sandbox | 2026-07-13 |
| Codex AGENTS.md | https://learn.chatgpt.com/docs/agent-configuration/agents-md | Codexの指示ファイル探索 | 2026-07-13 |
| Codex Windows sandbox | https://learn.chatgpt.com/docs/windows/windows-sandbox | Windows native sandbox | 2026-07-13 |

## 9. 更新メモ

- 2026-07-13: 要件定義、公式仕様調査、ユースケース、画面設計、PoC計画、リスク一覧を作成。アプリ実装は未開始。
- 2026-07-14: AI-Dev-Process-Documentsのルールに基づくREADME、仕様書、継続コンテキスト、AI指示、共通ルール、設定例を導入。
- 2026-07-14: P0-0を完了し、P0-1のstdio基本経路を確認。詳細は`docs/poc/CODEX_DECK_POC_RESULTS.md`を参照。
- 2026-07-14: P0-2でread-only Turnのworkspace A/B並行と同一workspace二重起動を確認。Deck Schedulerによるworkspace論理排他を必須とした。
- 2026-07-14: Backend基盤として、workspace lockとfake App Server経由のBridge開始契約を実装。実 App Server adapter、API、DBは未実装。
- 2026-07-14: `codex app-server --stdio`専用のJSON-RPC adapterを追加。承認の自動応答、WebSocket公開、実 App Server結合testは未実装。
