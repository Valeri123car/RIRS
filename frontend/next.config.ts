import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    // Profilne ikone in slike šampionov iz Riot Data Dragon.
    remotePatterns: [
      { protocol: "https", hostname: "ddragon.leagueoflegends.com", pathname: "/cdn/**" },
    ],
  },
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
