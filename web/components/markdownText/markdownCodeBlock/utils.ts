import type { ExtraProps } from 'react-markdown';

import { HighlightLanguage } from '@/components/codeBlock/types';

type MarkdownElement = NonNullable<ExtraProps['node']>;

const LANGUAGE_CLASS_PREFIX = 'language-';
const TRAILING_LINE_ENDING = /\n$/;

const LANGUAGE_BY_IDENTIFIER: Record<string, HighlightLanguage> = {
  bash: HighlightLanguage.BASH,
  sh: HighlightLanguage.BASH,
  shell: HighlightLanguage.BASH,
  zsh: HighlightLanguage.BASH,
  css: HighlightLanguage.CSS,
  javascript: HighlightLanguage.JAVASCRIPT,
  js: HighlightLanguage.JAVASCRIPT,
  json: HighlightLanguage.JSON,
  jsx: HighlightLanguage.JSX,
  markdown: HighlightLanguage.MARKDOWN,
  md: HighlightLanguage.MARKDOWN,
  python: HighlightLanguage.PYTHON,
  py: HighlightLanguage.PYTHON,
  sql: HighlightLanguage.SQL,
  toml: HighlightLanguage.TOML,
  tsx: HighlightLanguage.TSX,
  typescript: HighlightLanguage.TYPESCRIPT,
  ts: HighlightLanguage.TYPESCRIPT,
  yaml: HighlightLanguage.YAML,
  yml: HighlightLanguage.YAML,
};

const getCodeElement = (
  preElement: MarkdownElement | undefined,
): MarkdownElement | null => {
  const codeElement = preElement?.children[0];

  if (codeElement?.type !== 'element') {
    return null;
  }

  return codeElement;
};

const getLanguageIdentifier = (
  codeElement: MarkdownElement | null,
): string | null => {
  const classNames = codeElement?.properties.className;
  const isClassNameList = Array.isArray(classNames);

  if (!isClassNameList) {
    return null;
  }

  const languageClassName = classNames
    .map(String)
    .find((className) => className.startsWith(LANGUAGE_CLASS_PREFIX));

  return languageClassName?.slice(LANGUAGE_CLASS_PREFIX.length) ?? null;
};

/**
 * Returns fenced block text without a trailing line ending.
 */
export const getFencedBlockText = (
  preElement: MarkdownElement | undefined,
): string => {
  const codeElement = getCodeElement(preElement);
  const codeChildren = codeElement?.children ?? [];
  const text = codeChildren
    .map((child) => (child.type === 'text' ? child.value : ''))
    .join('');

  return text.replace(TRAILING_LINE_ENDING, '');
};

/**
 * Returns the highlight language for a fenced code block.
 */
export const getFencedBlockLanguage = (
  preElement: MarkdownElement | undefined,
): HighlightLanguage => {
  const codeElement = getCodeElement(preElement);
  const languageIdentifier = getLanguageIdentifier(codeElement);

  if (languageIdentifier === null) {
    return HighlightLanguage.PLAIN;
  }

  return (
    LANGUAGE_BY_IDENTIFIER[languageIdentifier.toLowerCase()] ??
    HighlightLanguage.PLAIN
  );
};
