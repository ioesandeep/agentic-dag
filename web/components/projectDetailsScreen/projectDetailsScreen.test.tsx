import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, test } from 'vitest';

import ProjectLayout from '@/app/projects/[projectId]/layout';
import ProjectPage from '@/app/projects/[projectId]/page';
import { LABELS } from '@/labels/en';
import { MOCK_PROJECTS, MOCK_REPOSITORIES } from '@/mocks/catalogMocks';
import { formatLabel } from '@/utils/formatLabel';
import { ProjectDetailsScreen } from './projectDetailsScreen';

const getProject = (projectId: string) => {
  const project = MOCK_PROJECTS.find((project) => project.id === projectId);
  if (project === undefined) {
    throw new Error('The project fixture is missing.');
  }

  return project;
};

test('ProjectDetailsScreen displays project fields and repository branches', () => {
  const project = getProject('project-platform');

  render(<ProjectDetailsScreen project={project} />);

  expect(screen.getByRole('heading', { name: project.name })).toBeVisible();
  expect(screen.getByText(LABELS.projectDetailsName)).toBeVisible();
  expect(screen.getByText(project.description)).toBeVisible();
  expect(screen.getAllByRole('listitem')).toHaveLength(project.repositoryCounts.total);

  for (const repository of MOCK_REPOSITORIES) {
    const membership = repository.memberships.find((membership) => membership.project === project);
    const repositoryItem = screen.queryByRole('listitem', { name: repository.fullName });
    if (membership === undefined) {
      expect(repositoryItem).not.toBeInTheDocument();

      continue;
    }

    expect(repositoryItem).toHaveTextContent(repository.checkoutPath);
    expect(repositoryItem).toHaveTextContent(membership.branch);
  }
});

test('ProjectDetailsScreen displays the empty project state', () => {
  const project = getProject('project-research');

  render(<ProjectDetailsScreen project={project} />);

  expect(screen.getByText(LABELS.projectRepositoriesEmpty)).toBeVisible();
  expect(screen.queryByRole('listitem')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: LABELS.projectRepositoryAdd })).toBeDisabled();
});

test('The project route returns not found when the project ID is unknown', async () => {
  const routeParameter = { projectId: 'project-unknown' };
  const params = Promise.resolve(routeParameter);
  const pageProps = { params };
  const layoutProps = { params, children: null };

  await expect(ProjectLayout(layoutProps)).rejects.toThrow('NEXT_HTTP_ERROR_FALLBACK;404');
  await expect(ProjectPage(pageProps)).rejects.toThrow('NEXT_HTTP_ERROR_FALLBACK;404');
});

test('ProjectDetailsScreen toggles repository access with archive and unarchive actions', async () => {
  const project = getProject('project-legacy');
  const user = userEvent.setup();
  render(<ProjectDetailsScreen project={project} />);

  const removeButton = screen.getByRole('button', { name: LABELS.repositoryRemoveFromProject });
  expect(removeButton).toBeDisabled();
  expect(screen.getByRole('button', { name: LABELS.repositoryRefresh })).toBeDisabled();

  await user.click(screen.getByRole('button', { name: LABELS.projectUnarchive }));

  expect(screen.getByText(LABELS.projectStateActive)).toBeVisible();
  expect(removeButton).toBeEnabled();

  await user.click(screen.getByRole('button', { name: LABELS.projectArchive }));

  expect(screen.getByText(LABELS.projectStateArchived)).toBeVisible();
  expect(removeButton).toBeDisabled();
});

test('ProjectDetailsScreen discards edits when Cancel is selected', async () => {
  const project = getProject('project-platform');
  const user = userEvent.setup();
  render(<ProjectDetailsScreen project={project} />);

  await user.tab();
  await user.tab();
  await user.keyboard('{Enter}');

  const nameInput = screen.getByRole('textbox', { name: LABELS.projectDetailsName });
  expect(nameInput).toHaveFocus();
  await user.clear(nameInput);
  await user.type(nameInput, 'Changed project');
  await user.click(screen.getByRole('button', { name: LABELS.projectEditCancel }));

  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  expect(screen.getByRole('heading', { name: project.name })).toBeVisible();
  expect(screen.getByRole('button', { name: LABELS.projectEdit })).toHaveFocus();
});

test('ProjectDetailsScreen applies editable values without changing catalog records', async () => {
  const project = getProject('project-platform');
  const user = userEvent.setup();
  render(<ProjectDetailsScreen project={project} />);

  await user.click(screen.getByRole('button', { name: LABELS.projectEdit }));

  const nameInput = screen.getByRole('textbox', { name: LABELS.projectDetailsName });
  await user.clear(nameInput);
  await user.paste('Platform operations');
  await user.click(screen.getByRole('combobox', { name: LABELS.projectDetailsState }));
  await user.click(screen.getByRole('option', { name: LABELS.projectStateArchived }));
  await user.click(screen.getByRole('button', { name: LABELS.projectEditApply }));

  expect(screen.getByRole('heading', { name: 'Platform operations' })).toBeVisible();
  expect(screen.getByText(LABELS.projectStateArchived)).toBeVisible();
  expect(project.name).toBe('Platform');
  expect(project.archivedAt).toBeNull();
});

test('ProjectDetailsScreen retains invalid project edits', async () => {
  const project = getProject('project-platform');
  const user = userEvent.setup();
  render(<ProjectDetailsScreen project={project} />);

  await user.click(screen.getByRole('button', { name: LABELS.projectEdit }));

  const nameInput = screen.getByRole('textbox', { name: LABELS.projectDetailsName });
  await user.clear(nameInput);
  await user.click(screen.getByRole('button', { name: LABELS.projectEditApply }));

  expect(nameInput).toBeInvalid();
  expect(nameInput).toHaveFocus();
  expect(nameInput).toHaveAccessibleDescription(LABELS.projectNameRequired);
});

test('ProjectDetailsScreen selects a project branch and reloads the fixed repository data', async () => {
  const project = getProject('project-platform');
  const user = userEvent.setup();
  const titleValues = { repository: 'virgo/service', branch: 'release/1.0' };
  const title = formatLabel(LABELS.repositoryBranchAction, titleValues);
  render(<ProjectDetailsScreen project={project} />);

  const repositoryItem = screen.getByRole('listitem', { name: 'virgo/service' });
  const branchButton = within(repositoryItem).getByRole('button', { name: title });
  expect(branchButton).toHaveTextContent('release/1.0');
  await user.click(branchButton);

  const branchInput = screen.getByRole('combobox', { name: LABELS.repositoryBranch });
  await user.clear(branchInput);
  await user.keyboard('{ArrowDown}');

  const branchValues = { branch: 'main' };
  const branchLabel = formatLabel(LABELS.repositoryBranchDefault, branchValues);
  await user.click(screen.getByRole('option', { name: branchLabel }));
  await user.click(screen.getByRole('button', { name: LABELS.repositoryUseBranch }));

  expect(branchButton).toHaveTextContent('main');

  await user.click(within(repositoryItem).getByRole('button', { name: LABELS.repositoryRefresh }));

  expect(within(repositoryItem).getByRole('button', { name: title })).toHaveTextContent(
    'release/1.0',
  );

  expect(screen.getByRole('status')).toBeVisible();
  await user.click(within(repositoryItem).getByRole('button', { name: LABELS.repositoryRefresh }));

  expect(screen.getByRole('status')).toBeVisible();
});

test('ProjectDetailsScreen preserves the repository when removal is confirmed', async () => {
  const project = getProject('project-platform');
  const user = userEvent.setup();
  render(<ProjectDetailsScreen project={project} />);

  const repositoryItem = screen.getByRole('listitem', { name: 'virgo/service' });
  const removeButton = within(repositoryItem).getByRole('button', {
    name: LABELS.repositoryRemoveFromProject,
  });

  await user.click(removeButton);

  const dialog = screen.getByRole('dialog');
  await user.click(
    within(dialog).getByRole('button', { name: LABELS.repositoryRemoveFromProject }),
  );

  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  expect(repositoryItem).toBeVisible();
  expect(removeButton).toHaveFocus();
});
