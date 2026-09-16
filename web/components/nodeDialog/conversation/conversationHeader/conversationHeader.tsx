import CloseFullscreenIcon from '@mui/icons-material/CloseFullscreen';
import OpenInFullIcon from '@mui/icons-material/OpenInFull';
import Box from '@mui/material/Box';
import FormControlLabel from '@mui/material/FormControlLabel';
import IconButton from '@mui/material/IconButton';
import Switch from '@mui/material/Switch';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';

import { widthToggleLabel } from '@/components/nodeDialog/conversation/utils';
import { LABELS } from '@/labels/en';

interface ConversationHeaderProps {
  isWide: boolean;
  isShowingSubagents: boolean;
  onToggleWidth: () => void;
  onToggleSubagents: () => void;
}

/**
 * Renders the conversation heading, the subagent toggle and the width toggle.
 */
export const ConversationHeader = ({
  isWide,
  isShowingSubagents,
  onToggleWidth,
  onToggleSubagents,
}: ConversationHeaderProps) => (
  <Box
    sx={{
      px: 2,
      py: 1,
      display: 'flex',
      alignItems: 'center',
      gap: 1,
      borderBottom: 1,
      borderColor: 'divider',
    }}
  >
    <Typography variant="overline" sx={{ fontWeight: 600 }}>
      {LABELS.conversationHeading}
    </Typography>
    <Box sx={{ flexGrow: 1 }} />
    <FormControlLabel
      label={LABELS.subagentThreads}
      slotProps={{ typography: { variant: 'body2' } }}
      control={
        <Switch
          size="small"
          checked={isShowingSubagents}
          onChange={onToggleSubagents}
        />
      }
    />
    <Tooltip title={widthToggleLabel(isWide)}>
      <IconButton
        size="small"
        onClick={onToggleWidth}
        aria-label={widthToggleLabel(isWide)}
      >
        {isWide ? <CloseFullscreenIcon fontSize="small" /> : <OpenInFullIcon fontSize="small" />}
      </IconButton>
    </Tooltip>
  </Box>
);
