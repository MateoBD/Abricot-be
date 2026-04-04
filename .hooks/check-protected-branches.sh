#!/bin/bash

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
PROTECTED_BRANCHES="master main dev staging"

case " $PROTECTED_BRANCHES " in
  *" $CURRENT_BRANCH "*)
    echo >&2 "You can't commit directly to '$CURRENT_BRANCH' branch. Please create a new branch and open a pull request."
    exit 1
    ;;
esac
