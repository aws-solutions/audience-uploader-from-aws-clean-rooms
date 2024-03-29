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
            <Sidebar :is-step1-active="true" />
          </b-col>
          <b-col cols="10">
            <h3>Select file</h3>
            Select a file to ingest into
            {{
              this.TARGET_PLATFORM.charAt(0).toUpperCase() +
              this.TARGET_PLATFORM.slice(1)
            }}.
            <br />
            <br />
            <div>
              <b-row align-v="end">
                <b-col sm="9" align="left">
                  <b-form-group
                    id="bucket-label"
                    label-cols-lg="2"
                    label-align-lg="left"
                    label="Bucket: "
                    label-for="bucket"
                  >
                    <b-form-input
                      id="bucket-input"
                      plaintext
                      :placeholder="DATA_BUCKET_NAME"
                    ></b-form-input>
                  </b-form-group>
                  <b-form-group
                    id="s3key-label"
                    label-cols-lg="2"
                    label-align-lg="left"
                    description="Select a file"
                    label="Key:"
                    label-for="s3key-input"
                  >
                    <b-form-input
                      id="s3key-input"
                      v-model="new_s3key"
                    ></b-form-input>
                  </b-form-group>
                </b-col>
                <b-col sm="2" align="right">
                  <button
                    type="submit"
                    class="btn btn-primary mb-2"
                    @click="onSubmit"
                  >
                    Next
                  </button>
                  <br />
                  <br />
                </b-col>
              </b-row>
            </div>

            <div>
              <b-table
                ref="selectableTable"
                :items="results"
                :fields="fields"
                :busy="isBusy"
                select-mode="single"
                responsive="sm"
                selectable
                small
                @row-selected="onRowSelected"
              >
                <template #table-busy>
                  <div class="text-center my-2">
                    <b-spinner class="align-middle"></b-spinner>
                    <strong>&nbsp;&nbsp;Loading...</strong>
                  </div>
                </template>
                <template #cell(selected)="{ rowSelected }">
                  <template v-if="rowSelected">
                    <span aria-hidden="true">&check;</span>
                    <span class="sr-only">Selected</span>
                  </template>
                  <template v-else>
                    <span aria-hidden="true">&nbsp;</span>
                    <span class="sr-only">Not selected</span>
                  </template>
                </template>
              </b-table>
            </div>
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
  name: "tiktokStep1",
  components: {
    Header,
    Sidebar,
  },
  data() {
    return {
      isBusy: false,
      fields: [
        { key: "selected" },
        { key: "key", sortable: true },
        { key: "last_modified", sortable: true },
        { key: "size", sortable: true },
      ],
      new_s3key: "",
      isStep1Active: true,
      results: [],
    };
  },
  computed: {
    ...mapState(["s3key"]),
  },
  deactivated: function () {
    console.log("deactivated");
  },
  activated: function () {
    console.log("activated");
  },
  created: function () {
    console.log("create");
    this.send_request("POST", "list_bucket", {
      s3bucket: this.DATA_BUCKET_NAME,
    });
  },
  mounted: function () {
    this.new_s3key = this.s3key;
  },
  methods: {
    onSubmit() {
      this.$store.commit("updateS3key", this.new_s3key);
      this.$router.push(this.TARGET_PLATFORM + "Step2");
    },
    onRowSelected(items) {
      this.new_s3key = items[0].key;
    },
    async send_request(method, resource, data) {
      this.results = [];
      console.log(
        "sending " +
          method +
          " " +
          resource +
          " " +
          JSON.stringify(data)
      );
      const apiName = "audience-uploader-from-aws-clean-rooms";
      let response = "";
      this.isBusy = true;
      try {
        if (method === "GET") {
          response = await this.$Amplify.API.get(apiName, resource);
        } else if (method === "POST") {
          let requestOpts = {
            headers: { "Content-Type": "application/json" },
            body: data,
          };
          response = await this.$Amplify.API.post(
            apiName,
            resource,
            requestOpts
          );
        }
        this.results = response;
      } catch (e) {
        console.log("ERROR: " + e.response.data.message);
        this.isBusy = false;
        this.results = e.response.data.message;
      }
      this.isBusy = false;
    },
  },
};
</script>