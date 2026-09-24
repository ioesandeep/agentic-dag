/**
 * Represents the memory file of a dag.
 */
export interface Memory {
  // The text of the memory file, empty when the file does not exist.
  content: string;
  // The modification time of the memory file, null when the file does not exist.
  updatedAt: string | null;
}
