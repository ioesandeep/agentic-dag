import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, test, vi } from 'vitest';

import { RepositoryDetailsScreen } from '@/components/repositoryDetailsScreen/repositoryDetailsScreen';
import { RepositoryActionEnum } from '@/entities/catalog/repositoryAction';
import { MOCK_REPOSITORIES } from '@/mocks/catalogMocks';
import { LABELS } from '@/labels/en';
import { formatLabel } from '@/utils/formatLabel';
import { RepositoryActionDialog } from './repositoryActionDialog';

test('RepositoryActionDialog identifies the project and repository when removal opens', () => {
  const projectName = 'Platform';
  const repositoryName = 'virgo/service';
  const titleValues = { project: projectName, repository: repositoryName };
  const title = formatLabel(
    LABELS.repositoryRemoveFromProjectTitle,
    titleValues,
  );

  render(
    <RepositoryActionDialog
      projectName={projectName}
      repositoryName={repositoryName}
      isOpen
      onClose={vi.fn()}
      onConfirm={vi.fn()}
    />,
  );

  const dialog = screen.getByRole('dialog', { name: title });
  expect(dialog).toHaveAccessibleDescription(
    LABELS.repositoryRemoveFromProjectDescription,
  );
});

test.each(['{Escape}', '{Enter}', '{Tab}{Enter}'])(
  'RepositoryActionDialog requests dismissal or confirmation when the keyboard input is %s',
  async (keyboardInput) => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    const onConfirm = vi.fn();
    render(
      <RepositoryActionDialog
        projectName="Platform"
        repositoryName="virgo/service"
        isOpen
        onClose={onClose}
        onConfirm={onConfirm}
      />,
    );

    const dialog = screen.getByRole('dialog');
    const dialogQueries = within(dialog);
    const cancelButton = dialogQueries.getByRole('button', {
      name: LABELS.repositoryActionCancel,
    });

    await waitFor(() => expect(cancelButton).toHaveFocus());

    await user.keyboard(keyboardInput);

    if (keyboardInput === '{Tab}{Enter}') {
      expect(onConfirm).toHaveBeenCalledOnce();
      expect(onClose).not.toHaveBeenCalled();

      return;
    }

    expect(onClose).toHaveBeenCalledOnce();
    expect(onConfirm).not.toHaveBeenCalled();
  },
);

const [READY_REPOSITORY, CLONING_REPOSITORY] = MOCK_REPOSITORIES;
if (READY_REPOSITORY === undefined || CLONING_REPOSITORY === undefined) {
  throw new Error('The repository fixture is missing.');
}

test('RepositoryActionDialog confirms cancellation when a clone is active', async () => {
  const user = userEvent.setup();
  const onConfirm = vi.fn();
  const titleValues = { repository: CLONING_REPOSITORY.fullName };
  const title = formatLabel(LABELS.repositoryCancelTitle, titleValues);

  render(
    <RepositoryActionDialog
      variant={RepositoryActionEnum.CANCEL}
      repository={CLONING_REPOSITORY}
      isOpen
      onClose={vi.fn()}
      onConfirm={onConfirm}
    />,
  );

  const dialog = screen.getByRole('dialog', { name: title });
  expect(dialog).toHaveAccessibleDescription(
    LABELS.repositoryCancelDescription,
  );

  const dialogQueries = within(dialog);
  const confirmButton = dialogQueries.getByRole('button', {
    name: LABELS.repositoryCancelClone,
  });

  await user.click(confirmButton);

  expect(onConfirm).toHaveBeenCalledOnce();
});

test('RepositoryDetailsScreen preserves project memberships when removal is confirmed by keyboard', async () => {
  const user = userEvent.setup();
  const catalogSnapshot = structuredClone(MOCK_REPOSITORIES);
  render(<RepositoryDetailsScreen repositoryId="repository-service" />);

  const projectRow = screen.getByRole('listitem', { name: 'Default' });
  const projectQueries = within(projectRow);
  const removeButton = projectQueries.getByRole('button', {
    name: LABELS.repositoryRemoveFromProject,
  });

  removeButton.focus();

  await user.keyboard('{Enter}');

  const titleValues = {
    repository: READY_REPOSITORY.fullName,
    project: 'Default',
  };

  const title = formatLabel(
    LABELS.repositoryRemoveFromProjectTitle,
    titleValues,
  );

  const dialog = screen.getByRole('dialog', { name: title });

  const dialogQueries = within(dialog);
  const cancelButton = dialogQueries.getByRole('button', {
    name: LABELS.repositoryActionCancel,
  });

  await waitFor(() => expect(cancelButton).toHaveFocus());

  await user.keyboard('{Tab}{Enter}');

  await waitFor(() => expect(dialog).not.toBeInTheDocument());
  expect(removeButton).toHaveFocus();
  expect(MOCK_REPOSITORIES).toEqual(catalogSnapshot);
});

test('RepositoryDetailsScreen closes repair without changing the catalog when a local folder is confirmed', async () => {
  const user = userEvent.setup();
  const catalogSnapshot = structuredClone(MOCK_REPOSITORIES);
  render(<RepositoryDetailsScreen repositoryId="repository-tools" />);

  const repairButton = screen.getByRole('button', {
    name: LABELS.localCheckoutRepair,
  });

  await user.click(repairButton);

  const titleValues = { repository: 'virgo/tools' };
  const title = formatLabel(LABELS.repositoryRepairTitle, titleValues);
  const dialog = screen.getByRole('dialog', { name: title });

  const dialogQueries = within(dialog);
  const folderInput = dialogQueries.getByRole('textbox', {
    name: LABELS.localCheckoutFolder,
  });

  await user.type(folderInput, '/work/repaired-tools');
  await user.tab();

  const repositoryLink = dialogQueries.getByRole('link', {
    name: 'virgo/tools',
  });

  const confirmRepair = dialogQueries.getByRole('button', {
    name: LABELS.localCheckoutRepair,
  });

  expect(repositoryLink).toBeVisible();
  await user.click(confirmRepair);

  await waitFor(() => expect(dialog).not.toBeInTheDocument());
  expect(repairButton).toHaveFocus();
  expect(MOCK_REPOSITORIES).toEqual(catalogSnapshot);
});
