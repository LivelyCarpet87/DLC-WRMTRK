"use client"
import { Divider, Select } from "@mantine/core";
import { UploadData } from "./_upload_data";
import { ProcessedData } from "./_processed_data";
import useSWR, { Fetcher } from "swr";
import { useRef, useState } from "react";


export default function DataProcessing() {
  const [primaryLabel, setPrimaryLabel] = useState(null as null|string);
  const [secondaryLabel, setSecondaryLabel] = useState(null as null|string);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fetcher: Fetcher<string[]> = (arg: any, ...args: any) => fetch(arg, ...args).then(res => res.json());
  const primaryLabelsSwr = useSWR(`/api/primaryLabels`, fetcher);
  const secondaryLabelsSwr = useSWR(`/api/secondaryLabels`, fetcher);
  const submissionCounter = useRef(0);

  return (
    <div className="flex flex-col gap-4 items-center justify-start">
      <div className="bg-slate-100 rounded-md p-3 flex flex-row gap-3">
        <Select
          className="w-40"
          placeholder="Primary Label"
          data={primaryLabelsSwr.data}
          onChange={setPrimaryLabel}
        />
        <Select
          className="w-40"
          placeholder="Secondary Label"
          data={secondaryLabelsSwr.data}
          onChange={setSecondaryLabel}
        />
      </div>
      <div className="flex flex-row justify-center items-start gap-5">
        <UploadData primaryLabel={primaryLabel} secondaryLabel={secondaryLabel} submissionCounter={submissionCounter}/>
        <Divider orientation="vertical" />
        <ProcessedData primaryLabel={primaryLabel} secondaryLabel={secondaryLabel} submissionCounter={submissionCounter} />
      </div>
    </div>
  );
}
