Place small reviewer-friendly model files here to be automatically attached to a GitHub release.

Guidance:

- Only add models you are legally permitted to distribute. Verify the model license before committing.
- Prefer very small test models to keep releases lightweight (e.g., small ggml quantized models).
- Files placed under `models/reviewers/` will be attached to the release artifacts by the CI `release` job.

How to include a reviewer model:

1. Add your model file(s) to `models/reviewers/`.
2. Commit and push to your repository.
3. Trigger the `Build Release` workflow via GitHub Actions (manual `workflow_dispatch`). The release job will attach files in `dist/` and `models/reviewers/`.

If you want me to add a specific model for reviewers, tell me the model name and confirm you have distribution rights and I will add it and update the release notes.