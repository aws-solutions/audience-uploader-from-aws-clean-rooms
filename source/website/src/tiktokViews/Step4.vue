/*
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
*/

<template>
  <div>
    <div class="headerTextBackground">
      <Header />
      <b-modal v-model="showModal" :title="modal_title" ok-only @ok="hideModal">
        {{ response }}
      </b-modal>
      <b-container fluid>
        <b-row style="text-align: left">
          <b-col cols="2">
            <Sidebar :is-step4-active="true" />
          </b-col>
          <b-col cols="10">
            <h3>Confirm Details</h3>
            <b-row>
              <b-col sm="7">
                Click Submit to push this dataset to {{ this.TARGET_PLATFORM }}.
              </b-col>
              <b-col sm="3" align="right">
                <button
                  type="submit"
                  class="btn btn-outline-primary mb-2"
                  @click="$router.push(TARGET_PLATFORM + 'Step3')"
                >
                  Previous
                </button>
                &nbsp;
                <button
                  type="submit"
                  class="btn btn-primary mb-2"
                  @click="onSubmit"
                >
                  Submit
                  <b-spinner
                    v-if="isBusy"
                    style="vertical-align: sub"
                    small
                    label="Spinning"
                  ></b-spinner>
                </button>
              </b-col>
            </b-row>
            <b-row>
              <b-col cols="7">
                <h5>Input file:</h5>
                {{ "s3://" + this.DATA_BUCKET_NAME + "/" + this.s3key }}
                <br />
                <br />
                <h5>Dataset Attributes:</h5>
                <b-table
                  small
                  outlined
                  :items="dataset.other_attributes"
                  thead-class="hidden_header"
                  show-empty
                >
                </b-table>
                <template #empty="scope">
                  {{ scope.emptyText }}
                </template>
              </b-col>
            </b-row>
            <b-row>
              <b-col cols="10">
                <h5>Columns:</h5>
                <b-table
                  v-if="dataset.columns && dataset.columns.length > 0"
                  small
                  outlined
                  :fields="column_fields"
                  :items="dataset.columns"
                >
                </b-table>
                <b-table
                  v-else
                  small
                  outlined
                  :items="dataset.columns"
                  show-empty
                ></b-table>
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
  name: "tiktokStep4",
  components: {
    Header,
    Sidebar,
  },
  data() {
    return {
      column_fields: [
        "name",
        "dataType",
        "columnType",
        "externalUserIdType.identifierType",
      ],
      dataset_fields: [
        { key: "0", label: "Name" },
        { key: "1", label: "Value" },
      ],
      isBusy: false,
      showModal: false,
      modal_title: "",
      isStep4Active: true,
      response: "",
    };
  },
  computed: {
    ...mapState(["dataset_definition", "s3key"]),
    pii_fields() {
      return this.dataset.columns
        .filter((x) => x.externalUserIdType)
        .map(
          (x) =>
            new Object({
              column_name: x.name,
              pii_type: x.externalUserIdType.identifierType,
            })
        );
    },
    dataset() {
      let { columns, ...other_attributes } = this.dataset_definition;
      return {
        columns: columns,
        other_attributes: Object.entries(other_attributes),
      };
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
  methods: {
    hideModal() {
      this.showModal = false;
    },
    onSubmit() {
      this.send_request(
        "POST",
        "start_" + this.TARGET_PLATFORM + "_transformation"
      );
      console.log("tiktokStep4 submitted");
    },
    async send_request(method, resource) {
      const apiName = "audience-uploader-from-aws-clean-rooms";
      let response = "";
      this.isBusy = true;
      try {
        // Start Glue ETL job
        console.log(
          "Starting Glue ETL job for s3://" +
            this.DATA_BUCKET_NAME +
            "/" +
            this.s3key
        );
        const data = {
          sourceBucket: this.DATA_BUCKET_NAME,
          sourceKey: this.s3key,
          outputBucket: this.ARTIFACT_BUCKET_NAME,
          piiFields: JSON.stringify(this.pii_fields),
          segmentName: this.dataset_definition.segmentName,
        };
        let requestOpts = {
          headers: { "Content-Type": "application/json" },
          body: data,
        };
        console.log("POST " + resource + " " + JSON.stringify(requestOpts));
        response = await this.$Amplify.API.post(apiName, resource, requestOpts);
        console.log(JSON.stringify(response));
        console.log("Started Glue ETL job");

        // Navigate to next step
        this.$router.push(this.TARGET_PLATFORM + "Step5");
      } catch (e) {
        console.log("ERROR: " + e.response.data.message);
        this.modal_title = "Error";
        this.isBusy = false;
        this.response = e.response.data.message;
        this.showModal = true;
      }
      this.isBusy = false;
    },
  },
};
</script>

<style>
.hidden_header {
  display: none;
}
</style>
