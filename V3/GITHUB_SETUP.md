# SO-101 / SO-ARM100 GitHub Synchronization Guide

This guide explains how to connect your local repository (`D:\projekt\ARM\V2`) containing both **V2** and **V3** to your GitHub account.

---

## Method 1: Automated Script (Recommended)

Once you create an empty repository on GitHub:

```powershell
cd D:\projekt\ARM\V2
python V3/git_setup.py --remote https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
```

This script automatically:
1. Stages all V2 and V3 files cleanly.
2. Commits everything with structured commit messages.
3. Configures the remote `origin`.
4. Pushes the `master` branch to GitHub.

---

## Method 2: Manual Git CLI Commands

If you prefer running Git commands manually:

```powershell
cd D:\projekt\ARM\V2

# 1. Stage all changes
git add .

# 2. Commit the changes
git commit -m "feat(v3): Production-ready architecture, futuristic 3D Web Studio, dual-arm teleop & simulation"

# 3. Add your GitHub remote repository
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# 4. Push to GitHub
git branch -M master
git push -u origin master
```

---

## Method 3: GitHub CLI (`gh`)

If you have GitHub CLI installed:

```powershell
# 1. Login to GitHub in your browser
gh auth login

# 2. Create the remote repo and push in one step
cd D:\projekt\ARM\V2
gh repo create SO-101-Studio --public --source=. --remote=origin --push
```
