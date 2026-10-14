import { useState } from "react";
import { Search } from "lucide-react";
import type { FlawRegion, WordAlignment } from "../../../contract";
import { formatTime } from "../../../shared/lib";
import { KIND_LABELS } from "../../../entities/flaw";

export interface TranscriptViewerProps {
  words: WordAlignment;
  currentTime: number;
  regions: FlawRegion[];
  selectedId: string | null;
  onSeek: (seconds: number) => void;
  onSelect: (id: string) => void;
  inspectionOnly?: boolean;
}

export function TranscriptViewer({
  words,
  currentTime,
  regions,
  selectedId,
  onSeek,
  onSelect,
  inspectionOnly = false,
}: TranscriptViewerProps) {
  const [query, setQuery] = useState("");
  const matches = query.trim()
    ? words.words.filter((word) =>
        word.text.toLowerCase().includes(query.trim().toLowerCase()),
      ).length
    : 0;
  return (
    <div className="transcript-view">
      <div className="transcript-toolbar">
        <div>
          <span className="tiny-dot teal-dot" /> Word-aligned transcript
        </div>
        <label className="transcript-search">
          <Search size={15} />
          <input
            aria-label="Find in transcript"
            placeholder="Find a word…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          {query && <span>{matches}</span>}
        </label>
      </div>
      <div className="transcript-content">
        {words.sentences.map((sentence, index) => (
          <div
            className="transcript-paragraph"
            key={`${sentence.first}-${sentence.last}`}
          >
            <button
              className="paragraph-time"
              onClick={() => onSeek(words.words[sentence.first]?.start ?? 0)}
              aria-label={`${inspectionOnly ? 'Inspect' : 'Seek to'} sentence ${index + 1}`}
            >
              {formatTime(words.words[sentence.first]?.start ?? 0)}
            </button>
            <p>
              {words.words
                .slice(sentence.first, sentence.last + 1)
                .map((word, offset) => {
                  const wordIndex = sentence.first + offset;
                  const region = regions.find(
                    (item) =>
                      wordIndex >= item.words.first &&
                      wordIndex <= item.words.last,
                  );
                  const active =
                    currentTime >= word.start && currentTime < word.end;
                  const match =
                    Boolean(query.trim()) &&
                    word.text
                      .toLowerCase()
                      .includes(query.trim().toLowerCase());
                  return (
                    <span key={wordIndex}>
                      <button
                        className={`transcript-word${region ? " flagged" : ""}${region?.id === selectedId ? " selected" : ""}${active ? " speaking" : ""}${match ? " search-match" : ""}`}
                        onClick={() => {
                          if (region) onSelect(region.id);
                          onSeek(word.start);
                        }}
                        title={`${formatTime(word.start)}${region ? ` · ${KIND_LABELS[region.kind]}` : ""}`}
                        aria-label={`${word.text}, ${formatTime(word.start)}${region ? `, ${KIND_LABELS[region.kind]}` : ""}`}
                      >
                        {word.text}
                      </button>{" "}
                    </span>
                  );
                })}
            </p>
          </div>
        ))}
      </div>
      <div className="transcript-legend">
        <span>
          <i className="legend-highlight" /> Delivery finding
        </span>
        <span>
          <i className="legend-playhead" /> {inspectionOnly ? 'Inspection position' : 'Currently speaking'}
        </span>
        <span>{inspectionOnly ? 'Click any word to inspect its timestamp' : 'Click any word to listen from there'}</span>
      </div>
    </div>
  );
}
