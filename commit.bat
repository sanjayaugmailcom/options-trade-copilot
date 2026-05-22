@echo off
cd /d "C:\Users\asdf\source\repos\Options.worktrees\agents-polygon-options-strategy-testing-ade29e22"
echo Checking repository status...
git status --short
echo.
echo Committing changes...
git add -A
git commit -m "Initial project setup: FastAPI backend + React frontend for options strategy testing" -m "- Backend: FastAPI server with Polygon.io integration for fetching options data- Frontend: React SPA with interactive strategy comparison UI- Strategies: Covered Call, Protective Put, Bull Call Spread, Iron Condor- Features: Real-time pricing, payoff calculations, risk/reward analysis- Setup: Complete with npm and pip dependencies" && (
  echo.
  echo Commit successful!
  git log --oneline -1
) || (
  echo.
  echo Commit failed!
)
