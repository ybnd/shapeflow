<template>
  <div class="fixed-page">
    <PageHeader>
      <PageHeaderItem>
        <b-button
          class="header-button-icon log-button log-follow"
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
            class="shapeflow-form-field-auto log-filter-field"
            v-model="filter"
            @input="handleSetFilter"
            placeholder="Filter log..."
          >
            {{ filter }}
          </b-form-input>
        </b-input-group>
      </PageHeaderItem>
      <PageHeaderItem>
        <b-button
          class="header-button-icon log-button log-case-sensitive"
          data-toggle="tooltip"
          :title="case_sensitive ? 'Ignore case' : 'Case sensitive filter'"
          :variant="case_sensitive ? 'danger' : null"
          @click="handleCaseSensitive"
        >
          <i class="fa fa-exclamation" />
        </b-button>
      </PageHeaderItem>
    </PageHeader>
    <div class="log-content" ref="view">
      <b-tbody class="log-table" ref="log" @scroll="handleScroll">
        <tr
          v-for="(row, index) in filtered_lines"
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
import { api } from "../src/api";
import {splitlines} from "../src/util";
import { debounce, throttle } from "throttle-debounce";
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
      filtered_lines: "",
      matches: {},
      followTimeout: undefined,
    };
  },
  mounted() {
    this.request = api.log();
    this.request.addEventListener('progress', (e) => {
      this.log = e.target.responseText;
    });
    setTimeout(() => {
      this.followInterval = setInterval(() => {
        if (this.follow && !this.release) {
          this.scrollNow();
        }
      }, FOLLOW_INTERVAL);
    }, 1000);
  },
  beforeDestroy() {
    api.stop_log();
    clearInterval(this.followInterval);
  },
  methods: {
    handleLogText() {
      this.filterLog();
      if (!this.release && (this.follow || this.isAtLimit()) ) {
        this.scrollNow();
      }
    },
    isAtLimit() {
      try {
        const top = this.$refs.log.$el.scrollTop;
        const left = this.$refs.log.$el.scrollLeft;
        const topMax = this.$refs.log.$el.scrollTopMax;

        console.log(`top=${top} topMax=${topMax} left=${left} -> ${Math.abs(top - topMax) < SCROLL_TOLERANCE_V && left < SCROLL_TOLERANCE_H}`)

        return Math.abs(top - topMax) < SCROLL_TOLERANCE_V && left < SCROLL_TOLERANCE_H;
      } catch(e) {
        console.warn(e);
      }
      return false;
    },
    scrollNow() {
      try {
        if (!this.isAtLimit()) {
          console.log(`log.scrollNow() scrolling: ${this.$refs.log.$el.scrollTop} -> ${this.$refs.log.$el.scrollTopMax + 50}`)

          this.$refs.log.$el.scrollTop = this.$refs.log.$el.scrollTopMax + 50;
          this.$refs.log.$el.scrollLeft = 0;
        }
      } catch(e) {
        console.warn(e);
      }
    },
    handleFollow() {
      this.follow = !this.follow;
      if (this.follow) {
        this.scrollNow();
      }
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
    handleSetFilter() {
      this.handleFilterLog();
    },
    filterLog() {
      // console.log("log.filterLog()");
      this.filter = this.filter.trim();

      if (this.filter) {
        // reset filter data

        const re = new RegExp(
          this.case_sensitive ? this.filter : this.filter.toLowerCase(),
          "g"
        );

        this.filtered_lines = [];
        this.matches = {};

        let lines = splitlines(this.log);
        let filtered_lines = [];

        for (let i = 0; i < lines.length; i++) {
          let matches = [];
          let raw_matches = this.case_sensitive
            ? [...lines[i].matchAll(re)]
            : [...lines[i].toLowerCase().matchAll(re)];

          for (let match in raw_matches) {
            matches = [...matches, match];
          }

          if (matches.length > 0) {
            this.filtered_lines = [...this.filtered_lines, lines[i]];
            this.matches = { ...this.matches, [i]: matches };
          }
        }
      } else {
        this.filtered_lines = splitlines(this.log);
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

.log-content {
  height: calc(100vh - #{$header-height});
  width: calc(100vw - #{$sidebar-width});
  display: flex;
  flex-flow: column;
}
.log-table {
  flex: 1 1 auto;
  overflow: auto;
  font-family: Hack, monospace;
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

.log-filter-field {
  height: $header-item-height !important;
}
</style>
