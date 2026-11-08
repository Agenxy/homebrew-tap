#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Merge a Dibs cask branch once it is proved to be the published release's cask.

The Dibs release workflow pushes the signed cask to `cask-<version>` with a
deploy key, which can push and cannot call the API, so until this existed a
person opened and merged the pull request by hand. The click carried no
judgement: everything a reviewer could check is checked here, against facts
the branch pusher cannot forge.

  * the branch is `cask-<x.y.z>` and changes `Casks/dibs.rb` and nothing else;
  * the cask names that version, and it is newer than the one on main, so a
    replayed old branch cannot downgrade every `brew upgrade`;
  * `Agenxy/dibs` has published `v<version>` as an immutable, non-draft,
    non-prerelease release;
  * the branch's cask is byte-for-byte that release's `dibs.rb` asset, by the
    digest GitHub computed when the asset was uploaded.

Anything else fails the run and leaves the branch for a person. The merge is
pinned to the verified commit, so a push after verification makes it refuse.

Runs from main's copy only (see cask-merge.yml). DRY_RUN=1 verifies and stops
before opening or merging anything; BASE=<commit> (dry runs only) verifies
against an older main, which is how the accepting path is exercised against a
release that has already merged.
"""

import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"
CASK = "Casks/dibs.rb"
RELEASE_REPO = "Agenxy/dibs"
BRANCH = re.compile(r"cask-(\d+)\.(\d+)\.(\d+)")
VERSION = re.compile(r'^\s*version "(\d+)\.(\d+)\.(\d+)"\s*$', re.MULTILINE)


class Refused(Exception):
    """The branch is not provably the release's cask; a person decides."""


def call(method, path, token, body=None, raw=False):
    req = urllib.request.Request(
        API + path,
        method=method,
        data=None if body is None else json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.raw" if raw else "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path}: HTTP {e.code}: {e.read().decode(errors='replace')[:400]}") from e
    return data if raw else json.loads(data or b"null")


def cask_version(text):
    found = VERSION.findall(text)
    if len(found) != 1:
        raise Refused(f"expected exactly one version line in {CASK}, found {len(found)}")
    return tuple(int(p) for p in found[0])


def verify(repo, branch, sha, token, base="main"):
    """Return the version string when the branch may merge, None when main already has it."""
    m = BRANCH.fullmatch(branch)
    if not m:
        raise Refused(f"{branch!r} is not a cask-<x.y.z> branch")
    want = tuple(int(p) for p in m.groups())
    version = ".".join(m.groups())

    cmp = call("GET", f"/repos/{repo}/compare/{base}...{sha}", token)
    files = [f["filename"] for f in cmp.get("files", [])]
    if not files:
        print(f"{branch} at {sha} changes nothing against main: already merged")
        return None
    if files != [CASK]:
        raise Refused(f"{branch} changes {files}; only {CASK} may change")

    cask = call("GET", f"/repos/{repo}/contents/{CASK}?ref={sha}", token, raw=True)
    if cask_version(cask.decode()) != want:
        raise Refused(f"{CASK} on {branch} does not name version {version}")
    main = call("GET", f"/repos/{repo}/contents/{CASK}?ref={base}", token, raw=True)
    if want <= cask_version(main.decode()):
        raise Refused(f"{version} is not newer than the cask on main; refusing a downgrade or replay")

    try:
        rel = call("GET", f"/repos/{RELEASE_REPO}/releases/tags/v{version}", token)
    except RuntimeError as e:
        raise Refused(f"no readable {RELEASE_REPO} release v{version}: {e}") from e
    if rel.get("draft") or rel.get("prerelease") or rel.get("immutable") is not True:
        raise Refused(
            f"{RELEASE_REPO} v{version} is not a published immutable release "
            f"(draft={rel.get('draft')}, prerelease={rel.get('prerelease')}, immutable={rel.get('immutable')})"
        )
    assets = [a for a in rel.get("assets", []) if a["name"] == "dibs.rb"]
    if len(assets) != 1:
        raise Refused(f"{RELEASE_REPO} v{version} has {len(assets)} dibs.rb assets, expected 1")
    digest = "sha256:" + hashlib.sha256(cask).hexdigest()
    if assets[0].get("digest") != digest:
        raise Refused(f"{CASK} on {branch} is {digest}; the release's dibs.rb is {assets[0].get('digest')}")
    print(f"{branch} at {sha} is {RELEASE_REPO} v{version}'s dibs.rb ({digest})")
    return version


def merge(repo, branch, sha, version, token):
    owner = repo.split("/")[0]
    open_prs = call("GET", f"/repos/{repo}/pulls?state=open&head={owner}:{branch}", token)
    if open_prs:
        pr = open_prs[0]
    else:
        pr = call("POST", f"/repos/{repo}/pulls", token, {
            "title": f"dibs {version}",
            "head": branch,
            "base": "main",
            "body": (
                f"Signed cask for the published, immutable "
                f"[v{version}](https://github.com/{RELEASE_REPO}/releases/tag/v{version}), "
                f"pushed by the release workflow and verified by cask-merge against the "
                f"release's dibs.rb digest."
            ),
        })
    if pr["head"]["sha"] != sha:
        raise Refused(f"PR #{pr['number']} head is {pr['head']['sha']}, verified {sha}; refusing")
    call("PUT", f"/repos/{repo}/pulls/{pr['number']}/merge", token, {
        "merge_method": "squash",
        "sha": sha,
        "commit_title": f"Brew cask update for dibs v{version} (#{pr['number']})",
    })
    print(f"merged PR #{pr['number']} ({pr['html_url']})")


def main():
    repo, branch, sha = (os.environ[k] for k in ("REPO", "BRANCH", "SHA"))
    token = os.environ["GITHUB_TOKEN"]
    base = os.environ.get("BASE", "main")
    dry = os.environ.get("DRY_RUN") == "1"
    if base != "main" and not dry:
        print("BASE is for dry runs only", file=sys.stderr)
        return 2
    try:
        version = verify(repo, branch, sha, token, base)
        if version is None:
            return 0
        if dry:
            print("DRY_RUN=1: verified, not opening or merging")
            return 0
        merge(repo, branch, sha, version, token)
    except Refused as e:
        print(f"refused: {e}. The branch is left for a person to inspect.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
