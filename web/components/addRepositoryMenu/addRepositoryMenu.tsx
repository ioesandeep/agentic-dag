'use client';

import AddIcon from '@mui/icons-material/Add';
import ArrowDropDownIcon from '@mui/icons-material/ArrowDropDown';
import GitHubIcon from '@mui/icons-material/GitHub';
import IconButton from '@mui/material/IconButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import type { PopoverOrigin } from '@mui/material/Popover';
import { useId, useRef, useState } from 'react';

import { GithubCloneDialog } from '@/components/githubCloneDialog/githubCloneDialog';
import type { ProjectSummary } from '@/entities/catalog/project';
import { LABELS } from '@/labels/en';
import { AddRepositoryMethodEnum } from './types';

const MENU_ANCHOR_ORIGIN: PopoverOrigin = { vertical: 'bottom', horizontal: 'right' };
const MENU_TRANSFORM_ORIGIN: PopoverOrigin = { vertical: 'top', horizontal: 'right' };

interface AddRepositoryMenuProps {
  methods: readonly AddRepositoryMethodEnum[];
  project?: ProjectSummary;
  isDisabled?: boolean;
}

/**
 * Opens the repository import methods available on a page.
 */
export const AddRepositoryMenu = ({ methods, project, isDisabled = false }: AddRepositoryMenuProps) => {
  const buttonRef = useRef<HTMLButtonElement>(null);
  const [anchorElement, setAnchorElement] = useState<HTMLElement | null>(null);
  const [isGithubOpen, setIsGithubOpen] = useState(false);
  const buttonId = useId();

  const menuId = useId();
  const isMenuOpen = anchorElement !== null;
  const hasGithub = methods.includes(AddRepositoryMethodEnum.GITHUB);

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
        {hasGithub && (
          <MenuItem onClick={handleOpenGithub}>
            <ListItemIcon><GitHubIcon fontSize="small" /></ListItemIcon>
            <ListItemText>{LABELS.repositoryAddGithub}</ListItemText>
          </MenuItem>
        )}
      </Menu>
      {hasGithub && (
        <GithubCloneDialog isOpen={isGithubOpen} onClose={handleCloseGithub} project={project} />
      )}
    </>
  );
};
