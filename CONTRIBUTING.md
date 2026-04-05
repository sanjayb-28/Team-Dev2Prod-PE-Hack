# Contributing

Thanks for contributing to Dev2Prod.

This repository is centered on a live platform, not only a sample app. Good contributions keep the product story, runtime behavior, and documentation aligned.

## Before You Start

- Read [README.md](README.md) for the product and repo overview.
- Read [AGENTS.md](AGENTS.md) for repo-specific operating guidance.
- Check the relevant docs in [docs/](docs) before changing behavior that is already documented.

## Development Flow

1. Create a branch from the current working branch.
2. Make focused changes with a clear scope.
3. Validate the affected surfaces locally.
4. Update docs when behavior, architecture, or operator flow changes.
5. Open a pull request with a concise description of what changed and how it was verified.

## Validation Expectations

At minimum:

- backend changes: run the relevant `uv run pytest ...` targets
- client changes: run `cd client && npm run build` and `cd client && npm run lint`
- workflow or infra changes: read the affected manifests and workflow files carefully
- docs changes: verify links, embedded assets, and references

If a change spans client and backend behavior, validate both.

## What Good Contributions Look Like

Good changes usually do one or more of the following:

- make reliability or scalability behavior clearer
- improve the control plane or cluster workflow
- tighten the operator-facing client
- improve documentation and evidence quality
- harden tests around real edge cases

## Scope Guidance

Please keep these project choices in mind:

- the reference workload is intentionally simple
- the platform direction is API-first and control-plane-first
- operator clarity matters more than adding more raw infrastructure detail
- docs should stay truthful to the current system, not the intended future state

## Pull Request Notes

When opening a PR, include:

- a short summary of the change
- the files or surfaces affected
- the validation you ran
- any follow-up work or known limits

## Questions

If something is unclear, open a GitHub issue before making a large change.
