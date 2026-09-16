import { ERROR_MAIN_COLOR } from '@/components/nodeDialog/constants';
import { isFailedExitCode } from '@/components/nodeDialog/sessionFailure/utils';
import { SoftChip } from '@/components/softChip/softChip';
import { LABELS } from '@/labels/en';
import { formatLabel } from '@/utils/formatLabel';

interface ExitCodeChipProps {
  // The session exit code to display.
  exitCode: number | null;
}

/**
 * Renders a chip for a nonzero session exit code.
 */
export const ExitCodeChip = ({ exitCode }: ExitCodeChipProps) => {
  const isFailed = isFailedExitCode(exitCode);

  if (!isFailed) {
    return null;
  }

  const codeValues = { code: exitCode };

  return (
    <SoftChip
      color={ERROR_MAIN_COLOR}
      label={formatLabel(LABELS.sessionExitCode, codeValues)}
    />
  );
};
