/**
 * Copyright 2023 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/**
 * Component for the mapping section for the multiVarMultiDateCol template
 */

import _ from "lodash";
import React from "react";

import { MappingTemplateProps } from "../../templates";
import {
  MAPPED_THING_NAMES,
  MappedThing,
  MappingType,
  MappingVal,
} from "../../types";
import { MappingColumnInput } from "../shared/mapping_column_input";
import { MappingHeaderInput } from "../shared/mapping_header_input";
import { MappingPlaceInput } from "../shared/mapping_place_input";

export function MultiVarMultiDateCol(props: MappingTemplateProps): JSX.Element {
  return (
    <div id="multi-var-multi-date">
      <MappingColumnInput
        mappedThing={MappedThing.STAT_VAR}
        mappingVal={props.userMapping.get(MappedThing.STAT_VAR)}
        onMappingValUpdate={(mappingVal) =>
          props.onMappingValUpdated(MappedThing.STAT_VAR, mappingVal)
        }
        orderedColumns={props.csvData.orderedColumns}
        isRequired={true}
      />
      <MappingPlaceInput
        mappingType={MappingType.COLUMN}
        mappingVal={props.userMapping.get(MappedThing.PLACE)}
        onMappingValUpdate={(mappingVal: MappingVal) =>
          props.onMappingValUpdated(MappedThing.PLACE, mappingVal)
        }
        orderedColumns={props.csvData.orderedColumns}
      />
      <MappingHeaderInput
        mappedThingName={
          MAPPED_THING_NAMES[MappedThing.DATE] || MappedThing.DATE
        }
        mappingVal={props.userMapping.get(MappedThing.DATE)}
        onMappingValUpdate={(mappingVal: MappingVal) =>
          props.onMappingValUpdated(MappedThing.DATE, mappingVal)
        }
        orderedColumns={props.csvData.orderedColumns}
      />
      <MappingColumnInput
        mappedThing={MappedThing.UNIT}
        mappingVal={props.userMapping.get(MappedThing.UNIT)}
        onMappingValUpdate={(mappingVal) =>
          props.onMappingValUpdated(MappedThing.UNIT, mappingVal)
        }
        orderedColumns={props.csvData.orderedColumns}
        isRequired={false}
      />
    </div>
  );
}
