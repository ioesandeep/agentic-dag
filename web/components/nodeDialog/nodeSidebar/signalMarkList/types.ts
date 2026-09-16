import type { SignalKind } from '@/entities/nodeDetail';

export interface SignalMark {
  signal: SignalKind;
  // How far this signal has been acted on.
  mark: string;
}
