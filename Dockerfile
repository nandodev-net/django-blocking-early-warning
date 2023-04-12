# -- < BUILDER > ---------------------
FROM python:3.10.2 as builder

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1


# install psycopg2 dependencies
# RUN apk update \
#     && apk add postgresql-dev gcc python3-dev musl-dev

# lint
# RUN pip install --upgrade pip
# RUN pip install flake8==3.9.2
COPY . .
# RUN flake8 --ignore=E501,F401 .

# -- < Final > -----------------------

FROM python:3.10.2 

RUN apt-get update
RUN apt-get install -y netcat

# -- This should be installed with poetry, fix later TODO
RUN pip install gunicorn
# ------------------------------------

# create the app user
RUN addgroup --system vsf && adduser --system vsf --ingroup vsf

# # create directory for the app user
# RUN mkdir -p /home/vsf

# create the appropriate directories
ENV HOME=/home/vsf
ENV APP_HOME=/home/vsf/web
RUN mkdir $APP_HOME
RUN mkdir $APP_HOME/staticfiles
WORKDIR $APP_HOME


# Install more dependencies 
RUN pip install poetry --no-cache-dir

# RUN apt-get update && apt-get install libpq

COPY ./entrypoint.prod.sh .
RUN sed -i 's/\r$//g'  $APP_HOME/entrypoint.prod.sh
RUN chmod +x  $APP_HOME/entrypoint.prod.sh

# Copy django project to its corresponding dir
RUN mkdir ${APP_HOME}/docker_project
COPY docker_project ${APP_HOME}/docker_project

# Copy standalone app to its corresponding dir
RUN mkdir ${APP_HOME}/early_warnings
COPY . ${APP_HOME}/early_warnings

# Remove duplicate project
RUN rm -r ${APP_HOME}/early_warnings/docker_project 

# Copy web service script
COPY run_web_service.sh ${APP_HOME}/docker_project/early_warnings/early_warnings
RUN chmod +x ${APP_HOME}/docker_project/early_warnings/early_warnings/run_web_service.sh

# chown all the files to the app user
RUN chown -R vsf:vsf $APP_HOME

# Install project
WORKDIR ${APP_HOME}/docker_project/early_warnings
RUN poetry config virtualenvs.create false --local
RUN poetry install && rm -rf ~/.cache/pypoetry/{cache,artifacts}
WORKDIR ${APP_HOME}/docker_project/early_warnings/early_warnings
RUN ls -l

# Install standalone app 
RUN pip install -e ${APP_HOME}/early_warnings --no-cache-dir


# change to the app user
USER vsf

# Add local executables 
ENV PATH=${PATH}:$HOME/.local/bin
# run entrypoint.prod.sh
ENTRYPOINT ["/home/vsf/web/entrypoint.prod.sh"]