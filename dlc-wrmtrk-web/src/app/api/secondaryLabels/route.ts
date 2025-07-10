import { db } from "../../../../utils";

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export async function GET(request: Request) {
    const secondaryLabelQ = db.prepare('SELECT secondaryLabel FROM secondaryLabelPool').all();
    const secondaryLabels = secondaryLabelQ ? secondaryLabelQ.map( (row:{secondaryLabel:string})=>row.secondaryLabel ) : [];
    return new Response(JSON.stringify(secondaryLabels), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
    });
}

export async function POST(request: Request) {
    // Parse the request body
    const body = await request.formData();
    const newSecondaryLabelPool = body.get('secondaryLabelPool') ? JSON.parse(body.get('secondaryLabelPool')! as string) as string[] : [] as string[];
    
    const secondaryLabelQ = db.prepare('SELECT secondaryLabel FROM secondaryLabelPool').all();
    const existingSecondaryLabels = secondaryLabelQ ? secondaryLabelQ.map( (row:{secondaryLabel:string})=>row.secondaryLabel ) : [] as string[];

    const secondaryLabelsRm = (new Set(existingSecondaryLabels) as Set<string>).difference(new Set(newSecondaryLabelPool) as Set<string>);
    const secondaryLabelsAdd = (new Set(newSecondaryLabelPool) as Set<string>).difference(new Set(existingSecondaryLabels)) as Set<string>;


    secondaryLabelsRm.forEach(label => db.prepare('DELETE FROM secondaryLabelPool WHERE secondaryLabel = ?').run(label));
    secondaryLabelsAdd.forEach(label => db.prepare('INSERT INTO secondaryLabelPool(secondaryLabel) VALUES(?)').run(label));
    
    return new Response(JSON.stringify("OK"), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
    });
}
