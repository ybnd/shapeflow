<script>
import { Scatter, mixins } from "vue-chartjs";

export default {
  name: "ResultChart",
  extends: Scatter,
  mixins: [mixins.reactiveProp],
  props: ["options"],
  mounted() {
    // this.chartData is created in the mixin.
    // If you want to pass options please create a local options object

    this.renderChart(this.chartData, {
      ...this.default_options,
      ...this.options
    });
  },
  data() {
    let vue = this; // todo: not super clean
    return {
      responsive: true,
      maintainAspectRatio: false,
      tooltips: {
        show: false,
        origin: { x: 0, y: 0 },
        labels: []
      },
      default_options: {
        elements: {
          point: {
            radius: 0,
            hoverRadius: 5,
            hitRadius: 5
          },
          line: {
            // stepped: true,
            fill: false,
            borderWidth: 2,
            tension: 0
          }
        },
        animation: {
          duration: 0
        },
        tooltips: {
          mode: "nearest",
          // enabled: false,
          // custom: function(tooltipModel) {
          //   // https://github.com/PierBover/vue-chartjs-tooltip
          //
          //   // todo: have to push $root event to parent elemtn; this one can't have <template>
          //

          //   vue.tooltips.show = tooltipModel.opacity !== 0;
          //   if (tooltipModel.dataPoints !== undefined) {
          //     console.log(tooltipModel);
          //     console.log(tooltipModel.dataPoints);
          //     vue.tooltips.labels = [];
          //     const keep = [];
          //     for (let i = 0; i < tooltipModel.dataPoints.length; i++) {
          //       vue.tooltips.labels = [
          //         ...vue.tooltips.labels,
          //         `NAME TIME VALUE`
          //       ];
          //     }
          //     console.log(vue.tooltips.labels);
          //   }
          // }
          callbacks: {
            label: function(tooltipItem, data) {
              // https://www.chartjs.org/docs/latest/configuration/tooltip.html
              var label = data.datasets[tooltipItem.datasetIndex].label || "";

              console.log(data);

              if (label) {
                label += ": ";
              }
              label += Math.round(tooltipItem.xLabel * 100) / 100;
              label += " s, ";
              label += Math.round(tooltipItem.yLabel * 100) / 100;
              label += " ";
              label += data.unit;
              return label;
            }
          }
        }
      }
    };
  }
};
</script>

<style scoped></style>
