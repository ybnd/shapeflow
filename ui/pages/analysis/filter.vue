<template>
  <!--  https://stackoverflow.com/questions/14025438 -->
  <div class="fixed-page">
    <PageHeader>
      <PageHeaderItem>
        <b-button @click="handleAnalyze">Analyze</b-button>
      </PageHeaderItem>
      <PageHeaderSeek :id="id" />
      <PageHeaderItem>
        <!-- todo: should not set features here though! -->
      </PageHeaderItem>
      <PageHeaderItem>
        <b-button-group>
          <b-dropdown :text="`${this.mask}`" data-toggle="tooltip" title="Mask">
            <b-dropdown-item
              v-for="(mask, index) in masks"
              :key="`mask-${mask}`"
              @click="handleSetMask(mask, index)"
            >
              {{ mask }}
            </b-dropdown-item>
          </b-dropdown>
          <b-dropdown
            :text="`${this.filter}`"
            data-toggle="tooltip"
            title="Filter type"
          >
            <b-dropdown-item
              v-for="filter in filter_options"
              :key="`filter-${filter}`"
              @click="handleSetFilter(filter)"
            >
              {{ filter }}
            </b-dropdown-item>
          </b-dropdown>
        </b-button-group>
      </PageHeaderItem>
    </PageHeader>
    <div class="filter">
      <img :src="frame_url" alt="" class="streamed-image-f" />
      <img
        :src="state_url"
        alt=""
        class="streamed-image-f overlay"
        ref="frame"
        @click="handleClick"
      />
    </div>
    <div class="controls"></div>
  </div>
</template>

<script>
import { get_options, set_config, url, analyze } from "../../static/api";
import PageHeader from "../../components/header/PageHeader";
import PageHeaderItem from "../../components/header/PageHeaderItem";
import PageHeaderSeek from "../../components/header/PageHeaderSeek";
import { throttle, debounce } from "throttle-debounce";

export default {
  name: "filter",
  beforeMount() {
    this.initFilter();
    this.waitUntilHasRect = setInterval(this.updateFrameOnceHasRect, 100);
  },
  beforeDestroy() {
    clearInterval(this.waitUntilHasRect);
    clearInterval(this.updateCall);
  },
  components: {
    PageHeader,
    PageHeaderItem,
    PageHeaderSeek
  },
  methods: {
    initFilter() {
      get_options("feature").then(options => {
        this.feature_options = options;
      });
      get_options("filter").then(options => {
        this.filter_options = options;
      });
      this.masks = this.$store.getters["analyzers/getMasks"](this.id);
      this.mask = this.masks[0];

      this.filter = this.$store.getters["analyzers/getFilterType"](this.id, 0);

      this.feature = this.$store.getters["analyzers/getFeatures"](this.id)[0];
      console.log(`setting this.feature to ${this.feature}`);

      this.$store.dispatch("filter/init", { id: this.id });
    },
    updateFrame() {
      console.log("Updating frame...");
      let frame = this.$refs.frame.getBoundingClientRect();
      console.log(frame);
      this.$store.commit("filter/setFrame", { id: this.id, frame: frame });
    },
    updateFrameOnceHasRect() {
      // todo: clean up
      let frame_ok = false;
      let overlay_ok = false;
      if (!(this.waitUntilHasRect === undefined)) {
        if (this.$refs.frame.getBoundingClientRect()["width"] > 50) {
          console.log("HAS FRAME");
          this.updateFrame();
          frame_ok = true;
        }
      }
      if (frame_ok) {
        clearInterval(this.waitUntilHasRect);
      }
    },
    handleClick(e) {
      this.$store.dispatch("filter/set", { id: this.id, event: e });
    },
    handleAnalyze() {
      analyze(this.id);
    },
    handleSetFeature(feature) {
      this.$store
        .dispatch("analyzers/set_config", {
          id: this.id,
          config: { features: [feature] }
        })
        .then(stuff => {
          console.log("in analyzers/set_config callback");
          let features = this.$store.getters["analyzers/getFeatures"](this.id);
          this.feature = features[0];
        });
    },
    handleSetMask(mask, index) {
      this.mask = mask;

      this.filter = this.$store.getters["analyzers/getFilterType"](
        this.id,
        index
      );
      this.filter_data = this.$store.getters["analyzers/getFilterData"](
        this.id,
        index
      );
    },
    handleSetFilter(filter) {
      let config = this.$store.getters["analyzers/getConfig"](this.id);
      config.masks[this.mask].filter.type = filter;

      this.$store
        .dispatch("analyzers/set_config", {
          id: this.id,
          config: config
        })
        .then(() => {
          this.filter = this.$store.getters["analyzers/getFilterType"](this.id);
        });
    }
  },
  computed: {
    id() {
      return this.$route.query.id;
    },
    state_url() {
      return url(this.$route.query.id, "stream/get_state_frame");
    },
    frame_url() {
      return url(this.$route.query.id, "stream/get_frame");
    }
  },
  data: () => ({
    waitUntilHasRect: null,
    feature: "",
    feature_options: {},
    filter: "",
    filter_options: {},
    filter_data: {},
    mask: "",
    masks: {}
  })
};
</script>

<style lang="scss">
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

.filter {
  position: absolute;
  float: left;
  display: block;
  margin: 0 0 0 0;
  max-height: calc(100vh - #{$header-height});
}

.streamed-image-f {
  z-index: 100; /* has to on top of fixed-page etc. to handle clicks*/
  display: block;
  max-width: calc(
    100vw - #{$sidebar-width}
  ); /* todo: handle actual width! (import assets/scss/core/_variables -> doesn't compile) */
  max-height: calc(100vh - #{$header-height});
  width: auto;
  height: auto;
  position: absolute;
}

.overlay {
  mix-blend-mode: multiply;
}

.hidden * {
  visibility: hidden;
}
</style>
