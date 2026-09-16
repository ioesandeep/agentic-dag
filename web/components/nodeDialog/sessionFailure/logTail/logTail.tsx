import { CodeBlock } from '@/components/codeBlock/codeBlock';

interface LogTailProps {
  // The log tail to display.
  logTail: string | null;
}

/**
 * Renders the session log tail.
 */
export const LogTail = ({ logTail }: LogTailProps) => {
  if (logTail === null) {
    return null;
  }

  return <CodeBlock text={logTail} />;
};
