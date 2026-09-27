import TableContainer from '@mui/material/TableContainer';
import type { ReactNode } from 'react';

const TABLE_CONTAINER_STYLE = { my: 1 };

interface MarkdownTableProps {
  children?: ReactNode;
}

/**
 * Renders a Markdown table that scrolls horizontally when it is wider than its container.
 */
export const MarkdownTable = ({ children }: MarkdownTableProps) => (
  <TableContainer sx={TABLE_CONTAINER_STYLE}>
    <table>{children}</table>
  </TableContainer>
);
