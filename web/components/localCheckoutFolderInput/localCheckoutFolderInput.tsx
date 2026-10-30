'use client';

import Button from '@mui/material/Button';
import InputAdornment from '@mui/material/InputAdornment';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import { useRef, useState } from 'react';

import type { DirectoryPickerWindow } from '@/components/cloneFolderInput/types';
import { LABELS } from '@/labels/en';
import { formatLabel } from '@/utils/formatLabel';

interface LocalCheckoutFolderInputProps {
  value: string;
  onChange: (folder: string) => void;
  onBlur: () => void;
  onSelect: () => void;
}

/**
 * Collects folder selections for local checkout registration.
 */
export const LocalCheckoutFolderInput = ({ value, onChange, onBlur, onSelect }: LocalCheckoutFolderInputProps) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [selectedFolderName, setSelectedFolderName] = useState<string | null>(null);
  const [pickerError, setPickerError] = useState<string | null>(null);
  const folderValues = { folder: selectedFolderName ?? '' };

  const selectionHint = formatLabel(LABELS.localCheckoutFolderSelected, folderValues);
  const helperText = pickerError ?? LABELS.localCheckoutFolderHint;
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

      onSelect();
      inputRef.current?.focus();
    } catch (error: unknown) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        return;
      }

      setPickerError(LABELS.githubFolderPickerFailed);
    }
  };

  const handleChange = (folder: string) => {
    setPickerError(null);
    onChange(folder);
  };

  const inputSlotProps = {
    input: { endAdornment: <InputAdornment position="end"><Button autoFocus onClick={handleBrowse}>{LABELS.localCheckoutBrowse}</Button></InputAdornment> },
    formHelperText: { role: helperRole },
  };

  return (
    <Stack spacing={1}>
      <TextField fullWidth label={LABELS.localCheckoutFolder} value={value} inputRef={inputRef} helperText={helperText} error={pickerError !== null} onChange={(event) => handleChange(event.target.value)} onBlur={onBlur} slotProps={inputSlotProps} />
      {selectedFolderName !== null && <Typography variant="body2" color="text.secondary" role="status">{selectionHint}</Typography>}
    </Stack>
  );
};
