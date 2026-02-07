import { db } from "../../../../utils";

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export async function GET(request: Request) {
    const pendingCount = db.prepare("SELECT COUNT(*) FROM videos WHERE proc_state = 'pending'").get();
    const processingCount = db.prepare("SELECT COUNT(*) FROM videos WHERE proc_state = 'processing'").get();
    return new Response(JSON.stringify({
        "pending": pendingCount['COUNT(*)'],
        "processing": processingCount['COUNT(*)']
    }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
    });
}