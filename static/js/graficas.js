(() => {
  const SVG_NS = "http://www.w3.org/2000/svg";
  const PALETA = ["#0284c7", "#f59e0b", "#10b981", "#8b5cf6", "#ef4444", "#64748b", "#0f766e", "#be185d"];
  const formato = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 2 });

  function svgNode(name, attributes, text) {
    const node = document.createElementNS(SVG_NS, name);
    Object.entries(attributes || {}).forEach(([key, value]) => node.setAttribute(key, value));
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function colorDe(dataset, datasetIndex, pointIndex) {
    if (pointIndex === 0 && dataset.primer_color) return dataset.primer_color;
    const color = dataset.color || dataset.backgroundColor || PALETA[datasetIndex % PALETA.length];
    return Array.isArray(color) ? color[pointIndex] || PALETA[datasetIndex % PALETA.length] : color;
  }

  function dibujar(canvas, chart) {
    const labels = chart.labels || [];
    const datasets = chart.datasets || [];
    if (!labels.length || !datasets.length) return;

    const horizontal = !!chart.horizontal;
    const line = chart.tipo === "line";
    const width = 800;
    const height = horizontal ? 420 : 360;
    const margin = { top: 20, right: 24, bottom: 76, left: horizontal ? 190 : 70 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;
    const values = datasets.flatMap(dataset => dataset.data || [])
      .map(Number).filter(value => Number.isFinite(value) && value >= 0);
    const dataMax = Math.max(0, ...values);
    const maximum = Number(chart.ymax) > 0 ? Number(chart.ymax) : (dataMax > 0 ? dataMax * 1.1 : 1);
    const svg = svgNode("svg", {
      width: "100%",
      height: "100%",
      viewBox: `0 0 ${width} ${height}`,
      role: "img",
      "aria-label": canvas.getAttribute("aria-label") || chart.titulo || "Gráfica",
      preserveAspectRatio: "xMidYMid meet",
      class: "nexo-chart-svg"
    });
    const plot = svgNode("g", { "font-family": "system-ui, sans-serif", "font-size": 11 });
    svg.appendChild(plot);

    for (let tick = 0; tick <= 4; tick += 1) {
      const ratio = tick / 4;
      const value = maximum * ratio;
      const x = horizontal ? margin.left + plotWidth * ratio : margin.left;
      const y = horizontal ? margin.top : margin.top + plotHeight * (1 - ratio);
      plot.appendChild(svgNode("line", {
        x1: horizontal ? x : margin.left,
        y1: horizontal ? margin.top : y,
        x2: horizontal ? x : margin.left + plotWidth,
        y2: horizontal ? margin.top + plotHeight : y,
        stroke: "#dbe3ec",
        "stroke-width": 1
      }));
      plot.appendChild(svgNode("text", {
        x: horizontal ? x : margin.left - 10,
        y: horizontal ? margin.top + plotHeight + 18 : y + 4,
        "text-anchor": horizontal ? "middle" : "end",
        fill: "#64748b"
      }, formato.format(value)));
    }

    if (horizontal) {
      const groupHeight = plotHeight / labels.length;
      const barHeight = Math.min(20, groupHeight * 0.72 / datasets.length);
      labels.forEach((label, labelIndex) => {
        const center = margin.top + groupHeight * (labelIndex + 0.5);
        plot.appendChild(svgNode("text", {
          x: margin.left - 10,
          y: center + 4,
          "text-anchor": "end",
          fill: "#475569"
        }, label.length > 28 ? `${label.slice(0, 27)}…` : label));
        datasets.forEach((dataset, datasetIndex) => {
          const value = Math.max(0, Number(dataset.data[labelIndex]) || 0);
          const barWidth = plotWidth * value / maximum;
          const y = center + (datasetIndex - (datasets.length - 1) / 2) * barHeight - barHeight / 2;
          const rect = svgNode("rect", {
            x: margin.left,
            y,
            width: barWidth,
            height: Math.max(2, barHeight - 2),
            rx: 3,
            fill: colorDe(dataset, datasetIndex, labelIndex)
          });
          rect.appendChild(svgNode("title", {}, `${dataset.label}: ${formato.format(value)}`));
          plot.appendChild(rect);
        });
      });
      if (chart.ytitle) {
        plot.appendChild(svgNode("text", {
          x: margin.left + plotWidth / 2,
          y: height - 14,
          "text-anchor": "middle",
          fill: "#475569"
        }, chart.ytitle));
      }
    } else if (line) {
      const step = labels.length > 1 ? plotWidth / (labels.length - 1) : 0;
      datasets.forEach((dataset, datasetIndex) => {
        const points = (dataset.data || []).map((value, index) => {
          const numericValue = Number(value);
          return Number.isFinite(numericValue)
            ? [margin.left + step * index, margin.top + plotHeight * (1 - numericValue / maximum), numericValue]
            : null;
        });
        const path = points.filter(Boolean).map(([x, y], index) => `${index ? "L" : "M"}${x},${y}`).join(" ");
        if (path) {
          plot.appendChild(svgNode("path", {
            d: path,
            fill: "none",
            stroke: colorDe(dataset, datasetIndex, 0),
            "stroke-width": dataset.dash ? 2.5 : 2,
            "stroke-dasharray": dataset.dash ? "6 4" : ""
          }));
        }
        points.forEach((point, index) => {
          if (!point) return;
          const circle = svgNode("circle", {
            cx: point[0],
            cy: point[1],
            r: labels.length > 30 ? 0 : 3,
            fill: colorDe(dataset, datasetIndex, index)
          });
          circle.appendChild(svgNode("title", {}, `${dataset.label}: ${formato.format(point[2])}`));
          plot.appendChild(circle);
        });
      });
      labels.forEach((label, index) => {
        if (labels.length > 14 && index % Math.ceil(labels.length / 14) !== 0) return;
        const x = margin.left + step * index;
        plot.appendChild(svgNode("text", {
          x,
          y: margin.top + plotHeight + 20,
          "text-anchor": labels.length > 10 ? "end" : "middle",
          transform: labels.length > 10 ? `rotate(-35 ${x} ${margin.top + plotHeight + 20})` : "",
          fill: "#475569"
        }, label));
      });
      if (chart.xtitle) {
        plot.appendChild(svgNode("text", {
          x: margin.left + plotWidth / 2,
          y: height - 14,
          "text-anchor": "middle",
          fill: "#475569"
        }, chart.xtitle));
      }
    } else {
      const groupWidth = plotWidth / labels.length;
      const barWidth = Math.min(34, groupWidth * 0.8 / datasets.length);
      labels.forEach((label, labelIndex) => {
        const center = margin.left + groupWidth * (labelIndex + 0.5);
        datasets.forEach((dataset, datasetIndex) => {
          const value = Math.max(0, Number(dataset.data[labelIndex]) || 0);
          const barHeight = plotHeight * value / maximum;
          const x = center + (datasetIndex - (datasets.length - 1) / 2) * barWidth - barWidth / 2;
          const rect = svgNode("rect", {
            x,
            y: margin.top + plotHeight - barHeight,
            width: Math.max(2, barWidth - 2),
            height: barHeight,
            rx: 3,
            fill: colorDe(dataset, datasetIndex, labelIndex)
          });
          let tooltip = `${dataset.label}: ${formato.format(value)}`;
          if (chart.tooltip_pct) tooltip += ` (${formato.format(chart.tooltip_pct[labelIndex])} % de la selección)`;
          rect.appendChild(svgNode("title", {}, tooltip));
          plot.appendChild(rect);
        });
        const labelX = center;
        plot.appendChild(svgNode("text", {
          x: labelX,
          y: margin.top + plotHeight + 20,
          "text-anchor": labels.length > 10 ? "end" : "middle",
          transform: labels.length > 10 ? `rotate(-35 ${labelX} ${margin.top + plotHeight + 20})` : "",
          fill: "#475569"
        }, label.length > 24 ? `${label.slice(0, 23)}…` : label));
      });
      if (chart.xtitle) {
        plot.appendChild(svgNode("text", {
          x: margin.left + plotWidth / 2,
          y: height - 14,
          "text-anchor": "middle",
          fill: "#475569"
        }, chart.xtitle));
      }
    }

    if (chart.ytitle && !horizontal) {
      plot.appendChild(svgNode("text", {
        x: 16,
        y: margin.top + plotHeight / 2,
        "text-anchor": "middle",
        transform: `rotate(-90 16 ${margin.top + plotHeight / 2})`,
        fill: "#475569"
      }, chart.ytitle));
    }

    if (datasets.length > 1) {
      const legendY = height - 42;
      let legendX = margin.left;
      datasets.forEach((dataset, index) => {
        const label = dataset.label || "";
        const itemWidth = Math.min(210, 26 + label.length * 7);
        plot.appendChild(svgNode("line", {
          x1: legendX,
          y1: legendY - 4,
          x2: legendX + 16,
          y2: legendY - 4,
          stroke: colorDe(dataset, index, 0),
          "stroke-width": 3,
          "stroke-dasharray": dataset.dash ? "5 3" : ""
        }));
        plot.appendChild(svgNode("text", { x: legendX + 21, y: legendY, fill: "#475569" }, label));
        legendX += itemWidth;
      });
    }

    canvas.replaceWith(svg);
  }

  document.querySelectorAll(".nexo-chart-data").forEach(script => {
    const charts = JSON.parse(script.textContent);
    charts.forEach(chart => {
      const canvas = document.getElementById(chart.id);
      if (canvas) dibujar(canvas, chart);
    });
  });
})();
