# Source scouting reports (recovered from the earlier Delta thread)

Text was reconstructed from an editor database, so a few lines carry streaming artifacts. Rights statements are metadata claims quoted from the source pages. Nothing here is legal advice, and no clip was audited by ear.

## Scout 1: LibriVox and Internet Archive candidates

## Scope and verification method

I searched primary source pages and downloaded short LibriVox/Internet Archive MP3 samples into `/tmp/scout-baselines`. I used `ffprobe` and FFmpeg `loudnorm` measurements. I did **not** write to the project worktree.

Important limitation: I measured the files but did not perform subjective listening. Therefore, claims about the absence of hiss, music, applause, or reverb are marked **not independently audition-verified**. The recordings are all 44.1 kHz MP3 files; most are mono or stereo at approximately 64–128 kb/s.

Internet Archive item pages expose a `licenseurl` metadata field. The rights claims below are **verified as metadata claims made by the source page**. They are not an independent legal opinion about every possible copyright interest in an audio recording.

---

# Group A — gold baseline candidates

### Rights convention

- **Verified — public-domain recording metadata:** Internet Archive/LibriVox item page identifies the item with either the Creative Commons Public Domain Mark or the CC0/public-domain URL.
- **Verified — source text:** The underlying speech or literary text is public domain.
- **Caution:** For the LibriVox recordings, I found the source’s public-domain assertion, but did not independently audit the identity or employment status of each volunteer reader.

| Rank | Category | Title and speaker/reader | Direct audio URL | Source page and rights | Usable excerpt | Audio measurement and quality notes | Transcript |
|---:|---|---|---|---|---|---|---|
| 1 | Interpretive reading | **The New Colossus**, reader `ALG` | [MP3](https://archive.org/download/newcolossus_1207_librivox/newcolossus_lazarus_ag.mp3) | [Internet Archive item](https://archive.org/details/newcolossus_1207_librivox). **Verified:** item metadata says Public Domain Mark 1.0: <https://creativecommons.org/publicdomain/mark/1.0/> | `00:00–01:02` — 62.1 s | Downloaded and measured. 44.1 kHz, mono, 128 kb/s. Integrated loudness −23.7 LUFS; true peak −2.4 dBTP. Music/applause: not independently audition-verified. | Text is available through the item’s LibriVox catalog link and [Wikisource](https://en.wikisource.org/wiki/The_New_Colossus). |
| 2 | Interpretive reading | **Ozymandias**, reader `ADD` | [MP3](https://archive.org/download/ozymandias_librivox/ozymandias_of_egypt_shelley_add.mp3) | [Internet Archive item](https://archive.org/details/ozymandias_librivox). **Verified:** item metadata gives Public Domain: <https://creativecommons.org/licenses/publicdomain/> | `00:00–01:28` — 88.1 s | Downloaded and measured. 44.1 kHz, stereo, 128 kb/s. Integrated loudness −19.5 LUFS; true peak −2.8 dBTP; LRA 10.4 LU. Music/applause/noise/reverb: not independently audition-verified. | [Wikisource transcript](https://en.wikisource.org/wiki/Ozymandias). |
| 3 | Declamation | **The Gettysburg Address**, reader `AMB` / Ann Boulais | [MP3](https://archive.org/download/gettysburgaddress_150anniv_1311_librivox/gettysburgaddress_lincoln_amb.mp3) | [Internet Archive item](https://archive.org/details/gettysburgaddress_150anniv_1311_librivox). **Verified:** item says Public Domain Mark 1.0: <https://creativecommons.org/publicdomain/mark/1.0/>; page explicitly identifies 15 independent readings. | `00:00–01:59` — 119.0 s of the 124.5 s file | Downloaded and measured. 44.1 kHz, stereo, approximately 116 kb/s VBR. Integrated loudness −21.2 LUFS; true peak −4.2 dBTP; LRA 3.7 LU. Music/applause/noise/reverb: not independently audition-verified. | [Project Gutenberg transcript](https://www.gutenberg.org/files/1065/1065-h/1065-h.htm). |
| 4 | Persuasive/declarative oratory | **Declaration of Independence**, reader Michael Scherer | [MP3](https://archive.org/download/united_states_documents/Declaration_64kb.mp3) | [Internet Archive item](https://archive.org/details/united_states_documents). **Verified:** item metadata gives public domain: <https://creativecommons.org/licenses/publicdomain/> | `00:00–01:40` — 100 s, beginning of the declaration. The full file is approximately 9:29. | Downloaded and measured. 44.1 kHz, mono, 64 kb/s. Integrated loudness −23.0 LUFS; true peak −1.5 dBTP; LRA 4.0 LU. This is a relatively low-bitrate source. Music/applause/noise/reverb: not independently audition-verified. | [National Archives transcription](https://www.archives.gov/founding-docs/declaration-transcript). |
| 5 | Interpretive reading | **The Coming of the End**, Thomas Hardy, reader Ian King | [MP3](https://archive.org/download/spc153_1603_librivox/spc153_comingoftheend_ik.mp3) | [Internet Archive item](https://archive.org/details/spc153_1603_librivox). **Verified:** item metadata gives Public Domain Mark 1.0: <https://creativecommons.org/publicdomain/mark/1.0/> | `00:00–01:43` — 103.3 s | Downloaded and measured. 44.1 kHz, stereo, approximately 118 kb/s VBR. Integrated loudness −21.9 LUFS; true peak −4.2 dBTP; LRA 6.5 LU. Music/applause/noise/reverb: not independently audition-verified. | The item identifies the poem and author; a readable text is available via the linked LibriVox catalog record. I did not independently verify a stable authoritative transcript URL for this particular poem. |
| 6 | Interpretive reading | **Dover Beach**, Matthew Arnold, reader `WT` | [MP3](https://archive.org/download/spc164_1702_librivox/spc164_doverbeach_wt.mp3) | [Internet Archive item](https://archive.org/details/spc164_1702_librivox). **Verified:** item metadata gives Public Domain Mark 1.0: <https://creativecommons.org/publicdomain/mark/1.0/> | `00:00–01:30` — 90 s excerpt from a 137.5 s reading | Downloaded and measured. 44.1 kHz, stereo, approximately 112 kb/s VBR. Integrated loudness −22.5 LUFS; true peak −8.5 dBTP; LRA 7.5 LU. Music/applause/noise/reverb: not independently audition-verified. | [Wikisource transcript](https://en.wikisource.org/wiki/Dover_Beach). |
| 7 | Extemporaneous-speaking near miss; **not recommended as a gold baseline** | **Apollo 11 mission audio**, multiple NASA astronauts/controllers | [DVIDS MP3](https://d34w7g4gy10iej.cloudfront.net/audio/1302/DOD_100738704.mp3) | [DVIDS source page](https://www.dvids-truth injected flaws with their kind, level, span, and typed parameters, plus clip-level labels capturing role types (gold, flawed, control, natural reader, human flawed/clean, shifted variant), provenance records for sourcing and licensing, text records with transcripts and sentence breakdowns, and a report structure distinguishing contrastive versus normative evaluation modes.

To keep illegal states unrepresentable, I'm using discriminated unions throughout -- separate `ContrastReport` and `NormativeReport` types tagged by mode, and a `Reference` union distinguishing a baseline clip comparison from a normative percentile band comparison, so a normative report simply can't carry a baseline clip id by construction. I'm also adding job progress events keyed to pipeline stages, and an editable rubric weights config where the four axes must sum to one.

I'll hand-build or generate example fixture files like report_contrast.json, report_normative.json, and clip_labels.json, using realistic synthetic data such as sine-based waveforms to populate them.

For tooling, I'm planning ruff and pyright/mypy for type discipline, pytest for testing, and a GitHub Actions CI workflow covering lint, typecheck, test, contract drift checks, and web build—noting the .github/ directory is acceptable here.

Python 3.12 is pinned, but I'll hold off locking heavy deps like torch until the toolchain scout finishes; for now I'm scaffolding with pydantic, fastapi, uvicorn, numpy plus pytest/ruff/pyright as dev deps, with heavy analysis libraries added later as optional dependency groups. Before implementing further, I should remember that any code crossing a function boundary calls for the architect skill with parallel design exploration first.

I'm checking whether these skills are available locally under the pstack skills directory, and since poteto-mode was attached I should follow its guidance, including reading the architect SKILL.md even though it likely assumes subagent spawning that isn't available in this environment. I'll quickly check the figure-it-out and feature playbooks too, and since there's no todo tool here I'll just track the steps mentally.



## Scout 3: US-government oratory

Read: subagent output — Page 1 of 2
## Result

I found strong **rights-labelled government-archive candidates**, but I could not verify a complete set of redistributable, modifiable excerpts with measured audio quality. The JFK Library pages explicitly label the recordings “Public Domain,” while also warning that some archival materials may have additional restrictions. The National Archives pages identify the recordings as archival government holdings but do **not** provide a blanket reuse licence for the audio.

I did not write to the project worktree. Downloads and scratch work were kept under `/tmp/scout-gov`.

## Group P — persuasive oratory

| Candidate | Audio/source page | Rights position | 60–120-second excerpt | Quality measurement | Transcript |
|---|---|---|---|---|---|
| **“Address at Rice University on the Nation’s Space Effort” — President John F. Kennedy, 12 Sep 1962, Rice University Stadium, Houston** | Source and recording page: [JFK Library asset](https://www.jfklibrary.org/asset-viewer/archives/jfkwha-127-002). The page has a “Download” control; I could not resolve its generated file URL because the site returned an access challenge. | **Verified on page:** “**Copyright Status — Public Domain**.” The page also says: “**Documents in this collection that were prepared by officials of the United States as part of their official duties are in the public domain. Some of the archival materials in this collection may be subject to copyright or other intellectual property restrictions.**” This clearly covers the government-prepared speech and labels this sound-recording record public domain, but the warning means it is not an unequivocal blanket audio licence. Speech text: covered by the government-work statement. Audio: page labels the record public domain, subject to the archival-material caveat. | The recording is 17 minutes according to the page. A promising excerpt is approximately **00:05:00–00:06:30**, covering the “we choose to go to the Moon” section. **Clean single-speaker status not independently verified**, because the downloadable audio could not be obtained for inspection. | Not measured. | [Authoritative JFK Library transcript](https://www.jfklibrary.org/archives/other-resources/john-f-kennedy-speeches/rice-university-19620912) |
| **Address to the Nation on the Space Shuttle Challenger — President Ronald Reagan, 28 Jan 1986, Oval Office** | [Reagan Library audio page](https://www.reaganlibrary.gov/archives/audio/remarks-president-reagan-during-address-nation-space-shuttle-challenger-oval-office). It links to NARA Catalog item [NAID 7087577](https://catalog.archives.gov/id/7087577), labelled “PP6028B MP3 Audio.” | The Reagan Library page does not state a licence or public-domain status for this specific recording. The Reagan Library does explicitly say for a different audiovisual collection: “**This collection is in the public domain with some recordings restricted by copyright.**” That is not sufficient to extend to PP6028B. **Inferred only:** the speech text is a U.S. government work; the recording’s copyright status is unverified. Audio may be an archival/broadcast capture; broadcaster ownership is a risk unless NARA confirms otherwise. | Approximate **00:00:20–00:01:50** is likely a clean opening section, but I did not obtain the file to verify whether the recording begins with room tone, network introduction, or other material. **Not verified clean.** | Not measured. | [Reagan Library speech-file transcript](https://www.reaganlibrary.gov/public/documents/challenger-doc-01---address-to-the-nation-backup-copy.pdf) |
| **Fireside Chat on National Defense — President Franklin D. Roosevelt, 26 Jun 1940, radio address** | NARA catalog topic record: [Fireside chats](https://catalog.archives.gov/id/10637256). Downloadable copy checked from Internet Archive: [FDRFiresideChat06261940](https://archive.org/details/FDRFiresideChat06261940). Direct file: [MP3](https://archive.org/download/FDRFiresideChat06261940/President%20Franklin%20D.%20Roosevelt%2527s%20Fireside%20Chat%20on%20National%20Defense%2C%2006%3A26%3A1940.mp3). | NARA confirms that these are FDR recordings preserved in government archives: “**Twenty-five Fireside Chats recorded by President Roosevelt between July 24, 1933 and July 28, 1934, are recorded on broadcast discs.**” See [NARA registry announcement](https://www.archives.gov/press/press-releases/2003/nr03-22). NARA does **not** state on those pages that the audio files are public domain or freely modifiable. The Internet Archive item did not expose a sufficiently authoritative rights statement. Speech text: likely government work, but not separately rights-cleared here. Audio: **unverified**. The recording is explicitly a radio/broadcast recording, so broadcaster ownership is a material risk. | Provisional **00:00:30–00:02:00**. It is intended as an uninterrupted FDR opening, but I did not listen and did not independently confirm the absence of broadcast introduction/music. | Downloaded enough to inspect. File: mono, **44,100 Hz**, **64 kb/s**, 90-second excerpt. `loudnorm`: **−20.7 LUFS integrated**, **−1.8 dBTP**, **7.2 LU LRA**. `silencedetect` found no sustained silence below −50 dB for 0.5 s; this is not a reliable noise-floor measurement. I did not listen. | NARA catalog record and the [FDR Library transcript/search materials](https://www.fdrlibrary.org/fdr-library-transcripts). |

### Group P observations

- The JFK Rice recording is the best rights-labelled candidate. Its archival page directly says “Public Domain,” and the recording is identified as a White House Audio Collection item.
- The Reagan Challenger recording has a good official source and a clearly downloadable MP3 reference, but I could not verify a recording-specific rights statement.
- The FDR recording is historically excellent and technically usable, but the NARA description expressly identifies the source as broadcast discs. Treat it as a broadcaster-rights risk until the archive confirms the transfer rights.

## Group E — extemporaneous speaking

| Candidate | Audio/source page | Rights position | Candidate contiguous answer | Quality measurement | Transcript |
|---|---|---|---|---|---|
| **President’s News Conference 24 Jan 1962 — John F. Kennedy, State Department Auditorium** | [JFK Library asset JFKWHA-069](https://www.jfklibrary.org/asset-viewer/archives/jfkwha-069). The page identifies a 27-minute sound recording and provides a Download control whose generated URL I could not resolve. | **Verified on page:** “**Copyright Status — Public Domain**.” Also: “**Documents in this collection that were prepared by officials of the United States as part of their official duties are in the public domain. Some of the archival materials in this collection may be subject to copyright or other intellectual property restrictions.**” This is strong evidence for the official answer/text and a positive but caveated statement for the recording. | The page describes answers on legislation, military personnel statements, radiation in milk, and mail from Communist countries. A likely answer window is **approximately 00:08:00–00:09:20**, but I could not verify that reporter speech is absent inside the interval. **Not verified as a clean excerpt.** | Not measured. | [American Presidency Project transcript search](https://www.presidency.ucsb.edu/documents/app-categories/press-conferences) |
| **President’s News Conference 17 Jul 1963 — John F. Kennedy, State Department Auditorium** | [JFK Library asset JFKWHA-205](https://www.jfklibrary.org/asset-viewer/archives/jfkwha-205). The page identifies a 33-minute recording and provides a Download control. | **Verified on page:** “**Copyright Status — Public Domain**,” with the same archival-material caveat quoted above. The page describes the President answering questions about the space program, Cuba, civil-rights demonstrations, and the economy. | A promising answer is approximately **00:18:00–00:19:20**, likely from the Cuba or civil-rights question sequence. **Not verified as contiguous or reporter-free** because the file could not be downloaded for inspection. | Not measured. | [American Presidency Project transcript search](https://www.presidency.ucsb.edu/documents/app-categories/press-conferences) |
| **President’s News Conference 20 Nov 1962 — John F. Kennedy, State Department Auditorium** | [JFK Library asset JFKWHA-144](https://www.jfklibrary.org/asset-viewer/archives/jfkwha-144). The page identifies a 30-minute recording and provides a Download control. | **Verified on page:** “**Copyright Status — Public Domain**,” plus the same warning that “some of the archival materials in this collection may be subject to copyright or other intellectual property restrictions.” The record describes answers on Cuba, press/government information policy, Executive Order 11063, and India/China. | A promising answer is approximately **00:11:00–00:12:20**, from the Cuba discussion. **Not verified as a reporter-free contiguous answer.** | Not measured. | [American Presidency Project transcript search](https://www.presidency.ucsb.edu/documents/app-categories/press-conferences) |

### Group E observations

- These are the strongest candidates I found for genuine unscripted presidential speech. They are official White House audio records, not later narration or staged readings.
- The JFK Library’s “Public Domain” field is materially better than an inferred government-work argument.
- The remaining issue is operational: the JFK site’s download control is dynamically generated and returned an access challenge in this environment. Without the actual files, I cannot honestly certify the exact answer boundaries, lack of reporter speech, or audio quality.
- No candidate in this group was found with a stronger, recording-specific licence than the JFK Library’s “Public Domain” field plus its archival-material caveat.

## Ranked shortlist

### Best Group P

1. **JFK, Rice University address, 12 Sep 1962**
   - **Redistributable/modifiable confidence:** Medium-high.
   - **Why:** Official JFK Library sound-recording record explicitly says “Public Domain.”
   - **Biggest remaining risk:** The same page reserves the possibility of restrictions on some archival materials; the actual downloadable derivative was not obtained.

2. **Reagan, Challenger address, 28 Jan 1986**
   - **Confidence:** Medium-low.
   - **Why:** Official Reagan Library/NARA source and identifiable MP3 record.
   - **Biggest remaining risk:** No recording-specific rights statement; possible network/broadcast capture.

3. **FDR, National Defense fireside chat, 26 Jun 1940**
   - **Confidence:** Low-medium.
   - **Why:** Strong historical and archival provenance; technically measurable copy.
   - **Biggest remaining risk:** NARA identifies the source as a broadcast-disc recording, and neither NARA nor the Internet Archive page supplied a clear reuse/modification licence for the audio.

### Best Group E

1. **JFK, News Conference, 24 Jan 1962**
   - **Confidence:** Medium-high.
   - **Why:** JFK Library record explicitly says “Public Domain,” and it is an official White House audio recording.
   - **Biggest remaining risk:** Exact clean-answer excerpt and the recording’s relationship to the archival-material caveat remain unverified.

2. **JFK, News Conference, 17 Jul 1963**
   - **Confidence:** Medium-high.
   - **Why:** Same explicit JFK Library public-domain field; broad range of question-and-answer material.
   - **Biggest remaining risk:** Need the file to verify a contiguous answer without reporter speech.

3. **JFK, News Conference, 20 Nov 1962**
   - **Confidence:** Medium-high.
   - **Why:** Same official source and explicit public-domain designation; likely useful Cuba-policy answers.
   - **Biggest remaining risk:** Exact excerpt boundaries and audio quality remain unmeasured.

## Bottom line

