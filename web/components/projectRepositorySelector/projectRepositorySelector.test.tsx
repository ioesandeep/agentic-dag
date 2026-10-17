import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderToString } from 'react-dom/server';
import { beforeEach, expect, test, vi } from 'vitest';

import type { ProjectSummary } from '@/entities/catalog/project';
import { RepositoryPresentationStatusEnum } from '@/entities/catalog/repository';
import type { ProjectSelectionRepository } from '@/hooks/catalog/types';
import { LABELS } from '@/labels/en';

import { ProjectRepositorySelector } from './projectRepositorySelector';
import { SelectionHarness } from './selectionHarness';

const DEFAULT_PROJECT: ProjectSummary = { id: 'default-id', name: 'Default', isDefault: true, archivedAt: null };
const ACME_PROJECT: ProjectSummary = { id: 'acme-id', name: 'Acme', isDefault: false, archivedAt: null };
const ARCHIVED_PROJECT = { ...ACME_PROJECT, id: 'archived-id', archivedAt: '2026-10-17T00:00:00Z' };
const PROJECT_QUERY = { name: LABELS.selectionProject };
const REPOSITORY_QUERY = { name: LABELS.selectionRepository };
const RETRY_QUERY = { name: LABELS.projectsRetry };
const PROJECT_STORAGE_KEY = 'catalog.lastProjectId';
const PROJECTS = [DEFAULT_PROJECT, ACME_PROJECT, ARCHIVED_PROJECT];

const createRepository = (id: string): ProjectSelectionRepository => ({
  id, fullName: `Acme/${id}`, projects: PROJECTS,
  presentationStatus: RepositoryPresentationStatusEnum.READY,
});

const changeStoredProject = (project: ProjectSummary) => {
  window.localStorage.setItem(PROJECT_STORAGE_KEY, project.id);
  const storageEvent = new Event('storage');
  window.dispatchEvent(storageEvent);
};

beforeEach(() => window.localStorage.clear());

test.each([
  { rememberedId: ARCHIVED_PROJECT.id, expectedName: DEFAULT_PROJECT.name },
  { rememberedId: 'missing-id', expectedName: DEFAULT_PROJECT.name },
  { rememberedId: ACME_PROJECT.id, expectedName: ACME_PROJECT.name },
])('ProjectRepositorySelector restores $expectedName when server markup hydrates with $rememberedId', ({ rememberedId, expectedName }) => {
  window.localStorage.setItem(PROJECT_STORAGE_KEY, rememberedId);
  const selector = <SelectionHarness projects={PROJECTS} repositories={[]} />;
  const container = document.createElement('div');
  container.innerHTML = renderToString(selector);
  document.body.appendChild(container);
  const hydrationConfig = { container, hydrate: true };

  render(selector, hydrationConfig);

  const projectControl = screen.getByRole('combobox', PROJECT_QUERY);
  expect(projectControl).toHaveTextContent(expectedName);
});

test.each([0, 1, 2])('ProjectRepositorySelector derives repository choice when the ready count is %i', (readyCount) => {
  const readyRepositories = [createRepository('first-id'), createRepository('second-id')];
  const unavailableRepository = { ...createRepository('missing-id'), presentationStatus: RepositoryPresentationStatusEnum.MISSING };
  const unrelatedRepository = { ...createRepository('unrelated-id'), projects: [ACME_PROJECT] };
  const repositories = [...readyRepositories.slice(0, readyCount), unavailableRepository, unrelatedRepository];
  const selector = <SelectionHarness projects={PROJECTS} repositories={repositories} />;

  render(selector);

  const repositoryControl = screen.getByRole('combobox', REPOSITORY_QUERY);
  const expectedName = readyCount === 1 ? 'Acme/first-id' : LABELS.selectionRepository;
  const isDisabled = repositoryControl.getAttribute('aria-disabled') === 'true';
  expect(repositoryControl).toHaveTextContent(expectedName);
  expect(isDisabled).toBe(readyCount === 0);
});

test.each([
  { condition: 'the user selects a project by keyboard', useKeyboard: true },
  { condition: 'browser storage changes the project', useKeyboard: false },
])('ProjectRepositorySelector clears repository choice when $condition', async ({ useKeyboard }) => {
  const user = userEvent.setup();
  const repositories = [createRepository('first-id'), createRepository('second-id')];
  const selector = <SelectionHarness projects={PROJECTS} repositories={repositories} />;
  render(selector);

  await user.tab();
  await user.tab();
  await user.keyboard('{Enter}{End}{Enter}');
  const repositoryControl = screen.getByRole('combobox', REPOSITORY_QUERY);
  expect(repositoryControl).toHaveTextContent('Acme/second-id');
  if (useKeyboard) {
    const previousControl = { shift: true };
    await user.tab(previousControl);
    await user.keyboard('{Enter}{End}{Enter}');
  } else {
    act(() => changeStoredProject(ACME_PROJECT));
  }

  const projectControl = screen.getByRole('combobox', PROJECT_QUERY);
  expect(projectControl).toHaveTextContent(ACME_PROJECT.name);
  expect(repositoryControl).toHaveTextContent(LABELS.selectionRepository);
  const storedProjectId = window.localStorage.getItem(PROJECT_STORAGE_KEY);
  const preferenceCount = window.localStorage.length;
  expect(storedProjectId).toBe(ACME_PROJECT.id);
  expect(preferenceCount).toBe(1);
  act(() => changeStoredProject(DEFAULT_PROJECT));
  expect(repositoryControl).toHaveTextContent(LABELS.selectionRepository);
});

test.each([
  { projects: null, repositories: null, hasFailed: false, message: LABELS.selectionLoading },
  { projects: [], repositories: [], hasFailed: false, message: LABELS.selectionNoReadyRepository },
  { projects: null, repositories: null, hasFailed: true, message: LABELS.selectionLoadFailed },
  { projects: PROJECTS, repositories: [createRepository('first-id')], hasFailed: true, message: LABELS.selectionLoadFailed },
])('ProjectRepositorySelector displays $message when catalog requests finish', async ({ projects, repositories, hasFailed, message }) => {
  const user = userEvent.setup();
  const onRetry = vi.fn();
  const projectId = projects?.[0]?.id ?? null;
  const repositoryId = repositories?.[0]?.id ?? null;
  const selector = <ProjectRepositorySelector projects={projects} repositories={repositories}
    projectId={projectId} repositoryId={repositoryId} hasFailed={hasFailed} onRetry={onRetry}
    onProjectSelect={vi.fn()} onRepositorySelect={vi.fn()} onAddRepository={vi.fn()} />;

  render(selector);

  const stateMessage = screen.getByText(message);
  expect(stateMessage).toBeVisible();
  if (hasFailed) {
    const retryButton = screen.getByRole('button', RETRY_QUERY);
    await user.click(retryButton);
    expect(onRetry).toHaveBeenCalledOnce();
  }
});
