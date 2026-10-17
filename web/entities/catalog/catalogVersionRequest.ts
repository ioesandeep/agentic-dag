/**
 * Requires a catalog mutation to match the current record version.
 */
export interface CatalogVersionRequest {
  expectedVersion: number;
}
