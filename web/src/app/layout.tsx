import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ROT — watch a programming language work",
  description:
    "ROT is a small, hand-rolled language. Every step it takes — tokenize, parse, execute, compile to bytecode — happens in front of you. Built as a visual learning project for how programming languages actually work under the hood.",
  openGraph: {
    title: "ROT — watch a programming language work",
    description:
      "Animated, step-through visualizations of the lexer, parser, tree-walking interpreter, and bytecode VM of a small hand-rolled language.",
    type: "website",
  },
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
