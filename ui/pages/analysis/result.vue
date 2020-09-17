<template>
  <div class="fixed-page">
    <PageHeader>
      <PageHeaderItem>
        <b-dropdown
          :text="info"
          data-toggle="tooltip"
          title="Select a result"
          placeholder="select a run to display"
        >
          <b-dropdown-item
            v-for="(time, run) in db.list"
            :key="run"
            @click="handleGetResult(run)"
          >
            {{ result_info(run) }}
          </b-dropdown-item>
        </b-dropdown>
      </PageHeaderItem>
    </PageHeader>
    <ResultChartStack
      v-if="colors !== undefined && result !== undefined"
      :id="id"
      :key="id"
      :colors="colors"
      :raw_result="result"
      container_class="fullpage-result-container"
      result_class="fullpage-result"
    />
  </div>
</template>

<script>
import ResultChartStack from "../../components/results/ResultChartStack";
import PageHeader from "../../components/header/PageHeader";
import PageHeaderItem from "../../components/header/PageHeaderItem";

import { get_db_id, get_result_list, get_result, get_colors } from "static/api";
import Vue from "vue";
import AsyncComputed from "vue-async-computed";

Vue.use(AsyncComputed);

export default {
  name: "result",
  components: { PageHeader, PageHeaderItem, ResultChartStack },
  mounted() {
    this.sync();
  },
  methods: {
    sync() {
      this.colors = undefined;
      this.result = undefined;

      get_db_id(this.id).then((id) => {
        this.db.id = id;
        get_result_list(this.db.id).then((list) => {
          // console.log(`get_result_list() callback: list =`);
          // console.log(list);
          this.db.list = list;
          if (list) {
            this.handleGetResult(Math.max(...Object.keys(list).map(Number)));
          } else {
            this.info = "No results yet!";
          }
        });
      });
    },
    handleGetResult(run) {
      // console.log(`result.handleGetResult() run=${run}`);
      this.info = this.result_info(run);
      return get_colors(this.id).then((colors) => {
        // console.log(`result.handleGetResult() callback 1 colors=`);
        // console.log(colors);
        this.colors = colors;
        get_result(this.db.id, run).then((result) => {
          // console.log(`result.handleGetResult() callback 2 result=`);
          // console.log(result);
          this.result = result;
        });
      });
    },
    result_info(run) {
      run = Number(run);
      if (Number.isInteger(run)) {
        return `${this.name}, Run ${run}, ${this.db.list[run]}`;
      } else {
        return "Select a run to display";
      }
    },
  },
  watch: {
    "$route.query.id"() {
      this.sync();
    },
  },
  computed: {
    id() {
      return this.$route.query.id;
    },
    name() {
      return this.$store.getters["analyzers/getName"](this.id);
    },
  },
  data() {
    return {
      db: {
        id: undefined,
        run: undefined,
        runs: {},
        list: {},
      },
      result: undefined,
      colors: undefined,
      info: null,
    };
  },
};
</script>

<style lang="scss">
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

.fullpage-result-container {
  width: $content-width;
  height: $content-height;
  max-width: $content-width;
  max-height: $content-height;
  display: flex;
  flex-direction: column;
}
.fullpage-result {
  position: relative;
  flex-shrink: 1;
  flex-grow: 1;
  flex-basis: 400px;
  max-height: $content-height;
  min-height: 200px;
  display: flex;
  width: $content-width;
}
.fullpage-result canvas {
  /*flex-grow: 1;*/
  width: $content-width;
}
</style>
