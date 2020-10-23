<template>
  <div class="fixed-page">
    <PageHeader>
      <PageHeaderItem>
        <b-button
          class="header-button-icon queue-button"
          data-toggle="tooltip"
          title="Start the queue"
          @click="start"
          :disabled="
            queue_state === QueueState.RUNNING ||
            queue.length === 0 ||
            !connected
          "
        >
          <i class="fa fa-play" />
        </b-button>
        <b-button
          class="header-button-icon queue-button"
          data-toggle="tooltip"
          title="Stop the queue"
          @click="stop"
          :disabled="queue_state === QueueState.STOPPED || !connected"
        >
          <i class="fa fa-stop" />
        </b-button>
        <b-button
          class="header-button-icon queue-button"
          data-toggle="tooltip"
          title="Clear the queue"
          @click="show_clear_popover"
          :disabled="
            queue_state === QueueState.RUNNING ||
            queue.length === 0 ||
            !connected
          "
          id="clear-queue"
        >
          <i class="fa fa-trash" />
          <b-popover
            v-if="show_popover"
            target="clear-queue"
            custom-class="queue-popover"
            id="clear-queue-popover"
            :show.sync="show_popover"
            :delay="{ show: 50, hide: 200 }"
            placement="bottomright"
            container="main"
            boundary="main"
          >
            <b-button variant="primary" @click="clear">
              <i class="fa fa-check" />
              &nbsp; Clear analysis queue
            </b-button>
            <b-button variant="danger" @click="hide_clear_popover">
              <i class="fa fa-times" />
            </b-button>
          </b-popover>
        </b-button>
        <span class="header-text queue-info">{{ queue_info }}</span>
      </PageHeaderItem>
      <PageHeaderItem> </PageHeaderItem>
    </PageHeader>
  </div>
</template>

<script>
import PageHeader from "../components/header/PageHeader";
import PageHeaderItem from "../components/header/PageHeaderItem";

import { QueueState, AnalyzerState } from "../static/api";

export default {
  name: "index",
  components: {
    PageHeader,
    PageHeaderItem,
  },
  mounted() {},
  methods: {
    start() {
      this.$store.dispatch("analyzers/q_start");
    },
    stop() {
      this.$store.dispatch("analyzers/q_stop");
    },
    show_clear_popover() {
      this.show_popover = true;
    },
    hide_clear_popover() {
      this.show_popover = false;
    },
    clear() {
      this.$store.dispatch("analyzers/q_clear");
      this.hide_clear_popover();
    },
  },
  computed: {
    connected() {
      return this.$store.getters["analyzers/isConnected"];
    },
    queue() {
      return this.$store.getters["analyzers/getQueue"];
    },
    queue_state() {
      return this.$store.getters["analyzers/getQueueState"];
    },
    queue_info() {
      const status = this.$store.getters["analyzers/getFullStatus"];

      const N = this.queue.length;
      const done = this.queue.reduce(
        function (done, id) {
          if (status.hasOwnProperty(id)) {
            if (status[id].state === AnalyzerState.DONE) {
              return {
                N: done.N + 1,
                progress: done.progress + status[id].progress,
              };
            } else {
              return {
                ...done,
                progress: done.progress + status[id].progress,
              };
            }
          } else {
            return done;
          }
        },
        { N: 0, progress: 0 }
      );

      if (this.queue_state === QueueState.RUNNING) {
        const percentage = Math.round((done.progress / N) * 100);
        return `Analyzing queue: ${percentage}% (${done.N}/${N} done)`;
      } else {
        return `${N === 0 ? "No" : N} ${
          N === 1 ? "analysis" : "analyses"
        } queued`.concat(
          done.N !== 0 ? ` (${done.N !== N ? done.N : "all"} done).` : "."
        );
      }
    },
  },
  data() {
    return { QueueState, show_popover: false };
  },
};
</script>

<style lang="scss">
@import "../assets/scss/_bootstrap-variables";
@import "../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

$clear-popover-scoot: 17px; // align popover 'ok' button with left edge of 'close' button
$clear-popover-arrow-nudge: 2px; // align arrow with center of button

.queue-button {
  font-size: 16px;
  vertical-align: middle;
  &:disabled {
    pointer-events: none;
  }
  .fa {
    padding: 0;
  }
}
.queue-info {
  padding: 5px;
  margin-left: 4px;
  font-family: monospace;
}

.queue-popover {
  margin-left: -$clear-popover-scoot;
  .arrow {
    left: calc(
      #{$clear-popover-scoot} - #{$clear-popover-arrow-nudge}
    ) !important;
  }
}
</style>
