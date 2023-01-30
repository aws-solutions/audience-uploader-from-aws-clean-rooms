/*
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
*/

<template>
  <div>
    <div class="headerTextBackground">
      <Header />
      <b-container fluid>
        <b-alert v-model="showFormError" variant="danger" dismissible>
          Form input is incomplete. {{ formErrorMessage }}
        </b-alert>
        <b-row style="text-align: left">
          <b-col cols="2">
            <Sidebar :is-step2-active="true" />
          </b-col>
          <b-col cols="10">
            <h3>Define Dataset</h3>
            Specify the following details for the dataset.
            <br />
            <br />
            <div>
              <b-form-group
                id="bucket"
                label-cols-lg="1"
                label-align-lg="left"
                content-cols-lg="9"
                label="Bucket:"
                label-for="bucket"
              >
                <b-form-input
                  id="bucket"
                  plaintext
                  :placeholder="bucket"
                ></b-form-input>
              </b-form-group>
              <b-form-group
                id="selected-file-field"
                label-cols-lg="1"
                label-align-lg="left"
                content-cols-lg="5"
                label="Key:"
                label-for="s3key"
              >
                <b-form-input
                  id="s3key"
                  v-model="new_s3key"
                  @change="updateS3key"
                ></b-form-input>
              </b-form-group>
              <b-form-group
                id="segment-name-field"
                label-cols-lg="1"
                label-align-lg="left"
                content-cols-lg="5"
                description="Name of audience/segment group being targeted."
                label="Segment name:"
                label-for="segment-name-input"
              >
                <b-form-input
                  id="segment-name-input"
                  v-model="segment_name"
                ></b-form-input>
              </b-form-group>
            </div>
            <b-row>
              <b-col sm="9" align="right">
                <button
                  type="submit"
                  class="btn btn-outline-primary mb-2"
                  @click="$router.push(TARGET_PLATFORM + 'Step1')"
                >
                  Previous
                </button>
                &nbsp;
                <button
                  type="submit"
                  class="btn btn-primary mb-2"
                  @click="onSubmit"
                >
                  Next
                </button>
              </b-col>
            </b-row>
          </b-col>
        </b-row>
      </b-container>
    </div>
  </div>
</template>

<script>
import Header from "@/components/Header.vue";
import Sidebar from "@/components/Sidebar.vue";
import { mapState } from "vuex";

export default {
  name: "snapStep2",
  components: {
    Header,
    Sidebar,
  },
  data() {
    return {
      new_s3key: "",
      new_dataset_definition: {},
      segment_name: "",
      file_format: "JSON",
      isStep2Active: true,
      file_format_options: ["CSV", "JSON"],
      showFormError: false,
      formErrorMessage: "",
    };
  },
  computed: {
    ...mapState(["dataset_definition", "s3key"]),
    bucket() {
      return "s3://" + this.DATA_BUCKET_NAME;
    },
  },
  deactivated: function () {
    console.log("deactivated");
  },
  activated: function () {
    console.log("activated");
  },
  created: function () {
    console.log("created");
  },
  mounted: function () {
    this.new_s3key = this.s3key;
    this.new_dataset_definition = this.dataset_definition;
    this.segment_name = this.new_dataset_definition["segmentName"];
    this.file_format = "JSON";
  },
  methods: {
    updateS3key() {
      console.log("snapStep2 changing s3key to " + this.new_s3key);
      this.$store.commit("updateS3key", this.new_s3key);
    },
    onSubmit() {
      this.showFormError = false;
      this.new_dataset_definition["segmentName"] = this.segment_name;
      this.new_dataset_definition["fileFormat"] = this.file_format;
      this.new_dataset_definition["compressionFormat"] = "GZIP";
      if (!this.validForm()) {
        this.showFormError = true;
      } else {
        this.$store.commit(
          "updateDatasetDefinition",
          this.new_dataset_definition
        );
        this.$router.push(this.TARGET_PLATFORM + "Step3");
      }
    },
    validForm() {
      if (!this.s3key && !this.new_s3key) {
        this.formErrorMessage = "Missing s3key.";
        return false;
      }
      if (
        !this.new_dataset_definition["segmentName"] ||
        this.new_dataset_definition["segmentName"].length === 0
      ) {
        this.formErrorMessage = "Missing segmentName.";
        return false;
      }
      return true;
    },
  },
};
</script>