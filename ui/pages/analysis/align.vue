<template>
  <!--  https://stackoverflow.com/questions/14025438 -->
  <div class="fixed-page">
    <PageHeader>
      <!--      <PageHeaderItem>-->
      <!--        <b-button>Reset ROI</b-button>-->
      <!--      </PageHeaderItem>-->
      <PageHeaderItem>
        <b-button
          class="header-button-icon"
          @click="handleClearAlignment"
          data-toggle="tooltip"
          title="Clear alignment"
        >
          <i class="icon-ban" />
        </b-button>
        <b-button
          class="header-button-icon"
          @click="handleUndoAlignment"
          data-toggle="tooltip"
          title="Undo alignment"
          v-hotkey="keymap"
        >
          <i class="icon-action-undo" />
        </b-button>
        <b-button
          class="header-button-icon"
          @click="handleRedoAlignment"
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
          @click="handleFlipH"
          data-toggle="tooltip"
          title="Flip horizontally"
        >
          <i class="fa fa-arrows-h" />
        </b-button>
        <b-button
          class="header-button-icon"
          @click="handleFlipV"
          data-toggle="tooltip"
          title="Flip vertically"
        >
          <i class="fa fa-arrows-v" />
        </b-button>
      </PageHeaderItem>
      <PageHeaderItem>
        <b-button
          class="header-button-icon"
          @click="handleTurnCW"
          data-toggle="tooltip"
          title="Rotate 90° clockwise"
        >
          <i class="fa fa-rotate-right" />
        </b-button>
        <b-button
          class="header-button-icon"
          @click="handleTurnCCW"
          data-toggle="tooltip"
          title="Rotate 90° counter-clockwise"
        >
          <i class="fa fa-rotate-left" />
        </b-button>
      </PageHeaderItem>
      <PageHeaderItem>
        <b-button
          class="header-button-icon"
          @click="toggleBounds"
          :variant="enforceBounds ? null : 'danger'"
          data-toggle="tooltip"
          :title="
            enforceBounds
              ? 'Ignore frame boundaries'
              : 'Enforce frame boundaries'
          "
        >
          <i
            :class="enforceBounds ? 'icon-size-fullscreen' : 'icon-size-actual'"
            :style="{
              'margin-top': '-4px' /* alignment */,
            }"
          />
        </b-button>
      </PageHeaderItem>
    </PageHeader>
    <div class="align-content">
      <div
        class="align align-placeholder"
        ref="align"
        v-on:mousedown="handleStartRectangle"
        v-on:mouseup="handleStopRectangle"
      >
        <img
          :src="`${overlaid_url}?${opened_at}`"
          alt=""
          class="streamed-image-a"
          ref="frame"
        />
        <Moveable
          class="moveable"
          :className="moveableShow ? '' : 'hidden-moveable'"
          ref="moveable"
          v-bind="moveable"
          @drag="handleTransform"
          @scale="handleTransform"
          @rotate="handleRotate"
          @warp="handleTransform"
          @render="handleUpdate"
          @renderEnd="handleSaveAlignment"
        >
        </Moveable>
      </div>
    </div>
  </div>
</template>

<script>
import {
  estimate_transform,
  clear_roi,
  commit,
  api,
  get_relative_roi, // todo: handle ~ VueX store
  undo_config, // todo: handle ~ VueX store
  redo_config, // todo: handle ~ VueX store
  turn_cw,
  turn_ccw,
  endpoints,
  stop_stream,
  AnalyzerState as ast,
  state_transition,
  flip_h,
  flip_v,
} from "../../static/api";
import Moveable from "vue-moveable";
import {
  roiRectInfoToRelativeCoordinates,
  clickEventToRelativeCoordinate,
  roiIsValid,
  getInitialTransform,
  dragEventToRelativeRectangle,
} from "../../static/coordinates";
import { events } from "../../static/events";

import PageHeader from "../../components/header/PageHeader";
import PageHeaderItem from "../../components/header/PageHeaderItem";
import PageHeaderSeek from "../../components/header/PageHeaderSeek";
import { throttle, debounce } from "throttle-debounce";
import ConfigSidebar from "../../components/config/ConfigSidebar";
import isEqual from "lodash/isEqual";

import VueHotkey from "v-hotkey";
import Vue from "vue";

Vue.use(VueHotkey);

export default {
  name: "analyzer-align",
  beforeMount() {
    this.handleInit();
    window.addEventListener("resize", this.updateFrame);
  },
  beforeDestroy() {
    this.handleSaveAlignment();
    this.handleCleanUp();
    window.removeEventListener("resize", this.updateFrame);
  },
  components: {
    Moveable,
    PageHeader,
    PageHeaderItem,
    PageHeaderSeek,
    ConfigSidebar,
  },
  methods: {
    handleInit() {
      // console.log("align: handleInit()");
      this.previous_id = this.id;
      this.$store.dispatch("analyzers/refresh", { id: this.id });

      this.opened_at = Date.now();

      // Check if this.id is queued. If not, navigate to /
      // if (this.$store.getters["analyzers/isValidId"](this.id) === false) {
      if (this.$store.getters["analyzers/getIndex"](this.id) === -1) {
        this.$router.push(`/`);
      } else {
        this.$root.$emit(events.sidebar.open(this.id));

        this.waitUntilHasRect = setInterval(this.updateFrameOnceHasRect, 100);

        get_relative_roi(this.id).then((roi) => {
          this.setRoi(roi);
        });
      }
    },
    handleCleanUp() {
      // console.log("align: handleCleanUp()");

      stop_stream(this.previous_id, endpoints.GET_INVERSE_OVERLAID_FRAME);

      clearInterval(this.waitUntilHasRect);

      // this.$store.commit("align/clearAlign", { id: this.previous_id });
      this.align = {
        frame: null,
        roi: null,
        transform: null,
        overlay: {
          // default moveable shape
          width: 100,
          height: 100,
          top: -50,
          left: -50,
          bottom: 50,
          right: 50,
        },
      };
    },
    handleClearAlignment() {
      // console.log("align: handleClearAlignment");
      commit(this.id).then((ok) => {
        if (ok) {
          clear_roi(this.id).then((ok) => {
            if (ok) {
              this.clearRoi();
              // this.handleUpdate();
            }
          });
        }
      });
    },
    handleSaveAlignment() {
      commit(this.previous_id);
    },
    handleUndoAlignment() {
      undo_config(this.id, "transform").then((config) => {
        this.setRoi(config.transform.roi);
      });
    },
    handleRedoAlignment() {
      redo_config(this.id, "transform").then((config) => {
        this.setRoi(config.transform.roi);
      });
    },
    setRoi(roi) {
      // console.log("filter: setRoi()");

      // console.log("roi");
      // console.log(roi);

      if (roi === undefined) {
        roi = this.config.roi;
      }

      if (!(this.align.roi === roi)) {
        if (roiIsValid(roi)) {
          // console.log("is valid");
          this.align.roi = roi;
          this.resolveTransform();
        } else {
          // console.log("is invalid");
          this.clearRoi();
        }
      }
    },
    clearRoi() {
      // console.log("filter: clearRoi()");
      this.handleHideMoveable();
      this.align.roi = null;
      this.align.transform = null;
    },
    resolveTransform() {
      // console.log("filter: resolveTransform()");
      // console.log("this.$refs.moveable = ");
      // console.log(this.$refs.moveable);

      if (this.align.roi && this.align.frame && this.align.overlay) {
        clearInterval(this.waitUntilHasMoveable);

        // console.log(
        //   `roi.BL = (x: ${this.align.roi.BL.x}, y: ${this.align.roi.BL.y})`
        // );
        // console.log("frame = ");
        // console.log(this.align.frame);
        // console.log("overlay = ");
        // console.log(this.align.overlay);

        this.align.transform = getInitialTransform(
          this.align.roi,
          this.align.frame,
          this.align.overlay
        );

        // todo: sanity check transform

        if (this.$refs.moveable === undefined) {
          this.waitUntilHasMoveable = setInterval(() => {
            // todo: try to do ~ Promise instead?
            if (this.$refs.moveable !== undefined) {
              this.$refs.moveable.$el.style.transform = this.align.transform;
              this.$refs.moveable.updateRect();
              this.$refs.moveable.updateTarget();
              clearInterval(this.waitUntilHasMoveable);
            } else {
              // console.log("oops no moveable");
            }
          }, 50);
        } else {
          this.$refs.moveable.$el.style.transform = this.align.transform;
          this.$refs.moveable.updateRect();
          this.$refs.moveable.updateTarget();
          this.handleShowMoveable();
        }
      } else {
      }
    },
    handleTransform({ target, transform }) {
      target.style.transform = transform;
    },
    handleRotate({ target, transform }) {
      // rotation is performed in the '3d plane' of the moveable, which is messy when it's not rectangular
      //   => there's no easy way to fix this, AFAIK
      // todo: it seems as if that's NOT the case; rotating a rectangle 90° makes it assume the same shape
      // todo:    -> this suggests that this issue may be solved by setting the initial shape of the moveable
      // todo:       to the size of the design!

      target.style.transform = transform;
    },
    handleFlipH() {
      flip_h(this.id);
    },
    handleFlipV() {
      flip_v(this.id);
    },
    handleTurnCW() {
      turn_cw(this.id);
    },
    handleTurnCCW() {
      turn_ccw(this.id);
    },
    updateRoiCoordinates() {
      // console.log("align: updateRoiCoordinates");
      if (this.align.frame) {
        this.align.roi = roiRectInfoToRelativeCoordinates(
          this.$refs.moveable.getRect(),
          this.align.frame
        );

        if (this.align.roi !== undefined) {
          if (this.report_change) {
            // todo: why is this here? seems like a backend thing
            state_transition(this.id).then(() => {
              estimate_transform(this.id, this.align.roi);
            });
          } else {
            estimate_transform(this.id, this.align.roi);
          }
        }
      }
    },
    handleUpdate: throttle(
      20,
      false,
      debounce(20, false, function () {
        this.updateRoiCoordinates();
      })
    ),
    updateFrame() {
      // console.log("align: updateFrame");
      try {
        let frame = this.$refs.frame.getBoundingClientRect();

        if (this.enforceBounds) {
          this.moveable.bounds = {
            left: frame.left,
            right: frame.right,
            top: frame.top,
            bottom: frame.bottom,
          };
        } else {
          this.temp_bounds = {
            left: frame.left,
            right: frame.right,
            top: frame.top,
            bottom: frame.bottom,
          };
        }

        this.align.frame = frame;
        this.resolveTransform();
      } catch (err) {
        console.warn(err);
      }
    },
    toggleBounds() {
      // console.log("toggling bounds...");
      // console.log(this);
      if (this.enforceBounds) {
        this.enforceBounds = false;
        if (this.moveable.bounds) {
          this.temp_bounds = this.moveable.bounds;
          this.moveable.bounds = null;
        } else {
          this.updateFrame();
        }
      } else {
        this.enforceBounds = true;
        if (this.temp_bounds) {
          this.moveable.bounds = this.temp_bounds;
        } else {
          this.updateFrame();
        }
      }
    },
    updateFrameOnceHasRect() {
      // todo: clean up
      let frame_ok = false;
      let overlay_ok = false;

      try {
        if (!(this.waitUntilHasRect === undefined)) {
          if (this.$refs.frame.getBoundingClientRect()["width"] > 50) {
            // console.log("HAS FRAME");
            this.updateFrame();
            clearInterval(this.waitUntilHasRect);
          }
        }
      } catch (err) {
        // console.log("oops @ updateFrameOnceHasRect");
      }
    },
    stepForward() {
      this.$root.$emit(events.seek.step_fw(this.id));
    },
    stepBackward() {
      this.$root.$emit(events.seek.step_bw(this.id));
    },
    async handleShowMoveable() {
      // console.log("align: handleShowMoveable()");
      return new Promise((resolve, reject) => {
        this.moveableShow = true;
        this.moveable.draggable = true;
        const wait = setInterval(() => {
          // console.log("checking if moveable exists");
          if (this.$refs.moveable !== undefined) {
            // console.log("it does, resolving");
            clearInterval(wait);
            resolve();
          } else {
            // console.log("it doesn't seem to...");
          }
        }, 5);
      });
    },
    handleHideMoveable() {
      // console.log("align: handleHideMoveable()");
      this.moveableShow = false;
      this.moveable.draggable = false;
    },
    handleStartRectangle(start_event) {
      // console.log("align: handleStartRectangle");
      if (!this.moveableShow) {
        this.dragROI.started = true;
        this.dragROI.start_event = start_event;
      }
    },
    handleStopRectangle(stop_event) {
      // console.log("align: handleStopRectangle()");
      if (!this.moveableShow && this.dragROI.started) {
        // console.log("align: handleStopRectangle() -- setting ROI");

        const rectangle = dragEventToRelativeRectangle(
          this.dragROI.start_event,
          stop_event,
          this.align.frame
        );

        if (rectangle !== null) {
          this.setRoi(rectangle);
          this.handleUpdate();
        }
      } else {
        // console.log("align: handleStopRectangle() -- moveable is already shown!");
      }
    },
  },
  watch: {
    "$route.query.id"() {
      // console.log(`id changed to ${this.id}`);

      this.handleCleanUp();
      this.handleInit();
      this.updateFrame();
    },
    "$refs.moveable.$el"() {
      console.warn("there was a change in $ref.moveable.data");
      console.warn(this.$refs.moveable);
    },
  },
  computed: {
    id() {
      return this.$route.query.id;
    },
    keymap() {
      return {
        "ctrl+z": this.handleUndoAlignment,
        "ctrl+shift+z": this.handleRedoAlignment,
        right: this.stepForward,
        left: this.stepBackward,
      };
    },
    overlaid_url() {
      return api(
        "stream",
        this.$route.query.id,
        endpoints.GET_INVERSE_OVERLAID_FRAME
      );
    },
    ref_frame() {
      return `frame`;
    },
    ref_moveable() {
      return `moveable`;
    },
    report_change() {
      const state = this.$store.getters["analyzers/getAnalyzerStatus"](this.id)
        .state;
      return (
        state === ast.DONE || state === ast.ERROR || state === ast.CANCELED
      ); // todo: cleaner
    },
    transform_options() {
      // console.log("transform_options computed property");
      // console.log('this.$store.getters["schemas/getTransformOptions"]=');
      // console.log(this.$store.getters["schemas/getTransformOptions"]);
      return this.$store.getters["schemas/getTransformOptions"];
    },
    config() {
      const config = this.$store.getters["analyzers/getAnalyzerConfig"](
        this.id
      );
      if (config.hasOwnProperty("transform")) {
        return {
          roi: config.transform.hasOwnProperty("roi")
            ? config.transform.roi
            : undefined,
          flip: config.transform.hasOwnProperty("flip")
            ? config.transform.flip
            : undefined,
          turn: config.transform.hasOwnProperty("turn")
            ? config.transform.turn
            : undefined,
        };
      } else {
        return { roi: undefined, flip: undefined, turn: undefined };
      }
    },
  },
  data: () => ({
    opened_at: 0,
    moveable: {
      // request-level throttle & debounce to limit traffic, but keep pixel-level throttle at 0 for precision
      draggable: true,
      throttleDrag: 0,
      rotatable: true,
      throttleRotate: 0,
      warpable: true,
      throttleWarp: 0,
      snappable: true,
      bounds: {},
      rotationPosition: "bottom", // becomes the top ~ transform, probably a coordinate mixup somewhere. works fine though
    },
    align: {
      frame: null,
      overlay: {
        // default moveable shape
        width: 100,
        height: 100,
        top: -50,
        left: -50,
        bottom: 50,
        right: 50,
      },
      roi: null,
      transform: null,
    },
    enforceBounds: true,
    temp_bounds: null,
    updateCall: null,
    moveableShow: false,
    dragROI: {
      start_event: {},
    },
    waitUntilHasRect: null,
    previous_id: "",
    hideConfigSidebar: true,
  }),
};
</script>

<style lang="scss">
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

.align {
  position: absolute;
  float: left;
  display: block;
  margin: 0 0 0 0;
  width: $content-width;
  height: $content-height;
  max-width: $content-width;
  max-height: $content-height;
  /* Disable double-click selection */
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
  -o-user-select: none;
  user-select: none;
  overflow: none;
}

.streamed-image-a {
  z-index: -100;
  pointer-events: none;
  display: block;
  width: auto;
  height: auto;
  max-width: $content-width;
  max-height: $content-height;
  position: absolute;
}

.moveable {
  /* todo: hide the 100x100 placeholder until initial_transform is set */
  position: absolute;
  width: 100px;
  height: 100px;
  left: 0;
  top: 0;
  margin: 0 0 0 0;
}

.hidden * {
  visibility: hidden;
}

/* match theme color & set size */
.moveable-control {
  border-color: darken(theme-color("primary"), 3%) !important;
  background: theme-color("primary") !important;
}

/* hide lines by default */
.moveable-line {
  visibility: hidden !important;
  border-color: darken(theme-color("primary"), 3%) !important;
  background: theme-color("primary") !important;
}

.moveable-control.moveable-rotation {
  border-color: darken(theme-color("primary"), 3%) !important;
  background: lighten(theme-color("primary"), 33%) !important;
}

/* override hidden & enable anti-aliasing */
/* https://stackoverflow.com/questions/6492027 */
.moveable-direction {
  visibility: visible !important;
  outline: 1px solid transparent !important;
}
.moveable-rotation-line {
  visibility: visible !important;
  outline: 1px solid transparent !important;
}

/* hide weird .moveable-reverse thing that gets rendered in the top left corner after refresh */
.moveable-reverse * {
  /*visibility: hidden !important;*/
}

.align-content {
  display: flex;
  flex-direction: row;
}

.filter-placeholder {
  /*background: #ff0000;*/
  flex-grow: 1;
  height: calc(100vh - #{$header-height});
}

.hidden-moveable > * {
  visibility: hidden !important;
}
</style>
