import { setRequestLocale } from "next-intl/server";
import { use } from "react";
import { HomeView } from "@/components/HomeView";

export default function HomePage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = use(params);
  setRequestLocale(locale);
  return <HomeView name="Alex" openOrders={2} />;
}
