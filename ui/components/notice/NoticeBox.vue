<template>
  <div class="notice-box">
    <Notice v-for="notice in notices" :notice="notice" :key="notice.uuid" />
  </div>
</template>

<script>
import Notice from "./Notice";

export default {
  name: "NoticeBox",
  components: { Notice },
  computed: {
    notices() {
      return this.$store.getters["analyzers/getNotices"];
    },
  },
};
</script>

<style lang="scss" scoped>
@import "../../assets/scss/bootstrap-variables";
@import "../../assets/scss/core-variables";
@import "../../node_modules/bootstrap/scss/functions";

.notice-box {
  position: absolute;
  bottom: 0;
  right: 0;
  min-height: 100px;
  max-height: $notice-box-max-height;
  width: calc(#{$notice-width} + 2 * #{$notice-gap});
  display: flex;
  flex-direction: column-reverse;
  z-index: 8000;
  padding-bottom: calc(#{$notice-gap} * 2) !important;
  padding-left: calc(#{$notice-gap} * 2) !important;
  padding-right: calc(#{$notice-gap} * 2) !important;
  pointer-events: none;
}
</style>
