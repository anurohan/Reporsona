import type { Metadata, Viewport } from "next";
import "./globals.css";
import { ToastProvider } from "@/components/ui/Toast";
import CommandPalette from "@/components/CommandPalette";
import ShortcutsHint from "@/components/ShortcutsHint";
import { Inter, Space_Grotesk } from "next/font/google";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const spaceGrotesk = Space_Grotesk({ subsets: ["latin"], variable: "--font-space" });

export const metadata: Metadata = {
  title: "RePersona — Explore the documented mind of history",
  description:
    "RePersona reconstructs a documented persona from multimodal historical material and lets you explore it — with evidence for every claim.",
  applicationName: "RePersona",
};

export const viewport: Viewport = {
  themeColor: "#05060f",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`dark ${inter.variable} ${spaceGrotesk.variable}`}>
      <body className="min-h-screen bg-void-950 text-slate-200">
        <ToastProvider>
          {children}
          <CommandPalette />
          <ShortcutsHint />
        </ToastProvider>
      </body>
    </html>
  );
}
