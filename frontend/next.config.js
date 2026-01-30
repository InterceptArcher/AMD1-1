/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/rad/:path*',
        destination: 'https://amd1-1-backend.onrender.com/rad/:path*',
      },
    ];
  },
}

module.exports = nextConfig
