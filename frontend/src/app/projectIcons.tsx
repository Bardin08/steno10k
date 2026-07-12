import {
  FolderSimple,
  Notebook,
  Microphone,
  Waveform,
  GraduationCap,
  Briefcase,
  Scales,
  Flask,
  Code,
  Book,
  Chat,
  Calendar,
  Star,
  Bookmark,
  Stack,
  Sparkle,
  type Icon,
} from "@phosphor-icons/react";

const MAP: Record<string, Icon> = {
  folder: FolderSimple,
  notebook: Notebook,
  microphone: Microphone,
  waveform: Waveform,
  "graduation-cap": GraduationCap,
  briefcase: Briefcase,
  scales: Scales,
  flask: Flask,
  code: Code,
  book: Book,
  chat: Chat,
  calendar: Calendar,
  star: Star,
  bookmark: Bookmark,
  stack: Stack,
  sparkle: Sparkle,
};

export const PROJECT_ICON_KEYS = Object.keys(MAP);
export const DEFAULT_PROJECT_ICON = "folder";

export function ProjectIcon({
  icon,
  size = 15,
}: {
  icon: string | null;
  size?: number;
}) {
  const Cmp = MAP[icon ?? DEFAULT_PROJECT_ICON] ?? MAP[DEFAULT_PROJECT_ICON];
  return <Cmp size={size} />;
}
