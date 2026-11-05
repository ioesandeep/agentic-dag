import {
  act,
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';

import { LABELS, REPOSITORY_STATUS_LABELS } from '@/labels/en';
import { MOCK_REPOSITORIES } from '@/mocks/catalogMocks';
import { formatLabel } from '@/utils/formatLabel';
import { RepositoriesScreen } from './repositoriesScreen';

const CLONE_COMPLETION_WAIT_MS = 2000;
const ARCHIVE_QUERY = { name: LABELS.repositoriesShowArchived };
const LEGACY_QUERY = { name: 'virgo/legacy' };
const ADD_QUERY = { name: LABELS.repositoryAdd };
const FROM_LIST_QUERY = { name: LABELS.repositoryAddFromList };
const REPOSITORY_QUERY = { name: LABELS.githubRepository };
const CLONE_QUERY = { name: LABELS.githubClone };
const DONE_QUERY = { name: LABELS.githubDone };
const BRANCH_QUERY = { name: LABELS.repositoryBranch };
const FOLDER_QUERY = { name: LABELS.localCheckoutFolder };
const LOCAL_ADD_QUERY = { name: LABELS.localCheckoutAdd };
const TIMER_CONFIG = { shouldAdvanceTime: true };
const USER_CONFIG = { advanceTimers: vi.advanceTimersByTime };

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => '/repositories',
}));

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

test('RepositoriesScreen displays active repositories with status and project branches', () => {
  render(<RepositoriesScreen />);

  const activeRepositories = MOCK_REPOSITORIES.filter(
    (repository) => repository.archivedAt === null,
  );

  const articles = screen.getAllByRole('article');
  expect(articles).toHaveLength(activeRepositories.length);
  for (const repository of activeRepositories) {
    const articleQuery = { name: repository.fullName };
    const article = screen.getByRole('article', articleQuery);
    const repositoryQueries = within(article);

    const repositoryValues = { repository: repository.fullName };
    const detailsLabel = formatLabel(
      LABELS.repositoryDetailsOpen,
      repositoryValues,
    );

    const statusLabel = REPOSITORY_STATUS_LABELS[repository.presentationStatus];
    const status = repositoryQueries.getByText(statusLabel);
    const detailsQuery = { name: detailsLabel };
    const detailsLink = repositoryQueries.getByRole('link', detailsQuery);

    expect(status).toBeVisible();
    expect(detailsLink).toHaveAttribute(
      'href',
      `/repositories/${repository.id}`,
    );

    for (const { project, branch } of repository.memberships) {
      const membershipValues = { project: project.name, branch };
      const membershipLabel = formatLabel(
        LABELS.repositoryProjectBranch,
        membershipValues,
      );

      const membershipText = repositoryQueries.getByText(membershipLabel);
      expect(membershipText).toBeVisible();
    }
  }
});

test('RepositoriesScreen includes archived registrations when the switch is enabled by keyboard', async () => {
  const user = userEvent.setup();
  render(<RepositoriesScreen />);

  const archiveSwitch = screen.getByRole('switch', ARCHIVE_QUERY);
  expect(archiveSwitch).not.toBeChecked();

  const archivedArticle = screen.queryByRole('article', LEGACY_QUERY);
  expect(archivedArticle).not.toBeInTheDocument();

  await user.tab();
  await user.tab();
  await user.tab();
  await user.tab();

  await user.tab();
  expect(archiveSwitch).toHaveFocus();
  await user.keyboard(' ');

  expect(archiveSwitch).toBeChecked();

  const archivedArticleAfterToggle = screen.getByRole('article', LEGACY_QUERY);
  const articles = screen.getAllByRole('article');
  expect(archivedArticleAfterToggle).toHaveTextContent(
    REPOSITORY_STATUS_LABELS.archived,
  );

  expect(articles).toHaveLength(MOCK_REPOSITORIES.length);

  await user.keyboard(' ');

  const archivedArticleAfterReset = screen.queryByRole('article', LEGACY_QUERY);
  expect(archivedArticleAfterReset).not.toBeInTheDocument();
});

test.each([LABELS.repositoryAddGithub, LABELS.repositoryAddLocal])(
  'RepositoriesScreen confirms %s without a project branch or catalog changes',
  async (source) => {
    vi.useFakeTimers(TIMER_CONFIG);

    const user = userEvent.setup(USER_CONFIG);
    const catalogSnapshot = structuredClone(MOCK_REPOSITORIES);
    render(<RepositoriesScreen />);

    await user.tab();
    await user.tab();
    await user.tab();
    await user.tab();

    await user.tab();
    await user.tab();

    const addButton = screen.getByRole('button', ADD_QUERY);
    expect(addButton).toHaveFocus();
    await user.keyboard('{Enter}');

    const menuItems = screen.getAllByRole('menuitem');
    const repositoryPickerItem = screen.queryByRole(
      'menuitem',
      FROM_LIST_QUERY,
    );

    expect(menuItems).toHaveLength(2);
    expect(repositoryPickerItem).not.toBeInTheDocument();
    if (source === LABELS.repositoryAddLocal) {
      await user.keyboard('{End}');
    }

    await user.keyboard('{Enter}');

    const dialog = screen.getByRole('dialog');
    if (source === LABELS.repositoryAddGithub) {
      const repositoryInput = screen.getByRole('combobox', REPOSITORY_QUERY);
      await waitFor(() => expect(repositoryInput).toHaveFocus());
      await user.type(repositoryInput, 'virgo/api');
      await user.tab();

      const cloneButton = screen.getByRole('button', CLONE_QUERY);
      await user.click(cloneButton);
      act(() => vi.advanceTimersByTime(CLONE_COMPLETION_WAIT_MS));

      const doneButton = screen.getByRole('button', DONE_QUERY);
      const branchSelect = screen.queryByRole('combobox', BRANCH_QUERY);
      expect(branchSelect).not.toBeInTheDocument();
      await user.click(doneButton);
    } else {
      const folderInput = screen.getByRole('textbox', FOLDER_QUERY);
      await user.type(folderInput, '/work/virgo/console');
      await user.tab();

      const branchSelect = screen.queryByRole('combobox', BRANCH_QUERY);
      expect(branchSelect).not.toBeInTheDocument();

      const confirmButton = screen.getByRole('button', LOCAL_ADD_QUERY);
      await user.click(confirmButton);
    }

    await waitFor(() => expect(dialog).not.toBeInTheDocument());

    expect(addButton).toHaveFocus();
    expect(MOCK_REPOSITORIES).toEqual(catalogSnapshot);

    const articles = screen.getAllByRole('article');
    const activeRepositories = catalogSnapshot.filter(
      (repository) => repository.archivedAt === null,
    );

    expect(articles).toHaveLength(activeRepositories.length);
  },
);

test('RepositoriesScreen displays retry feedback when Retry clone is selected', async () => {
  const user = userEvent.setup();
  render(<RepositoriesScreen />);

  const retryQuery = { name: LABELS.repositoryRetryClone };
  const retryButton = screen.getByRole('button', retryQuery);
  await user.click(retryButton);

  const repositoryValues = { repository: 'virgo/connector' };
  const notice = formatLabel(
    LABELS.repositoryCloneRetryUnavailable,
    repositoryValues,
  );

  const noticeText = screen.getByText(notice);
  expect(noticeText).toBeVisible();
});
