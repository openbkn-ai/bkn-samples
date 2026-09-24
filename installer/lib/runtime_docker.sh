#!/usr/bin/env bash

resolve_runtime() {
  local requested="$1" catalog_host="$2"
  case "$requested" in
    docker|k8s) printf '%s\n' "$requested" ;;
    auto)
      if command -v kubectl >/dev/null 2>&1 && kubectl get namespace openbkn >/dev/null 2>&1; then
        printf 'k8s\n'
      elif [[ -n "$catalog_host" ]]; then
        printf 'docker\n'
      else
        die "cannot choose a runtime automatically; use --runtime k8s or --runtime docker --catalog-host <host>"
      fi
      ;;
  esac
}

prepare_docker_runtime() {
  local root="$1" catalog_host="$2" catalog_port="$3" upgrade="$4"
  local state_dir password attempt image project env_file
  require_command docker
  docker compose version >/dev/null 2>&1 || die "Docker Compose plugin is required"
  state_dir="$(state_root)/runtime/$SAMPLE_ID"
  mkdir -p "$state_dir"
  chmod 700 "$(state_root)" "$(state_root)/runtime" "$state_dir"
  password_file="$state_dir/database-password"
  if [[ -f "$password_file" ]]; then
    password="$(<"$password_file")"
  else
    password="$(random_secret)"
    (umask 077; printf '%s\n' "$password" >"$password_file")
  fi
  attempt="$(random_secret)"
  image="swr.cn-east-3.myhuaweicloud.com/openbkn-ai/bkn-samples:$(<"$root/VERSION")"
  # Release tags are immutable.  Reusing a local copy also makes a verified
  # installation possible on hosts whose registry egress is restricted.
  if docker image inspect "$image" >/dev/null 2>&1; then
    printf 'runtime: using locally available image %s\n' "$image"
  elif ! docker pull "$image"; then
    image="ghcr.io/openbkn-ai/bkn-samples:$(<"$root/VERSION")"
    printf 'warning: SWR image could not be pulled; retrying from GHCR\n' >&2
    docker pull "$image" || die "could not pull the bkn-samples image from SWR or GHCR"
  fi
  project="bkn-sample-$SAMPLE_ID"
  env_file="$state_dir/compose.env"
  ( umask 077
    {
      printf 'BKN_SAMPLE_ID=%s\n' "$SAMPLE_ID"
      printf 'BKN_SAMPLE_VERSION=%s\n' "$SAMPLE_VERSION"
      printf 'BKN_DATA_VERSION=%s\n' "$SAMPLE_DATA_VERSION"
      printf 'BKN_DATABASE=%s\n' "$SAMPLE_DATABASE"
      printf 'BKN_DATABASE_PASSWORD=%s\n' "$password"
      printf 'BKN_INIT_ATTEMPT=%s\n' "$attempt"
      printf 'BKN_SAMPLES_IMAGE=%s\n' "$image"
      printf 'BKN_CATALOG_PORT=%s\n' "$catalog_port"
      printf 'BKN_CATALOG_BIND_HOST=0.0.0.0\n'
    } >"$env_file"
  )

  docker compose --env-file "$env_file" -p "$project" -f "$root/installer/manifests/compose.yaml" up -d
  wait_for_docker_health "$project" "$root/installer/manifests/compose.yaml" "$env_file"

  printf 'runtime: Docker container started for %s; OpenBKN must reach %s:%s\n' \
    "$SAMPLE_ID" "$catalog_host" "$catalog_port"
  if (( upgrade )); then
    printf 'note: --upgrade was requested; upgrade hook execution is pending platform bootstrap support\n'
  fi
}

wait_for_docker_health() {
  local project="$1" compose_file="$2" env_file="$3" id status attempt
  for attempt in $(seq 1 60); do
    id="$(docker compose --env-file "$env_file" -p "$project" -f "$compose_file" ps -q database)"
    if [[ -n "$id" ]]; then
      status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$id")"
      [[ "$status" == healthy ]] && return 0
      [[ "$status" == exited || "$status" == dead ]] && break
    fi
    sleep 2
  done
  docker compose --env-file "$env_file" -p "$project" -f "$compose_file" logs --no-color database >&2 || true
  die "sample database did not become healthy"
}
