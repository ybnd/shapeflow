<template>
  <div class="nav-item nav-dropdown">
    <div
      class="nav-link nav-dropdown-toggle"
      @click="handleDropdownClick"
      :id="'dropdown-' + id"
    >
      <!--      <b-popover class="analysis-info-popover"-->
      <!--        :target="'dropdown-'+id" container="body" placement="right" boundary="viewport"-->
      <!--        triggers="hover focus click" :delay="{'show': 500, 'hide': 25}">-->
      <!--        <div class="analysis-info-line">-->
      <!--          <i class="fa fa-file-video-o"/> {{config.video_path}}-->
      <!--        </div>-->
      <!--        <div class="analysis-info-line">-->
      <!--          <i class="fa fa-file-code-o"/> {{config.design_path}}-->
      <!--        </div>-->

      <!--      </b-popover>-->
      {{ name }}
    </div>
    <template v-if="state === ast.INCOMPLETE">
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
    <template v-if="state === ast.LAUNCHED">
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
    <template v-else-if="state === ast.CAN_LAUNCH">
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
    <template v-if="state === ast.CAN_RUN">
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
          @click="handleAnalyze"
        />
        <SidebarNavAnalysisLink
          name="Remove"
          icon="icon-trash"
          :two_stage="true"
          :id="event.remove"
        />
      </ul>
    </template>
    <template v-else-if="state === ast.RUNNING">
      <b-progress class="progress" height="2px" :value="progress"></b-progress>
      <ul class="nav-dropdown-items">
        <SidebarNavAnalysisLink
          name="Cancel"
          icon="icon-ban"
          :two_stage="true"
          :id="event.cancel"
        />
      </ul>
    </template>
    <template v-else-if="state === ast.DONE">
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
    <template v-else-if="state === ast.CANCELED">
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
    <template v-else-if="state === ast.ERROR">
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
  beforeMount() {
    this.$root.$on(this.event.remove, this.handleRemove);
    this.$root.$on(this.event.cancel, this.handleCancel);
  },
  destroyed() {
    // todo: unregister listeners!
  },
  methods: {
    handleDropdownClick(e) {
      e.preventDefault();
      e.target.parentElement.classList.toggle("open");
    },
    syncStore() {
      this.$store.dispatch("analyzers/sync");
    },
    handleAnalyze() {
      analyze(this.id).then(() => {
        this.syncStore();
      });
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
        this.syncStore();
      });
    },
    handleCancel() {
      console.log(`sidebar: handling cancel event (${this.id})`);
      cancel(this.id).then(() => {
        this.syncStore();
      });
    }
  },
  computed: {
    classList() {
      return ["nav-link"];
    },
    name() {
      return this.$store.getters["analyzers/getName"](this.id);
    },
    state() {
      return this.$store.getters["analyzers/getState"](this.id);
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
        cancel: `event-cancel-${this.id}`,
        remove: `event-remove-${this.id}`
      };
    }
  },
  data() {
    return {
      show: false,
      ast: ast
    };
  }
};
</script>

<style>
.analysis-info-popover {
  min-width: 25px;
  max-width: 400px;
}
.analysis-info-line {
}
</style>
