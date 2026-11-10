# Jenkins LTS with the tools the pipeline needs: Python 3, venv, Maven and unzip,
# plus the plugins listed in plugins.txt.
FROM jenkins/jenkins:2.462.3-lts-jdk17

USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv python3-pip maven unzip \
 && rm -rf /var/lib/apt/lists/*

USER jenkins
COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt
