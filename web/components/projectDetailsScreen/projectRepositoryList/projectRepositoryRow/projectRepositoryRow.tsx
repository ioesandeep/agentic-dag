'use client';

import DeleteOutlinedIcon from '@mui/icons-material/DeleteOutlined';
import RefreshOutlinedIcon from '@mui/icons-material/RefreshOutlined';
import Box from '@mui/material/Box';
import IconButton from '@mui/material/IconButton';
import ListItem from '@mui/material/ListItem';
import Snackbar from '@mui/material/Snackbar';
import type { SnackbarCloseReason } from '@mui/material/Snackbar';
import Stack from '@mui/material/Stack';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import type { SyntheticEvent } from 'react';
import { useRef, useState } from 'react';

import { BranchButton } from '@/components/branchButton/branchButton';
import type { Repository } from '@/entities/catalog/repository';
import { LABELS } from '@/labels/en';
import { formatLabel } from '@/utils/formatLabel';

const ROW_STYLE = {
  display: 'grid',
  gridTemplateColumns: 'minmax(0, 1fr) auto minmax(0, 1fr)',
  columnGap: 1,
  rowGap: 0.5,
  py: 1.5,
  borderTop: 1,
  borderColor: 'divider',
};

const NAME_STYLE = { fontWeight: 600, minWidth: 0, overflowWrap: 'anywhere' };
const BRANCH_STYLE = { minWidth: 0, justifySelf: 'center', maxWidth: '100%' };
const ACTION_STYLE = { justifySelf: 'end' };
const FOLDER_STYLE = { gridColumn: '1 / -1', overflowWrap: 'anywhere' };
const NOTICE_SLOT_PROPS = { content: { role: 'status' } };
const REFRESH_NOTICE_DURATION_MS = 4000;
const CLICK_AWAY_REASON = 'clickaway';

interface ProjectRepositoryRowProps {
  repository: Repository;
  projectId: string;
  isReadOnly: boolean;
  onRemove: (repository: Repository) => void;
}

/**
 * Displays a project's repository branch and checkout folder.
 */
export const ProjectRepositoryRow = ({
  repository,
  projectId,
  isReadOnly,
  onRemove,
}: ProjectRepositoryRowProps) => {
  const refreshButtonRef = useRef<HTMLButtonElement>(null);
  const [branchChange, setBranchChange] = useState<string | null>(null);
  const [refreshVersion, setRefreshVersion] = useState(0);
  const [isRefreshNoticeOpen, setIsRefreshNoticeOpen] = useState(false);

  const membership = repository.memberships.find(({ project }) => project.id === projectId);

  const branch = branchChange ?? membership?.branch ?? repository.defaultBranch ?? '';
  const noticeValues = { repository: repository.fullName };
  const notice = formatLabel(LABELS.repositoryRefreshed, noticeValues);
  const handleBranchChange = (branch: string) => setBranchChange(branch);

  const handleRemove = () => onRemove(repository);
  const handleRefresh = () => {
    setBranchChange(null);
    setRefreshVersion(refreshVersion + 1);
    setIsRefreshNoticeOpen(true);
  };

  const handleCloseNotice = (event: Event | SyntheticEvent | null, reason: SnackbarCloseReason) => {
    const target = event?.target;
    const isRefreshClick = target instanceof Node && refreshButtonRef.current?.contains(target);
    if (reason === CLICK_AWAY_REASON && isRefreshClick) {
      return;
    }

    setIsRefreshNoticeOpen(false);
  };

  return (
    <ListItem disableGutters aria-label={repository.fullName} sx={ROW_STYLE}>
      <Typography variant="body1" sx={NAME_STYLE}>
        {repository.fullName}
      </Typography>
      <Box sx={BRANCH_STYLE}>
        <BranchButton
          key={refreshVersion}
          repository={repository}
          branch={branch}
          disabled={isReadOnly}
          onChange={handleBranchChange}
        />
      </Box>
      <Stack direction="row" sx={ACTION_STYLE}>
        <Tooltip title={LABELS.repositoryRemoveFromProject}>
          <span>
            <IconButton
              size="small"
              color="error"
              aria-label={LABELS.repositoryRemoveFromProject}
              disabled={isReadOnly}
              onClick={handleRemove}
            >
              <DeleteOutlinedIcon fontSize="small" />
            </IconButton>
          </span>
        </Tooltip>
        <Tooltip title={LABELS.repositoryRefresh}>
          <span>
            <IconButton
              ref={refreshButtonRef}
              size="small"
              aria-label={LABELS.repositoryRefresh}
              disabled={isReadOnly}
              onClick={handleRefresh}
            >
              <RefreshOutlinedIcon fontSize="small" />
            </IconButton>
          </span>
        </Tooltip>
      </Stack>
      <Typography variant="body1" color="text.secondary" sx={FOLDER_STYLE}>
        {repository.checkoutPath}
      </Typography>
      <Snackbar
        key={refreshVersion}
        open={isRefreshNoticeOpen}
        autoHideDuration={REFRESH_NOTICE_DURATION_MS}
        message={notice}
        onClose={handleCloseNotice}
        slotProps={NOTICE_SLOT_PROPS}
      />
    </ListItem>
  );
};
