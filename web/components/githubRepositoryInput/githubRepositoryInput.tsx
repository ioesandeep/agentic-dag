'use client';

import Autocomplete from '@mui/material/Autocomplete';
import TextField from '@mui/material/TextField';
import type { Ref } from 'react';

import { LABELS } from '@/labels/en';
import { MOCK_GITHUB_REPOSITORY_NAMES } from '@/mocks/catalogMocks';
import { getGithubRepositorySuggestions } from './utils';

interface GithubRepositoryInputProps {
  value: string;
  inputRef: Ref<HTMLInputElement>;
  isDisabled: boolean;
  hasError: boolean;
  onChange: (repositoryInput: string) => void;
}

/**
 * Suggests GitHub repositories for a clone.
 */
export const GithubRepositoryInput = ({ value, inputRef, isDisabled, hasError, onChange }: GithubRepositoryInputProps) => {
  const helperText = hasError ? LABELS.githubRepositoryInvalid : LABELS.githubRepositoryHint;

  return (
    <Autocomplete
      freeSolo
      forcePopupIcon
      disabled={isDisabled}
      options={MOCK_GITHUB_REPOSITORY_NAMES}
      value={value}
      inputValue={value}
      clearText={LABELS.githubRepositoryClear}
      openText={LABELS.githubRepositorySuggestionsOpen}
      closeText={LABELS.githubRepositorySuggestionsClose}
      onChange={(_, repositoryInput) => onChange(repositoryInput ?? '')}
      onInputChange={(_, repositoryInput) => onChange(repositoryInput)}
      filterOptions={(repositoryNames, filterState) => getGithubRepositorySuggestions(repositoryNames, filterState.inputValue)}
      renderInput={(autocompleteInput) => (
        <TextField
          {...autocompleteInput}
          autoFocus required label={LABELS.githubRepository}
          inputRef={inputRef} error={hasError} helperText={helperText}
        />
      )}
    />
  );
};
