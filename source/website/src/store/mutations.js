/*
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
*/

export default {
  updateDatasetDefinition(state, value) {
    state.dataset_definition = value;
  },
  saveStep3FormInput(state, value) {
    state.step3_form_input = value;
  },
  updateS3key(state, value) {
    state.s3key = value;
  },
};
