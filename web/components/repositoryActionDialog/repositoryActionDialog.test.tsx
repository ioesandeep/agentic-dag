import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, test, vi } from 'vitest';

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

  expect(
    screen.getByRole('dialog', { name: title }),
  ).toHaveAccessibleDescription(LABELS.repositoryRemoveFromProjectDescription);
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
    const cancelButton = within(dialog).getByRole('button', {
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
