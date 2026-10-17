import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, test, vi } from 'vitest';

import type { Project } from '@/entities/catalog/project';
import { LABELS } from '@/labels/en';
import { formatLabel } from '@/utils/formatLabel';

import { ProjectList } from './projectList';

const createProject = (name: string): Project => ({
  id: name,
  name,
  description: 'Platform development',
  isDefault: false,
  version: 1,
  createdAt: '2026-10-17T00:00:00Z',
  updatedAt: '2026-10-17T00:00:00Z',
  archivedAt: null,
  repositoryCounts: { total: 4, ready: 1, importing: 1, failed: 1, unavailable: 1 },
});

test.each([
  { projects: null, hasFailed: false, text: LABELS.projectsLoading },
  { projects: null, hasFailed: true, text: LABELS.projectsLoadFailed },
  { projects: [], hasFailed: false, text: LABELS.projectsEmpty },
])(
  'ProjectList displays $text when the request has no projects',
  ({ projects, hasFailed, text }) => {
    const projectList = (
      <ProjectList
        projects={projects}
        hasFailed={hasFailed}
        showArchived={false}
        onShowArchivedChange={vi.fn()}
        onCreate={vi.fn()}
        onRetry={vi.fn()}
        onProjectSelect={vi.fn()}
      />
    );
    render(projectList);

    const stateText = screen.getByText(text);
    expect(stateText).toBeVisible();
  },
);

test('ProjectList displays project metadata when archive visibility changes', () => {
  const defaultProject = { ...createProject('Default'), isDefault: true };
  const archivedProject = { ...createProject('Archive'), archivedAt: '2026-10-17T00:00:00Z' };
  const acmeProject = {
    ...createProject('Acme'),
    description: 'Acme platform',
    repositoryCounts: { total: 1000, ready: 997, importing: 1, failed: 1, unavailable: 1 },
  };
  const projects = [createProject('Zebra'), acmeProject, defaultProject, archivedProject];
  const props = {
    projects,
    hasFailed: false,
    showArchived: false,
    onShowArchivedChange: vi.fn(),
    onProjectSelect: vi.fn(),
    onCreate: vi.fn(),
    onRetry: vi.fn(),
  };
  const projectList = <ProjectList {...props} />;
  const { rerender } = render(projectList);

  const projectButtons = screen.getAllByRole('button');
  const projectNames = projectButtons.map((button) => button.textContent);
  expect(projectNames).toEqual([LABELS.projectCreate, 'Default', 'Acme', 'Zebra']);
  const defaultStatus = screen.getByText(LABELS.projectDefault);
  expect(defaultStatus).toBeVisible();
  const countValues = {
    total: '1,000',
    ready: '997',
    importing: '1',
    failed: '1',
    unavailable: '1',
  };
  const countLabel = formatLabel(LABELS.projectRepositoryCounts, countValues);
  const countText = screen.getByText(countLabel);
  expect(countText).toBeVisible();
  const description = screen.getByText(acmeProject.description);
  expect(description).toBeVisible();
  const archivedList = <ProjectList {...props} showArchived />;
  rerender(archivedList);
  const archivedStatus = screen.getByText(LABELS.projectArchived);
  expect(archivedStatus).toBeVisible();
});

test('ProjectList keeps keyboard controls available when refresh fails', async () => {
  const user = userEvent.setup();
  const defaultProject = { ...createProject('Default'), isDefault: true };
  const projects = [defaultProject];
  const onProjectSelect = vi.fn();
  const onShowArchivedChange = vi.fn();
  const onCreate = vi.fn();
  const onRetry = vi.fn();
  const props = {
    projects,
    hasFailed: true,
    showArchived: false,
    onProjectSelect,
    onShowArchivedChange,
    onCreate,
    onRetry,
  };
  const projectList = <ProjectList {...props} />;
  render(projectList);

  await user.tab();
  await user.keyboard('{Enter}');
  await user.tab();
  await user.keyboard(' ');
  await user.tab();
  await user.keyboard('{Enter}');
  await user.tab();
  await user.keyboard('{Enter}');

  const alert = screen.getByRole('alert');
  expect(alert).toHaveTextContent(LABELS.projectsRefreshFailed);
  expect(onCreate).toHaveBeenCalledOnce();
  expect(onShowArchivedChange).toHaveBeenCalledWith(true);
  expect(onRetry).toHaveBeenCalledOnce();
  expect(onProjectSelect).toHaveBeenCalledWith(defaultProject.id);
});
