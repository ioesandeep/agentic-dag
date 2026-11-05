import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { usePathname } from 'next/navigation';
import { afterEach, expect, test, vi } from 'vitest';

import { LABELS } from '@/labels/en';
import { AppLayout } from '@/components/appLayout/appLayout';
import { CatalogNavigation } from './catalogNavigation';

vi.mock('next/navigation', () => ({ usePathname: vi.fn() }));

afterEach(() => vi.unstubAllGlobals());

test.each([
  ['/dags', LABELS.catalogDags],
  ['/dags/console', LABELS.catalogDags],
  ['/dags/console/UI-9', LABELS.catalogDags],
  ['/projects', LABELS.projectsHeading],
  ['/projects/project-platform', LABELS.projectsHeading],
  ['/repositories', LABELS.repositoriesHeading],
  ['/repositories/repository-service', LABELS.repositoriesHeading],
  ['/projects-other', null],
])(
  'CatalogNavigation identifies the current section when the route is %s',
  (pathname, currentLabel) => {
    const mockedUsePathname = vi.mocked(usePathname);
    mockedUsePathname.mockReturnValue(pathname);

    render(<CatalogNavigation />);

    const links = screen.getAllByRole('link');
    for (const link of links) {
      const linkLabel = link.getAttribute('aria-label');
      if (linkLabel === currentLabel) {
        expect(link).toHaveAttribute('aria-current', 'page');
      } else {
        expect(link).not.toHaveAttribute('aria-current');
      }
    }
  },
);

test('CatalogNavigation places section links before toolbar actions in keyboard order', async () => {
  const user = userEvent.setup();
  const mockedUsePathname = vi.mocked(usePathname);
  mockedUsePathname.mockReturnValue('/repositories');
  render(
    <AppLayout
      topAppBar={<button type="button">{LABELS.repositoryAdd}</button>}
    >
      {LABELS.repositoriesHeading}
    </AppLayout>,
  );

  const destinations = [
    { label: LABELS.catalogDags, href: '/dags' },
    { label: LABELS.projectsHeading, href: '/projects' },
    { label: LABELS.repositoriesHeading, href: '/repositories' },
  ];

  await user.tab();

  const collapseQuery = { name: LABELS.catalogCollapse };
  const collapseButton = screen.getByRole('button', collapseQuery);
  expect(collapseButton).toHaveFocus();

  for (const { label, href } of destinations) {
    await user.tab();

    const linkQuery = { name: label };
    const link = screen.getByRole('link', linkQuery);
    expect(link).toHaveFocus();
    expect(link).toHaveAttribute('href', href);
  }

  await user.tab();

  const addRepositoryQuery = { name: LABELS.repositoryAdd };
  const addRepositoryButton = screen.getByRole('button', addRepositoryQuery);
  expect(addRepositoryButton).toHaveFocus();
});

test('CatalogNavigation displays Settings as a disabled action', () => {
  const mockedUsePathname = vi.mocked(usePathname);
  mockedUsePathname.mockReturnValue('/repositories');
  render(<CatalogNavigation />);

  const settingsQuery = { name: LABELS.catalogSettings };
  const settingsButton = screen.getByRole('button', settingsQuery);
  expect(settingsButton).toBeDisabled();
});

test('CatalogNavigation collapses and expands the sidebar by keyboard', async () => {
  const user = userEvent.setup();
  render(<CatalogNavigation />);

  await user.tab();
  await user.keyboard('{Enter}');

  const expandQuery = { name: LABELS.catalogExpand };
  const expandButton = screen.getByRole('button', expandQuery);
  expect(expandButton).toHaveFocus();
  expect(expandButton).toHaveAttribute('aria-expanded', 'false');

  await user.keyboard(' ');

  const collapseQuery = { name: LABELS.catalogCollapse };
  const collapseButton = screen.getByRole('button', collapseQuery);
  expect(collapseButton).toHaveFocus();
  expect(collapseButton).toHaveAttribute('aria-expanded', 'true');
});

test('CatalogNavigation restores keyboard focus when the narrow drawer closes', async () => {
  const mediaQueryList = {
    matches: false,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  };

  vi.stubGlobal('matchMedia', () => mediaQueryList);

  const user = userEvent.setup();
  render(<CatalogNavigation />);

  const expandQuery = { name: LABELS.catalogExpand };
  const expandButton = screen.getByRole('button', expandQuery);

  await user.tab();
  await user.keyboard('{Enter}');

  const collapseQuery = { name: LABELS.catalogCollapse };
  const collapseButton = screen.getByRole('button', collapseQuery);
  expect(collapseButton).toHaveFocus();

  await user.keyboard('{Escape}');

  expect(expandButton).toHaveFocus();
});
