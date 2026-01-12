# Should match the hub image used by version of chart in hub/requirements.yaml
# If that changes, this should be changed too!
FROM jupyterhub/k8s-hub:4.2.0

USER root

RUN python3 -m pip install --no-cache git+https://github.com/berkeley-dsep-infra/canvasoauthenticator@d66662a
RUN python3 -m pip install --no-cache jupyterhub-ltiauthenticator==1.6.2
RUN python3 -m pip install --no-cache git+https://github.com/berkeley-dsep-infra/jupyterhub_grouper_sync.git@410300d
RUN python3 -m pip install --no-cache jupyterhub-fancy-profiles==0.6.0
COPY logos /srv/logos

USER ${NB_USER}
