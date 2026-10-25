import { notFound } from 'next/navigation';

import { ProjectDetailsScreen } from '@/components/projectDetailsScreen/projectDetailsScreen';
import { MOCK_PROJECTS } from '@/mocks/catalogMocks';
import type { ProjectPageProps } from './types';

const ProjectPage = async ({ params }: ProjectPageProps) => {
  const { projectId } = await params;
  const project = MOCK_PROJECTS.find((project) => project.id === projectId);
  if (project === undefined) {
    notFound();
  }

  return <ProjectDetailsScreen project={project} />;
};

export default ProjectPage;
