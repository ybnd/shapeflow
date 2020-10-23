<template>
  <div class="app">
    <div v-show="!tooSmall" class="app-body">
      <Sidebar />
      <main class="main">
        <nuxt />
        <NoticeBox />
      </main>
    </div>
    <div v-if="tooSmall" class="too-small-message">
      <i class="fa fa-exclamation-triangle" />
      Window size too small to properly render the application!
      <div style="margin: 16px; font-size: 1px;">
        (so I'm not even trying)
      </div>
      <div style="margin: 32px; font-size: 3px;">
        (zoom out maybe)
      </div>
    </div>
  </div>
</template>

<script>
import { Sidebar } from "~/components/";
import NoticeBox from "@/components/notice/NoticeBox";
import { api } from "../static/api";

export default {
  name: "default-layout",
  components: {
    Sidebar,
    NoticeBox,
  },
  beforeCreate() {
    this.$store.dispatch("schemas/sync"); // todo: is this really the place for this though?
    this.$store.dispatch("settings/sync");
  },
  mounted() {
    window.addEventListener("unload", api.unload);
    window.addEventListener("resize", this.checkIfTooSmall);
  },
  destroyed() {
    window.removeEventListener("resize", this.checkIftooSmall);
    window.removeEventListener("unload", api.unload);
  },
  methods: {
    checkIfTooSmall() {
      // console.log(`default.checkIfTooSmall`);
      // console.log(`width=${window.innerWidth} height=${window.innerHeight}`);

      this.tooSmall = window.innerWidth < 720 || window.innerHeight < 360;
      // width: sidebar + new analysis popover render correctly
      // height: arbitrary

      // console.log(`tooSmall = ${this.tooSmall}`);
    },
  },
  data() {
    return {
      tooSmall: false,
    };
  },
};
</script>

<style>
.too-small-message {
  padding: 16px;
  font-size: 16px;
}
</style>
