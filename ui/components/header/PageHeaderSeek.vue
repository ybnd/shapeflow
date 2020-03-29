<template>
  <PageHeaderItem>
    <div class="slider-container">
      <div class="slider-caption">Seek position</div>
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
import VueSlider from "vue-slider-component";
import PageHeaderItem from "./PageHeaderItem";
import { seek, get_seek_position } from "../../static/api";
import { throttle, debounce } from "throttle-debounce";

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
    this.setSeekPosition(0.5);
    this.updatePosition = setInterval(1000, this.getSeekPosition);
  },
  beforeDestroy() {
    clearInterval(this.updatePosition);
  },
  methods: {
    setSeekPosition() {
      seek(this.id, this.position).then(position => {
        this.position = position;
      });
    },
    getSeekPosition() {
      get_seek_position(this.id).then(position => {
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
    formatTooltip(tooltip) {
      return `${Math.round(tooltip * 100)}%`;
    }
  },
  data() {
    return {
      position: null,
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
        clickable: false,
        duration: 0.1,
        adsorb: false,
        lazy: false,
        tooltip: "active",
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
      }
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
  flex-direction: column;
  padding-left: 4px;
  padding-right: 4px;
}

.slider-caption {
  height: 14px;
  margin-bottom: 4px;
}
</style>
