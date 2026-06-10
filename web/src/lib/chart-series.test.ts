import { describe, expect, it } from "vitest";
import {
  firstLastValid,
  normalizedNavSeries,
  segmentTrendLine,
} from "./chart-series";

describe("nav trend in visible window", () => {
  it("segmentTrendLine connects window endpoints only", () => {
    const closes = [100, 110, 120, 130, 140, 150, 160, 170, 180, 190];
    const nav = normalizedNavSeries(closes);
    const visStart = 6;
    const win = nav.slice(visStart);
    const epWin = firstLastValid(win);
    expect(epWin).not.toBeNull();
    const ep = {
      i0: epWin!.i0 + visStart,
      v0: epWin!.v0,
      i1: epWin!.i1 + visStart,
      v1: epWin!.v1,
    };
    const trend = segmentTrendLine(nav.length, ep);
    expect(trend[0]).toBeNull();
    expect(trend[visStart]).toBeCloseTo(ep.v0, 5);
    expect(trend[ep.i1]).toBeCloseTo(ep.v1, 5);
    expect(trend[ep.i0]! < trend[ep.i1]!).toBe(true);
  });

  it("score trend uses visible window endpoints like nav", () => {
    const scores = Array.from({ length: 500 }, (_, i) =>
      i < 50 ? null : 50 + i * 0.01
    );
    const visStart = 500 - 252;
    const win = scores.slice(visStart);
    const epWin = firstLastValid(win);
    expect(epWin).not.toBeNull();
    const ep = {
      i0: epWin!.i0 + visStart,
      v0: epWin!.v0,
      i1: epWin!.i1 + visStart,
      v1: epWin!.v1,
    };
    const trend = segmentTrendLine(scores.length, ep);
    expect(trend[ep.i0]).toBeCloseTo(ep.v0, 5);
    expect(trend[ep.i1]).toBeCloseTo(ep.v1, 5);
    expect(Math.abs((trend[ep.i1] ?? 0) - (trend[ep.i0] ?? 0))).toBeGreaterThan(
      0.5
    );
  });
});
