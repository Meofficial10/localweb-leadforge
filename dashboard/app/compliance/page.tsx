import { apiGet } from "../lib/api";

export const dynamic = "force-dynamic";

export default async function Compliance() {
  let status: any = {};
  try { status = await apiGet<any>("/system/status"); } catch { /* offline */ }
  const rows = [
    ["Kill switch (system paused)", String(status.paused ?? "unknown")],
    ["Email channel paused", String(status.email_paused ?? "unknown")],
    ["Voice channel paused", String(status.voice_paused ?? "unknown")],
    ["Bounce rate", String(status.bounce_rate ?? "0")],
    ["Spam complaint rate", String(status.complaint_rate ?? "0")],
  ];
  return (
    <div>
      <h1 className="text-2xl font-bold">Compliance status</h1>
      <ul className="mt-4 space-y-2 text-sm">
        {rows.map(([k, v]) => (
          <li key={k} className="flex justify-between border-b border-gray-800 py-2">
            <span className="text-gray-400">{k}</span>
            <span className="font-mono">{v}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
