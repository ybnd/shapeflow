<template>
  <div class="nav-item nav-dropdown">
    <div
      class="nav-link nav-dropdown-toggle"
      @click="handleClick"
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
          :url="`/analysis/configure?id=${id}`"
        />
        <SidebarNavAnalysisLink
          name="Remove"
          icon="icon-trash"
          :url="`/api/analyzer/quit/${id}`"
          :two_stage="true"
        />
      </ul>
    </template>
    <template v-if="state === ast.LAUNCHED">
      <ul class="nav-dropdown-items">
        <SidebarNavAnalysisLink
          name="Configure"
          icon="icon-equalizer"
          :url="`/analysis/configure?id=${id}`"
        />
        <SidebarNavAnalysisLink
          name="Set alignment"
          icon="icon-frame"
          :url="`/analysis/align?id=${id}`"
        />
        <SidebarNavAnalysisLink
          name="Set filters"
          icon="icon-layers"
          :url="`/analysis/filter?id=${id}`"
        />
        <SidebarNavAnalysisLink
          name="Remove"
          icon="icon-trash"
          :url="`/api/analyzer/quit/${id}`"
          :two_stage="true"
        />
      </ul>
    </template>
    <template v-else-if="state === ast.CAN_LAUNCH">
      <ul class="nav-dropdown-items">
        <SidebarNavAnalysisLink
          name="Configure"
          icon="icon-equalizer"
          :url="`/analysis/configure?id=${id}`"
        />
        <SidebarNavAnalysisLink
          name="Remove"
          icon="icon-trash"
          :url="`/api/analyzer/${id}/quit`"
          :two_stage="true"
        />
      </ul>
    </template>
    <template v-else-if="state === ast.RUNNING">
      <b-progress class="progress" height="2px" :value="progress"></b-progress>
      <ul class="nav-dropdown-items">
        <SidebarNavAnalysisLink
          name="Monitor"
          icon="icon-graph"
          :url="`/analysis/monitor?id=${id}`"
        />
        <SidebarNavAnalysisLink
          name="Cancel"
          icon="icon-ban"
          :url="`/api/analyzer/${id}/cancel`"
          :two_stage="true"
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
          :url="`/analysis/configure?id=${id}`"
        />
        <SidebarNavAnalysisLink
          name="Set alignment"
          icon="icon-frame"
          :url="`/analysis/align?id=${id}`"
        />
        <SidebarNavAnalysisLink
          name="Set filters"
          icon="icon-layers"
          :url="`/analysis/filter?id=${id}`"
        />
        <SidebarNavAnalysisLink
          name="Run"
          icon="icon-control-play"
          :url="`/api/analyzer/${id}/analyze`"
        />
        <SidebarNavAnalysisLink
          name="Remove"
          icon="icon-trash"
          :url="`/api/analyzer/${id}/quit`"
          :two_stage="true"
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
          :url="`/analysis/configure?id=${id}`"
        />
        <SidebarNavAnalysisLink
          name="Set alignment"
          icon="icon-frame"
          :url="`/analysis/align?id=${id}`"
        />
        <SidebarNavAnalysisLink
          name="Set filters"
          icon="icon-layers"
          :url="`/analysis/filter?id=${id}`"
        />
        <SidebarNavAnalysisLink
          name="Run"
          icon="icon-control-play"
          :url="`/api/analyzer/${id}/analyze`"
        />
        <SidebarNavAnalysisLink
          name="Remove"
          icon="icon-trash"
          :url="`/api/analyzer/${id}/quit`"
          :two_stage="true"
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
          :url="`/analysis/configure?id=${id}`"
        />
        <SidebarNavAnalysisLink
          name="Set alignment"
          icon="icon-frame"
          :url="`/analysis/align?id=${id}`"
        />
        <SidebarNavAnalysisLink
          name="Set filters"
          icon="icon-layers"
          :url="`/analysis/filter?id=${id}`"
        />
        <SidebarNavAnalysisLink
          name="Run"
          icon="icon-control-play"
          :url="`/api/analyzer/${id}/analyze`"
        />
        <SidebarNavAnalysisLink
          name="Remove"
          icon="icon-trash"
          :url="`/api/analyzer/${id}/quit`"
          :two_stage="true"
        />
      </ul>
    </template>
  </div>
</template>

<script>
import SidebarNavAnalysisLink from "./SidebarNavAnalysisLink";
import { AnalyzerState as ast } from "../../static/api";

import { mapGetters, mapState, mapActions } from "vuex";

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
  methods: {
    handleClick(e) {
      e.preventDefault();
      e.target.parentElement.classList.toggle("open");
    }
  },
  computed: {
    classList() {
      return ["nav-link"];
    },
    name() {
      console.log(`Name is`);
      let name = this.$store.getters["analyzers/getName"](this.id);
      console.log(name);
      return name;
    },
    state() {
      console.log(`State is`);
      let state = this.$store.getters["analyzers/getState"](this.id);
      console.log(state);
      return state;
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
