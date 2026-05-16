# Branch Protection Setup (Manual Post-Deploy Step)

After the CI/CD workflows are merged to `main`, configure branch protection in GitHub
to enforce the three PR checks as required status checks.

## Steps

1. Go to the repository on GitHub.
2. Navigate to **Settings** → **Branches**.
3. Under **Branch protection rules**, click **Add rule**.
4. Set **Branch name pattern** to: `main`
5. Enable **Require status checks to pass before merging**.
6. In the search box, add each of the following required checks (they appear in the
   list once the workflows have run at least once). GitHub uses the job `name:` field
   as the status check identifier — not the job id — so search for the full display
   names below:
   - `Lint (Black + Ruff)`
   - `Test (pytest + coverage)`
   - `Security (pip-audit)`
7. Enable **Require branches to be up to date before merging**.
8. Click **Save changes**.

## Result

Any PR targeting `main` that fails lint, tests, or security scan will be blocked from
merging until all three checks pass.

## Note

This step cannot be automated without a repository admin token. It is a one-time manual
configuration performed after the first successful workflow run.
