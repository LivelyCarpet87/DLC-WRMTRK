import { db } from "../../../../utils";

export async function GET(request: Request) {
    const conditionTagQ = db.prepare('SELECT conditionTag FROM conditionTagPool').all();
    const conditionTags = conditionTagQ ? conditionTagQ.map( (row:{conditionTag:string})=>row.conditionTag ) : [];
    return new Response(JSON.stringify(conditionTags), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
    });
}

export async function POST(request: Request) {
    // Parse the request body
    const body = await request.formData();
    const newConditionTagPool = body.get('conditionTagPool') ? JSON.parse(body.get('conditionTagPool')! as string) as string[] : [] as string[];
    
    const conditionTagQ = db.prepare('SELECT conditionTag FROM conditionTagPool').all();
    const existingConditionTags = conditionTagQ ? conditionTagQ.map( (row:{conditionTag:string})=>row.conditionTag ) : [] as string[];

    const conditionTagsRm = (new Set(existingConditionTags) as Set<string>).difference(new Set(newConditionTagPool) as Set<string>);
    const conditionTagsAdd = (new Set(newConditionTagPool) as Set<string>).difference(new Set(existingConditionTags)) as Set<string>;


    conditionTagsRm.forEach(label => db.prepare('DELETE FROM conditionTagPool WHERE conditionTag = ?').run(label));
    conditionTagsAdd.forEach(label => db.prepare('INSERT INTO conditionTagPool(conditionTag) VALUES(?)').run(label));
    
    return new Response(JSON.stringify("OK"), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
    });
}
