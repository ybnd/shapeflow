<template>
  <section class="container">
    <div>
      <div class="test">
        <a @click="init()" class="button--grey">New VideoAnalyzer</a>
        <a @click="setAss()" class="button--grey">Send ass</a>
        <a @click="setGrass()" class="button--grey">Send grass</a>
      </div>
    </div>
  </section>
</template>

<script>
import axios from 'axios'

export default {
  methods: {
    ping () {
      axios.get('/api/ping');
    },
    unload() {
      // Called ~ onunload callback; axios doesn't work there.
      // todo: Only tested on Linux+Firefox for now
      navigator.sendBeacon('/api/unload', '');
    },
    init() {
      axios.get('/api/VideoAnalyzer/init');
    },
    setAss() {
      axios.get('/api/VideoAnalyzer/0/set_config?config={"video_path":"ass"}');
    },
    setGrass() {
      axios.get('/api/VideoAnalyzer/0/set_config?config={"design_path":"grass"}');
    },
  },
  beforeMount() {
      window.onload = this.ping;
      window.onunload = this.unload;
      setInterval(this.ping, 500);
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

