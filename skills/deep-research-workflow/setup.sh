#!/bin/bash
# deep-research-workflow — First-time setup
# Install dependencies and verify prerequisites

set -e

echo "Setting up deep-research-workflow..."
echo ""

# Check Node.js
if ! command -v node &>/dev/null; then
  echo "ERROR: Node.js not found. Install Node.js 18+ from https://nodejs.org"
  exit 1
fi

NODE_VERSION=$(node --version | sed 's/v//' | cut -d. -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
  echo "ERROR: Node.js 18+ required (found $(node --version))"
  exit 1
fi
echo "Node.js $(node --version) OK"

# Install npm dependencies
echo ""
echo "Installing dependencies..."
npm install

# Install Playwright Chromium
echo ""
echo "Installing Playwright Chromium..."
npx playwright install chromium

# Check Google Chrome
if [ -d "/Applications/Google Chrome.app" ]; then
  echo "Google Chrome found OK"
else
  echo "WARNING: Google Chrome not found at /Applications/Google Chrome.app"
  echo "  Install Chrome from https://www.google.com/chrome/"
  echo "  The script requires your real Chrome profile to reuse Google login."
fi

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Copy the task template: cp templates/tasks-template.json tasks.json"
echo "  2. Edit tasks.json with your research questions"
echo "  3. Create prompt files from each market's research_prompt"
echo "  4. Run: npm run research -- prompt-1.md prompt-2.md"
echo ""
echo "First run: Chrome may ask you to log into Google once."
echo "After that, your login session is preserved in ~/.chrome-debug-profile"
