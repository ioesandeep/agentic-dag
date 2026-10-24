import { act, render, screen } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';

import type { Repository } from '@/entities/catalog/repository';
import { RepositoryPresentationStatusEnum } from '@/entities/catalog/repository';
import { ImportStatusEnum } from '@/entities/catalog/repositoryImport';
import { LABELS, REPOSITORY_STATUS_LABELS } from '@/labels/en';
import { MOCK_REPOSITORIES } from '@/mocks/catalogMocks';
import { RUNNING_WORKER_IMPORT } from '@/mocks/catalogRepositoryImports';
import { formatLabel } from '@/utils/formatLabel';
import { RepositoryStatus } from './repositoryStatus';
import { RepositoryStatusVariantEnum } from './types';

const createRepository = (overrides: Partial<Repository>): Repository => {
  const [repository] = MOCK_REPOSITORIES;
  if (repository === undefined) {
    throw new Error('The repository fixture is missing.');
  }

  return { ...repository, ...overrides };
};

afterEach(() => vi.useRealTimers());

test.each(Object.values(RepositoryPresentationStatusEnum))(
  'RepositoryStatus displays its status label when the status is %s',
  (presentationStatus) => {
    const repository = createRepository({ presentationStatus });

    render(<RepositoryStatus repository={repository} />);

    expect(screen.getByRole('status')).toHaveTextContent(
      REPOSITORY_STATUS_LABELS[presentationStatus],
    );
  },
);

test.each([
  {
    presentationStatus: RepositoryPresentationStatusEnum.QUEUED,
    status: ImportStatusEnum.QUEUED,
    startedAt: null,
    duration: '2 min, 30 sec',
    nextDuration: '2 min, 31 sec',
  },
  {
    presentationStatus: RepositoryPresentationStatusEnum.CLONING,
    status: ImportStatusEnum.RUNNING,
    startedAt: '2026-10-15T12:01:00Z',
    duration: '1 min, 30 sec',
    nextDuration: '1 min, 31 sec',
  },
])(
  'RepositoryStatus updates elapsed time when the clone is $presentationStatus',
  ({ presentationStatus, status, startedAt, duration, nextDuration }) => {
    vi.useFakeTimers();
    vi.setSystemTime('2026-10-15T12:02:30Z');

    const latestImport = { ...RUNNING_WORKER_IMPORT, status, startedAt };
    const repository = createRepository({ presentationStatus, latestImport });
    const elapsedValues = { duration };
    const nextElapsedValues = { duration: nextDuration };

    render(<RepositoryStatus repository={repository} />);

    expect(
      screen.getByText(formatLabel(LABELS.repositoryCloneElapsed, elapsedValues)),
    ).toBeVisible();

    expect(screen.getByRole('progressbar')).not.toHaveAttribute('aria-valuenow');

    act(() => vi.advanceTimersByTime(1000));

    expect(
      screen.getByText(formatLabel(LABELS.repositoryCloneElapsed, nextElapsedValues)),
    ).toBeVisible();
  },
);

test.each([RepositoryStatusVariantEnum.STATUS, RepositoryStatusVariantEnum.PROGRESS])(
  'RepositoryStatus separates progress from the status label when the variant is %s',
  (variant) => {
    vi.useFakeTimers();
    vi.setSystemTime('2026-10-15T12:02:30Z');

    const repositoryOverrides = {
      presentationStatus: RepositoryPresentationStatusEnum.CLONING,
      latestImport: RUNNING_WORKER_IMPORT,
    };

    const repository = createRepository(repositoryOverrides);
    const elapsedValues = { duration: '2 min, 30 sec' };
    const elapsedLabel = formatLabel(LABELS.repositoryCloneElapsed, elapsedValues);

    render(<RepositoryStatus repository={repository} variant={variant} />);

    if (variant === RepositoryStatusVariantEnum.STATUS) {
      expect(screen.getByRole('status')).toHaveTextContent(REPOSITORY_STATUS_LABELS.cloning);
      expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
      expect(screen.queryByText(elapsedLabel)).not.toBeInTheDocument();

      return;
    }

    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    expect(screen.getByRole('progressbar')).not.toHaveAttribute('aria-valuenow');
    expect(screen.getByText(elapsedLabel)).toBeVisible();
  },
);

test('RepositoryStatus displays a cancellation request until the clone confirms cancellation', () => {
  const latestImport = { ...RUNNING_WORKER_IMPORT, cancelRequestedAt: '2026-10-15T12:00:30Z' };
  const repository = createRepository({
    presentationStatus: RepositoryPresentationStatusEnum.CLONING,
    latestImport,
  });

  const cancelledImport = {
    ...latestImport,
    status: ImportStatusEnum.CANCELLED,
    finishedAt: '2026-10-15T12:00:31Z',
  };

  const cancelledRepository = {
    ...repository,
    presentationStatus: RepositoryPresentationStatusEnum.CANCELLED,
    latestImport: cancelledImport,
  };

  const { rerender } = render(<RepositoryStatus repository={repository} />);

  expect(screen.getByRole('status')).toHaveTextContent(LABELS.repositoryCancellationRequested);
  expect(screen.queryByText(REPOSITORY_STATUS_LABELS.cancelled)).not.toBeInTheDocument();

  rerender(<RepositoryStatus repository={cancelledRepository} />);

  expect(screen.getByRole('status')).toHaveTextContent(REPOSITORY_STATUS_LABELS.cancelled);
  expect(screen.queryByText(LABELS.repositoryCancellationRequested)).not.toBeInTheDocument();
  expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
});
