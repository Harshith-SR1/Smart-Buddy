Release process for Smart Buddy

This project includes a GitHub Actions `release` job that builds sdist/wheel and drafts a GitHub Release with the built artifacts.

Local release (build only)

1. Ensure your venv is active:

```powershell
& ".\.venv\Scripts\Activate.ps1"
```

2. Install build tools (once):

```powershell
pip install --upgrade pip build twine
```

3. Build sdist and wheel:

```powershell
python -m build
```

The distribution files will be placed in `dist/`.

Create a GitHub Release via Actions

- The repository has a `release` job defined in `.github/workflows/ci.yml` that runs when manually triggered (`workflow_dispatch`). It builds `dist/*` and uses `softprops/action-gh-release` to create a published release and attach artifacts. The job also now includes any files under `models/reviewers/` when present.

Notes & suggestions

- If you want release artifacts to include a prepackaged small model, provide the model file and ensure you have rights to distribute it. I can add a `models/reviewers/` directory with the small test model and update the CI job to attach those files to the release.
- The release job is configured to publish releases (`draft: false`); if you prefer draft releases or prereleases, this can be adjusted.

If you'd like, I can:
- Add a small test model to `models/reviewers/` and include it in release artifacts (you must confirm which model and that licenses allow distribution). Files placed into `models/reviewers/` are automatically attached to releases by the CI job.
- Adjust the release job to auto-publish or to upload to a separate hosting provider.
