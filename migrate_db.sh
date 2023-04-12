#!/bin/bash
# Use this file to migrate database, might have son fixtures to apply 

# Colors
COLOR_NC="$(tput sgr0)" # No Color
COLOR_BLACK='\e[0;30m'
COLOR_GRAY='\e[1;30m'
COLOR_RED='\e[0;31m'
COLOR_LIGHT_RED='\e[1;31m'
COLOR_GREEN='$(tput setaf2)'
COLOR_LIGHT_GREEN='\e[1;32m'
COLOR_BROWN='\e[0;33m'
COLOR_YELLOW='\e[1;33m'
COLOR_BLUE='\e[0;34m'
COLOR_LIGHT_BLUE='\e[1;34m'
COLOR_PURPLE='\e[0;35m'
COLOR_LIGHT_PURPLE='\e[1;35m'
COLOR_CYAN='\e[0;36m'
COLOR_LIGHT_CYAN='\e[1;36m'
COLOR_LIGHT_GRAY='\e[0;37m'
COLOR_WHITE='\e[1;37m'

printf "${COLOR_LIGTH_BLUE}Making migrations...${COLOR_NC}\n" &&\
docker-compose -f docker-compose.yml exec web python manage.py makemigrations blocking_early_warnings --noinput
printf "${COLOR_LIGTH_BLUE}Migrating...${COLOR_NC}\n" &&\
docker-compose -f docker-compose.yml exec web python manage.py migrate --noinput