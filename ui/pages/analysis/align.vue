<template>
  <!--  https://stackoverflow.com/questions/14025438 -->
  <div class="fixed-page">
    <PageHeader>
      <PageHeaderItem>
        <b-button @click="handleSetFilters">Set filters</b-button>
      </PageHeaderItem>
      <!--      <PageHeaderItem>-->
      <!--        <b-button>Reset ROI</b-button>-->
      <!--      </PageHeaderItem>-->
      <PageHeaderSeek :id="id" />
      <PageHeaderItem>
        <b-button-group>
          <b-dropdown
            :text="`${this.align}`"
            data-toggle="tooltip"
            title="Transform type"
          >
            <b-dropdown-item
              v-for="align in align_options"
              :key="`align-${align}`"
            >
              {{ align }}
            </b-dropdown-item>
          </b-dropdown>
        </b-button-group>
      </PageHeaderItem>
    </PageHeader>
    <div class="align" ref="align">
      <img :src="overlaid_url" alt="" class="streamed-image-a" ref="frame" />
      <Moveable
        class="moveable"
        ref="moveable"
        v-bind="moveable"
        @drag="handleTransform"
        @scale="handleTransform"
        @rotate="handleRotate"
        @warp="handleTransform"
        @render="handleUpdate"
      >
      </Moveable>
    </div>
    <div class="controls"></div>
  </div>
</template>

<script>
import { estimate_transform, get_options, url } from "../../static/api";
import Moveable from "vue-moveable";
import {
  roiRectInfoToAbsoluteCoordinates,
  default_relative_coords
} from "../../static/coordinates";
import PageHeader from "../../components/header/PageHeader";
import PageHeaderItem from "../../components/header/PageHeaderItem";
import PageHeaderSeek from "../../components/header/PageHeaderSeek";
import { throttle, debounce } from "throttle-debounce";

export default {
  name: "align",
  beforeMount() {
    console.log(`beforeMount() of align @ ${this.id}`);
    this.handleInit();
    window.onresize = this.updateFrame;
  },
  beforeDestroy() {
    console.log(`beforeDestroy() of align`);
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
    handleSetFilters() {
      this.$router.push(`/analysis/filter?id=${this.id}`);
    },
    handleInit() {
      console.log(`Initializing align window for ${this.id}`);

      console.log("trying to emit seek event");
      this.$root.$emit(`seek-${this.id}`);

      this.waitUntilHasRect = setInterval(this.updateFrameOnceHasRect, 100);
      get_options("transform").then(options => {
        this.align_options = options;
        this.align = options[0];
      });
      this.moveable.className = this.moveableHide;
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
      // todo: during rotation, set warpable to false?
      target.style.transform = transform; // todo: temporarily disable bounds during rotation?
    },
    updateRoiCoordinates() {
      let frame = this.$store.getters["align/getFrame"](this.id);
      let roi = roiRectInfoToAbsoluteCoordinates(
        this.$refs.moveable.getRect(),
        frame
      );
      estimate_transform(this.id, roi);
    },
    handleUpdate: throttle(
      100,
      false,
      debounce(20, false, function() {
        this.updateRoiCoordinates();
      })
    ),
    updateFrame() {
      // console.log("Updating frame...");
      let frame = this.$refs.frame.getBoundingClientRect();
      // console.log(frame);
      this.moveable.bounds = {
        left: frame.left,
        right: frame.right,
        top: frame.top,
        bottom: frame.bottom
      };
      this.$store.commit("align/setFrame", { id: this.id, frame: frame });

      this.$store.dispatch("align/getRoi", { id: this.id }).then(() => {
        let transform = this.$store.getters["align/getInitialTransform"](
          this.id
        );
        this.$refs.moveable.$el.style.transform = transform;

        // console.log("updateFrame - initial_transform");
        // console.log(transform);
        // console.log(this.$refs.moveable.$el);

        this.$refs.moveable.updateRect();
        this.$refs.moveable.updateTarget();
      });
    },
    updateOverlay() {
      // console.log("Updating overlay...");
      let rect_info = this.$refs.moveable.getRect();

      let overlay = {
        width: rect_info.width,
        height: rect_info.height,
        top: -rect_info.height / 2,
        left: -rect_info.width / 2,
        bottom: rect_info.height / 2,
        right: rect_info.width / 2
      };

      // console.log(overlay);
      this.$store.commit("align/setOverlay", { id: this.id, overlay: overlay });
    },
    updateFrameOnceHasRect() {
      // todo: clean up
      let frame_ok = false;
      let overlay_ok = false;
      if (!(this.waitUntilHasRect === undefined)) {
        if (this.$refs.frame.getBoundingClientRect()["width"] > 50) {
          // console.log("HAS FRAME");
          this.updateFrame();
          frame_ok = true;
        }
      }
      if (this.$refs.moveable.getRect()["width"] > 50) {
        // console.log("HAS OVERLAY");
        this.updateOverlay();
        overlay_ok = true;
      }
      if (frame_ok && overlay_ok) {
        clearInterval(this.waitUntilHasRect);
        this.moveable.className = this.moveableShow;
      }
    }
  },
  watch: {
    "$route.query.id"() {
      console.log(`id has changed ${this.id}`);

      this.$forceUpdate();

      this.handleInit();
      this.updateFrame(); // todo: this *tries* to update the moveable, but it grows for some reason :( / :)
      this.updateOverlay();
    }
  },
  computed: {
    id() {
      return this.$route.query.id;
    },
    overlaid_url() {
      return url(this.$route.query.id, "stream/get_inverse_overlaid_frame");
    }
  },
  data: () => ({
    align_options: {},
    align: "",
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
    updateCall: null,
    moveableShow: "",
    moveableHide: "hidden",
    waitUntilHasRect: null
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
  visibility: hidden !important;
}
</style>
