
"use client";

import { ISOControlDetail } from "@/features/iso27001/ISOControlDetail";
import { useParams } from "next/navigation";

export default function ISOControlDetailPage() {
  const params = useParams();
  const id = params?.id as string;

  if (!id) return <div>Invalid Control ID</div>;

  return (
    <ISOControlDetail controlId={decodeURIComponent(id)} />
  );
}
