/*
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
*/

import Vue from "vue";
import VueRouter from "vue-router";

Vue.use(VueRouter);

const platformPages = {
  snap: ["Step1", "Step2", "Step3", "Step4", "Step5"],
  tiktok: ["Step1", "Step2", "Step3", "Step4", "Step5"],
};
const routerRoutes = [
  {
    path: "/login",
    name: "Login",
    component: () => import("@/views/Login.vue"),
    meta: { requiresAuth: false },
    alias: "/",
  },
];
for (const platform in platformPages) {
  for (const page of platformPages[platform]) {
    const routeParams = {
      path: "/" + platform + page.toLowerCase(),
      name: platform + page,
      component: () => import("@/" + platform + "Views/" + page + ".vue"),
      meta: { requiresAuth: true },
    };
    routerRoutes.push(routeParams);
  }
}

const platform = "snap";
const router = new VueRouter({
  mode: "history",
  base: process.env.BASE_URL,
  routes: routerRoutes,
});

router.beforeResolve(async (to, from, next) => {
  if (to.matched.some((record) => record.meta.requiresAuth)) {
    try {
      await Vue.prototype.$Amplify.Auth.currentAuthenticatedUser();
      next();
    } catch (e) {
      console.log(e);
      next({
        path: "/login",
      });
    }
  }
  console.log(next);
  next();
});

export default router;
