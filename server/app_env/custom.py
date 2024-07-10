# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os

from server.app_env import _base
from server.app_env import local


class Config(_base.Config):
  CUSTOM = True
  NAME = "Data Commons for Civil Society"
  OVERRIDE_CSS_PATH = '/custom_dc/custom/overrides.css'
  LOGO_PATH = "/custom_dc/custom/techsoup-logo.svg"
  MIN_STAT_VAR_GEO_COVERAGE = 1
  SHOW_DISASTER = False
  USE_LLM = False
  USE_MEMCACHE = False
  ENABLE_MODEL = os.environ.get('ENABLE_MODEL')


class LocalConfig(Config, local.Config):
  #LITE = True
  API_ROOT = 'https://api.datacommons.org'
  # NEED TO DO THE FOLLOWING CHANGES:
  # 1. Send an email to <support+custom@datacommons.org> to get an API key
  #    for Data Commons API.
  # 2. In the custom GCP project, store the API key in secret manager
  #    `printf "<API_KEY>" | gcloud secrets create mixer-api-key --data-file=-`
  # 3. Update SECRET_PROJECT to be the custom GCP project id.
  SECRET_PROJECT = 'techsoup-data-commons'

class ComposeConfig(Config, local.Config):
  pass
