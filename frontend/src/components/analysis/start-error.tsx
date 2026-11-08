import Link from "next/link";

import { FormMessage } from "@/components/ui/field";

type Props = { error: { message: string; limited: boolean } | null };

/** Napaka ob zagonu analize; pri dnevni omejitvi za goste doda povabilo k registraciji. */
export function StartError({ error }: Props) {
  if (!error) return null;
  return (
    <FormMessage tone="error">
      {error.message}
      {error.limited && (
        <>
          {" "}
          <Link href="/registracija" className="font-bold underline underline-offset-2">
            Ustvari račun
          </Link>
        </>
      )}
    </FormMessage>
  );
}
