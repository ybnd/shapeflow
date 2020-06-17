<template>
  <!--  https://stackoverflow.com/questions/14025438 -->
  <div class="fixed-page">
    <PageHeader>
      <PageHeaderItem>
        <b-button
          class="header-button-icon"
          @click="handleClearFilters"
          data-toggle="tooltip"
          title="Clear alignment"
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
        <!-- todo: should not set features here though! -->
      </PageHeaderItem>
      <PageHeaderItem>
        <b-button-group>
          <b-dropdown :text="`${this.mask}`" data-toggle="tooltip" title="Mask">
            <b-dropdown-item
              v-for="(mask, index) in masks"
              :key="`mask-${mask}`"
              @click="handleSetMask(mask, index)"
            >
              {{ mask }}
            </b-dropdown-item>
          </b-dropdown>
          <b-dropdown
            :text="`${this.filter_type}`"
            data-toggle="tooltip"
            title="Filter type"
          >
            <b-dropdown-item
              v-for="filter in filter_options"
              :key="`filter-${filter}`"
              @click="handleSetFilter(filter)"
            >
              {{ filter }}
            </b-dropdown-item>
          </b-dropdown>
        </b-button-group>
      </PageHeaderItem>
    </PageHeader>
    <div class="filter" @click="handleClick">
      <img
        :src="`${frame_url}?${opened_at}`"
        alt=""
        class="streamed-image-f"
        :ref="ref_frame"
      />
      <img
        :src="`${overlay_url}?${opened_at}`"
        alt=""
        class="streamed-image-f overlay"
      />
      <img
        :src="`${state_url}?${opened_at}`"
        alt=""
        class="streamed-image-f overlay-state"
      />
    </div>
  </div>
</template>

<script>
import {
  get_options,
  set_filter,
  api,
  analyze,
  stop_stream,
  endpoints,
} from "../../static/api";
import { events } from "../../static/events";

import PageHeader from "../../components/header/PageHeader";
import PageHeaderItem from "../../components/header/PageHeaderItem";
import PageHeaderSeek from "../../components/header/PageHeaderSeek";
import { throttle, debounce } from "throttle-debounce";
import { clickEventToRelativeCoordinate } from "../../static/coordinates";

export default {
  name: "analyzer-filter",
  beforeMount() {
    this.handleInit();
    window.onresize = this.updateFrame;
  },
  beforeDestroy() {
    this.handleCleanUp();
  },
  components: {
    PageHeader,
    PageHeaderItem,
    PageHeaderSeek,
  },
  methods: {
    handleInit() {
      console.log("filter: handleInit()");
      this.previous_id = this.id;

      this.opened_at = Date.now();

      // Check if this.id is queued. If not, navigate to /
      if (this.$store.getters["analyzers/getIndex"](this.id) === -1) {
        this.$router.push(`/`);
      } else {
        this.$root.$emit(events.sidebar.open(this.id));

        this.waitUntilHasRect = setInterval(this.updateFrameOnceHasRect, 100);
        this.waitForMasks = setInterval(this.getMasks, 100);
        this.waitForFeatures = setInterval(this.getFeatures, 100);

        get_options("filter").then((options) => {
          this.filter_options = options;
        });

        console.log(`setting this.feature to ${this.feature}`);

        this.$store
          .dispatch("analyzers/get_config", { id: this.id })
          .then(() => {
            this.$root.$emit(events.seek.reset(this.id));
          });
      }
    },
    handleCleanUp() {
      console.log("filter: handleCleanUp()");

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
      console.log("filter: getRefs()");

      console.log("this.ref_frame = ");
      console.log(this.ref_frame);

      console.log("this.$refs attrs = ");
      console.log(Object.keys(this.$refs));

      console.log("this.$refs[this.ref_frame] = ");
      console.log(this.$refs[this.ref_frame]);

      this.refs.frame = this.$refs[this.ref_frame];
    },
    getMasks() {
      console.log("filter: getMasks()");
      this.masks = this.$store.getters["analyzers/getMasks"](this.id);
      this.mask = this.masks[0];
      this.filter_type = this.$store.getters["analyzers/getMaskFilterType"](
        this.id,
        0
      );
      if (this.masks.length !== 0) {
        if (this.masks[0] !== undefined) {
          console.log("filter: getMasks() -- clearing interval");
          clearInterval(this.waitForMasks);
        }
      }
      console.log(this.masks);
    },
    getFeatures() {
      console.log("filter: getFeatures()");
      this.features = this.$store.getters["analyzers/getFeatures"](this.id);
      this.feature = this.features[0];
      if (this.features.length !== 0) {
        console.log("filter: getFeatures() -- clearing interval");
        clearInterval(this.waitForFeatures);
      }
      console.log(this.features);
    },
    updateFrame() {
      console.log("Updating frame...");
      let frame = this.refs.frame.getBoundingClientRect();
      console.log(frame);
      this.filter.frame = frame;
    },
    updateFrameOnceHasRect() {
      // todo: clean up
      let frame_ok = false;
      let overlay_ok = false;
      this.getRefs();

      if (!(this.waitUntilHasRect === undefined)) {
        if (this.refs.frame.getBoundingClientRect()["width"] > 50) {
          console.log("HAS FRAME");
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
      ).then((message) => {
        if (message) {
          console.log(`//PUT THIS IN A POPUP OR SOMETHING// ${message}`);
        }
      });
    },
    handleSetFeature(feature) {
      this.$store
        .dispatch("analyzers/set_config", {
          id: this.id,
          config: { features: [feature] },
        })
        .then((stuff) => {
          console.log("in analyzers/set_config callback");
          let features = this.$store.getters["analyzers/getFeatures"](this.id);
          this.feature = features[0];
        });
    },
    handleSetMask(mask, index) {
      this.mask = mask;

      this.filter_type = this.$store.getters["analyzers/getMaskFilterType"](
        this.id,
        index
      );
      this.filter_data = this.$store.getters["analyzers/getMaskFilterData"](
        this.id,
        index
      );
    },
    handleSetFilter(filter) {
      let config = this.$store.getters["analyzers/getAnalyzerConfig"](this.id);
      config.masks[this.mask].filter.type = filter;

      this.$store
        .dispatch("analyzers/set_config", {
          id: this.id,
          config: config,
        })
        .then(() => {
          this.filter_type = this.$store.getters["analyzers/getMaskFilterType"](
            this.id
          );
        });
    },
    handleClearFilters() {
      console.warn("NOT IMPLEMENTED YET");
    },
    handleUndoFilters() {
      console.warn("NOT IMPLEMENTED YET");
    },
    handleRedoFilters() {
      console.warn("NOT IMPLEMENTED YET");
    },
    stepForward() {
      this.$root.$emit(events.seek.step_fw(this.id));
    },
    stepBackward() {
      this.$root.$emit(events.seek.step_bw(this.id));
    },
  },
  watch: {
    "$route.query.id"() {
      console.log(`id has changed ${this.id}`);

      // this.$forceUpdate();
      this.handleCleanUp();
      this.handleInit();
      this.updateFrame();
    },
  },
  computed: {
    id() {
      return this.$route.query.id;
    },
    state_url() {
      return api(this.$route.query.id, "stream", endpoints.GET_STATE_FRAME);
    },
    frame_url() {
      return api(this.$route.query.id, "stream", endpoints.GET_FRAME);
    },
    overlay_url() {
      return api(this.$route.query.id, "call", endpoints.GET_OVERLAY_PNG);
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
  },
  data: () => ({
    opened_at: 0,
    waitUntilHasRect: null,
    waitForMasks: null,
    waitForFeatures: null,
    filter_type: "",
    filter_options: undefined,
    filter_data: {},
    mask: "",
    masks: [],
    feature: "",
    features: [],
    filter: {
      frame: null,
    },
    refs: {
      frame: null,
    },
  }),
};
</script>

<style lang="scss">
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

.filter {
  z-index: 100; /* has to be top of fixed-page etc. to handle clicks*/
  position: absolute;
  float: left;
  display: block;
  margin: 0 0 0 0;
  height: calc(100vh - #{$header-height});
  width: calc(100vw - #{$sidebar-width});
  /* Disable double-click selection */
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
  -o-user-select: none;
  user-select: none;
}

.streamed-image-f {
  display: block;
  max-width: calc(
    100vw - #{$sidebar-width}
  ); /* todo: handle actual width! (import assets/scss/core/_variables -> doesn't compile) */

  width: auto;
  height: auto;
  float: left;
  position: absolute;
  pointer-events: none;
}

.overlay {
  mix-blend-mode: multiply;
  pointer-events: none;
  float: left;
  max-height: calc(100vh - #{$header-height});
  opacity: 0.25;
}

.overlay-state {
  mix-blend-mode: multiply;
  pointer-events: none;
  float: left;
  max-height: calc(100vh - #{$header-height});
}

.hidden * {
  visibility: hidden;
}
</style>
