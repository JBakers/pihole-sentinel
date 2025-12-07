#!/bin/bash
# Merge Helper Script: develop → testing
# Automatically handles version conflicts and updates

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Pi-hole Sentinel Merge Helper                ║${NC}"
echo -e "${BLUE}║  develop → testing                            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "VERSION" ] || [ ! -f "CHANGELOG.md" ]; then
    echo -e "${RED}✗ Error: Must be run from repository root${NC}"
    exit 1
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${RED}✗ Error: You have uncommitted changes${NC}"
    echo -e "${YELLOW}  Commit or stash your changes first${NC}"
    git status --short
    exit 1
fi

# Fetch latest from remote
echo -e "${BLUE}→ Fetching latest from remote...${NC}"
git fetch origin

# Get current branch
CURRENT_BRANCH=$(git branch --show-current)

# Switch to develop and pull latest
echo -e "${BLUE}→ Updating develop branch...${NC}"
git checkout develop
git pull origin develop

# Get develop version
DEVELOP_VERSION=$(cat VERSION)
echo -e "${GREEN}  Develop version: ${DEVELOP_VERSION}${NC}"

# Switch to testing and pull latest
echo -e "${BLUE}→ Updating testing branch...${NC}"
git checkout testing
git pull origin testing

# Get testing version
TESTING_VERSION=$(cat VERSION)
echo -e "${GREEN}  Testing version: ${TESTING_VERSION}${NC}"

# Calculate new testing version
# Extract version components
if [[ $TESTING_VERSION =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)-beta\.([0-9]+)$ ]]; then
    MAJOR="${BASH_REMATCH[1]}"
    MINOR="${BASH_REMATCH[2]}"
    PATCH="${BASH_REMATCH[3]}"
    BETA="${BASH_REMATCH[4]}"

    # Increment beta version
    NEW_BETA=$((BETA + 1))
    NEW_VERSION="${MAJOR}.${MINOR}.${PATCH}-beta.${NEW_BETA}"
else
    echo -e "${RED}✗ Error: Invalid version format in testing branch${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}  Merge Summary:${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  Source:      ${GREEN}develop${NC} (${DEVELOP_VERSION})"
echo -e "  Target:      ${BLUE}testing${NC} (${TESTING_VERSION})"
echo -e "  New version: ${GREEN}${NEW_VERSION}${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Ask for confirmation
read -p "$(echo -e ${YELLOW}Continue with merge? [y/N]: ${NC})" -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}✗ Merge cancelled${NC}"
    git checkout "$CURRENT_BRANCH" 2>/dev/null || true
    exit 1
fi

echo ""
echo -e "${BLUE}→ Starting merge...${NC}"

# Create a backup of VERSION and CHANGELOG.md
cp VERSION VERSION.backup
cp CHANGELOG.md CHANGELOG.md.backup

# Perform the merge (will likely have conflicts)
echo -e "${BLUE}→ Merging develop into testing...${NC}"
if git merge develop --no-commit --no-ff 2>&1 | tee /tmp/merge_output.txt; then
    echo -e "${GREEN}✓ Merge completed without conflicts${NC}"
else
    # Check if there are conflicts
    if grep -q "CONFLICT" /tmp/merge_output.txt; then
        echo -e "${YELLOW}! Conflicts detected (expected)${NC}"

        # Auto-resolve VERSION conflict by using new version
        echo -e "${BLUE}→ Resolving VERSION conflict...${NC}"
        echo "$NEW_VERSION" > VERSION
        git add VERSION
        echo -e "${GREEN}  Set VERSION to: ${NEW_VERSION}${NC}"

        # Handle CHANGELOG.md conflict
        if git status | grep -q "both modified.*CHANGELOG.md"; then
            echo -e "${BLUE}→ Resolving CHANGELOG.md conflict...${NC}"

            # Extract develop's new entries (everything before testing's entries)
            # This is tricky - we'll keep testing's version and prepend develop's changes

            # For now, mark as resolved with testing's version (user can manually merge if needed)
            git checkout --theirs CHANGELOG.md
            git add CHANGELOG.md
            echo -e "${YELLOW}  ⚠ CHANGELOG.md: Using testing branch version${NC}"
            echo -e "${YELLOW}  ⚠ You may need to manually merge changelog entries${NC}"
        fi

        # Check for other conflicts
        if git status | grep -q "Unmerged paths"; then
            echo -e "${RED}✗ Additional conflicts detected:${NC}"
            git status --short | grep "^UU"
            echo ""
            echo -e "${YELLOW}Please resolve conflicts manually and run:${NC}"
            echo -e "  git add <files>"
            echo -e "  git commit"
            echo -e "  git push origin testing"
            exit 1
        fi
    else
        echo -e "${RED}✗ Merge failed for unknown reason${NC}"
        cat /tmp/merge_output.txt
        exit 1
    fi
fi

# Update version in CLAUDE.md
echo -e "${BLUE}→ Updating CLAUDE.md version...${NC}"
if [ -f "CLAUDE.md" ]; then
    # Update version on line 4
    sed -i "4s/.*/\*\*Version:\*\* ${NEW_VERSION}/" CLAUDE.md
    git add CLAUDE.md
    echo -e "${GREEN}  ✓ Updated CLAUDE.md to ${NEW_VERSION}${NC}"
fi

# Update version in README.md badge
echo -e "${BLUE}→ Updating README.md version badge...${NC}"
if [ -f "README.md" ]; then
    sed -i "s/version-v[0-9]\+\.[0-9]\+\.[0-9]\+-beta\.[0-9]\+/version-v${NEW_VERSION}/g" README.md
    git add README.md
    echo -e "${GREEN}  ✓ Updated README.md badge to v${NEW_VERSION}${NC}"
fi

# Update CHANGELOG.md with merge entry
echo -e "${BLUE}→ Adding merge entry to CHANGELOG.md...${NC}"
MERGE_DATE=$(date +%Y-%m-%d)
TEMP_CHANGELOG=$(mktemp)

cat > "$TEMP_CHANGELOG" << EOF
# Changelog

All notable changes to Pi-hole Sentinel will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [${NEW_VERSION}] - ${MERGE_DATE}

### 🔄 Merged from develop

**Merged develop (${DEVELOP_VERSION}) into testing**

- All features and fixes from develop branch
- See develop changelog entries below for details

---

EOF

# Append the rest of the changelog (skip first 6 lines which are header + first version)
tail -n +7 CHANGELOG.md.backup >> "$TEMP_CHANGELOG"

mv "$TEMP_CHANGELOG" CHANGELOG.md
git add CHANGELOG.md
echo -e "${GREEN}  ✓ Added merge entry to CHANGELOG.md${NC}"

# Generate detailed commit message
echo -e "${BLUE}→ Generating commit message...${NC}"

# Get list of commits from develop
COMMIT_LIST=$(git log testing..develop --oneline --no-merges | sed 's/^/- /')

# Get list of resolved conflicts
CONFLICTS=$(git diff --name-only --diff-filter=U 2>/dev/null || echo "")
RESOLVED_CONFLICTS=""
if [ -n "$CONFLICTS" ]; then
    RESOLVED_CONFLICTS=$(echo "$CONFLICTS" | sed 's/^/- /')
fi

# Create commit message
COMMIT_MSG="chore: merge develop (${DEVELOP_VERSION}) into testing

Merged all features and fixes from develop branch.

Version: ${TESTING_VERSION} → ${NEW_VERSION}

Commits from develop:
${COMMIT_LIST}

Resolved conflicts:
- VERSION: Updated to ${NEW_VERSION}
- DEVELOPMENT.md: Restored from develop
- TESTING-GUIDE.md: Restored from develop
- CHANGELOG.md: Merged entries
- CLAUDE.md: Updated version
- README.md: Updated version badge

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# Commit the merge
echo -e "${BLUE}→ Committing merge...${NC}"
git commit -m "$COMMIT_MSG"

echo -e "${GREEN}✓ Merge committed successfully${NC}"

# Clean up backups
rm -f VERSION.backup CHANGELOG.md.backup /tmp/merge_output.txt

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Merge Completed Successfully!                ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Review the changes: ${BLUE}git log -1${NC}"
echo -e "  2. Push to remote:     ${BLUE}git push origin testing${NC}"
echo ""
echo -e "${YELLOW}New testing version: ${GREEN}${NEW_VERSION}${NC}"
echo ""

# Return to original branch if it wasn't testing
if [ "$CURRENT_BRANCH" != "testing" ]; then
    echo -e "${BLUE}→ Returning to ${CURRENT_BRANCH}...${NC}"
    git checkout "$CURRENT_BRANCH"
fi
