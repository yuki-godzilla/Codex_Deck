# VS Code起点Thread PoC手順

## 目的

VS CodeのCodex拡張で開始したThreadを、Deck側App Serverが一覧またはID指定で読めるかを確認する。対象workspaceは使い捨てフォルダを使い、依頼は「Reply with exactly: VS CODE P0-2 OK. Do not run commands or modify files.」に限定する。

## 実施手順

1. VS Codeで使い捨てworkspaceを開き、Codex拡張から上記のread-only依頼を新規Threadとして開始する。
2. 拡張UIからThread IDをコピーする。ID以外の会話本文、認証情報、端末パスは記録しない。
3. PowerShellで次を実行する。`<workspace>`と`<thread-id>`だけをローカルで置き換え、出力中のIDは共有文書に貼らない。

```powershell
$env:CODEX_DECK_POC_CWD = '<workspace>'
$env:CODEX_DECK_POC_READ_THREAD_ID = '<thread-id>'
$env:CODEX_DECK_POC_SCENARIO = 'basic'
node tools/poc/app-server-harness.mjs
```

4. `threadListBeforeCount`、`requestedThreadRead`、`threadRead`を記録する。

## 判定

| 結果 | Deckへの反映 |
| --- | --- |
| 一覧で検出され、ID指定読取も成功 | VS Code起点Threadを条件付きで検出対象にできる。競合検証へ進む。 |
| 一覧は未検出、ID指定読取は成功 | CLIと同じく自動検出を保証せず、既知IDの読取だけを条件付き対応とする。 |
| ID指定読取も失敗 | VS Code起点ThreadはDeckの対象外として明示し、独自移植はしない。 |

このPoCは、VS Code UI上でのThread開始という人間操作を必要とする。App Server側の判定ハーネスは`tools/poc/app-server-harness.mjs`を使用する。
