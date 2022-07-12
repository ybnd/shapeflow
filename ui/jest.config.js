global.XMLHttpRequest = undefined;

module.exports = {
  // tell Jest to handle `*.vue` files
  moduleFileExtensions: [
    "js",
    "vue"
  ],
  watchman: false,
  moduleNameMapper: {
    "^~/(.*)$": "<rootDir>/$1",
    "^~~/(.*)$": "<rootDir>/$1",
  },
  transform: {
    // process js with `babel-jest`
    "^.+\\.js$": "<rootDir>/node_modules/babel-jest",
    // process `*.vue` files with `vue-jest`
    ".*\\.(vue)$": "<rootDir>/node_modules/vue-jest"
  },
  snapshotSerializers: ["<rootDir>/node_modules/jest-serializer-vue"],
  collectCoverage: true,
  collectCoverageFrom: [
    "<rootDir>/components/**/*.vue",
    "<rootDir>/layouts/*.vue",
    "<rootDir>/pages/*.vue",
    "<rootDir>/pages/**/*.vue",
    "<rootDir>/src/*.js",
    "<rootDir>/store/*.js"
  ],
  testEnvironment: "jsdom",
  testURL: 'http://127.0.0.1:7951',
  verbose: true,
};
