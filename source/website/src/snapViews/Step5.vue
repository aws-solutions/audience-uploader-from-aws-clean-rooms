/*
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
*/

<template>
  <div>
    <div class="headerTextBackground">
      <Header />
      <b-container fluid>
        <b-row style="text-align: left">
          <b-col cols="2">
            <Sidebar :is-step5-active="true" />
          </b-col>
          <b-col cols="10">
            <b-row>
              <b-col>
                <h3>Datasets transformed</h3>
              </b-col>
              <b-col align="right">
                <b-button @click="get_etl_jobs()">Refresh</b-button>
              </b-col>
            </b-row>
            <b-table
              small
              responsive="sm"
              :fields="etl_fields"
              :items="etl_jobs"
              :busy="isBusy2"
              show-empty
            >
              <template #cell(id)="data">
                ...{{ data.item.Id.substr(-8) }}
              </template>
              <template #empty="scope">
                No ETL jobs have started yet.
              </template>
              <template #table-busy>
                <div class="text-center my-2">
                  <b-spinner class="align-middle"></b-spinner>
                  <strong>&nbsp;&nbsp;Loading...</strong>
                </div>
              </template>
            </b-table>
          </b-col>
        </b-row>
      </b-container>
    </div>
  </div>
</template>

<script>
import Header from "@/components/Header.vue";
import Sidebar from "@/components/Sidebar.vue";

export default {
  name: "snapStep5",
  components: {
    Header,
    Sidebar,
  },
  data() {
    return {
      datasets: [],
      selected_dataset: "",
      dataset_fields: [
        "selected",
        "segmentName",
        "createdTime",
        "updatedTime",
        "Actions",
      ],
      etl_jobs: [],
      etl_fields: [
        "SegmentName",
        "Id",
        "StartedOn",
        "CompletedOn",
        "ExecutionTime",
        "JobRunState",
      ],
      uploads: [],
      upload_fields: [
        { key: "dateCreated", label: "Date", sortable: true },
        { key: "totalFileCount", label: "Total files" },
        { key: "errorFileCount", label: "Bad files" },
        { key: "rowsAcceptedTotal", label: "Rows Accepted" },
        { key: "rowsDroppedTotal", label: "Rows Dropped" },
        { key: "rowsWithResolvedIdentity", label: "Identities Resolved" },
        { key: "sourceFileS3Key", label: "Source File" },
        { key: "uploadId", label: "Upload Id" },
        { key: "status", label: "Status" },
      ],
      isBusy: false,
      isBusy2: false,
      isBusy3: false,
      isStep5Active: true,
      response: "",
    };
  },
  computed: {},
  deactivated: function () {
    console.log("deactivated");
  },
  activated: function () {
    console.log("activated");
  },
  created: function () {
    console.log("create");
    this.get_etl_jobs();
  },
  methods: {
    onRowSelected(items) {
      if (items.length > 0) {
        this.selected_dataset = items[0].segmentName;
        this.listDatasetUploads(this.selected_dataset);
      } else {
        this.uploads = [];
        this.selected_dataset = "";
      }
    },
    async listDatasetUploads(segmentName) {
      this.selected_dataset = segmentName;
      await this.list_uploads({ segmentName: segmentName });
    },
    async list_uploads(data) {
      this.uploads = [];
      const apiName = "audience-uploader-from-aws-clean-rooms";
      let response = "";
      const method = "POST";
      const resource = "list_uploads";
      this.isBusy3 = true;
      try {
        console.log(
          "sending " +
            method +
            " " +
            resource +
            " " +
            JSON.stringify(data)
        );
        let requestOpts = {
          headers: { "Content-Type": "application/json" },
          body: data,
        };
        response = await this.$Amplify.API.post(apiName, resource, requestOpts);
        console.log(response);
        this.uploads = response.uploads;
      } catch (e) {
        console.log("ERROR: " + e.response.data.message);
        this.isBusy3 = false;
        this.response = e.response.data.message;
      }
      this.isBusy3 = false;
    },
    async get_etl_jobs() {
      this.isBusy2 = true;
      this.etl_jobs = [];
      const apiName = "audience-uploader-from-aws-clean-rooms";
      let response = "";
      const method = "GET";
      const resource = "get_etl_jobs";
      try {
        if (method === "GET") {
          console.log("sending " + method + " " + resource);
          response = await this.$Amplify.API.get(apiName, resource);
          console.log(response);
          this.etl_jobs = response.JobRuns;
        }
      } catch (e) {
        console.log("ERROR: " + e.response.data.message);
        this.isBusy2 = false;
        this.response = e.response.data.message;
      }
      this.isBusy2 = false;
    },
  },
};
</script>

<style>
.hidden_header {
  display: none;
}
</style>
