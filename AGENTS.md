# Codex Deck AI作業指示

## 1. 目的と文書の役割

Codex Deckは、Windows PC上のCodexをスマートフォン、タブレット、PCブラウザから遠隔操作・監視・レビューするためのモバイルファーストWebクライアントである。

本ファイルは、AIエージェントが安全に本プロジェクトで作業するための安定ルールを定義する。上位目的・対象範囲は`README.md`、現在仕様・実装状況は`Project_Specification.md`、継続判断・進捗は`PROJECT_CONTEXT.md`、詳細要件は`docs/`を正本とする。

## 2. 作業開始時に読む文書

1. `README.md`
2. `PROJECT_CONTEXT.md`
3. `documents/ai/AI_Working_Rules.md`
4. 変更対象に応じた`Project_Specification.md`と`docs/`配下の資料
5. Codex連携を扱う場合は`docs/research/CODEX_OFFICIAL_CAPABILITY_RESEARCH.md`
6. 実装前PoCを扱う場合は`docs/poc/CODEX_DECK_POC_PLAN.md`

初めて実装に進む前は、メイン要件、PoC計画、リスク一覧、画面設計を確認する。

## 3. 判断の優先順位

1. ユーザーの明示要求
2. `README.md`と`docs/requirements/CODEX_DECK_REQUIREMENTS.md`
3. `Project_Specification.md`
4. `PROJECT_CONTEXT.md`
5. `docs/research/`、`docs/poc/`、`docs/design/`、`docs/requirements/`の詳細資料
6. 実装開始後の実コード、テスト、実測PoC結果

重要な不一致は推測で解消せず、関連文書へ記録し、アーキテクチャ・外部契約・セキュリティ・テスト方針に影響する場合は提案または確認を行う。

## 4. Codex Deck固有の原則

- Codex Deckは独自AIエージェントではない。CodexのThread、Turn、Item、approval、sandbox、MCPの正本をDeckに複製しない。
- Codex App ServerはDeck Bridgeからstdio JSONL/JSON-RPCで接続する。App Serverを外部WebSocketで直接公開しない。
- App Server WebSocketは実験的・未サポートとして扱い、MVP必須経路にしない。
- CLI、VS Code、DeckのThread共有、同時クライアント競合、実行中Turn復帰はPoC合格まで保証しない。
- 1 workspace 1 Active workを維持する。別workspaceの並行実行はPoCで安全性を確認してから実装する。
- Webの人間による直接編集、汎用Webシェル、Windows再起動後の自動依頼再実行を実装しない。
- SMAIとはプロセス、ポート、DB、ログ、設定、起動/更新、通知topic、障害復旧を共有しない。

## 5. セキュリティとデータ境界

- App Server、Codex credential、MCP secret、`.env`、SSH key、AWS/Git credential、ブラウザprofileをブラウザへ露出しない。
- secret mask/denyはイベント受信、ログ、UI、通知、エクスポート前に適用する。
- workspaceの選択範囲は許可rootと明示登録に限定する。OS全体の自由探索、許可root外のsymlink追跡を許可しない。
- `danger-full-access`を使えるようにしても、現在のアクセスモードをUIで隠さない。
- 実Codex、Tailscale、PWA push、ntfyを試す場合は、tokenや端末固有値をソース、ログ、文書、設定例へ書かない。

## 6. 実装・設計ルール

- フロントエンド、Backend API、Deck Bridge、Scheduler、File/Git Adapter、Notification Adapterを分離する。
- UIはApp Serverへ直接接続しない。Bridgeが公式JSON-RPCのversion境界を担う。
- App Server schemaは対象CLIから生成し、CLI versionとともに契約確認する。未知Itemは破棄せず、安全に記録・表示する。
- Deck SQLiteにはworkspace、表示、通知、未読、event位置、障害履歴などの補助状態だけを保存し、Thread本文の正本やtokenを保存しない。
- ブラウザ再接続はDeck event ID、outbox、重複排除、Thread snapshot再取得で扱う。Codex公式のevent再送を推測で前提にしない。
- 通常テストはfake App Server、fixture、record/replayを用い、network-freeかつdeterministicにする。実Codex・モバイル・Tailscaleはlive PoC/smokeに分離する。
- スマホ、タブレット、PCを別の情報構造として扱う。PC画面を縮小するだけのレスポンシブ実装にしない。

## 7. 現在のフェーズと禁止事項

現在は要件定義・公式仕様調査・PoC計画・AI文書整備フェーズである。

- ユーザーが明示しない限り、アプリ本体、フレームワーク初期化、依存関係、実行環境、Windowsサービス、ポート公開を作成しない。
- P0のPoC-0/1/2が完了するまで、App Serverの共有・並行・承認・停止の挙動を実装上の事実として断定しない。
- PoCを実施する場合は、`docs/poc/CODEX_DECK_POC_PLAN.md`の安全条件と成功条件に従い、結果を要件・コンテキストへ反映する。

## 8. 文書更新ルール

| 変更内容 | 更新先 |
| --- | --- |
| 上位目的、要件、範囲、主要リンク | `README.md` |
| 現在仕様、構成、外部契約、実装/確認状況 | `Project_Specification.md` |
| 継続判断、進捗、未決事項、次の作業 | `PROJECT_CONTEXT.md` |
| 詳細要件、画面、PoC、リスク、公式調査 | 対応する`docs/`文書 |
| AI作業規則・禁止事項・検証方針 | `AGENTS.md`または`documents/ai/AI_Working_Rules.md` |
| Codex/Claude設定の共有境界 | `documents/ai/Tool_Configuration_Guide.md`、設定例 |

長い説明は複数文書に重複させず、詳細元へリンクする。人向け文書は日本語を基本とし、MarkdownはUTF-8 without BOMで管理する。

## 9. Git・検証・完了報告

- 意味のある編集の前後に`git status --short`を確認する。ユーザー既存変更を上書き・取り消ししない。
- 完結した作業単位ごとに、変更範囲と検証結果を確認してからコミットし、現在の作業ブランチを対応するリモートへプッシュする。作業単位には無関係な既存変更を混在させない。
- コミットメッセージは、その作業単位の目的を簡潔に表す。コミットまたはプッシュに失敗した場合は、変更を破棄せず、失敗理由と未反映の範囲を報告する。
- 破壊的Git操作、広範囲削除、secret変更、外部書込み、Windows/firewall/network/タスクスケジューラの大きな変更は、対象と影響を確認してから行う。
- 文書変更では、リンク、相対パス、Markdownコードフェンス、末尾空白、`git diff --check`を確認する。
- 実装後は関連する最小限のテストを実行する。テストできない外部依存は、未確認範囲と理由を明記する。
- 完了時には、変更ファイル、実行した検証、未実施確認と理由、残リスクを簡潔に報告する。
