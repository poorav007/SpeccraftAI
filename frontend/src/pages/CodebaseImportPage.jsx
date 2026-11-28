import BackendWakeSkeleton from "../components/import/BackendWakeSkeleton.jsx";
import ProjectUploader from "../components/import/ProjectUploader.jsx";

export default function CodebaseImportPage({
  endpoints = [],
  backendStatus,
  wakeElapsedSeconds = 0,
  wakeBudgetSeconds = 50,
  onBackendConfirmedOnline,
  onParseSuccess,
}) {
  const isWaking = Boolean(backendStatus?.waking && !backendStatus?.checked);
  const controlledBackendOnline = backendStatus
    ? backendStatus.checked
      ? backendStatus.online
      : backendStatus.waking
        ? "waking"
        : null
    : undefined;

  return (
    <div className="row justify-content-center">
      <div className="col-12 col-md-10 col-lg-8">
        {isWaking ? (
          <BackendWakeSkeleton
            elapsedSeconds={wakeElapsedSeconds}
            maxWaitSeconds={wakeBudgetSeconds}
          />
        ) : (
          <ProjectUploader
            initialEndpoints={endpoints}
            backendOnline={controlledBackendOnline}
            onBackendConfirmedOnline={onBackendConfirmedOnline}
            onParseSuccess={onParseSuccess}
          />
        )}
      </div>
    </div>
  );
}

