# CDSS Discovery Configuration

## Stellar Shared Volume

A group needed additional storage for their particular project. While on other
hubs we would create directories on the filestore, at NRP we need to create
volumes in the cluster.

```shell
export KUBECONFIG=./deployments/cdss-discovery/secrets/cdss-discovery-all-sa.yaml
k --context cdss-discovery-staging apply -f stellar-staging.yaml
k --context cdss-discovery-prod    apply -f stellar-prod.yaml
```

The necessary `custom.group_profiles` configuration was added to `config/common.yaml`.

Finally, when the volume was mounted for the first time in a pod with write access, the permissions needed to be changed.

```shell-session
$ k --context cdss-discovery-staging exec -it jupyter-rylo -- bash
root@jupyter-rylo:~# cd /home/jovyan/
root@jupyter-rylo:~# chown jovyan:users _shared/2025-fall-stellar/ _shared/
root@jupyter-rylo:~# ls -ld _shared/
drwxr-sr-x 3 jovyan users 31 Sep 19 22:03 _shared/
root@jupyter-rylo:~# ls -ld _shared/2025-fall-stellar/
drwxr-xr-x 2 jovyan users 0 Sep 19 21:49 _shared/2025-fall-stellar/
```


### Install gsutil

This is fairly standard installation. I chose to do a one-time install from a kubectl shell, rather than build it into the image.

```shell
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] http://packages.cloud.google.com/apt cloud-sdk main" > a /etc/apt/sources.list.d/google-cloud-sdk.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
apt update
apt-get install google-cloud-sdk
```

### Fetch the Data

I then launched a jupyter terminal.

```shell
gcloud auth login
gcloud auth application-default login
cd _shared/2025-fall-stellar
gsutil cp -r gs://{bucket-name}/ .
gsutil -m cp -r -n gs://{bucket-name}/ .
```

 - `-m` is for multi-threaded to download files in parallel.
 - `-r` is to recursively copy the bucket.
 - `-n` is to not clobber files that already exist locally, in case the command needs to restart.
