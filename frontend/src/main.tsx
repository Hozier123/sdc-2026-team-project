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
import "./styles/order-queue.css";
import "./styles/form-select.css";
import "./styles/motion.css";
import "./tailwind.css";
import "./styles/theme.css";
import "./styles/theme-transition.css";
import "./styles/connection.css";
import "./styles/review.css";
import "./styles/manual-recovery.css";
import "./styles/receipt.css";
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
