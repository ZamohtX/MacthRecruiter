import { useId, useState } from "react";
import type { ReactNode } from "react";

export interface LegendItem {
  label: string;
  /** Papel CSS da série, ex.: "var(--series-1)". Nunca hex solto. */
  color: string;
}

interface ChartFrameProps {
  title: string;
  subtitle?: string;
  /** Obrigatório a partir de 2 séries — identidade nunca fica só na cor. */
  legend?: LegendItem[];
  /** Gêmeo em tabela do gráfico. Todo gráfico tem o seu: o tooltip enriquece,
   *  nunca é o único caminho para o valor. */
  table: ReactNode;
  children: ReactNode;
}

export function ChartFrame({ title, subtitle, legend, table, children }: ChartFrameProps) {
  const [showTable, setShowTable] = useState(false);
  const tableId = useId();

  return (
    <section
      className="rounded-xl p-5"
      style={{ background: "var(--surface-1)", border: "1px solid var(--hairline)" }}
    >
      <header className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
            {title}
          </h3>
          {subtitle && (
            <p className="mt-1 text-xs" style={{ color: "var(--text-secondary)" }}>
              {subtitle}
            </p>
          )}
        </div>

        <div className="flex items-center gap-4">
          {legend && legend.length > 0 && (
            <ul className="flex flex-wrap items-center gap-3">
              {legend.map((item) => (
                <li key={item.label} className="flex items-center gap-1.5">
                  {/* A marca colorida ao lado carrega a identidade; o texto fica
                      em tinta, nunca na cor da série. */}
                  <span
                    aria-hidden
                    className="inline-block h-2.5 w-2.5 rounded-sm"
                    style={{ background: item.color }}
                  />
                  <span className="text-xs" style={{ color: "var(--text-secondary)" }}>
                    {item.label}
                  </span>
                </li>
              ))}
            </ul>
          )}

          <button
            type="button"
            onClick={() => setShowTable((value) => !value)}
            aria-expanded={showTable}
            aria-controls={tableId}
            className="rounded-md px-2 py-1 text-xs transition-colors hover:bg-black/5 dark:hover:bg-white/10"
            style={{ color: "var(--text-secondary)", border: "1px solid var(--hairline)" }}
          >
            {showTable ? "Ver gráfico" : "Ver tabela"}
          </button>
        </div>
      </header>

      {showTable ? (
        <div id={tableId} className="overflow-x-auto">
          {table}
        </div>
      ) : (
        children
      )}
    </section>
  );
}

/** Tabela padrão dos gráficos — mesma tipografia e alinhamento em todos. */
export function DataTable({ headers, rows }: { headers: string[]; rows: (string | number)[][] }) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr style={{ borderBottom: "1px solid var(--baseline)" }}>
          {headers.map((header, index) => (
            <th
              key={header}
              scope="col"
              className={`py-2 text-xs font-medium ${index === 0 ? "text-left" : "text-right"}`}
              style={{ color: "var(--text-muted)" }}
            >
              {header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={String(row[0])} style={{ borderBottom: "1px solid var(--gridline)" }}>
            {row.map((cell, index) => (
              <td
                key={index}
                className={`py-2 ${index === 0 ? "text-left" : "tabular text-right"}`}
                style={{ color: index === 0 ? "var(--text-primary)" : "var(--text-secondary)" }}
              >
                {cell}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
