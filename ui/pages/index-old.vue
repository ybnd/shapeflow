<template>
  <section class="container">
    <div>
      <div class="test">
        <a
          class="button--grey"
          @click="init();">New analysis
        </a>
        <a
          class="button--green"
          @click="launch();">Launch
        </a>
        <a
          class="button--grey"
          @click="list();">List</a>
      </div>
    </div>
  </section>
</template>

<script>
import axios from 'axios'

export default {
  computed: {
    nothing () {return null},
  },
  beforeMount() {
    window.onload = this.ping;
    window.onunload = this.unload;
    setInterval(this.ping, 500);
  },
  methods: {
    async init (id = '') {
      await this.$store.commit('analyzers/init', id);
    },
    launch (id = '') {
      this.$store.commit('analyzers/launch', id);
    },
    list () {
      this.$store.commit('analyzers/list');
    },

    ping() {
      axios.get('/api/ping');
    },
    unload() {
      // Called ~ onunload callback; axios doesn't work there.
      // todo: Only tested on Linux+Firefox for now
      navigator.sendBeacon('/api/unload', '');
    },
  },
}
</script>

<style>
.container {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  text-align: center;
}

.title {
  font-family: "Quicksand", "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; /* 1 */
  display: block;
  font-weight: 300;
  font-size: 100px;
  color: #35495e;
  letter-spacing: 1px;
}

.subtitle {
  font-weight: 300;
  font-size: 42px;
  color: #526488;
  word-spacing: 5px;
  padding-bottom: 15px;
}

.links {
  padding-top: 15px;
}
</style>

