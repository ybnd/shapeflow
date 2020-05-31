<template>
  <PageHeaderItem>
    <div class="slider-container">
      <div class="slider-caption">{{ currentTime }} / {{ totalTime }}</div>
      <!--      todo: should format number into '00:00'-->
      &ensp;
      <vue-slider
        v-model="position"
        v-bind="options"
        ref="slider"
        @change="handleSeek"
      />
    </div>
  </PageHeaderItem>
</template>

<script>
import { seek } from "../../static/api";
import { events } from "../../static/events";

import VueSlider from "vue-slider-component";
import PageHeaderItem from "./PageHeaderItem";

import { throttle, debounce } from "throttle-debounce";

import VueHotkey from "v-hotkey";
import Vue from "vue";

Vue.use(VueHotkey);

export default {
  name: "PageHeaderSeek",
  props: {
    id: {
      type: String,
      default: "",
      required: true
    }
  },
  components: { VueSlider, PageHeaderItem },
  beforeMount() {
    this.resetSeekPosition();

    this.$root.$on(events.seek.get(this.id), this.getSeekPosition);
    this.$root.$on(events.seek.set(this.id), this.handleSeek);
    this.$root.$on(events.seek.reset(this.id), this.resetSeekPosition);
    this.$root.$on(events.seek.step_fw(this.id), this.stepForward);
    this.$root.$on(events.seek.step_bw(this.id), this.stepBackward);
  },
  beforeDestroy() {
    this.position = null;

    clearInterval(this.syncInterval);

    this.$root.$off(events.seek.get(this.id), this.getSeekPosition);
    this.$root.$off(events.seek.set(this.id), this.handleSeek);
    this.$root.$off(events.seek.reset(this.id), this.resetSeekPosition);
    this.$root.$off(events.seek.step_fw(this.id), this.stepForward);
    this.$root.$off(events.seek.step_bw(this.id), this.stepBackward);
  },
  methods: {
    setSeekPosition() {
      seek(this.id, this.position).then(position => {
        this.position = position;
      });
    },
    handleSeek: throttle(
      100,
      true,
      debounce(25, true, function() {
        this.setSeekPosition();
      })
    ),
    resetSeekPosition() {
      console.log(`PageHeaderSeek(${this.id}.resetSeek()`);
      this.position = null;
      this.handleSeek();
    },
    stepForward() {
      this.position = this.position + this.step;
      this.handleSeek();
    },
    stepBackward() {
      this.position = this.position - this.step;
      this.handleSeek();
    }
  },
  computed: {
    keymap() {
      return {
        right: this.stepForward,
        left: this.stepBackward
      };
    }
  },
  data() {
    return {
      position: null,
      step: 0.01,
      options: {
        dotSize: 14,
        width: 120,
        height: 4,
        contained: false,
        direction: "ltr",
        data: null,
        min: 0.0,
        max: 1.0,
        interval: 0.01,
        disabled: false,
        clickable: true,
        duration: 0.05,
        adsorb: false,
        lazy: false,
        tooltip: "inactive",
        tooltipPlacement: "bottom",
        tooltipFormatter: this.formatTooltip,
        useKeyboard: true,
        keydownHook: null,
        dragOnClick: false,
        enableCross: true,
        fixed: false,
        order: true,
        marks: false,
        process: false
      },
      syncInterval: null,
      currentTime: 0,
      totalTime: 0
    };
  }
};
</script>

<style lang="scss">
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

.vue-slider {
  padding: 4px 4px;
}

.vue-slider-rail {
  background: $gray-100 !important;
}

.vue-slider-dot {
  background: darken(theme-color("primary"), 10%);
  border-radius: 50%;
}

.vue-slider-dot-tooltip {
}

.slider-container {
  display: flex;
  flex-direction: row;
  padding-top: 4px;
  padding-left: 4px;
  padding-right: 4px;
}

.slider-caption {
  height: 14px;
  margin-bottom: 4px;
}
</style>
