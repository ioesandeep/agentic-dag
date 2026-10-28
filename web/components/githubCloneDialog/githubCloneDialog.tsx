'use client';

import Box from '@mui/material/Box';
import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import type { FormEvent } from 'react';
import { useEffect, useId, useRef, useState } from 'react';

import { BranchSelect } from '@/components/branchSelect/branchSelect';
import { CloneFolderInput } from '@/components/cloneFolderInput/cloneFolderInput';
import { isValidBranchName } from '@/components/branchButton/utils';
import { GithubCloneFeedback } from '@/components/githubCloneFeedback/githubCloneFeedback';
import { GithubImportFeedback } from '@/components/githubImportFeedback/githubImportFeedback';
import { GithubRepositoryInput } from '@/components/githubRepositoryInput/githubRepositoryInput';
import type { GithubAccountStatus } from '@/entities/catalog/githubAccountStatus';
import type { ProjectSummary } from '@/entities/catalog/project';
import { LABELS } from '@/labels/en';
import {
  MOCK_GITHUB_ACCOUNT_STATUS,
  MOCK_GITHUB_BRANCHES,
  MOCK_GITHUB_DEFAULT_BRANCH,
  MOCK_REPOSITORIES,
} from '@/mocks/catalogMocks';
import { formatLabel } from '@/utils/formatLabel';
import { GithubCloneStageEnum } from './types';
import { getGithubRepositoryFullName } from './utils';

const CONTENT_STYLE = { pt: 1 };
const FORM_STYLE = { display: 'flex', flexDirection: 'column', minHeight: 0 };
const FOOTER_STYLE = { flexDirection: { xs: 'column', sm: 'row' }, alignItems: { xs: 'stretch', sm: 'center' }, gap: 2, px: 3, pb: 2 };
const BUTTONS_STYLE = { justifyContent: 'flex-end' };
const MOCK_CLONE_DURATION_MS = 1800;
const CLONE_FOLDER_PREFIX = '~/.virgo-dag/repositories/';

interface GithubCloneDialogProps {
  isOpen: boolean;
  onClose: () => void;
  project?: ProjectSummary;
  accountStatus?: GithubAccountStatus;
}

/**
 * Collects a GitHub clone and the branch a project uses.
 */
export const GithubCloneDialog = ({
  isOpen, onClose, project, accountStatus = MOCK_GITHUB_ACCOUNT_STATUS,
}: GithubCloneDialogProps) => {
  const repositoryInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const branchInputRef = useRef<HTMLInputElement>(null);

  const [repositoryInput, setRepositoryInput] = useState('');
  const [folderOverride, setFolderOverride] = useState<string | null>(null);

  const [branchOverride, setBranchOverride] = useState<string | null>(null);
  const [stage, setStage] = useState(GithubCloneStageEnum.INPUT);
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const titleId = useId();

  const fullName = getGithubRepositoryFullName(repositoryInput);
  const registeredRepository = MOCK_REPOSITORIES.find((repository) =>
    repository.fullName.toLowerCase() === fullName?.toLowerCase());

  const defaultFolder = fullName === null ? '' : `${CLONE_FOLDER_PREFIX}${fullName}`;
  const cloneFolder = registeredRepository?.checkoutPath ?? folderOverride ?? defaultFolder;
  const isCloning = stage === GithubCloneStageEnum.CLONING;
  const isComplete = stage === GithubCloneStageEnum.COMPLETE;

  const isExisting = registeredRepository !== undefined;
  const showsBranch = project !== undefined && (isExisting || isComplete);
  const branches = registeredRepository?.branches ?? MOCK_GITHUB_BRANCHES;
  const defaultBranch = registeredRepository?.defaultBranch ?? MOCK_GITHUB_DEFAULT_BRANCH;

  const branch = branchOverride ?? defaultBranch;
  const isBranchValid = isValidBranchName(branch);
  const isFolderValid = cloneFolder.trim() !== '';

  const hasRepositoryError = hasSubmitted && fullName === null;
  const hasFolderError = hasSubmitted && !isFolderValid;
  const hasBranchError = hasSubmitted && showsBranch && !isBranchValid;

  const cloneLabel = isCloning ? LABELS.githubCloning : LABELS.githubClone;
  const completeLabel = isExisting ? LABELS.githubAddExisting : LABELS.githubDone;
  const submitLabel = isExisting || isComplete ? completeLabel : cloneLabel;

  const projectValues = { project: project?.name ?? '' };
  const projectBranchHint = formatLabel(LABELS.githubProjectBranchHint, projectValues);
  const handleRepositoryChange = (repositoryInput: string) => {
    setRepositoryInput(repositoryInput);
    setBranchOverride(null);
  };

  const handleFinish = () => {
    if (showsBranch && !isBranchValid) {
      branchInputRef.current?.focus();

      return;
    }

    onClose();
    setStage(GithubCloneStageEnum.INPUT);
    setRepositoryInput('');

    setFolderOverride(null);
    setBranchOverride(null);
    setHasSubmitted(false);
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isCloning || !accountStatus.authenticated) {
      return;
    }

    setHasSubmitted(true);
    if (fullName === null || !isFolderValid) {
      const invalidInputRef = fullName === null ? repositoryInputRef : folderInputRef;
      invalidInputRef.current?.focus();

      return;
    }

    if (isExisting || isComplete) {
      handleFinish();

      return;
    }

    setStage(GithubCloneStageEnum.CLONING);
  };

  useEffect(() => {
    if (stage !== GithubCloneStageEnum.CLONING) {
      return;
    }

    const cloneTimer = window.setTimeout(() => {
      setHasSubmitted(false);
      setStage(GithubCloneStageEnum.COMPLETE);
    }, MOCK_CLONE_DURATION_MS);

    return () => window.clearTimeout(cloneTimer);
  }, [stage]);

  return (
    <Dialog open={isOpen} onClose={onClose} fullWidth maxWidth="sm" aria-labelledby={titleId}>
      <Box component="form" noValidate onSubmit={handleSubmit} sx={FORM_STYLE}>
        <DialogTitle id={titleId}>{LABELS.githubCloneTitle}</DialogTitle>
        <DialogContent>
          <Stack spacing={3} sx={CONTENT_STYLE}>
            <GithubImportFeedback accountStatus={accountStatus} />
            {hasRepositoryError && hasFolderError && <Alert severity="error">{LABELS.githubCloneRequired}</Alert>}
            <GithubRepositoryInput
              value={repositoryInput} inputRef={repositoryInputRef}
              hasError={hasRepositoryError} isDisabled={isCloning || isComplete}
              onChange={handleRepositoryChange}
            />
            <CloneFolderInput
              value={cloneFolder} inputRef={folderInputRef} hasError={hasFolderError}
              isDisabled={isExisting || isCloning || isComplete} onChange={setFolderOverride}
            />
            {showsBranch && (
              <Stack spacing={1}>
                <BranchSelect key={fullName} branches={branches} defaultBranch={defaultBranch} branch={branch} autoFocus={isComplete} inputRef={branchInputRef} hasError={hasBranchError} onChange={setBranchOverride} />
                <Typography variant="body2" color="text.secondary">{projectBranchHint}</Typography>
              </Stack>
            )}
          </Stack>
        </DialogContent>
        <DialogActions disableSpacing sx={FOOTER_STYLE} role="group" aria-label={LABELS.githubCloneFooter}>
          <GithubCloneFeedback stage={stage} registeredRepository={registeredRepository} />
          <Stack direction="row" spacing={1} sx={BUTTONS_STYLE}>
            <Button onClick={onClose}>{LABELS.githubCloneClose}</Button>
            <Button key={stage} autoFocus={isComplete && !showsBranch} type="submit" variant="contained" disabled={isCloning || !accountStatus.authenticated} aria-busy={isCloning}>
              {submitLabel}
            </Button>
          </Stack>
        </DialogActions>
      </Box>
    </Dialog>
  );
};
