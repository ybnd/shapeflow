<template>
  <div class="fixed-page">
    <WebpackMarkdown :raw_content="raw_content" />
  </div>
</template>

<script>
import WebpackMarkdown from "../components/WebpackMarkdown";

export default {
  name: "about",
  components: { WebpackMarkdown },
  data() {
    return {
      raw_content: markdown.about,
    };
  },
};
</script>

<style></style>
