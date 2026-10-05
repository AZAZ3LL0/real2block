import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { ApiError, isAbort, normalizeSkin, papercraft, type ErrorCode } from "./api/client";
import { Alert } from "./components/Alert";
import { Stepper } from "./components/Stepper";
import { WarningList } from "./components/WarningList";
import type { RejectReason } from "./components/FileDrop";
import { saveBlob } from "./download";
import { useI18n } from "./i18n";
import { Layout } from "./Layout";
import { initialState, reducer, STEPS, type Step } from "./state";
import { Download } from "./steps/Download";
import { Preview } from "./steps/Preview";
import { Processing } from "./steps/Processing";
import { Upload } from "./steps/Upload";
import { useDebouncedSkin } from "./useDebouncedSkin";

const PDF_NAME = "real2block-figure.pdf";
const PNG_NAME = "real2block-skin.png";

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

function useSkinFlow() {
  const { lang } = useI18n();
  const [state, dispatch] = useReducer(reducer, initialState);
  const [pdfBusy, setPdfBusy] = useState(false);
  const request = useAbortable();
  const pdfLang = state.pdfLang ?? lang;

  const fail = useCallback((err: unknown) => {
    if (isAbort(err)) return;
    dispatch({ type: "failed", code: err instanceof ApiError ? err.code : "INTERNAL" });
  }, []);

  useDebouncedSkin(state.spec, {
    onSkin: (skin) => {
      dispatch({ type: "styled", skin });
    },
    onError: fail,
  });

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
    papercraft(state.skin, { model: state.model, lang: pdfLang, ...state.pdf }, request.next())
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

  return { state, dispatch, pdfBusy, pdfLang, importSkin, downloadPdf, cancel };
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
          spec={state.spec}
          onModel={(model) => {
            dispatch({ type: "setModel", model });
          }}
          onSpec={(spec) => {
            dispatch({ type: "setSpec", spec });
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
      pdfLang={flow.pdfLang}
      onPdfLang={(lang) => {
        flow.dispatch({ type: "setPdfLang", lang });
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

/** Moves focus to the heading of a newly shown step, so keyboard and screen reader users follow along. */
function useStepFocus(step: Step) {
  const heading = useRef<HTMLHeadingElement>(null);
  const first = useRef(true);
  useEffect(() => {
    // The first step is where the page starts; stealing focus there would skip the header.
    if (first.current) {
      first.current = false;
      return;
    }
    heading.current?.focus();
  }, [step]);
  return heading;
}

export function App() {
  const { t } = useI18n();
  const flow = useSkinFlow();
  const { state } = flow;
  const heading = useStepFocus(state.step);
  return (
    <Layout>
      <Stepper
        label={t("steps.label")}
        steps={STEPS.map((s) => t(`steps.${s}`))}
        current={STEPS.indexOf(state.step)}
      />
      <h2 ref={heading} tabIndex={-1} className="sr-only">
        {t(`steps.${state.step}`)}
      </h2>
      {state.error && (
        <Alert tone="error" title={t("errors.title")}>
          {t(`errors.${state.error}`)}
        </Alert>
      )}
      <WarningList warnings={state.warnings} />
      <StepView flow={flow} />
    </Layout>
  );
}
