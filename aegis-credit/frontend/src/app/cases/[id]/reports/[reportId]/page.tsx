import { redirect } from 'next/navigation';

export default function ReportDetailRedirect({ params }: { params: { id: string } }) {
  redirect(`/cases/${params.id}/reports`);
}
