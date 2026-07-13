import { FormEvent, useEffect, useRef, useState } from "react";
import { DeckEvent, ActiveWork, eventStreamUrl, getActiveWork, startWork } from "./api";

const workspaceId = "demo";
const navItems = ["会話", "作業", "差分", "ファイル", "実行"] as const;
type Tab = (typeof navItems)[number];

function displayState(work: ActiveWork | null): string {
  if (!work) return "待機中";
  return work.state === "running" ? "実行中" : work.state;
}

function App() {
  const [activeTab, setActiveTab] = useState<Tab>("会話");
  const [work, setWork] = useState<ActiveWork | null>(null);
  const [events, setEvents] = useState<DeckEvent[]>([]);
  const [draft, setDraft] = useState("");
  const [connection, setConnection] = useState("接続中");
  const [notice, setNotice] = useState("Codexは未接続です。デモBackendでは安全なfake App Serverを使用します。");
  const cursor = useRef(0);

  useEffect(() => {
    let cancelled = false;
    getActiveWork(workspaceId)
      .then((result) => { if (!cancelled) setWork(result); })
      .catch(() => { if (!cancelled) setConnection("Backend切断"); });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    const socket = new WebSocket(eventStreamUrl(workspaceId, cursor.current));
    socket.onopen = () => setConnection("同期中");
    socket.onmessage = (message) => {
      const event = JSON.parse(message.data) as DeckEvent;
      cursor.current = Math.max(cursor.current, event.event_id);
      setEvents((current) => [...current.filter((item) => item.event_id !== event.event_id), event]);
      setConnection("接続中");
    };
    socket.onerror = () => setConnection("Backend切断");
    socket.onclose = () => setConnection("再接続待ち");
    return () => socket.close();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft.trim()) return;
    try {
      const started = await startWork(workspaceId, draft);
      setWork(started);
      setNotice("作業を開始しました。Codexの正本イベントを受信するまで状態を推測しません。");
      setDraft("");
      setActiveTab("作業");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "送信できませんでした。");
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">CODEX DECK / DEMO WORKSPACE</p>
          <h1>Codex作業を、どこからでも安全に確認</h1>
        </div>
        <div className="connection" aria-live="polite"><span className="status-dot" />{connection}</div>
      </header>

      <section className="attention" aria-label="現在の状態">
        <div><strong>{displayState(work)}</strong><span>{work ? "このworkspaceには1件のActive workがあります。" : "開始できる作業はありません。"}</span></div>
        <span className="read-only">読み取り専用レビュー</span>
      </section>

      <div className="desktop-layout">
        <aside className="workspace-rail">
          <p className="section-label">WORKSPACE</p>
          <button className="workspace current" type="button"><span>●</span>Demo workspace <small>Active</small></button>
          <button className="workspace" type="button" disabled>＋ workspace追加（準備中）</button>
          <p className="section-label">SESSION</p>
          <button className="session" type="button">現在のThread <small>{work?.thread_id ?? "未開始"}</small></button>
        </aside>

        <section className="content-panel" aria-label="Codex作業">
          <div className="mobile-tabs" role="tablist" aria-label="作業領域">
            {navItems.map((item) => <button key={item} type="button" role="tab" aria-selected={activeTab === item} className={activeTab === item ? "selected" : ""} onClick={() => setActiveTab(item)}>{item}</button>)}
          </div>
          <Content activeTab={activeTab} events={events} work={work} />
        </section>

        <aside className="activity-panel">
          <p className="section-label">STATUS</p>
          <dl>
            <div><dt>Active work</dt><dd>{displayState(work)}</dd></div>
            <div><dt>Thread</dt><dd>{work?.thread_id ?? "—"}</dd></div>
            <div><dt>Turn</dt><dd>{work?.turn_id ?? "—"}</dd></div>
          </dl>
          <div className="notice" role="status">{notice}</div>
        </aside>
      </div>

      <form className="composer" onSubmit={handleSubmit}>
        <label htmlFor="request">Codexへの依頼 <span>未送信の下書き</span></label>
        <div>
          <textarea id="request" rows={3} value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="何を確認・実装したいかを入力" />
          <button type="submit" disabled={Boolean(work) || !draft.trim()}>作業を開始</button>
        </div>
        {work && <p>進行中の作業があるため、新規開始はできません。追加指示・停止はPoC完了後に有効化します。</p>}
      </form>

      <nav className="bottom-nav" aria-label="モバイルナビゲーション">
        {navItems.map((item) => <button key={item} type="button" className={activeTab === item ? "selected" : ""} onClick={() => setActiveTab(item)}>{item}</button>)}
      </nav>
    </main>
  );
}

function Content({ activeTab, events, work }: { activeTab: Tab; events: DeckEvent[]; work: ActiveWork | null }) {
  if (activeTab === "会話") return <section className="conversation"><p className="section-label">CONVERSATION</p><h2>安全な作業の入口</h2><p>依頼はCodexのThreadとTurnへ送信されます。Deckは会話本文を独自の正本として保存しません。</p><div className="empty">{work ? "作業開始済みです。明示発言はApp Serverから届いたものだけをここに表示します。" : "下のcomposerから、read-only sandboxの安全な依頼を開始できます。"}</div></section>;
  if (activeTab === "作業") return <section><p className="section-label">ACTIVITY</p><h2>作業イベント</h2>{events.length ? <ol className="timeline">{events.map((event) => <li key={event.event_id}><strong>{event.event_type}</strong><span>event #{event.event_id} / {new Date(event.received_at).toLocaleTimeString("ja-JP")}</span></li>)}</ol> : <div className="empty">まだDeck eventはありません。開始後に受信順で表示します。</div>}</section>;
  return <section><p className="section-label">{activeTab.toUpperCase()}</p><h2>{activeTab}は準備中です</h2><div className="empty">この縦スライスでは直接編集や自由ターミナルを提供しません。読み取り専用の安全な表示を順次追加します。</div></section>;
}

export default App;
