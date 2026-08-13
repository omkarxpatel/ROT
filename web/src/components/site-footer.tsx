import Link from "next/link";

const GITHUB_URL = "https://github.com/omkarxpatel/ROT";
const CHANGELOG_URL = `${GITHUB_URL}/blob/main/CHANGELOG.md`;
const ARCHITECTURE_URL = `${GITHUB_URL}/blob/main/ARCHITECTURE.md`;
const PAPER_URL = `${GITHUB_URL}/blob/main/paper/main.pdf`;
const GITHUB_PROFILE_URL = "https://github.com/omkarxpatel";
const EMAIL = "patel.omka@northeastern.edu";

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
              in Python. ~25,000 lines across language and site.
            </p>
            <div className="mt-5">
              <div className="text-xs uppercase tracking-wider text-muted-foreground/80">
                Built by Omkar Patel
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
                <a
                  href={`mailto:${EMAIL}`}
                  className="text-muted-foreground transition-colors hover:text-foreground"
                >
                  Email
                </a>
                <span className="text-border">{"·"}</span>
                <a
                  href={GITHUB_PROFILE_URL}
                  target="_blank"
                  rel="noreferrer"
                  className="text-muted-foreground transition-colors hover:text-foreground"
                >
                  GitHub
                </a>
              </div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-6 md:col-span-2 md:grid-cols-3">
            <FooterColumn title="Try">
              <FooterLink href="/playground">Playground</FooterLink>
              <FooterLink href="/docs#examples">Examples</FooterLink>
            </FooterColumn>
            <FooterColumn title="Read">
              <FooterLink href="/docs">Docs</FooterLink>
              <FooterLink href="/docs/internals">Internals</FooterLink>
              <FooterExternalLink href={PAPER_URL}>
                Design retrospective
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
        <div className="mt-10 border-t border-border/60 pt-6 text-xs text-muted-foreground">
          <span>{`(c) ${new Date().getFullYear()} Omkar Patel`}</span>
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
