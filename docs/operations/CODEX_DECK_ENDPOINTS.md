# Codex Deck 接続境界

Codex DeckはSMAIとプロセス、ポート、公開URL、DB、ログを共有しない。本書は開発・運用で使うDeck固有の名前空間を固定する。

## 確定した名前空間

| 区分 | Codex Deck | 用途 |
| --- | --- | --- |
| 開発UI | `http://127.0.0.1:43173` | Vite開発サーバー。`/api`と`/healthz`はDeck APIへproxyする。 |
| 開発API | `http://127.0.0.1:43174` | FastAPI。既定ではloopbackのみで待受する。 |
| 外部URL | `https://codex-deck.<tailnet-name>.ts.net` | Tailscale内だけで使う正規originの形式。実際のtailnet名は個人設定にのみ保持する。 |
| Tailscale端末名 | `codex-deck` | SMAIの端末名・Serve設定とは別に管理する。 |
| App Server | stdio | TCP/WS listenerを公開しない。Deck Bridgeだけが子プロセスとして接続する。 |

確認時点でSMAIは主に`8000`、`8088`、`8501`を使用している。Deckはこれらを予約・参照・proxyしない。

## 設定方法

`.env.example`を参考に、個人環境だけに`.env`または環境変数を設定する。`CODEX_DECK_BIND_HOST`の既定は`127.0.0.1`であり、FastAPIを直接tailnetやLANへ公開しない。外部公開は、Tailscale認証を前提としたリバースプロキシで`CODEX_DECK_PUBLIC_ORIGIN`へ集約する。

データベースとログはDeck専用のデータディレクトリに置き、SMAIのDB・ログ・通知topic・launcherへは接続しない。具体的な端末固有パス、tailnet名、認証情報はリポジトリへ記録しない。

## 運用上の制約

- `43173`/`43174`を他サービスが利用中なら、両方をDeck専用の未使用値へ同時に変更し、UI proxyと起動引数を一致させる。
- App Serverの`--listen`や実験的WebSocketを外部入口として設定しない。
- Tailscale Serve、TLS、identity header、端末sessionは認証PoCで別途検証する。ここで決めたURL形式は認証済みであることを意味しない。
