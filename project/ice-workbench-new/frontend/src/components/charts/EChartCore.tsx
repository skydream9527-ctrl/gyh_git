/**
 * ECharts core renderer — registers only needed chart types and components.
 *
 * This file is the dynamic import target for EChartLazy. It pulls in:
 * - BarChart + LineChart (the only series types used)
 * - Tooltip + Grid + Legend (the only interactive components used)
 * - SVGRenderer (smaller than Canvas, better for admin dashboards)
 *
 * Total bundle: ~250KB (vs ~1044KB with full echarts).
 */
import { useEffect, useRef } from "react";
import * as echarts from "echarts/core";
import { BarChart, LineChart } from "echarts/charts";
import {
  TooltipComponent,
  GridComponent,
  LegendComponent,
} from "echarts/components";
import { SVGRenderer } from "echarts/renderers";
import type { EChartsOption } from "./EChartLazy";

// Register only what we need (tree-shaking the rest)
echarts.use([
  BarChart,
  LineChart,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  SVGRenderer,
]);

interface Props {
  option: EChartsOption;
  style?: React.CSSProperties;
  className?: string;
}

export default function EChartCore({ option, style, className }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    if (!chartRef.current) {
      chartRef.current = echarts.init(containerRef.current, undefined, {
        renderer: "svg",
      });
    }

    chartRef.current.setOption(option, { notMerge: true, lazyUpdate: true });
  }, [option]);

  // Handle resize
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;

    const ro = new ResizeObserver(() => {
      chart.resize();
    });
    if (containerRef.current) {
      ro.observe(containerRef.current);
    }

    return () => {
      ro.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  return (
    <div
      ref={containerRef}
      style={{ width: "100%", height: 200, ...style }}
      className={className}
    />
  );
}
