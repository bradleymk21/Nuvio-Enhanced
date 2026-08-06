# Nuvio Enhanced — sideload source

A personal [AltStore](https://altstore.io)/Feather source that tracks Nuvio Enhanced
iOS releases and republishes them as `apps.json`.

## Source URL

```
https://bradleymk21.github.io/Nuvio-Enhanced/apps.json
```

Add that in Feather under **Sources → +**.

## How it works

A scheduled GitHub Action runs `build_source.py` every 6 hours. The script queries
the GitHub Releases API for the upstream repo, picks the newest matching `.ipa`
assets, and rewrites `apps.json`. If the file changed, the workflow commits it.
GitHub Pages serves the result.

The workflow also runs on `workflow_dispatch` and on any push that touches
`source-config.json`, `build_source.py`, or the workflow itself. When nothing has
changed for 25 days it commits a `.last-checked` heartbeat, because GitHub
disables scheduled workflows after 60 quiet days.

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

## Which Nuvio this tracks

Upstream is [luqmanfadlli/NuvioMobile-iOS](https://github.com/luqmanfadlli/NuvioMobile-iOS),
whose **Enhanced** variant ships `com.nuvio.media`.

Three separate iOS builds use confusingly similar names. The app name distinguishes
none of them reliably — only the bundle identifier does:

| Build | App name (`CFBundleName`) | Bundle identifier |
| --- | --- | --- |
| luqmanfadlli, Enhanced variant — **tracked here** | Nuvio Enhanced | `com.nuvio.media` |
| luqmanfadlli, Full variant | Nuvio | `com.nuvio.media` |
| [yesnt10/NuvioMobile-Enhanced](https://github.com/yesnt10/NuvioMobile-Enhanced) | Nuvio Enhanced | `com.nuvio.enhanced` |

Two consequences worth remembering:

- luqmanfadlli's Full and Enhanced variants **share one bundle identifier**, so they
  overwrite each other on device. They cannot be installed side by side.
- yesnt10's build is a different app entirely. This source used to track it. Anything
  installed from the old `com.nuvio.enhanced` listings stays installed and simply stops
  receiving updates here — it is not upgraded in place, and none of its data
  (watch history, Trakt login, downloads) carries over.

### Asset selection

Each upstream release ships three assets — `Nuvio-vX.Y.Z-Enhanced.apk`,
`Nuvio-vX.Y.Z-Enhanced.ipa`, and `Nuvio-vX.Y.Z-Full.ipa` — so `assetPattern` must be
`*-Enhanced.ipa`. A bare `*.ipa` matches both IPAs and would pick whichever the API
returns first, silently publishing the Full build under the Enhanced name.

### Build numbers

Upstream tags are bare versions (`0.4.2`), so no `buildVersion` is emitted. Every tag
so far is a distinct marketing version, which is enough for clients to order releases.
`build_source.py` still parses a build number when a tag carries one — yesnt10's
`enhanced-v0.3.1-build102` scheme did, and needed it, because two of its releases
shared the version `0.2.23`.

## Installing and updating in Feather

The app bundles an extension, `PlugIns/DownloadsWidgetExtension.appex`
(`com.nuvio.media.DownloadsWidgetExtension`). Extensions need their own App ID and
provisioning profile, which fails on a free 7-day certificate. The install then dies
partway and leaves a grey placeholder icon with a cloud badge — no app icon, and it
never launches.

Fix: in Feather's signing options open **Frameworks & PlugIns** and toggle
`PlugIns/DownloadsWidgetExtension.appex` for removal before signing. The only loss is
the home-screen downloads widget.

This applies to **every** update, since Feather re-signs each new build. If an update
leaves a grey placeholder, delete it and re-sign with the extension removed — the
source is not at fault.

## Requirements

Repository **Settings → Actions → General → Workflow permissions** must be set to
**Read and write permissions**, otherwise the final commit step is rejected.
