"""Numbers that the feature extractor, the comparison and the injectors must agree on."""

HOP_S = 0.01
"""Spacing of every `FeatureTrack` sample, in seconds."""

OVERLAY_HOP_S = 0.05
"""Spacing of the series sent to the dashboard. Tracks are down-sampled from `HOP_S`."""

SMOOTH_S = 0.25
"""Evidence is smoothed over this span before a region is flagged."""

MIN_REGION_S = 0.5
"""A flagged region shorter than this is dropped."""

PAUSE_MIN_S = 0.15
"""A silence at least this long is a pause and appears in `RecordingFeatures.pauses`."""

N_MFCC = 13
