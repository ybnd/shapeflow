<template>
  <div class="fixed-page">
    <div class="content">
      <h2 class="log-header">Log</h2>
      <b-container class="log-container" @scroll="handleScroll" ref="log">
        <pre class="log-pre">
          <code class="log-code">
            {{ this.log }}
          </code>
        </pre>
      </b-container>
    </div>
  </div>
</template>

<script>
import { get_log } from "../static/api";
import { debounce } from "throttle-debounce";

export default {
  name: "log",
  components: {},
  data: function() {
    return {
      request: null,
      log: "",
      scrolled: false
    };
  },
  mounted() {
    this.request = get_log();

    setInterval(this.handleLogText, 250);
  },
  methods: {
    handleScroll() {
      this.scrolled = this.isScrolled();
    },
    handleLogText() {
      this.log = " \n" + this.request.responseText;
      if (!(this.$refs.log === undefined)) {
        if (!this.scrolled) {
          this.$refs.log.scrollLeft = 0;
          this.$refs.log.scrollTop = this.$refs.log.scrollTopMax;
        }
      }
    },
    isScrolled() {
      if (this.$refs.log === undefined) {
        return false;
      } else {
        return (
          this.$refs.log.scrollTop !== this.$refs.log.scrollTopMax ||
          this.$refs.log.scrollLeft !== 0
        );
      }
    }
  }
};
</script>

<style lang="scss">
@import "../assets/scss/_bootstrap-variables";
@import "node_modules/bootstrap/scss/functions";

.fixed-page {
}
.content {
  display: flex;
  flex-flow: column;
  max-height: 100vh;
}
.log-header {
  padding-top: 12px;
  padding-left: 15px;
  flex: 0 1 auto;
}
.log-container {
  max-width: calc(100vw - 160px);
  display: block;
  overflow: hidden;
  overflow-y: auto;
  overflow-x: auto;
  white-space: pre-line;
  flex: 1 1 auto;
}
.log-pre {
  color: theme-color("gray-800") !important;
  margin-bottom: -16px;
  margin-top: -16px;
  /* https://www.dte.web.id/2012/03/css-only-zebra-striped-pre-tag.html#.UUoV6lugkoM */
  background: $body-bg;
  background-image: -webkit-linear-gradient(
    $body-bg 50%,
    lighten($gray-200, 6%) 50%
  );
  background-image: -moz-linear-gradient(
    $body-bg 50%,
    lighten($gray-200, 6%) 50%
  );
  background-image: -ms-linear-gradient(
    $body-bg 50%,
    lighten($gray-200, 6%) 50%
  );
  background-image: -o-linear-gradient(
    $body-bg 50%,
    lighten($gray-200, 6%) 50%
  );
  background-image: linear-gradient($body-bg 50%, lighten($gray-200, 6%) 50%);
  background-position: 0 0;
  background-repeat: repeat;
  background-size: 2rem 2rem;
  line-height: 1rem;
}
.log-code {
  white-space: pre;
}
</style>
