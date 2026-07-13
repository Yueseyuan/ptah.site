/** @type {import('next').NextConfig} */
// build: 2026-07-13-r1
const RAILWAY_URL = process.env.BACKEND_URL || 'https://ptahsite-production.up.railway.app';

const nextConfig = {
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: true },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${RAILWAY_URL}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
