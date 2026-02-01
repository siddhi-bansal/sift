"use client";

import { useRef, useEffect, useState } from "react";

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function toYYYYMMDD(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function parseYYYYMMDD(s: string): Date | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return null;
  const d = new Date(s + "T12:00:00");
  return isNaN(d.getTime()) ? null : d;
}

type DatePickerProps = {
  id?: string;
  value: string;
  onChange: (value: string) => void;
  className?: string;
};

export default function DatePicker({ id, value, onChange, className = "" }: DatePickerProps) {
  const [open, setOpen] = useState(false);
  const [view, setView] = useState(() => {
    const d = parseYYYYMMDD(value);
    return d ? { year: d.getFullYear(), month: d.getMonth() } : { year: new Date().getFullYear(), month: new Date().getMonth() };
  });
  const containerRef = useRef<HTMLDivElement>(null);

  const valueDate = parseYYYYMMDD(value);
  const today = toYYYYMMDD(new Date());

  useEffect(() => {
    if (!valueDate) return;
    setView({ year: valueDate.getFullYear(), month: valueDate.getMonth() });
  }, [value]);

  useEffect(() => {
    if (!open) return;
    const handle = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, [open]);

  const firstOfMonth = new Date(view.year, view.month, 1);
  const lastOfMonth = new Date(view.year, view.month + 1, 0);
  const startPad = firstOfMonth.getDay();
  const daysInMonth = lastOfMonth.getDate();
  const prevMonth = new Date(view.year, view.month - 1);
  const nextMonth = new Date(view.year, view.month + 1);

  const days: (number | null)[] = [];
  for (let i = 0; i < startPad; i++) days.push(null);
  for (let d = 1; d <= daysInMonth; d++) days.push(d);

  const selectDay = (d: number) => {
    const yyyy = String(view.year);
    const mm = String(view.month + 1).padStart(2, "0");
    const dd = String(d).padStart(2, "0");
    onChange(`${yyyy}-${mm}-${dd}`);
    setOpen(false);
  };

  const setToday = () => {
    onChange(today);
    const d = new Date();
    setView({ year: d.getFullYear(), month: d.getMonth() });
    setOpen(false);
  };

  const clear = () => {
    onChange("");
    setOpen(false);
  };

  const displayLabel = value ? (valueDate ? valueDate.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : value) : "Pick a date";

  return (
    <div ref={containerRef} className={`date-picker ${className}`}>
      <button
        type="button"
        id={id}
        className="date-picker__trigger"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-label="Choose date"
      >
        <span className="date-picker__label">{displayLabel}</span>
        <span className="date-picker__chevron" aria-hidden>▼</span>
      </button>
      {open && (
        <div className="date-picker__dropdown" role="dialog" aria-modal="true" aria-label="Calendar">
          <div className="date-picker__header">
            <button
              type="button"
              className="date-picker__nav"
              onClick={() => setView((v) => ({ ...v, month: v.month - 1 }))}
              aria-label="Previous month"
            >
              ‹
            </button>
            <span className="date-picker__month-year">
              {MONTHS[view.month]} {view.year}
            </span>
            <button
              type="button"
              className="date-picker__nav"
              onClick={() => setView((v) => ({ ...v, month: v.month + 1 }))}
              aria-label="Next month"
            >
              ›
            </button>
          </div>
          <div className="date-picker__weekdays">
            {["S", "M", "T", "W", "T", "F", "S"].map((w, i) => (
              <span key={i} className="date-picker__weekday">{w}</span>
            ))}
          </div>
          <div className="date-picker__grid">
            {days.map((d, i) => {
              if (d === null) {
                return <span key={`pad-${i}`} className="date-picker__day date-picker__day--other" />;
              }
              const yyyy = String(view.year);
              const mm = String(view.month + 1).padStart(2, "0");
              const dd = String(d).padStart(2, "0");
              const cellValue = `${yyyy}-${mm}-${dd}`;
              const isSelected = value === cellValue;
              const isToday = today === cellValue;
              return (
                <button
                  key={`${view.year}-${view.month}-${d}`}
                  type="button"
                  className={`date-picker__day ${isSelected ? "date-picker__day--selected" : ""} ${isToday ? "date-picker__day--today" : ""}`}
                  onClick={() => selectDay(d)}
                  aria-label={`${MONTHS[view.month]} ${d}, ${view.year}`}
                  aria-pressed={isSelected}
                >
                  {d}
                </button>
              );
            })}
          </div>
          <div className="date-picker__footer">
            <button type="button" className="date-picker__action" onClick={clear}>
              Clear
            </button>
            <button type="button" className="date-picker__action" onClick={setToday}>
              Today
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
