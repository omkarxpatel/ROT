import Link from "next/link";
import { Github, ExternalLink } from "lucide-react";

import { ROT_VERSION } from "@/lib/rot-version";

const GITHUB_URL = "https://github.com/omkarxpatel/ROT";

interface SiteHeaderProps {
  /** Show the version pill next to the wordmark. Default: true. */
  showVersion?: boolean;
}

export function SiteHeader({ showVersion = true }: SiteHeaderProps) {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-border/60 bg-background/70 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="font-mono text-sm font-semibold tracking-tight text-foreground hover:text-primary"
          >
            ROT
          </Link>
          {showVersion ? (
            <span className="font-mono text-[11px] text-muted-foreground">
              v{ROT_VERSION}
            </span>
          ) : null}
        </div>
        <nav className="flex items-center gap-1 sm:gap-2">
          <NavLink href="/docs">Docs</NavLink>
          <NavLink href="/docs/internals">Internals</NavLink>
          <NavLink href="/playground">Playground</NavLink>
          <NavExternalLink href="/paper/main.pdf">Paper</NavExternalLink>
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noreferrer"
            className="inline-flex h-8 items-center gap-1.5 rounded-md px-2.5 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          >
            <Github className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">GitHub</span>
          </a>
        </nav>
      </div>
    </header>
  );
}

function NavLink({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className="inline-flex h-8 items-center rounded-md px-2.5 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
    >
      {children}
    </Link>
  );
}

function NavExternalLink({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="inline-flex h-8 items-center gap-1 rounded-md px-2.5 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
    >
      {children}
      <ExternalLink className="h-3 w-3 opacity-60" />
    </a>
  );
}
