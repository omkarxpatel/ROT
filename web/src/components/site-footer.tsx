import Link from "next/link";

const GITHUB_URL = "https://github.com/omkarxpatel/ROT";
const CHANGELOG_URL = `${GITHUB_URL}/blob/main/CHANGELOG.md`;
const ARCHITECTURE_URL = `${GITHUB_URL}/blob/main/ARCHITECTURE.md`;

export function SiteFooter() {
  return (
    <footer className="mt-24 border-t border-border/60">
      <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
        <div className="grid gap-8 md:grid-cols-3">
          <div>
            <div className="font-mono text-sm font-semibold tracking-tight">
              ROT
            </div>
            <p className="mt-2 max-w-xs text-xs text-muted-foreground">
              A hand-rolled programming language. C++/Python-flavored, written
              in Python, ~3,800 lines.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-6 md:col-span-2 md:grid-cols-3">
            <FooterColumn title="Try">
              <FooterLink href="/playground">Playground</FooterLink>
              <FooterLink href="/docs#examples">Examples</FooterLink>
            </FooterColumn>
            <FooterColumn title="Read">
              <FooterLink href="/docs">Docs</FooterLink>
              <FooterExternalLink href="/paper/main.pdf">
                Paper (PDF)
              </FooterExternalLink>
              <FooterExternalLink href={CHANGELOG_URL}>
                Changelog
              </FooterExternalLink>
            </FooterColumn>
            <FooterColumn title="Code">
              <FooterExternalLink href={GITHUB_URL}>GitHub</FooterExternalLink>
              <FooterExternalLink href={ARCHITECTURE_URL}>
                Architecture
              </FooterExternalLink>
            </FooterColumn>
          </div>
        </div>
        <div className="mt-10 flex flex-col gap-2 border-t border-border/60 pt-6 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <span>{`(c) ${new Date().getFullYear()} Omkar Patel`}</span>
          <span>Built by Omkar Patel with Claude.</span>
        </div>
      </div>
    </footer>
  );
}

function FooterColumn({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wider text-muted-foreground/80">
        {title}
      </div>
      <ul className="mt-3 space-y-2 text-sm">{children}</ul>
    </div>
  );
}

function FooterLink({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) {
  return (
    <li>
      <Link
        href={href}
        className="text-muted-foreground transition-colors hover:text-foreground"
      >
        {children}
      </Link>
    </li>
  );
}

function FooterExternalLink({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) {
  return (
    <li>
      <a
        href={href}
        target="_blank"
        rel="noreferrer"
        className="text-muted-foreground transition-colors hover:text-foreground"
      >
        {children}
      </a>
    </li>
  );
}
