import type { RecoveryCauseEnum } from '@/entities/nodeDetail';
import { RECOVERY_CAUSES } from '@/entities/nodeDetail';
import type { WakeRequest } from '@/entities/wakeRequest';

const NO_HELPER_TEXT = '';

const getRecoveryCause = (causeValue: string): RecoveryCauseEnum | null =>
  RECOVERY_CAUSES.find((recoveryCause) => recoveryCause === causeValue) ??
  null;

/**
 * Returns true when a text value is empty or contains only white space.
 */
export const isBlank = (value: string): boolean => value.trim() === '';

/**
 * Returns a field's required-value text while the field shows its error, or an empty string otherwise.
 */
export const getRequiredHelperText = (
  hasError: boolean,
  requiredText: string,
): string => {
  if (hasError) {
    return requiredText;
  }

  return NO_HELPER_TEXT;
};

/**
 * Returns the wake request, or null when a value is missing.
 */
export const getWakeRequest = (
  causeValue: string,
  action: string,
  message: string,
): WakeRequest | null => {
  const cause = getRecoveryCause(causeValue);
  const isActionBlank = isBlank(action);
  const isMessageBlank = isBlank(message);

  if (cause === null || isActionBlank || isMessageBlank) {
    return null;
  }

  return { cause, action, message };
};
