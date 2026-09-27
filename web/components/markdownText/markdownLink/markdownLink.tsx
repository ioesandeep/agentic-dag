import Link from '@mui/material/Link';
import type { ReactNode } from 'react';

interface MarkdownLinkProps {
  href?: string;
  children?: ReactNode;
}

/**
 * Renders a Markdown link that opens in a new tab.
 */
export const MarkdownLink = ({ href, children }: MarkdownLinkProps) => (
  <Link href={href} target="_blank" rel="noopener noreferrer">
    {children}
  </Link>
);
