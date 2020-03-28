<template>
  <div class="hovertext">
    <div @click="show = true" :class="classList" id="new-analysis">
      <i :class="'fa fa-plus'"></i>
      New analysis...
      <b-popover
        target="new-analysis"
        :show.sync="show"
        placement="right"
        boundary="viewport"
        class="new-analysis-popover"
        container="body"
      >
        <div class="popover-form-container">
          <basic-config
            ref="new_analyzer_form"
            :formStyle="{ width: '600px' }"
          />
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
                    <i class="fa fa-check" /> New analysis
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
      </b-popover>
    </div>
  </div>
</template>

<script>
import BasicConfig from "../config/BasicConfig";
import { set_config, launch } from "../../static/api";

export default {
  name: "sidebar-nav-link",
  props: {
    icon: {
      type: String,
      default: ""
    },
    badge: {
      type: Object,
      default: () => {}
    },
    variant: {
      type: String,
      default: ""
    }
  },
  components: { BasicConfig },
  methods: {
    handleNewAnalysis() {
      let config = this.$refs.new_analyzer_form.getConfig();
      this.$refs.new_analyzer_form.hasValidFiles().then(ok => {
        if (ok) {
          this.show = false;
          this.$store.dispatch("analyzers/init").then(id => {
            set_config(id, config).then(config => {
              // todo: should be a $store action
              this.$store.commit("analyzers/setAnalyzerConfig", {
                id: id,
                config: config
              });
              launch(id);
            });
          });
        } else {
          // todo: some visual warning that it's incomplete...
          console.log("FORM IS NOT COMPLETE");
        }
      });
    },
    selectFrameIntervalSetting(e) {
      this.selected = e.target.value;
      console.log("ass");
      console.log(this.selected);
      console.log(this.interval_placeholder[selected]);
    }
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
    }
  },
  data() {
    return {
      show: false,
      selected: "dt", // todo: this means that the default value is always reset; we should go by the history though!
      interval_placeholder: {
        Nf: "# frames", // todo: this works when `selected`is changed here, but I'm not sure how to make it resolve on click...
        dt: "interval (s)"
      }
    };
  }
};
</script>

<style scoped>
.hovertext .nav-link {
  color: transparent;
}
.hovertext:hover .nav-link {
}

.popover {
  width: 600px;
  max-width: 600px;
  z-index: 9000;
  /* Should be drawn over moveable, which is @ z-index 3000 */
  /* https://github.com/daybrush/moveable/blob/master/handbook/handbook.md#toc-custom-css */
}
.popover-form-container {
  /* todo: should be a single component for the dashboard cards & this popover! Then we can recycle a bunch of stuff. */
  padding-top: 15px;
  padding-left: 12px;
  margin-right: -8px;
  margin-bottom: -16px;
}
.popover-form-row {
  margin-top: -10px;
  margin-bottom: -10px;
}
.popover-buttons {
  margin-left: -1px;
  margin-top: 32px;
}
</style>
