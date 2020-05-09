<template>
  <div class="fixed-page">
    <PageHeader>
      <PageHeaderItem>
        <b-button
          class="header-button-icon"
          data-toggle="tooltip"
          title="Copy to clipboard"
        >
          <i class="fa fa-clipboard" />
        </b-button>
      </PageHeaderItem>
      <PageHeaderItem>
        <b-input-group>
          <b-form-input v-model="filter" placeholder="Filter log...">
            {{ filter }}
          </b-form-input>
        </b-input-group>
      </PageHeaderItem>
    </PageHeader>
    <div class="content">
      <b-tbody class="log-table" @scroll="handleScroll" ref="log">
        <tr
          v-for="(row, index) in filtered_log.split('\n')"
          :key="index"
          class="log-row"
        >
          <td class="log-line">{{ row }}</td>
        </tr>
      </b-tbody>
    </div>
  </div>
</template>

<script>
import { get_log, stop_log } from "../static/api";
import { debounce } from "throttle-debounce";
import PageHeader from "../components/header/PageHeader";
import PageHeaderItem from "../components/header/PageHeaderItem";

export default {
  name: "log",
  components: { PageHeader, PageHeaderItem },
  data: function() {
    return {
      request: null,
      log: "",
      scrolled: false,
      filter: "",
      filtered_log: "",
      matches: {}
    };
  },
  mounted() {
    this.request = get_log();
    setInterval(this.handleLogText, 250);
  },
  beforeDestroy() {
    stop_log();
  },
  methods: {
    handleScroll() {
      this.scrolled = this.isScrolled();
    },
    handleLogText() {
      this.log = " \n" + this.request.responseText;
      this.filterLog();

      if (!(this.$refs.log === undefined)) {
        if (!this.scrolled) {
          this.$refs.log.$el.scrollLeft = 0;
          this.$refs.log.$el.scrollTop = this.$refs.log.$el.scrollTopMax;
        }
      }
    },
    handleClipboard() {},
    isScrolled() {
      if (this.$refs.log === undefined) {
        return false;
      } else {
        return (
          this.$refs.log.$el.scrollTop !== this.$refs.log.$el.scrollTopMax ||
          this.$refs.log.$el.scrollLeft !== 0
        );
      }
    },
    filterLog() {
      this.filter = this.filter.trim();

      if (this.filter) {
        // reset filter data
        this.filtered_log = [];
        this.matches = {};

        let lines = this.log.match(/[^\r\n]+/g); // split log into lines  todo: platform-agnostic ~ line endings
        let filtered_lines = [];

        for (let i = 0; i < lines.length; i++) {
          let matches = [];
          let raw_matches = lines[i].matchAll(RegExp(this.filter, "g"));

          console.log(lines[i]);

          for (match in raw_matches) {
            console.log(`line ${i} match: ${match}`);
            matches = [...matches, match];
          }

          for (const match of matches) {
            console.log(
              `Found ${match[0]} start=${match.index} end=${match.index +
                match[0].length}.`
            );
          }

          if (matches.length > 0) {
            filtered_lines = [...filtered_lines, lines[i]];
            this.matches = { ...this.matches, [i]: matches };
          }
        }
        this.filtered_log = filtered_lines.join("\r\n"); // todo: platform-agnostic ~ line endings
      } else {
        this.filtered_log = this.log;
        this.matches = {};
      }
    }
  },
  watch: {
    filter: function() {
      this.filterLog();
    }
  }
};
</script>

<style lang="scss">
@import "../assets/scss/_bootstrap-variables";
@import "../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

.content {
  height: calc(100vh - #{$header-height});
  width: calc(100vw - #{$sidebar-width});
  display: flex;
  flex-flow: column;
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
  width: calc(100vw - #{$sidebar-width});
  white-space: nowrap;
}
tr:nth-child(even) {
  background-color: $body-bg;
}
tr:nth-child(odd) {
  background-color: lighten($gray-200, 6%);
}
</style>
