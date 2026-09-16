import type { NodeState } from '@/entities/nodeState';

declare module '@mui/material/styles' {
  interface Palette {
    state: Record<NodeState, string>;
  }

  interface PaletteOptions {
    state?: Record<NodeState, string>;
  }

  interface TypographyVariants {
    fontFamilyMono: string;
  }

  interface TypographyVariantsOptions {
    fontFamilyMono?: string;
  }
}

export {};
