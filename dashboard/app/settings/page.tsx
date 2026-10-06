export default function Settings() {
  return (
    <div>
      <h1 className="text-2xl font-bold">Settings</h1>
      <p className="mt-2 text-gray-400">
        Kill switch, per-channel pause, daily caps, DNC provider and API keys are configured via the
        backend /system and /suppression endpoints, and via environment (.env).
      </p>
    </div>
  );
}
