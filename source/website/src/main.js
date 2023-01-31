/*
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
*/

import Vue from "vue";
import VueHighlightJS from "vue-highlightjs";
import BootstrapVue from "bootstrap-vue";

import "bootstrap/dist/css/bootstrap.css";
import "bootstrap-vue/dist/bootstrap-vue.css";
import "dropzone/dist/min/dropzone.min.css";
import "highlight.js/styles/github.css";

import App from "./App.vue";
import store from "./store";
import router from "./router.js";
import Amplify, * as AmplifyModules from "aws-amplify";
import { AmplifyPlugin } from "aws-amplify-vue";

const getRuntimeConfig = async () => {
  const runtimeConfig = await fetch("/runtimeConfig.json");
  return runtimeConfig.json();
};

getRuntimeConfig().then(function (json) {
  const awsconfig = {
    Auth: {
      region: json.AWS_REGION,
      userPoolId: json.USER_POOL_ID,
      userPoolWebClientId: json.USER_POOL_CLIENT_ID,
      identityPoolId: json.IDENTITY_POOL_ID,
    },
    Storage: {
      AWSS3: {
        region: json.AWS_REGION,
      },
    },
    API: {
      endpoints: [
        {
          name: "audience-uploader-from-aws-clean-rooms",
          endpoint: json.API_ENDPOINT,
          service: "execute-api",
          region: json.AWS_REGION,
        },
      ],
    },
  };
  console.log("Runtime config: " + JSON.stringify(json));
  Amplify.configure(awsconfig);
  Vue.config.productionTip = false;
  Vue.mixin({
    data() {
      return {
        // Distribute runtime configs into every Vue component
        AWS_REGION: json.AWS_REGION,
        DATA_BUCKET_NAME: json.DATA_BUCKET_NAME,
        ARTIFACT_BUCKET_NAME: json.ARTIFACT_BUCKET_NAME,
        TARGET_PLATFORM: json.TARGET_PLATFORM,
      };
    },
  });
  Vue.use(AmplifyPlugin, AmplifyModules);
  Vue.use(BootstrapVue);
  Vue.use(VueHighlightJS);
  new Vue({
    router,
    store,
    render: (h) => h(App),
  }).$mount("#app");
});
