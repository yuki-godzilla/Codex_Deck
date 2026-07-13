# AIツール設定ガイド

## 1. 目的

Codex Deckでは、個人端末のAIツール設定と、リポジトリで共有できる設定例を分離する。認証情報、端末固有パス、MCP実行コマンドをプロジェクトへ混入させず、再現可能な作業方針だけを共有する。

## 2. 設定の分け方

| 種類 | 例 | 管理方針 |
| --- | --- | --- |
| 個人Codex設定 | `~/.codex/config.toml` | 端末ごとに管理し、リポジトリへコピーしない。 |
| プロジェクト共有例 | `.codex/config.toml.example` | portableな既定値だけを例として管理する。利用者は必要に応じてコピーして調整する。 |
| Codex作業指示 | `AGENTS.md` | プロジェクト固有の前提、禁止事項、文書更新、検証方針を管理する。 |
| Claude Code入口 | `CLAUDE.md` | Claude固有の補足だけを記載し、共通ルールは重複させない。 |
| Claude設定例 | `.claude/settings.json.example` | 共有可能なdeny規則だけを例として管理する。 |
| 共通AIルール | `documents/ai/AI_Working_Rules.md` | Codex/Claude Codeなど共通の作業原則を管理する。 |

## 3. リポジトリへ含めないもの

- Codex/Claude/VS Code/Tailscaleの認証token、API key、cookie、session、device ID
- `notify`実行コマンド、MCP command/args/env、plugin cache、marketplace cache
- `projects.*` trust設定、個人workspaceの絶対パス、ユーザー名を含む実行パス
- ntfy URL/topic、PWA push鍵、TLS秘密鍵、DB実体、ログ、会話履歴
- App ServerのWebSocket capability token、signed bearer shared secret

## 4. Codexプロジェクト設定例

`.codex/config.toml.example`は、Codex Deckを開発するAIエージェント向けの控えめな設定例である。実際のmodel、MCP、認証、notify、端末固有のWindows sandbox設定は利用者の個人設定で管理する。

利用する場合は、次の順で確認する。

1. `.codex/config.toml.example`を参照し、必要な値だけを個人または信頼済みプロジェクト設定へ反映する。
2. `approval_policy`、`sandbox_mode`、`default_permissions`が組織/端末の要求と矛盾しないことを確認する。
3. `notify`、MCP、token、absolute path、`[projects.*]`を設定例へ追加しない。
4. Codex App Serverの実装/PoCでは、実際にインストールされたCLIのversionとschemaを記録する。

## 5. Claude Code設定例

`.claude/settings.json.example`は、明らかな秘密情報ファイルの読み取りをdenyする最小例である。実際のpermissions、hook、MCP、端末操作権限は各利用者・組織の方針で管理する。

## 6. 更新チェック

- 設定例を変更したら、秘密情報、個人情報、端末固有の絶対パスがないか確認する。
- Codex設定例の項目名は、対象CLIの公式設定リファレンスと整合するか確認する。
- 設定例の変更がapproval、sandbox、network、ログ、通知に影響する場合は、`Project_Specification.md`とリスク一覧の更新要否を確認する。
- `git diff --check`と`git status --short`で意図しない設定ファイルや生成物がないことを確認する。
