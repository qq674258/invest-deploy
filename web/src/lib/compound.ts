export type CompoundFrequency = "DAILY" | "WEEKLY" | "BIWEEKLY" | "MONTHLY";

/** 固定展示的多期限收益（与表单「投资时长」无关） */
export const COMPOUND_HORIZON_YEARS = [5, 10, 15, 20, 30, 40, 50] as const;

export type CompoundHorizonYear = (typeof COMPOUND_HORIZON_YEARS)[number];

export const FREQUENCY_OPTIONS: { id: CompoundFrequency; label: string }[] = [
  { id: "DAILY", label: "每日" },
  { id: "WEEKLY", label: "每周" },
  { id: "BIWEEKLY", label: "双周" },
  { id: "MONTHLY", label: "每月" },
];

const PERIODS_PER_YEAR: Record<CompoundFrequency, number> = {
  DAILY: 252,
  WEEKLY: 52,
  BIWEEKLY: 26,
  MONTHLY: 12,
};

export type CompoundInput = {
  amount: number;
  annualReturnPct: number;
  years: number;
  frequency: CompoundFrequency;
};

export type CompoundResult = {
  periods: number;
  totalInvested: number;
  finalValue: number;
  profit: number;
  profitPct: number;
};

/** 期末定投复利：每期期末投入 P，年化收益率按频率折算 */
export function calcCompoundDca(input: CompoundInput): CompoundResult {
  const periodsPerYear = PERIODS_PER_YEAR[input.frequency];
  const n = Math.max(0, Math.floor(input.years * periodsPerYear));
  const invested = input.amount * n;

  if (n === 0) {
    return { periods: 0, totalInvested: 0, finalValue: 0, profit: 0, profitPct: 0 };
  }

  const i = input.annualReturnPct / 100 / periodsPerYear;
  let finalValue: number;
  if (Math.abs(i) < 1e-12) {
    finalValue = invested;
  } else {
    finalValue = input.amount * ((Math.pow(1 + i, n) - 1) / i);
  }

  const profit = finalValue - invested;
  const profitPct = invested > 0 ? (profit / invested) * 100 : 0;

  return {
    periods: n,
    totalInvested: invested,
    finalValue,
    profit,
    profitPct,
  };
}

export function calcAllHorizons(
  amount: number,
  annualReturnPct: number,
  frequency: CompoundFrequency
) {
  return COMPOUND_HORIZON_YEARS.map((y) => ({
    years: y,
    ...calcCompoundDca({ amount, annualReturnPct, years: y, frequency }),
  }));
}
