import { Button } from "@/components/ui/button";
import { Panel } from "@/components/ui/panel";
import {
  KIND_LABEL,
  STATUS_LABEL,
  mainMetrics,
  type ModelStatus,
  type ModelVersion,
} from "@/lib/admin";

const STATUS_STYLE: Record<ModelStatus, string> = {
  active: "border-secondary text-secondary",
  trained: "border-primary/60 text-primary",
  retired: "border-outline/60 text-on-surface-variant",
};

type ModelsTableProps = {
  /** null, dokler se seznam nalaga. */
  models: ModelVersion[] | null;
  loadFailed?: boolean;
  /** ID verzije, katere aktivacija teče (vsi gumbi so takrat onemogočeni). */
  busyId: number | null;
  onActivate: (model: ModelVersion) => void;
};

/** Čist prikaz verzij modelov (brez prijave in klicev API-ja). */
export function ModelsTable({ models, loadFailed = false, busyId, onActivate }: ModelsTableProps) {
  return (
    <Panel title="Verzije" accent="secondary">
      {models === null && !loadFailed && (
        <p className="text-sm text-on-surface-variant">Nalagam ...</p>
      )}
      {models?.length === 0 && (
        <p className="text-sm text-on-surface-variant">Še ni naučenih modelov.</p>
      )}
      <ul className="flex flex-col gap-2">
        {models?.map((model) => (
          <li
            key={model.id}
            className="flex flex-col gap-2 rounded-sm border border-outline/50 bg-surface-container px-3 py-2 md:flex-row md:items-center md:justify-between"
          >
            <div className="flex flex-col gap-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-headline text-on-surface">
                  {KIND_LABEL[model.kind]} v{model.version}
                </span>
                <span
                  className={`rounded-sm border px-2 py-0.5 font-label text-[10px] tracking-wider uppercase ${STATUS_STYLE[model.status]}`}
                >
                  {STATUS_LABEL[model.status]}
                </span>
                <span className="font-label text-xs text-on-surface-variant">
                  patch {model.patch}
                </span>
              </div>
              <dl className="flex flex-wrap gap-x-4 gap-y-1 font-label text-xs text-on-surface-variant">
                {mainMetrics(model.metrics).map((metric) => (
                  <div key={metric.label} className="flex gap-1">
                    <dt>{metric.label}:</dt>
                    <dd className="text-on-surface">{metric.value}</dd>
                  </div>
                ))}
              </dl>
            </div>
            {model.status !== "active" && (
              <Button
                disabled={busyId !== null}
                onClick={() => onActivate(model)}
                aria-label={`Aktiviraj ${KIND_LABEL[model.kind]} v${model.version}`}
              >
                {busyId === model.id ? "Aktiviram ..." : "Aktiviraj"}
              </Button>
            )}
          </li>
        ))}
      </ul>
    </Panel>
  );
}
