import { apiGet } from "../lib/api";

export const dynamic = "force-dynamic";

export default async function Leads() {
  let leads: any[] = [];
  try { leads = await apiGet<any[]>("/leads"); } catch { /* offline */ }
  return (
    <div>
      <h1 className="text-2xl font-bold">Leads</h1>
      <p className="mt-2 text-sm text-gray-500">Showing up to 500 leads.</p>
      <table className="mt-4 w-full border-collapse text-sm">
        <thead>
          <tr className="text-left text-gray-400">
            <th className="py-2">Name</th>
            <th>Category</th>
            <th>Contacts</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {leads.map((l) => (
            <tr key={l.id} className="border-t border-gray-800">
              <td className="py-2">{l.name}</td>
              <td>{l.category}</td>
              <td>{(l.contacts || []).map((c: any) => c.value).join(", ")}</td>
              <td>{l.status}</td>
            </tr>
          ))}
          {leads.length === 0 && (
            <tr><td colSpan={4} className="py-4 text-gray-500">No leads yet.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
