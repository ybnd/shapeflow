<template>
  <div class="hovertext">
    <div @click="show = true" :class="classList" id="new-analysis">
      <i :class="'fa fa-plus'"></i>
      Analysis...
      <b-popover
        target="new-analysis"
        :show.sync="show"
        @bv::popover::shown="handleUpdatePopover"
        placement="right"
        boundary="viewport"
        class="new-analysis-popover"
        container="body"
        :class="{ connected: isConnected, 'not-connected': !isConnected }"
      >
        <div class="popover-form-container" v-if="isConnected">
          <b-row>
            <BasicConfig ref="new_analyzer_form" />
          </b-row>

          <b-row class="popover-form-row">
            <b-form-group>
              <b-input-group>
                <!--                <b-form-input id="name" type="text" placeholder="Analysis 7"></b-form-input>-->
                <div class="popover-buttons">
                  <b-button
                    variant="primary"
                    @click="handleNewAnalysis"
                    class="popover-ok"
                  >
                    <i class="fa fa-check" /> Add analysis
                  </b-button>
                  <b-button
                    variant="danger"
                    @click="show = false"
                    class="popover-cancel"
                  >
                    <i class="fa fa-times" />
                  </b-button>
                </div>
              </b-input-group>
            </b-form-group>
          </b-row>
        </div>
        <div v-else class="no-connection-message">
          <h6>
            <i class="fa fa-exclamation-triangle" /> &nbsp;
            <b>Not connected to the application!</b>
          </h6>
          <p>Restart the server by running `app.py` or `server.py`</p>
        </div>
      </b-popover>
    </div>
  </div>
</template>

<script>
import BasicConfig from "../config/BasicConfig";

export default {
  name: "sidebar-nav-link",
  props: {
    icon: {
      type: String,
      default: "",
    },
    badge: {
      type: Object,
      default: () => {},
    },
    variant: {
      type: String,
      default: "",
    },
  },
  components: { BasicConfig },
  methods: {
    handleUpdatePopover() {
      // console.log("UPDATING POPOVER");
    },
    handleNewAnalysis() {
      let config = this.$refs.new_analyzer_form.getConfig();

      // console.log("new analysis: config is");
      // console.log(config);

      this.$refs.new_analyzer_form.isValid().then((ok) => {
        if (ok) {
          this.show = false;
          this.$store
            .dispatch("analyzers/init", { config: config })
            .then((id) => {
              this.$router.push(`/analysis/align?id=${id}`);
            });
        } else {
          this.$store.commit("analyzers/newNotice", {
            notice: { message: "Form is incomplete." },
          });
        }
      });
    },
  },
  computed: {
    classList() {
      return ["nav-link", this.linkVariant, ...this.itemClasses];
    },
    linkVariant() {
      return this.variant ? `nav-link-${this.variant}` : "";
    },
    itemClasses() {
      return this.classes ? this.classes.split(" ") : [];
    },
    isExternalLink() {
      return this.url.substring(0, 4) === "http";
    },
    isApiLink() {
      return this.url.substring(0, 4) === "/api";
    },
    form_ref() {
      return id + "form";
    },
    isConnected() {
      return this.$store.getters["analyzers/isConnected"];
    },
  },
  data() {
    return {
      show: false,
      selected: "dt", // todo: this means that the default value is always reset; we should go by the history though!
      interval_placeholder: {
        Nf: "# frames", // todo: this works when `selected`is changed here, but I'm not sure how to make it resolve on click...
        dt: "interval (s)",
      },
    };
  },
};
</script>

<style lang="scss" scoped>
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

$max-width: 800px;
$popover-width: Min(Calc(#{$content-width} - 40px), #{$max-width});

.hovertext * {
  color: transparent;
}
.hovertext:hover * {
}

.popover {
  /*width: 600px;*/

  max-width: none;
  z-index: 9000;
  /* Should be drawn over moveable, which is @ z-index 3000 */
  /* https://github.com/daybrush/moveable/blob/master/handbook/handbook.md#toc-custom-css */
  &:connected {
    width: $popover-width !important;
  }
  &:not-connected {
  }
}
.popover-body {
  display: flex !important;
}
.popover-form-container {
  width: $popover-width;
  flex-direction: column;
  display: flex;
  padding-top: 0;
  padding-left: 12px;
  padding-right: 8px;
  margin-bottom: -1px;
}
.popover-buttons {
}

.no-connection-message {
  margin-bottom: -16px;
}
</style>
