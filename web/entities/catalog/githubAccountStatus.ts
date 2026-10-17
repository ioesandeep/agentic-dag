/**
 * Reports the host GitHub account and authentication guidance.
 */
export interface GithubAccountStatus {
  host: string;
  authenticated: boolean;
  login: string | null;
  guidance: string | null;
}
