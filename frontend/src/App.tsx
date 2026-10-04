import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { ApiError, normalizeSkin, papercraft, type ErrorCode } from "./api/client";
import { Alert } from "./components/Alert";
import { SegmentedControl } from "./components/SegmentedControl";
import { Stepper } from "./components/Stepper";
import { WarningList } from "./components/WarningList";
import type { RejectReason } from "./components/FileDrop";
import { saveBlob } from "./download";
import { useI18n, type Lang } from "./i18n";
import { initialState, reducer, STEPS } from "./state";
import { Download } from "./steps/Download";
import { Preview } from "./steps/Preview";
import { Processing } from "./steps/Processing";
import { Upload } from "./steps/Upload";

const PDF_NAME = "real2block-figure.pdf";
const PNG_NAME = "real2block-skin.png";

function isAbort(err: unknown): boolean {
  return err instanceof DOMException && err.name === "AbortError";
}

function useAbortable() {
  const current = useRef<AbortController | null>(null);
  useEffect(() => () => current.current?.abort(), []);
  return {
    next: () => {
      current.current?.abort();
      current.current = new AbortController();
      return current.current.signal;
    },
    abort: () => current.current?.abort(),
  };
}

function Header() {
  const { t, lang, setLang } = useI18n();
  return (
    <header className="flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 className="font-pixel text-lg">{t("app.title")}</h1>
        <p className="text-sm text-neutral-600">{t("app.tagline")}</p>
      </div>
      <SegmentedControl<Lang>
        label={t("lang.label")}
        value={lang}
        onChange={setLang}
        options={[
          { value: "ru", label: "RU" },
          { value: "en", label: "EN" },
        ]}
      />
    </header>
  );
}

function useSkinFlow() {
  const { lang } = useI18n();
  const [state, dispatch] = useReducer(reducer, initialState);
  const [pdfBusy, setPdfBusy] = useState(false);
  const request = useAbortable();

  const fail = useCallback((err: unknown) => {
    if (isAbort(err)) return;
    dispatch({ type: "failed", code: err instanceof ApiError ? err.code : "INTERNAL" });
  }, []);

  const importSkin = (file: File) => {
    dispatch({ type: "start" });
    normalizeSkin(file, request.next())
      .then((result) => {
        dispatch({ type: "imported", result });
      })
      .catch(fail);
  };

  const downloadPdf = () => {
    if (!state.skin) return;
    setPdfBusy(true);
    papercraft(state.skin, { model: state.model, lang, ...state.pdf }, request.next())
      .then(({ pdf, warnings }) => {
        dispatch({ type: "pdfReady", warnings });
        saveBlob(pdf, PDF_NAME);
      })
      .catch(fail)
      .finally(() => {
        setPdfBusy(false);
      });
  };

  const cancel = () => {
    request.abort();
    dispatch({ type: "cancelled" });
  };

  return { state, dispatch, pdfBusy, importSkin, downloadPdf, cancel };
}

type Flow = ReturnType<typeof useSkinFlow>;

function rejectCode(reason: RejectReason): ErrorCode {
  return reason === "type" ? "UNSUPPORTED_FORMAT" : "FILE_TOO_LARGE";
}

function StepView({ flow }: { flow: Flow }) {
  const { state, dispatch } = flow;
  switch (state.step) {
    case "upload":
      return (
        <Upload
          onSkin={flow.importSkin}
          onReject={(reason) => {
            dispatch({ type: "failed", code: rejectCode(reason) });
          }}
        />
      );
    case "processing":
      return <Processing onCancel={flow.cancel} />;
    case "preview":
      return state.skin ? (
        <Preview
          skin={state.skin}
          model={state.model}
          onModel={(model) => {
            dispatch({ type: "setModel", model });
          }}
          onNext={() => {
            dispatch({ type: "goto", step: "download" });
          }}
          onReset={() => {
            dispatch({ type: "reset" });
          }}
        />
      ) : null;
    case "download":
      return state.skin ? <DownloadStep flow={flow} skin={state.skin} /> : null;
  }
}

function DownloadStep({ flow, skin }: { flow: Flow; skin: Blob }) {
  return (
    <Download
      settings={flow.state.pdf}
      onSettings={(pdf) => {
        flow.dispatch({ type: "setPdf", pdf });
      }}
      busy={flow.pdfBusy}
      onPng={() => {
        saveBlob(skin, PNG_NAME);
      }}
      onPdf={flow.downloadPdf}
      onBack={() => {
        flow.dispatch({ type: "goto", step: "preview" });
      }}
    />
  );
}

export function App() {
  const { t } = useI18n();
  const flow = useSkinFlow();
  const { state } = flow;
  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 p-4 sm:p-8">
      <Header />
      <Stepper steps={STEPS.map((s) => t(`steps.${s}`))} current={STEPS.indexOf(state.step)} />
      {state.error && (
        <Alert tone="error" title={t("errors.title")}>
          {t(`errors.${state.error}`)}
        </Alert>
      )}
      <WarningList warnings={state.warnings} />
      <StepView flow={flow} />
    </main>
  );
}
