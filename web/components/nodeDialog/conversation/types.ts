import type { AgentSession } from '@/entities/nodeDetail';

export interface SessionStart {
  session: AgentSession;
  // Which wake of the node this session is, counting from one.
  wake: number;
}
