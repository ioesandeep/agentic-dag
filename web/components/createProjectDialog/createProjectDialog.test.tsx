import Button from '@mui/material/Button';
import { ThemeProvider } from '@mui/material/styles';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { expect, test, vi } from 'vitest';

import type { CreateProjectRequest } from '@/entities/catalog/projectRequest';
import { LABELS } from '@/labels/en';
import { theme } from '@/theme/theme';

import { CreateProjectDialog } from './createProjectDialog';
import type { CreateProjectDialogProps } from './types';

const CREATE_QUERY = { name: LABELS.projectCreate };
const NAME_QUERY = { name: LABELS.projectName };
const DESCRIPTION_QUERY = { name: LABELS.projectDescriptionOptional };
const PENDING_QUERY = { name: LABELS.projectCreatePending };
const EMPTY_REQUEST = { name: '' };
const PROJECT_REQUEST = { name: 'Virgo', description: 'Platform development' };
const ENTRY_KEYS = '{Enter}Virgo{Tab}Platform development';
const DISMISSAL_ACTIONS = [
  { name: 'Escape', keyboard: '{Escape}' },
  { name: 'Cancel', keyboard: '{Tab}{Tab}{Enter}' },
];

type DialogTestProps = Partial<
  Pick<CreateProjectDialogProps, 'isPending' | 'nameError' | 'failureDetail'>
> &
  Pick<CreateProjectDialogProps, 'onSubmit'>;

const DialogTest = (dialogTestProps: DialogTestProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [createProjectRequest, setCreateProjectRequest] =
    useState<CreateProjectRequest>(EMPTY_REQUEST);
  const handleOpen = () => setIsOpen(true);
  const handleClose = () => setIsOpen(false);

  return (
    <ThemeProvider theme={theme}>
      <Button onClick={handleOpen}>{LABELS.projectCreate}</Button>
      <CreateProjectDialog
        {...dialogTestProps}
        isPending={dialogTestProps.isPending ?? false}
        isOpen={isOpen}
        createProjectRequest={createProjectRequest}
        onChange={setCreateProjectRequest}
        onClose={handleClose}
      />
    </ThemeProvider>
  );
};

test('CreateProjectDialog submits metadata by keyboard when the required name is provided', async () => {
  const user = userEvent.setup();
  const onSubmit = vi.fn();
  const dialog = <DialogTest onSubmit={onSubmit} />;
  render(dialog);
  await user.tab();
  await user.keyboard('{Enter}{Tab}{Tab}{Tab}{Enter}');
  const nameInput = screen.getByRole('textbox', NAME_QUERY);
  expect(nameInput).toHaveFocus();
  expect(nameInput).toHaveAccessibleDescription(LABELS.projectNameRequired);
  expect(onSubmit).not.toHaveBeenCalled();

  await user.keyboard('Virgo{Tab}Platform development{Tab}{Tab}{Enter}');

  expect(onSubmit).toHaveBeenCalledExactlyOnceWith(PROJECT_REQUEST);
});

test('CreateProjectDialog preserves metadata when creation returns a field error', async () => {
  const user = userEvent.setup();
  const onSubmit = vi.fn();
  const dialog = <DialogTest onSubmit={onSubmit} />;
  const { rerender } = render(dialog);
  await user.tab();
  await user.keyboard(ENTRY_KEYS);
  await user.keyboard('{Tab}{Tab}{Enter}');
  const failedDialog = (
    <DialogTest
      onSubmit={onSubmit}
      nameError={LABELS.projectNameDuplicate}
      failureDetail={LABELS.projectCreateFailed}
    />
  );

  rerender(failedDialog);

  const nameInput = screen.getByRole('textbox', NAME_QUERY);
  const descriptionInput = screen.getByRole('textbox', DESCRIPTION_QUERY);
  const alert = screen.getByRole('alert');
  expect(nameInput).toHaveValue(PROJECT_REQUEST.name);
  expect(descriptionInput).toHaveValue(PROJECT_REQUEST.description);
  expect(nameInput).toHaveFocus();
  expect(nameInput).toHaveAttribute('aria-invalid', 'true');
  expect(nameInput).toHaveAccessibleDescription(LABELS.projectNameDuplicate);
  expect(alert).toHaveTextContent(LABELS.projectCreateFailed);
});

test('CreateProjectDialog prevents changes when creation is pending', async () => {
  const user = userEvent.setup();
  const onSubmit = vi.fn();
  const dialog = <DialogTest onSubmit={onSubmit} />;
  const { rerender } = render(dialog);
  await user.tab();
  await user.keyboard(ENTRY_KEYS);
  const pendingDialog = <DialogTest onSubmit={onSubmit} isPending />;
  rerender(pendingDialog);

  await user.keyboard('changed{Enter}{Escape}{Tab}{Tab}{Enter}');

  const descriptionInput = screen.getByRole('textbox', DESCRIPTION_QUERY);
  const pendingButton = screen.getByRole('button', PENDING_QUERY);
  expect(descriptionInput).toHaveValue(PROJECT_REQUEST.description);
  expect(pendingButton).toBeDisabled();
  expect(pendingButton).toHaveAttribute('aria-busy', 'true');
  expect(onSubmit).not.toHaveBeenCalled();
});

test.each(DISMISSAL_ACTIONS)(
  'CreateProjectDialog restores focus to its invoker when $name dismisses it',
  async ({ keyboard }) => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    const dialog = <DialogTest onSubmit={onSubmit} />;
    render(dialog);
    const invoker = screen.getByRole('button', CREATE_QUERY);
    await user.tab();
    await user.keyboard('{Enter}');

    await user.keyboard(keyboard);

    await waitFor(() => expect(invoker).toHaveFocus());
  },
);
