/** @type {import('next').NextConfig} */
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
