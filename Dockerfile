###########
# BUILDER #
###########

# first stage of build to pull repos
FROM python:3.8 as intermediate

# set work directory
WORKDIR /usr/src/chp_api

RUN git clone --single-branch --branch gene_spec_pydantic-ghyde https://github.com/di2ag/gene-specificity.git

# Upgrade pip
RUN pip3 install --upgrade pip

# install dependencies
COPY ./requirements.txt .
RUN pip3 wheel --no-cache-dir --no-deps --wheel-dir /usr/src/chp_api/wheels -r requirements.txt

#gather gene specificity wheel
RUN cd gene-specificity && python3 setup.py bdist_wheel && cd dist && cp gene_specificity-*-py3-none-any.whl /usr/src/chp_api/wheels

#########
# FINAL #
#########

#pull official base image
FROM python:3.8

# add app user
RUN groupadd chp_api && useradd -ms /bin/bash -g chp_api chp_api

# create the appropriate directories
ENV HOME=/home/chp_api
ENV APP_HOME=/home/chp_api/web
RUN mkdir $APP_HOME
RUN mkdir $APP_HOME/staticfiles
WORKDIR $APP_HOME

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV TZ=America/New_York

# set ARGs
ARG DEBIAN_FRONTEND=noninterative

# copy repo to new image
COPY --from=intermediate /usr/src/chp_api/wheels /wheels
COPY --from=intermediate /usr/src/chp_api/requirements.txt .
# Running this command to ensure version 1 of pydantic is being used until reasoner-pydantic is updated.
RUN pip3 install pydantic==1.10.12
RUN pip3 install --no-cache /wheels/*

# copy project
COPY ./chp_api/chp_api $APP_HOME/chp_api
COPY ./chp_api/manage.py $APP_HOME
COPY ./chp_api/dispatcher $APP_HOME/dispatcher
COPY ./gunicorn.config.py $APP_HOME

# chown all the files to the app user
RUN chown -R chp_api:chp_api $APP_HOME \
    && chmod 700 $APP_HOME/staticfiles

# change to the app user
USER chp_api
