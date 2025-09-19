# .github/workflows/process_data.yml
name: Process New Product Data
on:
  push:
    paths:
      - 'data/**.csv'

jobs:
  build-and-commit:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install pandas

      - name: Configure Git
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"

      - name: Sync with remote before processing
        run: |
          git fetch origin
          git reset --hard origin/main

      - name: Run data processing script
        run: python process_data.py

      - name: Commit and push with retry logic
        run: |
          # Check if there are any changes to commit
          git add new_master_catalog_DRAFT.csv
          
          if git diff-index --quiet HEAD; then
            echo "No changes to the draft file. Nothing to commit."
            exit 0
          fi
          
          # Retry loop for handling concurrent pushes
          for i in {1..5}; do
            echo "Attempt $i to commit and push..."
            
            # Fetch latest changes and rebase
            git fetch origin
            
            # Check if we can fast-forward
            if git merge-base --is-ancestor HEAD origin/main; then
              echo "Local branch is up to date, proceeding with push..."
            else
              echo "Local branch is behind, rebasing..."
              git rebase origin/main
            fi
            
            # Try to push
            if git push origin main; then
              echo "Successfully pushed changes!"
              exit 0
            else
              echo "Push failed, retrying in 5 seconds..."
              sleep 5
            fi
          done
          
          echo "Failed to push after 5 attempts"
          exit 1

      - name: Create Pull Request on push failure (fallback)
        if: failure()
        uses: peter-evans/create-pull-request@v5
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          commit-message: "Automated: Update master catalog draft"
          title: "Auto-generated: Master catalog update"
          body: |
            This PR was automatically created because the direct push failed due to concurrent changes.
            
            **Changes:**
            - Updated master catalog draft with new product data
            
            **Files changed:**
            - `new_master_catalog_DRAFT.csv`
          branch: auto-update-catalog-${{ github.run_number }}
          delete-branch: true
