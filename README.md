# Codex Deck

Codex Deckは、WindowsサーバーPC上で動作するCodexを、スマートフォン、タブレット、PCブラウザから遠隔操作・監視・レビューするためのモバイルファーストWebクライアントです。

これはリモートデスクトップや独自AIエージェントではありません。Codex CLI、VS CodeのCodex拡張、Codex App Serverの公式概念・操作体験を、モバイルでの依頼、監視、質問回答、承認、差分レビューに最適化して提供します。

本READMEは、Codex Deckの要件定義兼入口です。上位の目的、要件、対象範囲を定義し、初見の開発者、レビュアー、AIエージェントが主要文書へ到達できるようにします。

## 1. 目的

- スマートフォンやタブレットから、Windows PC上のCodex作業を安全に開始・監視・レビューできるようにする。
- CodexのThread、Turn、Item、承認、sandbox、設定を正本として尊重し、Deck独自の会話や承認モデルを作らない。
- ブラウザの切断やモバイル端末のスリープ中も、サーバー側でCodex作業を継続し、復帰時に状態を再同期できるようにする。
- ファイル、Git差分、コマンド、テスト結果を読み取り専用で確認し、必要な箇所をCodexへの次の依頼に引用できるようにする。

## 2. 上位要件

| ID | 要件 | 目的 / 背景 | 優先度 | 関連仕様 |
| --- | --- | --- | --- | --- |
| REQ-001 | Codex公式のThread、Turn、Item、approval、sandboxを踏襲する | 独自仕様による互換性低下を防ぐ | 高 | `docs/requirements/CODEX_DECK_REQUIREMENTS.md` |
| REQ-002 | モバイルファーストの操作・監視・レビュー体験を提供する | iPhone/iPadを主要端末として実用性を確保する | 高 | `docs/design/CODEX_DECK_SCREEN_MAP.md` |
| REQ-003 | workspace単位でCodex作業を安全に管理する | 1 workspace 1 Active workと、別workspace並行の両立を図る | 高 | `docs/requirements/CODEX_DECK_REQUIREMENTS.md` |
| REQ-004 | Tailscale配下で、App Serverを直接外部公開せずに利用する | 遠隔操作の安全性とApp Serverの実験的WebSocket依存回避 | 高 | `docs/research/CODEX_OFFICIAL_CAPABILITY_RESEARCH.md` |
| REQ-005 | ブラウザ切断・App Server障害・Windows再起動で安全に復旧する | 重複実行を避け、明示再開できるようにする | 高 | `docs/poc/CODEX_DECK_POC_PLAN.md` |
| REQ-006 | Smart Market AIとは完全に分離して運用する | プロセス、DB、ログ、設定、障害の相互波及を防ぐ | 高 | `docs/requirements/CODEX_DECK_REQUIREMENTS.md` |

## 3. 対象範囲

### 3.1 初期リリースの対象

- workspace登録・切替、セッション一覧、新規/再開、指示送信、追加指示、停止
- Codex発言、進捗、コマンド、ファイル変更、Git差分、テスト結果、承認要求の表示
- 読み取り専用のファイル/コード/差分ビューと、ファイル・行・diff引用
- スマホ向けタブUI、タブレット/PC向け複数ペイン、PWA、通知、再接続
- Windows上のDeck/Bridgeの自動起動、ヘルスチェック、ログ、Deck専用SQLite、Tailscale内アクセス

### 3.2 対象外

- Web上での人間によるコード編集、汎用Webシェル、完全なVS Code互換
- 一般インターネット公開、複数ユーザー共同編集、組織RBAC、SaaS化、課金
- Codex以外のAIエージェント統合、独自AIモデル、独自のGit制限
- Windows以外のサーバー正式対応、Windows再起動後のCodex作業の自動再実行

## 4. 現在のフェーズ

現在は**P0互換性PoCとMVP実装基盤**フェーズです。Backendには、App Server stdio adapter、Bridge、workspace Scheduler、FastAPIのHTTP/WebSocket API、SQLite対応の再接続用event storeを実装しています。最初のレスポンシブWeb UI縦スライスを実装しましたが、実ブラウザでのUI/UX検証は環境のブラウザ連携復旧待ちであり、完了扱いではありません。

各機能を有効化する前に、Codex App Serverのstdio接続、セッション共有、workspace別並行実行、復旧、モバイルPWA、Windows運用、大規模リポジトリ性能をPoCで検証します。

## 5. 文書構成と読む順番

| 文書 | 役割 |
| --- | --- |
| [要件定義書](docs/requirements/CODEX_DECK_REQUIREMENTS.md) | 機能・非機能・運用・セキュリティ・MVP境界の正本 |
| [公式機能調査](docs/research/CODEX_OFFICIAL_CAPABILITY_RESEARCH.md) | OpenAI公式情報、確認済み/PoC必要/未確認の区分 |
| [ユースケース](docs/requirements/CODEX_DECK_USE_CASES.md) | 利用者操作、例外、受入シナリオ |
| [画面一覧・情報設計](docs/design/CODEX_DECK_SCREEN_MAP.md) | スマホ/タブレット/PCの画面構成とUX |
| [UI実画面検証記録](docs/poc/CODEX_DECK_UI_VALIDATION.md) | Web UI縦スライスの確認結果・未実施項目 |
| [接続境界](docs/operations/CODEX_DECK_ENDPOINTS.md) | Deck専用URL、ポート、公開方式、SMAIとの分離 |
| [PoC計画](docs/poc/CODEX_DECK_POC_PLAN.md) | 実装前に確認する技術成立性と成功条件 |
| [リスク一覧](docs/requirements/CODEX_DECK_RISKS.md) | 互換性、セキュリティ、運用、性能のリスク登録簿 |
| [Project_Specification.md](Project_Specification.md) | 現在仕様、想定構成、実装状況、確認状況の横断整理 |
| [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) | AIセッション間で引き継ぐ判断、進捗、未決事項、次の作業 |
| [AGENTS.md](AGENTS.md) | CodexなどAIエージェントが守る作業指示 |
| [CLAUDE.md](CLAUDE.md) | Claude Code向けの入口と最小限の補足 |
| [AI Working Rules](documents/ai/AI_Working_Rules.md) | AIツール間で共有する作業方針 |
| [Tool Configuration Guide](documents/ai/Tool_Configuration_Guide.md) | 個人設定とプロジェクト共有設定の境界 |

## 6. 開発・レビューの進め方

1. 実装前に[PoC計画](docs/poc/CODEX_DECK_POC_PLAN.md)のP0ゲートを完了する。
2. 要件・PoC・リスクのレビューで、MVPへ進める条件を確認する。
3. 実装開始後は、現在仕様を`Project_Specification.md`、継続判断を`PROJECT_CONTEXT.md`へ反映する。
4. 実装・テスト・確認は小さな単位で行い、外部サービス・実Codex・モバイル端末に依存する確認を通常テストから分離する。

## 7. AI支援開発の運用

- AIエージェントは作業前に`AGENTS.md`、`documents/ai/AI_Working_Rules.md`、関連する仕様文書、`PROJECT_CONTEXT.md`を確認する。
- 永続的な仕様は`Project_Specification.md`、AIの引き継ぎ情報は`PROJECT_CONTEXT.md`、詳細な要件は`docs/`へ記録し、長い内容を重複させない。
- 個人の認証情報、token、端末固有パス、MCP実行パス、キャッシュは共有文書・設定例に含めない。
- AIがアプリ実装を開始するには、ユーザーからの明示依頼と、対象PoCゲートの確認が必要である。

## 8. メンテナンス方針

- 上位目的、要件、対象範囲、主要リンクが変わった場合は本READMEを更新する。
- 現在仕様、構成、外部インターフェース、実装状況、確認状況が変わった場合は`Project_Specification.md`を更新する。
- 継続的に参照する判断、進捗、未決事項、次の作業が変わった場合は`PROJECT_CONTEXT.md`を更新する。
- AIの作業規則、禁止事項、検証方針が変わった場合は`AGENTS.md`または`documents/ai/AI_Working_Rules.md`を更新する。
- 秘密情報、パスワード、token、個人情報、端末固有の絶対パスは文書や設定例に記録しない。
