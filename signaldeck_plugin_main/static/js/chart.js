(() => {
    function getChartConfigScatter(ctx, xVals, yVals, unit) {
        xStepSize = 1000 * 60 * 60 //for intraday, 1 hour
        if (ctx.dataset["agg"] == "day") {
            xStepSize = 1000 * 60 * 60 * 24 * 5 //5 days
        }
        data = [];
        for (i = 0; i < xVals.length; i++) {
            data.push({ x: xVals[i], y: yVals[i] })
        }
        const yScalePart =
            ctx.dataset["ymin"] != "" && ctx.dataset["ymax"] != ""
                ? { y: { min: Math.floor(ctx.dataset["ymin"]), max: Math.floor(ctx.dataset["ymax"]) } }
                : {};

        return {
            type: 'scatter',
            data: {
                datasets: [
                    {
                        label: ctx.dataset["label"],
                        data: data,
                        showLine: true,
                        fill: false,
                        //borderColor: 'rgba(0, 200, 0, 1)'
                    }
                ]
            },
            options: {
                aspectRatio: 1.25,
                tooltips: {
                    mode: 'index',
                    intersect: false,
                },
                hover: {
                    mode: 'nearest',
                    intersect: true
                },
                scales: {
                    x: {
                        ticks: {
                            callback: function (val, index) {
                                val = new Date(val);
                                if (ctx.dataset["agg"] == "") { return val.toLocaleTimeString(); }
                                if (ctx.dataset["agg"] == "day") { return val.toLocaleDateString(); }
                                return val.toString();
                            },
                            //color: "red",
                            stepSize: xStepSize
                        }
                    },
                    ...yScalePart
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                dateLong = context.parsed.x
                                date = new Date(dateLong);
                                dateRes = date.toString();
                                if (ctx.dataset["agg"] == "") { dateRes = date.toLocaleTimeString(); }
                                if (ctx.dataset["agg"] == "day") { dateRes = date.toLocaleDateString(); }
                                yVal = context.parsed.y
                                if (Math.round(yVal) != yVal) {
                                    yVal = Number(yVal).toFixed(2);
                                }
                                return dateRes + ": " + yVal + " " + unit
                            }
                        }
                    }
                }
            }
        };
    }


    function getChartConfigBar(ctx, xVals, yVals, unit) {
        var step = 1
        if (xVals.length > 10) {
            step = Math.round(xVals.length / 10)  //approx. 10 labels
        }
        data = {
            labels: xVals,
            datasets: [
                {
                    label: ctx.dataset["label"],
                    data: yVals
                }
            ]
        }
        return {
            type: 'bar',
            data: data,
            options: {
                aspectRatio: 1.25,
                scales: {
                    x: {
                        ticks: {
                            callback: function (val, index) {
                                return val % step == 0 ? new Date(parseInt(this.getLabelForValue(val))).toLocaleDateString() : "";
                            }
                        }
                    },
                    y: {
                        beginAtZero: true
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            title: function (context) {
                                data = context[0];
                                return new Date(parseInt(data.label)).toLocaleDateString();
                            },
                            label: function (context) {
                                return parseFloat(context.parsed.y).toFixed(1) + " " + unit;
                            }
                        }
                    }
                }
            }
        };
    }

    function initChart(ctx) {
        xVals = JSON.parse(ctx.dataset["xvals"])
        yVals = JSON.parse(ctx.dataset["yvals"])
        unit = ctx.dataset["unit"]

        var config = undefined;
        if (ctx.dataset["type"] == "scatter") {
            config = getChartConfigScatter(ctx, xVals, yVals, unit);
        }
        if (ctx.dataset["type"] == "bar") {
            config = getChartConfigBar(ctx, xVals, yVals, unit);
        }
        if (config == undefined) {
            console.log("Invalid chart type given.");
            return;
        }
        new Chart(ctx, config);
    }

    // --- DOM Ready ---
    document.addEventListener("DOMContentLoaded", () => {
        if (!window.jQuery) return;

        $(".state-chart").each(function (index, record) {
            el = record
            initChart(el);
        })
    });

    // Global export: für dynamische Initialisierung nach AJAX-HTML-Replace
    window.initChart = initChart;
})();