# FarmFit Git cheat sheet (beginners)

This project lives at **https://github.com/keydahknow/FarmFit**. Git saves **snapshots** of the code so everyone can work together without overwriting each other’s work.

**Shared rule:** The `main` branch should always run and be safe to deploy. Do your experiments on your own **branch**, then merge when ready.

---

## Words you will see

| Term | Meaning in plain English |
|------|---------------------------|
| **Repository (repo)** | The project folder + its full history on GitHub |
| **Clone** | Download the repo to your computer |
| **Branch** | A separate line of work (like a copy of the timeline) |
| `main` | The default branch everyone shares |
| **Commit** | A saved snapshot with a message describing what you changed |
| **Push** | Send your commits to GitHub |
| **Pull** | Download other people’s commits from GitHub |
| **Merge** | Combine one branch into another (often via a Pull Request on GitHub) |

---

## One-time setup (each programmer, once)

1. Install **Git**: https://git-scm.com/download/win  
2. Install **GitHub CLI** (optional but helpful): https://cli.github.com/  
3. Sign in to GitHub and clone the project:

```powershell
cd C:\Users\YOUR_NAME\Coding_Projects\github\keydahknow
git clone https://github.com/keydahknow/FarmFit.git
cd FarmFit
```

4. Tell Git your name (use your real name or GitHub username):

```powershell
git config user.name "Your Name"
git config user.email "you@example.com"
```

5. **Secrets:** Create `.streamlit/secrets.toml` locally for your API keys. It is in `.gitignore` and must **never** be committed. Ask a teammate how to get the values; do not paste keys in chat or GitHub.

6. Python environment (typical for this app):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

---

## The workflow we use (read this first)

```text
START OF DAY / BEFORE YOU CODE
    → pull latest main
    → create or switch to YOUR branch

WHILE YOU CODE
    → save files in your editor
    → commit small, logical snapshots

WHEN A FEATURE IS DONE
    → push your branch
    → open a Pull Request (PR) on GitHub into main
    → someone reviews (or you self-review), then merge

AFTER MERGE
    → switch back to main, pull, delete old branch locally
```

### When to use a branch

| Situation | What to do |
|-----------|------------|
| Any real change (bug fix, new screen, data update) | New branch from `main` |
| Quick typo on `main` alone | Still use a branch (good habit) |
| Experiment that might be thrown away | Branch named `experiment/...` |
| You are not sure it works yet | Stay on your branch; do not push broken code to `main` |

**Branch naming (pick one style and stick to it):**

- `feature/water-calculator`
- `fix/map-crash`
- `docs/readme-update`

```powershell
git checkout main
git pull origin main
git checkout -b feature/short-description
```

---

## Every time you sit down to code

Run this **before** you edit files:

```powershell
git checkout main
git pull origin main
git checkout feature/your-branch-name
git pull origin main
```

The last line updates your branch with anything new on `main` (do this often if others are merging often).

If you do not have a branch yet, create one (see above) instead of working directly on `main`.

---

## When you finish a chunk of work (commit)

1. See what changed:

```powershell
git status
```

2. Review the actual edits (optional but smart):

```powershell
git diff
```

3. Stage files (everything you intend to include in this commit):

```powershell
git add app.py
# or stage all safe changes:
git add -A
```

**Before `git add -A`:** make sure `git status` does not list `.streamlit/secrets.toml`, `.env`, or other secrets.

4. Commit with a clear message:

```powershell
git commit -m "Add crop filter to map page"
```

**Good commit messages (short, past tense or imperative):**

- `Fix crash when crop list is empty`
- `Update intercropping CSV for 2025 data`
- `Wire Gemini prompt to sidebar`

**Bad:** `stuff`, `fixed it`, `asdf`, `WIP` (unless it is truly temporary on a private branch)

5. Push your branch to GitHub:

```powershell
git push -u origin feature/short-description
```

(After the first push, you can use `git push` only.)

6. On GitHub: **Pull requests → New pull request** → base: `main`, compare: your branch → create PR → merge when ready.

---

## Pull (get teammates’ changes)

| When | Command |
|------|---------|
| Start of day on `main` | `git checkout main` then `git pull origin main` |
| Update your feature branch | On your branch: `git pull origin main` |
| After someone merged your PR | `git checkout main` then `git pull origin main` |

---

## Quick command reference

```powershell
# Where am I? What branch? What's changed?
git status

# Switch branch
git checkout main
git checkout feature/my-branch

# New branch from current HEAD
git checkout -b feature/new-thing

# See recent history
git log --oneline -10

# Undo unstaged edits in one file (careful)
git restore app.py

# Discard ALL local uncommitted changes (very careful)
git restore .

# See remote URL
git remote -v
```

---

## Pull Requests (how we share code safely)

1. Push your branch.
2. On GitHub, open a PR into `main`.
3. Describe **what** you changed and **how to test** (e.g. “Run streamlit, go to Planner tab, pick two crops”).
4. Another teammate (or you) reads the diff and merges.
5. Locally after merge:

```powershell
git checkout main
git pull origin main
git branch -d feature/short-description
```

---

## Merge conflicts (when Git says both of you edited the same lines)

1. Do not panic. Git marks conflicted files with `<<<<<<<`, `=======`, `>>>>>>>`.
2. Open the file, choose the correct code (or combine both), delete the marker lines.
3. Then:

```powershell
git add path/to/fixed-file.py
git commit -m "Resolve merge conflict in app.py"
git push
```

If you are stuck, ask in chat **before** force-pushing or deleting branches.

---

## Never do these on a shared repo

| Do not | Why |
|--------|-----|
| Commit `.streamlit/secrets.toml`, `.env`, passwords | Keys leak forever in Git history |
| `git push --force` to `main` | Can erase teammates’ work |
| Work for days only on your laptop without pushing | You might lose work; others cannot help |
| Merge broken code to `main` | Everyone’s copy breaks |

---

## If something went wrong

| Problem | Try this |
|---------|----------|
| “Your branch is behind” | `git pull origin main` (on your branch) |
| Committed wrong files, not pushed yet | `git reset --soft HEAD~1` (undo commit, keep files) |
| Pushed secrets by accident | Tell the team immediately; rotate the API key; ask for help cleaning history |
| Detached HEAD / weird state | `git checkout main` |
| Clone is messy | Rename folder, `git clone` again, copy only your uncommitted files over |

---

## Team habits that keep beginners sane

1. **Pull before you code.**
2. **One branch per task.**
3. **Small commits** with clear messages.
4. **One PR per feature or fix** when possible.
5. **Test** `streamlit run app.py` before you ask to merge.
6. **Talk** if two people might edit the same file (`app.py` is large—coordinate).

---

## FarmFit-specific reminders

- Data files: `crops.csv`, `intercropping.csv`, `crop_water.csv`, `farmfit.db` — coordinate before two people edit the same CSV at once.
- Large changes to `app.py` are easier to review in a PR with a short summary in the description.

---

## Cheat sheet one-liner (print this)

```text
pull main → branch → code → status → add → commit → push → PR → merge → pull main
```

Questions about Git for this project? Open a GitHub Discussion or ask in your team chat—include the exact error message and what command you ran.
