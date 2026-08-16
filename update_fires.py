name: Update Fars Fire Data

on:
  workflow_dispatch:

  schedule:
    - cron: "*/30 * * * *"

permissions:
  contents: write

jobs:
  update-fires:
    runs-on: ubuntu-latest

    steps:

      - name: Checkout repository
        uses: actions/checkout@v5

      - name: Setup Python
        uses: actions/setup-python@v6
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Update fire data
        env:
          EARTHDATA_TOKEN: ${{ secrets.EARTHDATA_TOKEN }}
        run: |
          python update_fires.py

      - name: Check output
        run: |
          test -f data/fires.csv
          echo "fires.csv created successfully"
          wc -l data/fires.csv

      - name: Commit updated data
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

          git add data/fires.csv

          if git diff --cached --quiet; then
            echo "No changes."
            exit 0
          fi

          git commit -m "Update Fars fire data"
          git push
