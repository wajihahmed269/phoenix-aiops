# PFMS MVP Image Publishing

PFMS MVP images are published to GitHub Container Registry because the project already uses GitHub-centered GitOps workflows and GHCR gives the MVP a simple immutable image location without introducing another registry service.

The selected image namespace is:

```text
ghcr.io/wajihahmed269
```

The selected immutable tag is:

```text
pfms-mvp-v1
```

## Login

Log in before pushing images:

```bash
echo "<GITHUB_TOKEN>" | docker login ghcr.io -u wajihahmed269 --password-stdin
```

The GitHub token must never be committed, written into files, pasted into manifests, or stored in this repository.

## Dry Run

Retag local PFMS MVP images and print the push commands without pushing:

```bash
./scripts/publish-pfms-mvp-images.sh
```

## Push

Push only after `docker login ghcr.io` succeeds:

```bash
PUSH_IMAGES=true ./scripts/publish-pfms-mvp-images.sh
```

The script does not handle GitHub tokens and does not store credentials.

## Verify Local Tags

```bash
docker images | grep ghcr.io/wajihahmed269/pfms
```

## Next Step

After images are pushed, validate Kustomize again and then prepare a manual Argo CD deployment. Keep Argo CD sync manual until the first rollout is reviewed and explicitly approved.
