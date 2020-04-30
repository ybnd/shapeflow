<template>
  <div class="fixed-page"></div>
</template>

<script>
import { url } from "../static/api";

export default {
  name: "index",
  watch: {
    queue(q) {
      for (let i = 0; i < q.length; i++) {
        let id = q[i];

        let evl = new EventSource(url(id, "stream-json/status"));

        evl.onmessage = function(message) {
          console.log(`Got message for ${id}: `);
          console.log(JSON.parse(message.data));
        };

        console.log("new EventStreamer: ");
        console.log(evl);

        this.source[id] = evl;
      }
    }
  },
  computed: {
    queue() {
      return this.$store.getters["queue/getQueue"];
    }
  },
  data() {
    return {
      source: {},
      status: {}
    };
  }
};
</script>

<style></style>
