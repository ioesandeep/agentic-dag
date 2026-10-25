import ArchiveOutlinedIcon from '@mui/icons-material/ArchiveOutlined';
import EditOutlinedIcon from '@mui/icons-material/EditOutlined';
import UnarchiveOutlinedIcon from '@mui/icons-material/UnarchiveOutlined';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import type { Ref } from 'react';

import { ColorSchemeToggle } from '@/components/colorSchemeToggle/colorSchemeToggle';
import { LABELS } from '@/labels/en';

interface ProjectActionsProps {
  isArchived: boolean;
  isEditing: boolean;
  editButtonRef: Ref<HTMLButtonElement>;
  onEdit: () => void;
  onArchive: () => void;
}

/**
 * Provides project editing and archive controls.
 */
export const ProjectActions = ({
  isArchived,
  isEditing,
  editButtonRef,
  onEdit,
  onArchive,
}: ProjectActionsProps) => {
  const archiveLabel = isArchived ? LABELS.projectUnarchive : LABELS.projectArchive;
  const ArchiveIcon = isArchived ? UnarchiveOutlinedIcon : ArchiveOutlinedIcon;

  return (
    <>
      <Tooltip title={LABELS.projectEdit}>
        <IconButton
          ref={editButtonRef}
          size="small"
          aria-label={LABELS.projectEdit}
          onClick={onEdit}
        >
          <EditOutlinedIcon fontSize="small" />
        </IconButton>
      </Tooltip>
      <Tooltip title={archiveLabel}>
        <span>
          <IconButton
            size="small"
            aria-label={archiveLabel}
            onClick={onArchive}
            disabled={isEditing}
          >
            <ArchiveIcon fontSize="small" />
          </IconButton>
        </span>
      </Tooltip>
      <ColorSchemeToggle />
    </>
  );
};
