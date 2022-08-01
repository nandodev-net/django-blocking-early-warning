FROM nginx:1.14.2 

RUN rm /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/conf.d/
COPY mime.types /etc/nginx/mime.types