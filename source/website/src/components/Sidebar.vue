/*
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
*/

<template>
  <div>
    <b-row class="my-1">
      <b-col>
        Step 1
        <b-link :to="'/' + TARGET_PLATFORM + 'step1'" :active="isStep1Active">
          <br />
          Select file
        </b-link>
        <hr />
        Step 2
        <b-link :to="'/' + TARGET_PLATFORM + 'step2'" :active="isStep2Active">
          <br />
          Define dataset
        </b-link>
        <hr />
        Step 3
        <b-link
          :to="'/' + TARGET_PLATFORM + 'step3'"
          :class="{ active: isStep3Active }"
        >
          <br />
          Define columns
        </b-link>
        <hr />
        Step 4
        <b-link
          :to="'/' + TARGET_PLATFORM + 'step4'"
          :class="{ active: isStep4Active }"
        >
          <br />
          Confirm details
        </b-link>
        <hr />
        Step5
        <b-link
          :to="'/' + TARGET_PLATFORM + 'step5'"
          :class="{ active: isStep5Active }"
        >
          <br />
          Monitor upload
        </b-link>
        <hr />
      </b-col>
    </b-row>
  </div>
</template>

<script>
export default {
  name: "Sidebar",
  props: [
    "isStep1Active",
    "isStep2Active",
    "isStep3Active",
    "isStep4Active",
    "isStep5Active",
  ],
};
</script>

<style>
a.active {
  color: black;
}
</style>
