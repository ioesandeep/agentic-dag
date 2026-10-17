import { ThemeProvider } from '@mui/material/styles';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, test } from 'vitest';

import { LABELS } from '@/labels/en';
import { theme } from '@/theme/theme';

import { SoftChip } from './softChip';
import type { SoftChipLink } from './types';

test('SoftChip focuses its link when the user presses Tab', async () => {
  const user = userEvent.setup();
  const softChipLink: SoftChipLink = {
    url: 'https://github.com/SK-Giri-Corp/virgo/pull/1',
    ariaLabel: LABELS.nodePullRequestLink,
  };
  const softChip = (
    <ThemeProvider theme={theme}>
      <SoftChip
        label={LABELS.nodePullRequestLink}
        color={theme.palette.primary.main}
        link={softChipLink}
      />
    </ThemeProvider>
  );
  render(softChip);

  await user.tab();

  const linkQuery = { name: LABELS.nodePullRequestLink };
  const link = screen.getByRole('link', linkQuery);
  expect(link).toHaveFocus();
  expect(link).toHaveAttribute('href', softChipLink.url);
});
