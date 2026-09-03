name: Update ESI Clinical Directory

on:
  workflow_dispatch: # Allows manual trigger from the "Actions" tab
  schedule:
    - cron: "0 0 1 * *" # Runs automatically on the 1st of every month

permissions:
  contents: write

jobs:
  run-scraper:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests

      - name: Run ESI Scraper & Filter
        run: |
          python scraper.py

      - name: Commit and Push Updated Dataset
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git add esi_master.json
          git diff --quiet && git diff --staged --quiet || (git commit -m "chore(data): auto-update verified ESI clinical directory" && git push)
