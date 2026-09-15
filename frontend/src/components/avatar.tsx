import type { User } from "@/services";

export function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

export function Avatar({
  user,
  size = 28,
  title,
}: {
  user: Pick<User, "name" | "avatarColor"> | null;
  size?: number;
  title?: string;
}) {
  if (!user) {
    return (
      <span
        title={title ?? "Unassigned"}
        className="inline-flex items-center justify-center rounded-full border border-dashed border-border text-[10px] text-muted-foreground"
        style={{ width: size, height: size }}
      >
        ?
      </span>
    );
  }
  return (
    <span
      title={title ?? user.name}
      className="inline-flex shrink-0 items-center justify-center rounded-full font-medium text-primary-foreground"
      style={{
        width: size,
        height: size,
        backgroundColor: user.avatarColor,
        fontSize: Math.max(9, size * 0.38),
      }}
    >
      {initials(user.name)}
    </span>
  );
}
