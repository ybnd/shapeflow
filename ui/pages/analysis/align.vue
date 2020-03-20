<template>
  <div class="fixed-page">
    <div class="align-image">
      <img :src="stream_url" alt="" />
    </div>
    <div class="controls">
      {{ id }}
      {{ stream_url }}
      <div class="clear">
        <b-button @click="handleClear">Clear</b-button>
      </div>
    </div>
  </div>
</template>

<script>
import { seek, stream, url_api } from "../../assets/api";

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
  components: {},
  data: function() {
    return {};
  },
  methods: {
    handleSeek() {
      seek(this.id, this.position).then(actual_position => {
        // todo: does this work like this?
        this.position = actual_position;
      });
    },
    handleClear() {}
  },
  computed: {
    id() {
      return this.$route.query.id; // todo: this should get ?id=<...> from the url query
    },
    stream_url() {
      return url_api(this.$route.query.id, `stream/get_raw_frame`);
    }
  }
};
</script>

<style></style>
