<template>
  <!--  https://stackoverflow.com/questions/14025438 -->
  <div class="fixed-page">
    <PageHeader>
      <PageHeaderItem>
        <b-button>Set filters</b-button>
      </PageHeaderItem>
      <PageHeaderItem>
        <b-button>Reset ROI</b-button>
      </PageHeaderItem>
      <PageHeaderSeek :id="id" />
      <PageHeaderItem>
        <b-button-group>
          <b-dropdown
            text="Transform type: Perspective"
            data-toggle="tooltip"
            title="Transform type"
          >
            <b-dropdown-item
              data-toggle="tooltip"
              title="info about perspective transform"
              >Perspective</b-dropdown-item
            >
          </b-dropdown>
        </b-button-group>
      </PageHeaderItem>
    </PageHeader>
    <div class="align" ref="align">
      <img
        :src="raw_url"
        alt=""
        class="streamed-image"
        v-bind:class="{ hidden: !aligning }"
        ref="frame"
      />
      <img
        :src="overlaid_url"
        alt=""
        class="streamed-image"
        v-bind:class="{ hidden: aligning }"
        ref="overlay"
      />
      <!-- todo: can't set callback on streamed image load :( -->
      <Moveable
        class="moveable"
        ref="moveable"
        v-bind="moveable"
        @drag="handleTransform"
        @scale="handleTransform"
        @rotate="handleRotate"
        @warp="handleTransform"
        @renderStart="handleRenderStart"
        @renderEnd="handleRenderEnd"
      >
        <img
          :src="overlay_url"
          alt=""
          class="overlay"
          v-bind:class="{ hidden: !aligning }"
          ref="overlay"
        />
      </Moveable>
    </div>
    <div class="controls"></div>
  </div>
</template>

<script>
import { estimate_transform, url_api } from "../../static/api";
import Moveable from "vue-moveable";
import {
  roiRectInfoToCoordinates,
  default_relative_coords
} from "../../static/align";
import PageHeader from "../../components/header/PageHeader";
import PageHeaderItem from "../../components/header/PageHeaderItem";
import PageHeaderSeek from "../../components/header/PageHeaderSeek";
import { throttle, debounce } from "throttle-debounce";

export default {
  name: "align",
  beforeMount() {
    window.onresize = this.updateFrame;
    // todo: there are some edge cases where the ROI gets messed up

    this.handleInit();
    this.waitUntilHasRect = setInterval(this.updateFrameOnceHasRect, 100);
  },
  beforeDestroy() {
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
    handleInit() {
      console.log(`Initializing align window for ${this.id}`);
      this.$store.dispatch("align/init", { id: this.id }).then(() => {
        console.log("Vuex/align: init should be done");
        console.log(this.$store.state.align);

        if (this.$store.getters["align/getInitialRoi"](this.id) === null) {
          this.$store.commit("align/setInitialRoi", {
            id: this.id,
            initial_roi: default_relative_coords
          });
        }
      });
    },
    handleTransform({ target, transform }) {
      target.style.transform = transform;
    },
    handleRotate({ target, transform }) {
      // todo: rotation messes up perspective
      target.style.transform = transform; // todo: temporarily disable bounds during rotation
    },
    updateRoiCoordinates() {
      let frame = this.$store.getters["align/getFrame"](this.id);
      let roi = roiRectInfoToCoordinates(this.$refs.moveable.getRect(), frame);
      estimate_transform(this.id, roi);
    },
    handleRenderStart() {
      this.aligning = true;
    },
    handleRenderEnd() {
      this.handleUpdate();
      this.aligning = false;
    },
    handleUpdate: throttle(
      100,
      false,
      debounce(20, false, function() {
        this.updateRoiCoordinates();
      })
    ),
    updateFrame() {
      console.log("Updating frame...");
      let frame = this.$refs.frame.getBoundingClientRect();
      console.log(frame);
      this.moveable.bounds = {
        left: frame.left,
        right: frame.right,
        top: frame.top,
        botto: frame.bottom
      };
      this.$store.commit("align/setFrame", { id: this.id, frame: frame });

      this.$store.dispatch("align/getRoi", { id: this.id }).then(() => {
        let transform = this.$store.getters["align/getInitialTransform"](
          this.id
        );
        this.$refs.moveable.$el.style.transform = transform;

        console.log("updateFrame - initial_transform");
        console.log(transform);
        console.log(this.$refs.moveable.$el);

        this.$refs.moveable.updateRect();
        this.$refs.moveable.updateTarget();
      });
    },
    updateOverlay() {
      console.log("Updating overlay...");
      let overlay = this.$refs.overlay.getBoundingClientRect();
      console.log(overlay);
      this.$store.commit("align/setOverlay", { id: this.id, overlay: overlay });
    },
    updateFrameOnceHasRect() {
      // todo: clean up
      let frame_ok = false;
      let overlay_ok = false;
      if (!(this.waitUntilHasRect === undefined)) {
        if (this.$refs.frame.getBoundingClientRect()["width"] > 100) {
          console.log("HAS FRAME");
          this.updateFrame();
          frame_ok = true;
        }
        if (this.$refs.overlay.getBoundingClientRect()["width"] > 100) {
          console.log("HAS OVERLAY");
          this.updateOverlay();
          overlay_ok = true;
        }
      }
      if (frame_ok && overlay_ok) {
        clearInterval(this.waitUntilHasRect);
      }
    }
  },
  computed: {
    id() {
      return this.$route.query.id;
    },
    overlaid_url() {
      return url_api(this.$route.query.id, "stream/get_inverse_overlaid_frame");
    },
    raw_url() {
      return url_api(this.$route.query.id, "stream/get_raw_frame");
    },
    overlay_url() {
      return url_api(this.$route.query.id, "call/get_overlay_png");
    },
    initial_coordinates() {
      // todo: query backend for initial coordinates
      //  -> https://daybrush.com/moveable/release/latest/doc/Moveable.html#updateRect
      return {};
    }
  },
  data: () => ({
    moveable: {
      draggable: true,
      throttleDrag: 0, // todo: should have a api request-level throttle & debounce to limit traffic, but keep this throttle 0 for precision
      rotatable: true,
      throttleRotate: 0,
      warpable: true,
      throttleWarp: 0,
      snappable: true,
      bounds: {}
    },
    updateCall: null,
    aligning: false
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

.streamed-image {
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

.overlay {
  mix-blend-mode: multiply;
}

.hidden {
  visibility: hidden;
}

.moveable {
  /* todo: hide the 100x100 placeholder until initial_transform is set */
  position: absolute;
  width: auto;
  height: auto;
  /*mix-blend-mode: multiply;*/
  max-width: 10000px;
  max-height: 10000px;
  left: 0;
  top: 0;
  margin: 0 0 0 0;
}

.overlay {
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
  visibility: hidden !important;
}
</style>
