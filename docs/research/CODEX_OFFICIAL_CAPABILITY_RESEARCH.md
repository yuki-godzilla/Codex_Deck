# Codex公式機能調査結果

## 1. 文書情報

| 項目 | 内容 |
| --- | --- |
| 対象 | Codex Deck の要件定義・PoC準備 |
| 調査日 | 2026-07-13 (JST) |
| 調査対象CLI | `codex-cli 0.144.1`（このWindows PCで確認） |
| 調査対象IDE拡張 | VS Code `openai.chatgpt 26.707.41301`（このPCで確認） |
| VS Code | 1.128.0（このPCで確認） |
| 調査方針 | OpenAI公式ドキュメント、インストール済みCodex CLIのヘルプを一次情報とし、未検証事項を推測で補わない。 |
| 判定記号 | **確認済み**: 公式仕様または実行環境で確認 / **PoC必要**: 公式APIはあるが組合せ・実運用が未検証 / **未確認**: 公式仕様で保証を確認できない。 |

本書は実装仕様の固定ではない。Codexの更新に追従するため、実装開始前とCLI更新時に再調査し、`codex app-server generate-ts` または `generate-json-schema` で対象バージョンの契約を生成して差分確認する。

## 2. 結論

Codex Deckは、Codex App Serverを利用する公式クライアント統合として成立する。App Serverはスレッド、ターン、承認、ストリーミングイベントをカスタムクライアント向けに提供している。

ただし、App Serverの直接WebSocket公開は実験的かつ未サポートである。したがって、初期構成ではApp ServerをWindows PC内の標準入出力（JSONL）に閉じ、Codex Deckバックエンドのみが子プロセスとして接続する。モバイルブラウザへ公開するのは、Tailscale配下で認証・認可・再接続制御を行うCodex DeckのHTTPS/WSS入口とする。

CLI、VS Code拡張、App Serverのセッション相互可視性や、同一実行中スレッドを複数クライアントが同時操作する挙動は、公式ページだけでは保証範囲を確定できない。これらはMVP開始ゲートとなるPoCで検証する。

## 3. 公式参照先

| ID | 一次情報 | 主な確認対象 |
| --- | --- | --- |
| O-01 | [Codex App Server](https://learn.chatgpt.com/docs/app-server) | App Serverの目的、JSON-RPC、スレッド/ターン、イベント、承認、生成可能なスキーマ |
| O-02 | [Codex App Server - Protocol](https://learn.chatgpt.com/docs/app-server#protocol) | stdio、WebSocket、Unix socket、health probe、WebSocket認証 |
| O-03 | [Codex App Server - Lifecycle overview](https://learn.chatgpt.com/docs/app-server#lifecycle-overview) | 初期化、start/resume/fork、steer、interrupt、完了イベント |
| O-04 | [Codex App Server - Approvals](https://learn.chatgpt.com/docs/app-server#approvals) | コマンド・ファイル変更承認、応答種別、ネットワーク承認 |
| O-05 | [Codex Config basics](https://learn.chatgpt.com/docs/config-file/config-basic) | CLI/IDE共通設定、設定優先順位、permission profile |
| O-06 | [Codex Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference) | `approval_policy`、`sandbox_mode`、MCP、ログ、SQLite state DB |
| O-07 | [Codex Advanced config - History persistence](https://learn.chatgpt.com/docs/config-file/config-advanced#history-persistence) | ローカル履歴保存と容量上限 |
| O-08 | [Custom instructions with AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md) | `AGENTS.md`探索順、継承、上限 |
| O-09 | [Windows sandbox](https://learn.chatgpt.com/docs/windows/windows-sandbox) | Windows native sandbox、OS要件、elevated/unelevated |

ローカル確認として、2026-07-13に `codex --version`、`codex app-server --help`、`code --version`、`code --list-extensions --show-versions` を実行した。認証情報、個人設定、既存セッション本文は確認対象に含めていない。

## 4. Codex App Server

### 4.1 確認済みの基本契約

| 項目 | 判定 | 確認内容 | Codex Deckへの要件化 |
| --- | --- | --- | --- |
| 起動 | 確認済み | `codex app-server`。この環境のヘルプでは `--listen`、WebSocket認証、`generate-ts`、`generate-json-schema` を確認。 | バックエンドはCodex CLI子プロセスとして起動・監視する。 |
| 既定通信 | 確認済み | `stdio://` が既定。改行区切りJSON（JSONL）。 | App ServerとDeck Bridge間はstdioのみをMVPの正規経路とする。 |
| プロトコル | 確認済み | 双方向JSON-RPC 2.0。wire上では`jsonrpc: "2.0"`ヘッダを省略する。 | バージョン固有の生成スキーマを使用し、独自の推測DTOを正本にしない。 |
| WebSocket | 確認済み | 1フレーム1 JSON-RPCメッセージ。ただし実験的・未サポート。非loopbackでは認証設定が必要。 | App Serverをモバイルへ直接公開しない。採用する場合は将来のPoCとセキュリティ再審査を必須とする。 |
| Unix socket | 確認済み | WebSocket接続をUnix socket上で提供。 | Windows MVPの依存経路にしない。 |
| Health probe | 確認済み | WebSocket listenerでは`/readyz`と`/healthz`を提供。Origin付き`/healthz`は403。 | stdio構成ではDeck Bridge自身がreadiness/livenessを提供する。WebSocket採用時のみ補助利用する。 |
| 初期化 | 確認済み | 各接続で`initialize`の後に`initialized`が必須。前の要求は拒否される。 | Bridgeの接続状態機械にhandshake失敗・再初期化を実装する。 |
| コア概念 | 確認済み | Thread（会話）、Turn（1依頼と作業）、Item（発言、コマンド、ファイル変更等）。 | UIは公式用語を基本にし、Deck独自会話IDを正本にしない。 |
| 新規・再開・分岐 | 確認済み | `thread/start`、`thread/resume`、`thread/fork`。 | MVPで新規/再開、分岐はUI露出前にPoCで検証する。 |
| 一覧・読取・アーカイブ | 確認済み | `thread/list`、`thread/read`、`thread/archive`、`thread/unarchive`、`thread/delete`。 | 一覧・検索・アーカイブ相当を公式APIの範囲で実装する。削除はMVP対象外。 |
| 実行開始・追加指示・停止 | 確認済み | `turn/start`、実行中ターンへ`turn/steer`、`turn/interrupt`。終了時は`turn/completed`。 | 追加指示は`turn/steer`の公式意味に限定する。キューUIはPoCで実際の挙動を確認するまで確定しない。 |
| ストリーミング | 確認済み | `item/started`、`item/completed`、`item/agentMessage/delta`、tool progress、`turn/completed`等の通知。 | 受信順にイベントログへ永続化し、ブラウザへ再配信する。内部思考を表示対象にしない。 |
| 状態取得 | 確認済み | `thread/read`/`thread/list`の返却Threadにruntime `status`、`thread/status/changed`通知。 | Deckの表示状態は公式イベント/状態から導出し、独自状態は接続状態等のUI補助だけに限定する。 |
| コマンド出力 | 確認済み | App Serverには`command/exec`系のAPIもあるが、これはスレッド/ターンを開始しない単体コマンド実行。 | 初期リリースのDeckはこのAPIを自由ターミナル用途に使わない。Codexが実行したItemのみを表示する。 |
| バックグラウンド端末 | 確認済み（実験的） | `thread/backgroundTerminals/*`はexperimental API。 | 表示・停止をMVPの保証機能に含めず、PoCの結果により段階導入する。 |

### 4.2 承認の公式契約

| 種別 | 判定 | 公式の流れ | Deckの扱い |
| --- | --- | --- | --- |
| コマンド実行承認 | 確認済み | `item/commandExecution/requestApproval`を受信し、`accept`、`acceptForSession`、`decline`、`cancel`、またはexecpolicy改定の決定で応答する。 | 公式の決定肢をそのまま表示する。Deck独自の承認規則を追加しない。 |
| ファイル変更承認 | 確認済み | `item/fileChange/requestApproval`を受信し、`accept`、`acceptForSession`、`decline`、`cancel`で応答する。 | 変更内容・理由・対象スレッド/ターンを表示して公式決定を送る。 |
| ネットワーク承認 | 確認済み | `networkApprovalContext`がある場合はhost/protocolを含むネットワーク固有の承認。 | シェルコマンドの一般承認と誤認させず、宛先を明示する。 |
| スコープ付き権限 | 確認済み | `request_permissions`はturnまたはsession scopeで要求された部分集合のみ許可可能。 | 公式提供時のみ表示する。Deckは権限範囲を拡張しない。 |
| MCP/フォーム要求 | 確認済み | `mcpServer/elicitation/request`等のサーバー要求があり得る。 | 初期は専用画面を作らず、互換性のある標準確認UIとして扱う。複雑なフォームはPoC後にMVP可否を決める。 |

### 4.3 App Serverの未保証・検証対象

| 項目 | 判定 | 理由と必要なPoC |
| --- | --- | --- |
| CLI、VS Code、App Serverのセッションを同一一覧で相互に読めること | PoC必要 | 公式には各表面でThread/Sessionがあるが、全表面・同一`CODEX_HOME`・同一workspaceでの相互可視性を保証する記述を確認できていない。 |
| 実行中Threadの複数クライアント同時閲覧・同時操作 | PoC必要 | `thread/unsubscribe`とsubscriptionの説明はあるが、競合時の排他、最後の承認者、追加指示の順序は未保証。 |
| App Server再起動後に実行中Turnへ復帰できること | PoC必要 | 保存済みThread再開と、実行中Turn/子プロセスの再接続は別問題である。 |
| イベントの再送、連番、欠落補完 | 未確認 | 公式にDeck用のイベント再送cursor契約を確認できない。Deckが永続イベントアウトボックスとsnapshot再取得を持つ必要がある。 |
| WebSocketの安定運用 | 未確認（推奨しない） | 公式にexperimental and unsupportedと明記されている。 |
| ファイル差分・テスト結果の専用イベントを全て受けられること | PoC必要 | Item種別は豊富だが、Codexバージョン・操作・サーフェスごとの粒度を実機で確認する必要がある。 |

## 5. Codex CLI・設定・Windows

### 5.1 確認済み事項

| 項目 | 判定 | 確認内容 | Deckへの影響 |
| --- | --- | --- | --- |
| ローカル履歴 | 確認済み | 既定で`CODEX_HOME`配下（例: `~/.codex/history.jsonl`）へ保存。`history.persistence = "none"`で無効化、`history.max_bytes`で容量上限。 | Deckは履歴ファイルを独自編集しない。App ServerのThread APIを優先する。 |
| ユーザー設定 | 確認済み | `~/.codex/config.toml`、信頼済みprojectの`.codex/config.toml`、profile、CLI flagに優先順位がある。 | セッション開始時はCodexの有効設定を尊重し、Deck設定で上書きする項目を明示・最小化する。 |
| CLI/IDE設定共有 | 確認済み | CLIとIDE拡張は同じ設定レイヤーを共有する。 | sandbox、approval、MCPなどのCodex設定をDeck独自設定へ複製しない。 |
| approval policy | 確認済み | `untrusted`、`on-request`、`never`、granular設定がある。 | UIの表示値・説明は起動時の実際のCodex返却値を正とする。 |
| sandbox mode | 確認済み | `read-only`、`workspace-write`、`danger-full-access`。workspace-writeのネットワーク可否も設定可能。 | 「読み取り専用」「ワークスペース」「フルアクセス」は説明用ラベルとし、実値は公式値を送受信する。 |
| permission profile | 確認済み | built-inは`:read-only`、`:workspace`、`:danger-full-access`。 | 利用可能プロファイルをAPIで列挙できる場合にだけ選択肢として表示する。 |
| MCP | 確認済み | `mcp_servers`をconfigで設定でき、CLI/IDEで利用可能。 | DeckはMCP設定を新設しない。現在有効なCodex設定・承認に従う。 |
| AGENTS.md | 確認済み | global→project root→cwdの順に読み、近いファイルが後勝ち。`AGENTS.override.md`優先、既定32KiB上限。 | workspaceの`cwd`を正確に渡し、Deck独自の指示ロード方式を作らない。 |
| Windows native sandbox | 確認済み | `elevated`（推奨）と`unelevated`（fallback）。Windows 11推奨、更新済みWindows 10はbest effort。 | Windowsサービス化前に、実行アカウントとsandboxセットアップ権限をPoCする。 |
| CLI更新 | 確認済み | この環境のCLIには`codex update`コマンドがあり、開始時更新確認設定もある。 | 更新はDeckを停止し、schema再生成・互換テスト・ロールバック確認を伴う運用手順にする。 |

### 5.2 未確認事項

| 項目 | 判定 | 対応 |
| --- | --- | --- |
| 保存済みinteractive sessionの正確な物理配置・複数プロセス同時アクセス安全性 | PoC必要 | ファイル形式・ディレクトリに依存せず、App Server APIを正規経路とする。 |
| 実行中CLIターンへの外部追加指示の見え方 | PoC必要 | `turn/steer`とCLI UIの整合、再送、停止時の扱いを検証する。 |
| Windowsサービスアカウントで既存Codexログイン・設定を安全に利用できること | PoC必要 | ユーザーアカウントでのタスクスケジューラ運用を第一候補とし、サービスアカウントは後続検証とする。 |

## 6. VS Code Codex拡張

| 項目 | 判定 | 確認内容・制約 |
| --- | --- | --- |
| 現在の導入状況 | 確認済み | このPCでは`openai.chatgpt 26.707.41301`を確認。 |
| App Server利用 | 確認済み | App Server公式文書はVS Code拡張をrich clientの例として明示し、初期化例に`codex_vscode`を示す。 |
| 設定共有 | 確認済み | Config basicsはCLIとIDE extensionが設定レイヤーを共有すると明記。 |
| セッション一覧、workspace連携、実行表示、差分、行リンク、承認UIの正確な画面動作 | PoC必要 | 公式のIDE landing pageだけでは、拡張バージョンごとのUI挙動・相互運用保証を十分に確認できない。実機観察とApp Serverログで検証する。 |
| CLIとIDEが同一Threadを同時に操作できること | PoC必要 | 公式の共有設定は確認済みだが、Thread相互操作は別の保証である。 |

## 7. 実装時の互換性ルール

1. `codex-cli 0.144.1`で調査したAPI名・Item種別を、将来の固定契約として扱わない。
2. Deck Bridgeは起動時にCLIバージョンと生成スキーマのバージョンを記録し、許容済み範囲外なら危険操作を開始しない。
3. experimental API、experimental capability、WebSocket listenerはMVPの必須経路にしない。
4. App Serverの未知Itemは破棄せず、「未対応イベント」として安全にログ保存・UI表示する。イベント本文の秘密情報マスクを先に通す。
5. Codex公式機能で満たせない表示・再接続・通知だけをDeck補助機能で補い、Thread、Turn、承認判断、sandbox、MCPの正本をDeckへ複製しない。

## 8. 要件への反映

| 調査結果 | 要件上の決定 |
| --- | --- |
| stdioが既定、WebSocketは実験的 | App Serverはlocalhost/stdioに閉じる。外部WebSocketはDeckバックエンドが提供する。 |
| Thread/Turn/Itemが公式モデル | 「セッション」はUIではThreadを指す。DBは補助メタデータとイベント受信位置だけを保存する。 |
| 承認はserver requestと公式decisionで処理 | Deck独自の承認モデルを禁止し、原文・理由・scopeを表示する。 |
| `turn/steer`/`turn/interrupt`がある | 追加指示・停止を公式呼出しに対応付ける。ただし競合・キューのUXはPoCで確定する。 |
| Windows native sandboxがある | Windows 11を推奨基準とし、Codex実行アカウントとsandboxを同時に運用検証する。 |

## 9. 次の調査・PoC優先順位

1. **P0: App Serverのstdio接続、承認、Itemイベント、停止** — Codex Deckの中核成立性。
2. **P0: 同一`CODEX_HOME`でCLI/VS Code/App Server間のThread相互運用** — セッション正本方針の成立性。
3. **P0: workspace別の同時Turnと1 workspace 1 active turnの排他** — 必須同時実行要件。
4. **P1: ブラウザ切断・App Server再起動・Windows再起動からの復旧** — バックグラウンド継続と安全な中断復元。
5. **P1: iOS/iPadOS PWAの通知・復帰・WebSocket再同期** — モバイルファーストの成立性。
6. **P1: Smart_Market_AI規模のファイル・diff・pytestログ** — 性能と情報過多対策。
