import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { assert, expect, test } from 'vitest';

import { usePlanner } from '@/hooks/usePlanner';
import { MOCK_PLANS } from '@/mocks/plannerMocks';
import { PlannerProvider } from './plannerProvider';

interface PlannerConsumerProps {
  label: string;
}

const PlannerConsumer = ({ label }: PlannerConsumerProps) => {
  const { plans, createPlan } = usePlanner();
  const handleCreatePlan = () => {
    createPlan('project-platform', 'Add audit exports to virgo.');
  };

  return (
    <section aria-label={label}>
      <button onClick={handleCreatePlan}>Create plan</button>
      <output aria-label="Plan count">{plans.length}</output>
    </section>
  );
};

test('PlannerProvider preserves shared plans when consumers are replaced', async () => {
  const user = userEvent.setup();
  const expectedCount = String(MOCK_PLANS.length + 1);
  const view = render(
    <PlannerProvider>
      <PlannerConsumer label="Plan list" />
      <PlannerConsumer label="Plan detail" />
    </PlannerProvider>,
  );

  const buttons = screen.getAllByRole('button', { name: 'Create plan' });
  const createButton = buttons[0];
  assert(createButton);

  await user.click(createButton);

  const counts = screen.getAllByRole('status', { name: 'Plan count' });

  for (const count of counts) {
    expect(count).toHaveTextContent(expectedCount);
  }

  view.rerender(
    <PlannerProvider>
      <PlannerConsumer key="node" label="Plan node" />
    </PlannerProvider>,
  );

  const count = screen.getByRole('status', { name: 'Plan count' });
  expect(count).toHaveTextContent(expectedCount);
});

test('PlannerProvider starts with mock plans when independent providers mount', async () => {
  const user = userEvent.setup();
  const expectedCount = String(MOCK_PLANS.length);
  const view = render(
    <>
      <PlannerProvider>
        <PlannerConsumer label="First planner" />
      </PlannerProvider>
      <PlannerProvider>
        <PlannerConsumer label="Second planner" />
      </PlannerProvider>
    </>,
  );

  const firstPlanner = screen.getByRole('region', {
    name: 'First planner',
  });

  const firstQueries = within(firstPlanner);
  const createButton = firstQueries.getByRole('button', {
    name: 'Create plan',
  });

  await user.click(createButton);

  const secondPlanner = screen.getByRole('region', {
    name: 'Second planner',
  });

  const secondQueries = within(secondPlanner);
  const secondCount = secondQueries.getByRole('status', { name: 'Plan count' });
  expect(secondCount).toHaveTextContent(expectedCount);

  view.unmount();
  render(
    <PlannerProvider>
      <PlannerConsumer label="Reloaded planner" />
    </PlannerProvider>,
  );

  const resetCount = screen.getByRole('status', { name: 'Plan count' });
  expect(resetCount).toHaveTextContent(expectedCount);
});
