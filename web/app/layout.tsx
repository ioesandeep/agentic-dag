import InitColorSchemeScript from '@mui/material/InitColorSchemeScript';
import type { Metadata } from 'next';
import { JetBrains_Mono, Roboto } from 'next/font/google';
import type { ReactNode } from 'react';

import { LABELS } from '@/labels/en';
import { ThemeRegistry } from '@/theme/themeRegistry';

const body = Roboto({
  subsets: ['latin'],
  weight: ['300', '400', '500', '700'],
  variable: '--font-body',
  display: 'swap',
});

const mono = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['400', '500'],
  variable: '--font-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: LABELS.appTitle,
  description: LABELS.appDescription,
};

const RootLayout = ({ children }: { children: ReactNode }) => (
  <html
    lang="en"
    suppressHydrationWarning
    className={`${body.variable} ${mono.variable}`}
  >
    <body>
      <InitColorSchemeScript attribute="data-mui-color-scheme" />
      <ThemeRegistry>{children}</ThemeRegistry>
    </body>
  </html>
);

export default RootLayout;
