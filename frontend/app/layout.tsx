import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RoomSense",
  description: "WiFi CSI Presence & Activity Detection",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#0a0a0a] text-[#ededed]">
        <nav className="border-b border-[#2a2a2a] px-6 py-4">
          <div className="mx-auto flex max-w-7xl items-center justify-between">
            <a href="/" className="text-xl font-bold">
              RoomSense
            </a>
            <div className="flex gap-6 text-sm text-[#737373]">
              <a href="/" className="hover:text-white transition">
                Dashboard
              </a>
              <a href="/calibrate" className="hover:text-white transition">
                Calibrate
              </a>
              <a href="/history" className="hover:text-white transition">
                History
              </a>
            </div>
          </div>
        </nav>
        <main className="mx-auto max-w-7xl p-6">{children}</main>
      </body>
    </html>
  );
}
