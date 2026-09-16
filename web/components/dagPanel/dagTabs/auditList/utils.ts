import type { AuditLine } from '@/entities/dagDetail';

/**
 * Compares two audit entries by when they were recorded.
 */
export const compareByNewest = (left: AuditLine, right: AuditLine): number =>
  right.createdAt.localeCompare(left.createdAt);

/**
 * Returns the key for one audit entry.
 */
export const getAuditLineKey = (line: AuditLine): string =>
  `${line.createdAt}-${line.nodeId}-${line.state}`;
