<template>
  <div class="fixed-page">
    <seek-container :id="id" :callback="updateFrame">
      <div class="align" ref="align">
        <img :src="stream_url" alt="" class="streamed-image" ref="frame" />
        <!-- todo: callback doesn't do anything -->
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
import Vue from "vue";

export default {
  name: "align",
  beforeMount() {
    window.onresize = this.updateFrame;
    this.handleInit(); // todo: should call updateFrame once img is loaded, but not before. element callbacks don't work :(

    setInterval(this.updateRoiCoordinates, 100); // todo: to fix the lagging overlay issue; way too intensive :/
    // todo: while transforming, have a transparent overlay image in the moveable element & render it over raw image
    // todo:    * N msec after 'letting go', make the moveable transparent, estimate the transform
    // todo:                                      & replace raw image with inverse transformed overlay image
    // todo:    => performance while dragging + precision in the end
  },
  components: {
    SeekContainer,
    Moveable
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
      this.moveable.bounds = frame;
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

<style>
.align {
  position: absolute;
  float: left;
  display: block;
  margin: 0 0 0 0;
}

.streamed-image {
  z-index: -100;
  pointer-events: none;
  display: block;
  max-width: 80vw;
  max-height: 100vh;
  width: auto;
  height: auto;
  position: absolute;
}

.moveable {
  z-index: 1;
  font-family: "Roboto", sans-serif;
  position: absolute;
  width: 100px;
  height: 100px;
  left: 0;
  top: 0;
  text-align: center;
  font-size: 40px;
  margin: 0 0 0 0;
  font-weight: 100;
  letter-spacing: 1px;
}
</style>
