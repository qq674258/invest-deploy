"use client";

import ReactEChartsCore from "echarts-for-react/lib/core";
import echarts from "@/components/charts/register-echarts";

type Props = React.ComponentProps<typeof ReactEChartsCore>;

export default function EChartsBundle(props: Props) {
  const { opts, lazyUpdate, notMerge, ...rest } = props;
  return (
    <ReactEChartsCore
      echarts={echarts}
      opts={{ renderer: "canvas", ...opts }}
      lazyUpdate={lazyUpdate ?? true}
      notMerge={notMerge ?? true}
      {...rest}
    />
  );
}
