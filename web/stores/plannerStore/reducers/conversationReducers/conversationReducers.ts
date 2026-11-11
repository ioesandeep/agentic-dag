import type { PlanMessage } from '@/entities/plan/planMessage';
import { PlanMessageKindEnum } from '@/entities/plan/planMessage';
import type {
  PlanMessageInput,
  PlannerState,
} from '@/stores/plannerStore/types';
import { updatePlan } from '@/stores/plannerStore/reducers/planUpdate/planUpdate';

/**
 * Appends a user message to a plan or node conversation.
 */
export const sendMessage = (
  plannerState: PlannerState,
  planMessageInput: PlanMessageInput,
): PlannerState => {
  const planMessage: PlanMessage = {
    id: planMessageInput.messageId,
    kind: PlanMessageKindEnum.USER,
    nodeId: planMessageInput.nodeId,
    text: planMessageInput.text,
    createdAt: planMessageInput.currentTime,
  };

  return updatePlan(plannerState, planMessageInput.planId, (plan) => ({
    ...plan,
    messages: [...plan.messages, planMessage],
    updatedAt: planMessageInput.currentTime,
  }));
};
