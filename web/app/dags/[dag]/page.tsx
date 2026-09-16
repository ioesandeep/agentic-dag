import { DagScreen } from '@/components/dagScreen/dagScreen';

interface DagPageProps {
  params: Promise<{ dag: string }>;
}

const DagPage = async ({ params }: DagPageProps) => {
  const { dag } = await params;

  return <DagScreen dagName={dag} />;
};

export default DagPage;
