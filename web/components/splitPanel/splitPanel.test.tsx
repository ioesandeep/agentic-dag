import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, test } from 'vitest';

import { LABELS } from '@/labels/en';
import { SplitPanel } from './splitPanel';
import { SplitPanelDirectionEnum } from './types';

test.each([
  {
    direction: undefined,
    orientation: 'horizontal',
    growKey: '{ArrowDown}',
    shrinkKey: '{ArrowUp}',
    ignoredKey: '{ArrowRight}',
    grownPercent: '54',
  },
  {
    direction: SplitPanelDirectionEnum.ROW,
    orientation: 'vertical',
    growKey: '{ArrowRight}',
    shrinkKey: '{ArrowLeft}',
    ignoredKey: '{ArrowDown}',
    grownPercent: '52',
  },
])(
  'SplitPanel resizes panels by keyboard when the separator is $orientation',
  async ({
    direction,
    orientation,
    growKey,
    shrinkKey,
    ignoredKey,
    grownPercent,
  }) => {
    const user = userEvent.setup();
    const panels = [
      <div key="canvas">Canvas</div>,
      <div key="conversation">Conversation</div>,
    ];

    const { container } = render(
      <SplitPanel panels={panels} direction={direction} />,
    );

    const containerDimensions = {
      clientWidth: { value: 800 },
      clientHeight: { value: 400 },
    };

    Object.defineProperties(container.firstElementChild, containerDimensions);

    const separator = screen.getByRole('separator', {
      name: LABELS.splitResize,
    });

    expect(separator).toHaveAttribute('aria-orientation', orientation);

    await user.tab();
    await user.keyboard(growKey);

    expect(separator).toHaveFocus();
    expect(separator).toHaveAttribute('aria-valuenow', grownPercent);

    await user.keyboard(ignoredKey);

    expect(separator).toHaveAttribute('aria-valuenow', grownPercent);

    await user.keyboard(shrinkKey);

    expect(separator).toHaveAttribute('aria-valuenow', '50');
  },
);

test('SplitPanel restores resized panels when expandedPanel returns to null', async () => {
  const user = userEvent.setup();
  const panels = [
    <section key="canvas" aria-label="Canvas">
      Canvas
    </section>,
    <section key="conversation" aria-label="Conversation">
      Conversation
    </section>,
    <section key="settings" aria-label="Settings">
      Settings
    </section>,
  ];

  const initialSplit = [40, 35, 25];
  const { container, rerender } = render(
    <SplitPanel
      panels={panels}
      initialSplit={initialSplit}
      direction={SplitPanelDirectionEnum.ROW}
    />,
  );

  const containerDimensions = {
    clientWidth: { value: 800 },
    clientHeight: { value: 400 },
  };

  Object.defineProperties(container.firstElementChild, containerDimensions);

  await user.tab();
  await user.keyboard('{ArrowRight}');

  const resizedSeparators = screen.getAllByRole('separator');
  expect(resizedSeparators[0]).toHaveAttribute('aria-valuenow', '42');
  expect(resizedSeparators[1]).toHaveAttribute('aria-valuenow', '33');

  rerender(
    <SplitPanel
      panels={panels}
      initialSplit={initialSplit}
      direction={SplitPanelDirectionEnum.ROW}
      expandedPanel={1}
    />,
  );

  const conversation = screen.getByRole('region', { name: 'Conversation' });
  const hiddenCanvas = screen.queryByRole('region', { name: 'Canvas' });
  const hiddenSettings = screen.queryByRole('region', { name: 'Settings' });

  expect(conversation).toBeVisible();
  expect(hiddenCanvas).not.toBeInTheDocument();
  expect(hiddenSettings).not.toBeInTheDocument();

  const hiddenSeparator = screen.queryByRole('separator');
  expect(hiddenSeparator).not.toBeInTheDocument();

  rerender(
    <SplitPanel
      panels={panels}
      initialSplit={initialSplit}
      direction={SplitPanelDirectionEnum.ROW}
      expandedPanel={null}
    />,
  );

  const restoredSeparators = screen.getAllByRole('separator');
  expect(restoredSeparators[0]).toHaveAttribute('aria-valuenow', '42');
  expect(restoredSeparators[1]).toHaveAttribute('aria-valuenow', '33');

  const restoredCanvas = screen.getByRole('region', { name: 'Canvas' });
  const restoredSettings = screen.getByRole('region', { name: 'Settings' });
  expect(restoredCanvas).toBeVisible();
  expect(restoredSettings).toBeVisible();
});
