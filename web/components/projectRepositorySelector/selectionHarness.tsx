import { ThemeProvider } from '@mui/material/styles';

import type { ProjectSelectionCatalog } from '@/hooks/catalog/types';
import { useProjectSelection } from '@/hooks/catalog/useProjectSelection';
import { theme } from '@/theme/theme';

import { ProjectRepositorySelector } from './projectRepositorySelector';

/**
 * Connects selection state to the controls for interaction tests.
 */
export const SelectionHarness = (projectSelectionCatalog: ProjectSelectionCatalog) => {
  const selection = useProjectSelection(projectSelectionCatalog);
  return (
    <ThemeProvider theme={theme}>
      <ProjectRepositorySelector {...projectSelectionCatalog} {...selection} hasFailed={false}
        onProjectSelect={selection.setProjectId} onRepositorySelect={selection.setRepositoryId}
        onAddRepository={() => undefined} onRetry={() => undefined} />
    </ThemeProvider>
  );
};
