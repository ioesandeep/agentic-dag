import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, test, vi } from 'vitest';

import { LABELS } from '@/labels/en';
import { MOCK_PROJECTS, MOCK_REPOSITORIES } from '@/mocks/catalogMocks';
import { theme } from '@/theme/theme';
import { formatLabel } from '@/utils/formatLabel';
import { ProjectList } from './projectList';

test('ProjectList orders Default first when projects arrive in reverse order', () => {
  const projects = MOCK_PROJECTS.toReversed();
  render(
    <ProjectList
      projects={projects}
      repositories={MOCK_REPOSITORIES}
      showArchived
      onSelectProject={vi.fn()}
    />,
  );

  const projectList = screen.getByRole('list', {
    name: LABELS.projectsHeading,
  });

  const projectListQueries = within(projectList);
  const projectHeadings = projectListQueries.getAllByRole('heading', {
    level: 6,
  });

  const projectNames = projectHeadings.map((heading) => heading.textContent);

  expect(projectNames).toEqual(['Default', 'Legacy', 'Platform', 'Research']);
});

test('ProjectList displays project details when archived projects are included', () => {
  render(
    <ProjectList
      projects={MOCK_PROJECTS}
      repositories={MOCK_REPOSITORIES}
      showArchived
      onSelectProject={vi.fn()}
    />,
  );

  const [defaultProject] = MOCK_PROJECTS;
  const defaultProjectCard = screen.getByRole('article', { name: 'Default' });
  const defaultProjectQueries = within(defaultProjectCard);
  const repositoryList = defaultProjectQueries.getByRole('list', {
    name: LABELS.projectRepositories,
  });

  const repositoryQueries = within(repositoryList);
  const repositoryItems = repositoryQueries.getAllByRole('listitem');
  const repositoryNames = repositoryItems.map((item) => item.textContent);

  const countValues = { count: '3' };
  const expectedCount = formatLabel(
    LABELS.projectRepositoryCountPlural,
    countValues,
  );

  const archivedCountValues = { count: '1' };
  const expectedArchivedCount = formatLabel(
    LABELS.projectRepositoryCountSingular,
    archivedCountValues,
  );

  const archivedProjectCard = screen.getByRole('article', { name: 'Legacy' });
  const researchProjectCard = screen.getByRole('article', { name: 'Research' });
  const activeStatuses = screen.getAllByText(LABELS.projectActive);

  expect(defaultProjectCard).toHaveTextContent(
    defaultProject?.description ?? '',
  );

  expect(defaultProjectCard).toHaveTextContent(expectedCount);
  expect(defaultProjectCard).not.toHaveTextContent(
    /ready|importing|failed|unavailable/,
  );

  expect(archivedProjectCard).toHaveTextContent(LABELS.projectArchived);
  expect(archivedProjectCard).toHaveTextContent(expectedArchivedCount);
  expect(activeStatuses).toHaveLength(3);

  expect(repositoryNames).toEqual([
    'acme/service',
    'acme/worker',
    'acme/connector',
  ]);

  expect(researchProjectCard).toHaveTextContent(
    LABELS.projectRepositoriesEmpty,
  );
});

test('ProjectList includes every repository in the bar when the text preview is limited', () => {
  const defaultProjects = MOCK_PROJECTS.filter((project) => project.isDefault);
  const projects = defaultProjects.map((project) => ({
    ...project,
    repositoryCounts: {
      total: 6,
      ready: 2,
      importing: 1,
      failed: 1,
      unavailable: 2,
    },
  }));

  const memberships = projects.map((project) => ({ project, branch: 'main' }));
  const repositories = MOCK_REPOSITORIES.map((repository) => ({
    ...repository,
    memberships,
  }));

  render(
    <ProjectList
      projects={projects}
      repositories={repositories}
      showArchived={false}
      onSelectProject={vi.fn()}
    />,
  );

  const repositoryList = screen.getByRole('list', {
    name: LABELS.projectRepositories,
  });

  const repositoryQueries = within(repositoryList);
  const repositoryItems = repositoryQueries.getAllByRole('listitem');
  const fourthRepository = repositoryQueries.queryByText('acme/console');
  const repositoryBar = screen.getByRole('group', {
    name: LABELS.projectRepositories,
  });

  const barQueries = within(repositoryBar);
  const repositorySegments = barQueries.getAllByRole('img');
  const segmentColors = repositorySegments.map(
    (segment) => getComputedStyle(segment).backgroundColor,
  );

  const distinctColors = new Set(segmentColors);

  expect(repositoryItems).toHaveLength(3);
  expect(fourthRepository).not.toBeInTheDocument();
  expect(repositorySegments).toHaveLength(6);
  expect(distinctColors.size).toBe(6);
});

test('ProjectList displays repository segments when a project has repositories', () => {
  render(
    <ProjectList
      projects={MOCK_PROJECTS}
      repositories={MOCK_REPOSITORIES}
      showArchived={false}
      onSelectProject={vi.fn()}
    />,
  );

  const defaultProjectCard = screen.getByRole('article', { name: 'Default' });
  const defaultProjectQueries = within(defaultProjectCard);
  const defaultBar = defaultProjectQueries.getByRole('group', {
    name: LABELS.projectRepositories,
  });

  const barQueries = within(defaultBar);
  const segments = barQueries.getAllByRole('img');
  const repositoryNames = segments.map((segment) =>
    segment.getAttribute('aria-label'),
  );

  const researchProjectCard = screen.getByRole('article', { name: 'Research' });
  const researchProjectQueries = within(researchProjectCard);
  const emptyBar = researchProjectQueries.getByRole('group', {
    name: LABELS.projectRepositories,
  });

  const emptyBarQueries = within(emptyBar);
  const emptySegments = emptyBarQueries.queryAllByRole('img');

  expect(repositoryNames).toEqual([
    'acme/service',
    'acme/worker',
    'acme/connector',
  ]);

  expect(emptyBar).toBeVisible();
  expect(emptyBar).toHaveStyle({ backgroundColor: theme.palette.grey[500] });
  expect(emptySegments).toHaveLength(0);
});

test('ProjectList opens project cards when a user operates the keyboard', async () => {
  const user = userEvent.setup();
  const onSelectProject = vi.fn();
  render(
    <ProjectList
      projects={MOCK_PROJECTS}
      repositories={MOCK_REPOSITORIES}
      showArchived={false}
      onSelectProject={onSelectProject}
    />,
  );

  const defaultProjectButton = screen.getByRole('button', { name: 'Default' });
  const platformProjectButton = screen.getByRole('button', {
    name: 'Platform',
  });

  await user.tab();
  expect(defaultProjectButton).toHaveFocus();
  await user.keyboard('{Enter}');

  await user.tab();
  expect(platformProjectButton).toHaveFocus();
  await user.keyboard(' ');

  expect(onSelectProject).toHaveBeenCalledTimes(2);
  expect(onSelectProject).toHaveBeenNthCalledWith(1, 'project-default');
  expect(onSelectProject).toHaveBeenNthCalledWith(2, 'project-platform');
});

test('ProjectList displays the empty state when no projects exist', () => {
  render(
    <ProjectList
      projects={[]}
      repositories={MOCK_REPOSITORIES}
      showArchived={false}
      onSelectProject={vi.fn()}
    />,
  );

  const emptyState = screen.getByText(LABELS.projectsEmpty);
  expect(emptyState).toBeVisible();
});
