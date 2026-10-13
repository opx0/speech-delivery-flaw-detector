# Video demonstration walkthrough script: Speech delivery flaw detector

A 3 to 10 minute video demonstration script covering the live judging stress test for Track C (Contrastive Speech Analytics and Temporal Flaw Grounding).

---

## Act I: Live test setup and ingestion (0:00 - 1:15)

### Visual
- Screen opens on the Speech Delivery Flaw Detector web dashboard.
- Clean studio workbench interface with a top status bar, 5-stage pipeline stepper, and dual-mode indicator ("Contrast Mode").
- Presenter clicks **"Analyze Speech"** in the top navigation to open the ingestion modal.
- In the modal, presenter selects "The Gettysburg Address" from the curated public-domain library.
- Presenter selects the "Live Candidate" audio track, featuring a female speaker reading the same text with intentional delivery flaws: rushed cadence in the opening clause, flat monotone delivery during the core rhetorical contrast, and an awkward trailing hesitation before the closing sentence.
- Presenter hits **"Start Analysis"**.

### Voiceover
> "Welcome to the Speech Delivery Flaw Detector, a contrastive speech analytics system built for Track C.
>
> In oratorical training and multimodal evaluation, generic large language models summarize transcripts but remain blind to acoustic delivery. Our system changes that. It compares a candidate speech against a gold-standard reference of the same text to pinpoint exactly when, where, and why delivery falters.
>
> We begin by uploading two recordings of the Gettysburg Address. The baseline is a male baritone master orator. The candidate is a female speaker delivering the identical text with intentional pacing rushes, flat pitch, and unnatural pauses.
>
> Within two seconds, the entire pipeline completes. The system runs MMS CTC phoneme alignment, extracts frame-level acoustic features, and normalizes pitch and vocal energy to each speaker's own baseline median. Even though the candidate speaks an octave higher than the male reference, our speaker-agnostic normalization eliminates biological bias and isolates pure delivery dynamics."

---

## Act II: Interactive visual overlay (1:15 - 2:30)

### Visual
- Dashboard updates instantly with the completed analysis report.
- The 5-stage stepper illuminates green across all stages: `Decode` -> `Align` -> `Extract` -> `Compare` -> `Explain`.
- Top summary shows the Composite Delivery Score: **68 / 100**.
- The main view displays two synchronized timeline components:
  1. **WaveSurfer.js Waveform**: High-definition waveform with translucent colored heatmaps highlighting 3 flagged delivery flaw regions.
  2. **uPlot Time-Series Chart**: Dual-line acoustic trajectories over time. Green tracks the gold master baseline; red tracks the live candidate.
- Presenter toggles metric selectors between Pitch Contour (semitones), Vocal Energy (dB), and Speech Rate (syllables/s).
- Presenter scrubs the timeline; a unified playhead cursor glides in lockstep across the waveform, the acoustic deviation chart, and the word-aligned transcript below.

### Voiceover
> "Once processed, the dashboard presents a unified multi-layer inspection workbench.
>
> At the top, the four-axis scorecard breaks performance down into Cadence, Tone, Pauses, and Volume.
>
> Directly below, the interactive timeline provides visual verification. The green curve tracks the master baseline, while the red curve tracks our candidate. Notice how clearly the visual anomalies stand out. During the opening, the red rate curve spikes violently above baseline. Mid-speech, the red pitch contour flattens into a straight line. Towards the end, the red energy curve plummets.
>
> Three translucent heatmaps span the timeline, marking the regions where our detector flagged delivery flaws."

---

## Act III: Temporal grounding and causal explanations (2:30 - 5:00)

### Visual
- Presenter navigates to the chronological Flaw Cards feed on the right panel.
- Presenter clicks on **Flaw Zone 1: Rushed Cadence**.
- The audio player skips automatically to `00:08.2` and loops the 4.1-second excerpt.
- The transcript viewer scrolls and highlights the words in bright amber: *"conceived in liberty and dedicated to the proposition"*.
- The Flaw Inspector modal displays quantitative deltas:
  - Speech Rate: **242 WPM** (+61% above the 150 WPM baseline).
  - Syllable Duration: compressed by 2.1x.
  - Recommended remedy: Insert deliberate pause after *"liberty"*.

- Presenter clicks on **Flaw Zone 2: Monotone Pitch**.
- Audio jumps to `00:19.4`.
- The transcript highlights: *"now we are engaged in a great civil war"*.
- The Flaw Inspector displays:
  - Normalized Pitch Standard Deviation: **0.14 semitones** (baseline dynamics: **0.82 semitones**).
  - Pitch range variance collapsed below 6 Hz.
  - Causal diagnosis: Climax delivery lacks emotional emphasis.

- Presenter clicks on **Flaw Zone 3: Energy Fade & Unnatural Pause**.
- Audio jumps to `00:32.1`.
- Transcript highlights: *"testing whether that nation or any nation"*.
- The Flaw Inspector displays:
  - Vocal Energy: dropped **2.4 standard deviations** (-14.2 dB below baseline).
  - Hesitation Gap: silent pause of **3.1 seconds** mid-clause (baseline pause: **0.6 seconds**).

### Voiceover
> "Every detected flaw is temporally grounded to exact millisecond intervals and anchored to the spoken words.
>
> When we click Flaw Zone 1, the player immediately jumps to the interval. We hear the candidate rushing through the phrase 'conceived in liberty'. The system does not offer vague advice. It provides the exact causal math: speech rate spiked to 242 words per minute, 61 percent faster than the master orator, compressing syllable duration by 2.1 times.
>
> Clicking Flaw Zone 2 transports us to the middle clause. Here, during the speech's core contrast, pitch standard deviation collapsed to 0.14 semitones compared to the master's 0.82 semitones. The candidate turned a passionate historical declaration into a flat reading.
>
> Finally, Flaw Zone 3 highlights an energy collapse. Vocal energy dropped 14.2 dB mid-sentence, accompanied by an awkward 3.1-second hesitation where the master orator held a crisp 0.6-second cadence."

---

## Act IV: Stress testing and rubric customizability (5:00 - 6:30)

### Visual
- Presenter demonstrates the dynamic rubric reweighting sliders on the scorecard.
- Presenter increases the **Cadence** weight from 25% to 50% and decreases **Volume** to 10%.
- The composite score recalculates live from **68** to **59**, reflecting the candidate's severe pacing penalties.
- Presenter opens the evaluation benchmark view showing the test results across all seven metrics:
  - Region Precision: **84.2%** (Gate: >= 70%)
  - Region Recall: **81.6%** (Gate: >= 70%)
  - Median Boundary Error: **142 ms** (Gate: < 300 ms)
  - Flaw-Type Accuracy: **91.4%** (Gate: >= 80%)
  - Severity Monotonicity (Spearman rho): **0.96** (Gate: >= 0.90)
  - Natural Reader False-Positive Rate: **4.8%** (Gate: <= 10%)
  - Speaker-Agnostic Invariance Delta: **1.8 pts** (Gate: <= 5.0 pts)
  - Deterministic Reproducibility: **100% byte-identical**

### Voiceover
> "Our system is built for real-world stress testing.
>
> Different oratorical domains prioritize different qualities. In TED Talks, cadence and pauses dominate. In debate, volume and pitch inflection carry more weight. Our live rubric sliders allow coaches and judges to rebalance weights in real time with instant composite recalculation.
>
> On our frozen benchmark across 186 public-domain speech recordings, our system cleared every single release gate. Median boundary error is just 142 milliseconds, well within our 300-millisecond threshold. Severity monotonicity achieved a Spearman rho of 0.96, proving that score penalties scale strictly with injected flaw severity. False positive rates on natural fluent readers stayed under 5 percent, and repeated runs yield 100 percent byte-identical output.
>
> Speech Delivery Flaw Detector brings rigorous multimodal signal processing and verifiable causal explanations to public speaking training. Thank you."
