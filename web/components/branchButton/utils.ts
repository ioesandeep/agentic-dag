const BRANCH_NAME_PATTERN =
  /^(?!HEAD$)(?![-/])(?!.*(?:\.\.|@\{|\/\/))(?!.*(?:^|\/)\.)(?!.*\.lock(?:\/|$))(?!.*[./]$)[^\u0000-\u0020\u007f~^:?*[\]\\]+$/;

/**
 * Validates a new Git branch name.
 */
export const isValidBranchName = (branch: string): boolean => BRANCH_NAME_PATTERN.test(branch);
