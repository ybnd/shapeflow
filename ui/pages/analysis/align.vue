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
    <seek-container :id="id" :callback="updateFrame">
      <div class="align" ref="align">
        <img :src="stream_url" alt="" class="streamed-image" ref="frame" />
        <!-- todo: can't set callback on streamed image load :( -->
        <Moveable
          class="moveable"
          ref="moveable"
          v-bind="moveable"
          @drag="handleTransform"
          @scale="handleTransform"
          @rotate="handleRotate"
          @warp="handleTransform"
        />
      </div>
    </seek-container>
    <div class="controls"></div>
  </div>
</template>

<script>
import { estimate_transform, url_api } from "../../static/api";
import SeekContainer from "../../components/SeekContainer";
import Moveable from "vue-moveable";
import {
  roiRectInfoToCoordinates,
  default_relative_coords
} from "../../static/align";
import PageHeader from "../../components/header/PageHeader";
import PageHeaderItem from "../../components/header/PageHeaderItem";

export default {
  name: "align",
  beforeMount() {
    window.onresize = this.updateFrame;
    // todo: there are some edge cases where the ROI gets messed up

    this.handleInit();

    setInterval(this.updateRoiCoordinates, 100); // todo: to fix the lagging overlay issue; way too intensive :/
    // todo: while transforming, have a transparent overlay image in the moveable element & render it over raw image
    // todo:    * N msec after 'letting go', make the moveable transparent, estimate the transform
    // todo:                                      & replace raw image with inverse transformed overlay image
    // todo:    => performance while dragging + precision in the end

    this.waitUntilHasRect = setInterval(this.updateFrameOnceHasRect, 100);
  },
  components: {
    SeekContainer,
    Moveable,
    PageHeader,
    PageHeaderItem
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
    updateFrameOnceHasRect() {
      if (!(this.waitUntilHasRect === undefined)) {
        if (this.$refs.frame.getBoundingClientRect()["width"] > 100) {
          console.log("HAS RECT");
          this.updateFrame();
          clearInterval(this.waitUntilHasRect);
          delete this.waitUntilHasRect;
        }
      }
    }
  },
  computed: {
    id() {
      return this.$route.query.id;
    },
    stream_url() {
      return url_api(this.$route.query.id, `stream/get_inverse_overlaid_frame`);
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
    }
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

.moveable {
  /* todo: hide the 100x100 placeholder until initial_transform is set */
  position: absolute;
  width: 100px;
  height: 100px;
  left: 0;
  top: 0;
  margin: 0 0 0 0;
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
