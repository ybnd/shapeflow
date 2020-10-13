<template>
  <b-alert
    :show="true"
    :variant="notice.variant !== undefined ? notice.variant : 'secondary'"
    class="notice"
  >
    <p class="message">
      <b v-if="notice.analyzer !== undefined"> {{ notice.analyzer }}: </b>
      {{ notice.message }}
    </p>
    <button
      type="button"
      class="close dismiss-button"
      data-dismiss="alert"
      @click="dismiss(notice)"
    >
      ×
    </button>
  </b-alert>
</template>

<script>
import { NOTICE_TIMEOUT } from "../../static/api";

export default {
  name: "Notice",
  props: {
    notice: {
      type: Object,
      required: true,
    },
    focus: {
      type: Boolean,
      default: false,
    },
  },
  mounted() {
    if (!this.notice.persist) {
      this.timeout = setTimeout(this.dismiss, NOTICE_TIMEOUT);
    }
  },
  destroyed() {
    clearTimeout(this.timeout);
  },
  methods: {
    dismiss() {
      if (this.focus) {
        // todo: defer again.
      } else {
        this.$store.commit("analyzers/dismissNotice", { notice: this.notice });
      }
    },
  },
  data() {
    return { timeout: null };
  },
};
</script>

<style lang="scss" scoped>
@import "../../assets/scss/bootstrap-variables";
@import "../../assets/scss/core-variables";
@import "../../node_modules/bootstrap/scss/functions";

.notice {
  margin: 0 !important;
  margin-top: calc(#{$notice-gap} * 2) !important;
  padding: $notice-gap !important;
  border-radius: 0;
  pointer-events: auto;
}
.dismiss-button {
  padding-right: $notice-gap !important;
  pointer-events: auto;
}
.message {
  float: left;
  width: calc(#{$notice-width} - #{$dismiss-width} - #{$notice-gap});
  margin-bottom: 0;
  margin-left: 2px;
  pointer-events: auto;
}
.dismiss-button-column {
  float: right;
  width: $dismiss-width;
}
</style>
