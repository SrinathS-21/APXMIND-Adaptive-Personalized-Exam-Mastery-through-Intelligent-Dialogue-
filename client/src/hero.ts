import { heroui } from "@heroui/react";

export default heroui({
  defaultTheme: "dark",
  themes: {
    dark: {
      colors: {
        background: "#0A0B0F",
        foreground: "#F0F0F5",
        primary:   { DEFAULT: "#7B6EF6", foreground: "#FFFFFF" },
        secondary: { DEFAULT: "#22232F", foreground: "#B8B9C8" },
        success:   { DEFAULT: "#4ADE80", foreground: "#0A0B0F" },
        warning:   { DEFAULT: "#F59E0B", foreground: "#0A0B0F" },
        danger:    { DEFAULT: "#F87171", foreground: "#FFFFFF" },
        default:   { DEFAULT: "#22232F", foreground: "#B8B9C8" },
      },
      layout: {
        radius: { small: "6px", medium: "10px", large: "14px" },
        borderWidth: { small: "1px", medium: "1px", large: "1px" },
      },
    },
    light: {
      colors: {
        background: "#F5F5F7",
        foreground: "#0F0F14",
        primary:   { DEFAULT: "#6355E8", foreground: "#FFFFFF" },
        secondary: { DEFAULT: "#E8E8F0", foreground: "#3A3A50" },
        success:   { DEFAULT: "#16A34A", foreground: "#FFFFFF" },
        warning:   { DEFAULT: "#D97706", foreground: "#FFFFFF" },
        danger:    { DEFAULT: "#DC2626", foreground: "#FFFFFF" },
        default:   { DEFAULT: "#E8E8F0", foreground: "#3A3A50" },
      },
      layout: {
        radius: { small: "6px", medium: "10px", large: "14px" },
        borderWidth: { small: "1px", medium: "1px", large: "1px" },
      },
    },
  },
});
