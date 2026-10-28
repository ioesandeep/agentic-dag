const GITHUB_URI_PREFIX_PATTERN = /^(?:https:\/\/github\.com\/|git@github\.com:|ssh:\/\/git@github\.com\/)/i;
const GITHUB_URI_SUFFIX_PATTERN = /(?:\.git)?\/$|\.git$/i;
const MAX_REPOSITORY_SUGGESTIONS = 10;

/**
 * Returns matching repository names within the suggestion limit.
 */
export const getGithubRepositorySuggestions = (repositoryNames: string[], repositoryInput: string): string[] => {
  const trimmedInput = repositoryInput.trim();
  const repositoryReference = trimmedInput.replace(GITHUB_URI_PREFIX_PATTERN, '');
  const searchName = repositoryReference.replace(GITHUB_URI_SUFFIX_PATTERN, '');
  const query = searchName.toLowerCase();

  const matches = repositoryNames.filter((repositoryName) => {
    const lowercaseName = repositoryName.toLowerCase();

    return lowercaseName.includes(query);
  });

  return matches.slice(0, MAX_REPOSITORY_SUGGESTIONS);
};
