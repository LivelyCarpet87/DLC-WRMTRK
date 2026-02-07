"use client"
import {TagsInput } from "@mantine/core";
import useSWR, { Fetcher } from "swr";


export default function ExperimentManagement() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fetcher: Fetcher<string[]> = (arg: any, ...args: any) => fetch(arg, ...args).then(res => res.json());
  const heartbeatFetcher: Fetcher<{pending: number, processing: number}> = (arg: any, ...args: any) => fetch(arg, ...args).then(res => res.json());
  const primaryLabelsSwr = useSWR(`/api/primaryLabels`, fetcher);
  const secondaryLabelsSwr = useSWR(`/api/secondaryLabels`, fetcher);
  const conditionTagsSwr = useSWR(`/api/conditionTags`, fetcher);
  const heartbeatSwr = useSWR<{pending: number, processing: number}>('/api/heartbeat', heartbeatFetcher);

  let heartbeatData:{pending: string|number, processing: string|number} = {
    pending: "Loading...",
    processing: "Loading...",
  }
  if (heartbeatSwr.data) {
    console.log(heartbeatSwr.data)
    heartbeatData = heartbeatSwr.data;
  }

  // const [primaryLabelsPool, setPrimaryLabelsPool] = useState<string[]>(primaryLabelsSwr.data ? primaryLabelsSwr.data : [] as string[]);
    async function setPrimaryLabelsPool(primaryLabelPool:string[]){
        const formData = new FormData();

        formData.append('primaryLabelPool', JSON.stringify(primaryLabelPool));
        await fetch('/api/primaryLabels', {
            method: 'POST',
            body: formData
        });
        primaryLabelsSwr.mutate();
    }

    async function setSecondaryLabelsPool(secondaryLabelPool:string[]){
        const formData = new FormData();

        formData.append('secondaryLabelPool', JSON.stringify(secondaryLabelPool));
        await fetch('/api/secondaryLabels', {
            method: 'POST',
            body: formData
        });
        secondaryLabelsSwr.mutate();
    }

    async function setConditionTagsPool(secondaryLabelPool:string[]){
        const formData = new FormData();

        formData.append('conditionTagPool', JSON.stringify(secondaryLabelPool));
        await fetch('/api/conditionTags', {
            method: 'POST',
            body: formData
        });
        conditionTagsSwr.mutate();
    }


  return (
    <div className="flex flex-col gap-4 items-center justify-start">
      <div className="bg-slate-100 rounded-md p-3 flex flex-col gap-3">
        <p className="font-bold text-md text-start w-120">Video Processing Queue Status</p>
        <p>Pending Videos: {heartbeatData['pending']}</p>
        <p>Processing Videos: {heartbeatData['processing']}</p>
      </div>
      <div className="bg-slate-100 rounded-md p-3 flex flex-col gap-3">
        <TagsInput label="Primary Labels (ENTER to add)" data={[]} value={primaryLabelsSwr.data} onChange={setPrimaryLabelsPool} className="w-120"/>
        <TagsInput label="Secondary Labels (ENTER to add)" data={[]} value={secondaryLabelsSwr.data} onChange={setSecondaryLabelsPool} className="w-120" />
        <TagsInput label="Experiment Condition Tags (ENTER to add)" data={[]} value={conditionTagsSwr.data} onChange={setConditionTagsPool} className="w-120" />
      </div>
    </div>
  );
}
