# Claude Code向け作業入口

Codex Deckでは、共通のAI作業ルールを`AGENTS.md`と`documents/ai/AI_Working_Rules.md`に集約する。本ファイルにはClaude Code固有の入口だけを記載する。

## 作業開始時に読む文書

- `README.md`
- `AGENTS.md`
- `PROJECT_CONTEXT.md`
- `Project_Specification.md`
- 変更対象に応じた`docs/`配下の資料
- `documents/ai/AI_Working_Rules.md`

## Claude Code固有の補足

- 現在は実装前フェーズである。ユーザーの明示指示とPoCゲートの確認なしに、アプリ本体、フレームワーク、依存関係、サービス設定を開始しない。
- Codex App Server、Thread共有、追加指示、承認、停止、並列実行について、公式調査で未確定の事項を推測で実装しない。
- 変更後は関連文書、Markdownリンク、Git状態を確認する。
- 端末固有パス、token、認証情報、MCP設定、実会話本文を文書・設定例・ログへ記録しない。
- 大きな設計変更、Windowsサービス/タスクスケジューラ、Tailscale公開、通知配送、秘密情報を扱う変更では、対象と影響を説明してから実施する。
