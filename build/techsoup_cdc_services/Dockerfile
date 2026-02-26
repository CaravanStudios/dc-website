# Use main_server as base
FROM gcr.io/datcom-ci/datacommons-services:stable AS base

# Stage 1: Extend React Static Files
FROM node:20 AS extended_builder
WORKDIR /workspace

# Install dependencies
#COPY techsoup_server/static/package.json techsoup_server/static/package-lock.json ./
#RUN npm install --prefix ./ ci --omit=dev

COPY packages/dc-home-reboot/ ./packages/dc-home-reboot/
COPY packages/dc-home-reboot/package-lock.json ./packages/dc-home-reboot/package-lock.json
RUN npm install --prefix ./packages/dc-home-reboot ci

# Copy extended static files (overrides)
#COPY techsoup_server/static/ ./techsoup_server/static/
COPY packages/dc-home-reboot/ ./packages/dc-home-reboot/


WORKDIR /workspace/packages/dc-home-reboot
RUN ls -alh

RUN npm run-script build

# Stage 2: Extended Flask App
FROM base
WORKDIR /workspace

# Override static files with extended ones
#COPY --from=extended_builder /extended_app/techsoup_server/static/dist /app/dist

# Workaround for the issue with the Flask app not being able to find the 'server.app_env.techsoup' module.
COPY ts_server/app_env/techsoup.py ./server/app_env/techsoup.py
COPY ts_server/requirements.txt ./ts_server/requirements.txt

# Workaround to put back the techsoup topic pages
COPY server/config ./server/config
COPY server/routes/topic_page ./server/routes/topic_page
COPY server/lib/util.py ./server/lib/util.py

RUN pip3 install --no-cache-dir -r /workspace/ts_server/requirements.txt

# Override Flask app if needed
COPY ts_server/ ./ts_server/
COPY ts_web_app.py .

# Copy executable script.
COPY build/techsoup_cdc_services/run_nginx.sh .
COPY build/techsoup_cdc_services/run.sh .

# Static website assets.
# Copy built package into a temporary folder
COPY --from=extended_builder /workspace/packages/dc-home-reboot/dist /tmp/packages_dist

# Copy static files into a temporary folder
COPY ts_server/static /tmp/ts_server_static

# Create final dist directory and merge both sources
RUN mkdir -p ./ts_server/dist && \
    cp -r /tmp/packages_dist/* ./ts_server/dist/ && \
    cp -r /tmp/ts_server_static/* ./ts_server/dist/

# Copy robotx and sitemaps to server/dist
RUN rm -rf ./server/dist/robots.txt && \
    rm -rf ./server/dist/sitemap && \
    cp -r /tmp/ts_server_static/robots.txt ./server/dist/robots.txt && \
    cp -r /tmp/ts_server_static/sitemap ./server/dist/sitemap

# nginx.
COPY build/techsoup_cdc_services/nginx.conf ./nginx.conf

## Copy executable script.
#COPY build/cdc_services/run.sh .

# Make script executable.
RUN chmod +x run_nginx.sh
RUN chmod +x run.sh

# Add virtual env to the path.
ENV PATH="/workspace/venv/bin:$PATH"

# Run the app
CMD ./run.sh