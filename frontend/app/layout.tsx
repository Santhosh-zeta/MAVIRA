import type { Metadata } from "next";
import "./globals.css";
import { Shell } from "@/components/shell";

export const metadata: Metadata = {
  title: "MAVIRA — Meridian AI Vendor Risk",
  description: "Internal vendor AI usage and risk assessment workbench for Meridian Financial",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
