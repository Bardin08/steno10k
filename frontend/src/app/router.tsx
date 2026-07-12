import { createBrowserRouter } from "react-router";
import { AppLayout } from "./AppLayout";
import { Library } from "../screens/Library";
import { SetDetail } from "../screens/SetDetail";
import { QueueScreen } from "../screens/QueueScreen";
import { ConfigScreen } from "../screens/ConfigScreen";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <Library /> },
      { path: "p/:project/s/:set", element: <SetDetail /> },
      { path: "queue", element: <QueueScreen /> },
      { path: "config", element: <ConfigScreen /> },
    ],
  },
]);
