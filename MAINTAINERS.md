# Maintainers

When implementation is deemed to be ready for a stable release, ensure the
following steps are performed:

- Update `CHANGELOG.md`, replacing the development title with release version
  and date.
- Ensure the version value in the implementation has been updated.

A release can be made with the following commands.

----

Perform a local clean build:

```shell
python -m build
```

Verify packages can be published:

```shell
twine check dist/*
```

Create a local release tag and verify the signed tag:

```shell
git tag -s -a v<version> <hash> -m "sphinx-confluence-relay <version>"
git verify-tag <tag>
```

Push the tag to GitHub to start the release workflow:

```shell
git push origin <tag>
```

After the release workflow creates a build, sanity check its logs to ensure
the generated artifact seems sane. If the package appears to be in a good
state, authorize the workflow's environment to complete publishing.

If no issues, complete the automatically created draft release notes in
GitHub to complete the release.
