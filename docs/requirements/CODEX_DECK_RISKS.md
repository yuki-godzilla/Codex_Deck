# Codex Deck リスク一覧

## 1. 文書情報

| 項目 | 内容 |
| --- | --- |
| 対象 | Codex Deckの実装前・MVP運用前に管理する技術、運用、セキュリティリスク |
| 評価 | 影響度・発生可能性は 高 / 中 / 低。残余リスクは対策後の見込み。 |
| 関連 | [要件定義書](CODEX_DECK_REQUIREMENTS.md)、[公式機能調査](../research/CODEX_OFFICIAL_CAPABILITY_RESEARCH.md)、[PoC計画](../poc/CODEX_DECK_POC_PLAN.md) |

## 2. リスク登録簿

| ID | リスク | 影響 | 可能性 | 早期兆候 | 予防・低減策 | 発生時対応 | 所有者 / ゲート | 残余 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R-01 | Codex App Serverの仕様・schemaが更新で変わる | 高 | 中 | JSON-RPC unknown method/field、schema diff、CLI更新 | CLI versionを記録し、`generate-ts`/`generate-json-schema`の差分を更新ゲートにする。未知Itemを安全に保存する。 | 互換性モードで危険操作を止め、Bridge adapterを更新し契約テストする。 | 技術責任者 / PoC-0 | 中 |
| R-02 | CLI・VS Code・Deck間でThreadを共有できない、または一部しか共有できない | 高 | 中 | `thread/list`に他表面起点Threadが出ない、cwd/履歴が一致しない | 正本はCodexに置き、ファイル走査や独自会話移植をしない。表面ごとにPoCする。 | Deck起点Threadの利用に限定し、外部起点は未検出として明示する。 | 技術責任者 / PoC-2 | 中 |
| R-03 | 複数クライアントの承認、追加指示、停止が競合する | 高 | 中 | 二重response、state不一致、`serverRequest/resolved`前の再送 | request ID/Thread/Turnを必須にし、同一pending requestの二重操作をローカルで防止する。 | 最新snapshotを取得し、最初に確定した公式decisionを監査ログへ残す。必要なら他クライアントをread-onlyにする。 | Bridge/Scheduler / PoC-2 | 中 |
| R-04 | 別workspaceの並行実行がcwd、イベント、Codex stateを混線させる | 高 | 中 | 異なるworkspaceで誤ったファイル変更、Thread lockの不整合 | workspace lock、worker識別、cwd検証、使い捨てworkspaceで並行PoCを行う。 | 並行を停止し、単一worker設計または公式に安全なworker分離へ見直す。 | Scheduler / PoC-2 | 低〜中 |
| R-05 | App Server/WebSocketを直接外部公開して無認証アクセス・token漏えいが起きる | 致命的 | 中 | non-loopback listener、raw tokenをCLI引数に渡す、Originなし外部アクセス | App Serverはstdio/localhostに閉じる。Tailscale上へはDeckだけをHTTPS/WSSで公開し、secretはfile/env経由にする。 | listener停止、token無効化、監査ログ確認、端末session失効。 | セキュリティ担当 / 設計レビュー | 低 |
| R-06 | フルアクセス/承認ミスにより破壊的操作やsecret露出が起きる | 致命的 | 中 | `danger-full-access`表示不十分、承認内容が省略、secret scanner hit | 公式承認decisionを改変せず対象/理由/cwd/hostを明示。フルアクセスbadge、イベント/ログ/通知マスク、deny readを実装。 | Turnを停止、token rotation・影響調査、必要に応じworkspace隔離。 | セキュリティ担当 / PoC-1 | 中 |
| R-07 | Webのファイル閲覧から`.env`、SSH key、credential等を露出する | 高 | 中 | deny対象へのpath request、symlink越境、binary download | 許可root、deny/maskリスト、symlink解決後のroot判定、ダウンロード制限、監査ログ。 | 当該閲覧を停止、ログ/キャッシュ/通知を確認・削除、秘密情報を必要に応じ更新。 | File Adapter / セキュリティレビュー | 低〜中 |
| R-08 | iOS/iPadOS PWAのbackground、push、WebSocket、clipboardが期待どおり動かない | 中 | 高 | 長時間background後のsocket切断、push permission拒否、keyboard overlap | アプリ内通知を必須にし、PWA push/ntfyをadapter化。event replay/snapshot復帰、実端末PoC。 | PWA pushを条件付にし、ntfy/アプリ内通知へfallback。UIをSafari制約に合わせる。 | フロントエンド / PoC-4 | 中 |
| R-09 | ブラウザ/App Server切断でイベント欠落、重複、二重送信が起きる | 高 | 中 | gap、重複card、同じTurnが2回起動 | Deck event ID、outbox、idempotency key、backoff+jitter、snapshot再同期を設計する。 | event replay停止、Thread snapshotを正として再構築し、二重操作を監査する。 | Bridge / PoC-3 | 低〜中 |
| R-10 | Windowsプロセス管理・sandbox・Codex認証がタスクスケジューラ/サービスで不整合になる | 高 | 中 | 起動後のlogin failure、sandbox 1385、user config未読、再起動loop | ユーザーコンテキストのタスクスケジューラをMVP推奨にし、service account化は別PoC。PID/exit code/healthを監視。 | 手動起動依存に戻さず、launcher/権限/sandboxを診断し、必要ならservice化を延期。 | 運用担当 / PoC-5 | 中 |
| R-11 | Windows再起動・App Server異常終了後に作業が二重実行される | 致命的 | 中 | startup時の自動prompt再送、同じGit操作/コマンドが再実行 | Active workを「中断」にし、復旧はログ/Thread確認後の明示操作だけにする。 | 自動replayを直ちに停止、Git/logを調査、影響範囲を通知。 | Scheduler / PoC-3,5 | 低 |
| R-12 | 大規模ログ・巨大diff・大量ファイルでモバイル/ブラウザが操作不能になる | 中 | 高 | 長時間main-thread block、memory増大、scroll不能 | lazy tree、chunk取得、virtual scroll、diff折畳み、server-side search、保持上限を採用。 | 詳細表示を遅延し、priority channelで承認/停止を維持。閾値を設定で調整。 | Frontend/Backend / PoC-6 | 低〜中 |
| R-13 | Git状態のpollingが負荷を増やす、または表示が古くなる | 中 | 中 | CPU/IO増、status差分とUI差異 | Codex file/Git Itemを優先し、debounce/poll間隔/visibilityで制御。repo規模別に計測。 | 手動refreshとstale表示へfallbackし、監視頻度を下げる。 | Git Adapter / PoC-6 | 低 |
| R-14 | テスト結果parserが誤判定し、失敗/成功を偽って表示する | 中 | 中 | summaryと原ログ/exit codeの不一致 | exit codeと生ログを正本にし、parserは明示的に「検出結果」と扱う。fixturesで検証。 | parserを無効化し一般ログ表示へ退避、誤表示を修正する。 | Execution UI / PoC-1,6 | 低 |
| R-15 | 通知の重複、欠落、秘密情報混入が起きる | 高 | 中 | 同一eventの複数配送、通知本文のsecret hit、delivery error | event fingerprint、quiet hours、channel別mask、delivery audit、最小本文を採用。 | 通知channelを停止、履歴を確認、secret rotationが必要なら実施。 | Notification Adapter / PoC-3,4 | 低〜中 |
| R-16 | Tailscale障害/端末紛失で遠隔アクセス不能または不正アクセスとなる | 高 | 低〜中 | tailnet auth failure、未知端末、長期session | Deckの端末登録/短期session/失効、Tailscaleに依存しないローカル管理経路、監査ログ。 | 端末/セッションを失効、ローカルから認証を再構成、通知。 | セキュリティ担当 / 認証PoC | 中 |
| R-17 | モバイル画面が情報過多で承認・エラー・状態を見逃す | 中 | 高 | 承認未応答、重要bannerがscroll外、誤タップ | 1カラム、Attention rail、bottom badge、stateの優先順位、ログの折畳み、実端末UXレビュー。 | 文言/優先度/レイアウトを改訂し、重要actionの二重確認を追加。 | UX担当 / PoC-4,6 | 低〜中 |
| R-18 | SMAIとプロセス/DB/設定/ntfyを共有し、障害が相互波及する | 高 | 中 | port/DB/log directory共通、更新時の同時停止 | 別repo、venv、service、port、SQLite、log、launcher、notification configを必須とする。 | 共有資産を分離、両サービスのstateを独立復旧する。 | 運用担当 / 設計レビュー | 低 |
| R-19 | Codex更新でCLI/IDE/App Serverの表示・アクセスモードが変わる | 高 | 中 | version変更、利用可能profile/approvalの差異 | version pin/compatibility matrix/schema diff、update前backup/health/PoC、UIは実返却値を列挙。 | updateをrollbackし、互換adapter/文書を更新してから再開。 | 技術責任者 / 更新手順 | 中 |

## 3. リスク別のMVP制約

| 制約 | 対応するリスク | 意味 |
| --- | --- | --- |
| App Serverの外部WebSocket公開を禁止 | R-01, R-05 | stdio Bridgeを唯一のMVP接続経路とする。 |
| 1 workspace 1 Active work | R-03, R-04, R-11 | 同一workspaceの並行Turnによりcwd/変更/承認が競合するのを防ぐ。 |
| 汎用Webシェルを対象外 | R-05, R-06, R-14 | Codexが実行した作業だけを観測・承認する。 |
| 人間の直接Web編集を対象外 | R-06, R-07, R-17 | 編集競合・誤保存・権限誤認を増やさない。 |
| OS再起動後の自動再実行を禁止 | R-04, R-11 | 冪等でない依頼、Git操作、破壊的コマンドの再実行を避ける。 |
| スマホはインラインdiff | R-12, R-17 | 可読性と誤操作防止を優先する。 |
| Parser失敗時は生ログへ退避 | R-14 | 構造化表示の便利さより事実性を優先する。 |
| Deck DBは補助情報のみ | R-01, R-02, R-11 | Codex Thread正本の分岐・破損を防ぐ。 |

## 4. 監視指標と閾値

| 指標 | 警戒 | 重大 | 初動 |
| --- | --- | --- | --- |
| Bridge再起動回数 | 1時間に3回 | 1時間に5回以上 | 新規Turn開始を警告し、App Server/CLI/Windows logを確認。 |
| event replay gap | 1 Threadで1回 | snapshotでも整合しない | Threadを再同期中にし、重複操作を止める。 |
| approval待機 | 10分 | 30分またはTurn timeout接近 | 通知再送（重複抑止付き）し、利用者へ対象を表示。 |
| backend CPU/memory | 10分継続で基準超過 | 応答不能/OS pressure | 大量log/diffをthrottle、診断ログ保存。 |
| SQLite/log容量 | 80% | 90% | ローテーション、古いDeckログを削除、Codex正本を削除しない。 |
| notification失敗率 | 15分で10% | 15分で50% | channel障害として表示、アプリ内通知へfallback。 |
| secret detector | 1件 | 認証情報らしき高確度1件 | 表示/配送を止め、マスク、監査、必要ならsecret rotation。 |

## 5. リスクレビューの運用

- PoC終了時、CLI/IDE更新時、認証/通知/ファイル閲覧の変更時、Windows運用方式を変更する時に登録簿を見直す。
- 新規の高影響リスクは、実装と同じ変更に隠さず、所有者、検知方法、fail-safe、受入条件を追記する。
- 「未確認」はリスク消滅ではない。PoC結果が得られるまでUIの保証文言を強くしない。
- 機密情報が含まれ得るログ・画面・通知の証跡は、本文へ貼らず、マスク済み診断IDで参照する。
