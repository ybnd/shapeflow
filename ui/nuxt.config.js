const BundleAnalyzerPlugin = require("webpack-bundle-analyzer")
  .BundleAnalyzerPlugin;

const changeLoaderOptions = (loaders) => {
  if (loaders) {
    for (const loader of loaders) {
      if (loader.loader === "sass-loader") {
        Object.assign(loader.options, {
          includePaths: ["./assets"],
        });
      }
    }
  }
};

module.exports = {
  head: {
    title: "isimple",
    meta: [
      { charset: "utf-8" },
      {
        name: "viewport",
        content:
          "width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no",
      },
      {
        hid: "description",
        name: "description",
        content: "",
      },
    ],
    link: [{ rel: "icon", type: "image/x-icon", href: "/favicon.ico" }],
  },

  router: {
    linkActiveClass: "active open",
    mode: "hash",
  },

  loading: { color: "#42A5CC" },

  css: [
    "~/node_modules/font-awesome/css/font-awesome.min.css",
    "~/node_modules/simple-line-icons/css/simple-line-icons.css",
    "~/node_modules/bootstrap-vue/dist/bootstrap-vue.css",
    { src: "~/assets/scss/style.scss", lang: "scss" },
  ],

  plugins: [],

  modules: ["@nuxtjs/axios", "@nuxtjs/proxy", "bootstrap-vue/nuxt"],

  bootstrapVue: {
    components: [
      "BButton",
      "BButtonGroup",
      "BDropdown",
      "BDropdownItem",
      "BCol",
      "BRow",
      "BContainer",
      "BFormGroup",
      "BFormRow",
      "BFormInput",
      "BInputGroupPrepend",
      "BFormTextarea",
      "BCollapse",
      "BInputGroup",
      "BInputGroupText",
      "BFormSelect",
      "BProgress",
      "BPopover",
      "BTbody",
      "BCard",
    ],
  },

  axios: {
    // See https://github.com/nuxt-community/axios-module#options
  },

  proxy: {
    "/api": {
      target: "http://localhost:7951",
      pathrewrite: { "^/api": "/" },
    },
  },

  styleResources: {
    scss: "./assets/scss/style.scss",
  },

  build: {
    extend(config, { isDev, isClient }) {
      config.externals = {
        moment: "moment", // exclude moment.js
      };

      if (isDev && isClient) {
        config.devtool = "eval-source-map";
        config.module.rules.push({
          enforce: "pre",
          test: /\.(js|vue)$/,
          loader: "eslint-loader",
          exclude: /(node_modules)/,
        });

        const vueLoader = config.module.rules.find(
          ({ loader }) => loader === "vue-loader"
        );
        const {
          options: { loaders },
        } = vueLoader || { options: {} };

        if (loaders) {
          for (const loader of Object.values(loaders)) {
            changeLoaderOptions(Array.isArray(loader) ? loader : [loader]);
          }
        }

        config.module.rules.forEach((rule) => changeLoaderOptions(rule.use));
      }
      if (isClient) {
      }
    },
    plugins: [
      // new BundleAnalyzerPlugin({
      //   analyzerMode: "static",
      //   generateStatsFile: true,
      //   openAnalyzer: true,
      //   logLevel: "info",
      //   reportFilename: "/home/ybnd/temp/reports/ui-webpack-report.html",
      //   statsFilename: "/home/ybnd/temp/reports/ui-webpack-stats.json",
      // }),
    ],
  },

  lintOnSave: true,
};
