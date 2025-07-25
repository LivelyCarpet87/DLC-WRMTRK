import { db } from "../../../../utils";

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export function GET(request: Request) {
    db.pragma('journal_mode = WAL');
    db.prepare("CREATE TABLE IF NOT EXISTS primaryLabelPool (primaryLabel TEXT UNIQUE);").run();
    db.prepare("CREATE TABLE IF NOT EXISTS secondaryLabelPool (secondaryLabel TEXT UNIQUE);").run();
    db.prepare("CREATE TABLE IF NOT EXISTS conditionTagPool (conditionTag TEXT UNIQUE);").run();
    db.prepare("CREATE TABLE IF NOT EXISTS plates (plateUUID TEXT PRIMARY KEY, plateID TEXT, primaryLabel TEXT, secondaryLabel TEXT, normMD5 TEXT, uploadTime TEXT);").run();
    db.prepare("CREATE TABLE IF NOT EXISTS conditions (plateUUID TEXT, condTag TEXT, UNIQUE (plateUUID,condTag));").run();
    db.prepare("CREATE TABLE IF NOT EXISTS videos (plateUUID TEXT, vidMD5 TEXT UNIQUE, filename TEXT, proc_state TEXT, numInd INTEGER, uploadTime TEXT);").run();
    db.prepare("CREATE TABLE IF NOT EXISTS detectedIndv (vidMD5 TEXT, ind TEXT, speed REAL, confidence BOOLEAN, UNIQUE (vidMD5,ind));").run();
    db.prepare("CREATE TABLE IF NOT EXISTS normalization (normMD5 TEXT, value REAL, UNIQUE (normMD5,value));").run();
    return new Response(JSON.stringify({status:"ok"}), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
    });
}
