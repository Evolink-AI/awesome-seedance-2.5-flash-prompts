# Contributing

This repository collects Seedance 2.5 Flash prompts and demos. The Seedance 2.0 archive preserves examples from the previous model.

## Source evidence

For every submission, provide the public post, author profile, and an original preview or playback link. Identify Seedance 2.5 Flash using evidence from the source and check the index for duplicates.

A prompt case needs the exact public prompt and any reference requirements. When a creator shares a result without the full prompt, submit it as a demo and describe only what the source supports.

## Repository updates

Update the English README, all localized READMEs, and the source index together. Keep prompt text, source URLs, media, and anchors consistent across languages. See the [maintenance guide](docs/maintenance.md) for the index and audit commands.

Before opening a pull request, run:

```bash
python3 tools/verify_repo.py
git diff --check
```
