# Codex Deck Backend

この段階のBackendは、Codex App Serverへ直接公開せず、次の境界を実装する。

- `Scheduler`: `1 workspace = 1 Active work`の論理排他
- `Bridge`: App ServerのThread/Turn開始契約
- `StdioJsonRpcTransport`: `codex app-server --stdio`だけを起動するJSON-RPC transport
- `EventStore`: browser再接続用のDeck event ID。Codex本文の正本は保存しない
- `create_app`: workspaceのActive workとイベントreplayを返すFastAPI

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
| `POST` | `/api/v1/workspaces/{workspace_id}/work` | Thread/Turn開始。競合時は`409 workspace_busy` |
| `GET` | `/api/v1/events?after={event_id}` | event ID以降の再接続用replay |

実 App Server接続、SQLite永続化、認証、WebSocket、承認応答、ブラウザUIは次の実装単位で追加する。`POST /work`へ渡された依頼本文は、Deck event payloadには複製しない。
