# gh-gt — GitHub Issue → Todoist Task

Create a Todoist task from a GitHub issue using GitHub CLI.

## Install

```bash
gh extension install gaejabong/gh-gt
```

## Usage

```bash
# From a repository directory (single or multiple issues)
gh gt 123
gh gt 123 124 125

# Specify repository explicitly
gh gt 45 46 --repo owner/repo

# Options (applied to all issues)
gh gt 123 124 --project-id 2293812345 --section-id 99887766 \
  --priority 3 --due "next Monday 9am" --labels-as-tags --strip-markdown --open
```

On first run, if a Todoist token is not found, you will be prompted to save it to your OS keychain (recommended) or a local config file.

## Auth & Setup

```bash
# Interactive (prompts for token and save target; default keychain)
gh gt auth todoist

# Non-interactive examples
gh gt auth todoist --token <TODOIST_API_TOKEN> --save keychain
gh gt auth todoist --token <TODOIST_API_TOKEN> --save file

# Set a default project (interactive)
gh gt config project

# Clear default project
gh gt config project --clear

# Delete stored token
gh gt auth unset

# Show storage status
gh gt auth show
```

Environment variable `TODOIST_API_TOKEN` is also supported and overrides stored values.

## Notes

- Requires `gh auth login` for GitHub API access.
- Python virtualenv is created in `.venv` automatically. If dependency installation fails (offline), the tool attempts to run with available modules; storing tokens via keychain requires the `keyring` package.
- Todoist SDK is used when available; otherwise REST is used as a fallback.
- If `--project-id` is not provided, the tool uses the saved default project (if any).
