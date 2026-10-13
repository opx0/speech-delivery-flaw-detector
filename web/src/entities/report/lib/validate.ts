import type { Contract } from '../../../contract';

export function validatePayload<K extends keyof Contract>(
  root: K,
  payload: unknown,
): Contract[K] {
  if (!payload || typeof payload !== 'object') {
    throw new Error(`Invalid payload: expected object for ${String(root)}`);
  }
  const obj = payload as Record<string, unknown>;
  if (root === 'LibraryListing') {
    if (!Array.isArray(obj.entries) || !Array.isArray(obj.demos)) {
      throw new Error('Invalid LibraryListing: missing entries or demos');
    }
  } else if (root === 'Report') {
    if (typeof obj.overall !== 'number' || !obj.participant) {
      throw new Error('Invalid Report: missing overall or participant');
    }
  }
  return payload as Contract[K];
}
