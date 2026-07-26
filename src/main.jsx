import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./auth.css";

const rootElement = document.getElementById("auth-react-root");
if (rootElement) createRoot(rootElement).render(<StrictMode><App /></StrictMode>);
