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
"""Fine Tune the base model."""

from datetime import datetime
import glob
import os
import time
from typing import Any, List

from absl import app
from absl import flags
from google.cloud import storage
import gspread
import pandas as pd
from sentence_transformers import InputExample
from sentence_transformers import losses
from sentence_transformers import SentenceTransformer
from torch.utils.data import DataLoader
import utils

FLAGS = flags.FLAGS

flags.DEFINE_string('model_name_v2', 'all-MiniLM-L6-v2', 'Model name')
flags.DEFINE_string('bucket_name_v2', 'datcom-nl-models', 'Storage bucket')
flags.DEFINE_string(
    'start_from', 'base',
    'Valid values are: "base", "intermediate". Determines what model to start finetuning from.'
)
flags.DEFINE_string(
    'generate', '',
    'Valid values are: "intermediate", "final", "all". Determines what stages to generate. "All" generates both intermediate and final.'
)
flags.DEFINE_string(
    'pretuned_model', '',
    'The versioned model folder name on GCS for the Final model which has already been finetuned.'
)

flags.DEFINE_string(
    'autogen_input_basedir', 'data/autogen_input',
    'Base path for CSVs with autogenerated SVs with name and description. '
    'The actual path is `{--autogen_input_base}/{medium}/*.csv`.')

flags.DEFINE_string('alternatives_filepattern', 'data/alternatives/*.csv',
                    'File pattern (relative) for CSVs with alternatives')

flags.DEFINE_string('sentence_pairs_filepath',
                    'data/finetuning/sentence_pairs.csv',
                    'File path for sentence pairs CSV')

START_FROM_BASE = "base"
START_FROM_INTERMEDIATE = "intermediate"

GENERATE_ALL = "all"
GENERATE_INTERMEDIATE = "intermediate"
GENERATE_FINAL = "final"

# Use the Medium embeddings size for the larger training set.
EMBEDDINGS_SIZE = "medium"

# Batch size determines the number of examples used together in a batch for
# training. This can help speed up training time.
BATCH_SIZE = 256

# The params below are described in https://www.sbert.net/docs/package_reference/SentenceTransformer.html
# Increasing NUM_EPOCHS can theoretically lead to better convergence of the estimated weights but
# using 10 should be Ok.
NUM_WARMUP_STEPS = 10
NUM_EPOCHS = 10

VERY_HIGH_MATCH_SCORE = 0.95
HIGH_MATCH_SCORE = 0.90
MEDIUM_HIGH_MATCH_SCORE = 0.85


def _upload_to_gcs(ctx: utils.Context,
                   gcs_path: str,
                   local_filepath: str,
                   empty_folder: bool = False) -> None:
  print(f'Uploading {local_filepath}')
  blob = ctx.bucket.blob(gcs_path)

  if empty_folder:
    blob.upload_from_string(
        '', content_type='application/x-www-form-urlencoded;charset=UTF-8')
  else:
    blob.upload_from_filename(local_filepath)
  print(f'Path in GCS: {gcs_path}')


def _make_gcs_model_folder(stage: str, base_model_name: str) -> str:
  now = datetime.now()

  month_str = utils.two_digits(now.month)
  day_str = utils.two_digits(now.day)
  hour_str = utils.two_digits(now.hour)
  minute_str = utils.two_digits(now.minute)
  second_str = utils.two_digits(now.second)

  prefix = f"ft_{stage}_v{now.year}{month_str}{day_str}{hour_str}{minute_str}{second_str}"
  if base_model_name:
    return f"{prefix}.{base_model_name}"
  else:
    return prefix


def _alternatives(autogen_input_filepattern: str,
                  alternatives_filepattern: str) -> pd.DataFrame:

  df_svs = pd.DataFrame()
  # Append autogen CSVs if any.
  autogen_dfs = []
  for autogen_csv in sorted(glob.glob(autogen_input_filepattern)):
    print(f'Processing autogen input file: {autogen_csv}')
    autogen_dfs.append(pd.read_csv(autogen_csv).fillna(""))
  if autogen_dfs:
    df_svs = pd.concat(autogen_dfs)
    df_svs = df_svs.drop_duplicates(subset=utils.DCID_COL)

  # Get alternatives and add to the dataframe.
  for alt_fp in sorted(glob.glob(alternatives_filepattern)):
    df_alts = utils.get_local_alternatives(
        alt_fp, [utils.DCID_COL, utils.ALTERNATIVES_COL])
    df_svs = utils.merge_dataframes(df_svs, df_alts)

  return df_svs


def _save_finetuned_model(ctx: utils.Context, stage: str,
                          model_name: str) -> str:
  gcs_model_folder = _make_gcs_model_folder(stage, model_name)
  gcs_tmp_out_path = os.path.join(ctx.tmp, gcs_model_folder)

  print(f"Saving finetuned model locally to {gcs_tmp_out_path}")
  ctx.model.save(gcs_tmp_out_path)

  print("Attempting to write to GCS")
  print(f"\t GCS Path: gs://{FLAGS.bucket_name_v2}/{gcs_model_folder}/")
  # To upload the model directory, we need to traverse the files and folders.
  for str_path in glob.glob(f"{gcs_tmp_out_path}/**"):
    # Check if str_path is a folder.
    if os.path.isdir(str_path):
      if not glob.glob(f"{str_path}/**"):
        # This means we found an empty folder.
        foldername = os.path.basename(str_path)
        gcs_path = gcs_model_folder + "/" + foldername + "/"
        print(f'Path in GCS: {gcs_path}')
        _upload_to_gcs(ctx, gcs_path, str_path, empty_folder=True)

      for filepath in glob.glob(f"{str_path}/**"):
        # Found files under a folder.
        filename = filepath.split(gcs_tmp_out_path)[1]
        gcs_path = gcs_model_folder + filename
        _upload_to_gcs(ctx, gcs_path, filepath)
    else:
      # Just files under the main model folder.
      foldername = os.path.basename(str_path)
      gcs_path = gcs_model_folder + "/" + foldername
      _upload_to_gcs(ctx, gcs_path, str_path)

  print("Done uploading to GCS.")
  print(f"\t Finetuned Model Filename: {gcs_model_folder}")

  return gcs_model_folder


def _generate_training_examples_from_sentence_pairs(
    df_sentence_pairs: pd.DataFrame) -> List[InputExample]:
  """Transform `df_sentence_pairs` (text pairs with approx similarity scores) to
  produce a list of training examples (text pairs and scores). We use the provided
  similarity scores/labels without any edits.
  """
  training_examples: List[InputExample] = []

  # Add the manual sentence pairs (which are assumed to have the scores).
  for _, row in df_sentence_pairs.iterrows():
    assert "sentence_1" in row
    assert "sentence_2" in row
    assert float(row["score"])
    training_examples.append(
        InputExample(texts=[row["sentence_1"], row["sentence_2"]],
                     label=row["score"]))

  return training_examples


def _generate_training_examples_from_alternatives(
    df_svs: pd.DataFrame) -> List[InputExample]:
  """Use `df_svs` (alternatives) to produce a list of training examples (text pairs and scores).
  Using the StatVar name, description and alternatives (human curated and LLM-generated) in `df_svs` we create pairs
  of sentences/text with high similarity scores`.
  """
  training_examples: List[InputExample] = []
  # Iterate over SV Names, Descriptions and Alternatives to produce
  # pairs of texts which we want to associated with each other in
  # terms of similarity.
  for _, row in df_svs.iterrows():
    name = row[utils.NAME_COL]
    descriptions = row[utils.DESCRIPTION_COL].split(";")
    desc = descriptions[0]

    if not name and not desc:
      continue
    if ((not name) and desc):
      name = desc
    elif ((not desc) and name):
      desc = name

    curated = row[utils.CURATED_ALTERNATIVES_COL].split(";")
    palm_alts = row[utils.ALTERNATIVES_COL].split(";")

    # Pair name and description with very high score.
    if name != desc:
      training_examples.append(
          InputExample(texts=[name, desc], label=VERY_HIGH_MATCH_SCORE))

    # If there are more descriptions, pair them with the name as well.
    if len(descriptions) > 1:
      for i in range(1, len(descriptions)):
        if descriptions[i]:
          training_examples.append(
              InputExample(texts=[name, descriptions[i]],
                           label=HIGH_MATCH_SCORE))

    for c in curated:
      # All all curated alternatives as pairs with the description.
      if c:
        training_examples.append(
            InputExample(texts=[desc, c], label=VERY_HIGH_MATCH_SCORE))

    for p in palm_alts:
      if p:
        # High match score but since these are auto-generated, keep the score lower
        # than for the manual/curated cases.
        training_examples.append(
            InputExample(texts=[name, p], label=MEDIUM_HIGH_MATCH_SCORE))

  return training_examples


def finetune_model(model: Any, training_examples: List[InputExample]):
  """Fine tuning involves providing pairs of sentences/text with an
  approximate similar score to a baseline model. These pairs (and scores)
  are used for further `training` (with CosineSimilarityLoss as the objecive).
  The end result is that the baseline model's weights get updated based on
  the `new` training examples (pairs).
  Effectively, the training examples (pairs and scores) provide additional
  context to a baseline model about the kinds of associations between
  sentences/text that we care about.
  """
  # Setting shuffle to True to ensure the training examples are not always provided
  # in the same manner for each epoch.
  train_dataloader = DataLoader(training_examples,
                                shuffle=True,
                                batch_size=BATCH_SIZE)
  t = time.time()
  model.fit(train_objectives=[(train_dataloader,
                               losses.CosineSimilarityLoss(model=model))],
            epochs=NUM_EPOCHS,
            warmup_steps=NUM_WARMUP_STEPS)
  t = time.time() - t
  print(f"Time taken = {t}")
  return model


def main(_):

  assert FLAGS.model_name_v2 and FLAGS.bucket_name_v2
  assert FLAGS.start_from in [START_FROM_BASE, START_FROM_INTERMEDIATE]
  assert FLAGS.generate in [GENERATE_ALL, GENERATE_INTERMEDIATE, GENERATE_FINAL]

  if FLAGS.start_from == START_FROM_INTERMEDIATE and FLAGS.generate != GENERATE_FINAL:
    print(
        "Unsupported mode: if start_from == intermediate, then generate must be final."
    )
    exit(1)

  assert os.path.exists(os.path.join('data'))

  # Determine whether to start with an intermediate model.
  start_intermediate = False
  if FLAGS.start_from == START_FROM_INTERMEDIATE and FLAGS.pretuned_model:
    start_intermediate = True

  # Determine if the intermediate model needs to be built.
  build_intermediate = False
  if FLAGS.generate in [GENERATE_INTERMEDIATE, GENERATE_ALL]:
    build_intermediate = True

  autogen_input_filepattern = f'{FLAGS.autogen_input_basedir}/{EMBEDDINGS_SIZE}/*.csv'

  gs = gspread.oauth()
  sc = storage.Client()
  bucket = sc.bucket(FLAGS.bucket_name_v2)

  # Step 0. Gather the sentence/text alternatives and load the base model.
  print("Gathering the training sentence/text pairs.")
  df_svs = _alternatives(autogen_input_filepattern,
                         FLAGS.alternatives_filepattern)
  df_sentence_pairs = pd.read_csv(FLAGS.sentence_pairs_filepath).fillna("")
  print(f"Found {len(df_svs)} rows in the alternatives dataframe.")
  print(
      f"Found {len(df_sentence_pairs)} human-curated sentence pairs with scores."
  )

  if build_intermediate:
    # Build the Intermediate finetuned model using sentence/text alternatives.
    # Checkpoint (save/upload) that model to GCS.

    # Step 1. Loading the base model.
    print(f"Loading the base model: {FLAGS.model_name_v2}")
    model_base = SentenceTransformer(FLAGS.model_name_v2)

    # Step 2a. Fine tuning with alternatives.
    print(f"(Intermediate) Fine tuning with alternatives. Stage: {FLAGS.stage}")
    model_intermediate = finetune_model(
        model_base, _generate_training_examples_from_alternatives(df_svs))

    ctx = utils.Context(gs=gs,
                        model=model_intermediate,
                        bucket=bucket,
                        tmp='/tmp')

    # Step 2b. Upload the alternatives finetuned model to the NL model server's GCS bucket.
    model_intermediate_name = _save_finetuned_model(ctx, "intermediate",
                                                    FLAGS.model_name_v2)
    print(
        f"Produced and uploaded finetuned intermediate model: {model_intermediate_name}"
    )

  elif start_intermediate:
    # If a pretuned (intermediate) model was provided, use it to download and load
    # the intermediate model.

    # Step 1. Loading the Intermediate pre-finetuned model.
    # No need for Steps 2a and 2b (see above).
    model_intermediate_name = FLAGS.pretuned_model

    print(f"Using the intermediate model (on GCS): {model_intermediate_name}")
    assert "." in model_intermediate_name
    assert GENERATE_INTERMEDIATE in model_intermediate_name
    assert GENERATE_FINAL not in model_intermediate_name

    print(
        f"Loading the pre-finetuned Intermediate model: {model_intermediate_name}"
    )
    ctx = utils.Context(gs=gs, model=None, bucket=bucket, tmp='/tmp')
    downloaded_model_path = utils.download_model_from_gcs(
        ctx, model_intermediate_name)
    model_intermediate = SentenceTransformer(downloaded_model_path)

  else:
    # The intermediate model is the base model.
    # Note that in this case, there is no "intermediate" finetuning using
    # the sentence alternatives. The next step (finetuning with sentence pairs)
    # will use the base model and do the "final" finetuning step.
    model_intermediate = SentenceTransformer(FLAGS.model_name_v2)
    model_intermediate_name = FLAGS.model_name_v2

  # Step 3. Fine tuning with sentence pairs.
  print(f"Fine tuning with sentence pairs.")
  model_final_finetuned = finetune_model(
      model_intermediate,
      _generate_training_examples_from_sentence_pairs(df_sentence_pairs))

  # Step 4. Upload the final finetuned model to the NL model server's GCS bucket.
  ctx = utils.Context(gs=gs,
                      model=model_final_finetuned,
                      bucket=bucket,
                      tmp='/tmp')
  model_final_folder_name = _save_finetuned_model(ctx, "final",
                                                  model_intermediate_name)
  print(
      f"NOTE: Please update `tuned_model` in models.yaml with:: {model_final_folder_name}"
  )


if __name__ == "__main__":
  app.run(main)
