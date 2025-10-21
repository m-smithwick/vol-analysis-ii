# Git Workflow: Local to GitHub to Multi-Computer Collaboration

This document provides a concise command list for the complete git workflow, from initializing a local project to collaborating across multiple computers via GitHub.

## Initial Local Setup & First GitHub Push

### 1. Initialize Local Repository
```bash
# Initialize git repository in your project folder
git init
```

### 2. Stage and Commit Your Files
```bash
# Add all files to staging area
git add .

# Create your first commit
git commit -m "Initial commit"
```

### 3. Set Up Main Branch and Remote
```bash
# Ensure you're on the main branch (modern Git standard)
git branch -M main

# Add GitHub remote (replace USERNAME/REPO-NAME with your actual details)
git remote add origin https://github.com/USERNAME/REPO-NAME.git

# Push to GitHub for the first time and set upstream tracking
git push -u origin main
```

## Working from Another Computer

### 4. Clone the Repository
```bash
# Clone your repository to the new computer
git clone https://github.com/USERNAME/REPO-NAME.git
cd REPO-NAME
```

### 5. Make Changes and Push
```bash
# After making your changes, stage them
git add .

# Commit with a descriptive message
git commit -m "Descriptive commit message about what you changed"

# Push changes back to GitHub
git push origin main
```

## Continuing Work on Original Computer

### 6. Stay Synchronized
```bash
# ALWAYS pull latest changes before starting new work
git pull origin main

# Continue normal workflow: edit, add, commit, push
git add .
git commit -m "Another meaningful update"
git push origin main
```

## Daily Workflow Pattern

For ongoing development, follow this pattern on any computer:

```bash
# 1. Start by getting latest changes
git pull origin main

# 2. Make your changes to files
# (your coding work here)

# 3. Stage changes
git add .

# 4. Commit changes
git commit -m "Clear description of what you did"

# 5. Push to GitHub
git push origin main
```

## Important Notes

- **Create GitHub Repository First**: You need to create the repository on GitHub (via web interface or GitHub CLI) before step 5
- **Replace Placeholders**: Change `USERNAME/REPO-NAME` to your actual GitHub username and repository name
- **Always Pull First**: Run `git pull origin main` before starting work to avoid merge conflicts
- **Descriptive Commits**: Use meaningful commit messages to track your progress and changes
- **Stay Synchronized**: The key to multi-computer collaboration is keeping repositories in sync with frequent pulls and pushes

## Common Commands Reference

```bash
# Check repository status
git status

# View commit history
git log --oneline

# Check which remote repositories are configured
git remote -v

# See differences in your working directory
git diff
```

## Troubleshooting

- **Merge Conflicts**: If you get merge conflicts, Git will mark the conflicting areas in your files. Edit them manually, then `git add .` and `git commit`
- **Authentication**: You may need to set up SSH keys or personal access tokens for GitHub authentication
- **Branch Protection**: Some repositories may require pull requests instead of direct pushes to main branch

This workflow ensures your code stays synchronized across all your computers while maintaining a complete version history on GitHub.
