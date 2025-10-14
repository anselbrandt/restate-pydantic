#!/bin/bash

docker run -it --network=host \
docker.restate.dev/restatedev/restate-cli:latest \
deployments register host.docker.internal:9080 --yes