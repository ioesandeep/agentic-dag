/**
 * Defines the text displayed with a local checkout inspection.
 */
export interface LocalCheckoutPreviewContent {
  gitRoot: string;
  githubRepository: string;
  identityRequired: string;
  branches: string;
  uncommitted: string;
  existing: string;
  expected: string;
  projects: string;
  noProjects: string;
  mismatch: string;
}
