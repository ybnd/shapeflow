<template>
  <div
    class="result-container"
    :class="container_class"
    ref="container"
    :key="charts_key"
  >
    <template v-for="(feature_data, feature) in result">
      <div
        class="result"
        :class="result_class"
        :key="`result-${name}-${feature}`"
      >
        <ResultChart
          :chart-data="{
            datasets: feature_data,
            unit: $store.state.schemas.feature.units[feature],
          }"
          :options="{
            ...options,
            legend: {
              // display: is_last(index),
              position: 'bottom',
            },
            scales: {
              xAxes: [
                {
                  scaleLabel: {
                    // display: is_last(index),
                    labelString: 'Time (s)',
                    fontStyle: 'bold',
                    fontSize: 14,
                  },
                  ticks: {
                    stepSize: 60,
                    userCallback: formatTick,
                    max: maxX,
                  },
                },
              ],
              yAxes: [
                {
                  scaleLabel: {
                    display: true,
                    labelString: `${$store.state.schemas.feature.labels[feature]} (${$store.state.schemas.feature.units[feature]})`,
                    fontStyle: 'bold',
                    fontSize: 14,
                  },
                },
              ],
            },
          }"
        />
      </div>
    </template>
  </div>
</template>

<script>
import Vue from "vue";

import AsyncComputed from "vue-async-computed";

import { get_results, get_colors } from "../../static/api";

import ResultChart from "../../components/results/ResultChart";
import { events } from "../../static/events";
import { seconds2timestr } from "../../static/util";

Vue.use(AsyncComputed);

export default {
  name: "ResultChartStack",
  props: {
    id: {
      type: String,
      required: true,
    },
    container_class: {
      type: String,
      default: "",
    },
    result_class: {
      type: String,
      default: "",
    },
    canvas_class: {
      type: String,
      default: "",
    },
  },
  components: { ResultChart },
  beforeMount() {
    this.updateChartsKey();
    window.addEventListener("resize", this.updateChartsKey);
    this.$root.$on(events.data.update(this.id), this.updateChartsKey);
  },
  beforeDestroy() {
    window.removeEventListener("resize", this.updateChartsKey);
  },
  methods: {
    is_last(index) {
      return index === Object.keys(this.result).length - 1;
    },
    updateChartsKey() {
      this.charts_key = Date.now();
    },
    formatTick(tick) {
      return seconds2timestr(tick);
    },
  },
  computed: {
    name() {
      return this.$store.getters["analyzers/getName"](this.id);
    },
    maxX() {
      return Math.max(
        ...this.result[Object.keys(this.result)[0]][0].data
          .filter((point) => point.x !== null)
          .map((point) => point.x)
      );
    },
  },
  asyncComputed: {
    colors: {
      get() {
        return get_colors(this.id).then((colors) => {
          return colors;
        });
      },
      default: null,
    },
    result: {
      async get() {
        if (this.colors !== null) {
          return get_results(this.id).then((results) => {
            // backend returns results ~ pandas.DataFrame.to_json(orient='split')
            // -> convert to
            // {
            //  feature:
            //    [                           -> array of data / mask
            //      {
            //        ...metadata,
            //        data: [{x:t y:mask}]    -> array of data points
            //      }
            //    ]
            // }
            console.log("ResultChartStack.result.get() -> results = ");
            console.log(results);

            let formatted_results = {};

            for (const feature of Object.keys(results)) {
              console.log(`feature = ${feature}`);
              let feature_results = [];
              if (results.hasOwnProperty(feature)) {
                let masks = results[feature].columns.slice(1);

                for (let m = 0; m < masks.length; m++) {
                  let data = [];

                  console.log(results[feature].data.length);

                  for (let i = 0; i < results[feature].data.length; i++) {
                    data = [
                      ...data,
                      {
                        x: results[feature].data[i][0],
                        y: results[feature].data[i][m + 1],
                      },
                    ];
                  }

                  feature_results = [
                    ...feature_results,
                    {
                      label: masks[m],
                      backgroundColor: this.colors[feature][m],
                      borderColor: this.colors[feature][m],
                      showLine: true,
                      data: data,
                    },
                  ];
                }
              }
              formatted_results = {
                ...formatted_results,
                [feature]: feature_results,
              };
            }

            return formatted_results;
          });
        } else {
          return {};
        }
      },
      default: {},
    },
  },
  data() {
    return {
      options: {
        responsive: true,
        maintainAspectRatio: false,
      },
      charts_key: "",
    };
  },
};
</script>

<style lang="scss">
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

.result-container {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding-top: 8px;
}
.result {
  position: relative;
  flex-shrink: 1;
  display: flex;
}
</style>
