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

Upstream is [yesnt10/NuvioMobile-Enhanced](https://github.com/yesnt10/NuvioMobile-Enhanced),
which ships `com.nuvio.enhanced` under the app name **Nuvio Enhanced**.

Do not confuse it with [luqmanfadlli/NuvioMobile-iOS](https://github.com/luqmanfadlli/NuvioMobile-iOS),
a separate project that also calls one of its variants "Enhanced" but ships
`com.nuvio.media` under the app name **Nuvio**. The two are different apps with
different features, and their own release notes say so.

Asset naming upstream is inconsistent (`Nuvio-Enhanced-`, `NuvioEnhanced-`,
`Nuvio-`), but each release contains exactly one `.ipa`, so `*.ipa` is safe here.

`buildVersion` is parsed out of the tag (`enhanced-v0.3.1-build102` → `102`).
It matters because two releases can share a marketing version — `0.2.23` exists
as both build 97 and build 98 — and the build number is what distinguishes them.

## Requirements

Repository **Settings → Actions → General → Workflow permissions** must be set to
**Read and write permissions**, otherwise the final commit step is rejected.
