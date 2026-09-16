import { NodeScreen } from '@/components/nodeScreen/nodeScreen';

interface NodePageProps {
  params: Promise<{ dag: string; node: string }>;
}

const NodePage = async ({ params }: NodePageProps) => {
  const { dag, node } = await params;

  return <NodeScreen dagName={dag} nodeId={node} />;
};

export default NodePage;
