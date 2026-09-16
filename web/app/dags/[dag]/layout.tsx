import type { ReactNode } from 'react';

import { AppLayout } from '@/components/appLayout/appLayout';
import { BackButton } from '@/components/backButton/backButton';
import { ColorSchemeToggle } from '@/components/colorSchemeToggle/colorSchemeToggle';
import { DagProvider } from '@/components/dagProvider/dagProvider';
import { DagStateFilter } from '@/components/dagStateFilter/dagStateFilter';
import { TopAppBar } from '@/components/topAppBar/topAppBar';
import { LABELS } from '@/labels/en';
import { DAGS_ROUTE } from '@/utils/route';

interface DagLayoutProps {
  params: Promise<{ dag: string }>;
  children: ReactNode;
}

const DagLayout = async ({ params, children }: DagLayoutProps) => {
  const { dag } = await params;

  return (
    <AppLayout
      topAppBar={
        <TopAppBar
          backButton={
            <BackButton href={DAGS_ROUTE} label={LABELS.dagListBack} />
          }
          title={dag}
          actions={
            <>
              <DagStateFilter />
              <ColorSchemeToggle />
            </>
          }
        />
      }
    >
      <DagProvider dagName={dag}>{children}</DagProvider>
    </AppLayout>
  );
};

export default DagLayout;
