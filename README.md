# SDC Hackathon 2026 - Team Project Starter

This repository starts from the official SDC GitHub submission template. It is a command-line scaffold, **not a finished competition product**. Replace every TODO before submitting.

## Team information

| Field | Value |
| --- | --- |
| Team name | TODO: registered team name |
| Team domain | Domain 2 - Orbyte Smart SME Challenge (provided brief; confirm assignment) |
| SDG track | SDG 8, targets 8.2 and 8.3; confirm against the final solution |
| Project name | TODO |
| Team leader | TODO: registered leader |
| University | TODO |
| Team members | 5; confirm registration |
| Repository maintainer | [Hozier123](https://github.com/Hozier123) |

## Necessary links

| Resource | Link / status |
| --- | --- |
| GitHub | https://github.com/Hozier123/sdc-2026-team-project |
| Live demo / accessible build | TODO: actual working prototype |
| Pitch video | TODO: 5-7 minute YouTube pitch with prototype demonstration |
| Slide deck | TODO: accessible link |
| Replit project / deployment | TODO: actual team links |
| RunPod endpoint | TODO: actual endpoint, if used; no keys |
| Official submission | [SDC website](https://sdchack.my/) - use the Submit page |

## Problem, solution and scope

- Problem: TODO - choose one recurring operational burden for Malaysian micro/small businesses.
- Solution: TODO - describe the product and measurable benefit.
- Core journey: business trigger -> connected data -> rules/AI decision -> human approval -> outcome and activity log.
- Domain 2: use team-created synthetic business data; no live Orbyte access is required. Permissions and roles may be simulated. Do not process real payments or statutory filings.
- Current implementation: sample welcome message and statistics only. No web UI, business automation or actual model integration exists yet.

## Overall project structure

```text
.
|-- README.md
|-- LICENSE                       # Apache License 2.0
|-- requirements.txt
|-- .env.example                  # Names/placeholders, never real keys
|-- .gitignore
|-- .replit
|-- src/
|   |-- main.py                   # Replace sample application
|   `-- utils.py
|-- runpod/
|   `-- handler.py                # Echo example, not a deployed model
|-- tests/
|   `-- test_utils.py
|-- docs/
|   |-- setup-windows.md
|   `-- competition-checklist.md
`-- submission/
    |-- README.md
    |-- REPLIT PROOF OF USE.pdf    # EXAMPLE ONLY: replace
    |-- RUNPOD PROOF OF USE.pdf    # EXAMPLE ONLY: replace
    `-- Submission Template SDC Hackathon.pdf  # Blank form
```

Update this tree to match the real project before submission.

## How to run the project

The starter uses Python 3.10 or later; record the team's chosen version before submitting. No API keys or GPU are needed for the sample. Record model/platform requirements when actually implemented.

### Windows PowerShell

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

Expected output:

```text
Welcome to SDC Team Project!
Result: {'count': 5, 'min': 3, 'max': 21, 'average': 10.4}
```

Current code uses `os.getenv` and does **not** automatically load `.env`. The environment variable above sets the sample project name. Never commit real keys. The example exits after printing; it does not run a website. The starter has three tests.

### macOS / Linux

```bash
git clone https://github.com/Hozier123/sdc-2026-team-project.git
cd sdc-2026-team-project
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
PROJECT_NAME="SDC Team Project" .venv/bin/python src/main.py
.venv/bin/python -m unittest discover tests
```

### Replit

1. Import this repository at https://replit.com/import .
2. Install dependencies: `python -m pip install -r requirements.txt`.
3. Set the run command to `python src/main.py`.
4. Add `PROJECT_NAME` in Secrets. Add real RunPod secrets only after implementing the integration.
5. Run. No web preview is expected until a web server/UI is built.

See [Windows setup and collaboration](docs/setup-windows.md). Replace these commands with the final prototype's real instructions and test from a fresh clone.

## How we used Replit

**Status: TODO - team usage has not been verified in this starter.**

Before submission, describe the actual development/testing/hosting work, modules running on Replit, project/deployment URLs, startup steps, and the team's own proof. Include proof in the technical/tools declaration.

[Replit proof](submission/REPLIT%20PROOF%20OF%20USE.pdf) is currently **EXAMPLE ONLY** and must be replaced. Replit is required by the Participant Handbook.

## How we used RunPod

**Status: TODO - not deployed or integrated.** Installing the SDK is not evidence of platform use; the bundled handler merely echoes input.

If used, document:
- GPU workload, model/version and why a GPU is needed.
- Pod/Serverless setup and connection to the application.
- Environment variable names `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID`, never secret values.
- Actual dashboard evidence: Pod ID (or Serverless endpoint URL), GPU type, runtime and team account, as applicable.

[RunPod proof](submission/RUNPOD%20PROOF%20OF%20USE.pdf) is currently **EXAMPLE ONLY** and must be replaced. The handbook requires GPU work to use RunPod; the template labels this section Required. If no GPU is used, retain an honest non-use explanation and clarify evidence requirements with organizers.

## Submission and public visibility

A public starter repository is not a complete competition entry.

- [ ] Implement real source code and a functional prototype.
- [ ] Fill team name, assigned domain, SDG, project name and real links.
- [ ] Update run instructions, project structure and both platform-use sections.
- [ ] Complete the official proposal and technical/tools declaration.
- [ ] Replace example proof PDFs with team evidence.
- [ ] Add slides and the 5-7 minute YouTube pitch/demo.
- [ ] Retain Apache 2.0 LICENSE and applicable attribution.
- [ ] Verify repository, prototype, slides and video in a signed-out browser.
- [ ] Add organizers' designated GitHub accounts as instructed.
- [ ] Keep this repository **Public** throughout judging.
- [ ] Paste the repository URL on the SDC website's **Submit** page and complete submission.
- [ ] Submit by **25 October 2026, 07:59:59 AM MYT (UTC+8)**; aim for 24 October evening.
- [ ] Stop modifying submitted materials after cutoff unless explicitly authorized.

For a private repository: **Settings -> General -> Danger Zone -> Change repository visibility -> Public**. Review all contents/history for secrets before changing visibility. See [the complete checklist](docs/competition-checklist.md).

## License and attribution

[Apache License 2.0](LICENSE). Adapted from the official SDC Hackathon GitHub Submission Template. The initial upload represents template setup, not completed competition development. Declare supporting templates, third-party resources and AI-assisted tools in the final submission.
