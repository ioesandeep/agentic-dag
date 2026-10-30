'use client';

import AddIcon from '@mui/icons-material/Add';
import ArrowDropDownIcon from '@mui/icons-material/ArrowDropDown';
import GitHubIcon from '@mui/icons-material/GitHub';
import FolderIcon from '@mui/icons-material/Folder';
import FolderOutlinedIcon from '@mui/icons-material/FolderOutlined';
import Dialog from '@mui/material/Dialog';
import IconButton from '@mui/material/IconButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import type { PopoverOrigin } from '@mui/material/Popover';
import { useId, useRef, useState } from 'react';

import { GithubCloneDialog } from '@/components/githubCloneDialog/githubCloneDialog';
import { LocalCheckoutForm } from '@/components/localCheckoutForm/localCheckoutForm';
import { RepositoryPickerDialog } from '@/components/repositoryPickerDialog/repositoryPickerDialog';
import type { ProjectSummary } from '@/entities/catalog/project';
import { LABELS } from '@/labels/en';

const MENU_ANCHOR_ORIGIN: PopoverOrigin = { vertical: 'bottom', horizontal: 'right' };
const MENU_TRANSFORM_ORIGIN: PopoverOrigin = { vertical: 'top', horizontal: 'right' };

interface AddRepositoryActionButtonProps {
  project: ProjectSummary;
  isDisabled?: boolean;
}

/**
 * Opens the repository import actions for a project.
 */
export const AddRepositoryActionButton = ({ project, isDisabled = false }: AddRepositoryActionButtonProps) => {
  const buttonRef = useRef<HTMLButtonElement>(null);
  const [anchorElement, setAnchorElement] = useState<HTMLElement | null>(null);

  const [isGithubOpen, setIsGithubOpen] = useState(false);
  const [isRepositoryPickerOpen, setIsRepositoryPickerOpen] = useState(false);
  const [isLocalOpen, setIsLocalOpen] = useState(false);

  const buttonId = useId();
  const menuId = useId();

  const isMenuOpen = anchorElement !== null;

  const menuSlotProps = {
    list: { 'aria-labelledby': buttonId },
    paper: { sx: { minWidth: anchorElement?.offsetWidth } },
  };

  const handleOpenMenu = () => setAnchorElement(buttonRef.current);
  const handleCloseMenu = () => setAnchorElement(null);
  const handleOpenGithub = () => {
    handleCloseMenu();
    setIsGithubOpen(true);
  };

  const handleCloseGithub = () => {
    setIsGithubOpen(false);
    buttonRef.current?.focus();
  };

  const handleOpenRepositoryPicker = () => {
    handleCloseMenu();
    setIsRepositoryPickerOpen(true);
  };

  const handleCloseRepositoryPicker = () => {
    setIsRepositoryPickerOpen(false);
    buttonRef.current?.focus();
  };

  const handleOpenLocal = () => {
    handleCloseMenu();
    setIsLocalOpen(true);
  };

  const handleCloseLocal = () => {
    setIsLocalOpen(false);
    buttonRef.current?.focus();
  };

  return (
    <>
      <IconButton
        ref={buttonRef}
        id={buttonId}
        size="small"
        disabled={isDisabled}
        aria-label={LABELS.repositoryAdd}
        aria-haspopup="menu"
        aria-controls={isMenuOpen ? menuId : undefined}
        aria-expanded={isMenuOpen}
        onClick={handleOpenMenu}
      >
        <AddIcon fontSize="small" />
        <ArrowDropDownIcon fontSize="small" />
      </IconButton>
      <Menu
        id={menuId}
        anchorEl={anchorElement}
        anchorOrigin={MENU_ANCHOR_ORIGIN}
        transformOrigin={MENU_TRANSFORM_ORIGIN}
        open={isMenuOpen}
        onClose={handleCloseMenu}
        slotProps={menuSlotProps}
      >
        <MenuItem onClick={handleOpenGithub}>
          <ListItemIcon><GitHubIcon fontSize="small" /></ListItemIcon>
          <ListItemText>{LABELS.repositoryAddGithub}</ListItemText>
        </MenuItem>
        <MenuItem onClick={handleOpenRepositoryPicker}>
          <ListItemIcon><FolderIcon fontSize="small" /></ListItemIcon>
          <ListItemText>{LABELS.repositoryAddFromList}</ListItemText>
        </MenuItem>
        <MenuItem onClick={handleOpenLocal}>
          <ListItemIcon><FolderOutlinedIcon fontSize="small" /></ListItemIcon>
          <ListItemText>{LABELS.repositoryAddLocal}</ListItemText>
        </MenuItem>
      </Menu>
      <GithubCloneDialog isOpen={isGithubOpen} onClose={handleCloseGithub} project={project} />
      {isRepositoryPickerOpen && (
        <RepositoryPickerDialog isOpen onClose={handleCloseRepositoryPicker} project={project} />
      )}
      {isLocalOpen && (
        <Dialog open onClose={handleCloseLocal} fullWidth maxWidth="sm">
          <LocalCheckoutForm onClose={handleCloseLocal} project={project} />
        </Dialog>
      )}
    </>
  );
};
