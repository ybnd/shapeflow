<template>
  <div class="content">
    <b-tbody class="log-table" @scroll="handleScroll" ref="log">
      <tr v-for="row in log.split('\n')" :key="row" class="log-row">
        <td class="log-line">{{ row }}</td>
      </tr>
    </b-tbody>
  </div>
</template>

<script>
import { get_log } from "../static/api";
import { debounce } from "throttle-debounce";
import { PageHeader } from "../components/header/PageHeader";
import PageHeaderItem from "../components/header/PageHeaderItem";

export default {
  name: "log",
  components: { PageHeader, PageHeaderItem },
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
      console.log(`set this.scrolled to ${this.scrolled}`);
    },
    handleLogText() {
      this.log = " \n" + this.request.responseText;
      if (!(this.$refs.log === undefined)) {
        if (!this.scrolled) {
          console.log("scrolling down");
          console.log(this.$refs.log.$el);
          this.$refs.log.$el.scrollLeft = 0;
          this.$refs.log.$el.scrollTop = this.$refs.log.$el.scrollTopMax;
        }
      }
    },
    isScrolled() {
      if (this.$refs.log === undefined) {
        return false;
      } else {
        console.log({
          scrollTop: this.$refs.log.$el.scrollTop,
          scrollTopMax: this.$refs.log.$el.scrollTopMax,
          scrollLeft: this.$refs.log.$el.scrollLeft
        });
        return (
          this.$refs.log.$el.scrollTop !== this.$refs.log.$el.scrollTopMax ||
          this.$refs.log.$el.scrollLeft !== 0
        );
      }
    }
  }
};
</script>

<style lang="scss">
@import "../assets/scss/_bootstrap-variables";
@import "../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

.content {
  max-height: 100vh;
  min-width: calc(100vw - #{$sidebar-width});
  display: flex;
  flex-flow: column;
}
.log-header {
  padding-top: 12px;
  padding-left: 15px;
  flex: 0 0 auto;
}
.log-container {
  max-width: calc(100vw - #{$sidebar-width});
  display: flex;
  flex: 1 1 auto;
  flex-flow: column;
  overflow: hidden;
  white-space: pre-line;
}
.log-table {
  flex: 1 1 auto;
  overflow: auto;
  font-family: monospace;
  font-size: 11px;
  table-layout: fixed;
}
.log-line {
  color: theme-color("gray-900") !important;
  width: calc(100vw - #{$sidebar-width} - 20);
  white-space: nowrap;
}
tr:nth-child(even) {
  background-color: $body-bg;
}
tr:nth-child(odd) {
  background-color: lighten($gray-200, 6%);
}
</style>
