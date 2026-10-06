import { apiGet } from "./lib/api";

async function getStatus() {
  try {
    return await apiGet<any>("/health");
  } catch {
    return { status: "offline" };
  }
}

export default async function Home() {
  const health = await getStatus();
  return (
    <div>
      <h1 className="text-2xl font-bold">Control plane</h1>
      <p className="mt-2 text-gray-400">
        Backend status: <span className={health.status === "ok" ? "text-emerald-400" : "text-red-400"}>{String(health.status)}</span>
      </p>
      <p className="mt-4 text-sm text-gray-500">
        Dry-run is enabled by default. No outbound email or calls are sent until you explicitly enable LIVE mode per channel.
      </p>
    </div>
  );
}
