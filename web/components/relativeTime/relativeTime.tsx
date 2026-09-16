'use client';

import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import { useEffect, useState } from 'react';

import { formatLabel } from '@/utils/formatLabel';

const MINUTE = 60;
const HOUR = 3600;
const DAY = 86400;

const formatRelative = (at: string): string => {
  const formatter = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });
  const seconds = Math.round((Date.parse(at) - Date.now()) / 1000);
  const magnitude = Math.abs(seconds);

  if (magnitude < MINUTE) {
    return formatter.format(Math.round(seconds), 'second');
  }
  if (magnitude < HOUR) {
    return formatter.format(Math.round(seconds / MINUTE), 'minute');
  }
  if (magnitude < DAY) {
    return formatter.format(Math.round(seconds / HOUR), 'hour');
  }

  return formatter.format(Math.round(seconds / DAY), 'day');
};

const BLANK_TEXT = ' ';

const readText = (text: string, template: string | undefined): string => {
  if (text === '') {
    return BLANK_TEXT;
  }

  if (template === undefined) {
    return text;
  }

  const timeValues = { time: text };

  return formatLabel(template, timeValues);
};

interface RelativeTimeProps {
  at: string;
  // The label to fill with the time, carrying a {time} placeholder.
  template?: string;
}

export const RelativeTime = ({ at, template }: RelativeTimeProps) => {
  const [text, setText] = useState('');

  useEffect(() => {
    const refresh = () => setText(formatRelative(at));

    refresh();
    const timer = window.setInterval(refresh, 30000);

    return () => window.clearInterval(timer);
  }, [at]);

  return (
    <Tooltip title={new Date(at).toLocaleString()}>
      <Typography variant="body2" color="text.secondary">
        {readText(text, template)}
      </Typography>
    </Tooltip>
  );
};
