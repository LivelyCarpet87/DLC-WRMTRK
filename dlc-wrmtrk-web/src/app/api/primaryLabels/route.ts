import { db } from "../../../../utils";

export async function GET(request: Request) {
    const primaryLabelQ = db.prepare('SELECT primaryLabel FROM primaryLabelPool').all();
    const primaryLabels = primaryLabelQ ? primaryLabelQ.map( (row:{primaryLabel:string})=>row.primaryLabel ) : [];
    return new Response(JSON.stringify(primaryLabels), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
    });
}

export async function POST(request: Request) {
    // Parse the request body
    const body = await request.formData();
    const newPrimaryLabelPool = body.get('primaryLabelPool') ? JSON.parse(body.get('primaryLabelPool')! as string) as string[] : [] as string[];
    
    const primaryLabelQ = db.prepare('SELECT primaryLabel FROM primaryLabelPool').all();
    const existingPrimaryLabels = primaryLabelQ ? primaryLabelQ.map( (row:{primaryLabel:string})=>row.primaryLabel ) : [] as string[];

    const primaryLabelsRm = (new Set(existingPrimaryLabels) as Set<string>).difference(new Set(newPrimaryLabelPool) as Set<string>);
    const primaryLabelsAdd = (new Set(newPrimaryLabelPool) as Set<string>).difference(new Set(existingPrimaryLabels)) as Set<string>;


    primaryLabelsRm.forEach(label => db.prepare('DELETE FROM primaryLabelPool WHERE primaryLabel = ?').run(label));
    primaryLabelsAdd.forEach(label => db.prepare('INSERT INTO primaryLabelPool(primaryLabel) VALUES(?)').run(label));
    
    return new Response(JSON.stringify("OK"), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
    });
}
