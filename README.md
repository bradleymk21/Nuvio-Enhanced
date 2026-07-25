# Nuvio Enhanced — sideload source

A personal [AltStore](https://altstore.io)/Feather source that tracks Nuvio Enhanced
iOS releases and republishes them as `apps.json`.

## Source URL

```
https://bradleymk21.github.io/Nuvio-Enhanced/apps.json
```

Add that in Feather under **Sources → +**.

## How it works

A scheduled GitHub Action runs `build_source.py` daily at 06:00 UTC. The script
queries the GitHub Releases API for the upstream repo, picks the newest matching
`.ipa` assets, and rewrites `apps.json`. If the file changed, the workflow commits
it. GitHub Pages serves the result.

The workflow also runs on `workflow_dispatch` and on any push that touches
`source-config.json`, `build_source.py`, or the workflow itself.

## Configuration

Everything lives in `source-config.json`:

| Key | Meaning |
| --- | --- |
| `repo` | Upstream `owner/name` whose releases are tracked |
| `assetPattern` | Glob selecting the right asset — releases ship more than one `.ipa` |
| `maxVersions` | How many past versions to keep listed |
| `includePrereleases` | Whether to include GitHub prereleases |
| `app.bundleIdentifier` | Must match the installed app, or Feather never shows updates |
| `app.minOSVersion` | Read from the IPA's `Info.plist` |

### Notes

`assetPattern` is deliberately `*-Enhanced.ipa` rather than `*.ipa`, because each
upstream release also ships a `-Full.ipa` variant. A looser pattern would pick
whichever GitHub happened to return first.

Releases before `0.2.18` predate the Enhanced IPA and are skipped with a log line.

## Requirements

Repository **Settings → Actions → General → Workflow permissions** must be set to
**Read and write permissions**, otherwise the final commit step is rejected.
