#!/bin/bash

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
BRANCH_REGEX='^((feature|bugfix|refactor|hotfix|release|chore)\/[a-zA-Z0-9\-]+)$'

if ! echo "$CURRENT_BRANCH" | grep -Eq "$BRANCH_REGEX"; then
  echo "Invalid branch name: $CURRENT_BRANCH."
  echo "Branch should have this format <type>/<desc>. Where <type> is one of 'feature', 'bugfix', 'refactor', 'hotfix', 'release', 'chore'."
  echo "Examples:"
  echo "  feature/add-new-login"
  echo "  bugfix/fix-header-alignment"
  exit 1
fi
