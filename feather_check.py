#!/usr/bin/env python3
"""Mirror Feather's ASRepository decoder and report anything it would reject.

Rules transcribed from claration/Feather:
AltSourceKit/Sources/AltSourceKit/Models/ASRepository.swift
"""
import json
import re
import sys
from datetime import datetime

ISO = ["%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"]
LEGACY = [
    "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M", "%Y-%m-%d", "%a, %d %b %Y %H:%M:%S %Z",
    "%a %b %d %H:%M:%S %z %Y", "%Y-%m-%d %H:%M:%S",
]
errors = []


def parses_as_date(value):
    if isinstance(value, (int, float)):
        return True
    if not isinstance(value, str):
        return False
    text = value.strip().replace("Z", "+0000")
    for fmt in ISO + LEGACY:
        try:
            datetime.strptime(text, fmt)
            return True
        except ValueError:
            continue
    try:
        float(value)
        return True
    except ValueError:
        return False


def is_url(value):
    return isinstance(value, str) and bool(re.match(r"^[a-z][a-z0-9+.-]*:", value, re.I))


doc = json.load(open(sys.argv[1]))

# --- ASRepository ---
apps = doc.get("apps")
if not isinstance(apps, list) or not apps:
    errors.append("apps: missing or empty -> 'This source does not contain any apps.'")

for key in ("website", "iconURL", "headerURL"):
    if key in doc and doc[key] is not None and not is_url(doc[key]):
        errors.append(f"repo.{key}: not a valid URL ({doc[key]!r})")

for i, item in enumerate(doc.get("news") or []):
    for key in ("identifier", "title", "caption"):
        if not item.get(key):
            errors.append(f"news[{i}].{key}: REQUIRED (keyNotFound)")

# --- App ---
for i, app in enumerate(apps or []):
    tag = f"apps[{i}]"
    if "iconURL" not in app:
        errors.append(f"{tag}.iconURL: REQUIRED, non-optional decode (keyNotFound)")
    elif not is_url(app["iconURL"]):
        errors.append(f"{tag}.iconURL: not a valid URL ({app['iconURL']!r})")

    if "screenshots" in app and not isinstance(app["screenshots"], dict):
        errors.append(
            f"{tag}.screenshots: Feather needs a keyed iphone/ipad object; "
            f"got {type(app['screenshots']).__name__} -> typeMismatch"
        )
    if "screenshotURLs" in app and not isinstance(app["screenshotURLs"], list):
        errors.append(f"{tag}.screenshotURLs: must be a list")

    if app.get("marketplaceID", "").strip():
        errors.append(f"{tag}.marketplaceID: non-empty -> AltStore PAL repos unsupported")

    if "downloadURL" in app and not is_url(app["downloadURL"]):
        errors.append(f"{tag}.downloadURL: not a valid URL")

    if "size" in app and not isinstance(app["size"], (int, str)):
        errors.append(f"{tag}.size: must be Int64 or numeric string")

    for key in ("versionDate", "date"):
        if key in app and not parses_as_date(app[key]):
            errors.append(f"{tag}.{key}: unparseable date ({app[key]!r})")

    for j, ver in enumerate(app.get("versions") or []):
        vtag = f"{tag}.versions[{j}]"
        if "version" not in ver:
            errors.append(f"{vtag}.version: REQUIRED, non-optional decode (keyNotFound)")
        elif not isinstance(ver["version"], str):
            errors.append(f"{vtag}.version: must be a String")
        if "downloadURL" in ver and not is_url(ver["downloadURL"]):
            errors.append(f"{vtag}.downloadURL: not a valid URL")
        if "size" in ver and not isinstance(ver["size"], (int, str)):
            errors.append(f"{vtag}.size: must be UInt or numeric string")
        if "date" in ver and not parses_as_date(ver["date"]):
            errors.append(f"{vtag}.date: unparseable ({ver['date']!r})")
        if "minOSVersion" in ver and not isinstance(ver["minOSVersion"], str):
            errors.append(f"{vtag}.minOSVersion: must be a String")

if errors:
    print(f"REJECTED — {len(errors)} issue(s) Feather would hit:")
    for e in errors:
        print("  x", e)
    sys.exit(1)

print("PASS — no field would make Feather's decoder throw")
print(f"  apps={len(apps)}  versions={len(apps[0].get('versions') or [])}")
