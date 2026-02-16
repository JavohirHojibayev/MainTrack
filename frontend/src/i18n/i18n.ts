import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

import en from "./locales/en/translation.json";
import ru from "./locales/ru/translation.json";
import uz from "./locales/uz/translation.json";

const saved = localStorage.getItem("minetrack_lang") || "en";

i18n
    .use(LanguageDetector)
    .use(initReactI18next)
    .init({
        resources: {
            en: { translation: en },
            ru: { translation: ru },
            uz: { translation: uz },
        },
        lng: saved,
        fallbackLng: "en",
        interpolation: { escapeValue: false },
        detection: { order: ["localStorage"], lookupLocalStorage: "minetrack_lang", caches: ["localStorage"] },
    });

export default i18n;
