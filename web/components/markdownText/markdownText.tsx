import Box from '@mui/material/Box';
import type { SxProps, Theme } from '@mui/material/styles';
import Markdown from 'react-markdown';
import type { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { MarkdownCodeBlock } from '@/components/markdownText/markdownCodeBlock/markdownCodeBlock';
import { MarkdownLink } from '@/components/markdownText/markdownLink/markdownLink';
import { MarkdownTable } from '@/components/markdownText/markdownTable/markdownTable';

const REMARK_PLUGINS = [remarkGfm];

const MARKDOWN_COMPONENTS: Components = {
  a: MarkdownLink,
  pre: MarkdownCodeBlock,
  table: MarkdownTable,
};

const MARKDOWN_STYLE: SxProps<Theme> = {
  overflowWrap: 'break-word',
  '& > :first-child': { mt: 0 },
  '& > :last-child': { mb: 0 },
  '& p, & ul, & ol, & blockquote': { my: 1 },
  '& h1, & h2, & h3, & h4, & h5, & h6': { mt: 2, mb: 1 },
  '& h1': { typography: 'h5', fontWeight: 'fontWeightBold' },
  '& h2': { typography: 'h6', fontWeight: 'fontWeightBold' },
  '& h3, & h4, & h5, & h6': {
    typography: 'subtitle1',
    fontWeight: 'fontWeightBold',
  },
  '& ul, & ol': { pl: 3 },
  '& li > ul, & li > ol': { my: 0 },
  '& blockquote': {
    mx: 0,
    pl: 1.5,
    borderLeft: 3,
    borderColor: 'divider',
    color: 'text.secondary',
  },
  '& table': { borderCollapse: 'collapse' },
  '& th, & td': {
    px: 1,
    py: 0.5,
    border: 1,
    borderColor: 'divider',
    textAlign: 'left',
  },
  '& th': { bgcolor: 'action.hover', fontWeight: 'fontWeightBold' },
  '& :not(pre) > code': {
    px: 0.5,
    borderRadius: 0.5,
    bgcolor: 'action.hover',
    fontFamily: (theme) => theme.typography.fontFamilyMono,
  },
};

interface MarkdownTextProps {
  text: string;
}

/**
 * Renders text as GitHub Flavored Markdown.
 */
export const MarkdownText = ({ text }: MarkdownTextProps) => (
  <Box sx={MARKDOWN_STYLE}>
    <Markdown remarkPlugins={REMARK_PLUGINS} components={MARKDOWN_COMPONENTS}>
      {text}
    </Markdown>
  </Box>
);
