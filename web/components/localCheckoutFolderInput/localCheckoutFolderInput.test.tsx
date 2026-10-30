import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';

import { LABELS } from '@/labels/en';
import { LocalCheckoutFolderInput } from './localCheckoutFolderInput';

const PICKER_ERRORS = [new DOMException('Cancelled', 'AbortError'), new Error('Directory selection fails')];

afterEach(() => vi.unstubAllGlobals());

test.each(PICKER_ERRORS)('LocalCheckoutFolderInput preserves the Virgo path when the picker rejects with %s', async (error) => {
  const directoryPicker = vi.fn().mockRejectedValue(error);
  vi.stubGlobal('showDirectoryPicker', directoryPicker);

  const user = userEvent.setup();
  const onChange = vi.fn();
  const onBlur = vi.fn();
  const onSelect = vi.fn();

  render(<LocalCheckoutFolderInput value="/work/virgo" onChange={onChange} onBlur={onBlur} onSelect={onSelect} />);

  const browseButton = screen.getByRole('button', { name: LABELS.localCheckoutBrowse });
  await user.click(browseButton);

  const folderInput = screen.getByRole('textbox', { name: LABELS.localCheckoutFolder });
  const isCancellation = error instanceof DOMException && error.name === 'AbortError';
  const hint = isCancellation ? LABELS.localCheckoutFolderHint : LABELS.githubFolderPickerFailed;
  expect(folderInput).toHaveAccessibleDescription(hint);

  expect(folderInput).toHaveValue('/work/virgo');
  expect(onSelect).not.toHaveBeenCalled();
});

test('LocalCheckoutFolderInput offers path entry when the browser has no directory picker', async () => {
  vi.stubGlobal('showDirectoryPicker', undefined);

  const user = userEvent.setup();
  const onChange = vi.fn();
  const onBlur = vi.fn();
  const onSelect = vi.fn();

  render(<LocalCheckoutFolderInput value="" onChange={onChange} onBlur={onBlur} onSelect={onSelect} />);

  const browseButton = screen.getByRole('button', { name: LABELS.localCheckoutBrowse });
  await user.click(browseButton);

  const alert = screen.getByRole('alert');
  expect(alert).toHaveTextContent(LABELS.githubFolderPickerUnavailable);
  expect(onSelect).not.toHaveBeenCalled();
});
