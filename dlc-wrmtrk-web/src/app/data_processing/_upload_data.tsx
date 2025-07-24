"use client"
import {
  Title,
  TextInput,
  MultiSelect,
  FileInput,
  NumberInput,
  Button,
  ActionIcon,
  Divider,
  Notification,
  Tooltip,
} from "@mantine/core";
import { UUID } from "node:crypto";
import { MutableRefObject, useState } from 'react';
import { v4 as uuidv4 } from 'uuid';
import useSWR, { Fetcher } from 'swr';
import { useFocusTrap, useHotkeys } from "@mantine/hooks";

function VideoUploadTile(
  {onDelete, onChange, uuid, file, num}:
  {onDelete:(uuid:UUID)=>void, onChange:(uuid:UUID, videoFile:null|File, numInd:undefined|number)=>void, uuid:UUID, file:File | null, num:number | undefined}
){
  const [videoFile, setVideoFile] = useState(file);
  const [numInd, setNumInd] = useState(num);

  function onVideoFileChange(file:null|File){
    setVideoFile(file);
    onChange(uuid, file, numInd);
  }

  function onNumIndChange(numInd:number|string){
    numInd = numInd as number;
    setNumInd(numInd);
    onChange(uuid, videoFile, numInd);
  }

  return (
    <div className="bg-slate-200 rounded-md p-2 flex flex-row gap-2 items-start">
      <div className="flex flex-row gap-4 items-end p-2">
        <FileInput
          className="w-60"
          label="Microscope Video Recording"
          placeholder="Select Video (.mp4)"
          value={videoFile}
          onChange={onVideoFileChange}
          ref={useFocusTrap(videoFile == null)}
        />
        <Tooltip label="Total # of individuals that appear in video." openDelay={700}>
          <NumberInput
            className="w-26"
            label="Total ind count"
            placeholder="Ind Count"
            min={1}
            max={10}
            value={numInd}
            onChange={onNumIndChange}
          />
        </Tooltip>
      </div>
      <Tooltip label="Remove this video entry from plate." openDelay={700}>
        <ActionIcon variant="transparent" aria-label="Settings" className="size-9 -m-2" onClick={() => onDelete(uuid) }>
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="size-6 text-red-700">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 12H9m12 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
          </svg>
        </ActionIcon>
      </Tooltip>
    </div>
  );
}

function PlateTile({onDelete, uuid, primaryLabel, secondaryLabel, submissionCounter}:{onDelete:(uuid:UUID)=>void, uuid:UUID, primaryLabel:string|null, secondaryLabel:string|null, submissionCounter: MutableRefObject<number>}){
  const [videoTiles, setVideoTiles] = useState([] as UUID[]);
  const [videos, setVideos] = useState(new Map() as Map<UUID,{video:null|File,numInd:undefined|number}>);
  const [plateID, setPlateID] = useState("");
  const [normImg, setNormImg] = useState(null as null|File);
  const [conditions, setConditions] = useState([] as string[]);
  const [warnMsg, setWarnMsg] = useState("");

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fetcher: Fetcher<string[]> = (arg: any, ...args: any) => fetch(arg, ...args).then(res => res.json());
  const conditionTagsSwr = useSWR(`/api/conditionTags`, fetcher);

  function addVideoTile() {
    const newVideoTiles = [... videoTiles];
    const key = uuidv4() as UUID;
    newVideoTiles.push(key);
    setVideoTiles(newVideoTiles);
    const newVideos = new Map(videos);
    newVideos.set(key, {video:null,numInd:undefined});
    setVideos(newVideos);
  }

  function deleteVideoTile(uuid:UUID) {
    setVideoTiles(videoTiles.filter( key => key != uuid));
    const newVideos = new Map(videos);
    newVideos.delete(uuid);
    setVideos(newVideos);
  }

  function onVideoTileChange(uuid:UUID, videoFile:null|File, numInd:undefined|number){
    const newVideos = new Map(videos);
    newVideos.set(uuid, {video:videoFile,numInd:numInd});
    setVideos(newVideos);
  }

  async function submitPlate(){
    console.log("Submitting Plate.");
    console.log(primaryLabel, secondaryLabel, plateID, normImg,conditions, videos);
    if (primaryLabel == null){
      setWarnMsg('Primary Label has not been provided. The plate was not submitted for processing.');
      return;
    } else if (secondaryLabel == null){
      setWarnMsg('Secondary Label has not been provided. The plate was not submitted for processing.');
      return;
    } else if (plateID == ""){
      setWarnMsg('Plate ID has not been provided. The plate was not submitted for processing.');
      return;
    } else if (normImg == null){
      setWarnMsg('Normalizing Image has not been provided. The plate was not submitted for processing.');
      return;
    } else if (normImg.type != "image/png") {
        setWarnMsg("Normalizing Image provided was not a PNG. The plate was not submitted for processing.");
        return;
    } else if (normImg.size >= 16000000) {
        setWarnMsg("Normalizing Image provided exceeded Max Size of 16MB. The plate was not submitted for processing.");
        return;
    } else if (videoTiles.length == 0){
      setWarnMsg('No videos have been provided. The plate was not submitted for processing.');
      return;
    }
    /*
      if (conditions.length == 0){
        console.log('Condition Tags not provided.');
      } 
      */
    for (const ind in videoTiles) {
      const vid_uuid = videoTiles[ind];
      if (videos.get(vid_uuid) === undefined) {
        console.warn("FOUND UUID NOT DEFINED IN MAP");
        console.log(vid_uuid, videos);
        return;
      } else if (videos.get(videoTiles[ind])!.video == null) {
        setWarnMsg("Video file has not been provided for a specific entry. The plate was not submitted for processing.");
        return;
      } else if (videos.get(videoTiles[ind])!.video!.type != "video/mp4") {
        setWarnMsg("Video file provided for a specific entry was not an MP4 file. The plate was not submitted for processing.");
        return;
      } else if (videos.get(videoTiles[ind])!.video!.size >= 200000000) {
        setWarnMsg("Video file provided for a specific entry exceeded the max size of 200MB. The plate was not submitted for processing.");
        return;
      } else if (videos.get(videoTiles[ind])!.numInd == undefined || videos.get(videoTiles[ind])!.numInd == 0) {
        setWarnMsg("Total Number of Individuals has not been provided for a specific entry. The plate was not submitted for processing.");
        return;
      }
    }
    setWarnMsg("");

    const plateFormData = new FormData();
    plateFormData.append('uuid', uuid);
    plateFormData.append('action', "SUBMIT");
    plateFormData.append('primaryLabel', primaryLabel);
    plateFormData.append('secondaryLabel', secondaryLabel);
    plateFormData.append('plateID', plateID);
    plateFormData.append('normImg', normImg);
    plateFormData.append('conditions', JSON.stringify(conditions));

    const plateSubmitResponse = await fetch('/api/plates', {
        method: 'POST',
        body: plateFormData
    });

    for (const ind in videoTiles) {
      const vid_uuid = videoTiles[ind];
      if (videos.get(vid_uuid) === undefined) {
        console.warn("FOUND UUID NOT DEFINED IN MAP");
        console.log(uuid, videos);
        continue;
      }
      const formData = new FormData();
      formData.append('plate_uuid', uuid);
      formData.append('action', "SUBMIT");
      formData.append('vid_file', videos.get(vid_uuid)!.video as Blob);
      formData.append('num_ind', videos.get(vid_uuid)!.numInd!.toString());

      await fetch('/api/videos', {
          method: 'POST',
          body: formData
      });
    }

    const body = await plateSubmitResponse.json() as { status: 'ok' | 'fail', message: string };

    if (body.status === 'ok') {
        submissionCounter.current += 1;
    } else {
        console.log("Plate submission failed.", body);
    }

  }

  const notifications = [] as React.JSX.Element[]
  if (warnMsg != ""){
    notifications.push(
      <Notification key="warning" color="yellow" title="Warning!" onClose={ () => {setWarnMsg("");} } className="w-104"> 
        {warnMsg}
      </Notification>
    )
  }
  
  return (
    <div className="bg-slate-100 rounded-md p-4 flex flex-col gap-4">
      <div className="flex flex-row gap-4">
        <TextInput
          className="w-40"
          label="Plate ID"
          placeholder="Plate ID"
          value={plateID}
          onChange={(event) => setPlateID(event.currentTarget.value)}
          ref={useFocusTrap(plateID === "")}
        />
        <Tooltip label="Image to convert pixels to distance." openDelay={700}>
          <FileInput
            className="w-60"
            label="Normalization Image"
            placeholder="Select Normalization Image"
            value={normImg}
            onChange={setNormImg}
          />
        </Tooltip>
      </div>
      <MultiSelect
        className="w-104"
        label="Conditions"
        data={conditionTagsSwr.data}
        value={conditions}
        onChange={setConditions}
      />
      <Divider my="xs"/>
      
      {videoTiles.map( uuid => <VideoUploadTile key={uuid} onDelete={deleteVideoTile} onChange={onVideoTileChange} uuid={uuid} file={videos.get(uuid)!.video!} num={videos.get(uuid)?.numInd} />)}

      <Button variant="outline" onClick={addVideoTile}>
        + Add Video
      </Button>
      <Divider my="xs"/>

      {notifications}

      <div className="grid grid-cols-2 gap-4">
        <Tooltip label="Can resubmit to update information." openDelay={700}>
          <Button className="bg-green-700" onClick={submitPlate}>
            Submit For Processing
          </Button>
        </Tooltip>
        <Tooltip label="This does not delete submitted data." openDelay={700}>
          <Button className="bg-red-700" onClick={() => onDelete(uuid) }>
            Delete Plate Locally
          </Button>
        </Tooltip>
      </div>
    </div>
  )
}

export function UploadData({primaryLabel, secondaryLabel, submissionCounter}:{primaryLabel:string|null, secondaryLabel:string|null,submissionCounter: MutableRefObject<number>}){
    const [plates, setPlates] = useState([] as UUID[]);

    function addPlate() {
      const newPlates = [... plates];
      const key = uuidv4() as UUID;
      newPlates.push(key);
      setPlates(newPlates);
    }

    function deletePlate(uuid:UUID) {
      console.log(plates);
      setPlates(plates.filter( key => key != uuid));
    }

    useHotkeys([['ctrl+K', () => addPlate()]]);

    return (
        <div className="flex flex-col justify-start items-center gap-5">
          <Title>Upload Data</Title>

          {plates.map( uuid => (
              <PlateTile key={uuid} onDelete={deletePlate} uuid={uuid} primaryLabel={primaryLabel} secondaryLabel={secondaryLabel} submissionCounter={submissionCounter}></PlateTile>
            )
          )}

          <Tooltip label="Create another form for another plate. Hotkey: CTRL+K" openDelay={700}>
            <Button variant="outline" onClick={addPlate} className="w-114">
              + Add Plate
            </Button>
          </Tooltip>
      </div>
    );
}