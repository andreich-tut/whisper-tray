#!/bin/bash
# Trigger Windows build via GitHub Actions
# Usage: ./trigger-windows-build.sh

set -e

echo "============================================================"
echo "  WhisperTray - Trigger Windows Build"
echo "============================================================"
echo ""

# Check if git remote exists
if ! git remote get-url origin &>/dev/null; then
    echo "❌ Error: No git remote 'origin' found"
    echo "   Push this repo to GitHub first:"
    echo "   1. Create a repo on GitHub"
    echo "   2. git remote add origin <url>"
    echo "   3. git push -u origin main"
    exit 1
fi

# Check if GitHub CLI is installed
if command -v gh &>/dev/null; then
    echo "✓ GitHub CLI found"
    
    # Check authentication
    if gh auth status &>/dev/null; then
        echo "✓ GitHub CLI authenticated"
        echo ""
        echo "Triggering workflow..."
        
        # Push current changes
        git add -A
        git commit -m "trigger: windows build" --allow-empty || true
        git push
        
        # Trigger workflow manually
        echo ""
        echo "Starting GitHub Actions workflow..."
        gh workflow run build-windows.yml
        
        echo ""
        echo "✓ Workflow triggered!"
        echo ""
        echo "Monitor progress:"
        gh run list --workflow=build-windows.yml --limit 3
        echo ""
        echo "Or visit: $(git remote get-url origin | sed 's/git@github.com:/https:\/\/github.com\//' | sed 's/\.git//')/actions"
        
    else
        echo "⚠ GitHub CLI not authenticated"
        echo "  Run: gh auth login"
        echo ""
        echo "Alternative: Just push to trigger automatically"
        echo "  git push"
        echo ""
        echo "Workflow runs on: push to main/master, tags (v*), or manual trigger"
    fi
else
    echo "⚠ GitHub CLI not installed"
    echo ""
    echo "To trigger the build:"
    echo ""
    echo "  Option 1: Install GitHub CLI"
    echo "    sudo apt install gh"
    echo "    gh auth login"
    echo "    ./trigger-windows-build.sh"
    echo ""
    echo "  Option 2: Just push to GitHub"
    echo "    git push"
    echo "    (Workflow auto-triggers on push to main/master)"
    echo ""
    echo "  Option 3: Use GitHub web interface"
    echo "    1. Go to your repo → Actions tab"
    echo "    2. Click 'Build Windows EXE'"
    echo "    3. Click 'Run workflow' → Run workflow"
    echo ""
fi

echo ""
echo "============================================================"
echo "  After build completes:"
echo "  1. Go to Actions → Build Windows EXE → Latest run"
echo "  2. Download 'WhisperTray-Windows' artifact"
echo "  3. Extract and run WhisperTray.exe"
echo "============================================================"
