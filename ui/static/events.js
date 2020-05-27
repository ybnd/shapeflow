export let events = {
  seek: {
    get(analyzer_id) {
      return `seek-sync-${analyzer_id}`;
    },
    reset(analyzer_id) {
      return `seek-reset-${analyzer_id}`;
    },
    set(analyzer_id) {
      return `seek-go-${analyzer_id}`;
    },
    step_fw(analyzer_id) {
      return `seek-forward-${analyzer_id}`;
    },
    step_bw(analyzer_id) {
      return `seek-backward-${analyzer_id}`;
    }
  },
  sidebar: {
    status(analyzer_id) {
      return `sidebar-status-${analyzer_id}`;
    },
    remove(analyzer_id) {
      return `sidebar-remove-${analyzer_id}`;
    },
    cancel(analyzer_id) {
      return `sidebar-cancel-${analyzer_id}`;
    },
    open(analyzer_id) {
      return `sidebar-open-${analyzer_id}`;
    },
    highlight(link_id) {
      return `sidebar-highlight-${link_id}`;
    },
    unhighlight(link_id) {
      return `sidebar-unhighlight-${link_id}`;
    }
  },
  data: {
    update(analyzer_id) {
      return `data-update-${analyzer_id}`;
    }
  }
};
