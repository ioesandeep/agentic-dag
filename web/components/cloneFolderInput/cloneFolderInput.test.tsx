import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createRef } from 'react';
import { afterEach, expect, test, vi } from 'vitest';

import { LABELS } from '@/labels/en';
import { formatLabel } from '@/utils/formatLabel';
import { CloneFolderInput } from './cloneFolderInput';

afterEach(() => vi.unstubAllGlobals());

test('CloneFolderInput identifies a native selection without replacing the host path', async () => {
  const directoryHandle = { name: 'checkout' };
  const directoryPicker = vi.fn().mockResolvedValue(directoryHandle);
  vi.stubGlobal('showDirectoryPicker', directoryPicker);

  const inputRef = createRef<HTMLInputElement>();
  const user = userEvent.setup();
  const onChange = vi.fn();
  render(<CloneFolderInput value="/work/virgo/api" inputRef={inputRef} isDisabled={false} hasError={false} onChange={onChange} />);

  await user.tab();
  await user.tab();
  await user.keyboard('{Enter}');

  const folderInput = screen.getByRole('textbox', { name: LABELS.githubCloneFolder });
  const folderValues = { folder: 'checkout' };
  const selectionHint = formatLabel(LABELS.githubFolderSelected, folderValues);
  expect(folderInput).toHaveAccessibleDescription(selectionHint);

  expect(folderInput).toHaveFocus();
  expect(folderInput).toHaveValue('/work/virgo/api');
  expect(onChange).not.toHaveBeenCalled();
  expect(directoryPicker).toHaveBeenCalledOnce();
});

test('CloneFolderInput preserves the host path when native selection is cancelled', async () => {
  const cancellation = new DOMException('Cancelled', 'AbortError');
  const directoryPicker = vi.fn().mockRejectedValue(cancellation);
  vi.stubGlobal('showDirectoryPicker', directoryPicker);

  const user = userEvent.setup();
  const inputRef = createRef<HTMLInputElement>();
  render(<CloneFolderInput value="/work/virgo/api" inputRef={inputRef} isDisabled={false} hasError={false} onChange={vi.fn()} />);

  await user.click(screen.getByRole('button', { name: LABELS.githubFolderBrowse }));

  const folderInput = screen.getByRole('textbox', { name: LABELS.githubCloneFolder });
  expect(folderInput).toHaveValue('/work/virgo/api');
  expect(folderInput).toHaveAccessibleDescription(LABELS.githubCloneFolderHint);
  expect(folderInput).not.toBeInvalid();
});

test('CloneFolderInput displays a manual entry instruction when native selection is unsupported', async () => {
  vi.stubGlobal('showDirectoryPicker', undefined);

  const user = userEvent.setup();
  const inputRef = createRef<HTMLInputElement>();
  render(<CloneFolderInput value="/work/virgo/api" inputRef={inputRef} isDisabled={false} hasError={false} onChange={vi.fn()} />);

  await user.click(screen.getByRole('button', { name: LABELS.githubFolderBrowse }));

  expect(screen.getByRole('textbox', { name: LABELS.githubCloneFolder })).toHaveAccessibleDescription(LABELS.githubFolderPickerUnavailable);
  expect(screen.getByRole('alert')).toHaveTextContent(LABELS.githubFolderPickerUnavailable);
});

test('CloneFolderInput permits another selection when the native picker fails', async () => {
  const pickerError = new Error('Directory selection fails');
  const directoryHandle = { name: 'checkout' };
  const directoryPicker = vi.fn().mockRejectedValueOnce(pickerError).mockResolvedValueOnce(directoryHandle);
  vi.stubGlobal('showDirectoryPicker', directoryPicker);

  const user = userEvent.setup();
  const inputRef = createRef<HTMLInputElement>();
  render(<CloneFolderInput value="/work/virgo/api" inputRef={inputRef} isDisabled={false} hasError={false} onChange={vi.fn()} />);

  const browseButton = screen.getByRole('button', { name: LABELS.githubFolderBrowse });
  const folderInput = screen.getByRole('textbox', { name: LABELS.githubCloneFolder });
  await user.click(browseButton);

  expect(folderInput).toHaveAccessibleDescription(LABELS.githubFolderPickerFailed);
  expect(screen.getByRole('alert')).toHaveTextContent(LABELS.githubFolderPickerFailed);

  await user.click(browseButton);

  expect(folderInput).not.toBeInvalid();
  expect(folderInput).toHaveValue('/work/virgo/api');
});
