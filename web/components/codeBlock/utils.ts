import { HighlightLanguage } from '@/components/codeBlock/types';

const LANGUAGE_BY_EXTENSION: Record<string, HighlightLanguage> = {
  ts: HighlightLanguage.TYPESCRIPT,
  tsx: HighlightLanguage.TSX,
  js: HighlightLanguage.JAVASCRIPT,
  jsx: HighlightLanguage.JSX,
  py: HighlightLanguage.PYTHON,
  json: HighlightLanguage.JSON,
  md: HighlightLanguage.MARKDOWN,
  yml: HighlightLanguage.YAML,
  yaml: HighlightLanguage.YAML,
  sh: HighlightLanguage.BASH,
  css: HighlightLanguage.CSS,
  sql: HighlightLanguage.SQL,
  toml: HighlightLanguage.TOML,
};

/**
 * Returns the highlight language for a file path, read from the file name's extension.
 */
export const languageForFile = (filePath: string): HighlightLanguage => {
  const fileName = filePath.split('/').pop() ?? '';
  const extension = fileName.split('.').pop();

  if (extension === undefined || extension === fileName) {
    return HighlightLanguage.PLAIN;
  }

  return (
    LANGUAGE_BY_EXTENSION[extension.toLowerCase()] ?? HighlightLanguage.PLAIN
  );
};

/**
 * Returns true when the text has at least the given number of lines.
 */
export const hasManyLines = (text: string, minimum: number): boolean =>
  text.split('\n').length >= minimum;
