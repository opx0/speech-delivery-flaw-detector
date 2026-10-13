"use strict";

const AXES = ["cadence", "tone", "pauses", "volume"];
const STAGES = [
  ["decode", "Decode the recording"],
  ["align", "Align the words to the audio"],
  ["extract", "Extract acoustic features"],
  ["compare", "Compare with the reference"],
  ["explain", "Explain the flaws"],
];
const ERRORS = {
  unsupported_audio: "That file could not be read as audio.",
  too_long: "That recording is too long. The limit is 10 minutes.",
  too_large: "That file is too large. The limit is 50 MB.",
  transcript_mismatch: "The words you said do not match the transcript.",
  alignment_failed: "The words could not be lined up with the audio.",
  internal: "Something went wrong on the server. Try again.",
};
const FEATURES = {
  pitch: "Pitch (semitones from your median)",
  pitch_variation: "Pitch variation (semitones)",
  speech_rate: "Speech rate (words/s)",
  energy: "Vocal energy (dB from your loud speech)",
  pause: "Silence (fraction)",
};

const $ = (id) => document.getElementById(id);
const state = { library: null, blob: null, blobName: "", report: null, weights: null, recorder: null };

function fmt(seconds) {
  const m = Math.floor(seconds / 60);
  const s = seconds - m * 60;
  return `${String(m).padStart(2, "0")}:${s.toFixed(1).padStart(4, "0")}`;
}

async function loadLibrary() {
  const response = await fetch("/api/library");
  if (!response.ok) throw new Error("The server did not return the library.");
  state.library = await response.json();
  const select = $("text-select");
  for (const entry of state.library.entries) {
    select.add(new Option(`${entry.title} (${entry.category.replace("_", " ")})`, entry.text_id));
  }
  select.add(new Option("Something else (paste a transcript)", ""));
  const demos = $("demo-select");
  for (const demo of state.library.demos) demos.add(new Option(demo.title, demo.clip_id));
  select.addEventListener("change", onTextChange);
  $("transcript").addEventListener("input", updateMode);
  onTextChange();
}

function currentEntry() {
  return state.library.entries.find((e) => e.text_id === $("text-select").value) || null;
}

function onTextChange() {
  const entry = currentEntry();
  $("transcript").value = entry ? entry.transcript : "";
  $("transcript").readOnly = false;
  updateMode();
}

function updateMode() {
  const entry = currentEntry();
  const typed = $("transcript").value.trim();
  const same = entry && typed === entry.transcript.trim();
  $("mode-note").textContent = same
    ? "Contrast mode: you will be compared with the gold reading of this text."
    : typed
      ? "Normative mode: no matching text in the library, so you will be compared with typical ranges. Findings are lower confidence."
      : "Paste or type the words you will say.";
  refreshAnalyze();
}

function refreshAnalyze() {
  $("analyze").disabled = !(state.blob && $("transcript").value.trim());
  $("chosen").textContent = state.blob ? `Recording ready: ${state.blobName}` : "No recording chosen.";
}

$("file").addEventListener("change", (event) => {
  const file = event.target.files[0];
  if (!file) return;
  state.blob = file;
  state.blobName = file.name;
  $("demo-select").value = "";
  refreshAnalyze();
});

$("demo-select").addEventListener("change", async (event) => {
  const clipId = event.target.value;
  if (!clipId) return;
  const demo = state.library.demos.find((d) => d.clip_id === clipId);
  const response = await fetch(demo.audio_url);
  state.blob = await response.blob();
  state.blobName = `${clipId}.flac`;
  const entry = state.library.entries.find((e) => e.text_id === demo.text_id);
  $("text-select").value = entry.text_id;
  onTextChange();
  const flaws = demo.flaw_kinds.length ? `contains: ${demo.flaw_kinds.join(", ")}` : "a clean control";
  $("chosen").textContent = `Demo clip ready (${flaws}).`;
  $("analyze").disabled = false;
});

$("record").addEventListener("click", async () => {
  if (state.recorder) {
    state.recorder.stop();
    return;
  }
  if (!navigator.mediaDevices || !window.MediaRecorder) {
    $("record-status").textContent = "Recording is not supported in this browser. Upload a file instead.";
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const chunks = [];
    const recorder = new MediaRecorder(stream);
    recorder.ondataavailable = (e) => chunks.push(e.data);
    recorder.onstop = () => {
      stream.getTracks().forEach((t) => t.stop());
      state.blob = new Blob(chunks, { type: recorder.mimeType });
      state.blobName = "microphone recording";
      state.recorder = null;
      $("record").textContent = "Start recording";
      $("record-status").textContent = "Recorded.";
      $("demo-select").value = "";
      refreshAnalyze();
    };
    recorder.start();
    state.recorder = recorder;
    $("record").textContent = "Stop recording";
    $("record-status").textContent = "Recording... read the text now.";
  } catch (error) {
    $("record-status").textContent = "Microphone access was denied or is unavailable.";
  }
});

function showStages() {
  const list = $("stages");
  list.innerHTML = "";
  for (const [id, label] of STAGES) {
    const item = document.createElement("li");
    item.id = `stage-${id}`;
    item.textContent = label;
    list.append(item);
  }
}

function markStage(stage, fraction) {
  let reached = false;
  for (const [id] of STAGES) {
    const item = $(`stage-${id}`);
    item.className = "";
    if (id === stage) {
      item.className = fraction >= 1 ? "done" : "active";
      reached = true;
    } else if (!reached) {
      item.className = "done";
    }
  }
}

$("analyze").addEventListener("click", async () => {
  const entry = currentEntry();
  const transcript = $("transcript").value.trim();
  const sameText = entry && transcript === entry.transcript.trim();
  const options = { transcript, library_text_id: sameText ? entry.text_id : null };
  const form = new FormData();
  form.append("audio", state.blob, state.blobName);
  form.append("options", JSON.stringify(options));
  $("progress").hidden = false;
  $("result").hidden = true;
  $("error").hidden = true;
  $("analyze").disabled = true;
  showStages();
  $("progress").scrollIntoView({ behavior: "smooth" });
  let created;
  try {
    const response = await fetch("/api/jobs", { method: "POST", body: form });
    if (!response.ok) throw new Error((await response.json()).detail || response.statusText);
    created = await response.json();
  } catch (error) {
    fail(String(error.message || error));
    return;
  }
  const source = new EventSource(`/api/jobs/${created.job_id}/events`);
  source.onmessage = (message) => {
    const event = JSON.parse(message.data);
    if (event.type === "progress") markStage(event.stage, event.fraction);
    if (event.type === "failed") {
      source.close();
      fail(ERRORS[event.code] || event.message, event.message);
    }
    if (event.type === "done") {
      source.close();
      STAGES.forEach(([id]) => ($(`stage-${id}`).className = "done"));
      render(event.report);
    }
  };
  source.onerror = () => {
    if (source.readyState === EventSource.CLOSED) return;
    source.close();
    fail("The connection to the server was lost.");
  };
});

function fail(message, detail) {
  $("error").hidden = false;
  $("error").textContent = detail && detail !== message ? `${message} ${detail}` : message;
  $("analyze").disabled = false;
}

function weightedOverall(report, weights) {
  return report.axis_scores.reduce((sum, s) => sum + s.score * weights[s.axis], 0);
}

function render(report) {
  state.report = report;
  state.weights = Object.fromEntries(report.axis_scores.map((s) => [s.axis, s.weight]));
  $("analyze").disabled = false;
  $("result").hidden = false;
  const contrast = report.reference.basis === "baseline";
  const banner = $("banner");
  banner.hidden = contrast;
  banner.textContent = "No matching baseline. Measured against typical ranges, so findings are lower confidence.";
  $("gold-fig").hidden = !contrast;
  $("player").src = URL.createObjectURL(state.blob);
  if (contrast) $("gold").src = `/api/audio/${report.reference.clip_id}`;
  renderScores();
  renderWeights();
  renderTranscript();
  renderCards();
  const select = $("feature");
  select.innerHTML = "";
  for (const series of report.overlay) select.add(new Option(FEATURES[series.feature] || series.feature, series.feature));
  select.onchange = drawChart;
  drawChart();
  $("result").scrollIntoView({ behavior: "smooth" });
}

function renderScores() {
  $("overall").textContent = Math.round(weightedOverall(state.report, state.weights));
  const box = $("axes");
  box.innerHTML = "";
  for (const s of state.report.axis_scores) {
    const row = document.createElement("div");
    row.className = "axis";
    row.innerHTML = `<span>${s.axis}</span><div class="bar"><i style="width:${s.score}%;background:var(--${s.axis})"></i></div><b>${Math.round(s.score)}</b>`;
    box.append(row);
  }
}

function renderWeights() {
  const box = $("weights");
  box.innerHTML = "";
  for (const axis of AXES) {
    const row = document.createElement("div");
    row.className = "axis";
    const id = `w-${axis}`;
    row.innerHTML = `<label for="${id}">${axis}</label><input id="${id}" type="range" min="0" max="100" value="${Math.round(state.weights[axis] * 100)}"><b id="${id}-v"></b>`;
    box.append(row);
    row.querySelector("input").addEventListener("input", () => reweigh(axis));
  }
  AXES.forEach((a) => ($(`w-${a}-v`).textContent = `${Math.round(state.weights[a] * 100)}%`));
}

function reweigh(changed) {
  const raw = Object.fromEntries(AXES.map((a) => [a, Number($(`w-${a}`).value)]));
  const total = AXES.reduce((s, a) => s + raw[a], 0) || 1;
  AXES.forEach((a) => {
    state.weights[a] = raw[a] / total;
    $(`w-${a}-v`).textContent = `${Math.round(state.weights[a] * 100)}%`;
  });
  $("overall").textContent = Math.round(weightedOverall(state.report, state.weights));
}

function regionAt(index) {
  return state.report.regions.find((r) => index >= r.words.first && index <= r.words.last);
}

function renderTranscript() {
  const box = $("transcript-view");
  box.innerHTML = "";
  state.report.words.words.forEach((word, i) => {
    const span = document.createElement("span");
    span.className = "w";
    const region = regionAt(i);
    if (region) span.classList.add(region.axis);
    span.textContent = word.text;
    span.title = fmt(word.start);
    span.dataset.index = i;
    span.addEventListener("click", () => seek(word.start));
    box.append(span, " ");
  });
}

function renderCards() {
  const box = $("cards");
  box.innerHTML = "";
  $("count").textContent = `(${state.report.regions.length})`;
  if (!state.report.regions.length) {
    box.innerHTML = '<p class="none">Nothing was flagged. Check the scores above for how close the delivery is.</p>';
    return;
  }
  for (const region of state.report.regions) {
    const d = region.deviation;
    const card = document.createElement("article");
    card.className = `card ${region.axis}`;
    const expected = d.expected.basis === "baseline" ? d.expected.value.toFixed(2) : `${d.expected.low.toFixed(2)} to ${d.expected.high.toFixed(2)}`;
    card.innerHTML = `<h4></h4><p class="quote"></p><p class="detail"></p>
      <p class="nums">${fmt(region.start)} to ${fmt(region.end)} &middot; observed ${d.observed.toFixed(2)} ${d.unit}, expected ${expected}, z ${d.z_score.toFixed(1)}
      &middot; severity <span class="sev" style="color:var(--${region.axis})"><i style="width:${Math.round(region.severity * 100)}%"></i></span></p>
      <button type="button">Play from here</button>`;
    card.querySelector("h4").textContent = region.explanation.headline;
    card.querySelector(".quote").textContent = `\u201c${region.explanation.quoted_text}\u201d`;
    card.querySelector(".detail").textContent = region.explanation.detail;
    card.querySelector("button").addEventListener("click", () => seek(Math.max(region.start - 0.3, 0)));
    box.append(card);
  }
}

function seek(time) {
  const player = $("player");
  player.currentTime = time;
  player.play();
}

function goldTime(participantTime) {
  const warp = state.report.reference.warp;
  if (participantTime <= warp[0].participant_s) return Math.max(0, warp[0].baseline_s - (warp[0].participant_s - participantTime));
  for (let i = 1; i < warp.length; i++) {
    const a = warp[i - 1], b = warp[i];
    if (participantTime <= b.participant_s) {
      const span = b.participant_s - a.participant_s || 1;
      return a.baseline_s + ((participantTime - a.participant_s) / span) * (b.baseline_s - a.baseline_s);
    }
  }
  const last = warp[warp.length - 1];
  return last.baseline_s + (participantTime - last.participant_s);
}

$("gold-sync").addEventListener("click", () => {
  const gold = $("gold");
  gold.currentTime = goldTime($("player").currentTime);
  gold.play();
});

function drawChart() {
  const report = state.report;
  const series = report.overlay.find((s) => s.feature === $("feature").value);
  const canvas = $("chart");
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height, pad = { l: 52, r: 12, t: 12, b: 26 };
  const style = getComputedStyle(document.documentElement);
  const color = (name) => style.getPropertyValue(name).trim();
  ctx.clearRect(0, 0, W, H);
  if (!series) return;
  const duration = report.participant.duration_s;
  const expected = series.expected;
  const lows = expected.basis === "band" ? expected.low : expected.values;
  const highs = expected.basis === "band" ? expected.high : expected.values;
  const all = [...series.participant, ...lows, ...highs].filter((v) => v !== null);
  let lo = Math.min(...all), hi = Math.max(...all);
  if (hi - lo < 1e-6) { hi = lo + 1; }
  const x = (t) => pad.l + (t / duration) * (W - pad.l - pad.r);
  const y = (v) => H - pad.b - ((v - lo) / (hi - lo)) * (H - pad.t - pad.b);
  for (const region of report.regions) {
    ctx.fillStyle = color(`--${region.axis}`);
    ctx.globalAlpha = 0.18;
    ctx.fillRect(x(region.start), pad.t, x(region.end) - x(region.start), H - pad.t - pad.b);
    ctx.globalAlpha = 1;
  }
  ctx.strokeStyle = color("--line");
  ctx.fillStyle = color("--muted");
  ctx.font = "12px system-ui";
  for (let i = 0; i <= 4; i++) {
    const v = lo + ((hi - lo) * i) / 4;
    ctx.beginPath(); ctx.moveTo(pad.l, y(v)); ctx.lineTo(W - pad.r, y(v)); ctx.stroke();
    ctx.fillText(v.toFixed(1), 6, y(v) + 4);
  }
  for (let t = 0; t <= duration; t += Math.max(5, Math.round(duration / 8 / 5) * 5)) ctx.fillText(`${Math.round(t)}s`, x(t) - 8, H - 8);
  const line = (values, stroke, width, dash) => {
    ctx.beginPath(); ctx.strokeStyle = stroke; ctx.lineWidth = width; ctx.setLineDash(dash);
    let pen = false;
    values.forEach((v, i) => {
      if (v === null) { pen = false; return; }
      const px = x(i * series.hop_s), py = y(v);
      if (!pen) { ctx.moveTo(px, py); pen = true; } else ctx.lineTo(px, py);
    });
    ctx.stroke(); ctx.setLineDash([]);
  };
  if (expected.basis === "band") {
    ctx.beginPath();
    expected.high.forEach((v, i) => (i ? ctx.lineTo(x(i * series.hop_s), y(v)) : ctx.moveTo(x(0), y(v))));
    for (let i = expected.low.length - 1; i >= 0; i--) ctx.lineTo(x(i * series.hop_s), y(expected.low[i]));
    ctx.closePath(); ctx.fillStyle = color("--muted"); ctx.globalAlpha = 0.18; ctx.fill(); ctx.globalAlpha = 1;
  } else {
    line(expected.values, color("--muted"), 2, [6, 4]);
  }
  line(series.participant, color("--accent"), 2, []);
  $("chart-note").textContent = expected.basis === "band"
    ? "Blue is you. The grey band is the typical range (p10 to p90)."
    : "Blue is you. The dashed grey line is the gold reading, lined up to your timing.";
  drawPlayhead.canvasImage = ctx.getImageData(0, 0, W, H);
  drawPlayhead.geom = { x, pad, H };
}

function drawPlayhead() {
  if (!drawPlayhead.canvasImage) return;
  const ctx = $("chart").getContext("2d");
  ctx.putImageData(drawPlayhead.canvasImage, 0, 0);
  const t = $("player").currentTime;
  const { x, pad, H } = drawPlayhead.geom;
  ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue("--fg").trim();
  ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(x(t), pad.t); ctx.lineTo(x(t), H - pad.b); ctx.stroke();
  const words = state.report.words.words;
  const now = words.findIndex((w) => t >= w.start && t <= w.end);
  document.querySelectorAll("#transcript-view .w.now").forEach((n) => n.classList.remove("now"));
  if (now >= 0) document.querySelector(`#transcript-view .w[data-index="${now}"]`)?.classList.add("now");
}

$("player").addEventListener("timeupdate", drawPlayhead);
$("player").addEventListener("seeked", drawPlayhead);

loadLibrary().catch((error) => {
  $("chosen").textContent = String(error.message || error);
});
