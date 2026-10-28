/**
 * Provides fixed catalog records for console pages.
 */
import type { GithubAccountStatus } from '@/entities/catalog/githubAccountStatus';
import type { Project } from '@/entities/catalog/project';
import {
  CheckoutKindEnum,
  CheckoutStateEnum,
  RepositoryPresentationStatusEnum,
} from '@/entities/catalog/repository';
import type { Repository } from '@/entities/catalog/repository';
import type { RepositoryInspection } from '@/entities/catalog/repositoryInspection';
import {
  FAILED_CONNECTOR_IMPORT,
  RUNNING_WORKER_IMPORT,
  SUCCEEDED_LEGACY_IMPORT,
  SUCCEEDED_SERVICE_IMPORT,
} from './catalogRepositoryImports';

export { MOCK_REPOSITORY_IMPORTS } from './catalogRepositoryImports';

const CREATED_AT = '2026-10-01T09:00:00Z';
const UPDATED_AT = '2026-10-15T12:00:00Z';
const ARCHIVED_AT = '2026-10-10T09:00:00Z';

const DEFAULT_PROJECT: Project = {
  id: 'project-default',
  name: 'Default',
  isDefault: true,
  archivedAt: null,
  description: 'Repositories without a specific project.',
  version: 1,
  createdAt: CREATED_AT,
  updatedAt: UPDATED_AT,
  repositoryCounts: {
    total: 3,
    ready: 1,
    importing: 1,
    failed: 1,
    unavailable: 0,
  },
};

const PLATFORM_PROJECT: Project = {
  id: 'project-platform',
  name: 'Platform',
  isDefault: false,
  archivedAt: null,
  description: 'Services and tools for the platform.',
  version: 1,
  createdAt: CREATED_AT,
  updatedAt: UPDATED_AT,
  repositoryCounts: {
    total: 3,
    ready: 2,
    importing: 0,
    failed: 0,
    unavailable: 1,
  },
};

const RESEARCH_PROJECT: Project = {
  id: 'project-research',
  name: 'Research',
  isDefault: false,
  archivedAt: null,
  description: 'Repository evaluation projects.',
  version: 1,
  createdAt: CREATED_AT,
  updatedAt: UPDATED_AT,
  repositoryCounts: {
    total: 0,
    ready: 0,
    importing: 0,
    failed: 0,
    unavailable: 0,
  },
};

const LEGACY_PROJECT: Project = {
  id: 'project-legacy',
  name: 'Legacy',
  isDefault: false,
  archivedAt: ARCHIVED_AT,
  description: 'Archived services.',
  version: 2,
  createdAt: CREATED_AT,
  updatedAt: ARCHIVED_AT,
  repositoryCounts: {
    total: 1,
    ready: 0,
    importing: 0,
    failed: 0,
    unavailable: 1,
  },
};

/**
 * Provides fixtures for active, empty, and archived projects.
 */
export const MOCK_PROJECTS: Project[] = [
  DEFAULT_PROJECT,
  PLATFORM_PROJECT,
  RESEARCH_PROJECT,
  LEGACY_PROJECT,
];

const REPOSITORY_DEFAULTS = {
  host: 'github.com',
  defaultBranch: 'main',
  remoteName: 'origin',
  lastCheckedAt: UPDATED_AT,
  validationMessage: null,
  version: 1,
  createdAt: CREATED_AT,
  updatedAt: UPDATED_AT,
  archivedAt: null,
};

const SERVICE_REPOSITORY: Repository = {
  ...REPOSITORY_DEFAULTS,
  id: SUCCEEDED_SERVICE_IMPORT.repositoryId,
  providerRepositoryId: '2001',
  fullName: 'virgo/service',
  webUrl: 'https://github.com/virgo/service',
  checkoutKind: CheckoutKindEnum.MANAGED,
  checkoutPath: '/Users/sandeep/.virgo-dag/repositories/service',
  branches: ['main', 'release/1.0'],
  checkoutState: CheckoutStateEnum.READY,
  memberships: [
    { project: DEFAULT_PROJECT, branch: 'main' },
    { project: PLATFORM_PROJECT, branch: 'release/1.0' },
  ],
  latestImport: SUCCEEDED_SERVICE_IMPORT,
  presentationStatus: RepositoryPresentationStatusEnum.READY,
};

const WORKER_REPOSITORY: Repository = {
  ...REPOSITORY_DEFAULTS,
  id: RUNNING_WORKER_IMPORT.repositoryId,
  providerRepositoryId: '2002',
  fullName: 'virgo/worker',
  webUrl: 'https://github.com/virgo/worker',
  checkoutKind: CheckoutKindEnum.MANAGED,
  checkoutPath: '/Users/sandeep/.virgo-dag/repositories/worker',
  branches: ['main', 'develop'],
  checkoutState: CheckoutStateEnum.PENDING,
  lastCheckedAt: null,
  createdAt: UPDATED_AT,
  memberships: [{ project: DEFAULT_PROJECT, branch: 'main' }],
  latestImport: RUNNING_WORKER_IMPORT,
  presentationStatus: RepositoryPresentationStatusEnum.CLONING,
};

const CONNECTOR_REPOSITORY: Repository = {
  ...REPOSITORY_DEFAULTS,
  id: FAILED_CONNECTOR_IMPORT.repositoryId,
  providerRepositoryId: '2003',
  fullName: 'virgo/connector',
  webUrl: 'https://github.com/virgo/connector',
  checkoutKind: CheckoutKindEnum.MANAGED,
  checkoutPath: '/Users/sandeep/.virgo-dag/repositories/connector',
  branches: ['main'],
  checkoutState: CheckoutStateEnum.PENDING,
  lastCheckedAt: null,
  memberships: [{ project: DEFAULT_PROJECT, branch: 'main' }],
  latestImport: FAILED_CONNECTOR_IMPORT,
  presentationStatus: RepositoryPresentationStatusEnum.FAILED,
};

const CONSOLE_REPOSITORY: Repository = {
  ...REPOSITORY_DEFAULTS,
  id: 'repository-console',
  providerRepositoryId: '2004',
  fullName: 'virgo/console',
  webUrl: 'https://github.com/virgo/console',
  checkoutKind: CheckoutKindEnum.EXTERNAL,
  checkoutPath: '/Users/sandeep/work/console',
  branches: ['main', 'develop'],
  checkoutState: CheckoutStateEnum.READY,
  memberships: [{ project: PLATFORM_PROJECT, branch: 'develop' }],
  latestImport: null,
  presentationStatus: RepositoryPresentationStatusEnum.READY,
};

const TOOLS_REPOSITORY: Repository = {
  ...REPOSITORY_DEFAULTS,
  id: 'repository-tools',
  providerRepositoryId: '2005',
  fullName: 'virgo/tools',
  webUrl: 'https://github.com/virgo/tools',
  checkoutKind: CheckoutKindEnum.EXTERNAL,
  checkoutPath: '/Users/sandeep/work/tools',
  branches: ['main'],
  checkoutState: CheckoutStateEnum.MISSING,
  validationMessage: 'The checkout folder does not exist.',
  memberships: [{ project: PLATFORM_PROJECT, branch: 'main' }],
  latestImport: null,
  presentationStatus: RepositoryPresentationStatusEnum.MISSING,
};

const LEGACY_REPOSITORY: Repository = {
  ...REPOSITORY_DEFAULTS,
  id: SUCCEEDED_LEGACY_IMPORT.repositoryId,
  providerRepositoryId: '2006',
  fullName: 'virgo/legacy',
  webUrl: 'https://github.com/virgo/legacy',
  checkoutKind: CheckoutKindEnum.MANAGED,
  checkoutPath: '/Users/sandeep/.virgo-dag/repositories/legacy',
  branches: ['main'],
  checkoutState: CheckoutStateEnum.READY,
  archivedAt: ARCHIVED_AT,
  updatedAt: ARCHIVED_AT,
  lastCheckedAt: ARCHIVED_AT,
  memberships: [{ project: LEGACY_PROJECT, branch: 'main' }],
  latestImport: SUCCEEDED_LEGACY_IMPORT,
  presentationStatus: RepositoryPresentationStatusEnum.ARCHIVED,
};

/**
 * Provides registration fixtures for managed and external repository checkouts.
 */
export const MOCK_REPOSITORIES: Repository[] = [
  SERVICE_REPOSITORY,
  WORKER_REPOSITORY,
  CONNECTOR_REPOSITORY,
  CONSOLE_REPOSITORY,
  TOOLS_REPOSITORY,
  LEGACY_REPOSITORY,
];

/**
 * Provides an account status fixture for authenticated GitHub access.
 */
export const MOCK_GITHUB_ACCOUNT_STATUS: GithubAccountStatus = {
  host: 'github.com',
  authenticated: true,
  login: 'sandeep',
  guidance: null,
};

/**
 * Provides an inspection fixture for a registered local clone.
 */
export const MOCK_REPOSITORY_INSPECTION: RepositoryInspection = {
  canonicalPath: CONSOLE_REPOSITORY.checkoutPath,
  remotes: [
    {
      name: 'origin',
      url: 'git@github.com:virgo/console.git',
      supported: true,
    },
    {
      name: 'upstream',
      url: 'https://github.com/virgo/console-template.git',
      supported: true,
    },
  ],
  selectedRemoteName: CONSOLE_REPOSITORY.remoteName,
  dirty: true,
  identity: CONSOLE_REPOSITORY,
  branches: CONSOLE_REPOSITORY.branches,
  existingRepository: CONSOLE_REPOSITORY,
};

/**
 * Provides branch options for cloning a GitHub repository.
 */
export const MOCK_GITHUB_BRANCHES: string[] = [
  'main',
  'develop',
  'release/1.0',
];
/**
 * Defines the default branch for cloning a GitHub repository.
 */
export const MOCK_GITHUB_DEFAULT_BRANCH = 'main';

/**
 * Provides GitHub repository names for clone suggestions.
 */
export const MOCK_GITHUB_REPOSITORY_NAMES: string[] = [
  SERVICE_REPOSITORY.fullName,
  WORKER_REPOSITORY.fullName,
  CONNECTOR_REPOSITORY.fullName,
  CONSOLE_REPOSITORY.fullName,
  TOOLS_REPOSITORY.fullName,
  LEGACY_REPOSITORY.fullName,
  'virgo/api',
  'virgo/docs',
  'virgo/cli',
  'virgo/sdk',
  'virgo/agent',
  'virgo/infra',
];
