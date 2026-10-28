const GITHUB_REPOSITORY_PATTERN = /^(?:https:\/\/github\.com\/|git@github\.com:|ssh:\/\/git@github\.com\/)?([a-z\d](?:[a-z\d-]*[a-z\d])?)\/([a-z\d._-]+?)(?:\.git)?\/?$/i;

/**
 * Returns the repository owner and name from a GitHub reference.
 */
export const getGithubRepositoryFullName = (repositoryInput: string): string | null => {
  const trimmedInput = repositoryInput.trim();
  const repositoryMatch = GITHUB_REPOSITORY_PATTERN.exec(trimmedInput);
  if (repositoryMatch === null || repositoryMatch[2] === '.' || repositoryMatch[2] === '..') {
    return null;
  }

  return `${repositoryMatch[1]}/${repositoryMatch[2]}`;
};
