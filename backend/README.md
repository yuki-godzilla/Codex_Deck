# Codex Deck Backend

この段階のBackendは、Codex App Serverへ直接公開せず、次の境界を実装する。

- `Scheduler`: `1 workspace = 1 Active work`の論理排他
- `Bridge`: App ServerのThread/Turn開始契約
- `StdioJsonRpcTransport`: `codex app-server --stdio`だけを起動するJSON-RPC transport
- `EventStore` / `SqliteEventStore`: browser再接続用のDeck event ID。Codex本文の正本は保存しない
- `create_app`: workspaceのActive work、HTTP replay、WebSocketのイベント配信を提供するFastAPI
- `WorkspaceStore` / `ReadOnlyFileService`: 許可root配下で明示登録したworkspaceだけを、秘密情報・越境symlinkを除外して読み取り専用で扱う
- `ReadOnlyGitService`: 許可済みworkspaceのGit statusとファイル単位diffだけを、固定の非対話readコマンドで取得する
- `ApprovalBroker`: App Serverのstableなcommand/file approval requestを保留し、人が選んだ公式decisionだけを返す
- `SqliteApprovalAuditStore`: 承認決定の最小監査情報をDeck専用SQLiteへ保存する

## 開発用セットアップ

```powershell
python -m pip install -e backend
python -m pip install httpx2
python -m unittest discover -s backend\tests -v
```

`httpx2`はFastAPI/Starletteのテストクライアント用であり、実行時のAPI依存ではない。

## 現在のHTTP契約

| Method | Path | 用途 |
| --- | --- | --- |
| `GET` | `/healthz` | Backendの生存確認 |
| `GET` | `/api/v1/workspaces/{workspace_id}/active-work` | workspaceのActive work取得 |
| `GET` | `/api/v1/workspaces` | 明示登録済みworkspaceの一覧。ローカル絶対パスは返さない |
| `GET` | `/api/v1/workspaces/{workspace_id}/files?path=...` | 許可済みディレクトリの読み取り専用一覧 |
| `GET` | `/api/v1/workspaces/{workspace_id}/file?path=...` | 許可済みUTF-8テキストの読み取り専用プレビュー |
| `GET` | `/api/v1/workspaces/{workspace_id}/git/status` | branchと変更状態の読み取り専用要約 |
| `GET` | `/api/v1/workspaces/{workspace_id}/git/diff?path=...` | 許可済み1ファイルのunstaged/staged diff |
| `GET` | `/api/v1/approvals` | 保留中のcommand/file approval一覧 |
| `POST` | `/api/v1/approvals/{request_id}/decision` | `accept` / `acceptForSession` / `decline` / `cancel`を明示応答 |
| `GET` | `/api/v1/approval-audit` | 明示承認の最小監査記録 |
| `POST` | `/api/v1/workspaces/{workspace_id}/work` | Thread/Turn開始。競合時は`409 workspace_busy` |
| `GET` | `/api/v1/events?after={event_id}` | event ID以降の再接続用replay |
| `WS` | `/api/v1/events/stream?after={event_id}` | replay後のリアルタイムイベント配信 |

WebSocketは先に購読を登録してからreplayを送るため、その間に受信したイベントを取りこぼさない。重複イベントはDeck event IDでクライアントが排除する。`POST /work`へ渡された依頼本文は、Deck event payloadには複製しない。

SQLiteのファイルパス、起動時の`SqliteEventStore`構成、認証、承認応答、ブラウザUIは次の実装単位で追加する。

## ローカルデモ

実Codexを起動せずUI/APIを確認する場合だけ、明示的に`--demo`を指定する。

```powershell
python -m codex_deck.main --demo --database codex-deck-demo.sqlite `
  --workspace-root <許可root> --workspace <登録するworkspace>
```

このモードは決定的なfake Thread/Turn IDを返すだけで、Codex CLIやApp Serverへ接続しない。本番のApp Server構成ではない。

workspaceの追加は現在、起動時のローカル引数だけで行う。認証前のBrowser APIから任意パスを登録するエンドポイントは提供しない。`.env`、鍵形式、credential、`.git`、`.ssh`、`.codex`、`.claude`は一覧・読取の対象外であり、外部へ解決するsymlinkは追跡しない。

Git Adapterは`status`、`rev-parse`、`diff`だけを非対話で起動する。commit、stage、checkout、reset、merge、push、pull、任意Git引数の実行は提供しない。差分は許可済みの1ファイルだけを対象にし、サイズ上限で切り詰める。

承認Brokerはstable APIの`item/commandExecution/requestApproval`と`item/fileChange/requestApproval`だけを対象にする。未対応のpolicy amendmentやpermissions requestを独自形式へ変換しない。実App Server transportとの結合はlive PoCで確認するまで有効化しない。

承認監査にはrequest ID、kind、Thread/Turn/Item ID、公式decision、決定時刻だけを保存する。command、cwd、reason、file change本文、端末情報は保存しない。
