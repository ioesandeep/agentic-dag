'use client';

import ChevronLeftOutlinedIcon from '@mui/icons-material/ChevronLeftOutlined';
import MenuOutlinedIcon from '@mui/icons-material/MenuOutlined';
import Box from '@mui/material/Box';
import Drawer from '@mui/material/Drawer';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import { useState } from 'react';

import { DagCard } from '@/components/dagList/dagCard/dagCard';
import { DagCardVariant } from '@/components/dagList/dagCard/types';
import {
  SIDEBAR_COLLAPSE_KEY,
  SIDEBAR_DRAWER_WIDTH,
} from '@/components/dagPanel/dagSidebar/constants';
import { DagSidebarSkeleton } from '@/components/dagPanel/dagSidebar/dagSidebarSkeleton/dagSidebarSkeleton';
import {
  findCurrentDagIndex,
  getSidebarCardVariant,
  getSidebarChevronRotation,
  getSidebarListPaddingX,
  getSidebarStyle,
  getSidebarToggleLabel,
} from '@/components/dagPanel/dagSidebar/utils';
import type { DagSummary } from '@/entities/dagSummary';
import { useScrollCurrentItemToTop } from '@/hooks/useScrollCurrentItemToTop';
import { useStoredDagState } from '@/hooks/useStoredDagState';
import { useStoredFlag } from '@/hooks/useStoredFlag';
import { LABELS } from '@/labels/en';
import { getDagsInStateWithCurrentDag } from '@/utils/dagState';
import { isNull } from '@/utils/typeGuards';

interface DagSidebarProps {
  // The dags of this host, null until the api sends them.
  dags: DagSummary[] | null;
  currentName: string;
  // True where the dag list opened this page and the sidebar plays its entrance.
  isEntering: boolean;
}

/**
 * Renders the left column of the DagPanel.
 */
export const DagSidebar = ({
  dags,
  currentName,
  isEntering,
}: DagSidebarProps) => {
  const collapse = useStoredFlag(SIDEBAR_COLLAPSE_KEY, false);
  const dagFilter = useStoredDagState();
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const visibleDags = getDagsInStateWithCurrentDag(
    dags,
    dagFilter.dagState,
    currentName,
  );
  const currentIndex = findCurrentDagIndex(visibleDags, currentName);
  const listRef = useScrollCurrentItemToTop(currentIndex);

  const handleDrawerOpen = () => setIsDrawerOpen(true);
  const handleDrawerClose = () => setIsDrawerOpen(false);

  if (isNull(visibleDags)) {
    return <DagSidebarSkeleton isCollapsed={collapse.isOn} />;
  }

  return (
    <Box component="nav" sx={getSidebarStyle(collapse.isOn, isEntering)}>
      <Box
        sx={{
          display: { xs: 'none', md: 'flex' },
          flexDirection: 'column',
          height: '100%',
        }}
      >
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', p: 0.5 }}>
          <Tooltip title={getSidebarToggleLabel(collapse.isOn)}>
            <IconButton
              size="small"
              onClick={collapse.toggle}
              aria-label={getSidebarToggleLabel(collapse.isOn)}
            >
              <ChevronLeftOutlinedIcon
                fontSize="small"
                sx={{
                  transform: getSidebarChevronRotation(collapse.isOn),
                  transition: 'transform 200ms ease',
                }}
              />
            </IconButton>
          </Tooltip>
        </Box>
        <Box
          ref={listRef}
          sx={{
            flexGrow: 1,
            minHeight: 0,
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: 1,
            px: getSidebarListPaddingX(collapse.isOn),
            pb: 1.5,
          }}
        >
          {visibleDags.map((dag) => (
            <DagCard
              key={dag.name}
              dag={dag}
              variant={getSidebarCardVariant(collapse.isOn)}
              isCurrent={dag.name === currentName}
            />
          ))}
        </Box>
      </Box>
      <Box sx={{ display: { xs: 'block', md: 'none' }, p: 0.5 }}>
        <Tooltip title={LABELS.dagListOpen}>
          <IconButton
            size="small"
            onClick={handleDrawerOpen}
            aria-label={LABELS.dagListOpen}
          >
            <MenuOutlinedIcon fontSize="small" />
          </IconButton>
        </Tooltip>
        <Drawer open={isDrawerOpen} onClose={handleDrawerClose}>
          <Box
            sx={{
              width: SIDEBAR_DRAWER_WIDTH,
              display: 'flex',
              flexDirection: 'column',
              gap: 1,
              p: 1.5,
            }}
          >
            {visibleDags.map((dag) => (
              <DagCard
                key={dag.name}
                dag={dag}
                variant={DagCardVariant.FLEXIBLE}
                isCurrent={dag.name === currentName}
                onSelect={handleDrawerClose}
              />
            ))}
          </Box>
        </Drawer>
      </Box>
    </Box>
  );
};
