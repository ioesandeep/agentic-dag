'use client';

import Button from '@mui/material/Button';
import InputAdornment from '@mui/material/InputAdornment';
import TextField from '@mui/material/TextField';
import type { RefObject } from 'react';
import { useState } from 'react';

import { LABELS } from '@/labels/en';
import { formatLabel } from '@/utils/formatLabel';
import type { DirectoryPickerWindow } from './types';

interface CloneFolderInputProps {
  value: string;
  inputRef: RefObject<HTMLInputElement | null>;
  isDisabled: boolean;
  hasError: boolean;
  onChange: (cloneFolder: string) => void;
}

/**
 * Collects the typed host clone folder path independently of browser directory selection.
 */
export const CloneFolderInput = ({ value, inputRef, isDisabled, hasError, onChange }: CloneFolderInputProps) => {
  const [selectedFolderName, setSelectedFolderName] = useState<string | null>(null);
  const [pickerError, setPickerError] = useState<string | null>(null);
  const folderValues = { folder: selectedFolderName ?? '' };
  const selectionHint = formatLabel(LABELS.githubFolderSelected, folderValues);

  const folderHint = selectedFolderName === null ? LABELS.githubCloneFolderHint : selectionHint;
  const validationHint = hasError ? LABELS.githubCloneFolderRequired : folderHint;
  const helperText = pickerError ?? validationHint;

  const hasInputError = hasError || pickerError !== null;
  const helperRole = pickerError === null ? undefined : 'alert';

  const handleBrowse = async () => {
    const pickerWindow: DirectoryPickerWindow = window;
    if (pickerWindow.showDirectoryPicker === undefined) {
      setPickerError(LABELS.githubFolderPickerUnavailable);

      return;
    }

    try {
      const directoryHandle = await pickerWindow.showDirectoryPicker();
      setSelectedFolderName(directoryHandle.name);
      setPickerError(null);
      inputRef.current?.focus();
    } catch (error: unknown) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        return;
      }

      setPickerError(LABELS.githubFolderPickerFailed);
    }
  };

  const handleChange = (cloneFolder: string) => {
    setPickerError(null);
    onChange(cloneFolder);
  };

  const inputSlotProps = {
    input: { endAdornment: (
      <InputAdornment position="end">
        <Button onClick={handleBrowse} disabled={isDisabled}>{LABELS.githubFolderBrowse}</Button>
      </InputAdornment>
    ) },
    formHelperText: { role: helperRole },
  };

  return (
    <TextField
      required fullWidth label={LABELS.githubCloneFolder} value={value}
      inputRef={inputRef} error={hasInputError} helperText={helperText}
      disabled={isDisabled} onChange={(event) => handleChange(event.target.value)}
      slotProps={inputSlotProps}
    />
  );
};
