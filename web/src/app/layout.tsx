import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ROT — a hand-rolled programming language",
  description:
    "A C++/Python-flavored programming language built from scratch in Python. Tree-walking interpreter with rustc-style errors, written as a learning project and portfolio piece.",
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
