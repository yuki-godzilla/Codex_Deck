# AI Working Rules

この文書は、Codex、Claude Codeなど複数のAIエージェントで共有するCodex Deckの作業方針である。ツール固有の設定や操作方法は本書に混在させず、`AGENTS.md`、`CLAUDE.md`、`documents/ai/Tool_Configuration_Guide.md`、各ツールの設定例に記載する。

## 作業開始時

- `README.md`を読み、プロジェクトの目的、対象範囲、現在フェーズを確認する。
- `PROJECT_CONTEXT.md`を読み、継続判断、未決事項、次の作業を確認する。
- 変更対象に応じて`Project_Specification.md`と`docs/`配下の要件、調査、PoC、画面設計、リスク資料を確認する。
- Codex/App Server連携を扱う場合は、公式調査結果とPoC計画を優先して読む。
- 作業前後にGit状態を確認し、既存のユーザー変更を明示的な依頼なしに上書き・取り消ししない。

## 実装と文書

- 現在は実装前フェーズである。ユーザーの明示依頼なしに、アプリ本体、フレームワーク、依存関係、実行環境、Windowsサービスを作成しない。
- 実装を開始した後は、既存の構成、命名、型、helper、テストパターンを優先し、無関係なリファクタリングを混ぜない。
- 仕様に影響する実装を変更した場合は、`Project_Specification.md`と該当する`docs/`文書の更新要否を確認する。
- 継続的な判断、進捗、未決事項、次の作業は`PROJECT_CONTEXT.md`へ記録する。
- 上位目的、対象範囲、主要リンクは`README.md`、現在仕様は`Project_Specification.md`、詳細要件・PoC・リスクは`docs/`に集約し、長い説明を重複させない。

## Codex連携の原則

- CodexのThread、Turn、Item、approval policy、sandbox、MCP設定を正本とする。Deck独自の会話・承認・Git制限を設計しない。
- App Serverの外部WebSocket公開をMVP前提にしない。Deck Bridgeからstdio JSONL/JSON-RPCで接続する方針を守る。
- CLI、VS Code、Deck間のThread共有、複数クライアント競合、実行中Turn復帰、workspace別並行は、PoCで確認されるまで可能と断定しない。
- P0のPoC結果によりUI、実装方針、受入条件が変わる場合は、要件文書と`PROJECT_CONTEXT.md`へ反映する。
- App Server schemaは対象CLIバージョンから生成・比較し、未知Itemを破棄せず安全に扱う。

## テストと確認

- 文書変更では、リンク、相対パス、コードフェンス、末尾空白、Markdownの表・リスト、`git diff --check`を確認する。
- 実装後は、変更に関連する最小限のunit/integration testを実行する。
- 通常テストはfake App Server、fixture、record/replayを用い、network-freeかつdeterministicに保つ。
- 実Codex、Tailscale、PWA push、iOS/iPadOS、Windows再起動、実通知配送はlive PoC/smokeとして通常テストから分離する。
- テストできない場合は、理由、依存条件、未確認範囲を明記する。成功扱いにしない。
- 自動テストでは、テストコードだけでなく、期待結果、判定条件、マスク済みログや画面証跡を確認する。

## セキュリティと安全性

- パスワード、API key、token、個人情報、実会話本文、端末固有の絶対パス、キャッシュパス、実行ファイルパスをソース、ログ、文書、設定例に記録しない。
- `.env`、SSH key、AWS/Git credential、Codex認証情報、ブラウザprofileは、人間向けWeb UIの閲覧deny/mask対象として扱う。
- secret mask/denyはイベント受信、ログ保存、UI表示、通知、エクスポート前に適用する。
- 破壊的操作、広範囲削除、設定変更、外部システムへの書込み、Windows/firewall/network/タスクスケジューラの変更は、対象と影響を確認してから行う。
- `danger-full-access`を利用する場合も、アクセスモードを隠さず、実行対象と影響を明確にする。
- 不明点がアーキテクチャ、外部契約、データ境界、セキュリティ、テスト方針に影響する場合は、推測で進めず、提案または判断記録を行う。

## レスポンシブUI

- スマホ、タブレット、PCは別の情報構造として設計する。PC画面の単純縮小版にしない。
- スマホでは会話、作業、差分、ファイル、実行の優先順位を守り、承認・質問・接続状態を常に見つけられるようにする。
- ファイルとコードは読み取り専用であることを明示し、編集可能に見えるUIを置かない。
- 色だけで状態を表さず、ラベル、アイコン、形状、読み上げ可能な説明を組み合わせる。
- background復帰、通信断、keyboard、safe area、画面回転を端末別の確認項目として扱う。

## 返却内容

作業の最後に、次を簡潔に報告する。

1. 変更ファイルと目的
2. 実行した検証と結果
3. 実行していない確認と理由
4. 残っているリスク、未決事項、次の推奨作業
