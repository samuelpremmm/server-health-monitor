# CI/CD with Jenkins, Maven, SonarQube and Nexus

This guide sets up a full CI/CD pipeline for the health monitor on your own machine, using Docker.

```
GitHub ──► Jenkins
             ├─ 1. Checkout
             ├─ 2. Set up Python        (virtualenv + pytest, pytest-cov, flake8)
             ├─ 3. Version              (from health_monitor/__init__.py)
             ├─ 4. Lint                 (flake8)
             ├─ 5. Test                 (mvn test → pytest + coverage)
             ├─ 6. SonarQube Analysis   (bugs, code smells, coverage)
             ├─ 7. Quality Gate         (pipeline stops if quality fails)
             ├─ 8. Package              (mvn package → server-health-monitor-<version>-dist.zip)
             ├─ 9. Smoke Test           (unzip and run a real health check on Linux)
             └─ 10. Deploy to Nexus     (mvn deploy → maven-snapshots or maven-releases)
```

## Why Maven in a Python project?

Maven doesn't compile anything here. It runs the **release lifecycle** (`test` → `package` → `deploy`), builds a versioned `.zip` with `maven-assembly-plugin`, and publishes it to a **Nexus Maven repository**. That gives the project the same build and release flow that Java teams use, with versioned, downloadable artifacts.

| File | Purpose |
|---|---|
| `Jenkinsfile` | The pipeline |
| `pom.xml` | Maven build: runs pytest, builds the zip, deploys to Nexus |
| `src/assembly/distribution.xml` | What goes into the zip |
| `sonar-project.properties` | SonarQube settings for Python |
| `ci/maven-settings.xml` | Nexus logins for Maven, filled in by Jenkins at build time |
| `ci/docker-compose.yml` | Starts Jenkins, SonarQube (+ PostgreSQL) and Nexus |
| `ci/jenkins/Dockerfile` | Jenkins with Python 3, Maven and the needed plugins |

## Versions

The version lives in one place: `__version__` in `health_monitor/__init__.py` (currently `1.0.0`).

| Build | Version | Nexus repository |
|---|---|---|
| Normal build | `1.0.0-SNAPSHOT` | `maven-snapshots` (can be overwritten) |
| **Build with Parameters** → tick **RELEASE** | `1.0.0-<build number>`, e.g. `1.0.0-7` | `maven-releases` (permanent) |

---

## 1. Install Docker Desktop

1. Install Docker Desktop for Windows: https://www.docker.com/products/docker-desktop/ (needs admin rights and a restart).
2. Open Docker Desktop and wait until it says **Engine running**.
3. In Docker Desktop → **Settings → Resources**, give it at least **6 GB** of memory.
4. SonarQube needs a larger memory-map limit. Run this in PowerShell each time Docker Desktop restarts:

   ```powershell
   wsl -d docker-desktop sysctl -w vm.max_map_count=524288
   ```

## 2. Start the stack

```bash
cd ci
docker compose up -d --build
docker compose ps
```

The first start takes several minutes (image downloads). Then:

| Tool | URL | First login |
|---|---|---|
| Jenkins | http://localhost:8080 | Password from `docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword` |
| SonarQube | http://localhost:9000 | `admin` / `admin`, then you must set a new password |
| Nexus | http://localhost:8081 | `admin`, password from `docker exec nexus cat /nexus-data/admin.password` |

## 3. Set up Nexus

1. Sign in as `admin` and finish the setup wizard (set a new password, and **disable anonymous access**).
2. The repositories **maven-releases** and **maven-snapshots** already exist. Nothing to create.
3. Optional but better practice: **Settings → Security → Users → Create local user**, for example `jenkins-deployer`, with the `nx-admin` role (or a custom deploy role).

## 4. Set up SonarQube

1. Sign in and change the admin password.
2. **My Account → Security → Generate Tokens**: name `jenkins`, type **Global Analysis Token**. Copy the token.
3. **Administration → Configuration → Webhooks → Create**:
   - Name: `jenkins`
   - URL: `http://jenkins:8080/sonarqube-webhook/`

   Jenkins needs this to receive the Quality Gate result.

## 5. Set up Jenkins

1. Unlock Jenkins, click **Install suggested plugins**, and create your admin user. The plugins from `ci/jenkins/plugins.txt` are already installed.
2. **Manage Jenkins → Credentials → System → Global → Add Credentials**:
   - **Secret text**, ID `sonar-token`, Secret = the SonarQube token
   - **Username with password**, ID `nexus-credentials`, username and password of your Nexus user
3. **Manage Jenkins → System → SonarQube servers**:
   - Tick **Environment variables**
   - Name: `sonarqube`
   - Server URL: `http://sonarqube:9000`
   - Server authentication token: `sonar-token`
4. **Manage Jenkins → Tools → SonarQube Scanner installations → Add**:
   - Name: `sonar-scanner`
   - Tick **Install automatically**

## 6. Create the pipeline job

1. **New Item** → name `server-health-monitor` → **Pipeline** → OK.
2. Under **Pipeline**: Definition **Pipeline script from SCM** → SCM **Git**
   - Repository URL: `https://github.com/samuelpremmm/server-health-monitor.git`
   - Branch: `*/main`
   - Script Path: `Jenkinsfile`
3. Optional: under **Build Triggers**, tick **Poll SCM** with `H/5 * * * *` to build automatically after each push.
4. Save, then click **Build Now**. The first run only loads the `RELEASE` parameter, so run it again with **Build with Parameters**.

## 7. Check the results

- **Jenkins → the job → Stage View**: every stage should be green. Click **Test Result** for the 19 tests.
- **SonarQube → Projects → Linux Server Health Monitor**: Quality Gate, bugs, code smells and coverage.
- **Nexus → Browse → maven-snapshots** (or `maven-releases`) → `com/samuelpremmm/server-health-monitor/<version>/`: the `.pom` and `-dist.zip`.

Download the zip on any Linux server and run it:

```bash
unzip server-health-monitor-1.0.0-7-dist.zip
cd server-health-monitor-1.0.0-7
python3 -m health_monitor
```

## Screenshots to take for your portfolio

1. Jenkins Stage View with all stages green
2. Jenkins test results (19 passed)
3. SonarQube project overview with the Quality Gate **Passed**
4. Nexus browse view showing the uploaded zip
5. The smoke-test health report in the Jenkins console log

## Troubleshooting

| Problem | Fix |
|---|---|
| SonarQube container keeps restarting | Run the `vm.max_map_count` command from step 1, then `docker compose restart sonarqube` |
| Quality Gate stage waits, then times out | The SonarQube webhook from step 4 is missing or has the wrong URL |
| `No tool named sonar-scanner found` | The tool name in step 5.4 must be exactly `sonar-scanner` |
| Deploy fails with `401 Unauthorized` | Wrong `nexus-credentials` username or password |
| Deploy fails with `400 Bad Request` on a release | That release version already exists. Releases can't be overwritten. Run a new build. |
| `python3: not found` | The job is running on an agent without Python. Use the Jenkins image from `ci/jenkins/Dockerfile`. |
| Everything is slow | Give Docker Desktop more memory, or stop the stack when you're not using it: `docker compose stop` |

## Stop or remove the stack

```bash
cd ci
docker compose stop          # stop, keep all data
docker compose down          # remove containers, keep data volumes
docker compose down -v       # remove everything, including Jenkins, SonarQube and Nexus data
```
