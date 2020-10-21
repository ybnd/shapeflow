<script>
import { Scatter, mixins } from "vue-chartjs";
import { seconds2timestr } from "../../src/util";

export function labelCallback (tooltipItem, data) {  // todo: should be in src/results.js
  // https://www.chartjs.org/docs/latest/configuration/tooltip.html
  var label = data.datasets[tooltipItem.datasetIndex].label || "";

  if (label) {
    label += ": ";
  }
  label += seconds2timestr(tooltipItem.xLabel);
  label += " ➔ ";
  label += Math.round(tooltipItem.yLabel * 100) / 100;
  label += " ";
  label += data.unit;
  return label;
}

export default {
  name: "ResultChart",
  extends: Scatter,
  mixins: [mixins.reactiveProp],
  props: ["options"],
  mounted() {
    // this.chartData is created in the mixin.
    this.renderChart(this.chartData, {
      ...this.default_options,
      ...this.options,
    });
  },
  data() {
    let vue = this; // todo: not super clean  -- also why was this again?
    return {
      responsive: true,
      maintainAspectRatio: false,
      tooltips: {
        show: false,
        origin: { x: 0, y: 0 },
        labels: [],
      },
      default_options: {
        elements: {
          point: {
            radius: 0,
            hoverRadius: 5,
            hitRadius: 5,
          },
          line: {
            // stepped: true,
            fill: false,
            borderWidth: 2,
            tension: 0,
          },
        },
        animation: {
          duration: 0,
        },
        tooltips: {
          mode: "nearest",
          callbacks: {
            label: labelCallback,
          },
        },
      },
    };
  },
};
</script>

<style scoped></style>
