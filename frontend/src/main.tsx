import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { createRoot } from "react-dom/client";
import { Navigate, Route, BrowserRouter, Routes } from "react-router-dom";

import { AppShell } from "@/components/AppShell";
import { RevisionPage } from "@/pages/RevisionPage";
import { ScenarioPage } from "@/pages/ScenarioPage";
import { ScenariosPage } from "@/pages/ScenariosPage";

import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppShell>
          <Routes>
            <Route path="/app/" element={<ScenariosPage />} />
            <Route path="/app/scenarios/:slug" element={<ScenarioPage />} />
            <Route path="/app/revisions/:id" element={<RevisionPage />} />
            <Route path="*" element={<Navigate to="/app/" replace />} />
          </Routes>
        </AppShell>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
