'use client';

import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import MenuItem from '@mui/material/MenuItem';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import type { FormEvent } from 'react';
import { useRef, useState } from 'react';

import { isValidBranchName } from '@/components/branchButton/utils';
import { BranchSelect } from '@/components/branchSelect/branchSelect';
import { LocalCheckoutFolderInput } from '@/components/localCheckoutFolderInput/localCheckoutFolderInput';
import { LocalCheckoutPreview } from '@/components/localCheckoutPreview/localCheckoutPreview';
import { isRepositoryMismatch } from '@/components/localCheckoutPreview/utils';
import type { ProjectSummary } from '@/entities/catalog/project';
import type { Repository } from '@/entities/catalog/repository';
import type { RepositoryInspection, RepositoryRemoteChoice } from '@/entities/catalog/repositoryInspection';
import { LABELS } from '@/labels/en';
import { MOCK_LOCAL_CHECKOUT_INSPECTIONS } from '@/mocks/catalogMocks';
import { formatLabel } from '@/utils/formatLabel';
import { getLocalCheckoutPreviewContent } from './utils';

const FORM_STYLE = { display: 'flex', flexDirection: 'column', minHeight: 0 };
const CONTENT_STYLE = { pt: 1 };
const ACTIONS_STYLE = { px: 3, pb: 2 };
const REMOTE_STYLE = { overflowWrap: 'anywhere', whiteSpace: 'normal' };

interface LocalCheckoutFormProps {
  onClose: () => void;
  project?: ProjectSummary;
  repairRepository?: Repository;
  inspections?: readonly RepositoryInspection[];
}

/**
 * Collects an inspected local folder for registration or repository repair.
 */
export const LocalCheckoutForm = ({ onClose, project, repairRepository, inspections = MOCK_LOCAL_CHECKOUT_INSPECTIONS }: LocalCheckoutFormProps) => {
  const branchInputRef = useRef<HTMLInputElement>(null);
  const [folder, setFolder] = useState('');
  const [inspection, setInspection] = useState<RepositoryInspection | null>(null);
  const [remotes, setRemotes] = useState<RepositoryRemoteChoice[]>([]);

  const [remoteName, setRemoteName] = useState('');
  const [branchOverride, setBranchOverride] = useState<string | null>(null);
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const [folderSelectionVersion, setFolderSelectionVersion] = useState(0);

  const defaultBranch = inspection?.identity?.defaultBranch ?? '';
  const branch = branchOverride ?? defaultBranch;
  const showsBranch = project !== undefined && inspection?.identity != null;
  const isBranchValid = !showsBranch || isValidBranchName(branch);

  const selectedRemote = inspection?.remotes.find((remote) => remote.name === inspection.selectedRemoteName);
  const hasMismatch = isRepositoryMismatch(inspection, repairRepository);
  const canAdd = inspection?.identity != null && selectedRemote?.supported === true && !hasMismatch;
  const title = repairRepository === undefined ? LABELS.localCheckoutTitle : LABELS.localCheckoutRepairTitle;

  const submitLabel = repairRepository === undefined ? LABELS.localCheckoutAdd : LABELS.localCheckoutRepair;
  const projectValues = { project: project?.name ?? '' };
  const projectBranchHint = formatLabel(LABELS.githubProjectBranchHint, projectValues);
  const previewContent = getLocalCheckoutPreviewContent(inspection, repairRepository);

  const handleFolderChange = (folder: string) => {
    setFolder(folder);
    setInspection(null);

    setRemotes([]);
    setRemoteName('');
    setBranchOverride(null);
  };

  const handleInspect = (remoteName = '') => {
    const nextInspection = inspections.find((inspection) => remoteName === '' || inspection.selectedRemoteName === remoteName) ?? null;
    setInspection(nextInspection);
    setRemotes(nextInspection?.remotes ?? []);
    setRemoteName(nextInspection?.selectedRemoteName ?? '');

    setHasSubmitted(false);
  };

  const handleRemoteChange = (remoteName: string) => {
    setBranchOverride(null);
    handleInspect(remoteName);
  };

  const handleDirectorySelect = () => {
    setBranchOverride(null);
    setFolderSelectionVersion((version) => version + 1);
    handleInspect();
  };

  const handleFolderBlur = () => {
    const hasFolder = folder.trim() !== '';
    if (hasFolder) {
      handleInspect(remoteName);
    }
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canAdd) {
      return;
    }

    setHasSubmitted(true);
    if (!isBranchValid) {
      branchInputRef.current?.focus();

      return;
    }

    onClose();
  };

  return (
    <Box component="form" noValidate onSubmit={handleSubmit} sx={FORM_STYLE}>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <Stack spacing={3} sx={CONTENT_STYLE}>
          <Typography variant="body2" color="text.secondary">{LABELS.localCheckoutHint}</Typography>
          <LocalCheckoutFolderInput value={folder} onChange={handleFolderChange} onBlur={handleFolderBlur} onSelect={handleDirectorySelect} />
          {remotes.length > 1 && (
            <TextField select fullWidth label={LABELS.localCheckoutRemote} helperText={LABELS.localCheckoutRemoteHint} value={remoteName} onChange={(event) => handleRemoteChange(event.target.value)}>
              {remotes.map((remote) => {
                const remoteValues = { name: remote.name, url: remote.url };
                const remoteLabel = formatLabel(LABELS.localCheckoutRemoteOption, remoteValues);

                return <MenuItem key={remote.name} value={remote.name} sx={REMOTE_STYLE}>{remoteLabel}</MenuItem>;
              })}
            </TextField>
          )}
          {showsBranch && inspection !== null && (
            <Stack spacing={1}>
              <BranchSelect key={`${folderSelectionVersion}:${remoteName}`} branches={inspection.branches} defaultBranch={inspection.identity?.defaultBranch ?? null} branch={branch} inputRef={branchInputRef} hasError={hasSubmitted && !isBranchValid} onChange={setBranchOverride} />
              <Typography variant="body2" color="text.secondary">{projectBranchHint}</Typography>
            </Stack>
          )}
          {(inspection !== null || repairRepository !== undefined) && <LocalCheckoutPreview inspection={inspection} repairRepository={repairRepository} showExistingRegistration={project === undefined || repairRepository !== undefined} content={previewContent} />}
        </Stack>
      </DialogContent>
      <DialogActions sx={ACTIONS_STYLE}>
        <Button onClick={onClose}>{LABELS.repositoryActionCancel}</Button>
        <Button type="submit" variant="contained" disabled={!canAdd}>{submitLabel}</Button>
      </DialogActions>
    </Box>
  );
};
