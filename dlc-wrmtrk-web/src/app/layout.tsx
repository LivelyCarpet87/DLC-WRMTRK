import type { Metadata } from "next";
import {
  ColorSchemeScript,
  mantineHtmlProps,
  MantineProvider,
  AppShell,
  AppShellHeader,
  AppShellMain,
  Group,
  Text,
} from "@mantine/core";
import theme from "./theme";
import "./globals.css";
import Link from "next/link";

export const metadata: Metadata = {
  title: "DLC WRMTRK",
  description: "C. elegans speed data pipeline using DeepLabCut.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" {...mantineHtmlProps}>
      <head>
        <ColorSchemeScript />
      </head>
      <body className="antialiased">
        <MantineProvider theme={theme}>
          <AppShell header={{ height: 60 }} padding="md">
            <AppShellHeader>
              <Group className="h-full px-md w-full">
                <div className="flex flex-row gap-10  w-full justify-center">
                  <Link href="data_processing">
                    <Text className="text-blue-700">Data Processing</Text>
                  </Link>
                  <Link href="experiment_management">
                    <Text className="text-gray-700">Experiment Management</Text>
                  </Link>
                </div>
              </Group>
            </AppShellHeader>
            <AppShellMain>
              {children}
            </AppShellMain>
          </AppShell>
        </MantineProvider>
      </body>
    </html>
  );
}
