import json
import os

import requests
from flask import current_app


def submit_form_directly(form_url, field_mapping, form_data):
  """
  Submit data to a public Google Form (without using Google Forms API).

  Args:
      form_url (str): The form's 'formResponse' URL.
      field_mapping (dict): Mapping of logical names to Google Form entry IDs.
          Example: {"name": "entry.123456", "email": "entry.654321"}
      form_data (dict): Data to be submitted.
          Example: {"name": "John", "email": "john@example.com"}

  Returns:
      Response object from the POST request.
  """
  payload = {}

  for key, value in form_data.items():
    if key in field_mapping:
      payload[field_mapping[key]] = value

  headers = {
    "Content-Type": "application/x-www-form-urlencoded"
  }

  try:
    response = requests.post(form_url, data=payload, headers=headers)
    response.raise_for_status()
    return response
  except requests.RequestException as e:
    raise RuntimeError(f"Form submission failed: {e}")


def get_field_mapping():
  mapping_str = os.getenv("FORM_FIELD_MAPPING_JSON")
  if not mapping_str:
    raise ValueError("FORM_FIELD_MAPPING_JSON not provided")
  try:
    return json.loads(mapping_str)
  except json.JSONDecodeError:
    raise ValueError("FORM_FIELD_MAPPING_JSON is not valid JSON")

def submit_to_google_form(email, first_name='', last_name='', organization='', is_subscribed=True):
  """
  Submit data to a Google Form.

  Args:
      email (str): Email of the user.
      first_name (str): First name of the user.
      last_name (str): Last name of the user.
      organization (str): Organization of the user.
      is_subscribed (bool): Subscription status.

  Returns:
      Response object from the POST request.
  """
  form_url = current_app.config["GOOGLE_FORM_URL"]

  if not form_url:
    raise ValueError("GOOGLE_FORM_URL not provided")

  if not email:
    raise ValueError("Email is required")

  if is_subscribed is True and not first_name and not last_name and not organization:
    raise ValueError("First name, last name, organization are required for subscription")

  if is_subscribed is False:
    first_name = first_name if first_name else ""
    last_name = last_name if last_name else ""
    organization = organization if organization else ""

  field_mapping = get_field_mapping()

  form_data = {
    "first_name": first_name,
    "last_name": last_name,
    "email": email,
    "organization": organization,
    "is_active": 'Yes' if is_subscribed else 'No',
  }

  return submit_form_directly(form_url, field_mapping, form_data)