import type { CreateProjectRequest } from '@/entities/catalog/projectRequest';

/**
 * Defines project creation values, errors, and actions.
 */
export interface CreateProjectDialogProps {
  isOpen: boolean;
  isPending: boolean;
  createProjectRequest: CreateProjectRequest;
  nameError?: string;
  descriptionError?: string;
  failureDetail?: string;
  onChange: (createProjectRequest: CreateProjectRequest) => void;
  onSubmit: (createProjectRequest: CreateProjectRequest) => void;
  onClose: () => void;
}
