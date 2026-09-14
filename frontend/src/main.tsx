import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";
import { App } from "./App";

class BootErrorBoundary extends React.Component<{ children: React.ReactNode }, { error: Error | null }> {
  state: { error: Error | null } = { error: null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <pre style={{ padding: 16, color: "#b00020", whiteSpace: "pre-wrap", fontFamily: "sans-serif" }}>
          {this.state.error.stack || this.state.error.message}
        </pre>
      );
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <BootErrorBoundary>
    <React.StrictMode>
      <MantineProvider defaultColorScheme="light" forceColorScheme="light">
        <Notifications position="top-right" />
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </MantineProvider>
    </React.StrictMode>
  </BootErrorBoundary>,
);
