<template>
  <div
    class="result-container"
    :class="container_class"
    ref="container"
    :key="charts_key"
  >
    <template v-for="(feature_data, feature) in result">
      <div class="result" :class="result_class" :key="`result-${feature}`">
        <ResultChart
          :chart-data="{
            datasets: feature_data,
            unit: features.units[feature],
          }"
          :options="{
            ...options,  // todo: should be a computed property
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
                    labelString: `${features.labels[feature]} (${features.units[feature]})`,
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
import ResultChart from "../../components/results/ResultChart";
import { events } from "../../static/events";
import { seconds2timestr } from "../../static/util";

export default {
  name: "ResultChartStack",
  props: {
    raw_result: {
      type: Object,
      required: true,
    },
    colors: {
      type: Array,
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
    maxX() {
      return Math.max(
        ...this.result[Object.keys(this.result)[0]][0].data
          .filter((point) => point.x !== null)
          .map((point) => point.x)
      );
    },
    result() {
      let formatted_results = {};  // todo: should be in static/results.js

      for (const feature of Object.keys(this.raw_result)) {
        // console.log(`feature = ${feature}`);
        let feature_results = [];
        if (this.raw_result.hasOwnProperty(feature)) {
          let masks = this.raw_result[feature].columns.slice(1);

          for (let m = 0; m < masks.length; m++) {
            let data = [];

            // console.log(this.raw_result[feature].data.length);

            for (let i = 0; i < this.raw_result[feature].data.length; i++) {
              data = [
                ...data,
                {
                  x: this.raw_result[feature].data[i][0],
                  y: this.raw_result[feature].data[i][m + 1],
                },
              ];
            }

            feature_results = [
              ...feature_results,
              {
                label: masks[m],
                backgroundColor: this.colors[m],
                borderColor: this.colors[m],
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
    },
    features() {
      // console.log(this.$store.getters["schemas/getFeature"]);
      return this.$store.getters["schemas/getFeature"];
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
  position: absolute;
  padding-top: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  margin: 0;
}
.result {
  position: relative;
  flex-shrink: 1;
  flex-grow: 1;
  display: relative;
}
</style>
