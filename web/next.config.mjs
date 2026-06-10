/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  transpilePackages: ["echarts", "zrender", "echarts-for-react"],
  experimental: {
    optimizePackageImports: ["lucide-react"],
  },
  async redirects() {
    return [
      { source: "/login", destination: "/", permanent: false },
      { source: "/my/alerts", destination: "/settings", permanent: false },
      { source: "/my/alerts/:path*", destination: "/settings", permanent: false },
    ];
  },
};

export default nextConfig;
