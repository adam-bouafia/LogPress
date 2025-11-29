#!/bin/bash
# Automated release script for LogPress
# Creates a new version tag and triggers CI/CD pipeline

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}              ${GREEN}LogPress Release Manager${NC}                        ${BLUE}║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Get current version from setup.py
CURRENT_VERSION=$(grep -oP 'version="\K[0-9.]+' setup.py)
echo -e "${YELLOW}Current version:${NC} v${CURRENT_VERSION}"
echo ""

# Parse current version
IFS='.' read -ra VERSION_PARTS <<< "$CURRENT_VERSION"
MAJOR="${VERSION_PARTS[0]}"
MINOR="${VERSION_PARTS[1]}"
PATCH="${VERSION_PARTS[2]}"

# Calculate next versions
NEXT_PATCH="${MAJOR}.${MINOR}.$((PATCH + 1))"
NEXT_MINOR="${MAJOR}.$((MINOR + 1)).0"
NEXT_MAJOR="$((MAJOR + 1)).0.0"

echo -e "${GREEN}Select release type:${NC}"
echo -e "  ${YELLOW}[1]${NC} Patch release (bug fixes):     v${NEXT_PATCH}"
echo -e "  ${YELLOW}[2]${NC} Minor release (new features):  v${NEXT_MINOR}"
echo -e "  ${YELLOW}[3]${NC} Major release (breaking):      v${NEXT_MAJOR}"
echo -e "  ${YELLOW}[4]${NC} Custom version"
echo -e "  ${YELLOW}[0]${NC} Cancel"
echo ""

read -p "Choice: " choice

case "$choice" in
    1)
        NEW_VERSION="$NEXT_PATCH"
        ;;
    2)
        NEW_VERSION="$NEXT_MINOR"
        ;;
    3)
        NEW_VERSION="$NEXT_MAJOR"
        ;;
    4)
        read -p "Enter version (e.g., 2.0.0): " NEW_VERSION
        ;;
    0)
        echo -e "${YELLOW}Cancelled.${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid choice!${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Creating release:${NC} v${CURRENT_VERSION} → v${NEW_VERSION}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Update version in source files
echo -e "${YELLOW}📝 Updating version in source files...${NC}"
sed -i "s/version=\"${CURRENT_VERSION}\"/version=\"${NEW_VERSION}\"/" setup.py
sed -i "s/version = \"${CURRENT_VERSION}\"/version = \"${NEW_VERSION}\"/" pyproject.toml
echo -e "${GREEN}✓${NC} Updated setup.py and pyproject.toml"

# Commit version bump
echo ""
echo -e "${YELLOW}📦 Committing version bump...${NC}"
git add setup.py pyproject.toml
git commit -m "Bump version to ${NEW_VERSION}"
echo -e "${GREEN}✓${NC} Committed version change"

# Create and push tag
echo ""
echo -e "${YELLOW}🏷️  Creating git tag v${NEW_VERSION}...${NC}"
read -p "Release message (default: 'Release v${NEW_VERSION}'): " RELEASE_MESSAGE
RELEASE_MESSAGE="${RELEASE_MESSAGE:-Release v${NEW_VERSION}}"

git tag -a "v${NEW_VERSION}" -m "${RELEASE_MESSAGE}"
echo -e "${GREEN}✓${NC} Created tag v${NEW_VERSION}"

# Push to remote
echo ""
echo -e "${YELLOW}🚀 Pushing to GitHub...${NC}"
git push origin main
git push origin "v${NEW_VERSION}"
echo -e "${GREEN}✓${NC} Pushed to GitHub"

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Release v${NEW_VERSION} created successfully!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}CI/CD Pipeline Status:${NC}"
echo -e "  Monitor: https://github.com/adam-bouafia/LogPress/actions"
echo ""
echo -e "${YELLOW}Once pipeline completes, packages will be available at:${NC}"
echo -e "  PyPI:       https://pypi.org/project/LogPress/${NEW_VERSION}/"
echo -e "  Docker Hub: https://hub.docker.com/r/adambouafia/logpress/tags"
echo -e "  GHCR:       https://github.com/adam-bouafia/LogPress/pkgs/container/logpress"
echo ""
