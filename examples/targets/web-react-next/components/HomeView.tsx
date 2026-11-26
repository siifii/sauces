import { useTranslations } from "next-intl";
import { Button } from "./Button";
import { Card } from "./Card";
import { TextField } from "./TextField";

export type HomeViewProps = { name: string; openOrders: number };

export function HomeView({ name, openOrders }: HomeViewProps) {
  const t = useTranslations("Home");
  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 p-6">
      <h1 className="text-3xl font-semibold">{t("title")}</h1>
      <p>{t("greeting", { name })}</p>
      <TextField id="home-search" type="search" label={t("searchLabel")} />
      <Card title={t("ordersTitle")} action={<Button>{t("viewOrders")}</Button>}>
        {t("ordersBody", { count: openOrders })}
      </Card>
    </main>
  );
}
