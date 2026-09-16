import { ELLIPSIS, NO_SPACE_INDEX, SNIPPET_LENGTH } from './constants';
import { LABELS } from '@/labels/en';

/**
 * Returns true where a text runs past the snippet the card shows collapsed.
 */
export const hasMoreThanSnippet = (text: string): boolean =>
  text.length > SNIPPET_LENGTH;

/**
 * Returns the opening words of a text, cut at the last whole word.
 */
export const getSnippet = (text: string): string => {
  const start = text.slice(0, SNIPPET_LENGTH);
  const lastSpace = start.lastIndexOf(' ');

  if (lastSpace === NO_SPACE_INDEX) {
    return `${start}${ELLIPSIS}`;
  }

  const wholeWords = start.slice(0, lastSpace);

  return `${wholeWords}${ELLIPSIS}`;
};

/**
 * Returns the whole text where it is expanded, and its snippet where it is not.
 */
export const getTextToDisplay = (text: string, isExpanded: boolean): string => {
  if (isExpanded) {
    return text;
  }

  return getSnippet(text);
};

/**
 * Returns the label of the control that expands and collapses a text.
 */
export const getToggleLabel = (isExpanded: boolean): string => {
  if (isExpanded) {
    return LABELS.instructionsViewLess;
  }

  return LABELS.instructionsViewMore;
};
