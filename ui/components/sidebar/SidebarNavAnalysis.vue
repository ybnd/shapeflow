<template>
  <div class="nav-item nav-dropdown" :ref="ref" v-if="status !== undefined">
    <div
      class="nav-link nav-dropdown-toggle"
      @click="handleDropdownClick"
      :id="ref"
    >
      <!--      <b-popover-->
      <!--        class="analysis-info-popover"-->
      <!--        :target="'dropdown-' + id"-->
      <!--        container="body"-->
      <!--        placement="right"-->
      <!--        boundary="viewport"-->
      <!--        triggers="hover focus click"-->
      <!--        :delay="{ show: 500, hide: 25 }"-->
      <!--      >-->
      <!--        <div class="analysis-info-line">-->
      <!--          <i class="fa fa-file-video-o" /> {{ config.video_path }}-->
      <!--        </div>-->
      <!--        <div class="analysis-info-line">-->
      <!--          <i class="fa fa-file-code-o" /> {{ config.design_path }}-->
      <!--        </div>-->
      <!--      </b-popover>-->
      {{ name }}
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
            [ast.CAN_ANALYZE, ast.CANCELED, ast.DONE, ast.ERROR].includes(
              status.state
            )
          "
        />
      </template>
      <SidebarNavAnalysisLink
        name="Results"
        icon="icon-graph"
        :id="link.result"
        :disabled="![ast.DONE, ast.CANCELED, ast.ERROR].includes(status.state)"
      />
      <SidebarNavAnalysisLink
        name="Remove"
        icon="icon-trash"
        :two_stage="true"
        :id="event.remove"
        :disabled="[undefined, ast.ANALYZING].includes(status.state)"
      />
    </ul>
  </div>
</template>

<script>
import SidebarNavAnalysisLink from "./SidebarNavAnalysisLink";
import {
  AnalyzerState as ast,
  analyze,
  remove,
  cancel,
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
  },
  created() {
    // this.$root.$on(this.event.status, this.handleUpdateStatus);
    this.$root.$on(this.event.remove, this.handleRemove);
    this.$root.$on(this.event.cancel, this.handleCancel);
    this.$root.$on(this.event.open, this.handleOpen);
  },
  destroyed() {
    // this.$root.$off(this.event.status, this.handleUpdateStatus);
    this.$root.$off(this.event.remove, this.handleRemove);
    this.$root.$off(this.event.cancel, this.handleCancel);
    this.$root.$off(this.event.open, this.handleOpen);
  },
  methods: {
    handleDropdownClick(e) {
      e.preventDefault();
      e.target.parentElement.classList.toggle("open");
    },
    handleOpen() {
      console.log(`${this.id} got open event`); // todo: doesn't seem to work
      this.$refs[this.ref].classList.add("open");
    },
    handleAnalyze() {
      this.$store.dispatch("analyzers/analyze", { id: this.id });
    },
    handleRemove() {
      console.log(`sidebar: handling remove event (${this.id})`);
      remove(this.id).then(() => {
        if (
          this.$route.query.id === this.id ||
          this.$route.query.id === undefined
        ) {
          this.$router.push("/");
        }
        this.$store.dispatch("analyzers/sync"); // todo: this doesn't help
      });
    },
    handleCancel() {
      console.log(`sidebar: handling cancel event (${this.id})`);
      cancel(this.id).then(() => {
        this.$store.dispatch("analyzers/sync");
      });
    },
  },
  computed: {
    name() {
      try {
        return this.$store.getters["analyzers/getName"](this.id);
      } catch (err) {
        console.log(`no such analyzer: ${this.id}`);
        return "";
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
        remove: events.sidebar.remove(this.id),
        open: events.sidebar.open(this.id),
      };
    },
    status() {
      try {
        return this.$store.getters["analyzers/getAnalyzerStatus"](this.id);
      } catch (err) {
        console.log(`no such analyzer: ${this.id}`);
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
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

.sidebar-progress * {
  /*transition-duration: 0.25s !important;*/
  transition: none !important;
}

/* todo: make sure this overrides busy */
.sidebar-progress.error * {
  background-color: theme-color("danger") !important;
}

/* todo: make sure this overrides busy */
.sidebar-progress.done * {
  background-color: theme-color("success") !important;
}

/* todo: make sure this overrides busy */
.sidebar-progress.canceled * {
  background-color: theme-color("warning") !important;
}
</style>
