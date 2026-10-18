---
description: Cut a release - bump version, update changelog, tag and publish.
---

# Release workflow

1. Ensure the working tree is clean and on the release branch.
2. Determine the next semantic version from the change history.
3. Bump the version in the project's manifest.
4. Update `CHANGELOG.md` (or generate it) with the user-facing changes.
5. Run the full test suite and lint; do not proceed on failure.
6. Commit with a `chore(release): vX.Y.Z` message.
7. Create an annotated tag and push branch + tag.
8. Publish the package/artifact if applicable.

Ask the user before steps 6-8. Report the resulting version and tag.
