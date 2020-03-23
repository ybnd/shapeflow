<template>
  <div class="fixed-page">
    <seek-container :id="id">
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
          @render="updateRoiCoordinates"
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

export default {
  name: "align",
  props: {
    coordinates: {
      type: Object,
      default: {
        TL: { x: 0.25, y: 0.75 },
        TR: { x: 0.75, y: 0.75 },
        BL: { x: 0.25, y: 0.25 },
        BR: { x: 0.75, y: 0.25 }
      }
    }
  },
  beforeMount() {
    window.onload = () => {
      this.updateFrame;
      this.$store.dispatch("analyzers/sync");
    };
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
      // todo: connect to backend transform estimation
    },
    handleResize({ target, width, height }) {
      target.style.width = `${width}px`;
      target.style.height = `${height}px`;
      // todo: connect to backend transform estimation
    },
    handleScale({ target, transform }) {
      target.style.transform = transform;
      // todo: connect to backend transform estimation
    },
    handleRotate({ target, transform }) {
      target.style.transform = transform;
      // todo: connect to backend transform estimation
    },
    handleWarp({ target, transform }) {
      target.style.transform = transform;
      // todo: connect to backend transform estimation
    },
    updateRoiCoordinates() {
      this.$refs.moveable.updateRect();
      this.$props.coordinates = roiRectInfoToCoordinates(
        this.$refs.moveable.getRect(),
        this.frame
      );
    },
    updateFrame() {
      if (this.frame === {}) {
        this.frame = this.$refs.frame.getBoundingClientRect();
      }
      this.moveable.bounds = this.frame;
    }
  },
  computed: {
    id() {
      return this.$route.query.id; // todo: this should get ?id=<...> from the url query
    },
    stream_url() {
      return url_api(this.$route.query.id, `stream/get_raw_frame`);
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
    frame: {},
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
}

.moveable {
  z-index: 100;
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
