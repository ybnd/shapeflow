<template>
  <!--  https://stackoverflow.com/questions/14025438 -->
  <div class="fixed-page">
    <PageHeader>
      <PageHeaderItem>
        <b-button
          class="header-button-icon"
          @click="handleClearFilters"
          data-toggle="tooltip"
          title="Clear filters"
        >
          <i class="icon-ban" />
        </b-button>
        <b-button
          class="header-button-icon"
          @click="handleUndoFilters"
          data-toggle="tooltip"
          title="Undo alignment"
          v-hotkey="keymap"
        >
          <i class="icon-action-undo" />
        </b-button>
        <b-button
          class="header-button-icon"
          @click="handleRedoFilters"
          data-toggle="tooltip"
          title="Redo alignment"
          v-hotkey="keymap"
        >
          <i class="icon-action-redo" />
        </b-button>
      </PageHeaderItem>
      <PageHeaderSeek :id="id" :key="id" />
      <PageHeaderItem>
        <b-button
          class="header-button-icon"
          @click="handleHideConfigSidebar"
          data-toggle="tooltip"
          title="Toggle configuration sidebar"
        >
          <i class="icon-menu" />
        </b-button>
      </PageHeaderItem>
      <PageHeaderItem>
        <b-button
          class="header-button-icon"
          :variant="hideVideoFrame ? 'danger' : null"
          data-toggle="tooltip"
          :title="hideVideoFrame ? 'Show video frame' : 'Hide video frame'"
          @click="hideVideoFrame = !hideVideoFrame"
          :disabled="hideStateFrame && hideOverlay"
        >
          <i class="icon-film" />
        </b-button>
        <b-button
          class="header-button-icon"
          :variant="hideStateFrame ? 'danger' : null"
          data-toggle="tooltip"
          :title="hideStateFrame ? 'Show state frame' : 'Hide state frame'"
          @click="hideStateFrame = !hideStateFrame"
          :disabled="hideVideoFrame && hideOverlay"
        >
          <i class="icon-layers" />
        </b-button>
        <b-button
          class="header-button-icon"
          :variant="hideOverlay ? 'danger' : null"
          data-toggle="tooltip"
          :title="hideStateFrame ? 'Show overlay' : 'Hide overlay'"
          @click="hideOverlay = !hideOverlay"
          :disabled="hideVideoFrame && hideStateFrame"
        >
          <i class="icon-frame" />
        </b-button>
      </PageHeaderItem>
    </PageHeader>
    <div class="filter-content">
      <ConfigSidebar
        :id="this.id"
        :key="this.id"
        :hidden="true"
        v-if="!hideConfigSidebar"
        :skip="[
          'frame_interval_setting',
          'Nf',
          'dt',
          'video_path',
          'design_path',
          'design',
          'features',
          'feature_parameters',
          'name',
          'description',
          'transform',
        ]"
      />
      <div class="filter filter-placeholder" @click="handleClick">
        <img
          v-if="!hideVideoFrame"
          :src="`${frame_url}&${opened_at}`"
          alt=""
          :class="
            hideConfigSidebar ? 'streamed-image-f' : 'streamed-image-f with-cs'
          "
          :ref="ref_frame"
        />
        <img
          v-if="!hideOverlay"
          :src="`${overlay_url}?${opened_at}`"
          alt=""
          class="overlay"
          :class="hideConfigSidebar ? 'overlay' : 'overlay with-cs'"
        />
        <img
          v-if="!hideStateFrame"
          :src="`${state_url}&${opened_at}`"
          alt=""
          class="overlay-state"
          :class="hideConfigSidebar ? 'overlay-state' : 'overlay-state with-cs'"
        />
      </div>
    </div>
  </div>
</template>

<script>
import {
  set_filter,
  api,
  undo_config,
  redo_config,
  analyze,
  stop_stream,
  endpoints,
  clear_filters,
} from "../../static/api";
import { events } from "../../static/events";

import PageHeader from "../../components/header/PageHeader";
import PageHeaderItem from "../../components/header/PageHeaderItem";
import PageHeaderSeek from "../../components/header/PageHeaderSeek";
import ConfigSidebar from "../../components/config/ConfigSidebar";
import { throttle, debounce } from "throttle-debounce";
import { clickEventToRelativeCoordinate } from "../../static/coordinates";

import cloneDeep from "lodash/cloneDeep";
import Vue from "vue";
import AsyncComputed from "vue-async-computed";

Vue.use(AsyncComputed);

export default {
  name: "analyzer-filter",
  beforeMount() {
    this.handleInit();
    window.addEventListener("resize", this.updateFrame);
  },
  beforeDestroy() {
    this.handleCleanUp();
    window.removeEventListener("resize", this.updateFrame);
  },
  components: {
    PageHeader,
    PageHeaderItem,
    PageHeaderSeek,
    ConfigSidebar,
  },
  methods: {
    handleInit() {
      // console.log("filter: handleInit()");
      this.previous_id = this.id;
      this.$store.dispatch("analyzers/refresh", { id: this.id });

      this.opened_at = Date.now();

      // Check if this.id is queued. If not, navigate to /
      // if (this.$store.getters["analyzers/isValidId"](this.id) === false) {
      if (this.$store.getters["analyzers/getIndex"](this.id) === -1) {
        this.$router.push(`/`);
      } else {
        this.$root.$emit(events.sidebar.open(this.id));

        this.$store.dispatch("analyzers/get_config", { id: this.id });

        this.waitUntilHasRect = setInterval(this.updateFrameOnceHasRect, 100);
        this.waitForMasks = setInterval(this.getMasks, 100);
        this.waitForFeatures = setInterval(this.getFeatures, 100);
      }
    },
    handleCleanUp() {
      // console.log("filter: handleCleanUp()");

      stop_stream(this.previous_id, endpoints.GET_FRAME);
      stop_stream(this.previous_id, endpoints.GET_STATE_FRAME);

      clearInterval(this.waitUntilHasRect);
      clearInterval(this.waitForFeatures);
      clearInterval(this.waitForMasks);

      this.filter = {
        frame: null,
      };
      this.refs = {
        frame: null,
      };
    },
    getRefs() {
      // console.log("filter: getRefs()");

      // console.log("this.ref_frame = ");
      // console.log(this.ref_frame);

      // console.log("this.$refs attrs = ");
      // console.log(Object.keys(this.$refs));

      // console.log("this.$refs[this.ref_frame] = ");
      // console.log(this.$refs[this.ref_frame]);

      this.refs.frame = this.$refs[this.ref_frame];
    },
    getFeatures() {
      // console.log("filter: getFeatures()");
      this.features = this.$store.getters["analyzers/getFeatures"](this.id);
      this.feature = this.features[0];
      if (this.features.length !== 0) {
        // console.log("filter: getFeatures() -- clearing interval");
        clearInterval(this.waitForFeatures);
      }
      // console.log(this.features);
    },
    updateFrame() {
      // console.log("filter: updateFrame");
      try {
        let frame = this.refs.frame.getBoundingClientRect();
        // console.log(frame);
        this.filter.frame = frame;
      } catch (err) {
        // console.warn(err);
      }
    },
    updateFrameOnChange() {
      // console.log("filter: updateFrameOnChange");
      const og_width = this.refs.frame.getBoundingClientRect().width;

      while (this.refs.frame.getBoundingClientRect().width === og_width) {
        // console.log("frame is still the same");
      }
      // console.log("frame has changed");
      this.updateFrame();
    },
    updateFrameOnceHasRect() {
      // todo: clean up
      let frame_ok = false;
      let overlay_ok = false;
      this.getRefs();

      if (!(this.waitUntilHasRect === undefined)) {
        if (this.refs.frame.getBoundingClientRect()["width"] > 50) {
          // console.log("HAS FRAME");
          this.updateFrame();
          frame_ok = true;
        }
      }
      if (frame_ok) {
        clearInterval(this.waitUntilHasRect);
      }
    },
    handleClick(e) {
      set_filter(
        this.id,
        clickEventToRelativeCoordinate(e, this.filter.frame)
      ).then((data) => {
        if (data.message) {
          // console.log(`//PUT THIS IN A POPUP OR SOMETHING// ${data.message}`);
        }
      });
    },
    handleClearFilters() {
      clear_filters(this.id);
    },
    handleUndoFilters() {
      undo_config(this.id, "masks");
    },
    handleRedoFilters() {
      redo_config(this.id, "masks");
    },
    stepForward() {
      this.$root.$emit(events.seek.step_fw(this.id));
    },
    stepBackward() {
      this.$root.$emit(events.seek.step_bw(this.id));
    },
    handleHideConfigSidebar() {
      this.hideConfigSidebar = !this.hideConfigSidebar;
      this.waitUntilHasRect = setInterval(this.updateFrameOnceHasRect, 100);
    },
  },
  watch: {
    "$route.query.id"() {
      // console.log(`id has changed ${this.id}`);

      // this.$forceUpdate();
      this.handleCleanUp();
      this.handleInit();
      this.updateFrame();
    },
    "refs.frame.class"() {
      // console.log("waaa this is a change");
    },
  },
  asyncComputed: {},
  computed: {
    id() {
      return this.$route.query.id;
    },
    state_url() {
      return `/api/va/stream?id=${this.$route.query.id}&endpoint=${endpoints.GET_STATE_FRAME}`;
    },
    frame_url() {
      return `/api/va/stream?id=${this.$route.query.id}&endpoint=${endpoints.GET_FRAME}`;
    },
    overlay_url() {
      return api("va", this.$route.query.id, endpoints.GET_OVERLAY_PNG);
    },
    ref_frame() {
      return `filter-frame-${this.$route.query.id}`;
    },
    keymap() {
      return {
        "ctrl+z": this.handleUndoFilters,
        "ctrl+shift+z": this.handleRedoFilters,
        right: this.stepForward,
        left: this.stepBackward,
      };
    },
    config() {
      return this.$store.getters["analyzers/getAnalyzerConfig"](
        this.$route.query.id
      );
    },
    masks() {
      if (this.config !== undefined) {
        return this.config.masks.map(({ name }) => name);
      } else {
        return [];
      }
    },
    filter_options() {
      // console.log('this.$store.getters["schemas/getFilterOptions"]');
      // console.log(this.$store.getters["schemas/getFilterOptions"]);
      return this.$store.getters["schemas/getFilterOptions"];
    },
    filter_type() {
      if (this.config !== undefined) {
        return this.config.masks[this.mask].filter.type;
      } else {
        return undefined;
      }
    },
  },
  data: () => ({
    opened_at: 0,
    waitUntilHasRect: null,
    waitForMasks: null,
    waitForFeatures: null,
    mask: 0,
    filter: {
      frame: null,
    },
    refs: {
      frame: null,
    },
    hideConfigSidebar: true,
    hideVideoFrame: false,
    hideStateFrame: false,
    hideOverlay: false,
  }),
};
</script>

<style lang="scss">
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

.filter {
  z-index: 100; /* has to be top of fixed-page etc. to handle clicks*/
  /*position: relative;*/
  /*float: left;*/
  /*display: block;*/
  margin: 0 0 0 0;
  height: $content-height;
  width: $content-width;
  /* Disable double-click selection */
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
  -o-user-select: none;
  user-select: none;
  overflow: hidden;
}

.with-cs {
  max-width: calc(
    100vw - #{$sidebar-width} - #{$config-sidebar-width}
  ) !important;
}

.streamed-image-f {
  display: inline;
  max-width: $content-width;
  max-height: $content-height;
  //width: auto;
  //height: auto;
  float: left;
  position: absolute;
  pointer-events: none;
}

.overlay {
  display: inline;
  max-width: $content-width;
  max-height: $content-height;
  //width: auto;
  //height: auto;
  float: left;
  position: absolute;
  pointer-events: none;
  opacity: 0.15;
}

.overlay-state {
  mix-blend-mode: multiply;
  display: inline;
  max-width: $content-width;
  max-height: $content-height;
  //width: auto;
  //height: auto;
  float: left;
  position: absolute;
  pointer-events: none;
}

.hidden * {
  visibility: hidden;
}

.button-hidden {
  background: theme-color("danger") !important;
  color: theme-color("gray-100") !important;
  font-weight: bold;
}

.filter-content {
  display: flex;
  flex-direction: row;
}

.filter-placeholder {
  /*background: #ff0000;*/
  flex-grow: 1;
  height: calc(100vh - #{$header-height});
}
</style>
