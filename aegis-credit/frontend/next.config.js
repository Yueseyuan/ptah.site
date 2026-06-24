/** @type {import('next').NextConfig} */
// build: 2026-06-24-r1
const nextConfig = {
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: true },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'https://ptahsite-production.up.railway.app/api/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
