# Copyright 2020 Google LLC
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
"""Data Commons static content routes."""

from flask import Blueprint
from flask import render_template

bp = Blueprint('ts_issue_landing', __name__)


@bp.route('/food-security')
def food_security():
    return render_template('custom_dc/techsoup/issue_landing/foodsecurity.html')


@bp.route('/climate')
def climate():
    return render_template('custom_dc/techsoup/issue_landing/climate.html')
