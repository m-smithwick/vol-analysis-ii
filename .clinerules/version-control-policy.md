# Version Control Policy

This project uses git for version control. The following policy defines AI assistant responsibilities regarding git operations.

---

## 🚨 Core Principle

**THE USER HANDLES ALL GIT OPERATIONS**

The AI assistant does NOT execute git commands. The user maintains full control over version control.

---

## ✅ AI Responsibilities

### What the AI SHOULD Do:

1. **Make Code Changes**
   - Modify files as requested
   - Create new files
   - Delete or rename files
   - Refactor code

2. **Test Changes**
   - Run tests to verify functionality
   - Execute commands to validate changes
   - Check for syntax errors

3. **Present Completed Work**
   - Use `attempt_completion` to summarize changes
   - List all files modified
   - Explain what was done
   - Provide context for the changes

4. **Inform About Git State**
   - Can run `git status` to show current state
   - Can run `git diff` to show pending changes
   - Can run `git log` to show history
   - But ONLY for informational purposes, never to commit/push

---

## ❌ AI Restrictions

### What the AI MUST NOT Do:

The AI is **STRICTLY FORBIDDEN** from executing these commands:

```bash
git add
git commit
git push
git pull
git merge
git rebase
git cherry-pick
git reset
git revert
git stash
git tag
```

### Why This Policy Exists:

1. **User Control**: Version control is a critical decision point
2. **Review Process**: User needs to review changes before committing
3. **Commit Messages**: User writes appropriate commit messages
4. **Branch Management**: User decides when to commit/push/merge
5. **Undo Prevention**: Avoids accidental commits that are hard to undo

---

## 📋 Standard Workflow

### Correct Pattern:

```
1. User requests feature/fix
2. AI makes code changes
3. AI tests changes
4. AI presents work via attempt_completion
   ↓
5. User reviews changes
6. User decides to commit (or request modifications)
7. User runs: git add, git commit, git push
```

### What Happens When Work is Complete:

```xml
<attempt_completion>
<result>
I've completed the requested changes:

Files Modified:
- file1.py: Added new feature X
- file2.py: Fixed bug Y
- README.md: Updated documentation

Changes are ready for review. When satisfied, you can commit with:
  git add file1.py file2.py README.md
  git commit -m "Your commit message"
  git push origin branch-name
</result>
</attempt_completion>
```

---

## 🔧 Exception Handling

### If User Says "commit this"

**AI Response:**
```
I don't execute git commands per the version control policy. 

To commit these changes:
  git add <files>
  git commit -m "description"
  git push origin <branch>
```

### If AI Starts to Use Git in Act Mode

**AI MUST:**
1. STOP before executing git command
2. Use `attempt_completion` instead
3. Let user handle git operations

### Checking Git State (Allowed)

These READ-ONLY commands are OK for informational purposes:
- `git status` - show current state
- `git log` - show history
- `git diff` - show changes
- `git branch` - list branches

But the AI should NOT act on this information by committing/pushing.

---

## 💡 Benefits of This Policy

1. **Transparency**: User always knows what's being committed
2. **Control**: User can modify changes before committing
3. **Meaningful Commits**: User writes descriptive commit messages
4. **Safety**: Prevents accidental commits to wrong branch
5. **Review**: User reviews AI changes before they enter version control

---

## 🎯 Examples

### ✅ CORRECT - AI Behavior

```
User: "Add --ticker-files argument to populate_cache_bulk.py"

AI Actions:
1. Modifies populate_cache_bulk.py
2. Tests with --help to verify argument works
3. Uses attempt_completion to present changes

<attempt_completion>
<result>
Added --ticker-files argument to populate_cache_bulk.py:
- Modified collect_all_tickers() to accept file list
- Added argparse argument for --ticker-files
- Updated examples in help text
- Default changed to stocks.txt

Changes ready for review and commit.
</result>
</attempt_completion>
```

### ❌ INCORRECT - AI Behavior

```
User: "Add --ticker-files argument to populate_cache_bulk.py"

AI Actions:
1. Modifies populate_cache_bulk.py
2. Tests with --help
3. Runs: git add populate_cache_bulk.py
4. Runs: git commit -m "Add ticker-files argument"
5. Runs: git push origin branch-name

⚠️ VIOLATION: AI should NOT execute git commands
```

---

## 📝 Summary

| Operation | AI Action |
|-----------|-----------|
| Code changes | ✅ AI does this |
| Testing | ✅ AI does this |
| Presenting work | ✅ AI does this via attempt_completion |
| Git status (info only) | ✅ AI can check this |
| Git add/commit/push | ❌ USER does this |
| Writing commit messages | ❌ USER does this |
| Branch management | ❌ USER does this |

---

## 🔒 Enforcement

This policy is MANDATORY for all AI operations in this repository.

**No exceptions. User controls version control.**
