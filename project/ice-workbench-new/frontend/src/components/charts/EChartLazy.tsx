/**
 * Lazy-loading wrapper for ECharts with tree-shaking.
 *
 * Uses echarts/core + only the chart types and components actually needed
 * (BarChart, LineChart, Tooltip, Grid). This reduces the echarts bundle from
 * ~1044KB to ~250KB. The component is still lazy-loaded via React.lazy so
 * the bundle is only fetched when a chart is actually rendered (admin pages).
 */
import { lazy, Suspense, memo } from "react";

// Re-export EChartsOption type for consumers
import type { ComposeOption } from "echarts/core";
import type { BarSeriesOption, LineSeriesOption } from "echarts/charts";
import type {
  TooltipComponentOption,
  GridComponentOption,
  LegendComponentOption,
} from "echarts/components";

export type EChartsOption = ComposeOption<
  | BarSeriesOption
  | LineSeriesOption
  | TooltipComponentOption
  | GridComponentOption
  | LegendComponentOption
>;

// The actual chart component (loaded lazily)
const EChartCore = lazy(() => import("./EChartCore"));

interface Props {
  option: EChartsOption;
  style?: React.CSSProperties;
  className?: string;
  /** Fallback content shown while echarts loads */
  fallback?: React.ReactNode;
}

function EChartLazyImpl({ option, style, className, fallback }: Props) {
  return (
    <Suspense
      fallback={
        fallback ?? (
          <div
            style={{
              ...style,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--text-muted)",
            }}
          >
            加载图表…
          </div>
        )
      }
    >
      <EChartCore option={option} style={style} className={className} />
    </Suspense>
  );
}

export const EChartLazy = memo(EChartLazyImpl);
