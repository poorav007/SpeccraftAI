import ProjectUploader from "../components/import/ProjectUploader.jsx";

export default function CodebaseImportPage({ endpoints = [], onParseSuccess }) {
  return (
    <div className="row justify-content-center">
      <div className="col-12 col-md-10 col-lg-8">
        <ProjectUploader initialEndpoints={endpoints} onParseSuccess={onParseSuccess} />
      </div>
    </div>
  );
}

