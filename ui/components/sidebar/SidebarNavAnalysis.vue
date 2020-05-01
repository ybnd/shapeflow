<template>
  <div class="nav-item nav-dropdown">
    <div
      class="nav-link nav-dropdown-toggle"
      @click="handleDropdownClick"
      :id="'dropdown-' + id"
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
    <template v-if="status.progress > 0">
      <b-progress
        height="2px"
        :class="{
          'sidebar-progress': true,
          busy: status.busy,
          error: status.state === ast.ERROR,
          canceled: status.state === ast.CANCELED,
          done: status.state === ast.DONE
        }"
        v-bind:value="status.progress"
        max="1"
      ></b-progress>
    </template>
    <template v-if="status.state === ast.INCOMPLETE">
      <ul class="nav-dropdown-items">
        <SidebarNavAnalysisLink
          name="Configure"
          icon="icon-equalizer"
          :id="link.configure"
        />
        <SidebarNavAnalysisLink
          name="Remove"
          icon="icon-trash"
          :two_stage="true"
          :id="event.remove"
        />
      </ul>
    </template>
    <template v-if="status.state === ast.LAUNCHED">
      <ul class="nav-dropdown-items">
        <SidebarNavAnalysisLink
          name="Configure"
          icon="icon-equalizer"
          :id="link.configure"
        />
        <SidebarNavAnalysisLink
          name="Set alignment"
          icon="icon-frame"
          :id="link.align"
        />
        <SidebarNavAnalysisLink
          name="Set filters"
          icon="icon-layers"
          :id="link.filter"
        />
        <SidebarNavAnalysisLink
          name="Remove"
          icon="icon-trash"
          :two_stage="true"
          :id="event.remove"
        />
      </ul>
    </template>
    <template v-else-if="status.state === ast.CAN_LAUNCH">
      <ul class="nav-dropdown-items">
        <SidebarNavAnalysisLink
          name="Configure"
          icon="icon-equalizer"
          :id="link.configure"
        />
        <SidebarNavAnalysisLink
          name="Remove"
          icon="icon-trash"
          :two_stage="true"
          :id="event.remove"
        />
      </ul>
    </template>
    <template v-if="status.state === ast.CAN_RUN">
      <ul class="nav-dropdown-items">
        <SidebarNavAnalysisLink
          name="Configure"
          icon="icon-equalizer"
          :id="link.configure"
        />
        <SidebarNavAnalysisLink
          name="Set alignment"
          icon="icon-frame"
          :id="link.align"
        />
        <SidebarNavAnalysisLink
          name="Set filters"
          icon="icon-layers"
          :id="link.filter"
        />
        <SidebarNavAnalysisLink
          name="Analyze"
          icon="icon-control-play"
          :id="link.analyze"
        />
        <SidebarNavAnalysisLink
          name="Remove"
          icon="icon-trash"
          :two_stage="true"
          :id="event.remove"
        />
      </ul>
    </template>
    <template v-else-if="status.state === ast.RUNNING">
      <ul class="nav-dropdown-items">
        <SidebarNavAnalysisLink
          name="Cancel"
          icon="icon-ban"
          :two_stage="true"
          :id="event.cancel"
        />
      </ul>
    </template>
    <template v-else-if="status.state === ast.DONE">
      <b-progress
        class="progress"
        height="2px"
        :value="progress"
        variant="success"
      ></b-progress>
      <ul class="nav-dropdown-items">
        <SidebarNavAnalysisLink
          name="Configure"
          icon="icon-equalizer"
          :id="link.configure"
        />
        <SidebarNavAnalysisLink
          name="Set alignment"
          icon="icon-frame"
          :id="link.align"
        />
        <SidebarNavAnalysisLink
          name="Set filters"
          icon="icon-layers"
          :id="filter"
        />
        <SidebarNavAnalysisLink
          name="Remove"
          icon="icon-trash"
          :two_stage="true"
          :id="event.remove"
        />
      </ul>
    </template>
    <template v-else-if="status.state === ast.CANCELED">
      <b-progress
        class="progress"
        height="2px"
        :value="progress"
        variant="warning"
      ></b-progress>
      <ul class="nav-dropdown-items">
        <SidebarNavAnalysisLink
          name="Configure"
          icon="icon-equalizer"
          :id="link.configure"
        />
        <SidebarNavAnalysisLink
          name="Set alignment"
          icon="icon-frame"
          :id="link.align"
        />
        <SidebarNavAnalysisLink
          name="Set filters"
          icon="icon-layers"
          :id="filter"
        />
        <SidebarNavAnalysisLink
          name="Analyze"
          icon="icon-control-play"
          :id="link.analyze"
        />
        <SidebarNavAnalysisLink
          name="Remove"
          icon="icon-trash"
          :two_stage="true"
          :id="event.remove"
        />
      </ul>
    </template>
    <template v-else-if="status.state === ast.ERROR">
      <b-progress
        class="progress"
        height="2px"
        :value="progress"
        variant="danger"
      ></b-progress>
      <ul class="nav-dropdown-items">
        <SidebarNavAnalysisLink
          name="Configure"
          icon="icon-equalizer"
          :id="link.configure"
        />
        <SidebarNavAnalysisLink
          name="Set alignment"
          icon="icon-frame"
          :id="link.align"
        />
        <SidebarNavAnalysisLink
          name="Set filters"
          icon="icon-layers"
          :id="filter"
        />
        <SidebarNavAnalysisLink
          name="Analyze"
          icon="icon-control-play"
          :id="link.analyze"
        />
        <SidebarNavAnalysisLink
          name="Remove"
          icon="icon-trash"
          :two_stage="true"
          :id="event.remove"
        />
      </ul>
    </template>
  </div>
</template>

<script>
import SidebarNavAnalysisLink from "./SidebarNavAnalysisLink";
import {
  AnalyzerState as ast,
  analyze,
  remove,
  cancel
} from "../../static/api";

import { events } from "../../static/events";

// todo: should do color/icon resolution in a separate .js module, should be shared with e.g. dashboard
export default {
  props: {
    id: {
      type: String,
      required: true
    }
  },
  components: {
    SidebarNavAnalysisLink
  },
  mounted() {
    this.$root.$on(this.event.status, this.handleUpdateStatus);
    this.$root.$on(this.event.remove, this.handleRemove);
    this.$root.$on(this.event.cancel, this.handleCancel);
    this.$root.$on(this.event.open, this.handleOpen);
  },
  destroyed() {
    this.$root.$off(this.event.status, this.handleUpdateStatus);
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
      this.dropdown = true;
    },
    handleUpdateStatus(status) {
      this.status = status;
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
        this.syncStore(); // todo oops
      });
    },
    handleCancel() {
      console.log(`sidebar: handling cancel event (${this.id})`);
      cancel(this.id).then(() => {
        this.syncStore(); // todo oops
      });
    }
  },
  computed: {
    name() {
      return this.$store.getters["analyzers/getName"](this.id);
    },
    link() {
      return {
        configure: `/analysis/configure?id=${this.id}`,
        align: `/analysis/align?id=${this.id}`,
        filter: `/analysis/filter?id=${this.id}`,
        analyze: `/api/analyzer/${this.id}/analyze`
      };
    },
    event() {
      return {
        status: events.sidebar.status(this.id),
        cancel: events.sidebar.cancel(this.id),
        remove: events.sidebar.remove(this.id),
        open: events.sidebar.open(this.id)
      };
    }
  },
  data() {
    return {
      dropdown: false,
      ast: ast,
      status: {
        state: ast.UNKNOWN,
        busy: false,
        progress: 0,
        position: 0
      }
    };
  }
};
</script>

<style lang="scss">
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

.sidebar-progress * {
  background-color: theme-color("primary") !important;
}
.sidebar-progress.busy * {
  background-color: theme-color("secondary") !important;
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
