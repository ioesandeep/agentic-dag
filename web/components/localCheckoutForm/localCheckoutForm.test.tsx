import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';

import { AddRepositoryActionButton } from '@/components/addRepositoryActionButton/addRepositoryActionButton';
import { LABELS } from '@/labels/en';
import { MOCK_PROJECTS, MOCK_REPOSITORIES, MOCK_REPOSITORY_INSPECTION } from '@/mocks/catalogMocks';
import { formatLabel } from '@/utils/formatLabel';
import { LocalCheckoutForm } from './localCheckoutForm';

const [PROJECT] = MOCK_PROJECTS;
if (PROJECT === undefined) {
  throw new Error('The project fixture is missing.');
}

afterEach(() => vi.unstubAllGlobals());

test.each([[true, true], [true, false], [false, true]])('LocalCheckoutForm inspects the folder on blur with project context %s and multiple remotes %s', async (hasProject, hasMultipleRemotes) => {
  const user = userEvent.setup();
  const onClose = vi.fn();
  const project = hasProject ? MOCK_PROJECTS[1] : undefined;
  const remotes = hasMultipleRemotes ? MOCK_REPOSITORY_INSPECTION.remotes : MOCK_REPOSITORY_INSPECTION.remotes.slice(0, 1);

  const inspections = [{ ...MOCK_REPOSITORY_INSPECTION, remotes }];
  render(<LocalCheckoutForm onClose={onClose} project={project} inspections={inspections} />);

  const folderInput = screen.getByRole('textbox', { name: LABELS.localCheckoutFolder });
  const addButton = screen.getByRole('button', { name: LABELS.localCheckoutAdd });
  expect(addButton).toBeDisabled();

  await user.type(folderInput, '/work/virgo');
  await user.tab();

  const repositoryLink = screen.getByRole('link', { name: 'virgo/console' });
  const remoteSelect = screen.queryByRole('combobox', { name: LABELS.localCheckoutRemote });
  expect(repositoryLink).toBeVisible();
  if (hasMultipleRemotes) {
    expect(remoteSelect).toHaveTextContent('origin');
  } else {
    expect(remoteSelect).not.toBeInTheDocument();
  }

  expect(addButton).toBeEnabled();

  const branchSelect = screen.queryByRole('combobox', { name: LABELS.repositoryBranch });
  const existingRegistration = screen.queryByRole('group', { name: LABELS.localCheckoutExisting });
  if (hasProject) {
    expect(branchSelect).toHaveTextContent('main (default)');
    expect(existingRegistration).not.toBeInTheDocument();
    if (hasMultipleRemotes) {
      await user.tab();
    }

    await user.tab();
    expect(branchSelect).toHaveFocus();
  } else {
    expect(branchSelect).not.toBeInTheDocument();
    expect(existingRegistration).toBeVisible();
  }

  await user.type(folderInput, '/other');

  const staleLink = screen.queryByRole('link');
  const gitRoot = screen.queryByText(LABELS.localCheckoutGitRoot);
  const staleBranchSelect = screen.queryByRole('combobox', { name: LABELS.repositoryBranch });
  expect(staleLink).not.toBeInTheDocument();

  expect(gitRoot).not.toBeInTheDocument();
  expect(staleBranchSelect).not.toBeInTheDocument();
  expect(addButton).toBeDisabled();
  expect(onClose).not.toHaveBeenCalled();
});

test('LocalCheckoutForm inspects the repository when the selected remote changes', async () => {
  const user = userEvent.setup();
  const onClose = vi.fn();
  render(<LocalCheckoutForm onClose={onClose} />);

  const folderInput = screen.getByRole('textbox', { name: LABELS.localCheckoutFolder });
  await user.type(folderInput, '/work/virgo');
  await user.tab();

  const remoteSelect = screen.getByRole('combobox', { name: LABELS.localCheckoutRemote });
  await user.click(remoteSelect);

  const upstreamOption = screen.getByRole('option', { name: /upstream/ });
  await user.click(upstreamOption);

  const existingRegistration = screen.queryByText(LABELS.localCheckoutExisting);
  const addButton = screen.getByRole('button', { name: LABELS.localCheckoutAdd });
  expect(existingRegistration).not.toBeInTheDocument();

  const repositoryLink = screen.getByRole('link', { name: 'virgo/console-template' });
  expect(repositoryLink).toHaveAttribute('href', 'https://github.com/virgo/console-template');
  expect(addButton).toBeEnabled();
});

test.each([true, false])('LocalCheckoutForm prevents Add when the inspection has no identity and remote support is %s', async (supported) => {
  const user = userEvent.setup();
  const remotes = [{ name: 'origin', url: 'https://example.com/virgo/console.git', supported }];
  const inspections = [{ ...MOCK_REPOSITORY_INSPECTION, remotes, identity: null, existingRepository: null }];
  const onClose = vi.fn();

  render(<LocalCheckoutForm onClose={onClose} inspections={inspections} />);

  const folderInput = screen.getByRole('textbox', { name: LABELS.localCheckoutFolder });
  await user.type(folderInput, '/work/virgo');
  await user.tab();

  const guidance = screen.getByText(LABELS.localCheckoutIdentityRequired);
  const addButton = screen.getByRole('button', { name: LABELS.localCheckoutAdd });
  expect(guidance).toBeVisible();
  expect(addButton).toBeDisabled();
});

test('LocalCheckoutForm validates the entered branch name when a project is provided', async () => {
  const user = userEvent.setup();
  const onClose = vi.fn();
  render(<LocalCheckoutForm onClose={onClose} project={MOCK_PROJECTS[1]} />);

  const folderInput = screen.getByRole('textbox', { name: LABELS.localCheckoutFolder });
  await user.type(folderInput, '/work/virgo');
  await user.tab();

  const branchSelect = screen.getByRole('combobox', { name: LABELS.repositoryBranch });
  await user.click(branchSelect);

  const newBranchOption = screen.getByRole('option', { name: LABELS.repositoryAddBranch });
  await user.click(newBranchOption);

  const branchInput = screen.getByRole('textbox', { name: LABELS.repositoryNewBranch });
  const addButton = screen.getByRole('button', { name: LABELS.localCheckoutAdd });
  await user.type(branchInput, 'invalid branch');
  await user.click(addButton);

  expect(branchInput).toHaveFocus();
  expect(branchInput).toHaveAccessibleDescription(LABELS.repositoryBranchInvalid);
  expect(onClose).not.toHaveBeenCalled();

  await user.clear(branchInput);
  await user.type(branchInput, 'feature/local-folder');
  await user.click(folderInput);

  await user.tab();
  expect(branchInput).toHaveValue('feature/local-folder');

  await user.click(addButton);

  expect(onClose).toHaveBeenCalledOnce();
  expect(MOCK_REPOSITORY_INSPECTION.branches).not.toContain('feature/local-folder');
});

test('LocalCheckoutForm prevents repair when the inspected identity differs from the expected repository', async () => {
  const user = userEvent.setup();
  const onClose = vi.fn();
  const { rerender } = render(<LocalCheckoutForm onClose={onClose} repairRepository={MOCK_REPOSITORIES[0]} />);

  const folderInput = screen.getByRole('textbox', { name: LABELS.localCheckoutFolder });
  await user.type(folderInput, '/work/virgo');
  await user.tab();

  const warning = screen.getByRole('alert');
  const repairButton = screen.getByRole('button', { name: LABELS.localCheckoutRepair });
  expect(warning).toHaveTextContent(LABELS.localCheckoutMismatch);
  expect(repairButton).toBeDisabled();

  rerender(<LocalCheckoutForm onClose={onClose} repairRepository={MOCK_REPOSITORY_INSPECTION.existingRepository ?? undefined} />);
  await user.click(repairButton);

  expect(onClose).toHaveBeenCalledOnce();
});

test('LocalCheckoutForm closes without changing the catalog when the menu flow uses the keyboard', async () => {
  const user = userEvent.setup();
  const catalogSnapshot = structuredClone(MOCK_REPOSITORIES);
  const directoryHandle = { name: 'console' };
  const directoryPicker = vi.fn().mockResolvedValue(directoryHandle);

  vi.stubGlobal('showDirectoryPicker', directoryPicker);
  render(<AddRepositoryActionButton project={PROJECT} />);

  const addRepositoryButton = screen.getByRole('button', { name: LABELS.repositoryAdd });
  await user.tab();
  await user.keyboard('{Enter}{End}{Enter}');

  const dialog = screen.getByRole('dialog', { name: LABELS.localCheckoutTitle });
  const browseButton = screen.getByRole('button', { name: LABELS.localCheckoutBrowse });
  const folderInput = screen.getByRole('textbox', { name: LABELS.localCheckoutFolder });
  expect(dialog).toBeVisible();

  await waitFor(() => expect(browseButton).toHaveFocus());
  await user.keyboard('{Enter}');

  const repositoryLink = screen.getByRole('link', { name: 'virgo/console' });
  expect(repositoryLink).toBeVisible();
  expect(folderInput).toHaveValue('');
  expect(folderInput).toHaveFocus();

  const folderValues = { folder: 'console' };
  const selectionHint = formatLabel(LABELS.localCheckoutFolderSelected, folderValues);
  const selectionStatus = screen.getByRole('status');
  expect(selectionStatus).toHaveTextContent(selectionHint);

  await user.keyboard('{Tab}{Tab}{Tab}{Tab}{Tab}{Tab}{Enter}');

  await waitFor(() => expect(dialog).not.toBeInTheDocument());
  expect(addRepositoryButton).toHaveFocus();
  expect(MOCK_REPOSITORIES).toEqual(catalogSnapshot);

  await user.keyboard('{Enter}{End}{Enter}');

  const reopenedDialog = screen.getByRole('dialog', { name: LABELS.localCheckoutTitle });
  await user.keyboard('{Escape}');

  await waitFor(() => expect(reopenedDialog).not.toBeInTheDocument());
  expect(addRepositoryButton).toHaveFocus();
});

test('LocalCheckoutForm resets the remote and branch when another directory is selected', async () => {
  const directoryHandle = { name: 'console' };
  const directoryPicker = vi.fn().mockResolvedValue(directoryHandle);
  vi.stubGlobal('showDirectoryPicker', directoryPicker);

  const user = userEvent.setup();
  const onClose = vi.fn();
  render(<LocalCheckoutForm onClose={onClose} project={MOCK_PROJECTS[1]} />);

  const browseButton = screen.getByRole('button', { name: LABELS.localCheckoutBrowse });
  await user.click(browseButton);

  const remoteSelect = screen.getByRole('combobox', { name: LABELS.localCheckoutRemote });
  await user.click(remoteSelect);

  const upstreamOption = screen.getByRole('option', { name: /upstream/ });
  await user.click(upstreamOption);

  const branchSelect = screen.getByRole('combobox', { name: LABELS.repositoryBranch });
  await user.click(branchSelect);

  const newBranchOption = screen.getByRole('option', { name: LABELS.repositoryAddBranch });
  await user.click(newBranchOption);

  const branchInput = screen.getByRole('textbox', { name: LABELS.repositoryNewBranch });
  await user.type(branchInput, 'feature/local-folder');

  const otherDirectoryHandle = { name: 'other-console' };
  directoryPicker.mockResolvedValue(otherDirectoryHandle);

  await user.click(browseButton);

  const resetBranchSelect = screen.getByRole('combobox', { name: LABELS.repositoryBranch });
  const newBranchInput = screen.queryByRole('textbox', { name: LABELS.repositoryNewBranch });
  expect(resetBranchSelect).toHaveTextContent('main (default)');
  expect(newBranchInput).not.toBeInTheDocument();

  expect(remoteSelect).toHaveTextContent('origin');
});
