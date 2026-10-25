import { notFound } from 'next/navigation';
import type { ReactNode } from 'react';

import { MOCK_PROJECTS } from '@/mocks/catalogMocks';
import type { ProjectPageProps } from './types';

interface ProjectLayoutProps extends ProjectPageProps {
  children: ReactNode;
}

const ProjectLayout = async ({ params, children }: ProjectLayoutProps) => {
  const { projectId } = await params;
  const project = MOCK_PROJECTS.find((project) => project.id === projectId);
  if (project === undefined) {
    notFound();
  }

  return children;
};

export default ProjectLayout;
