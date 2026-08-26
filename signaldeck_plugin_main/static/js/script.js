function applyScriptProcessorResponse(stateContainer, data) {
  if (data.html !== undefined) {
    stateContainer.innerHTML = data.html;
  }

  if (data.stateChangeEvents !== undefined) {
    data.stateChangeEvents.forEach(element => {
      addStateChangeEvent(element["id"], element["actionhash"], element["get_params"]);
    });
  }

  if (data.js_functions !== undefined) {
    Object.entries(data.js_functions).forEach(([elementId, functionName]) => {
      const el = document.getElementById(elementId);
      const fn = window[functionName];
      if (el && typeof fn === "function") {
        fn(el);
      }
    });
  }
}

function initScriptSelect(el) {
  if (!el || el.dataset.scriptInitialized === "true") {
    return;
  }
  el.dataset.scriptInitialized = "true";

  el.addEventListener("change", function () {
    if (!el.value) {
      return;
    }

    const actionhash = el.dataset.actionhash;
    const stateContainer = el.closest(".state");
    if (!stateContainer) {
      return;
    }

    const stateParamsElement = document.getElementById("state_" + actionhash);
    const stateParams = stateParamsElement ? ($(stateParamsElement).data("params") || {}) : {};
    const payload = {
      actionhash,
      ...stateParams,
      selected_script: el.value,
      tab: el.dataset.tab || "run"
    };

    const fd = new FormData();
    fd.append("payload", JSON.stringify(payload));

    $.ajax({
      url: "/run",
      type: "POST",
      data: fd,
      processData: false,
      contentType: false,
      success: function (data) {
        applyScriptProcessorResponse(stateContainer, data);
      }
    });
  });
}
