/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false, // disable in dev to prevent Supabase lock race conditions
  output: 'standalone',
  images: {
    unoptimized: true,
  },
  // Allow cross-origin HMR from local network (e.g. when accessing via LAN IP)
  allowedDevOrigins: ['192.168.150.1'],
};

module.exports = nextConfig;
