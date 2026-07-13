# Codex Deck PoC実施結果

## 1. 記録方針

本書は、実装前PoCの観測結果と、MVPへ進むために残る検証を記録する。IDはSHA-256の先頭12文字へ置換し、認証情報、実会話本文、端末固有パス、生ログは保存しない。

## 2. 実施環境

| 項目 | 値 |
| --- | --- |
| 実施日 | 2026-07-14 JST |
| Codex CLI | `codex-cli 0.144.1` |
| App Server transport | `stdio://` |
| App Server platform | `windows` |
| 生成TypeScript | 598 files / tree SHA-256 `cfc9fea07cd1014015cf4bddfb0cc188d9e65f25ae73efbdcc584910ccbac221` |
| 生成JSON Schema | 267 files / tree SHA-256 `9a97967d1959c308755f5a29e4b7c99293a40a7bd516f35bb921062b58d6d118` |
| 検証workspace | 空の使い捨てローカルworkspace。read-only sandbox。 |

生成物は一時領域にだけ置き、リポジトリにはハッシュと観測結果だけを保存した。

## 3. P0-0 バージョン固定・契約ベースライン

| 確認項目 | 結果 | 判定 |
| --- | --- | --- |
| `generate-ts --out` | 成功 | 合格 |
| `generate-json-schema --out` | 成功 | 合格 |
| Thread/Turnの基本型 | `ThreadStartParams`、`TurnStartParams`、`TurnSteerParams`、`TurnInterruptParams`を確認 | 合格 |
| 承認型 | command/file approval用のParams/Responseを確認 | 合格 |
| experimental範囲 | realtime、plugin/app、plan delta等にexperimental表記を確認 | 合格。MVP必須経路から除外する。 |

実装時は、上記CLI versionと生成tree hashをBridgeの契約ベースラインとして比較する。生成物の手書きDTOへの置換はしない。

## 4. P0-1 App Server接続と基本イベント

`tools/poc/app-server-harness.mjs`で、使い捨てworkspaceに対してread-onlyの短い依頼を実行した。

| 確認項目 | 観測結果 | 判定 |
| --- | --- | --- |
| handshake | `initialize`後に`initialized`を送信し、Windows platformとuser agentを受信 | 合格 |
| Thread操作 | `thread/list`、`thread/start`、`thread/read`、`thread/resume`が成功 | 合格 |
| Turnと通知 | `turn/start`後に`item/started`、`item/agentMessage/delta`、`item/completed`、`turn/completed`を受信 | 合格 |
| 非コア通知の保持 | `remoteControl/status/changed`などの未構造化通知を記録してもハーネスが停止しないことを確認 | 条件付合格。未知Item本文の表示方針はBridge実装時に検証する。 |
| file approval | `item/fileChange/requestApproval`を受信し、公式`decline`応答後に使い捨てworkspaceが未変更であることを確認 | 合格 |
| command approval | `item/commandExecution/requestApproval`を受信し、公式`decline`応答で解決 | 合格 |
| `turn/steer` / `turn/interrupt` | 完了済みTurnでは双方とも`no active turn`で拒否。`turn/started`通知から実行中Turn IDを取得して送った場合は双方が受理 | 合格 |
| App Server障害・再起動 | 未実行 | 未判定 |

Thread IDとTurn IDは保存せず、それぞれのハッシュ先頭12文字だけを検証時に確認した。App Server stderrは2行出力されたが、内容は証跡へ保存していない。

## 5. P0-2 セッション共有・並行実行

P0-1で同一App Server接続内の`thread/resume`は成功した。一方、CLI起点、VS Code起点、複数App Server、同一Thread競合、同一承認競合、workspace A/B並行、同一workspaceの二重開始は未検証である。

判定は**未判定**とする。Deckは、P0-2の検証完了までCLI/VS CodeとのThread共有や別workspace並行を保証せず、同一workspace 1 Active workの設計前提を維持する。

## 6. 次の実施順

1. App Server終了時のexit code、未完了request、二重送信防止、保存済みThreadの可視性を使い捨てworkspaceで観測する。
2. CLI起点およびVS Code起点のThreadをApp Serverから読めるかを確認する。
3. 同一Threadの閲覧・追加指示・停止・承認の競合を、先後関係を変えて3回ずつ確認する。
4. workspace A/Bの同時Turnと、同一workspaceの二重開始抑止を確認する。

P0-1/2が完了するまで、Bridge・Scheduler・UIの実装はこの結果を越える互換性を前提にしない。
