export type ActiveWork = {
  work_id: string;
  workspace_id: string;
  thread_id: string | null;
  turn_id: string | null;
  state: string;
};

export type DeckEvent = {
  event_id: number;
  received_at: string;
  workspace_id: string;
  event_type: string;
  thread_id: string | null;
  turn_id: string | null;
  payload: Record<string, unknown>;
};

const apiBase = import.meta.env.VITE_DECK_API_BASE ?? "";

export async function getActiveWork(workspaceId: string): Promise<ActiveWork | null> {
  const response = await fetch(`${apiBase}/api/v1/workspaces/${encodeURIComponent(workspaceId)}/active-work`);
  if (!response.ok) throw new Error("Deck Backendへ接続できません。");
  return response.json() as Promise<ActiveWork | null>;
}

export async function startWork(workspaceId: string, text: string): Promise<ActiveWork> {
  const response = await fetch(`${apiBase}/api/v1/workspaces/${encodeURIComponent(workspaceId)}/work`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      workspace_path: "demo-workspace",
      text,
      approval_policy: "untrusted",
      sandbox: "read-only",
    }),
  });
  if (response.status === 409) throw new Error("このworkspaceには進行中の作業があります。先に状態を確認してください。");
  if (!response.ok) throw new Error("作業を開始できませんでした。送信内容は保持しています。");
  return response.json() as Promise<ActiveWork>;
}

export function eventStreamUrl(workspaceId: string, after: number): string {
  const base = new URL(apiBase || window.location.origin);
  base.protocol = base.protocol === "https:" ? "wss:" : "ws:";
  base.pathname = "/api/v1/events/stream";
  base.searchParams.set("workspace_id", workspaceId);
  base.searchParams.set("after", String(after));
  return base.toString();
}
