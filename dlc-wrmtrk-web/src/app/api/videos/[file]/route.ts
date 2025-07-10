import fs from "fs"
import path from "path"
import { NextResponse } from "next/server";

export async function GET(request: Request, { params }: { params: Promise<{ file: string }>} ) {
    const {file} = await params;
    try {
        let safeSuffix = path.normalize(`${file}`).replace(/^(\.\.(\/|\\|$))+/, '');
        let filePath = path.join('../data/outputs', safeSuffix);
        console.log(filePath);
    if (fs.existsSync(filePath)) {
        const fileBuffer = fs.readFileSync(filePath) // Synchronously read the file into a buffer
        const contentType = "video/mp4" // Extract the content type

        // * return the file buffer as is
        return new Response(fileBuffer, {
            headers: {
            "Content-Type": contentType,
            },
        })
    }

    return new Response(JSON.stringify("ERROR: VIDEO NOT FOUND"), {
        status: 404,
        headers: { 'Content-Type': 'application/json' }
    });
    } catch (error) {
        return new Response(JSON.stringify(error), {
            status: 500,
            headers: { 'Content-Type': 'application/json' }
        });
    }
}