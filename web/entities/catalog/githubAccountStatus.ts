/**
 * Describes GitHub authentication for repository imports.
 */
export interface GithubAccountStatus {
  host: string;
  authenticated: boolean;
  login: string | null;
  guidance: string | null;
}
