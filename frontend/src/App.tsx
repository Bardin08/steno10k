import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router";
import { Toaster } from "./components";
import { makeQueryClient } from "./app/queryClient";
import { router } from "./app/router";
import { ThemeProvider } from "./theme/ThemeProvider";

const queryClient = makeQueryClient();

export default function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
        <Toaster />
      </QueryClientProvider>
    </ThemeProvider>
  );
}
