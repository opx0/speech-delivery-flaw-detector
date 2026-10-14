import { useEffect, useState } from 'react';

export function RecordingPreview({ file }: { file: File }) {
  const [url, setUrl] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  useEffect(() => {
    const objectUrl = URL.createObjectURL(file);
    setUrl(objectUrl);
    setUnavailable(false);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file]);
  return <div className="recording-preview">
    <span>Listen before analyzing</span>
    {url && <audio controls preload="metadata" src={url} aria-label="Preview selected recording" onError={() => setUnavailable(true)} />}
    {unavailable && <small role="status">This browser cannot preview the format. You can still submit it for analysis.</small>}
  </div>;
}
