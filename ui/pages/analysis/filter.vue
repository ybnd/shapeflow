<template>
  <!--  https://stackoverflow.com/questions/14025438 -->
  <div class="fixed-page">
    <PageHeader>
      <PageHeaderItem>
        <b-button>Analyze</b-button>
      </PageHeaderItem>
      <PageHeaderSeek :id="id" />
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
import { set_filter, url_api } from "../../static/api";
import PageHeader from "../../components/header/PageHeader";
import PageHeaderItem from "../../components/header/PageHeaderItem";
import PageHeaderSeek from "../../components/header/PageHeaderSeek";
import { throttle, debounce } from "throttle-debounce";

export default {
  name: "filter",
  beforeMount() {
    this.init();
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
    init() {
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
    }
  },
  computed: {
    id() {
      return this.$route.query.id;
    },
    state_url() {
      return url_api(this.$route.query.id, "stream/get_state_frame");
    },
    frame_url() {
      return url_api(this.$route.query.id, "stream/get_frame");
    }
  },
  data: () => ({
    waitUntilHasRect: null
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
