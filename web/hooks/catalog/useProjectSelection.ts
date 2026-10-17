'use client';

import { useState, useSyncExternalStore } from 'react';

import type { ProjectSelection, ProjectSelectionCatalog } from './types';
import { getActiveProjects, getReadyRepositories } from './utils';

const PROJECT_STORAGE_KEY = 'catalog.lastProjectId';
const STORAGE_EVENT = 'storage';

const subscribeProjectId = (onStoreChange: () => void) => {
  window.addEventListener(STORAGE_EVENT, onStoreChange);
  window.addEventListener(PROJECT_STORAGE_KEY, onStoreChange);
  return () => {
    window.removeEventListener(STORAGE_EVENT, onStoreChange);
    window.removeEventListener(PROJECT_STORAGE_KEY, onStoreChange);
  };
};

const getStoredProjectId = () => window.localStorage.getItem(PROJECT_STORAGE_KEY);
const getServerProjectId = () => null;

const storeProjectId = (projectId: string) => {
  window.localStorage.setItem(PROJECT_STORAGE_KEY, projectId);
  const projectSelectionEvent = new Event(PROJECT_STORAGE_KEY);
  window.dispatchEvent(projectSelectionEvent);
};

/**
 * Validates catalog selections and remembers the project preference.
 */
export const useProjectSelection = ({ projects, repositories }: ProjectSelectionCatalog): ProjectSelection => {
  const storedProjectId = useSyncExternalStore(subscribeProjectId, getStoredProjectId, getServerProjectId);
  const [repositorySelection, setRepositorySelection] = useState<Pick<ProjectSelection, 'projectId' | 'repositoryId'> | null>(null);
  const activeProjects = getActiveProjects(projects);
  const project = activeProjects.find((project) => project.id === storedProjectId)
    ?? activeProjects.find((project) => project.isDefault);
  const projectId = project?.id ?? null;
  if (repositorySelection !== null && repositorySelection.projectId !== projectId) {
    setRepositorySelection(null);
  }

  const readyRepositories = getReadyRepositories(repositories, projectId);
  const repositoryId = repositorySelection?.projectId === projectId ? repositorySelection?.repositoryId : null;
  const selectedRepository = readyRepositories.find((repository) => repository.id === repositoryId);
  const soleRepository = readyRepositories.length === 1 ? readyRepositories[0] : null;
  const selectedRepositoryId = selectedRepository?.id ?? soleRepository?.id ?? null;

  const setProjectId = (projectId: string) => {
    setRepositorySelection(null);
    storeProjectId(projectId);
  };
  const setRepositoryId = (repositoryId: string) => {
    const selection = { projectId, repositoryId };
    setRepositorySelection(selection);
  };

  return { projectId, repositoryId: selectedRepositoryId, setProjectId, setRepositoryId };
};
