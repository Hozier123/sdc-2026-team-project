import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles/tokens.css";
import "./styles.css";
import "./business-ui.css";
import "./styles/typography.css";
import "./styles/workflow.css";
import "./styles/header.css";
import "./styles/overview.css";
import "./styles/form-select.css";
import "./tailwind.css";
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
