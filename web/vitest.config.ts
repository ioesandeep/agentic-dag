import { fileURLToPath } from 'node:url';
import { configDefaults, defineConfig } from 'vitest/config';
import type { ViteUserConfig } from 'vitest/config';

const WEB_DIRECTORY_URL = new URL('.', import.meta.url);
const WEB_DIRECTORY = fileURLToPath(WEB_DIRECTORY_URL);

const VITEST_CONFIG = {
  root: WEB_DIRECTORY,
  resolve: {
    alias: { '@': WEB_DIRECTORY },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./test/setup.ts'],
    include: ['**/*.test.{ts,tsx}'],
    exclude: [...configDefaults.exclude, '.next/**', 'out/**', 'e2e/**'],
    clearMocks: true,
    restoreMocks: true,
  },
} satisfies ViteUserConfig;

export default defineConfig(VITEST_CONFIG);
