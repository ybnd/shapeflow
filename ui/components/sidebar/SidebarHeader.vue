<template>
  <header class="sidebar-header">
    <ul class="sidebar-header-items">
      <li
        class="nav-link sidebar-header-button queue"
        v-if="queue_state === QueueState.STOPPED"
        @click="start"
      >
        <i class="fa fa-play" />
      </li>
      <li
        class="nav-link sidebar-header-button queue"
        v-if="queue_state === QueueState.RUNNING"
        @click="stop"
      >
        <i class="fa fa-stop" />
      </li>
      <li
        class="nav-link sidebar-header-button home"
        @click="$router.push('/')"
      >
        isimple
      </li>
    </ul>
  </header>
</template>

<script>
import { axios, api, QueueState } from "../../static/api";

export default {
  name: "sidebar-header",
  components: {},
  methods: {
    start() {
      axios.post(api("start"), this.payload);
    },
    stop() {
      axios.post(api("stop"));
    },
  },
  mounted() {
    // console.log(`SidebarHeader.mounted() -> queue_state = ${this.queue_state}`);
    // console.log(this.queue_state === QueueState.RUNNING);
    // console.log(this.queue_state === QueueState.STOPPED);
  },
  computed: {
    queue_state() {
      return this.$store.getters["analyzers/getQueueState"];
    },
    payload() {
      return { queue: this.$store.getters["analyzers/getQueue"] };
    },
  },
  data() {
    return {
      api,
      QueueState,
    };
  },
};
</script>

<style lang="scss" scoped>
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

$header-button-height: 28px;
$header-button-width: 28px;
$header-button-padding: 4px;

.sidebar-header {
  height: $header-height;
  padding: 4px;
  padding-top: 2px;
  padding-left: 3px;
  margin: 0;
}
.sidebar-header-items {
  margin: 0;
  padding: 0;
  height: calc(#{$header-height} - 4px);
  display: flex;
  flex-direction: row;
  overflow: hidden;
}

.sidebar-header-button {
  color: theme-color("gray-200");
  background: theme-color("gray-700");
  margin: 2px;
  padding: 4px;
  height: $header-button-height;
}

.queue {
  width: $header-button-width;
}

.sidebar-header-button i {
  color: theme-color("gray-300");
}

.home {
  margin: 2px;
  padding: 4px;
  height: $header-button-height;
  width: calc(
    #{$sidebar-width} - #{$header-button-width} - 3 * #{$header-button-padding}
  );
  font-family: Console, monospace;
}
</style>
