import { heroui } from "@heroui/react";

export default heroui({
  defaultTheme: "dark",
  themes: {
    dark: {
      colors: {
        background: "#0A0B0F",
        foreground: "#F0F0F5",
        primary: { DEFAULT: "#7B6EF6", foreground: "#FFFFFF" },
        secondary: { DEFAULT: "#22232F", foreground: "#B8B9C8" },
        success: { DEFAULT: "#4ADE80", foreground: "#0A0B0F" },
        warning: { DEFAULT: "#F59E0B", foreground: "#0A0B0F" },
        danger: { DEFAULT: "#F87171", foreground: "#FFFFFF" },
        default: { DEFAULT: "#22232F", foreground: "#B8B9C8" },
      },
      layout: {
        radius: { small: "6px", medium: "10px", large: "14px" },
        borderWidth: { small: "1px", medium: "1px", large: "1px" },
      },
    },
    light: {
      colors: {
        background: "#F7F4EF",
        foreground: "#1F2937",
        primary: { DEFAULT: "#B45309", foreground: "#FFFFFF" },
        secondary: { DEFAULT: "#F6EFE3", foreground: "#334155" },
        success: { DEFAULT: "#15803D", foreground: "#FFFFFF" },
        warning: { DEFAULT: "#B45309", foreground: "#FFFFFF" },
        danger: { DEFAULT: "#B91C1C", foreground: "#FFFFFF" },
        default: { DEFAULT: "#F6EFE3", foreground: "#334155" },
      },
      layout: {
        radius: { small: "6px", medium: "10px", large: "14px" },
        borderWidth: { small: "1px", medium: "1px", large: "1px" },
      },
    },
  },
});
