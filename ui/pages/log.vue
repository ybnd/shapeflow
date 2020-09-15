<template>
  <div class="fixed-page">
    <PageHeader>
      <PageHeaderItem>
        <b-button
          class="header-button-icon log-button"
          data-toggle="tooltip"
          :title="!follow ? 'Follow log' : 'Stop following log'"
          :variant="follow ? 'danger' : null"
          @click="handleFollow"
        >
          <i class="fa fa-arrow-down" />
        </b-button>
      </PageHeaderItem>
      <PageHeaderItem>
        <b-input-group>
          <b-form-input
            class="isimple-form-field-auto filter-field"
            v-model="filter"
            @input="filterLog"
            placeholder="Filter log..."
          >
            {{ filter }}
          </b-form-input>
        </b-input-group>
      </PageHeaderItem>
      <PageHeaderItem>
        <b-button
          class="header-button-icon log-button"
          data-toggle="tooltip"
          :title="case_sensitive ? 'Ignore case' : 'Case sensitive filter'"
          :variant="case_sensitive ? 'danger' : null"
          @click="handleCaseSensitive"
        >
          <i class="fa fa-exclamation" />
        </b-button>
      </PageHeaderItem>
    </PageHeader>
    <div class="content">
      <b-tbody class="log-table" ref="log" @scroll="handleScroll">
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
import { throttle, debounce } from "throttle-debounce";
import PageHeader from "../components/header/PageHeader";
import PageHeaderItem from "../components/header/PageHeaderItem";

const SCROLL_TOLERANCE_V = 60;
const SCROLL_TOLERANCE_H = 30;

const FOLLOW_INTERVAL = 100;
const SCROLL_TIMEOUT = 500;

export default {
  name: "log",
  components: { PageHeader, PageHeaderItem },
  data: function () {
    return {
      request: null,
      log: "",
      follow: false,
      release: false,
      filter: "",
      case_sensitive: false,
      filtered_log: "",
      matches: {},
    };
  },
  mounted() {
    this.request = get_log();
    this.request.onprogress = (stuff) => {
      this.log = stuff.target.responseText;
    };
    setTimeout(() => {
      setInterval(() => {
        if (!this.release) {
          if (this.follow || this.scrolled_down()) {
            this.scrollNow();
          }
        }
      }, FOLLOW_INTERVAL);
    }, 1000);
  },
  beforeDestroy() {
    stop_log();
  },
  methods: {
    handleLogText() {
      this.filterLog();

      if (this.$refs.log !== undefined) {
        if (!this.release) {
          if (this.follow || this.scrolled_down()) {
            this.scrollNow();
          }
        }
      }
    },
    scrolled_down() {
      if (this.$refs.log !== undefined) {
        const scrolled_down =
          Math.abs(
            this.$refs.log.$el.scrollTop - this.$refs.log.$el.scrollTopMax
          ) < SCROLL_TOLERANCE_V &&
          this.$refs.log.$el.scrollLeft < SCROLL_TOLERANCE_H;
        return scrolled_down;
      } else {
        return false;
      }
    },
    scrollNow() {
      if (this.$refs.log !== undefined) {
        this.$refs.log.$el.scrollLeft = 0;
        this.$refs.log.$el.scrollTop = this.$refs.log.$el.scrollTopMax + 50;
      }
    },
    handleFollow() {
      this.follow = !this.follow;
      this.scrollNow();
    },
    handleScroll() {
      this.release = true;
      setTimeout(() => {
        this.release = false;
      }, SCROLL_TIMEOUT);
    },
    handleFilterLog: throttle(
      500,
      true,
      debounce(500, false, () => {
        this.filterLog();
      })
    ),
    handleCaseSensitive() {
      this.case_sensitive = !this.case_sensitive;
      this.filterLog();
    },
    filterLog() {
      console.log("log.filterLog()");
      this.filter = this.filter.trim();

      if (this.filter) {
        // reset filter data

        const re = new RegExp(
          this.case_sensitive ? this.filter : this.filter.toLowerCase(),
          "g"
        );

        this.filtered_log = [];
        this.matches = {};

        let lines = this.log.match(/[^\r\n]+/g); // split log into lines  todo: platform-agnostic ~ line endings
        let filtered_lines = [];

        for (let i = 0; i < lines.length; i++) {
          let matches = [];
          let raw_matches = this.case_sensitive
            ? [...lines[i].matchAll(re)]
            : [...lines[i].toLowerCase().matchAll(re)];

          // console.log(raw_matches);
          // console.log(lines[i]);

          for (let match in raw_matches) {
            // console.log(`line ${i} match: ${match}`);
            matches = [...matches, match];
          }

          // for (const match of matches) {
          //   console.log(
          //     `Found ${match[0]} start=${match.index} end=${
          //       match.index + match[0].length
          //     }.`
          //   );
          // }

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
    },
  },
  watch: {
    log() {
      this.handleLogText();
    },
  },
};
</script>

<style lang="scss" scoped>
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

.filter-field {
  height: $header-item-height !important;
}
</style>
