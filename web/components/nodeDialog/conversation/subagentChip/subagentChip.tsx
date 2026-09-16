import { PRIMARY_MAIN_COLOR } from '@/components/nodeDialog/constants';
import { isFromSubagent } from '@/components/nodeDialog/conversation/utils';
import { SoftChip } from '@/components/softChip/softChip';
import type { ConversationMessage } from '@/entities/conversationMessage';
import { LABELS } from '@/labels/en';

interface SubagentChipProps {
  message: ConversationMessage;
}

/**
 * Renders a chip on a message that came from a subagent.
 */
export const SubagentChip = ({ message }: SubagentChipProps) => {
  if (!isFromSubagent(message)) {
    return null;
  }

  return <SoftChip color={PRIMARY_MAIN_COLOR} label={LABELS.subagentThread} />;
};
