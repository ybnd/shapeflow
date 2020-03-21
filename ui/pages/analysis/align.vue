<template>
  <div class="fixed-page">
    <seek-container :id="id">
      <div class="align-image">
        <img :src="stream_url" alt="" />
        <Moveable
          class="moveable"
          v-bind="moveable"
          @drag="handleDrag"
          @resize="handleResize"
          @scale="handleScale"
          @rotate="handleRotate"
          @warp="handleWarp"
        >
          <span>This thing is moveable</span>
        </Moveable>
      </div>
      <div class="controls">
        {{ id }}
        {{ stream_url }}
        <div class="clear">
          <b-button @click="handleClear">Clear</b-button>
        </div>
      </div>
    </seek-container>
  </div>
</template>

<script>
import { estimate_transform, url_api } from "../../assets/api";
import SeekContainer from "../../components/SeekContainer";
import Moveable from "vue-moveable";

export default {
  name: "dashboard",
  props: {
    position: {
      type: Number,
      default: 0.0
    }
  },
  beforeMount() {
    window.onload = () => {
      this.$store.dispatch("analyzers/sync");
    };
  },
  components: {
    SeekContainer,
    Moveable
  },
  methods: {
    toBackend() {
      // todo: send rect coordinates to backend
      //  -> https://daybrush.com/moveable/release/latest/doc/Moveable.html#getRect
    },
    handleDrag({ target, transform }) {
      target.style.transform = transform;
      // todo: connect to backend transform estimation
    },
    handleResize({ target, transform }) {
      target.style.transform = transform;
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
    }
  },
  data: () => ({
    moveable: {
      draggable: true,
      throttleDrag: 0,
      resizable: true,
      throttleResize: 1,
      scalable: true,
      throttleScale: 0,
      rotatable: true,
      throttleRotate: 0,
      warpable: true,
      throttleWarp: 0,
      origin: false // todo: set starting position from here?
    }
  })
};
</script>

<style></style>
