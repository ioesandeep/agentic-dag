import type { NodeStateEnum } from '@/entities/nodeState';

declare module '@mui/material/styles' {
  interface Palette {
    state: Record<NodeStateEnum, string>;
  }

  interface PaletteOptions {
    state?: Record<NodeStateEnum, string>;
  }

  interface TypographyVariants {
    fontFamilyMono: string;
  }

  interface TypographyVariantsOptions {
    fontFamilyMono?: string;
  }
}

export {};
