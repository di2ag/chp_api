#!/bin/bash

# variables 
projectName="chp-api"
namespace="chp"
# replace place_holder with values from env var
# env var's key needs to be the same as the place_holder
toReplace=('BUILD_VERSION')

# export .env values to env vars
# export $(egrep -v '^#' .env)

# printenv

# replace variables in values.yaml with env vars

for item in "${toReplace[@]}";
do
  sed -i.bak \
      -e "s/${item}/${!item}/g" \
      values.yaml
  rm values.yaml.bak
done

sed -i.bak \
    -e "s/APP_SECRET_KEY_VALUE/$APP_SECRET_KEY/g" \
    -e "s/DB_USERNAME_VALUE/$DB_USERNAME/g" \
    -e "s/DB_PASSWORD_VALUE/$DB_PASSWORD/g" \
    -e "s/DJANGO_SUPERUSER_PASSWORD_VALUE/$DJANGO_SUPERUSER_PASSWORD/g" \
    values-ncats.yaml
rm values-ncats.yaml.bak

kubectl apply -f namespace.yaml

# deploy helm chart
helm -n ${namespace} upgrade --install ${projectName} -f values-ncats.yaml ./