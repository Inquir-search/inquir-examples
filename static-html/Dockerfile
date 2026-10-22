# nginx that runs as a regular user and listens on port 8080
FROM nginxinc/nginx-unprivileged:1.30.6-alpine@sha256:f5116ed4606f3eb015dd4a8e28cb9b351476dc0ad4bc6e9f93b19cec130cdf03
# Your site: everything in the public/ folder
COPY public/ /usr/share/nginx/html/
EXPOSE 8080
