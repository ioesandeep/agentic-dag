import Box from '@mui/material/Box';
import type { ExtraProps } from 'react-markdown';

import { CodeBlock } from '@/components/codeBlock/codeBlock';

import { getFencedBlockLanguage, getFencedBlockText } from './utils';

const FENCED_BLOCK_STYLE = { my: 1 };

interface MarkdownCodeBlockProps {
  // The `pre` syntax tree element for a fenced Markdown block.
  node?: ExtraProps['node'];
}

/**
 * Renders a fenced Markdown block as a code block.
 */
export const MarkdownCodeBlock = ({ node }: MarkdownCodeBlockProps) => {
  const text = getFencedBlockText(node);
  const language = getFencedBlockLanguage(node);

  return (
    <Box sx={FENCED_BLOCK_STYLE}>
      <CodeBlock text={text} language={language} />
    </Box>
  );
};
