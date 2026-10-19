import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vitest/config';

const WEB_ROOT_URL = new URL('.', import.meta.url);
const WEB_ROOT = fileURLToPath(WEB_ROOT_URL);

const VITEST_CONFIG = {
  resolve: { alias: { '@': WEB_ROOT } },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./test/setup.ts'],
    include: ['**/*.test.{ts,tsx}'],
    exclude: ['node_modules/**', '.next/**', 'out/**'],
  },
};

export default defineConfig(VITEST_CONFIG);
