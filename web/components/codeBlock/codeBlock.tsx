'use client';

import Box from '@mui/material/Box';
import { useColorScheme } from '@mui/material/styles';
import type { SxProps, Theme } from '@mui/material/styles';
import { PrismLight } from 'react-syntax-highlighter';
import bash from 'react-syntax-highlighter/dist/esm/languages/prism/bash';
import css from 'react-syntax-highlighter/dist/esm/languages/prism/css';
import javascript from 'react-syntax-highlighter/dist/esm/languages/prism/javascript';
import json from 'react-syntax-highlighter/dist/esm/languages/prism/json';
import jsx from 'react-syntax-highlighter/dist/esm/languages/prism/jsx';
import markdown from 'react-syntax-highlighter/dist/esm/languages/prism/markdown';
import python from 'react-syntax-highlighter/dist/esm/languages/prism/python';
import sql from 'react-syntax-highlighter/dist/esm/languages/prism/sql';
import toml from 'react-syntax-highlighter/dist/esm/languages/prism/toml';
import tsx from 'react-syntax-highlighter/dist/esm/languages/prism/tsx';
import typescript from 'react-syntax-highlighter/dist/esm/languages/prism/typescript';
import yaml from 'react-syntax-highlighter/dist/esm/languages/prism/yaml';
import a11yDark from 'react-syntax-highlighter/dist/esm/styles/prism/a11y-dark';
import coldarkCold from 'react-syntax-highlighter/dist/esm/styles/prism/coldark-cold';

import {
  LINE_NUMBER_MIN_LINES,
  MAX_BLOCK_HEIGHT,
  PLAIN_TEXT_THRESHOLD,
} from '@/components/codeBlock/constants';
import { HighlightLanguage } from '@/components/codeBlock/types';
import { hasManyLines } from '@/components/codeBlock/utils';

PrismLight.registerLanguage(HighlightLanguage.BASH, bash);
PrismLight.registerLanguage(HighlightLanguage.CSS, css);
PrismLight.registerLanguage(HighlightLanguage.JAVASCRIPT, javascript);
PrismLight.registerLanguage(HighlightLanguage.JSON, json);
PrismLight.registerLanguage(HighlightLanguage.JSX, jsx);
PrismLight.registerLanguage(HighlightLanguage.MARKDOWN, markdown);
PrismLight.registerLanguage(HighlightLanguage.PYTHON, python);
PrismLight.registerLanguage(HighlightLanguage.SQL, sql);
PrismLight.registerLanguage(HighlightLanguage.TOML, toml);
PrismLight.registerLanguage(HighlightLanguage.TSX, tsx);
PrismLight.registerLanguage(HighlightLanguage.TYPESCRIPT, typescript);
PrismLight.registerLanguage(HighlightLanguage.YAML, yaml);

const CONTAINER_STYLE = {
  borderRadius: 1,
  bgcolor: 'action.hover',
  maxHeight: MAX_BLOCK_HEIGHT,
  overflow: 'auto',
};

const HIGHLIGHTER_STYLE = {
  margin: 0,
  padding: '0.625rem',
  background: 'transparent',
  fontSize: '0.8125rem',
  whiteSpace: 'pre-wrap' as const,
  wordBreak: 'break-word' as const,
  overflowWrap: 'anywhere' as const,
};

const PLAIN_TEXT_STYLE: SxProps<Theme> = {
  ...HIGHLIGHTER_STYLE,
  fontFamily: (theme) => theme.typography.fontFamilyMono,
};

const LINE_NUMBER_STYLE = {
  color: 'var(--mui-palette-text-secondary)',
  paddingRight: '0.75rem',
};

const CODE_TAG_PROPS = {
  style: {
    whiteSpace: 'pre-wrap' as const,
    wordBreak: 'break-word' as const,
    overflowWrap: 'anywhere' as const,
  },
};

interface CodeBlockProps {
  text: string;
  // The language to highlight the text in.
  language?: HighlightLanguage;
}

/**
 * Renders text in a scrollable code block.
 */
export const CodeBlock = ({
  text,
  language = HighlightLanguage.PLAIN,
}: CodeBlockProps) => {
  const { mode, systemMode } = useColorScheme();

  if (text.length > PLAIN_TEXT_THRESHOLD) {
    return (
      <Box sx={CONTAINER_STYLE}>
        <Box component="pre" sx={PLAIN_TEXT_STYLE}>
          {text}
        </Box>
      </Box>
    );
  }

  const resolved = mode === 'system' ? systemMode : mode;
  const style = resolved === 'dark' ? a11yDark : coldarkCold;

  return (
    <Box sx={CONTAINER_STYLE}>
      <PrismLight
        language={language}
        style={style}
        customStyle={HIGHLIGHTER_STYLE}
        codeTagProps={CODE_TAG_PROPS}
        showLineNumbers={hasManyLines(text, LINE_NUMBER_MIN_LINES)}
        lineNumberStyle={LINE_NUMBER_STYLE}
        wrapLongLines
      >
        {text}
      </PrismLight>
    </Box>
  );
};
