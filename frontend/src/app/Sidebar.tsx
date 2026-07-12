import { useState } from "react";
import { NavLink } from "react-router";
import { FolderSimple, Plus } from "@phosphor-icons/react";
import { Button, EmptyState, Skeleton } from "../components";
import { toast } from "../components";
import { useCreateProject, useCreateSet, useProjects } from "../api/hooks";
import { ApiError } from "../api/client";
import { CreateDialog } from "./CreateDialog";

function reportError(e: unknown) {
  toast.error(e instanceof ApiError ? e.message : "Something went wrong");
}

function NewSet({
  project,
  existingNames,
}: {
  project: string;
  existingNames: string[];
}) {
  const create = useCreateSet(project);
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        className="flex items-center gap-1.5 px-2 py-1 text-[11px] text-ink-faint hover:text-ink"
        onClick={() => setOpen(true)}
      >
        <Plus size={12} /> set
      </button>
      <CreateDialog
        open={open}
        onOpenChange={setOpen}
        title="New set"
        label="Set title"
        submitLabel="Create set"
        pending={create.isPending}
        existingNames={existingNames}
        onSubmit={(title) =>
          create.mutate(title, {
            onSuccess: () => setOpen(false),
            onError: reportError,
          })
        }
      />
    </>
  );
}

export function Sidebar() {
  const { data: projects, isLoading } = useProjects();
  const createProject = useCreateProject();
  const [projectOpen, setProjectOpen] = useState(false);

  if (isLoading) {
    return (
      <div className="flex flex-col gap-2 p-4">
        <Skeleton className="h-6 w-full" />
        <Skeleton className="h-6 w-full" />
      </div>
    );
  }

  return (
    <nav className="flex h-full flex-col gap-4 p-4">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-faint">
          Library
        </span>
        <Button
          variant="ghost"
          className="px-2 py-1 text-[11px]"
          disabled={createProject.isPending}
          onClick={() => setProjectOpen(true)}
        >
          <Plus size={12} /> project
        </Button>
      </div>

      <CreateDialog
        open={projectOpen}
        onOpenChange={setProjectOpen}
        title="New project"
        label="Project title"
        submitLabel="Create project"
        pending={createProject.isPending}
        existingNames={(projects ?? []).map((p) => p.title)}
        onSubmit={(title) =>
          createProject.mutate(title, {
            onSuccess: () => setProjectOpen(false),
            onError: reportError,
          })
        }
      />

      {projects && projects.length === 0 && (
        <EmptyState
          title="No projects yet"
          description="Create a project to begin."
          icon={<FolderSimple size={24} weight="duotone" />}
        />
      )}

      <ul className="flex flex-col gap-3">
        {projects?.map((p) => (
          <li key={p.id}>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-ink">{p.title}</span>
              <NewSet
                project={p.slug}
                existingNames={p.sets.map((s) => s.title)}
              />
            </div>
            <ul className="mt-1 flex flex-col">
              {p.sets.map((s) => (
                <li key={s.id}>
                  <NavLink
                    to={`/p/${p.slug}/s/${s.slug}`}
                    className={({ isActive }) =>
                      `block rounded-sm px-2 py-1 text-[13px] ${isActive ? "bg-ink text-paper" : "text-ink-soft hover:text-ink"}`
                    }
                  >
                    {s.title}
                  </NavLink>
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </nav>
  );
}
