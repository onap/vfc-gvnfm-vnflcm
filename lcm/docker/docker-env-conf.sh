#!/bin/bash

install_sf(){

    apk --no-cache update
    apk --no-cache add bash curl gcc wget mysql-client openssl-dev
    apk --no-cache add python36-dev libffi-dev musl-dev py3-virtualenv

    # get binary zip from nexus - vfc-nfvo-catalog
    wget -q -O vfc-gvnfm-vnflcm-lcm.zip "https://nexus.onap.org/service/local/artifact/maven/redirect?r=snapshots&g=org.onap.vfc.gvnfm.vnflcm.lcm&a=vfc-gvnfm-vnflcm-lcm&v=${pkg_version}-SNAPSHOT&e=zip" && \
    unzip vfc-gvnfm-vnflcm-lcm.zip && \
    rm -rf vfc-gvnfm-vnflcm-lcm.zip
    wait
    pip install --upgrade setuptools pip
    pip install --no-cache-dir --pre -r  /service/vfc/gvnfm/vnflcm/lcm/requirements.txt
}

add_user(){

    apk --no-cache add sudo
    addgroup -g 1000 -S onap
    adduser onap -D -G onap -u 1000
    chmod u+w /etc/sudoers
    sed -i '/User privilege/a\\onap    ALL=(ALL:ALL) NOPASSWD:ALL' /etc/sudoers
    chmod u-x /etc/sudoers
    sudo chown onap:onap -R /service
}

config_logdir(){

    if [ ! -d "/var/log/onap" ]; then
       sudo mkdir /var/log/onap
    fi 
   
    sudo chown onap:onap -R /var/log/onap
    chmod g+s /var/log/onap
    
}

clean_sf_cache(){

    rm -rf /var/cache/apk/*
    rm -rf /root/.cache/pip/*
    rm -rf /tmp/*
}

patch_redisco_2py3(){
    sed -i 's/raise KeyError, value/raise KeyError(value)/g' /usr/local/lib/python3.6/site-packages/redisco/containers.py
}
install_sf
wait
add_user
config_logdir
patch_redisco_2py3
clean_sf_cache

