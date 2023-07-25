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
"""Endpoints for Datacommons NL"""

from enum import Enum
import json
import logging
import os
import time
from typing import Dict, List

import flask
from flask import Blueprint
from flask import current_app
from flask import request
from google.protobuf.json_format import MessageToJson

import server.lib.insights.fulfiller as fulfillment
import server.lib.nl.common.constants as constants
import server.lib.nl.common.counters as ctr
import server.lib.nl.common.topic as topic
import server.lib.nl.common.utils as utils
import server.lib.nl.common.utterance as nl_utterance
import server.lib.nl.config_builder.builder as config_builder
import server.lib.nl.detection.detector as detector
from server.lib.nl.detection.types import Place
from server.lib.nl.detection.utils import create_utterance
from server.lib.subject_page_config import place_metadata
from server.lib.util import get_nl_disaster_config
from server.routes.nl import helpers

bp = Blueprint('insights_api', __name__, url_prefix='/api/insights')


class Params(str, Enum):
  ENTITIES = 'entities'
  VARS = 'variables'
  CHILD_TYPE = 'childEntityType'
  SESSION_ID = 'sessionId'
  CTX = 'context'


#
# The detection endpoint.
#
@bp.route('/detect', methods=['POST'])
def detect():
  debug_logs = {}
  utterance, error_json = helpers.parse_query_and_detect(request, debug_logs)
  if error_json:
    return error_json
  if not utterance:
    return helpers.abort('Failed to process!', '', [])

  _hoist_topic(utterance)
  dbg_counters = utterance.counters.get()
  utterance.counters = None
  context_history = nl_utterance.save_utterance(utterance)
  data_dict = {
      Params.ENTITIES.value: [
          p.dcid for p in utterance.detection.places_detected.places_found
      ],
      Params.VARS.value: utterance.svs,
      Params.CTX: context_history,
      Params.SESSION_ID: utterance.session_id,
  }
  place_type = utils.get_contained_in_type(utterance)
  if place_type:
    data_dict[Params.CHILD_TYPE.value] = place_type
  status_str = "Successful"
  return helpers.prepare_response(data_dict,
                                  status_str,
                                  utterance.detection,
                                  dbg_counters,
                                  debug_logs,
                                  is_nl=False)


#
# The fulfillment endpoint.
#
# POST request should contain:
#  - entities: An ordered list of places or other entity DCIDs.
#  - variables: A ordered list of SV or topic (dc/topic/..) DCIDs.
#  - childEntityType: A type of child entity (optional)
#
@bp.route('/fulfill', methods=['POST'])
def fulfill():
  """Data handler."""
  logging.info('NL Chart API: Enter')
  # NO production support yet.
  if os.environ.get('FLASK_ENV') == 'production':
    flask.abort(404)

  req_json = request.get_json()
  if not req_json:
    helpers.abort('Missing input', '', [])
    return
  if (not req_json.get('entities') or not req_json.get('variables')):
    helpers.abort('Entities and variables must be provided', '', [])
    return

  entities = req_json.get(Params.ENTITIES.value)
  variables = req_json.get(Params.VARS.value)
  child_type = req_json.get(Params.CHILD_TYPE.value)
  session_id = req_json.get(Params.SESSION_ID.value)

  counters = ctr.Counters()
  debug_logs = {}

  if not session_id:
    if current_app.config['LOG_QUERY']:
      session_id = utils.new_session_id()
    else:
      session_id = constants.TEST_SESSION_ID

  # There is not detection, so just construct a structure.
  start = time.time()
  query_detection, error_msg = detector.construct(entities, variables,
                                                  child_type, debug_logs,
                                                  counters)
  counters.timeit('query_detection', start)
  if not query_detection:
    helpers.abort(error_msg, '', [])
    return

  utterance = create_utterance(query_detection, None, counters, session_id)
  return _fulfill_with_chart_config(utterance, debug_logs)


#
# Given an utterance constructed either from a query or from dcids,
# fulfills it into charts.
#
def _fulfill_with_chart_config(utterance: nl_utterance.Utterance,
                               debug_logs: Dict) -> Dict:
  disaster_config = current_app.config['NL_DISASTER_CONFIG']
  if current_app.config['LOCAL']:
    # Reload configs for faster local iteration.
    disaster_config = get_nl_disaster_config()
  else:
    logging.info('Unable to load event configs!')

  cb_config = config_builder.Config(
      event_config=disaster_config,
      sv_chart_titles=current_app.config['NL_CHART_TITLES'],
      nopc_vars=current_app.config['NL_NOPC_VARS'])

  start = time.time()
  page_config_pb = fulfillment.fulfill_chart_config(utterance, cb_config)
  related_things = {
      'parentPlaces': [],
      'childPlaces': {},
      'parentTopics': {},
      'peerTopics': {},
  }
  utterance.counters.timeit('fulfillment', start)
  if page_config_pb:
    # Use the first chart's place as main place.
    main_place = utterance.places[0]
    page_config = json.loads(MessageToJson(page_config_pb))
    start = time.time()
    metadata = place_metadata(main_place.dcid,
                              get_child_places=True,
                              arg_place_type=main_place.place_type,
                              arg_place_name=main_place.name)
    if not metadata.is_error:
      related_things['parentPlaces'] = _trim_names(metadata.parent_places)
      related_things['childPlaces'] = _trim_names(metadata.child_places)
    utterance.counters.timeit('place_expansion', start)

    if utterance.svs:
      start = time.time()
      pt = topic.get_parent_topics(utterance.svs)
      related_things['parentTopics'] = pt
      pt = [p['dcid'] for p in pt]
      related_things['peerTopics'] = topic.get_child_topics(pt)
      utterance.counters.timeit('topic_expansion', start)

  else:
    page_config = {}
    utterance.place_source = nl_utterance.FulfillmentResult.UNRECOGNIZED
    main_place = Place(dcid='', name='', place_type='')
    logging.info('Found empty place for query "%s"',
                 utterance.detection.original_query)

  dbg_counters = utterance.counters.get()
  utterance.counters = None
  context_history = nl_utterance.save_utterance(utterance)

  data_dict = {
      'place': {
          'dcid': main_place.dcid,
          'name': main_place.name,
          'place_type': main_place.place_type,
      },
      'config': page_config,
      'context': context_history,
      'placeFallback': context_history[0]['placeFallback'],
      'svSource': utterance.sv_source.value,
      'placeSource': utterance.place_source.value,
      'pastSourceContext': utterance.past_source_context,
      'relatedThings': related_things,
  }
  status_str = "Successful"
  if utterance.rankedCharts:
    status_str = ""
  else:
    if not utterance.places:
      status_str += '**No Place Found**.'
    if not utterance.svs:
      status_str += '**No SVs Found**.'

  return helpers.prepare_response(data_dict,
                                  status_str,
                                  utterance.detection,
                                  dbg_counters,
                                  debug_logs,
                                  is_nl=False)


def _trim_names(places: List[Dict]) -> List[Dict]:

  # Helper to strip out suffixes.
  def _trim(l):
    r = []
    for s in [' County']:
      for p in l:
        if 'name' in p:
          p['name'] = p['name'].removesuffix(s)
        r.append(p)
    return r

  if isinstance(places, dict):
    result = {}
    for t, l in places.items():
      result[t] = _trim(l)
    return result
  else:
    return _trim(places)


#
# A topic may not often be the top-most result. In that case,
# we look for a topic for up to TOPIC_RANK_LIMIT, and hoist to top
# (This is the same limit NL interface uses for opening up topic).
#
def _hoist_topic(uttr):
  # If no SVs, or topic is already on top, return.
  if not uttr.svs or utils.is_topic(uttr.svs[0]):
    return
  for i in range(1, topic.TOPIC_RANK_LIMIT):
    if utils.is_topic(uttr.svs[i]):
      t = uttr.svs[0]
      uttr.svs[0] = uttr.svs[i]
      uttr.svs[i] = t
      return