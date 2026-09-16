'use client';

import MuiLink from '@mui/material/Link';
import Typography from '@mui/material/Typography';
import { useId, useState } from 'react';

import {
  getTextToDisplay,
  getToggleLabel,
  hasMoreThanSnippet,
} from './utils';

const TEXT_STYLE = { whiteSpace: 'pre-wrap' as const };
const TOGGLE_STYLE = { alignSelf: 'flex-start' };

interface ExpandableTextProps {
  text: string;
}

/**
 * Renders a text the reader expands and collapses.
 */
export const ExpandableText = ({ text }: ExpandableTextProps) => {
  const textId = useId();
  const [isExpanded, setIsExpanded] = useState(false);
  const handleToggle = () => setIsExpanded((expanded) => !expanded);

  if (!hasMoreThanSnippet(text)) {
    return (
      <Typography variant="body2" sx={TEXT_STYLE}>
        {text}
      </Typography>
    );
  }

  return (
    <>
      <Typography id={textId} variant="body2" sx={TEXT_STYLE}>
        {getTextToDisplay(text, isExpanded)}
      </Typography>
      <MuiLink
        component="button"
        type="button"
        variant="body2"
        onClick={handleToggle}
        aria-expanded={isExpanded}
        aria-controls={textId}
        sx={TOGGLE_STYLE}
      >
        {getToggleLabel(isExpanded)}
      </MuiLink>
    </>
  );
};
