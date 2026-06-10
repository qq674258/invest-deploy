/** K 线衍生序列：净值归一化、起点至终点直线（趋势弦） */

export type Endpoints = {
  i0: number;
  v0: number;
  i1: number;
  v1: number;
};

export function closesFromCandles(
  candles: number[][]
): (number | null)[] {
  return candles.map((c) => (c && c.length > 1 ? c[1] : null));
}

/** 净值走势：首个有效收盘价归一为 1.0 */
export function normalizedNavSeries(
  closes: (number | null)[]
): (number | null)[] {
  let base: number | null = null;
  for (const c of closes) {
    if (c != null && c > 0) {
      base = c;
      break;
    }
  }
  if (base == null || base <= 0) {
    return closes.map(() => null);
  }
  return closes.map((c) =>
    c != null && c > 0 ? c / base : null
  );
}

/** 首、末有效点（用于 markLine 坐标） */
export function firstLastValid(
  values: (number | null)[]
): Endpoints | null {
  let i0 = -1;
  let v0 = 0;
  let i1 = -1;
  let v1 = 0;

  for (let i = 0; i < values.length; i++) {
    const v = values[i];
    if (v == null || !Number.isFinite(v)) continue;
    if (i0 < 0) {
      i0 = i;
      v0 = v;
      i1 = i;
      v1 = v;
    } else {
      i1 = i;
      v1 = v;
    }
  }

  if (i0 < 0 || i1 < 0) return null;
  return { i0, v0, i1, v1 };
}

/**
 * 图表左端→右端的直线（y(0)=v0, y(n-1)=v1）。
 * v0/v1 取序列首末有效值，保证与净值/评分曲线起终点一致。
 */
export function chartSpanTrendLine(
  length: number,
  endpoints: Endpoints
): (number | null)[] {
  if (length < 1) return [];
  const { v0, v1 } = endpoints;
  if (length === 1) return [v0];
  return Array.from({ length }, (_, i) => {
    const t = i / (length - 1);
    return v0 + (v1 - v0) * t;
  });
}

/** 仅在 [i0, i1] 区间内的直线（用于评分等有前置 null 的序列） */
export function segmentTrendLine(
  length: number,
  endpoints: Endpoints
): (number | null)[] {
  const { i0, v0, i1, v1 } = endpoints;
  if (length < 1 || i0 < 0 || i1 < i0) return Array.from({ length }, () => null);
  if (i0 === i1) {
    return Array.from({ length }, (_, i) => (i === i0 ? v0 : null));
  }
  return Array.from({ length }, (_, i) => {
    if (i < i0 || i > i1) return null;
    const t = (i - i0) / (i1 - i0);
    return v0 + (v1 - v0) * t;
  });
}

/** @deprecated 使用 chartSpanTrendLine + firstLastValid */
export function startToEndTrendLine(
  values: (number | null)[]
): (number | null)[] {
  const ep = firstLastValid(values);
  if (!ep) return values.map(() => null);
  return chartSpanTrendLine(values.length, ep);
}
