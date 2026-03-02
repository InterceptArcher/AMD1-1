/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // Backend URL configurable via env var (enables beta/prod separation)
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    return [
      {
        source: '/api/rad/:path*',
        destination: `${backendUrl}/rad/:path*`,
      },
    ];
  },
}

module.exports = nextConfig
