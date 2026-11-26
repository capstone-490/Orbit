<h1 align="center">Orbit</h1>

## CI Information

**GitHub Actions** is used for continuous integration.

[View GitHub Actions workflows](https://github.com/capstone-490/Orbit/actions)
  
## Release demos   
- Release 1 Demo Video:  

 https://drive.google.com/file/d/1v-vE-wtCb19aHuWyVFc6kBANI4IcnZIB/view?usp=sharing    

- Release 1 Slides:   

https://docs.google.com/presentation/d/17RosGkqKAPLe0rOtL0uF40UAQ8pBdH7P_8N5PPo3GQ4/edit?usp=sharing
  
## Project summary

Orbit is an AI-powered client and workflow management platform built for financial advisors that focuses on centralizing daily administrative tasks and client management activities to reduce the burden of managing multiple clients. Specialized AI agents support advisors by handling tasks such as drafting messages, suggesting tasks, summarizing information and identifying follow-up actions. Orbit includes a coordination mechanism that detects conflicting, duplicate and stale updates to reconcile the outputs of different AI agents before any changes are committed, while advisors have final approval over important actions.

## Developer getting started guide

### 1. Prerequisites

- [GIT](https://git-scm.com/install/)
- [Docker](https://docs.docker.com/engine/install/) | [docker desktop](https://docs.docker.com/desktop/setup/install/windows-install/)
- [UV](https://docs.astral.sh/uv/getting-started/installation/)
- [PNPM](https://pnpm.io/installation)
- [Make](https://gnuwin32.sourceforge.net/downlinks/make.php) | [Make windows](https://gnuwin32.sourceforge.net/downlinks/make.php)

### Downloading dependencies (Windows)

Docker: Here's a [video tutorial](https://www.youtube.com/watch?v=5Mfe54238xE) to simplify the installation of Docker Desktop on a Windows computer. You only need to follow the tutorial until 11:20. Our application only requires Docker Desktop to be installed and running. You don't need to configure anything else.

Make:

- Click on make in the Install section which should directly lead you to having an make***.exe file downloaded on your computer.
- After download, click on the exe file to install it on your computer.
- Go to the folder where you installed it. Click on the GnuWin32 folder, then bin folder.
- Ctrl + C the path
  Example here the path is C:\Users\Temp\Downloads\GnuWin32\bin
  <img width="909" height="154" alt="image" src="https://github.com/user-attachments/assets/436f7d92-722d-468c-9577-af43ebf79eb8" />
- Add this path to your Systems Variables [tutorial here](https://www.youtube.com/watch?v=dTZJQfMCHbg)
- Open the Terminal or Powershell program

UV:

- Click on uv in the Install section
- Open the Terminal or Powershell
- Copy and Paste the command for Windows shown on the uv webpage to the Windows Powershell program and press Enter

PNPM:

- Click on pnpm in the Install section
- Open Powershell
- Copy-Paste the command for Powershell shown on the pnpm webpage and press Enter


Run the following block to confirm every tool is ready:

```bash
git --version
docker --version
docker compose version
make --version
uv --version
pnpm --version
```

---

## 2. Quickstart

**Prerequisites:** Docker running and dependencies above installed

```bash
# open your terminal program and navigate to some empty folder

git clone git@github.com:capstone-490/Orbit.git orbit
cd orbit/

cp .env.example .env

cd backend/ && uv sync && cd ..
cd frontend/ && pnpm install && cd ..

make dev        # run live app
make mon        # run live with metrics
make test       # run front/backend tests
make test-cov   # run front/backend tests show coverage
make test-fe    # run frontend tests
make test-be    # run backend tests
make down       # stop containers
make clean      # remove all containers and data

# OR
docker compose -f compose.yml -f compose.dev.yml up -d --build
docker compose -f compose.yml -f compose.dev.yml down --remove-orphans
```

### See Backend/Frontend README for further detailed instruction

---

### End-to-end tests (Playwright)

**Prerequisites:**

- Docker running, frontend dependencies are installed, and the Playwright browser installed (one-time):
- Stop any running app before running E2E tests. The test stack uses the same ports (backend: 8001, frontend: 5173).

```bash
cd frontend
pnpm exec playwright install chromium
```

**Run everything** from the project root:

```bash
make test-e2e
```

**Run Playwright directly**:

```bash
docker compose -f compose.test.yml up -d --wait --build backend
cd frontend && pnpm test:e2e
# when finished:
docker compose -f compose.test.yml down -v
```

**View the test report:** `cd frontend && pnpm test:e2e:report`. Traces and screenshots from failed tests are in `frontend/test-results/`.

## Tech Stack

| Layer | Technologies |
| --- | --- |
| **Frontend Application** | React.js, Vite, CSS, Nginx |
| **Frontend Tooling & QA** | Node.js 22, pnpm, Vitest, Biome, ESLint |
| **Backend API** | Python 3.14, FastAPI, Pydantic, Uvicorn |
| **Database & Persistence** | PostgreSQL, SQLAlchemy, Alembic |
| **Backend Tooling & QA** | uv, Pytest, Ruff, Mypy |
| **Security & Privacy** | Custom PII Redactor, Anonymizer, Token Cipher |
| **Observability & Load Testing** | Prometheus, Structured Logging, k6, Codecov |
| **Infrastructure & Orchestration** | Docker, Docker Compose, GNU Make |
  
## Project board

[Orbit Project Board](https://github.com/orgs/capstone-490/projects/3/views/2)

# Diversity and Inclusion Statement

We believe that projects like ours thrive when shaped by diverse perspectives, backgrounds, nationalities, and identities. A diverse community creates better, more robust technology.

The Orbit project welcomes and encourages participation by everyone. Our community is based on mutual respect, tolerance, and encouragement, and we are working to help each other live up to these principles. We want our community to be more diverse: whoever you are, and whatever
your background, we welcome you.

## Our Commitments

- **Inclusive Language:** We encourage and utilize inclusive language in our codebase, documentation, issues, and discussions. This includes avoiding gendered, ableist, or exclusionary terminology.
- **Representation:** We intentionally seek and welcome contributions from different genders, ethnicities, backgrounds, abilities, and other historically underrepresented groups in technology.
- **Barrier Reduction:** We work to minimize technical and social barriers to entry. Whether you are fixing a typo, updating documentation, or refactoring code, your contributions are equally valued.
- **Safe Environments:** We will not officially participate in, align with, or sponsor events unless they operate under and enforce a clear code of conduct.

We recognize that we may not always get everything right, but we are committed to continuous learning, listening, and evolving our processes to ensure an equitable ecosystem.

## Wiki table of contents

- [Home](https://github.com/capstone-490/Orbit/wiki)
- [Meeting Minutes](https://github.com/capstone-490/Orbit/wiki/01.-Meeting-Minutes)
- [Risks](https://github.com/capstone-490/Orbit/wiki/02.-Risks)
- [User Consent & License Agreement](https://github.com/capstone-490/Orbit/wiki/03.-User-Consent-&-License-Agreement)
- [Legal & Ethical Issues](https://github.com/capstone-490/Orbit/wiki/04.-Legal-&-Ethical-Issues)
- [Economic](https://github.com/capstone-490/Orbit/wiki/05.-Economic)
- [Budget](https://github.com/capstone-490/Orbit/wiki/06.-Budget)
- [Personas](https://github.com/capstone-490/Orbit/wiki/07.-Personas)
- [Diversity Statement](https://github.com/capstone-490/Orbit/wiki/08.-Diversity-Statement)
- [Overall Architecture and Class Diagrams](https://github.com/capstone-490/Orbit/wiki/09.-Overall-Architecture-and-Class-Diagrams)
- [Infrastructure & Tools](https://github.com/capstone-490/Orbit/wiki/10.-Infrastructure-&-Tools)
- [Name Conventions](https://github.com/capstone-490/Orbit/wiki/11.-Name-Conventions)
- [Testing Plan & Continuous Integration](https://github.com/capstone-490/Orbit/wiki/12.-Testing-Plan-&-Continuous-Integration)
- [Security](https://github.com/capstone-490/Orbit/wiki/13.-Security)
- [Performance](https://github.com/capstone-490/Orbit/wiki/14.-Performance)
- [Deployment Plan & Infrastructure](https://github.com/capstone-490/Orbit/wiki/15.-Deployment-Plan-&-Infrastructure)
- [Missing Knowledge & Independent Learning](https://github.com/capstone-490/Orbit/wiki/16.-Missing-Knowledge-&-Independent-Learning)
- [Iteration & Release Notes](https://github.com/capstone-490/Orbit/wiki/17.-Iteration-&-Release-Notes)
- [Overall Summary](https://github.com/capstone-490/Orbit/wiki/18.-Overall-Summary)
- [Velocity and Contractor Estimate](https://github.com/capstone-490/Orbit/wiki/19.-Velocity-and-Contractor-Estimate)
- [Retrospective](https://github.com/capstone-490/Orbit/wiki/20.-Retrospective)
- [Breakdown by individual](https://github.com/capstone-490/Orbit/wiki/21.-Breakdown-by-individual)
- [UI Mockups](https://github.com/capstone-490/Orbit/wiki/22.-UI-Mockups)
