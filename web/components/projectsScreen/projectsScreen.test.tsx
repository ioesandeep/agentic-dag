import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useRouter } from 'next/navigation';
import { expect, test, vi } from 'vitest';

import { LABELS } from '@/labels/en';
import { ProjectsScreen } from './projectsScreen';

vi.mock('next/navigation', () => ({ useRouter: vi.fn() }));

test('ProjectsScreen includes archived projects when Show archived is enabled', async () => {
  const user = userEvent.setup();
  const router = {
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
    bfcacheId: 'projects',
  };

  const mockedUseRouter = vi.mocked(useRouter);
  mockedUseRouter.mockReturnValue(router);
  render(<ProjectsScreen />);

  const archivedProjectBeforeToggle = screen.queryByRole('button', {
    name: 'Legacy',
  });

  const appBar = screen.getByRole('banner');
  const appBarQueries = within(appBar);
  const archiveSwitch = appBarQueries.getByRole('switch', {
    name: LABELS.projectsShowArchived,
  });

  expect(archivedProjectBeforeToggle).not.toBeInTheDocument();
  expect(archiveSwitch).not.toBeChecked();

  await user.tab();
  expect(archiveSwitch).toHaveFocus();
  await user.keyboard(' ');

  const archivedProjectAfterToggle = screen.getByRole('button', {
    name: 'Legacy',
  });

  expect(archivedProjectAfterToggle).toBeVisible();
  expect(archiveSwitch).toBeChecked();
  await user.click(archiveSwitch);

  const archivedProjectAfterReset = screen.queryByRole('button', {
    name: 'Legacy',
  });

  expect(archivedProjectAfterReset).not.toBeInTheDocument();
  expect(archiveSwitch).not.toBeChecked();
});

test('ProjectsScreen opens the selected project when its name is activated', async () => {
  const user = userEvent.setup();
  const router = {
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
    bfcacheId: 'projects',
  };

  const mockedUseRouter = vi.mocked(useRouter);
  mockedUseRouter.mockReturnValue(router);
  render(<ProjectsScreen />);

  const platformProjectButton = screen.getByRole('button', {
    name: 'Platform',
  });

  await user.click(platformProjectButton);

  expect(router.push).toHaveBeenCalledWith('/projects/project-platform');
});

test('ProjectsScreen closes the dialog without adding a project when creation is submitted', async () => {
  const user = userEvent.setup();
  const router = {
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
    bfcacheId: 'projects',
  };

  const mockedUseRouter = vi.mocked(useRouter);
  mockedUseRouter.mockReturnValue(router);
  render(<ProjectsScreen />);

  const appBar = screen.getByRole('banner');
  const appBarQueries = within(appBar);
  const opener = appBarQueries.getByRole('button', {
    name: LABELS.projectCreate,
  });

  expect(opener).toHaveTextContent(LABELS.projectCreate);

  await user.tab();
  await user.tab();
  expect(opener).toHaveFocus();
  await user.keyboard('{Enter}');

  const dialog = screen.getByRole('dialog', { name: LABELS.projectCreate });
  const dialogQueries = within(dialog);
  const nameInput = dialogQueries.getByRole('textbox', { name: /Name/ });
  const createProjectButton = dialogQueries.getByRole('button', {
    name: LABELS.projectCreate,
  });

  await waitFor(() => expect(nameInput).toHaveFocus());
  await user.type(nameInput, 'Operations');
  await user.click(createProjectButton);

  await waitFor(() => {
    const closedDialog = screen.queryByRole('dialog');
    expect(closedDialog).not.toBeInTheDocument();
  });

  const projectItems = screen.getAllByRole('article');
  const createdProjectButton = screen.queryByRole('button', {
    name: 'Operations',
  });

  expect(projectItems).toHaveLength(3);
  expect(createdProjectButton).not.toBeInTheDocument();
  expect(opener).toHaveFocus();
});
