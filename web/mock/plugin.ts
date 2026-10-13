import { Plugin } from "vite";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const contractDir = path.resolve(__dirname, "../../contract");

function generateWav() {
  const sampleRate = 16000;
  const duration = 2; // seconds
  const numSamples = sampleRate * duration;
  const buffer = new ArrayBuffer(44 + numSamples * 2);
  const view = new DataView(buffer);

  const writeString = (offset: number, string: string) => {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  };

  writeString(0, "RIFF");
  view.setUint32(4, 36 + numSamples * 2, true);
  writeString(8, "WAVE");

  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);

  writeString(36, "data");
  view.setUint32(40, numSamples * 2, true);

  let offset = 44;
  for (let i = 0; i < numSamples; i++) {
    const t = i / sampleRate;
    const sample = Math.sin(t * 440 * Math.PI * 2) * 10000;
    view.setInt16(offset, sample, true);
    offset += 2;
  }

  return Buffer.from(buffer);
}

const wavBuffer = generateWav();

export function mockApiPlugin(): Plugin {
  return {
    name: "mock-api",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (!req.url?.startsWith("/api/")) {
          return next();
        }

        if (req.url === "/api/library" && req.method === "GET") {
          res.setHeader("Content-Type", "application/json");
          res.end(
            fs.readFileSync(path.join(contractDir, "fixtures", "library.json")),
          );
          return;
        }

        if (req.url.startsWith("/api/audio/")) {
          res.setHeader("Content-Type", "audio/wav");
          res.end(wavBuffer);
          return;
        }

        if (req.url === "/api/jobs" && req.method === "POST") {
          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify({ job_id: "mock-job-123" }));
          return;
        }

        if (req.url.startsWith("/api/jobs/") && req.url.endsWith("/events")) {
          res.setHeader("Content-Type", "text/event-stream");
          res.setHeader("Cache-Control", "no-cache");
          res.setHeader("Connection", "keep-alive");

          let step = 0;
          const stages = ["decode", "align", "extract", "compare", "explain"];

          const interval = setInterval(() => {
            if (step < stages.length) {
              const event = {
                type: "progress",
                job_id: "mock-job-123",
                stage: stages[step],
                fraction: (step + 1) / stages.length,
                message: `Running ${stages[step]}...`,
              };
              res.write(`data: ${JSON.stringify(event)}\n\n`);
              step++;
            } else {
              clearInterval(interval);
              // Pick normative or contrast depending on some global state or just use contrast for now
              // Ideally the mock server remembers the last POST
              const reportPath = path.join(
                contractDir,
                "fixtures",
                "report_contrast.json",
              );
              const report = JSON.parse(fs.readFileSync(reportPath, "utf8"));

              const doneEvent = {
                type: "done",
                job_id: "mock-job-123",
                report,
              };
              res.write(`data: ${JSON.stringify(doneEvent)}\n\n`);
              res.end();
            }
          }, 500);

          req.on("close", () => clearInterval(interval));
          return;
        }

        res.statusCode = 404;
        res.end();
      });
    },
  };
}
