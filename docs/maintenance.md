# Maintenance Guide

- The English README establishes prompt order and gallery order.
- The source index at `data/ingested_sources.json` records prompt text and hashes under `cases`, and source and media attribution under `demos`.
- The files in `data/localized-titles` map the numbered prompt cases to reviewed titles.
- The 11 READMEs share source order, prompt bytes, media URLs, and stable anchors. Translate visible labels and prose.
- Keep Seedance 2.0 cases in the localized archives. Use tracked preview files or original source previews when the media can be matched to a case.

Add a numbered case only when its full prompt is public. Place source-backed examples without a full prompt in the Demo Gallery. Preserve the creator attribution and pair each preview with its corresponding playback link. Check the index for duplicate sources and media IDs.

Run the repository and link checks before opening a pull request.

```bash
python3 tools/verify_repo.py
python3 tools/audit_public_surface.py --out /tmp/seedance-links.md
python3 tools/audit_rendered_media.py --out /tmp/seedance-media.md
git diff --check
```

The repository check includes localization and the live Star History rule. The rendered media check compares the GitHub output against the cover and preview URLs in the source index. For an already pushed branch, pass its repository URL with `--live-url` and its branch or commit with `--ref`.
