import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ROT Playground",
  description:
    "Write .rot code in your browser and watch the lex / parse / interpret pipeline run live.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark h-full">
      <body className="h-full">{children}</body>
    </html>
  );
}
