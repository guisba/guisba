# guisba — A Portfolio in Motion

An original, code-rendered motion-graphics film built around Guilherme Sabatini's GitHub profile and **every public repository observed on November 11, 2026**. Visual identity takes its cues from the profile README's ruby, black, white and deep red. No proprietary assets, external music, or third-party images are required.

## Featured source material

| Chapter | Project | Grounding |
| --- | --- | --- |
| 01 | [guisba](https://github.com/guisba/guisba) | Profile README: São Paulo, cybersecurity, AI, software development, economics, open to work |
| 02 | [DataBreaker](https://github.com/guisba/DataBreaker) | Local-first file metadata inspection, privacy cleaning, provenance/C2PA and verification |
| 03 | [Listed](https://github.com/guisba/Listed) | Shared game lists, Steam discovery, voting, real-time rooms, and QR invites |
| 04 | [veil](https://github.com/guisba/veil) | File sharing and chatting (public README only; no unverified security claims) |
| 05 | [github-workflow-lab](https://github.com/guisba/github-workflow-lab) | Documented GitHub workflows, PR review and automation safety |

## Play (double-click)

Open **`index.html`** in Chrome, Firefox, Edge, or Safari. No server or installation is required for playback. The HTML/Canvas preview includes timeline seeking, pause/play, fullscreen, keyboard shortcuts, and synthesised preview pulse cues. Space toggles play; Left/Right seeks 2 seconds. If you prefer reduced motion, the animation starts paused.

## Render a complete film with sound

Requires Python 3.11+, FFmpeg and Chromium for Playwright. From this directory:

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
python render.py --samples-only   # inspect scene frames
python render.py                  # H.264 MP4, 1280x720 / 24 fps with AAC original soundtrack
```

The original soundtrack is generated locally by `score.py` using procedural synthesis and no third-party recordings. Run `python score.py` to regenerate `soundtrack.wav` alone. Frames are deterministic; rendering via browser page screenshots allows you to modify `index.html` and get the exact same composition in the exported movie. Larger output: `python render.py --width 1920 --fps 30`. Avoid claiming that a particular device will meet a rendering-time target.

## Design decisions

- **Ruby as a visual anchor**: drawn from the actual profile README; the faceted 3D-like ruby is geometry rendered in canvas, rather than a downloaded model.
- **Editorial typography + forensic graphics**: the film's treatment reflects public portfolio themes and differentiates each project rather than recycling generic UI cards.
- **Project-specific visual metaphors**: an evidence inventory for DataBreaker, abstract group decisions for Listed, connected nodes for veil, PR workflow topology for GitHub Workflow Lab.
- **Source honesty**: fictional interface sample labels for Listed are abstract visualisations, not asserted screenshots or real user statistics. No private repositories are included.

## Structure

- `index.html` — complete browser player and deterministic timeline.
- `score.py` — original ambient/percussive stereo soundtrack generator.
- `render.py` — browser-to-FFmpeg exporter and scene screenshot QA.
- `requirements.txt` — Python dependencies required only for offline rendering.

All graphics and audio are generated from project code. Third-party names and brands are used descriptively.