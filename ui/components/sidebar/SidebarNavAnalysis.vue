<template>
  <div
    class="nav-item nav-dropdown nav-analysis"
    :ref="ref"
    v-if="status !== undefined"
  >
    <div
      class="nav-link nav-dropdown-toggle"
      @click="handleDropdownClick"
      :id="ref"
    >
      <template v-if="name !== undefined">
        <div class="analysis-name">{{ name }}</div>
        <div class="analysis-name-fade" />
      </template>
      <Waiting v-else />
    </div>
    <b-progress
      height="2px"
      :class="{
        'sidebar-progress': true,
        busy: status.busy,
        error: status.state === ast.ERROR,
        canceled: status.state === ast.CANCELED,
        done: status.state === ast.DONE,
      }"
      v-bind:value="status.progress"
      max="1"
    ></b-progress>
    <ul class="nav-dropdown-items">
      <SidebarNavAnalysisLink
        name="Configure"
        icon="icon-equalizer"
        :id="link.configure"
        :disabled="[undefined, ast.ANALYZING].includes(status.state)"
      />
      <SidebarNavAnalysisLink
        name="Set alignment"
        icon="icon-frame"
        :id="link.align"
        :disabled="
          [
            undefined,
            ast.UNKNOWN,
            ast.INCOMPLETE,
            ast.CAN_LAUNCH,
            ast.ANALYZING,
          ].includes(status.state)
        "
      />
      <SidebarNavAnalysisLink
        name="Set filters"
        icon="icon-layers"
        :id="link.filter"
        :enabled="
          [
            ast.CAN_FILTER,
            ast.CAN_ANALYZE,
            ast.DONE,
            ast.CANCELED,
            ast.ERROR,
          ].includes(status.state)
        "
      />
      <template v-if="status.state === ast.ANALYZING">
        <SidebarNavAnalysisLink
          name="Cancel"
          icon="icon-ban"
          :id="link.cancel"
        />
      </template>
      <template v-else>
        <SidebarNavAnalysisLink
          name="Analyze"
          icon="icon-control-play"
          :id="link.analyze"
          :enabled="
            [ast.CAN_ANALYZE, ast.CANCELED, ast.ERROR].includes(status.state)
          "
        />
      </template>
      <SidebarNavAnalysisLink
        name="Results"
        icon="icon-graph"
        :id="link.result"
        :disabled="
          ![ast.CAN_ANALYZE, ast.DONE, ast.CANCELED, ast.ERROR].includes(
            status.state
          )
        "
      />
      <SidebarNavAnalysisLink
        name="Close"
        icon="icon-close"
        :two_stage="true"
        :id="event.close"
        :disabled="[undefined, ast.ANALYZING].includes(status.state)"
      />
    </ul>
  </div>
</template>

<script>
import SidebarNavAnalysisLink from "./SidebarNavAnalysisLink";
import Waiting from "./Waiting";

import {
  AnalyzerState as ast,
  analyze,
  close,
  cancel,
  AnalyzerState,
} from "../../static/api";

import { events } from "../../static/events";

// todo: should do color/icon resolution in a separate .js module, should be shared with e.g. dashboard
export default {
  props: {
    id: {
      type: String,
      required: true,
    },
  },
  components: {
    SidebarNavAnalysisLink,
    Waiting,
  },
  created() {
    // this.$root.$on(this.event.status, this.handleUpdateStatus);
    this.$root.$on(this.event.close, this.handleRemove);
    this.$root.$on(this.event.cancel, this.handleCancel);
    this.$root.$on(this.event.open, this.handleOpen);
  },
  destroyed() {
    // this.$root.$off(this.event.status, this.handleUpdateStatus);
    this.$root.$off(this.event.close, this.handleRemove);
    this.$root.$off(this.event.cancel, this.handleCancel);
    this.$root.$off(this.event.open, this.handleOpen);
  },
  methods: {
    handleDropdownClick(e) {
      e.preventDefault();
      e.target.parentElement.classList.toggle("open");
    },
    handleOpen() {
      // console.log(`${this.id} got open event`);
      this.$refs[this.ref].classList.add("open");
    },
    handleAnalyze() {
      this.$store.dispatch("analyzers/analyze", { id: this.id });
    },
    handleRemove() {
      // console.log(`sidebar: handling close event (${this.id})`);
      if (this.$route.query.id === this.id) {
        // navigate away from closed analyzer
        this.$router.push("/");
      }
      this.$store.dispatch("analyzers/close", { id: this.id });
    },
    handleCancel() {
      // console.log(`sidebar: handling cancel event (${this.id})`);
      cancel(this.id).then(() => {
        this.$store.dispatch("analyzers/sync");
      });
    },
  },
  computed: {
    name() {
      var name;
      try {
        return this.$store.getters["analyzers/getName"](this.id);
      } catch (err) {
        console.warn(`no such analyzer: ${this.id}`);
        return undefined;
      }
    },
    ref() {
      return `dropdown-${this.id}`;
    },
    link() {
      return {
        configure: `/analysis/configure?id=${this.id}`,
        align: `/analysis/align?id=${this.id}`,
        filter: `/analysis/filter?id=${this.id}`,
        result: `/analysis/result?id=${this.id}`,
        cache: `/api/${this.id}/call/cache`,
        analyze: `/api/${this.id}/call/analyze`,
        cancel: `/api/${this.id}/call/cancel`,
      };
    },
    event() {
      return {
        status: events.sidebar.status(this.id),
        cancel: events.sidebar.cancel(this.id),
        close: events.sidebar.close(this.id),
        open: events.sidebar.open(this.id),
      };
    },
    status() {
      try {
        return this.$store.getters["analyzers/getAnalyzerStatus"](this.id);
      } catch (err) {
        // console.log(`no such analyzer: ${this.id}`);
        return undefined;
      }
    },
  },
  data() {
    return {
      ast: ast,
      // status: {
      //   state: ast.UNKNOWN,
      //   busy: false,
      //   progress: 0,
      //   position: 0
      // }
    };
  },
};
</script>

<style lang="scss">
// should not be scoped!
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

$padding: 0.5rem; // CoreUI
$fade: 1.5rem;
$spacing: 1.85rem;
$name-height: calc(#{$header-height} - 2 * #{$padding});
$fade-margin: -$name-height;
$name-width: calc(#{$sidebar-width} - #{$spacing});

.analysis-name {
  pointer-events: none;
  box-sizing: border-box;
  max-height: $name-height;
  max-width: $name-width;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: clip;
  -o-text-overflow: ellipsis; /* opera */
}

.analysis-name-fade {
  pointer-events: none;
  background: ghostwhite;
  min-height: $name-height;
  max-width: $fade;
  min-width: $fade;
  margin-top: calc(#{$name-height} * -1);
  margin-left: calc(#{$sidebar-width} - #{$fade} - #{$spacing});
  mix-blend-mode: darken;
  background: linear-gradient(to right, transparent, $gray-800);
}

.sidebar .nav-link:hover {
  .analysis-name-fade {
    background: linear-gradient(to right, transparent, theme-color("primary"));
  }
}

.sidebar-progress * {
  /*transition-duration: 0.25s !important;*/
  transition: none !important;
}

.sidebar-progress.error * {
  background-color: theme-color("danger") !important;
}

.sidebar-progress.done * {
  background-color: theme-color("success") !important;
}

.sidebar-progress.canceled * {
  background-color: theme-color("warning") !important;
}
</style>
