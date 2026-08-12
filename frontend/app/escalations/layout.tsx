import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Escalation Dashboard | Local Commerce Assistant",
  description:
    "Human-in-the-loop escalation ticket management for the Local Commerce Voice Agent. View, triage, and resolve support requests raised by the AI agent.",
};

export default function EscalationsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
