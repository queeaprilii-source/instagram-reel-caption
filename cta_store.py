#!/usr/bin/env python3
"""Persist named CTA URLs for the instagram-reel-caption skill."""

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from urllib.parse import urlparse
from uuid import uuid4


def store_path():
    override = os.environ.get("CODEX_INSTAGRAM_CTA_STORE")
    if override:
        return Path(override).expanduser()
    codex_home = Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser()
    return codex_home / "instagram-reel-caption" / "ctas.json"


def load(path):
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or any(
        not isinstance(item, dict)
        or not all(isinstance(item.get(key), str) for key in ("id", "name", "url"))
        for item in data
    ):
        raise ValueError("CTA store has an invalid format")
    return data


def save_file(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".ctas-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write("\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def valid_url(value):
    parsed = urlparse(value)
    return (
        parsed.scheme in ("http", "https")
        and bool(parsed.netloc)
        and not any(character.isspace() for character in value)
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="Print saved CTA choices as JSON")
    save = commands.add_parser("save", help="Add a choice or update one by ID")
    save.add_argument("--id", help="ID of an existing choice to update")
    save.add_argument("--name", help="Name for a new choice or updated choice")
    save.add_argument("--url", required=True, help="Destination URL")
    args = parser.parse_args()

    path = store_path()
    try:
        choices = load(path)
        if args.command == "list":
            print(json.dumps(choices, ensure_ascii=False))
            return

        url = args.url.strip()
        if not valid_url(url):
            raise ValueError("URL must be an absolute http(s) URL without spaces")

        if args.id:
            choice = next((item for item in choices if item["id"] == args.id), None)
            if choice is None:
                raise ValueError("CTA ID not found")
            if args.name:
                name = args.name.strip()
                if not name or any(item is not choice and item["name"].casefold() == name.casefold() for item in choices):
                    raise ValueError("CTA name is empty or already in use")
                choice["name"] = name
            choice["url"] = url
        else:
            name = (args.name or "").strip()
            if not name:
                raise ValueError("--name is required for a new CTA")
            if any(item["name"].casefold() == name.casefold() for item in choices):
                raise ValueError("CTA name already exists; use its ID to update it")
            choice = {"id": uuid4().hex, "name": name, "url": url}
            choices.append(choice)

        save_file(path, choices)
        print(json.dumps(choice, ensure_ascii=False))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.exit(1, f"error: {error}\n")


if __name__ == "__main__":
    main()
