// The default Babel config disables ES modules transpilation because webpack already knows how to handle ES modules.
// However, we do need to enable it for our tests because Jest tests run directly in Node.

function isBabelLoader(caller) {
  return caller && caller.name === "babel-loader";
}

module.exports = function(api) {
  if (api.env("test") && !api.caller(isBabelLoader)) {
    return {
      plugins: [
        "@babel/plugin-proposal-object-rest-spread"
      ],
      presets: [
        [
          "@babel/preset-env",
          {
            targets: {
              node: "current"
            }
          }
        ],
      ]
    };
  } else {
    return {};
  }
};
