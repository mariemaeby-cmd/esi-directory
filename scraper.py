name: Update ESI Clinical Directory

on:
  workflow_dispatch:
  schedule:
    - cron: "0 0 1 * *"

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

      - name: Run Scraper and Exclude Offices
        run: |
          python scraper.py

      - name: Commit and Push Updated Directory
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git add esi_master.json esi_master.csv
          git diff --quiet && git diff --staged --quiet || (git commit -m "chore(data): sync verified clinical ESI directory [skip ci]" && git push)
