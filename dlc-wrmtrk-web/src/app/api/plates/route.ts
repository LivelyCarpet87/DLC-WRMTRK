import fs from 'node:fs';
import md5 from "md5";
import { db } from '../../../../utils';
import moment from 'moment';

export async function POST(request: Request) {
  // Parse the request body
  const body = await request.formData();
 
  if (body.get("action") == "SUBMIT") {
    const uuid = body.get("uuid") as string;
    const normImg:File = body.get('normImg')! as File;
    console.log(normImg)
    const normImgBytes = await normImg.bytes()
    const normImgHash = md5(normImgBytes);
    fs.writeFileSync(`../data/ingest/normalizingImages/${normImgHash}.png`, normImgBytes);

    db.prepare('INSERT OR REPLACE INTO plates(plateUUID, plateID, primaryLabel, secondaryLabel, normMD5, uploadTime) VALUES(?,?,?,?,?,?)').run(
      uuid,
      body.get("plateID") as string,
      body.get("primaryLabel") as string,
      body.get("secondaryLabel") as string,
      normImgHash,
      moment().format()
    )
      
    db.prepare('INSERT OR REPLACE INTO normalization(normMD5, value) VALUES(?, NULL)').run(normImgHash)

    const conditionTags = new Set( body.get('conditions') ? JSON.parse(body.get('conditions')! as string) as string[] : [] as string[] )
    conditionTags.forEach(label => db.prepare('INSERT OR REPLACE INTO conditions(plateUUID, condTag) VALUES(?,?)').run(uuid, label));

    return new Response(JSON.stringify({status:"ok"}), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
    });
  } else if (body.get("action") == "FETCH_ALL") {
    const primaryLabel = body.get("primaryLabel") as string;
    const secondaryLabel = body.get("secondaryLabel") as string;

    const plateUUIDQ = db.prepare('SELECT plateUUID FROM plates WHERE primaryLabel = ? AND secondaryLabel = ?').all(primaryLabel, secondaryLabel);
    const plateUUIDs = plateUUIDQ ? plateUUIDQ.map( (row:{plateUUID:string})=>row.plateUUID ) : [] as string[];

    return new Response(JSON.stringify(plateUUIDs), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
    });
  } else if (body.get("action") == "QUERY_PLATE") {
    const plateUUID = body.get("plateUUID");
    const plateQ = db.prepare('SELECT * FROM plates WHERE plateUUID = ?').get(plateUUID)

    if (!plateQ){
      return new Response(JSON.stringify({status:"Not Found"}), {
        status: 404,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const plateID = plateQ.plateID;

    const tagQ = db.prepare('SELECT condTag FROM conditions WHERE plateUUID = ?').all(plateUUID);
    const conditionTags = tagQ ? tagQ.map( (row:{condTag:string})=>row.condTag ) : [] as string[];
    
    const videoQ = db.prepare('SELECT vidMD5 FROM videos WHERE plateUUID = ?').all(plateUUID);
    const videoMD5s = videoQ ? videoQ.map( (row:{vidMD5:string})=>row.vidMD5 ) : [] as string[];

    return new Response(JSON.stringify(
        {
            plateID: plateID,
            conditionTags:conditionTags,
            videoMD5s: videoMD5s,
        }
    ), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
    });
  }
  
}
