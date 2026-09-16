export const formatLabel = (
  template: string,
  values: Record<string, string | number>,
): string =>
  Object.entries(values).reduce(
    (text, [key, value]) => text.split(`{${key}}`).join(String(value)),
    template,
  );
