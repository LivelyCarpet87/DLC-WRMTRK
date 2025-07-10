import fs from 'node:fs';
import md5 from "md5";
import { db } from '../../../../utils';
import moment from 'moment';

export async function POST(request: Request) {
    // Parse the request body
    const body = await request.formData();
    console.log(body)
    
    if (body.get("action") == "SUBMIT") {
        const vidFile:File = body.get('vid_file')! as File;
        console.log(vidFile)
        const vidFileBytes = await vidFile.bytes()
        const vidFileHash = md5(vidFileBytes);
        fs.writeFileSync(`../data/ingest/videos/${vidFileHash}.mp4`, vidFileBytes);

        const plateUUID = body.get("plate_uuid") as string;

        db.prepare('INSERT OR REPLACE INTO videos(plateUUID, vidMD5, filename, proc_state, numInd, uploadTime) VALUES(?,?,?,?,?,?)').run(
            plateUUID,
            vidFileHash,
            vidFile.name,
            "pending",
            parseInt(body.get("num_ind") as string),
            moment().format()
        )

        return new Response(JSON.stringify("ok"), {
            status: 200,
            headers: { 'Content-Type': 'application/json' }
        });
    } else if (body.get("action") == "QUERY_VIDEO") {
        const videoMD5 = body.get("videoMD5") as string;
        const videoQ = db.prepare('SELECT filename, proc_state FROM videos WHERE vidMD5 = ?').get(videoMD5);
        if (!videoQ){
            return new Response(JSON.stringify({}), {
                status: 404,
                headers: { 'Content-Type': 'application/json' }
            });
        }

        const {filename, proc_state} = videoQ;

        let data = {};
        if (proc_state == "done" || proc_state == "warning"){
            const dataQ = db.prepare('SELECT ind, speed, confidence FROM detectedIndv WHERE vidMD5 = ?').all(videoMD5);
            let tsv = "";
            let table = [] as {ind:string, speed:number, confidence:boolean}[]

            for (let i in dataQ) {
                const row = dataQ[i];
                table.push({ind:row.ind, speed:row.speed, confidence:row.confidence==1})
                if(row.confidence==1){
                    tsv += `${row.ind}\t${row.speed}\n`
                }
            }

            data = {
                tsv: tsv,
                labeled_download: `/api/videos/${videoMD5}_labeled.mp4`,
                table: table
            };
    }

    return new Response(JSON.stringify(
        {
            filename: filename,
            proc_state: proc_state,
            displayData: data,
        }
    ), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
    });
  }
}