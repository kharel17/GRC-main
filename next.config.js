/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false, // disable in dev to prevent Supabase lock race conditions
  output: 'standalone',
  images: {
    unoptimized: true,
  },
};

module.exports = nextConfig;
