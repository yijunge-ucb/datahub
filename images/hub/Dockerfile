# Should match the hub image used by version of chart in hub/requirements.yaml
# If that changes, this should be changed too!
FROM jupyterhub/k8s-hub:4.2.0

USER root

RUN python3 -m pip install --no-cache git+https://github.com/berkeley-dsep-infra/canvasoauthenticator@09e7ed8
RUN python3 -m pip install --no-cache jupyterhub-ltiauthenticator==1.6.2
RUN python3 -m pip install --no-cache git+https://github.com/berkeley-dsep-infra/jupyterhub_grouper_sync.git@ab1cca5
COPY logos /srv/logos

USER ${NB_USER}
