/*
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
*/


<template>
	<div>
		<b-navbar toggleable="lg" type="dark" variant="dark">
			<b-navbar-brand to="/"> Audience Uploader from AWS Clean Rooms Uploader </b-navbar-brand>
			<b-navbar-toggle target="nav-collapse" />

			<b-collapse id="nav-collapse" is-nav>
				<!-- Right aligned nav items -->
				<b-navbar-nav class="ml-auto">
					<b-nav-item v-if="signedIn" @click="signOut()">
						<p id="signOutBtn">Sign Out</p>
					</b-nav-item>
				</b-navbar-nav>
			</b-collapse>
		</b-navbar>
		<br />
	</div>
</template>

<script>
import { AmplifyEventBus } from "aws-amplify-vue";

export default {
	name: "Header",
	props: ["isCollectionActive", "isUploadActive"],
	data() {
		return {
			signedIn: false,
		};
	},
	async beforeCreate() {
		try {
			await this.$Amplify.Auth.currentAuthenticatedUser();
			this.signedIn = true;
		} catch (err) {
			this.signedIn = false;
		}
		AmplifyEventBus.$on("authState", (info) => {
			this.signedIn = info === "signedIn";
		});
	},
	async mounted() {
		AmplifyEventBus.$on("authState", (info) => {
			this.signedIn = info === "signedOut";
			this.$router.push({ name: "Login" });
		});
	},
	methods: {
		openWindow: function (url) {
			window.open(url, "noopener,noreferer");
		},
		signOut() {
			this.$Amplify.Auth.signOut()
				.then(() => this.$router.push({ name: "Login" }))
				.catch((err) => console.log(err));
		},
	},
};
</script>

<style>
#signOutBtn {
	color: #ed900e;
}
</style>
