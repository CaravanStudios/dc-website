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
"""Build the embeddings index by concatenating various inputs."""

# TODO: Consider adding the model name to the embeddings file for downstream
# validation.

import csv
import datetime as datetime
import glob
import os
from typing import Dict, List

from absl import app
from absl import flags
from google.cloud import storage
import gspread
import pandas as pd
from sentence_transformers import SentenceTransformer
import utils

FLAGS = flags.FLAGS

# TODO: use only one flag from the two below and "gcs://" prefix to differentiate
# between local and GCS path.
flags.DEFINE_string('finetuned_model_gcs', '',
                    'Existing finetuned model folder name on GCS')
flags.DEFINE_string('existing_model_path', '',
                    'Path to an existing model (local)')
flags.DEFINE_string('model_name_v2', 'all-MiniLM-L6-v2', 'Model name')
flags.DEFINE_string('bucket_name_v2', 'datcom-nl-models', 'Storage bucket')
flags.DEFINE_string('embeddings_size', '', 'Embeddings size')

flags.DEFINE_string('local_sheets_csv_filepath',
                    'data/curated_input/sheets_svs.csv',
                    'Local Sheets csv (relative) file path')
flags.DEFINE_string(
    'sheets_url',
    'https://docs.google.com/spreadsheets/d/1-QPDWqD131LcDTZ4y_nnqllh66W010HDdows1phyneU',
    'Google Sheets Url for the latest SVs')
flags.DEFINE_list(
    'worksheet_names', ['Demo_SVs', 'SDG_GOALS_INDICATORS_ONLY'],
    'List of names of worksheets in the Google Sheets file to use')

flags.DEFINE_string(
    'autogen_input_basedir', 'data/autogen_input',
    'Base path for CSVs with autogenerated SVs with name and description. '
    'The actual path is `{--autogen_input_base}/{--embeddings_size}/*.csv`.')

flags.DEFINE_string('alternatives_filepattern', 'data/alternatives/*.csv',
                    'File pattern (relative) for CSVs with alternatives')

#
# curated_input/ + autogen_input/ + alternatives/ => preindex/ => embeddings
#

# Setting to a very high number right for now.
MAX_ALTERNATIVES_LIMIT = 50


def _make_gcs_embeddings_filename(embeddings_size: str,
                                  model_version: str) -> str:
  now = datetime.datetime.now()

  month_str = utils.two_digits(now.month)
  day_str = utils.two_digits(now.day)
  hour_str = utils.two_digits(now.hour)
  minute_str = utils.two_digits(now.minute)
  second_str = utils.two_digits(now.second)

  return f"embeddings_{embeddings_size}_{now.year}_{month_str}_{day_str}_{hour_str}_{minute_str}_{second_str}.{model_version}.csv"


def _build_embeddings(ctx, texts: List[str], dcids: List[str]) -> pd.DataFrame:
  assert len(texts) == len(dcids)

  embeddings = ctx.model.encode(texts, show_progress_bar=True)
  embeddings = pd.DataFrame(embeddings)
  embeddings[utils.DCID_COL] = dcids
  embeddings[utils.COL_ALTERNATIVES] = texts
  return embeddings


def _validateEmbeddings(embeddings_df: pd.DataFrame,
                        output_dcid_sentences_filepath: str) -> None:
  # Verify that embeddings were created for all DCIDs and Sentences.
  dcid_sentence_df = pd.read_csv(output_dcid_sentences_filepath).fillna("")
  sentences = set()
  for alts in dcid_sentence_df["sentence"].values:
    for s in alts.split(";"):
      s = s.strip()
      if not s:
        continue
      sentences.add(s)

  # Verify that each of the texts in the embeddings_df is in the sentences set
  # and that all the sentences in the set are in the embeddings_df. Finally, also
  # verify that embeddings_df has no duplicate sentences.
  embeddings_sentences = embeddings_df['sentence'].values
  embeddings_sentences_unique = set()
  for s in embeddings_sentences:
    assert s in sentences, f"Embeddings sentence not found in processed output file. Sentence: {s}"
    assert s not in embeddings_sentences_unique, f"Found multiple instances of sentence in embeddings. Sentence: {s}."
    embeddings_sentences_unique.add(s)

  for s in sentences:
    assert s in embeddings_sentences_unique, f"Output File sentence not found in Embeddings. Sentence: {s}"

  # Verify that the number of columns = length of the embeddings vector + one each for the
  # dcid and sentence columns.
  assert len(embeddings_df.columns), 384 + 2


def get_sheets_data(ctx, sheets_url: str, worksheet_name: str) -> pd.DataFrame:
  sheet = ctx.gs.open_by_url(sheets_url).worksheet(worksheet_name)
  df = pd.DataFrame(sheet.get_all_records()).fillna("")
  return df


def _write_intermediate_output(name2sv_dict: Dict[str, str],
                               dup_sv_rows: List[List[str]],
                               local_merged_filepath: str,
                               dup_names_filepath: str) -> None:
  sv2names = {}
  for name, sv in name2sv_dict.items():
    if sv not in sv2names:
      sv2names[sv] = []
    sv2names[sv].append(name)

  sv_list = sorted(list(sv2names.keys()))
  name_list = [';'.join(sorted(sv2names[v])) for v in sv_list]

  # Write to local_merged_filepath.
  print(
      f"Writing the concatenated dataframe after merging alternates to local file: {local_merged_filepath}"
  )
  df_svs = pd.DataFrame({'dcid': sv_list, 'sentence': name_list})
  df_svs.to_csv(local_merged_filepath, index=False)

  if dup_names_filepath:
    print(f"Writing duplicate names file: {dup_names_filepath}")
    with open(dup_names_filepath, 'w') as f:
      csv.writer(f).writerows(dup_sv_rows)


def get_embeddings(ctx, df_svs: pd.DataFrame, local_merged_filepath: str,
                   dup_names_filepath: str) -> pd.DataFrame:
  print(f"Concatenate all alternative sentences for descriptions.")
  alternate_descriptions = []
  for _, row in df_svs.iterrows():
    alternatives = []
    if row[utils.OVERRIDE_COL]:
      # Override takes precendence over everything else.
      alternatives += utils.split_alt_string(row[utils.OVERRIDE_COL])
    else:
      for col_name in [
          utils.NAME_COL,
          utils.DESCRIPTION_COL,
          utils.CURATED_ALTERNATIVES_COL,
          utils.ALTERNATIVES_COL,
      ]:
        # In order of preference, traverse the various alternative descriptions.
        alternatives += utils.split_alt_string(row[col_name])

    alt_str = utils.concat_alternatives(alternatives, MAX_ALTERNATIVES_LIMIT)
    alternate_descriptions.append(alt_str)

  assert len(df_svs) == len(alternate_descriptions)
  df_svs[utils.COL_ALTERNATIVES] = alternate_descriptions
  # Trim df
  df_svs = df_svs[[utils.DCID_COL, utils.COL_ALTERNATIVES]]

  # Dedupe texts
  (name2sv_dict, dup_sv_rows) = utils.dedup_texts(df_svs)

  # Write dcid -> texts and dups to intermediate files.
  _write_intermediate_output(name2sv_dict, dup_sv_rows, local_merged_filepath,
                             dup_names_filepath)

  print("Getting texts, dcids and embeddings.")
  (texts, dcids) = utils.get_texts_dcids(name2sv_dict)

  print("Building embeddings")
  return _build_embeddings(ctx, texts, dcids)


def build(ctx, sheets_url: str, worksheet_names: List[str],
          local_sheets_csv_filepath: str, local_merged_filepath: str,
          dup_names_filepath: str, autogen_input_filepattern: str,
          alternative_filepattern: str) -> pd.DataFrame:
  worksheet_df_list = list()
  # First download the latest files from sheets.
  for worksheet_name in worksheet_names:
    print(
        f"Downloading the latest sheets data from: {sheets_url} (worksheet: {worksheet_name})"
    )
    worksheet_df = get_sheets_data(ctx, sheets_url, worksheet_name)
    worksheet_df_list.append(worksheet_df)
    print(
        f"Downloaded {len(worksheet_df)} rows and {len(worksheet_df.columns)} columns."
    )

  # Merge the downloaded files into one dataframe and write it to local.
  print(f"Writing the dataframe to local at: {local_sheets_csv_filepath}")
  df_svs = pd.concat(worksheet_df_list, join="inner")
  df_svs.to_csv(local_sheets_csv_filepath, index=False)

  # Append autogen CSVs if any.
  autogen_dfs = []
  for autogen_csv in sorted(glob.glob(autogen_input_filepattern)):
    print(f'Processing autogen input file: {autogen_csv}')
    autogen_dfs.append(pd.read_csv(autogen_csv).fillna(""))
  if autogen_dfs:
    df_svs = pd.concat([df_svs] + autogen_dfs)
    df_svs = df_svs.drop_duplicates(subset=utils.DCID_COL)

  # Get alternatives and add to the dataframe.
  for alt_fp in sorted(glob.glob(alternative_filepattern)):
    df_alts = utils.get_local_alternatives(
        alt_fp, [utils.DCID_COL, utils.ALTERNATIVES_COL])
    df_svs = utils.merge_dataframes(df_svs, df_alts)

  return get_embeddings(ctx, df_svs, local_merged_filepath, dup_names_filepath)


def main(_):
  assert FLAGS.model_name_v2 and FLAGS.bucket_name_v2 and FLAGS.local_sheets_csv_filepath and FLAGS.sheets_url and FLAGS.worksheet_names

  assert os.path.exists(os.path.join('data'))

  if FLAGS.existing_model_path:
    assert os.path.exists(FLAGS.existing_model_path)

  use_finetuned_model = False
  use_local_model = False
  model_version = FLAGS.model_name_v2
  if FLAGS.finetuned_model_gcs:
    use_finetuned_model = True
    model_version = FLAGS.finetuned_model_gcs
  elif FLAGS.existing_model_path:
    use_local_model = True
    model_version = os.path.basename(FLAGS.existing_model_path)

  if not os.path.exists(os.path.join('data', 'preindex',
                                     FLAGS.embeddings_size)):
    os.mkdir(os.path.join('data', 'preindex', FLAGS.embeddings_size))
  local_merged_filepath = f'data/preindex/{FLAGS.embeddings_size}/sv_descriptions.csv'
  dup_names_filepath = f'data/preindex/{FLAGS.embeddings_size}/duplicate_names.csv'

  if not os.path.exists(
      os.path.join(FLAGS.autogen_input_basedir, FLAGS.embeddings_size)):
    os.mkdir(os.path.join(FLAGS.autogen_input_basedir, FLAGS.embeddings_size))
  autogen_input_filepattern = f'{FLAGS.autogen_input_basedir}/{FLAGS.embeddings_size}/*.csv'

  gs = gspread.oauth()
  sc = storage.Client()
  bucket = sc.bucket(FLAGS.bucket_name_v2)

  if use_finetuned_model:
    ctx_no_model = utils.Context(gs=gs, model=None, bucket=bucket, tmp='/tmp')

    # Check if this model is already downloaded locally.
    if os.path.exists(os.path.join(ctx_no_model.tmp, model_version)):
      tuned_model_path = os.path.join(ctx_no_model.tmp, model_version)
      print(f"Model already downloaded at path: {tuned_model_path}")
    else:
      print("Model not previously downloaded locally. Downloading from GCS.")
      tuned_model_path = utils.download_model_from_gcs(ctx_no_model,
                                                       model_version)
      print(f"Model downloaded locally to: {tuned_model_path}")

    model = SentenceTransformer(tuned_model_path)

  elif use_local_model:
    print(f"Use the local model at: {FLAGS.existing_model_path}")
    print(f"Extracted model version: {model_version}")
    model = SentenceTransformer(FLAGS.existing_model_path)

  else:
    model = SentenceTransformer(FLAGS.model_name_v2)

  ctx = utils.Context(gs=gs, model=model, bucket=bucket, tmp='/tmp')

  gcs_embeddings_filename = _make_gcs_embeddings_filename(
      FLAGS.embeddings_size, model_version)
  gcs_tmp_out_path = os.path.join(ctx.tmp, gcs_embeddings_filename)

  # Process all the data, produce the final dataframes, build the embeddings and return the embeddings dataframe.
  # During this process, the downloaded latest SVs and Descriptions data and the
  # final dataframe with SVs and Alternates are also written to local_merged_dir.
  embeddings_df = build(ctx, FLAGS.sheets_url, FLAGS.worksheet_names,
                        FLAGS.local_sheets_csv_filepath, local_merged_filepath,
                        dup_names_filepath, autogen_input_filepattern,
                        FLAGS.alternatives_filepattern)

  print(f"Saving locally to {gcs_tmp_out_path}")
  embeddings_df.to_csv(gcs_tmp_out_path, index=False)

  # Before uploading embeddings to GCS, validate them.
  print("Validating the built embeddings.")
  _validateEmbeddings(embeddings_df, local_merged_filepath)
  print("Embeddings DataFrame is validated.")

  # Finally, upload to the NL embeddings server's GCS bucket
  print("Attempting to write to GCS")
  print(f"\t GCS Path: gs://{FLAGS.bucket_name_v2}/{gcs_embeddings_filename}")
  blob = ctx.bucket.blob(gcs_embeddings_filename)
  # Since the files can be fairly large, use a 10min timeout to be safe.
  blob.upload_from_filename(gcs_tmp_out_path, timeout=600)
  print("Done uploading to gcs.")
  print(f"\t Embeddings Filename: {gcs_embeddings_filename}")
  print("\nNOTE: Please update embeddings.yaml with the Embeddings Filename")


if __name__ == "__main__":
  app.run(main)
