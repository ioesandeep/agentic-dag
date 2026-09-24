import { fileURLToPath } from 'node:url';

const DEFAULT_API_ORIGIN = 'http://127.0.0.1:8788';
const API_ORIGIN = process.env.DAG_CONSOLE_API_ORIGIN ?? DEFAULT_API_ORIGIN;
const API_PATTERN = '/api/:path*';

const nextConfig = {
  agentRules: false,
  outputFileTracingRoot: fileURLToPath(new URL('.', import.meta.url)),
  rewrites: async () => [
    { source: API_PATTERN, destination: `${API_ORIGIN}${API_PATTERN}` },
  ],
};

export default nextConfig;
