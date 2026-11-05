import { RepositoryDetailsScreen } from '@/components/repositoryDetailsScreen/repositoryDetailsScreen';

interface RepositoryPageProps {
  params: Promise<{ repositoryId: string }>;
}

const RepositoryPage = async ({ params }: RepositoryPageProps) => {
  const { repositoryId } = await params;

  return <RepositoryDetailsScreen repositoryId={repositoryId} />;
};

export default RepositoryPage;
