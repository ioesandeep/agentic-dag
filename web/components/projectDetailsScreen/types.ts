/**
 * Specifies the editable project details.
 */
export interface ProjectDetailsInput {
  name: string;
  description: string;
  isArchived: boolean;
}

/**
 * Specifies the project state options.
 */
export enum ProjectStateEnum {
  ACTIVE = 'active',
  ARCHIVED = 'archived',
}
