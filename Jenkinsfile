// CI/CD pipeline for the Linux Server Health Monitor.
//
//   Checkout -> Python setup -> Version -> Lint -> Test (Maven + pytest)
//   -> SonarQube analysis -> Quality Gate -> Package (Maven zip)
//   -> Smoke test on Linux -> Deploy to Nexus
//
// Jenkins setup this file expects (see docs/CICD_SETUP.md):
//   - SonarQube server named   'sonarqube'      (Manage Jenkins > System)
//   - SonarQube Scanner tool   'sonar-scanner'  (Manage Jenkins > Tools)
//   - Credentials 'nexus-credentials' (username + password for Nexus)
//   - python3, python3-venv, maven and unzip on the agent (ci/jenkins/Dockerfile)

pipeline {
    agent any

    parameters {
        booleanParam(
            name: 'RELEASE',
            defaultValue: false,
            description: 'Deploy a release (e.g. 1.0.0-12) to maven-releases. Unticked deploys 1.0.0-SNAPSHOT to maven-snapshots.'
        )
    }

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
        timeout(time: 30, unit: 'MINUTES')
    }

    environment {
        NEXUS_URL = 'http://nexus:8081'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Set up Python') {
            steps {
                sh '''
                    python3 -m venv .venv
                    .venv/bin/pip install --quiet --upgrade pip
                    .venv/bin/pip install --quiet pytest pytest-cov flake8
                    .venv/bin/python --version
                '''
            }
        }

        stage('Version') {
            steps {
                script {
                    def base = sh(
                        returnStdout: true,
                        script: ".venv/bin/python -c 'import health_monitor; print(health_monitor.__version__)'"
                    ).trim()
                    env.APP_VERSION = params.RELEASE ? "${base}-${env.BUILD_NUMBER}" : "${base}-SNAPSHOT"
                    currentBuild.displayName = "#${env.BUILD_NUMBER} ${env.APP_VERSION}"
                }
                sh 'mvn -B -q org.codehaus.mojo:versions-maven-plugin:2.16.2:set -DnewVersion="$APP_VERSION" -DgenerateBackupPoms=false'
                echo "Building version ${env.APP_VERSION}"
            }
        }

        stage('Lint') {
            steps {
                sh '''
                    mkdir -p target
                    # Fail the build on syntax errors and undefined names.
                    .venv/bin/flake8 . --exclude .venv,target --count --select=E9,F63,F7,F82 --show-source --statistics
                    # Style warnings only, saved for SonarQube.
                    .venv/bin/flake8 . --exclude .venv,target --exit-zero --max-line-length=127 --output-file=target/flake8.txt
                '''
            }
        }

        stage('Test') {
            steps {
                sh 'mvn -B test -Dpython.executable="$WORKSPACE/.venv/bin/python"'
            }
            post {
                always {
                    junit allowEmptyResults: false, testResults: 'target/test-reports/*.xml'
                }
            }
        }

        stage('SonarQube Analysis') {
            steps {
                script {
                    def scannerHome = tool 'sonar-scanner'
                    withSonarQubeEnv('sonarqube') {
                        sh "${scannerHome}/bin/sonar-scanner -Dsonar.projectVersion=${env.APP_VERSION}"
                    }
                }
            }
        }

        stage('Quality Gate') {
            steps {
                // Needs a SonarQube webhook to http://jenkins:8080/sonarqube-webhook/
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Package') {
            steps {
                sh 'mvn -B package -DskipTests'
                archiveArtifacts artifacts: 'target/*-dist.zip', fingerprint: true
            }
        }

        stage('Smoke Test') {
            steps {
                // Unzip the package exactly as a server would and run a real health check.
                sh '''
                    rm -rf target/smoke && mkdir -p target/smoke
                    unzip -q target/server-health-monitor-*-dist.zip -d target/smoke
                    cd target/smoke/server-health-monitor-*/
                    status=0
                    python3 -m health_monitor --disk / || status=$?
                    echo "Health monitor exit code: $status (0=OK, 1=WARNING, 2=CRITICAL)"
                    test "$status" -le 2
                '''
            }
        }

        stage('Deploy to Nexus') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'nexus-credentials',
                    usernameVariable: 'NEXUS_USERNAME',
                    passwordVariable: 'NEXUS_PASSWORD'
                )]) {
                    sh 'mvn -B -s ci/maven-settings.xml deploy -DskipTests -Dnexus.url="$NEXUS_URL"'
                }
            }
        }
    }

    post {
        success {
            script {
                def repo = params.RELEASE ? 'maven-releases' : 'maven-snapshots'
                echo "Deployed server-health-monitor ${env.APP_VERSION} to ${env.NEXUS_URL}/#browse/browse:${repo}"
            }
        }
        failure {
            echo 'Pipeline failed. Open the red stage in Stage View to see which step broke.'
        }
    }
}
