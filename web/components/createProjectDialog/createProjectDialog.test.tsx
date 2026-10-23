import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, test, vi } from 'vitest';

import { LABELS } from '@/labels/en';
import { CreateProjectDialog } from './createProjectDialog';

test('CreateProjectDialog focuses the required name when the dialog opens', async () => {
  render(
    <CreateProjectDialog isOpen onClose={vi.fn()} onCreateProject={vi.fn()} />,
  );

  const nameInput = screen.getByRole('textbox', { name: /Name/ });
  const descriptionInput = screen.getByRole('textbox', {
    name: LABELS.projectDescription,
  });

  const dialog = screen.getByRole('dialog', { name: LABELS.projectCreate });

  await waitFor(() => expect(nameInput).toHaveFocus());

  expect(nameInput).toBeRequired();
  expect(descriptionInput).not.toBeRequired();
  expect(dialog).toBeVisible();
});

test('CreateProjectDialog rejects submission when the name contains only spaces', async () => {
  const user = userEvent.setup();
  const onCreateProject = vi.fn();
  render(
    <CreateProjectDialog
      isOpen
      onClose={vi.fn()}
      onCreateProject={onCreateProject}
    />,
  );

  const nameInput = screen.getByRole('textbox', { name: /Name/ });
  const createProjectButton = screen.getByRole('button', {
    name: LABELS.projectCreate,
  });

  await waitFor(() => expect(nameInput).toHaveFocus());

  await user.type(nameInput, '   ');
  await user.click(createProjectButton);

  expect(onCreateProject).not.toHaveBeenCalled();
  expect(nameInput).toHaveFocus();
  expect(nameInput).toBeInvalid();
  expect(nameInput).toHaveAccessibleDescription(LABELS.projectNameRequired);
});

test.each(['', 'Platform services'])(
  'CreateProjectDialog submits entered values when the description is "%s"',
  async (description) => {
    const user = userEvent.setup();
    const onCreateProject = vi.fn();
    const expectedInput = { name: 'Operations', description };
    render(
      <CreateProjectDialog
        isOpen
        onClose={vi.fn()}
        onCreateProject={onCreateProject}
      />,
    );

    const nameInput = screen.getByRole('textbox', { name: /Name/ });
    const createProjectButton = screen.getByRole('button', {
      name: LABELS.projectCreate,
    });

    await waitFor(() => expect(nameInput).toHaveFocus());

    await user.type(nameInput, '  Operations  ');
    await user.tab();
    await user.paste(description);

    await user.tab();
    await user.tab();
    expect(createProjectButton).toHaveFocus();
    await user.keyboard('{Enter}');

    expect(onCreateProject).toHaveBeenCalledExactlyOnceWith(expectedInput);
  },
);

test.each(['{Escape}', '{Tab}{Tab}{Enter}'])(
  'CreateProjectDialog restores focus when dismissed with %s',
  async (keyboardInput) => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    const renderDialog = (isOpen: boolean) => (
      <>
        <button>{LABELS.projectCreate}</button>
        <CreateProjectDialog
          isOpen={isOpen}
          onClose={onClose}
          onCreateProject={vi.fn()}
        />
      </>
    );

    const closedDialog = renderDialog(false);
    const { rerender } = render(closedDialog);
    await user.tab();

    const opener = screen.getByRole('button', { name: LABELS.projectCreate });
    const openDialog = renderDialog(true);
    rerender(openDialog);

    const nameInput = screen.getByRole('textbox', { name: /Name/ });
    await waitFor(() => expect(nameInput).toHaveFocus());

    await user.keyboard(keyboardInput);
    expect(onClose).toHaveBeenCalledOnce();
    rerender(closedDialog);

    await waitFor(() => expect(opener).toHaveFocus());
  },
);
