<template>
  <div class="fixed-page">
    <seek-container :id="id" :callback="updateFrame">
      <div class="align" ref="align">
        <img
          :src="stream_url"
          alt=""
          class="streamed-image"
          ref="frame"
          @load="updateFrame"
        />
        <!-- todo: callback doesn't do anything -->
        <Moveable
          class="moveable"
          ref="moveable"
          v-bind="moveable"
          @drag="handleDrag"
          @resize="handleResize"
          @scale="handleScale"
          @rotate="handleRotate"
          @warp="handleWarp"
        />
      </div>
    </seek-container>
    <div class="controls"></div>
  </div>
</template>

<script>
import { estimate_transform, url_api } from "../../assets/api";
import SeekContainer from "../../components/SeekContainer";
import Moveable from "vue-moveable";
import { roiRectInfoToCoordinates } from "../../assets/align";
import { throttle } from "throttle-debounce";

export default {
  name: "align",
  beforeMount() {
    this.updateFrame;
    this.$store.dispatch("analyzers/sync");
    window.onresize = this.updateFrame;
  },
  components: {
    SeekContainer,
    Moveable
  },
  methods: {
    toBackend() {
      // todo: send rect coordinates to backend
      //  -> https://daybrush.com/moveable/release/latest/doc/Moveable.html#getRect
      //  -> todo: should be debounced a bit
    },
    handleDrag({ target, transform }) {
      target.style.transform = transform;
      this.updateRoiCoordinates();
    },
    handleResize({ target, width, height }) {
      target.style.width = `${width}px`;
      target.style.height = `${height}px`;
      this.updateRoiCoordinates();
    },
    handleScale({ target, transform }) {
      target.style.transform = transform;
      this.updateRoiCoordinates();
    },
    handleRotate({ target, transform }) {
      target.style.transform = transform;
      this.updateRoiCoordinates();
    },
    handleWarp({ target, transform }) {
      target.style.transform = transform;
      this.updateRoiCoordinates();
    },
    updateRoiCoordinates() {
      // todo: connect to backend transform estimation
      if (this.$store.state.analyzers[this.id].frame === undefined) {
        this.updateFrame();
      }

      this.$refs.moveable.updateRect();
      this.$store.state.analyzers[this.id].roi = roiRectInfoToCoordinates(
        this.$refs.moveable.getRect(),
        this.$store.state.analyzers[this.id].frame
      ); // todo: should be a Vuex commit

      estimate_transform(this.id, this.$store.state.analyzers[this.id].roi);
    },
    updateFrame() {
      this.$store.state.analyzers[
        this.id
      ].frame = this.$refs.frame.getBoundingClientRect(); // todo: should be a Vuex commit
      this.moveable.bounds = this.$store.state.analyzers[this.id].frame;
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
      throttleDrag: 1, // todo: this is a pixel-level throttle; affects transform precision!
      resizable: false,
      throttleResize: 1,
      scalable: false,
      throttleScale: 1,
      rotatable: true,
      throttleRotate: 1,
      warpable: true,
      throttleWarp: 1,
      snappable: true,
      bounds: {}
    },
    frame: {}, // todo: should be in Vuex store; we're reusing the same page for all alignment!
    coordinates: {}
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
  width: 300px;
  height: 200px;
  text-align: center;
  font-size: 40px;
  margin: 0 auto;
  font-weight: 100;
  letter-spacing: 1px;
}
</style>
