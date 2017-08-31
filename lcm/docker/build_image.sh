#!/bin/bash

MYSQL_ROOT_PASSWORD="root"
PROXY_ARGS=""

if [ $HTTP_PROXY ]; then
    PROXY_ARGS+="--build-arg HTTP_PROXY=${HTTP_PROXY}"
fi
if [ $HTTPS_PROXY ]; then
    PROXY_ARGS+=" --build-arg HTTPS_PROXY=${HTTPS_PROXY}"
fi

function build_vnflcm {
    cd ../
    docker build ${PROXY_ARGS} --build-arg MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD} -f docker/Dockerfile -t gvnfm-vnflcm .
}

build_vnflcm
docker image list
