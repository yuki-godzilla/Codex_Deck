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
| App Server強制終了 | 実行中Turn開始後に`SIGTERM`で終了。検証クライアントは`turn/start`を1回だけ送信し、再送・二重Turnを発生させなかった | 条件付合格。 |
| App Server再起動後の読取 | 新しいstdio接続で同じ使い捨てworkspaceの既存Thread一覧を取得し、`thread/read`と`thread/resume`を再確認。前回Turnの自動再実行は行わなかった | 条件付合格。強制終了した特定Turnの実行中状態を公式に復帰できるかは未確認。 |

### 4.1 Deck Approval Broker実機結合

`tools/poc/live_approval_broker.py`で、Deckの`StdioJsonRpcTransport`、`ApprovalTransportBinding`、`ApprovalBroker`、SQLite監査storeを実App Serverへ結合した。既存workspaceをcwdにするだけで、書込みを許可せずに実施した。

| 確認項目 | 観測結果 | 判定 |
| --- | --- | --- |
| command approval受信 | `untrusted` / `workspace-write`で発生した`item/commandExecution/requestApproval`をBrokerが1件だけ保留 | 合格 |
| 同一request IDへの`decline` | Brokerの保留IDとtransportへの応答IDが一致し、公式`decline`を送信 | 合格 |
| 最小監査ログ | Deck専用の一時SQLiteに、同一request ID、種別、`decline`、時刻だけを記録。command/cwd/reason本文は保存しない | 合格 |
| App Server障害中の承認 | 承認保留中にApp Serverを終了。保留は残り、監査0件、決定・再送なし | 合格 |

このPoCは「障害時に自動決定・自動再送しない」ことを確認したものである。障害検知、UIへの中断表示、利用者が復旧後に改めて操作する導線はPoC-3/実行状態実装の残件である。

Thread IDとTurn IDは保存せず、それぞれのハッシュ先頭12文字だけを検証時に確認した。App Server stderrは2行出力されたが、内容は証跡へ保存していない。

## 5. P0-2 セッション共有・並行実行

CLI起点のread-only Threadを、別App Server接続の`thread/read`でID指定して読めた。一方、同じcwdを指定した`thread/list`は0件を返した。したがってCLIとApp Serverの完全な一覧共有は保証できず、ID既知のThread読取と一覧検出を同一の互換性として扱わない。

空の使い捨てworkspace A/Bに対する2本のread-only Turnを同時に実行し、両方で`thread/read`と`thread/resume`が成功した。Thread/Turnのハッシュは相互に異なり、通知種別は一致し、承認要求は発生しなかった。同じ検証を**同一workspace**へ同時に2本起動しても、両Turnは別Thread/Turnとして完了した。よって、App Serverが並行起動を許容しても、Deckは`1 workspace = 1 Active work`をSchedulerの論理排他として必ず強制する。

再実行には`tools/poc/parallel-app-server-harness.mjs`を使用する。このランナーは絶対パスの使い捨てworkspaceを2件以上受け取り、各App Server harnessの結果を、IDや会話本文を含まない集約値だけにして出力する。

VS Code起点は、導入済みのVS Code 1.128.0と`openai.chatgpt@26.707.41301`で実施可能な状態を確認し、[専用手順](CODEX_DECK_VSCODE_POC_RUNBOOK.md)を追加した。Thread開始はVS Code UI操作を必要とするため、結果は未判定である。複数App Serverの読み取り専用Turn、同一workspaceの二重開始、workspace A/B並行は確認済みだが、同一Thread競合、同一承認競合、ファイル変更を伴う並行実行は未検証である。

判定は**条件付合格**とする。読み取り専用の別workspace並行は実行できたが、Deckは、P0-2の残検証が完了するまでCLI/VS CodeとのThread共有やファイル変更を伴う別workspace並行を保証しない。同一workspace 1 Active workの設計前提を維持する。

## 6. 次の実施順

1. VS Code起点のThreadをApp Serverから読めるかを確認する。
2. 同一Threadの閲覧・追加指示・停止・承認の競合を、先後関係を変えて3回ずつ確認する。
3. workspace A/Bでファイル変更・承認を伴う並行実行が混線しないかを確認する。
4. Deck Schedulerのworkspace lockが、同一workspaceの2本目を開始前に拒否することを自動テストで確認する。

P0-1/2が完了するまで、Bridge・Scheduler・UIの実装はこの結果を越える互換性を前提にしない。
