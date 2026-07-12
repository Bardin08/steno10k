import { useMemo, useState } from "react";
import { NavLink } from "react-router";
import {
  CaretDown,
  CaretRight,
  FolderSimple,
  Plus,
} from "@phosphor-icons/react";
import { Button, EmptyState, Input, Skeleton } from "../components";
import { toast } from "../components";
import type { ProjectDTO, SetDTO } from "../api/types";
import { useCreateProject, useCreateSet, useProjects } from "../api/hooks";
import { ApiError } from "../api/client";
import { CreateDialog } from "./CreateDialog";

const COLLAPSED_KEY = "steno10k.sidebar.collapsed";

function reportError(e: unknown) {
  toast.error(e instanceof ApiError ? e.message : "Something went wrong");
}

function readCollapsed(): Set<string> {
  try {
    const raw = localStorage.getItem(COLLAPSED_KEY);
    const arr = raw ? (JSON.parse(raw) as unknown) : [];
    return new Set(Array.isArray(arr) ? (arr as string[]) : []);
  } catch {
    return new Set();
  }
}

function writeCollapsed(collapsed: Set<string>) {
  localStorage.setItem(COLLAPSED_KEY, JSON.stringify([...collapsed]));
}

interface FilteredProject {
  project: ProjectDTO;
  sets: SetDTO[];
  forceExpand: boolean;
}

function filterProjects(
  projects: ProjectDTO[] | undefined,
  query: string,
): FilteredProject[] {
  const q = query.trim().toLowerCase();
  if (!projects) return [];
  if (!q) {
    return projects.map((p) => ({
      project: p,
      sets: p.sets,
      forceExpand: false,
    }));
  }
  const result: FilteredProject[] = [];
  for (const p of projects) {
    const titleMatch = p.title.toLowerCase().includes(q);
    const matchingSets = p.sets.filter((s) =>
      s.title.toLowerCase().includes(q),
    );
    if (titleMatch) {
      result.push({ project: p, sets: p.sets, forceExpand: true });
    } else if (matchingSets.length > 0) {
      result.push({ project: p, sets: matchingSets, forceExpand: true });
    }
  }
  return result;
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
  const [query, setQuery] = useState("");
  const [collapsed, setCollapsed] = useState<Set<string>>(() =>
    readCollapsed(),
  );

  const filtered = useMemo(
    () => filterProjects(projects, query),
    [projects, query],
  );

  function toggleCollapsed(slug: string) {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(slug)) next.delete(slug);
      else next.add(slug);
      writeCollapsed(next);
      return next;
    });
  }

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
        withIconPicker
        onSubmit={(title, icon) =>
          createProject.mutate(
            { title, icon },
            {
              onSuccess: () => setProjectOpen(false),
              onError: reportError,
            },
          )
        }
      />

      {projects && projects.length === 0 && (
        <EmptyState
          title="No projects yet"
          description="Create a project to begin."
          icon={<FolderSimple size={24} weight="duotone" />}
        />
      )}

      {projects && projects.length > 0 && (
        <Input
          value={query}
          placeholder="Filter projects & sets…"
          aria-label="Filter projects and sets"
          onChange={(e) => setQuery(e.target.value)}
          className="text-[13px]"
        />
      )}

      <ul className="flex flex-col gap-3">
        {filtered.map(({ project: p, sets, forceExpand }) => {
          const isCollapsed = collapsed.has(p.slug) && !forceExpand;
          return (
            <li key={p.id}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    aria-label={
                      isCollapsed ? `expand ${p.title}` : `collapse ${p.title}`
                    }
                    onClick={() => toggleCollapsed(p.slug)}
                    className="grid h-5 w-5 place-items-center text-ink-faint hover:text-ink"
                  >
                    {isCollapsed ? (
                      <CaretRight size={12} />
                    ) : (
                      <CaretDown size={12} />
                    )}
                  </button>
                  <span className="text-sm font-medium text-ink">
                    {p.title}
                  </span>
                </div>
                <NewSet
                  project={p.slug}
                  existingNames={p.sets.map((s) => s.title)}
                />
              </div>
              {!isCollapsed && (
                <ul className="mt-1 flex flex-col">
                  {sets.map((s) => (
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
              )}
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
