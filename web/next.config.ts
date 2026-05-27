import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Pyodide ships its own WebAssembly assets from a CDN; nothing to bundle
  // server-side. The playground is a fully-static client app.
  experimental: {
    // Allow the .py files inside public/rot_package to be served as plain
    // text from the static asset server (Next does this by default, listed
    // here as a reminder for future maintainers).
  },
};

export default nextConfig;
