import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableRow from '@mui/material/TableRow';

import { SETTING_NAME_WIDTH } from '@/components/dagPanel/dagTabs/dagSettings/constants';
import { getSettings } from '@/components/dagPanel/dagTabs/dagSettings/utils';
import type { DagDetail } from '@/entities/dagDetail';

interface DagSettingsProps {
  dag: DagDetail;
}

/**
 * Renders the Settings tab of the DagTabs.
 */
export const DagSettings = ({ dag }: DagSettingsProps) => (
  <Table size="small">
    <TableBody>
      {getSettings(dag).map((setting) => (
        <TableRow key={setting.name}>
          <TableCell
            sx={{ width: SETTING_NAME_WIDTH, color: 'text.secondary' }}
          >
            {setting.name}
          </TableCell>
          <TableCell
            sx={{ fontFamily: (theme) => theme.typography.fontFamilyMono }}
          >
            {setting.value}
          </TableCell>
        </TableRow>
      ))}
    </TableBody>
  </Table>
);
