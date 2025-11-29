# Automated Release Process

LogPress uses an automated release script that handles version bumping and triggers CI/CD pipelines.

## Quick Start

To create a new release:

```bash
./scripts/release.sh
```

## What It Does

The release script will:

1. ✅ Show current version
2. ✅ Offer next version options (patch/minor/major)
3. ✅ Update `setup.py` and `pyproject.toml`
4. ✅ Commit version bump
5. ✅ Create git tag (`v1.0.5`, `v1.1.0`, etc.)
6. ✅ Push to GitHub
7. ✅ Trigger automated CI/CD pipeline

## CI/CD Pipeline (Automatic)

When you push a tag, GitHub Actions automatically:

### 1. Test Job
- Runs Python unit tests
- Runs integration tests
- Builds Docker image
- Tests inside Docker container

### 2. Publish Docker (if tests pass)
- Builds multi-arch images (amd64, arm64)
- Pushes to GitHub Container Registry (GHCR)
- Pushes to Docker Hub

### 3. Publish PyPI (if tests pass)
- Extracts version from git tag
- Updates version in source files
- Builds fresh wheel and tarball
- Uploads to PyPI

## Version Numbering

LogPress follows [Semantic Versioning](https://semver.org/):

- **Patch** (1.0.4 → 1.0.5): Bug fixes, minor improvements
- **Minor** (1.0.5 → 1.1.0): New features, backward compatible
- **Major** (1.1.0 → 2.0.0): Breaking changes

## Example Usage

### Creating a Patch Release (Bug Fix)

```bash
$ ./scripts/release.sh

Current version: v1.0.4

Select release type:
  [1] Patch release (bug fixes):     v1.0.5
  [2] Minor release (new features):  v1.1.0
  [3] Major release (breaking):      v2.0.0
  [4] Custom version
  [0] Cancel

Choice: 1

Creating release: v1.0.4 → v1.0.5
```

### Creating a Minor Release (New Feature)

```bash
Choice: 2

Creating release: v1.0.5 → v1.1.0
Release message (default: 'Release v1.1.0'): Add query optimization feature
```

### Custom Version

```bash
Choice: 4
Enter version (e.g., 2.0.0): 1.0.6-beta1
```

## Manual Release (Old Way)

If you prefer manual control:

```bash
# 1. Update version manually
vim setup.py        # Change version="1.0.4" to version="1.0.5"
vim pyproject.toml  # Change version = "1.0.4" to version = "1.0.5"

# 2. Commit and tag
git add setup.py pyproject.toml
git commit -m "Bump version to 1.0.5"
git tag -a v1.0.5 -m "Release v1.0.5"

# 3. Push
git push origin main
git push origin v1.0.5
```

**Note**: With automatic versioning in the workflow, you can skip step 1 and just push the tag. The workflow will update versions automatically from the tag.

## Monitoring Releases

Check pipeline status:
- **GitHub Actions**: https://github.com/adam-bouafia/LogPress/actions
- **PyPI Package**: https://pypi.org/project/LogPress/
- **Docker Hub**: https://hub.docker.com/r/adambouafia/logpress/tags
- **GHCR**: https://github.com/adam-bouafia/LogPress/pkgs/container/logpress

## Troubleshooting

### Pipeline Failed

Check the GitHub Actions logs to see which job failed:
- **Test job failed**: Fix tests, commit, and create a new tag
- **Docker job failed**: Check Docker Hub credentials in GitHub secrets
- **PyPI job failed**: Check PyPI token in GitHub secrets (`PYPI_API_TOKEN`)

### Version Already Exists on PyPI

If you accidentally pushed a tag with an existing version:
```bash
# Delete the tag locally and remotely
git tag -d v1.0.5
git push origin :refs/tags/v1.0.5

# Create a new patch version
./scripts/release.sh
```

### Failed to Push Tag

Ensure you have push permissions and that the tag doesn't already exist:
```bash
# List existing tags
git tag -l

# Delete conflicting tag
git tag -d v1.0.5
git push origin :refs/tags/v1.0.5
```

## GitHub Secrets Required

For automated publishing, ensure these secrets are set in your repository:

- `PYPI_API_TOKEN`: PyPI API token for package uploads
- `DOCKERHUB_USERNAME`: Docker Hub username
- `DOCKERHUB_TOKEN`: Docker Hub access token
- `GHCR_PAT`: GitHub Personal Access Token (or use `GITHUB_TOKEN`)

Set secrets at: https://github.com/adam-bouafia/LogPress/settings/secrets/actions
