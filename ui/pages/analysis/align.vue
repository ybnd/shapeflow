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
          <i class="fa fa-remove" />
        </b-button>
        <b-button
          class="header-button-icon"
          @click="handleUndoAlignment"
          data-toggle="tooltip"
          title="Undo alignment"
          v-hotkey="keymap"
        >
          <i class="fa fa-undo" />
        </b-button>
        <b-button
          class="header-button-icon"
          @click="handleRedoAlignment"
          data-toggle="tooltip"
          title="Redo alignment"
          v-hotkey="keymap"
        >
          <i class="fa fa-repeat" />
        </b-button>
      </PageHeaderItem>
      <PageHeaderItem>
        <b-button
          class="header-button-icon"
          @click="handleFlipV"
          data-toggle="tooltip"
          title="Flip horizontally"
        >
          <i class="fa fa-arrows-h" />
        </b-button>
        <b-button
          class="header-button-icon"
          @click="handleFlipH"
          data-toggle="tooltip"
          title="Flip vertically"
        >
          <i class="fa fa-arrows-v" />
        </b-button>
      </PageHeaderItem>
      <PageHeaderSeek :id="id" />
      <PageHeaderItem>
        <b-button-group>
          <b-dropdown
            :text="`${this.transform}`"
            data-toggle="tooltip"
            title="Transform type"
          >
            <b-dropdown-item
              v-for="align in transform_options"
              :key="`align-${align}`"
            >
              {{ align }}
            </b-dropdown-item>
          </b-dropdown>
        </b-button-group>
      </PageHeaderItem>
    </PageHeader>
    <div class="align" ref="align">
      <img
        :src="overlaid_url"
        alt=""
        class="streamed-image-a"
        :ref="ref_frame"
      />
      <Moveable
        class="moveable"
        :class="moveableHide"
        :ref="ref_moveable"
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
</template>

<script>
import {
  estimate_transform,
  clear_roi,
  get_options,
  commit,
  url,
  get_relative_roi,
  undo_roi,
  redo_roi,
  flip_transform,
  set_config
} from "../../static/api";
import Moveable from "vue-moveable";
import {
  roiRectInfoToRelativeCoordinates,
  default_relative_coords,
  roiIsValid,
  getInitialTransform
} from "../../static/coordinates";
import { events } from "../../static/events";

import PageHeader from "../../components/header/PageHeader";
import PageHeaderItem from "../../components/header/PageHeaderItem";
import PageHeaderSeek from "../../components/header/PageHeaderSeek";
import { throttle, debounce } from "throttle-debounce";

import VueHotkey from "v-hotkey";
import Vue from "vue";

Vue.use(VueHotkey);

export default {
  name: "align",
  beforeMount() {
    this.handleInit();
    window.onresize = this.updateFrame;
  },
  beforeDestroy() {
    this.handleSaveAlignment();

    this.handleCleanUp();

    clearInterval(this.waitUntilHasRect);
    clearInterval(this.updateCall);
  },
  components: {
    Moveable,
    PageHeader,
    PageHeaderItem,
    PageHeaderSeek
  },
  methods: {
    handleClearAlignment() {
      commit(this.id).then(ok => {
        if (ok) {
          clear_roi(this.id).then(ok => {
            if (ok) {
              this.setRoi(default_relative_coords);
              this.handleUpdate();
            }
          });
        }
      });
    },
    handleSaveAlignment() {
      commit(this.previous_id);
    },
    handleUndoAlignment() {
      undo_roi(this.id).then(roi => {
        this.setRoi(roi);
      });
    },
    handleRedoAlignment() {
      redo_roi(this.id).then(roi => {
        this.setRoi(roi);
      });
    },
    handleCleanUp() {
      console.log("handleCleanUp");
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
          right: 50
        }
      };
      this.refs = {
        frame: null,
        moveable: null
      };
    },
    getRefs() {
      this.refs.frame = this.$refs[this.ref_frame];
      this.refs.moveable = this.$refs[this.ref_moveable];
    },
    handleInit() {
      console.log("handleInit");
      this.getRefs();
      // Check if this.id is queued. If not, navigate to /
      if (this.$store.getters["analyzers/getIndex"](this.id) === -1) {
        this.$router.push(`/`);
      } else {
        this.previous_id = this.id;

        this.align.flip = this.$store.getters["analyzers/getConfig"](
          this.id
        ).transform.flip;

        this.waitUntilHasRect = setInterval(this.updateFrameOnceHasRect, 100);
        get_options("transform").then(options => {
          this.transform_options = options;
          this.transform = options[0];
        });
        // this.$store.dispatch("align/init", { id: this.id }).then(() => {
        get_relative_roi(this.id).then(roi => {
          this.setRoi(roi);
          this.$root.$emit(events.seek.reset(this.id)); // todo: this doesn't trigger the stream for some reason
          // this.$store.dispatch("analyzers/get_config", { id: this.id }); // todo: why?
        });
        this.handleUpdate();
      }
    },
    setRoi(roi) {
      console.log("roi");
      console.log(roi);
      if (!(this.align.roi === roi)) {
        if (roiIsValid(roi)) {
          console.log("is valid");
          this.align.roi = roi;
        } else {
          console.log("is invalid");
          this.align.roi = default_relative_coords;
        }
        this.resolveTransform();
      }
    },
    resolveTransform() {
      console.log("handleResolveTransform");
      if (this.align.roi && this.align.frame && this.align.overlay) {
        console.log(
          `roi.BL = (x: ${this.align.roi.BL.x}, y: ${this.align.roi.BL.y})`
        );
        console.log("frame = ");
        console.log(this.align.frame);
        console.log("overlay = ");
        console.log(this.align.overlay);

        this.align.transform = getInitialTransform(
          this.align.roi,
          this.align.frame,
          this.align.overlay
        );

        // todo: sanity check transform

        this.refs.moveable.$el.style.transform = this.align.transform;
        this.refs.moveable.updateRect();
        this.refs.moveable.updateTarget();
      } else {
      }
    },
    handleTransform({ target, transform }) {
      target.style.transform = transform;
    },
    handleRotate({ target, transform }) {
      // todo: rotation messes up perspective
      // todo: during rotation, set warpable to false?
      target.style.transform = transform; // todo: temporarily disable bounds during rotation?
    },
    handleFlipH() {
      this.$store
        .dispatch("analyzers/set_config", {
          id: this.id,
          config: {
            transform: {
              flip: [this.align.flip[0], !this.align.flip[1]]
            }
          }
        })
        .then(config => {
          this.align.flip = config.transform.flip;
        });
    },
    handleFlipV() {
      this.$store
        .dispatch("analyzers/set_config", {
          id: this.id,
          config: {
            transform: {
              flip: [!this.align.flip[0], this.align.flip[1]]
            }
          }
        })
        .then(config => {
          this.align.flip = config.transform.flip;
        });
    },
    updateRoiCoordinates() {
      if (this.align.frame) {
        this.align.roi = roiRectInfoToRelativeCoordinates(
          this.refs.moveable.getRect(),
          this.align.frame
        );

        if (this.align.roi !== undefined) {
          estimate_transform(this.id, this.align.roi);
        }
      }
    },
    handleUpdate: throttle(
      100,
      false,
      debounce(20, false, function() {
        this.updateRoiCoordinates();
      })
    ),
    updateFrame() {
      try {
        let frame = this.refs.frame.getBoundingClientRect();

        this.moveable.bounds = {
          left: frame.left,
          right: frame.right,
          top: frame.top,
          bottom: frame.bottom
        };
        this.align.frame = frame;
        this.resolveTransform();
      } catch (err) {
        console.log("oops @ updateFrame");
      }
    },
    updateFrameOnceHasRect() {
      // todo: clean up
      let frame_ok = false;
      let overlay_ok = false;
      this.getRefs();

      try {
        if (!(this.waitUntilHasRect === undefined)) {
          if (this.refs.frame.getBoundingClientRect()["width"] > 50) {
            // console.log("HAS FRAME");
            this.updateFrame();
            clearInterval(this.waitUntilHasRect);
            this.moveable.className = this.moveableShow;
          }
        }
      } catch (err) {
        console.log("oops @ updateFrameOnceHasRect");
      }
    },
    stepForward() {
      this.$root.$emit(events.seek.step_fw(this.id));
    },
    stepBackward() {
      this.$root.$emit(events.seek.step_bw(this.id));
    }
  },
  watch: {
    "$route.query.id"() {
      console.log(`id has changed ${this.id}`);

      this.handleCleanUp();

      this.handleInit();
    }
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
        left: this.stepBackward
      };
    },
    overlaid_url() {
      return url(this.$route.query.id, "stream/get_inverse_overlaid_frame");
    },
    ref_frame() {
      return `frame-${this.$route.query.id}`;
    },
    ref_moveable() {
      return `moveable-${this.$route.query.id}`;
    }
  },
  data: () => ({
    transform_options: {},
    transform: "",
    moveable: {
      className: "hidden", //
      draggable: true,
      throttleDrag: 0, // todo: should have a api request-level throttle & debounce to limit traffic, but keep this throttle 0 for precision
      rotatable: true,
      throttleRotate: 0,
      warpable: true,
      throttleWarp: 0,
      snappable: true,
      bounds: {}
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
        right: 50
      },
      roi: null,
      transform: null
    },
    refs: {
      frame: null,
      moveable: null
    },
    updateCall: null,
    moveableShow: "",
    moveableHide: "hidden",
    waitUntilHasRect: null,
    previous_id: ""
  })
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
  max-height: calc(100vh - #{$header-height});
}

.streamed-image-a {
  z-index: -100;
  pointer-events: none;
  display: block;
  max-width: calc(
    100vw - #{$sidebar-width}
  ); /* todo: handle actual width! (import assets/scss/core/_variables -> doesn't compile) */
  max-height: calc(100vh - #{$header-height});
  width: auto;
  height: auto;
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
</style>
