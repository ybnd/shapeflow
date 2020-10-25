<template>
  <PageHeaderItem>
    <div
      :class="{
        'slider-container': !isLoading,
        'slider-container-loading': isLoading,
      }"
    >
      <span class="header-text slider-caption"
        >{{ currentTime }} / {{ totalTime }}</span
      >
      <vue-slider
        v-model="position"
        v-bind="options"
        @change="handleSeek"
        @drag-start="handleDragStart"
        @drag-end="handleDragEnd"
      />
    </div>
  </PageHeaderItem>
</template>

<script>
import { api } from "../../src/api";
import { events } from "../../src/events";
import { seconds2timestr } from "../../src/util";

import VueSlider from "vue-slider-component";
import PageHeaderItem from "./PageHeaderItem";

import { throttle, debounce } from "throttle-debounce";

import VueHotkey from "v-hotkey";
import Vue from "vue";

Vue.use(VueHotkey);

const LOADING_INTERVAL = 100;

export default {
  name: "PageHeaderSeek",
  props: {
    id: {
      type: String,
      default: "",
      required: true,
    },
  },
  components: { VueSlider, PageHeaderItem },
  beforeMount() {
    api.va.__id__.get_seek_position(this.id).then((position) => {
      this.setPosition(position);
    });
    api.va.__id__.get_total_time(this.id).then((total) => {
      this.totalSeconds = total;
    });

    this.$root.$on(events.seek.set(this.id), this.handleSeek);
    this.$root.$on(events.seek.reset(this.id), this.resetSeek);
    this.$root.$on(events.seek.step_fw(this.id), this.stepForward);
    this.$root.$on(events.seek.step_bw(this.id), this.stepBackward);
  },
  beforeDestroy() {
    this.$root.$off(events.seek.set(this.id), this.handleSeek);
    this.$root.$off(events.seek.reset(this.id), this.resetSeek);
    this.$root.$off(events.seek.step_fw(this.id), this.stepForward);
    this.$root.$off(events.seek.step_bw(this.id), this.stepBackward);
  },
  methods: {
    setPosition(position) {
      this.position = position;
      setTimeout(() => {
        this.isLoading = false;
        // console.log(this.isLoading);
      }, LOADING_INTERVAL);
    },
    doSeek() {
      api.va.__id__.seek(this.id, this.position).then((position) => {
        this.position = position;
      });
    },
    handleSeek: throttle(
      100,
      true,
      debounce(25, true, function () {
        this.doSeek();
      })
    ),
    resetSeek() {
      // console.log(`PageHeaderSeek.resetSeek()`);
      this.setPosition(null);
      this.handleSeek();
    },
    stepForward() {
      this.position = this.position + this.step;
      this.handleSeek();
    },
    stepBackward() {
      this.position = this.position - this.step;
      this.handleSeek();
    },
    handleDragStart() {
      this.isDragging = true;
    },
    handleDragEnd() {
      this.isDragging = false;
    },
  },
  computed: {
    keymap() {
      return {
        right: this.stepForward,
        left: this.stepBackward,
      };
    },
    currentTime() {
      if (this.position !== null && this.totalSeconds !== null) {
        return seconds2timestr(this.position * this.totalSeconds);
      } else {
        return "";
      }
    },
    totalTime() {
      if (this.totalSeconds !== null) {
        return seconds2timestr(this.totalSeconds);
      } else {
        return "";
      }
    },
    dotSize() {
      return this.isLoading ? 0 : 14;
    },
  },
  data() {
    return {
      isLoading: true,
      isDragging: false,
      position: null,
      step: 0.01,
      options: {
        dotSize: 14,
        width: 120,
        height: 4,
        contained: true,
        direction: "ltr",
        data: null,
        min: 0.0,
        max: 1.0,
        interval: 0.01,
        disabled: false,
        clickable: true,
        duration: (LOADING_INTERVAL - 10) / 1000,
        adsorb: false,
        lazy: false,
        useKeyboard: true,
        keydownHook: null,
        dragOnClick: false,
        marks: false,
        process: false,
      },
      totalSeconds: null,
    };
  },
};
</script>

<style lang="scss">
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

.slider-container {
  display: flex;
  flex-direction: row;
  padding-top: 5px;

  .slider-caption {
    height: 14px;
    min-width: 100px;
    max-width: 200px;
    margin-bottom: 4px;
    margin-right: 4px;
  }

  .vue-slider {
    .vue-slider-rail {
      background: $gray-100 !important;
      cursor: pointer;

      .vue-slider-dot {
        background: darken(theme-color("primary"), 10%);
        border-radius: 50%;
        cursor: ew-resize;
      }
    }
  }
}
/* todo: can't get this to work with a 'loading' pseudo-class */
.slider-container-loading {
  display: flex;
  flex-direction: row;
  padding-top: 5px;

  .slider-caption {
    height: 14px;
    min-width: 100px;
    max-width: 200px;
    margin-bottom: 4px;
    margin-right: 4px;
  }

  .vue-slider {
    cursor: pointer;
    pointer-events: all;
    .vue-slider-rail {
      background: $gray-100 !important;
      .vue-slider-dot {
        //background: darken(theme-color("primary"), 10%);
        border-radius: 50%;
        cursor: ew-resize;
        transition: background 1s !important; /* todo doesn't work ~ changing the whole class... */
      }
    }
  }
}
</style>
