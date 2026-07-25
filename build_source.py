#!/usr/bin/env python3
"""Build an AltStore/Feather source (apps.json) from a GitHub repo's releases.

Reads source-config.json, queries the GitHub Releases API, and writes apps.json
next to this script. Standard library only, so CI needs no pip install.
"""

import fnmatch
import json
import os
import re
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "source-config.json")
OUTPUT_PATH = os.path.join(HERE, "apps.json")

API = "https://api.github.com/repos/{repo}/releases?per_page=100"
VERSION_RE = re.compile(r"\d+(?:\.\d+)*")
# Upstream tags look like "enhanced-v0.3.1-build102". Two releases can share a
# marketing version, so the build number is what tells them apart.
BUILD_RE = re.compile(r"build[-_]?(\d+)", re.IGNORECASE)
DESCRIPTION_LIMIT = 2000


def fail(message):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def load_config():
    try:
        with open(CONFIG_PATH, encoding="utf-8") as handle:
            config = json.load(handle)
    except FileNotFoundError:
        fail(f"{CONFIG_PATH} not found")
    except json.JSONDecodeError as exc:
        fail(f"source-config.json is not valid JSON: {exc}")

    repo = config.get("repo", "")
    if "REPLACE_ME" in repo or "/" not in repo:
        fail('set "repo" in source-config.json to "owner/name"')
    return config


def fetch_releases(repo):
    request = urllib.request.Request(
        API.format(repo=repo),
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "build-source-script",
        },
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        fail(f"GitHub API returned {exc.code} for {repo}: {exc.read()[:200]!r}")
    except urllib.error.URLError as exc:
        fail(f"could not reach the GitHub API: {exc.reason}")


def pick_asset(release, pattern):
    for asset in release.get("assets", []):
        if fnmatch.fnmatch(asset.get("name", ""), pattern):
            return asset
    return None


def version_from_tag(tag):
    match = VERSION_RE.search(tag or "")
    return match.group(0) if match else (tag or "0")


def normalize_date(value):
    # GitHub already returns ISO-8601 UTC (e.g. 2026-01-31T12:00:00Z).
    return value or "1970-01-01T00:00:00Z"


def build_versions(releases, config):
    pattern = config.get("assetPattern", "*.ipa")
    include_prereleases = bool(config.get("includePrereleases", False))
    min_os = config.get("app", {}).get("minOSVersion")

    versions = []
    for release in releases:
        if release.get("draft"):
            continue
        if release.get("prerelease") and not include_prereleases:
            continue

        asset = pick_asset(release, pattern)
        if asset is None:
            print(f"skipping {release.get('tag_name')}: no asset matching {pattern!r}")
            continue

        notes = (release.get("body") or "").strip()
        tag = release.get("tag_name") or ""
        entry = {
            "version": version_from_tag(tag),
            "date": normalize_date(asset.get("created_at") or release.get("published_at")),
            "localizedDescription": notes[:DESCRIPTION_LIMIT],
            "downloadURL": asset["browser_download_url"],
            "size": asset["size"],
        }
        if min_os:
            entry["minOSVersion"] = min_os

        build_match = BUILD_RE.search(tag)
        if build_match:
            entry["buildVersion"] = build_match.group(1)

        versions.append(entry)

    if not versions:
        fail(f"no releases had an asset matching {pattern!r}")

    max_versions = int(config.get("maxVersions", 5))
    return versions[:max_versions]


def build_source(config, versions):
    source = config.get("source", {})
    app = config.get("app", {})

    entry = {
        "name": app.get("name", "App"),
        "bundleIdentifier": app["bundleIdentifier"],
        "developerName": app.get("developerName", ""),
        "subtitle": app.get("subtitle", ""),
        "localizedDescription": app.get("localizedDescription", ""),
        "category": app.get("category", "entertainment"),
        "versions": versions,
        # Mirror the newest version at the top level for older clients.
        "version": versions[0]["version"],
        "versionDate": versions[0]["date"],
        "versionDescription": versions[0]["localizedDescription"],
        "downloadURL": versions[0]["downloadURL"],
        "size": versions[0]["size"],
    }
    for key in ("iconURL", "tintColor"):
        if app.get(key):
            entry[key] = app[key]

    # Feather decodes "screenshots" as a keyed iphone/ipad object and throws on
    # an array, which kills the whole document. The array form is screenshotURLs.
    shots = app.get("screenshotURLs") or []
    if shots:
        entry["screenshotURLs"] = shots

    document = {
        "name": source.get("name", "Source"),
        "identifier": source.get("identifier", "com.example.source"),
        "subtitle": source.get("subtitle", ""),
        "description": source.get("description", ""),
        "website": source.get("website", ""),
        "apps": [entry],
        "news": [],
    }
    for key in ("iconURL", "headerURL", "tintColor"):
        if source.get(key):
            document[key] = source[key]
    return document


# AltStore's decoder declares these non-optional. A missing key makes clients
# reject the entire document with an unhelpful "data couldn't be read" error,
# so fail here instead, where the cause is obvious.
REQUIRED_SOURCE_KEYS = ("name", "identifier", "apps")
REQUIRED_APP_KEYS = (
    "name",
    "bundleIdentifier",
    "developerName",
    "localizedDescription",
    "iconURL",
    "versions",
)
REQUIRED_VERSION_KEYS = ("version", "date", "downloadURL", "size")


def validate(document):
    missing = [k for k in REQUIRED_SOURCE_KEYS if not document.get(k)]
    if missing:
        fail(f"source is missing required key(s): {', '.join(missing)}")

    for app in document["apps"]:
        missing = [k for k in REQUIRED_APP_KEYS if not app.get(k)]
        if missing:
            fail(
                f"app {app.get('bundleIdentifier', '?')} is missing required "
                f"key(s): {', '.join(missing)} — set them in source-config.json"
            )
        # Feather decodes this as a keyed iphone/ipad object, not an array.
        if "screenshots" in app and not isinstance(app["screenshots"], dict):
            fail(
                "app screenshots must be an object keyed by iphone/ipad; "
                "use screenshotURLs for a plain list"
            )

        for version in app["versions"]:
            missing = [k for k in REQUIRED_VERSION_KEYS if version.get(k) in (None, "")]
            if missing:
                fail(
                    f"version {version.get('version', '?')} is missing required "
                    f"key(s): {', '.join(missing)}"
                )

    # News entries need all three or Feather rejects the document.
    for item in document.get("news", []):
        missing = [k for k in ("identifier", "title", "caption") if not item.get(k)]
        if missing:
            fail(f"news item is missing required key(s): {', '.join(missing)}")


def main():
    config = load_config()
    releases = fetch_releases(config["repo"])
    versions = build_versions(releases, config)
    document = build_source(config, versions)
    validate(document)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    print(f"wrote apps.json with {len(versions)} version(s); newest {versions[0]['version']}")


if __name__ == "__main__":
    main()
