#!/usr/bin/env python3
"""Create an Android Compose, SwiftUI, or Compose Multiplatform starter in cwd."""

import argparse
import json
from pathlib import Path
import re
import shutil
import sys

TEMPLATES = Path(__file__).resolve().parent.parent / "examples" / "targets"
DESTINATIONS = {"android-compose": "android", "ios-swiftui": "ios", "kmp-cmp": "kmp"}
SKIP = (".DS_Store", ".git", ".gradle", ".kotlin", ".sauces", "build", "DerivedData",
        "local.properties", "xcuserdata")


def update(path, old, new):
    source = path.read_text(encoding="utf-8")
    if source.count(old) != 1:
        raise ValueError(f"unexpected template contents in {path.name}: {old}")
    path.write_text(source.replace(old, new), encoding="utf-8")


def prepare(starter, platform, name, app_id):
    if platform in {"android-compose", "kmp-cmp"}:
        build = starter / "build.gradle.kts"
        previous = "dev.sauces.fixture" if platform == "android-compose" else "dev.sauces.kmpfixture"
        update(build, f'applicationId = "{previous}"', f'applicationId = "{app_id}"')
        source = "main" if platform == "android-compose" else "androidMain"
        update(starter / "src" / source / "AndroidManifest.xml", 'android:label="Sauces Fixture"',
               f'android:label="{name}"')
        update(starter / "settings.gradle.kts", '"SaucesFixture"', f'"{name.replace(" ", "-")}"')

    if platform in {"ios-swiftui", "kmp-cmp"}:
        host = starter if platform == "ios-swiftui" else starter / "iosApp"
        project = host / "Fixture.xcodeproj" / "project.pbxproj"
        previous = "dev.sauces.swiftfixture" if platform == "ios-swiftui" else "dev.sauces.kmpfixture"
        update(project, f"PRODUCT_BUNDLE_IDENTIFIER = {previous};",
               f'PRODUCT_BUNDLE_IDENTIFIER = {app_id};\n                INFOPLIST_KEY_CFBundleDisplayName = "{name}";')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("platform", choices=DESTINATIONS)
    parser.add_argument("--name", required=True, help="display name, starting with an ASCII letter")
    parser.add_argument("--org", required=True, help="lowercase reverse-domain identifier")
    args = parser.parse_args()

    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9 _-]{0,63}", args.name):
        parser.error("--name must start with a letter and contain only ASCII letters, digits, spaces, _ or -")
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:\.[a-z][a-z0-9]*)+", args.org):
        parser.error("--org must be a lowercase reverse-domain identifier")

    dest = Path.cwd() / DESTINATIONS[args.platform]
    app_id = args.org + "." + re.sub(r"[^a-z0-9]", "", args.name.lower())
    if dest.exists() or dest.is_symlink():
        parser.error(f"destination already exists: {dest.name}/")

    try:
        dest.mkdir()
        try:
            shutil.copytree(TEMPLATES / args.platform, dest, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns(*SKIP))
            prepare(dest, args.platform, args.name, app_id)
        except (OSError, ValueError):
            shutil.rmtree(dest)
            raise
    except (OSError, ValueError) as exc:
        print(f"scaffold failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({"platform": args.platform, "root": dest.name, "application_id": app_id}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
