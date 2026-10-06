import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LeadForge Dashboard",
  description: "Lead generation and outreach control plane",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <nav className="border-b border-gray-800 bg-gray-900">
          <div className="mx-auto flex max-w-6xl items-center gap-6 px-4 py-3">
            <a href="/" className="font-bold text-emerald-400">LeadForge</a>
            <a href="/campaigns" className="text-sm text-gray-300 hover:text-white">Campaigns</a>
            <a href="/leads" className="text-sm text-gray-300 hover:text-white">Leads</a>
            <a href="/compliance" className="text-sm text-gray-300 hover:text-white">Compliance</a>
            <a href="/settings" className="text-sm text-gray-300 hover:text-white">Settings</a>
          </div>
        </nav>
        <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
