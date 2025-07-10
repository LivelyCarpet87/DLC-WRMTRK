import { ColorSchemesSwitcher } from "@/components/color-schemes-switcher";
import {
  Group,
  Text,
  Title,
} from "@mantine/core";
import Image from "next/image";

export default function Home() {
  return (
      <div>
        <Title className="text-center mt-20">
          Welcome to DLC WRMTRK Web Interface
        </Title>
        <Text
          className="text-center text-gray-700 dark:text-gray-300 max-w-[500px] mx-auto mt-xl"
          ta="center"
          size="lg"
          maw={580}
          mx="auto"
          mt="xl"
        >
          Go to Data Processing to upload videos for processing and review processed results. Go to Experiment Management to manage experiment labels and condition tags.
        </Text>
      </div>
  );
}
