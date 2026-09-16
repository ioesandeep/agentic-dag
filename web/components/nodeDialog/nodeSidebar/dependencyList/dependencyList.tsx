import Box from '@mui/material/Box';
import MuiLink from '@mui/material/Link';
import Typography from '@mui/material/Typography';
import Link from 'next/link';

import { NodeStateChip } from '@/components/nodeStateChip/nodeStateChip';
import type { NodeLink } from '@/entities/nodeDetail';
import { LABELS } from '@/labels/en';

interface DependencyListProps {
  dagName: string;
  nodes: NodeLink[];
}

/**
 * Renders a state chip and a link for each dependency node.
 */
export const DependencyList = ({ dagName, nodes }: DependencyListProps) => {
  if (nodes.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        {LABELS.dependenciesEmpty}
      </Typography>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
      {nodes.map((node) => (
        <Box
          key={node.id}
          sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0 }}
        >
          <NodeStateChip state={node.state} />
          <MuiLink
            component={Link}
            href={`/dags/${dagName}/${node.id}`}
            variant="body2"
            noWrap
            sx={{ minWidth: 0 }}
          >
            {node.title}
          </MuiLink>
        </Box>
      ))}
    </Box>
  );
};
