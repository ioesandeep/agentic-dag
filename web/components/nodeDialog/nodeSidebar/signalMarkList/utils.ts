import type { SignalMark } from '@/components/nodeDialog/nodeSidebar/signalMarkList/types';
import type { NodeWorktree } from '@/entities/nodeDetail';
import { SIGNAL_KINDS } from '@/entities/nodeDetail';

const NO_MARK = '';

/**
 * Returns the mark of every signal a node's worktree has been notified about.
 */
export const listSignalMarks = (
  worktree: NodeWorktree | null,
): SignalMark[] => {
  if (worktree === null) {
    return [];
  }

  const signalMarks = SIGNAL_KINDS.map((signal) => ({
    signal,
    mark: worktree.signalMarks[signal] ?? NO_MARK,
  }));

  return signalMarks.filter((signalMark) => signalMark.mark !== NO_MARK);
};
