# Windows setup and collaboration

Install Git from https://git-scm.com/install/windows and Python from https://www.python.org/downloads/windows/ .
Reopen PowerShell; check `git --version` and `py --version`.

## Clone, install, run

```powershell
git clone https://github.com/Hozier123/sdc-2026-team-project.git
cd sdc-2026-team-project
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item -LiteralPath .env.example -Destination .env
$env:PROJECT_NAME = "SDC Team Project"
.\.venv\Scripts\python.exe src/main.py
.\.venv\Scripts\python.exe -m unittest discover tests
```

Expect a welcome message, sample statistics and three passing tests. This starter has no web interface.
Each teammate creates their own ignored .venv and .env.
The program does not automatically load .env; use environment variables or implement explicit loading later.
No environment activation or PowerShell execution-policy change is needed.

## Collaborate

The repository owner invites registered teammates in Settings -> Collaborators / Access.
Use their correct GitHub usernames. Public visibility does not grant push permission.

Set your own local commit identity:
```powershell
git config user.name "YOUR_NAME"
git config user.email "YOUR_GITHUB_EMAIL_OR_NOREPLY_EMAIL"
```

Preserve existing edits before starting a new task:
```powershell
git switch main
git pull --ff-only
git switch -c feature/your-task-name
```

Review and commit real progress:
```powershell
git status
git add .
git diff --cached --stat
git commit -m "Describe the actual change"
git push -u origin feature/your-task-name
```

Open a Pull Request for teammate review. Use one branch per task and truthful commit history.
Do not force-push over teammates' changes.

## Replit

Import via https://replit.com/import .
Install with `python -m pip install -r requirements.txt`.
Set startup to `python src/main.py`.
Use Secrets for environment variables; never commit keys.
Use Git tools to sync changes: GitHub and Replit edits are not always automatically synchronized.
Document real web startup/deployment instructions after implementing a web prototype.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| git / py unavailable | Check installation/PATH; reopen terminal. |
| Activation blocked | Use .venv's Python directly, as above. |
| Push denied | Check authenticated account and repository write access. |
| .env changes ineffective | Starter has no automatic dotenv loading. |
| No Replit web preview | Starter is a CLI; build a web server/UI. |

