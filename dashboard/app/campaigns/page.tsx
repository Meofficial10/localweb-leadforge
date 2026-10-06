import { apiGet } from "../lib/api";

export const dynamic = "force-dynamic";

export default async function Campaigns() {
  let campaigns: any[] = [];
  try { campaigns = await apiGet<any[]>("/campaigns"); } catch { /* offline */ }
  return (
    <div>
      <h1 className="text-2xl font-bold">Campaigns</h1>
      <table className="mt-4 w-full border-collapse text-sm">
        <thead>
          <tr className="text-left text-gray-400">
            <th className="py-2">Name</th>
            <th>City</th>
            <th>Categories</th>
            <th>Mode</th>
            <th>Email cap/day</th>
            <th>Paused</th>
          </tr>
        </thead>
        <tbody>
          {campaigns.map((c) => (
            <tr key={c.id} className="border-t border-gray-800">
              <td className="py-2">{c.name}</td>
              <td>{c.city}</td>
              <td>{(c.categories || []).join(", ")}</td>
              <td className={c.mode === "dry_run" ? "text-amber-400" : "text-emerald-400"}>{c.mode}</td>
              <td>{c.daily_email_cap}</td>
              <td>{String(c.is_paused)}</td>
            </tr>
          ))}
          {campaigns.length === 0 && (
            <tr><td colSpan={6} className="py-4 text-gray-500">No campaigns yet.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
