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
          origin="tr"
          @drag="handleDrag"
          @resize="handleResize"
          @scale="handleScale"
          @rotate="handleRotate"
          @warp="handleWarp"
          @renderEnd="setToDummyCoords"
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
  transform,
  toCssMatrix3d
} from "../../static/align";
import { multiply } from "mathjs";

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
    handleDrag({ target, transform }) {
      target.style.transform = transform;
      console.log(transform);
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
      this.updateRoiCoordinates(); // todo: temporarily disable bounds during rotation
    },
    handleWarp({ target, transform }) {
      target.style.transform = transform;
      this.updateRoiCoordinates();
    },
    setToDummyCoords({ target }) {
      let starting_coordinates_absolute = [
        { x: -50, y: 50 },
        { x: -50, y: -50 },
        { x: 50, y: -50 },
        { x: 50, y: 50 }
      ];

      let dummy_coordinates_relative = [
        { x: 0.82, y: 0.23 },
        { x: 0.81, y: 0.89 },
        { x: 0.23, y: 0.89 },
        { x: 0.22, y: 0.23 }
      ];

      let dummy_coordinates_absolute = [];

      this.updateFrame();

      console.log(
        `Image ${this.$store.state.analyzers[this.id].frame.width} x ${
          this.$store.state.analyzers[this.id].frame.height
        }`
      );

      for (let i = 0; i < dummy_coordinates_relative.length; i++) {
        dummy_coordinates_absolute[i] = {
          x:
            dummy_coordinates_relative[i].x *
              this.$store.state.analyzers[this.id].frame.width -
            50, // apparently have to compensate for origin?
          y:
            dummy_coordinates_relative[i].y *
              this.$store.state.analyzers[this.id].frame.height -
            50
        };
      }

      console.log("Starting coordinates: (absolute)");
      console.log(starting_coordinates_absolute);

      console.log("Dummy coordinates: (relative)");
      console.log(dummy_coordinates_relative);

      console.log("Dummy coordinates: (absolute)");
      console.log(dummy_coordinates_absolute);

      console.log("Dummy transform:");
      console.log(
        transform(starting_coordinates_absolute, dummy_coordinates_absolute)
      );
      console.log(
        toCssMatrix3d(
          transform(starting_coordinates_absolute, dummy_coordinates_absolute)
        )
      );

      console.log("Transform of origin, [50,50]:");
      console.log(
        multiply(
          transform(starting_coordinates_absolute, dummy_coordinates_absolute),
          [50, 50, 0, 1]
        )
      );

      this.$store.state.analyzers[this.id].transform = transform(
        starting_coordinates_absolute,
        dummy_coordinates_absolute
      );
      target.style.transform = toCssMatrix3d(
        transform(starting_coordinates_absolute, dummy_coordinates_absolute)
      );

      this.$refs.moveable.updateRect();
      this.$refs.moveable.updateTarget();
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
