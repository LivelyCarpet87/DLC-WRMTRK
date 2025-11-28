"use client"

import { Title, Button, CopyButton, Table, Loader, Skeleton, Pill, Tooltip } from "@mantine/core";
import { UUID } from "crypto";
import { MutableRefObject, useRef, memo, useEffect } from "react";
import useSWR from "swr";


const VideoTile = memo(function VideoTile({md5}:{md5:string}){
    const pauseRef = useRef(false);
    const fetchWithToken = async (url:string, md5:string) => {
        const plateFormData = new FormData();
        plateFormData.append('action', "QUERY_VIDEO");
        plateFormData.append('videoMD5', md5 as string);
        return fetch(url, {
            method: "POST",
            body: plateFormData
        }).then(response => response.json());
    }
    function ifPause(){
        return pauseRef.current
    }
    const videoSWR = useSWR( ['/api/videos', md5], ([url, md5]) => fetchWithToken(url, md5),{ refreshInterval: 10000, keepPreviousData: true, isPaused: ifPause});
    
    const proc_state = videoSWR.data?.proc_state;
    useEffect(() => {
        if (proc_state === "done" || proc_state === "warning" || proc_state === "error" || proc_state === "failed") {
            pauseRef.current = true;
        }
    }, [proc_state]);

    if (videoSWR.data === undefined && (videoSWR.isLoading || videoSWR.isValidating)) {
        return (
            <div className="bg-slate-100 rounded-md p-3 flex flex-col gap-4 w-80">
                <>
                    <Skeleton height={8} radius="xl" />
                    <Skeleton height={8} mt={2} radius="xl" />
                    <Skeleton height={8} mt={2} width="70%" radius="xl" />
                </>
            </div>
        );
    }

    let proc_indicator = <Loader color="gray" type="bars" size="xs" />;
    if (proc_state == "pending"){
        proc_indicator = (<Loader color="gray" type="bars" size="xs" />);
    } else if (proc_state == "processing"){
        proc_indicator = (<Loader color="green" type="bars" size="xs" />);
    } else if (proc_state == "done"){
        pauseRef.current = true;
        proc_indicator = (
            <Tooltip label="Processing successful." openDelay={700}>
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="size-6 text-green-800">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M10.125 2.25h-4.5c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125v-9M10.125 2.25h.375a9 9 0 0 1 9 9v.375M10.125 2.25A3.375 3.375 0 0 1 13.5 5.625v1.5c0 .621.504 1.125 1.125 1.125h1.5a3.375 3.375 0 0 1 3.375 3.375M9 15l2.25 2.25L15 12" />
                </svg>
            </Tooltip>
        );
    } else if (proc_state == "warning"){
        proc_indicator = (
            <Tooltip label="Slight inconsistencies detected during processing." openDelay={700}>
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="size-6 text-blue-800">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m0-10.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.75c0 5.592 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.57-.598-3.75h-.152c-3.196 0-6.1-1.25-8.25-3.286Zm0 13.036h.008v.008H12v-.008Z" />
                </svg>
            </Tooltip>
        );
    } else if (proc_state == "error"){
        proc_indicator = (
            <Tooltip label="Extreme inconsistencies created during processing." openDelay={700}>
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="size-6 text-yellow-700">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
                </svg>
            </Tooltip>
        );
    } else if (proc_state == "failed"){
        proc_indicator = (
            <Tooltip label="Video failed to process." openDelay={700}>
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="size-6 text-red-800">
                    <path strokeLinecap="round" strokeLinejoin="round" d="m20.25 7.5-.625 10.632a2.25 2.25 0 0 1-2.247 2.118H6.622a2.25 2.25 0 0 1-2.247-2.118L3.75 7.5m6 4.125 2.25 2.25m0 0 2.25 2.25M12 13.875l2.25-2.25M12 13.875l-2.25 2.25M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125Z" />
                </svg>
            </Tooltip>
        );
    } else {
        proc_indicator = (
            <Tooltip label="Video failed to process." openDelay={700}>
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="size-6 text-red-800">
                    <path strokeLinecap="round" strokeLinejoin="round" d="m20.25 7.5-.625 10.632a2.25 2.25 0 0 1-2.247 2.118H6.622a2.25 2.25 0 0 1-2.247-2.118L3.75 7.5m6 4.125 2.25 2.25m0 0 2.25 2.25M12 13.875l2.25-2.25M12 13.875l-2.25 2.25M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125Z" />
                </svg>
            </Tooltip>
        );
    }

    let dataDisplay = <></>;
    if (proc_state == "done" || proc_state == "warning"){
        const tableRows = [] as React.JSX.Element[];
        for (const i in videoSWR.data.displayData.table){
            const row = videoSWR.data.displayData.table[i];
            tableRows.push(
                <Table.Tr key={row.ind}>
                    <Table.Td>{row.ind}</Table.Td>
                    <Table.Td>{row.speed.toFixed(2)}</Table.Td>
                    <Table.Td>
                        {
                            row.confidence ?
                            <Tooltip label="No inconsistencies detected." openDelay={2000}>
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="size-6 text-green-700">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
                                </svg>
                            </Tooltip>
                            :
                            <Tooltip label="Weak inconsistencies detected." openDelay={700}>
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="size-6 text-red-700">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 3v1.5M3 21v-6m0 0 2.77-.693a9 9 0 0 1 6.208.682l.108.054a9 9 0 0 0 6.086.71l3.114-.732a48.524 48.524 0 0 1-.005-10.499l-3.11.732a9 9 0 0 1-6.085-.711l-.108-.054a9 9 0 0 0-6.208-.682L3 4.5M3 15V4.5" />
                                </svg>
                            </Tooltip>
                        }
                    </Table.Td>
                </Table.Tr>
            )
        }

        dataDisplay = (
            <>
                <div className="flex flex-row gap-2">
                    <CopyButton value={videoSWR.data.displayData!.tsv}>
                        {({ copied, copy }) => (
                            <Button color={copied ? 'teal' : 'blue'} onClick={copy}>
                            {copied ? 'Copied data' : 'Copy data'}
                            </Button>
                        )}
                    </CopyButton>
                    <Button variant="filled" className="bg-gray-700" onClick={()=>window.open(videoSWR.data.displayData!.labeled_download)}>Download Labeled Video</Button>
                </div>
                <Table striped withTableBorder withColumnBorders>
                    <Table.Thead>
                        <Table.Tr>
                            <Table.Th>Individual</Table.Th>
                            <Table.Th>{"Speed (Pixels/Second)"}</Table.Th>
                            <Table.Th>Confidence</Table.Th>
                        </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                        {tableRows}
                    </Table.Tbody>
                </Table>
            </>
        );
    }

    return (
        <div className="border-2 border-slate-300 rounded-md p-3 flex flex-col gap-2 w-104">
            <div className="flex flex-row gap-2 items-center">
                <p className="text-ellipsis w-90">{videoSWR.data.filename}</p>
                {proc_indicator}
            </div>
            {dataDisplay}
        </div>
    );
})

function PlateTile({uuid}:{uuid:UUID}){
    const fetchWithToken = async (url:string, uuid:string) => {
        const plateFormData = new FormData();
        plateFormData.append('action', "QUERY_PLATE");
        plateFormData.append('plateUUID', uuid as string);
        return fetch(url, {
            method: "POST",
            body: plateFormData
        }).then(response => response.json());
    }
    const plateSWR = useSWR( ['/api/plates', uuid], ([url, uuid]) => fetchWithToken(url, uuid), { refreshInterval: 1000, keepPreviousData: true});
    
    if (plateSWR.data === undefined && (plateSWR.isLoading || plateSWR.isValidating)) {
        return (
        <div className="bg-slate-100 rounded-md p-3 flex flex-col gap-4 w-112">
            <div className="flex flex-row gap-4 w-104 items-center justify-between">
                <p className="text-ellipsis w-50">PlateID: Loading...</p>
                <div className="flex flex-row gap-2 items-center">
                    Loading...
                </div>
            </div>
            <div className="bg-slate-100 rounded-md p-3 flex flex-col gap-4 w-80">
                <>
                    <Skeleton height={8} radius="xl" />
                    <Skeleton height={8} mt={2} radius="xl" />
                    <Skeleton height={8} mt={2} width="70%" radius="xl" />
                </>
            </div>
        </div>
            
        );
    }

    const condTags = [] as React.JSX.Element[];
    for (const i in plateSWR.data!.conditionTags) {
        condTags.push(<Pill key={plateSWR.data!.conditionTags[i]} className="bg-slate-300">{plateSWR.data!.conditionTags[i]}</Pill>);
    }

    const videoTiles = [] as React.JSX.Element[]
    for (const i in plateSWR.data!.videoMD5s) {
        videoTiles.push(<VideoTile key={plateSWR.data!.videoMD5s[i]} md5={plateSWR.data!.videoMD5s[i]} />);
    }

    return (
        <div className="bg-slate-100 rounded-md p-3 flex flex-col gap-4 w-112">
            <div className="flex flex-row gap-4 w-104 items-center justify-between">
                <p className="text-ellipsis w-50">PlateID: {plateSWR.data!.plateID}</p>
                <div className="flex flex-row gap-2 items-center">
                    {condTags}
                </div>
            </div>
            {videoTiles}
        </div>
    )
}

export function ProcessedData({primaryLabel, secondaryLabel, submissionCounter}:{primaryLabel:string|null, secondaryLabel:string|null, submissionCounter: MutableRefObject<number>}){
    const fetchWithToken = async (url:string, primaryLabel:string,secondaryLabel:string) => {
        const plateFormData = new FormData();
        plateFormData.append('action', "FETCH_ALL");
        plateFormData.append('primaryLabel', primaryLabel as string);
        plateFormData.append('secondaryLabel', secondaryLabel as string);
        return fetch(url, {
            method: "POST",
            body: plateFormData
        }).then(response => response.json());
    }
    console.log(submissionCounter.current);
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const platesSWR = useSWR( (primaryLabel && secondaryLabel) ? ['/api/plates', primaryLabel,secondaryLabel, submissionCounter.current] : null, ([url, primaryLabel,secondaryLabel, submissionCounterCur]) => fetchWithToken(url, primaryLabel!,secondaryLabel!), { refreshInterval: 1000, keepPreviousData: true });

    const plateTiles = [] as React.JSX.Element[];
    if (platesSWR.data){
        for (const i in platesSWR.data){
            plateTiles.push(<PlateTile key={platesSWR.data[i]} uuid={platesSWR.data[i]} />)
        }
    }

    return (
        <div className="flex flex-col justify-start items-center gap-5 w-112">
            <Title>Processed Data</Title>
            <div className="flex flex-col justify-start items-center gap-5 w-112">
                {plateTiles}
            </div>
        </div>
    );
}
