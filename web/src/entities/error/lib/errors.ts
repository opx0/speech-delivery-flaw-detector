import type { ErrorCode } from '../../../contract';

export const ERROR_MESSAGES: Record<ErrorCode, string> = {
  unsupported_audio: 'The audio format could not be decoded. Provide a 16–48 kHz WAV, FLAC, or MP3 file.',
  too_long: 'Recording exceeds the 10-minute maximum duration.',
  too_large: 'Upload exceeds the 50 MB file size limit.',
  transcript_mismatch: 'The words spoken do not match the expected library transcript sufficiently.',
  alignment_failed: 'Phonetic forced alignment failed to match audio with the transcript.',
  internal: 'An unexpected processing error occurred. Please try again.',
};
