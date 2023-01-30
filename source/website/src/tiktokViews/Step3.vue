/*
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
*/

<template>
  <div>
    <div class="headerTextBackground">
      <Header />
      <b-container fluid>
        <b-alert v-model="showMissingDataAlert" variant="danger">
          Missing s3key. Go back and select a file.
        </b-alert>
        <b-alert v-model="showUserIdWarning" variant="danger" dismissible>
          {{ userIdWarningMessage }}
        </b-alert>
        <b-alert
          v-model="showIncompleteFieldsError"
          variant="danger"
          dismissible
        >
          PII type is missing for fields {{ incompleteFields }}
        </b-alert>
        <b-row style="text-align: left">
          <b-col cols="2">
            <Sidebar :is-step3-active="true" />
          </b-col>
          <b-col cols="10">
            <h3>Define Columns</h3>
            <b-row>
              <b-col>
                Fill in the table to define properties for each field in
                {{ s3key }}.
              </b-col>
              <b-col sm="3" align="right" class="row align-items-end">
                <button
                  type="submit"
                  class="btn btn-outline-primary mb-2"
                  @click="$router.push(TARGET_PLATFORM + 'Step2')"
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
            <b-table
              :items="items"
              :fields="fields"
              :busy="isBusy"
              head-variant="light"
              small
              borderless
            >
              <template #cell(Actions)="data">
                <b-link
                  class="text-danger"
                  @click="deleteColumn(`${data.item.name}`)"
                >
                  Delete
                </b-link>
              </template>
              <template #cell(data_type)="data">
                <b-form-select
                  id="dropdown-1"
                  :options="data_type_options"
                  :value="data.item.data_type"
                  @change="(x) => changeDataType(x, data.index)"
                >
                </b-form-select>
              </template>
              <template #cell(column_type)="data">
                <b-form-select
                  id="dropdown-column-type"
                  :options="column_type_options"
                  :value="data.item.column_type"
                  @change="(x) => changeColumnType(x, data.index)"
                >
                </b-form-select>
              </template>
              <template #cell(pii_type)="data">
                <b-form-select
                  id="dropdown-pii-type"
                  :options="pii_type_options"
                  :value="data.item.pii_type"
                  :disabled="data.item.column_type !== 'PII'"
                  @change="(x) => changePiiType(x, data.index)"
                >
                </b-form-select>
              </template>
              <template #table-busy>
                <div class="text-center my-2">
                  <b-spinner class="align-middle"></b-spinner>
                  <strong>&nbsp;&nbsp;Loading...</strong>
                </div>
              </template>
            </b-table>
            <b-row>
              <b-col></b-col>
              <b-col sm="2" align="right" class="row align-items-end">
                <b-button
                  type="submit"
                  variant="outline-secondary"
                  @click="onReset"
                  >Reset</b-button
                >
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
  name: "tiktokStep3",
  components: {
    Header,
    Sidebar,
  },
  data() {
    return {
      mainEventTimeSelected2: true,
      new_dataset_definition: {},
      isBusy: false,
      showMissingDataAlert: false,
      showIncompleteFieldsError: false,
      showIncompleteTimeFieldError: false,
      showUserIdWarning: false,
      userIdWarningMessage:
        "Do not include user_id and user_type columns in data files containing hashed identifiers. These columns are used by " +
        this.TARGET_PLATFORM +
        " when a match is found in a hashed record.",
      items: [],
      columns: [],
      fields: [
        { key: "name", sortable: true },
        { key: "data_type", sortable: true },
        { key: "column_type", sortable: true },
        { key: "pii_type", sortable: true },
        { key: "Actions", sortable: false },
      ],
      data_type_options: [
        { value: "STRING", text: "String" },
        { value: "DECIMAL", text: "Decimal" },
        { value: "INTEGER", text: "Integer (32-bit)" },
        { value: "LONG", text: "Integer (64-bit)" },
        { value: "TIMESTAMP", text: "Timestamp" },
        { value: "DATE", text: "Date" },
      ],
      column_type_options: [
        { value: "PII", text: "PII", disabled: false },
        { value: "NON-PII", text: "Non-PII", disabled: false },
      ],
      pii_type_options: [
        { value: "EMAIL", text: "Email", disabled: false },
        { value: "PHONE", text: "Phone", disabled: false },
        { value: "GAID", text: "Google Advertising ID", disabled: false },
        { value: "IDFA", text: "Identifier For Advertising", disabled: false },
      ],
      isStep3Active: true,
    };
  },
  computed: {
    ...mapState(["dataset_definition", "s3key", "step3_form_input"]),
    contains_hashed_identifier() {
      return this.items.filter((x) => x.column_type === "PII").length > 0;
    },
    incompleteFields() {
      return this.items
        .filter((x) => x.column_type === "PII" && x.pii_type === "")
        .map((x) => x.name);
    },
  },
  activated: function () {
    console.log("activated");
  },
  deactivated: function () {
    console.log("deactivated");
  },
  created: function () {
    console.log("created");
  },
  mounted: function () {
    this.new_dataset_definition = this.dataset_definition;
    if (!this.s3key) {
      this.showMissingDataAlert = true;
    } else if (!this.step3_form_input.length) {
      this.send_request("POST", "get_data_columns", {
        s3bucket: this.DATA_BUCKET_NAME,
        s3key: this.s3key,
        file_format: this.dataset_definition.fileFormat,
      });
    } else {
      this.items = this.step3_form_input;
    }
  },
  methods: {
    deleteColumn(column_name) {
      this.items = this.items.filter((x) => x.name !== column_name);
      console.log("removed " + column_name);
    },
    onReset() {
      this.send_request("POST", "get_data_columns", {
        s3bucket: this.DATA_BUCKET_NAME,
        s3key: this.s3key,
        file_format: this.dataset_definition.fileFormat,
      });

      this.column_type_options.forEach((x) => (x.disabled = false));
      this.pii_type_options.forEach((x) => (x.disabled = false));
    },
    onSubmit() {
      // ------- Validate form ------- //
      if (this.incompleteFields.length > 0) {
        this.showIncompleteFieldsError = true;
        return;
      } else {
        this.showIncompleteFieldsError = false;
      }
      // add hashed identifiers for each PII column
      this.items
        .filter((x) => x.pii_type !== "")
        .forEach((x) => {
          const column_definition = {
            name: x.name,
            dataType: x.data_type,
            columnType: x.column_type,
            externalUserIdType: {
              type: "HashedIdentifier",
              identifierType: x.pii_type,
            },
          };
          this.columns.push(column_definition);
        });
      // add identifiers for non-PII columns
      this.items
        .filter((x) => x.pii_type === "")
        .forEach((x) => {
          const column_definition = {
            name: x.name,
            dataType: x.data_type,
            columnType: x.column_type,
          };
          this.columns.push(column_definition);
        });
      this.new_dataset_definition["columns"] = this.columns;
      this.$store.commit(
        "updateDatasetDefinition",
        this.new_dataset_definition
      );
      this.$router.push(this.TARGET_PLATFORM + "Step4");
    },
    changeDataType(value, index) {
      this.items[index].data_type = value;
      this.$store.commit("saveStep3FormInput", this.items);
    },
    changeColumnType(value, index) {
      this.items[index].column_type = value;
      this.$store.commit("saveStep3FormInput", this.items);
    },
    changePiiType(value, index) {
      // enable previously selected value
      if (this.items[index].pii_type !== "") {
        const previous_value = this.items[index].pii_type;
        let idx = this.pii_type_options.findIndex(
          (x) => x.value == previous_value
        );
        this.pii_type_options[idx].disabled = false;
      }
      // disable currently selected value
      let idx = this.pii_type_options.findIndex((x) => x.value === value);
      this.pii_type_options[idx].disabled = true;
      this.items[index].pii_type = value;
      this.$store.commit("saveStep3FormInput", this.items);
    },
    async send_request(method, resource, data) {
      console.log(
        "sending " + method + " " + resource + " " + JSON.stringify(data)
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
        this.items = response.columns.map((x) => {
          return {
            name: x,
            data_type: "STRING",
            column_type: "",
            pii_type: "",
          };
        });
        console.log(JSON.stringify(this.items));
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