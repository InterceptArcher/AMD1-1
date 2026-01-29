/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/rad/:path*',
        destination: 'http://localhost:8000/rad/:path*',
      },
    ];
  },
}

module.exports = nextConfig
