# Record the demonstration video

Target length is 3 to 10 minutes. The video has not been recorded or published.
Use the real application and read values from the screen. Do not promise a processing time,
a score, or a finding count before the recording completes.

## Prepare

1. Follow [the launch guide](LOCAL_SETUP.md). Run one analysis before recording to load the model.
2. Keep the dataset manifest and technical report available in separate windows.
3. Use The New Colossus dragging-pace example. The verified browser run found two regions in
   `new-colossus.drag-l3`. The rushed level-three example returned no findings.
4. Record the application, terminal, and your narration. Use audible playback when comparing passages.
5. Use the full evaluation results in [the technical report](TECHNICAL_REPORT.md).

## Introduce the task, about 30 seconds

Show the welcome screen. Explain that the app compares delivery of the same text, not content
quality. Say that it scores cadence, tone, pauses, and volume and links findings to timestamps
and measured differences.

## Explain the dataset, about one minute

Show the manifest and dataset release. Explain the six source texts and public-domain provenance.
Describe the 186 recordings, including gold readings, independent readers, neutral controls,
four severity levels for each injected flaw, mixed flaws, and shifted controls.

Show one labeled passage and its physical injection parameters. Explain that synthetic injections
provide known timing labels but do not replace testing on new human recordings.

## Run a real analysis, about one minute

Choose **Explore examples**, **The New Colossus**, and **Dragging pace**.
Show the progress stages and wait for the actual report. Explain forced alignment and the
speaker-relative pitch and energy measurements. If processing is slow, keep the delay visible
or identify any edited wait in the narration.

## Inspect findings, about two minutes

Select a finding. Read its actual timestamps, quoted words, observed speaking pace, and gold pace.
Use **Play passage** to hear the participant, then **Gold reference** to hear the comparison.

Open **Acoustic features** and inspect pace and pitch. Click the chart to seek.
Return to **Transcript** and click a word. Explain that the measurements describe acoustic
differences and do not prove that a listener would judge every difference as a flaw.

## Change the rubric and discuss results, about one minute

Open **Adjust rubric**, increase the cadence weight, and read the updated score.
Export the report. Show the full evaluation table in the technical report, not a nonexistent
dashboard benchmark view.

State the measured results. Precision is 80.34%, recall is 20.26%, and median matched boundary
error is 168.45 ms. All three held-out natural readers received findings, so their false-positive
rate is 100%. Recall and false-positive rate fail the stated targets. The three repeated GPU runs
of one sample produced identical reports. Cross-environment reproducibility remains unverified.

## Close, about 30 seconds

Show the repository and public dataset release links. Name the remaining work: improve detection
on independent readers, add the held-out human recordings, and verify deployment on other hosts.
Upload the recording to YouTube and add its URL to the README before submission.
