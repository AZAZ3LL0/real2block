import { describe, expect, it } from "vitest";
import { detectLang } from ".";
import en from "./en.json";
import ru from "./ru.json";

describe("i18n", () => {
  it("has the same keys in every language", () => {
    expect(Object.keys(en).sort()).toEqual(Object.keys(ru).sort());
  });

  it("picks the language from navigator.language", () => {
    expect(detectLang("en-GB")).toBe("en");
    expect(detectLang("ru-RU")).toBe("ru");
    expect(detectLang("de-DE")).toBe("ru");
    expect(detectLang(undefined)).toBe("ru");
  });
});
