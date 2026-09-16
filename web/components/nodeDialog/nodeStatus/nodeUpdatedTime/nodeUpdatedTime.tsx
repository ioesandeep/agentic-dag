import { RelativeTime } from '@/components/relativeTime/relativeTime';
import { LABELS } from '@/labels/en';

interface NodeUpdatedTimeProps {
  // When the node's state was last written, or null when it never was.
  at: string | null;
}

/**
 * Renders when the node's state was last written.
 */
export const NodeUpdatedTime = ({ at }: NodeUpdatedTimeProps) => {
  if (at === null) {
    return null;
  }

  return <RelativeTime at={at} template={LABELS.nodeUpdatedAt} />;
};
