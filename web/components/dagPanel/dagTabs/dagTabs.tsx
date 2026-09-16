'use client';

import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import type { SyntheticEvent } from 'react';
import { useState } from 'react';

import { TAB_PANEL_ID } from '@/components/dagPanel/dagTabs/constants';
import { DagTabPanel } from '@/components/dagPanel/dagTabs/dagTabPanel/dagTabPanel';
import { DagTab } from '@/components/dagPanel/dagTabs/types';
import { getTabId } from '@/components/dagPanel/dagTabs/utils';
import type { DagDetail } from '@/entities/dagDetail';
import { LABELS } from '@/labels/en';

interface DagTabsProps {
  dag: DagDetail;
}

/**
 * Renders the tabbed section of the DagPanel.
 */
export const DagTabs = ({ dag }: DagTabsProps) => {
  const [tab, setTab] = useState(DagTab.AUDIT);

  const handleTabChange = (_: SyntheticEvent, nextTab: DagTab) =>
    setTab(nextTab);

  return (
    <Paper
      variant="outlined"
      sx={{
        flexGrow: 1,
        minHeight: 0,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <Tabs
        value={tab}
        onChange={handleTabChange}
        sx={{ borderBottom: 1, borderColor: 'divider', flexShrink: 0 }}
      >
        <Tab
          value={DagTab.AUDIT}
          id={getTabId(DagTab.AUDIT)}
          aria-controls={TAB_PANEL_ID}
          label={LABELS.dagAudit}
        />
        <Tab
          value={DagTab.NODES}
          id={getTabId(DagTab.NODES)}
          aria-controls={TAB_PANEL_ID}
          label={LABELS.dagNodes}
        />
        <Tab
          value={DagTab.SETTINGS}
          id={getTabId(DagTab.SETTINGS)}
          aria-controls={TAB_PANEL_ID}
          label={LABELS.dagSettings}
        />
      </Tabs>
      <Box
        id={TAB_PANEL_ID}
        role="tabpanel"
        aria-labelledby={getTabId(tab)}
        sx={{ flexGrow: 1, minHeight: 0, overflowY: 'auto' }}
      >
        <DagTabPanel dag={dag} tab={tab} />
      </Box>
    </Paper>
  );
};
